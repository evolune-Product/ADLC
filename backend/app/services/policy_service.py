"""
Approval policy engine — the control-plane primitive the category is converging on.

Forrester's ADP criteria and every 2026 agent-governance writeup name the same
five things: tool/path allowlists, read-to-write escalation, human approval
routing, spend caps, and an audit trail. The approval gate already existed here;
this module gives it teeth by deciding, per environment:

  * how many humans must approve, and which roles count
  * whether the Reviewer agent must pass, and at what score
  * what the agent was never allowed to touch in the first place
  * what a single run may cost

Resolution order (most specific wins): project+env → project+'*' → org+env →
org+'*' → built-in default.
"""
from __future__ import annotations

import fnmatch
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.governance import ApprovalPolicy
from app.models.insight import ReviewFinding
from app.models.run import Approval
from app.services import audit_service

SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

# Production-shaped default used when an org has defined no policy at all:
# one approver, no reviewer gate. Deliberately permissive — governance a team
# didn't ask for that blocks their first run is how a pilot dies.
DEFAULT_POLICY = {
    "name": "Default",
    "environment": "*",
    "min_approvers": 1,
    "approver_roles": ["owner", "admin", "member"],
    "require_review_pass": False,
    "min_review_score": 0,
    "block_on_severity": None,
    "protected_paths": [],
    "protected_branches": [],
    "max_files_changed": 0,
    "max_run_cost_cents": 0,
    "max_concurrent_runs": 0,
    "max_queue_depth": 0,
    "conditions": [],
}


@dataclass
class PolicyDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    policy_id: uuid.UUID | None = None
    policy_name: str = "Default"
    approvals_required: int = 1
    approvals_have: int = 0
    review_score: int | None = None

    def as_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reasons": self.reasons,
            "policy_id": str(self.policy_id) if self.policy_id else None,
            "policy_name": self.policy_name,
            "approvals_required": self.approvals_required,
            "approvals_have": self.approvals_have,
            "review_score": self.review_score,
        }


def _as_dict(p: ApprovalPolicy) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "environment": p.environment,
        "min_approvers": p.min_approvers,
        "approver_roles": p.approver_roles or DEFAULT_POLICY["approver_roles"],
        "require_review_pass": p.require_review_pass,
        "min_review_score": p.min_review_score,
        "block_on_severity": p.block_on_severity,
        "protected_paths": p.protected_paths or [],
        "protected_branches": p.protected_branches or [],
        "max_files_changed": p.max_files_changed,
        "max_run_cost_cents": p.max_run_cost_cents,
        "max_concurrent_runs": p.max_concurrent_runs or 0,
        "max_queue_depth": p.max_queue_depth or 0,
        "conditions": p.conditions or [],
    }


def resolve_policy(db: Session, *, org_id, project_id, environment: str = "*") -> dict:
    """Return the effective policy dict for this project + environment."""
    candidates = (
        db.query(ApprovalPolicy)
        .filter(ApprovalPolicy.is_active.is_(True))
        .filter(
            (ApprovalPolicy.project_id == project_id)
            | ((ApprovalPolicy.project_id.is_(None)) & (ApprovalPolicy.org_id == org_id))
        )
        .all()
    )
    if not candidates:
        return dict(DEFAULT_POLICY)

    def rank(p: ApprovalPolicy) -> int:
        score = 0
        if p.project_id == project_id:
            score += 2
        if p.environment == environment:
            score += 1
        return score

    scoped = [p for p in candidates if p.environment in (environment, "*")]
    if not scoped:
        return dict(DEFAULT_POLICY)
    return _as_dict(max(scoped, key=rank))


# ── Pre-flight: what the agent may touch ──────────────────────────────────────

def check_changes(policy: dict, *, files: list[dict], branch: str | None) -> list[str]:
    """
    Run BEFORE the PR is opened. Blast-radius control is cheaper than review:
    it is the read-to-write escalation boundary that agent-governance writeups
    identify as the critical heuristic.
    """
    violations: list[str] = []
    paths = [f.get("path", "") for f in files]

    for pattern in policy.get("protected_paths") or []:
        hits = [p for p in paths if fnmatch.fnmatch(p, pattern)]
        if hits:
            violations.append(
                f"Protected path '{pattern}' would be modified: {', '.join(hits[:5])}"
            )

    for pattern in policy.get("protected_branches") or []:
        if branch and fnmatch.fnmatch(branch, pattern):
            violations.append(f"Branch '{branch}' matches protected pattern '{pattern}'")

    cap = policy.get("max_files_changed") or 0
    if cap and len(files) > cap:
        violations.append(f"Change touches {len(files)} files; policy allows {cap}")

    return violations


# ── Approval gate: may this run deploy? ───────────────────────────────────────

def evaluate_deploy(
    db: Session, *, run_id, policy: dict, approver_roles_present: list[str] | None = None
) -> PolicyDecision:
    reasons: list[str] = []

    approvals = (
        db.query(Approval)
        .filter(Approval.run_id == run_id, Approval.decision == "approved")
        .all()
    )
    distinct_reviewers = {a.reviewer_id for a in approvals if a.reviewer_id}
    have = len(distinct_reviewers) or len(approvals)
    need = policy.get("min_approvers", 1)
    if have < need:
        reasons.append(f"{have}/{need} required approvals")

    findings = db.query(ReviewFinding).filter(ReviewFinding.run_id == run_id).all()
    score = review_score(findings) if findings else None

    if policy.get("require_review_pass"):
        if score is None:
            reasons.append("Reviewer agent has not produced a verdict")
        elif score < policy.get("min_review_score", 0):
            reasons.append(f"Review score {score} is below the required {policy['min_review_score']}")

    block_at = policy.get("block_on_severity")
    if block_at:
        threshold = SEVERITY_RANK.get(block_at, 99)
        blocking = [f for f in findings if SEVERITY_RANK.get(f.severity, 0) >= threshold]
        if blocking:
            reasons.append(
                f"{len(blocking)} unresolved {block_at}+ finding(s): "
                + "; ".join(f.message[:60] for f in blocking[:3])
            )

    if approver_roles_present is not None:
        allowed_roles = set(policy.get("approver_roles") or [])
        if allowed_roles and not (set(approver_roles_present) & allowed_roles):
            reasons.append(f"Approver role not permitted (needs one of: {', '.join(sorted(allowed_roles))})")

    return PolicyDecision(
        allowed=not reasons,
        reasons=reasons,
        policy_id=policy.get("id"),
        policy_name=policy.get("name", "Default"),
        approvals_required=need,
        approvals_have=have,
        review_score=score,
    )


def review_score(findings) -> int:
    """
    100 = clean. Weighted so one critical finding alone fails a 70-point gate,
    which is the behaviour an engineering lead expects from "block on critical".
    """
    weights = {"info": 0, "low": 3, "medium": 8, "high": 20, "critical": 40}
    penalty = sum(weights.get(getattr(f, "severity", "info"), 0) for f in findings)
    return max(0, 100 - penalty)


# ── Concurrency: how many runs may be in flight at once ───────────────────────
#
# The named gap this closes is Devin's "automations queueing": a cap on
# concurrent runs plus a bounded queue behind it. It lives here rather than in
# the Celery task because it is a *policy* decision — the same place an org
# already says which paths agents may touch and how many approvers a deploy
# needs — and because the answer has to be identical whether a run was started
# from the Runs page, from chat, from CI through the public API, or by an agent
# through MCP.
#
# Both limits default to 0 (unlimited), so an org that never configures them
# sees exactly the behaviour it saw before this existed.

# Statuses that occupy a concurrency slot. `awaiting_approval` deliberately does
# NOT: a run parked at the gate is waiting on a human who may be asleep, and
# holding a slot for it would let three un-reviewed PRs deadlock a project's
# entire pipeline.
ACTIVE_STATUSES = ("running",)
QUEUED_STATUSES = ("queued",)


@dataclass
class ConcurrencyDecision:
    """Whether a run may start now, wait, or be refused outright."""
    admitted: bool                 # dispatch to Celery immediately
    queued: bool                   # accepted, but held until a slot frees
    reason: str | None = None      # set when neither — the run is refused
    running: int = 0
    waiting: int = 0
    limit: int = 0

    def as_dict(self) -> dict:
        return {
            "admitted": self.admitted, "queued": self.queued, "reason": self.reason,
            "running": self.running, "waiting": self.waiting, "limit": self.limit,
        }


def check_concurrency(db: Session, *, project_id, org_id, policy: dict | None = None,
                      exclude_run_id=None) -> ConcurrencyDecision:
    """
    Decide whether a newly created run may start.

    Three outcomes, and the distinction matters to the caller:
      admitted  — dispatch it now
      queued    — keep it at `queued` and do not dispatch; a finishing run will
                  promote it (see `promote_next`)
      neither   — refuse it, because the queue itself is full. A queue that
                  grows without bound is not backpressure, it is a memory leak
                  with a nicer name.
    """
    from app.models.run import Run

    # `is None`, not a truthiness test: an explicitly-passed empty policy is a
    # valid caller intent ("no limits"), and falling through to a DB lookup for
    # it would both hit the database needlessly and crash any caller that
    # passed a policy precisely so it would not need a session.
    if policy is None:
        policy = resolve_policy(db, org_id=org_id, project_id=project_id)
    limit = int(policy.get("max_concurrent_runs") or 0)
    if limit <= 0:
        return ConcurrencyDecision(admitted=True, queued=False, limit=0)

    def _count(statuses):
        q = db.query(Run).filter(Run.project_id == project_id, Run.status.in_(statuses))
        if exclude_run_id is not None:
            q = q.filter(Run.id != exclude_run_id)
        return q.count()

    running = _count(ACTIVE_STATUSES)
    waiting = _count(QUEUED_STATUSES)

    if running < limit:
        return ConcurrencyDecision(admitted=True, queued=False,
                                   running=running, waiting=waiting, limit=limit)

    depth = int(policy.get("max_queue_depth") or 0)
    if depth > 0 and waiting >= depth:
        return ConcurrencyDecision(
            admitted=False, queued=False,
            reason=(f"{running} runs already in flight and the queue is full "
                    f"({waiting}/{depth}). Wait for one to finish or raise the "
                    f"limit on policy '{policy.get('name', 'Default')}'."),
            running=running, waiting=waiting, limit=limit,
        )

    return ConcurrencyDecision(admitted=False, queued=True,
                               running=running, waiting=waiting, limit=limit)


# ── Conditional escalation: monetary thresholds, risk-level rules ────────────
#
# The gap this closes: CLAUDE.md named it explicitly — "the full spec section-18
# policy-condition vocabulary: monetary thresholds, risk-level rules... only
# min_approvers/approver_roles are real". Scoped to the workflow-approval path
# only (see `_evaluate_workflow_approval` below) — the SDLC deploy gate
# (`evaluate_deploy`) never evaluates conditions, because a `Run` has no
# amount or risk field to check them against; a `Work` row does.

_CONDITION_OPERATORS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gte": lambda a, b: a is not None and a >= b,
    "lte": lambda a, b: a is not None and a <= b,
    "gt": lambda a, b: a is not None and a > b,
    "lt": lambda a, b: a is not None and a < b,
    "in": lambda a, b: a in (b or []),
    "not_in": lambda a, b: a not in (b or []),
}


def _condition_field_value(field: str, work) -> object:
    """The vocabulary a condition may key off — deliberately small, and drawn
    only from columns/context keys `Work` already has, not a new schema.
    `amount_cents` and `risk_level` live in `Work.context` (a free JSONB bag
    every Work row already carries) because "how much is this request for"
    and "how risky is it" are intake-form data, not columns this generic
    model should grow just for policy's sake."""
    if field == "amount_cents":
        value = (work.context or {}).get("amount_cents")
        return value if isinstance(value, (int, float)) else None
    if field == "risk_level":
        return (work.context or {}).get("risk_level")
    if field == "department_id":
        return str(work.department_id) if work.department_id else None
    if field == "team_id":
        return str(work.team_id) if work.team_id else None
    if field == "work_type":
        return work.type
    return None


def resolve_condition_override(conditions: list[dict], *, work) -> dict | None:
    """
    The single matching condition to apply, or None if no condition matches
    (or there is nothing to match against — a workflow run with no linked
    Work item, e.g. a manual trigger, has no fields for a condition to read).

    "Monetary thresholds" and "risk-level rules" both reduce to the same
    shape: escalate `min_approvers` (and optionally replace `approver_roles`)
    once some field on the Work crosses a threshold.

    When several conditions match, the one with the HIGHEST `min_approvers`
    wins as a whole unit — this never mixes a numeric threshold from one
    matched condition with a role list from another, a combination nobody
    actually configured. "The most severe matching rule governs" is simpler
    to reason about, and to explain in an audit log, than a field-by-field
    merge across independently-authored conditions.
    """
    if not conditions or work is None:
        return None

    winner = None
    for condition in conditions:
        field = condition.get("field")
        operator = condition.get("operator")
        evaluator = _CONDITION_OPERATORS.get(operator)
        candidate_need = condition.get("min_approvers")
        if not field or evaluator is None or candidate_need is None:
            continue
        actual = _condition_field_value(field, work)
        try:
            matched = evaluator(actual, condition.get("value"))
        except TypeError:
            # A misconfigured condition (e.g. comparing a string with `gte`)
            # must never crash the approval gate — it simply never matches.
            matched = False
        if matched and (winner is None or candidate_need > winner.get("min_approvers", 0)):
            winner = condition
    return winner


# ── Company OS steps 17-18: workflow-approval-node policy gating ──────────────
#
# The `approval` node in workflow_engine.py has, until now, treated moving its
# linked Work row to "completed" as the entire approval record — real and
# working, but not `ApprovalPolicy`-aware (see that module's docstring). This
# section is the opt-in richer path: when the node's config carries a
# `policy_id`, real per-approver `Approval` rows (the same table the deploy
# gate uses, now with `execution_id` set instead of `run_id` — see
# app/models/run.py) are counted against that policy's `min_approvers` /
# `approver_roles` before the execution is allowed to advance. No `policy_id`
# on the node means nothing here runs at all — the existing Work-status
# fallback is completely unaffected, byte-for-byte the same behavior as
# before this section existed.
#
# Explicitly NOT implemented this session (see ADLC_PROJECT_OVERVIEW.md):
# monetary thresholds, risk-level-based rules, department/team/user/agent/
# environment/action-type conditions. Only min_approvers + approver_roles are
# real; everything else in the spec's section-18 wishlist stays future work.

@dataclass
class WorkflowApprovalDecision:
    """
    `allow` / `deny` / `require_approval` — the three-outcome vocabulary
    spec section 18 asks for, distinct from the deploy gate's boolean
    `PolicyDecision.allowed` because a workflow approval node has a third,
    legitimate steady state: waiting on more approvers, which is neither an
    outright allow nor a hard deny.
    """
    outcome: str                    # "allow" | "deny" | "require_approval"
    policy_id: uuid.UUID | None
    policy_name: str
    approvals_required: int
    approvals_have: int
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "outcome": self.outcome,
            "policy_id": str(self.policy_id) if self.policy_id else None,
            "policy_name": self.policy_name,
            "approvals_required": self.approvals_required,
            "approvals_have": self.approvals_have,
            "reasons": self.reasons,
        }


def evaluate_workflow_approval(
    db: Session, *, execution_id, policy_id, approver_role: str | None = None,
) -> WorkflowApprovalDecision:
    """Wraps `_evaluate_workflow_approval` with the step-19 audit row — a
    single exit point so the decision (allow/deny/require_approval) is
    recorded exactly once regardless of which of the inner function's return
    branches fired, tagged with the execution's org/department so it lands
    on the unified timeline next to the workflow's other events."""
    decision = _evaluate_workflow_approval(
        db, execution_id=execution_id, policy_id=policy_id, approver_role=approver_role,
    )
    try:
        from app.models.workflow import Workflow, WorkflowExecution
        execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
        workflow = (
            db.query(Workflow).filter(Workflow.id == execution.workflow_id).first()
            if execution else None
        )
        audit_service.record(
            db, action=f"workflow_approval.{decision.outcome}",
            entity_type="workflow_execution", entity_id=execution_id,
            org_id=workflow.organization_id if workflow else None,
            department_id=workflow.department_id if workflow else None,
            metadata={
                "policy_id": str(policy_id) if policy_id else None,
                "policy_name": decision.policy_name,
                "approver_role": approver_role,
                "approvals_required": decision.approvals_required,
                "approvals_have": decision.approvals_have,
                "reasons": decision.reasons,
            },
        )
    except Exception:
        pass  # audit is best-effort — never let it affect the approval decision itself
    return decision


def _evaluate_workflow_approval(
    db: Session, *, execution_id, policy_id, approver_role: str | None = None,
) -> WorkflowApprovalDecision:
    """
    Real approval-record gating for a workflow `approval` node.

    Counts distinct-reviewer `Approval` rows with `execution_id == execution_id`
    and `decision == 'approved'` against the referenced `ApprovalPolicy`'s
    `min_approvers`. A `decision == 'rejected'` row is an immediate `deny` —
    one rejection ends the vote, it does not just fail to count toward the
    total, matching how a deploy rejection behaves today.

    `approver_role` is the acting approver's own org role, checked against
    `approver_roles` at the moment they vote (not retroactively against
    historical rows) — the same shape `evaluate_deploy`'s
    `approver_roles_present` check uses, adapted to a single-caller call site
    since a workflow approval endpoint approves one person at a time rather
    than evaluating a whole set of existing rows.

    Before either of those checks, `resolve_condition_override` gets a look at
    the execution's linked `Work` row (if any) and may escalate `min_approvers`
    / replace `approver_roles` for this one evaluation — see that function's
    docstring. The policy's own base values are what apply when no condition
    matches, so a policy with an empty `conditions` list behaves exactly as it
    did before this existed.
    """
    policy_row = db.query(ApprovalPolicy).filter(ApprovalPolicy.id == policy_id).first()
    if not policy_row:
        return WorkflowApprovalDecision(
            outcome="deny", policy_id=policy_id, policy_name="(missing)",
            approvals_required=1, approvals_have=0,
            reasons=[f"Referenced policy {policy_id} does not exist or was deleted"],
        )
    policy = _as_dict(policy_row)

    from app.models.workflow import WorkflowExecution
    execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
    work = execution.work if execution else None
    override = resolve_condition_override(policy.get("conditions") or [], work=work)
    need = override.get("min_approvers", policy.get("min_approvers", 1)) if override else policy.get("min_approvers", 1)
    effective_roles = override.get("approver_roles") if override and override.get("approver_roles") else policy.get("approver_roles")

    if approver_role is not None:
        allowed_roles = set(effective_roles or [])
        if allowed_roles and approver_role not in allowed_roles:
            return WorkflowApprovalDecision(
                outcome="deny", policy_id=policy_row.id, policy_name=policy["name"],
                approvals_required=need, approvals_have=0,
                reasons=[f"Role '{approver_role}' is not permitted to approve (needs one of: "
                        f"{', '.join(sorted(allowed_roles))})"],
            )

    rejections = (
        db.query(Approval)
        .filter(Approval.execution_id == execution_id, Approval.decision == "rejected")
        .first()
    )
    if rejections:
        return WorkflowApprovalDecision(
            outcome="deny", policy_id=policy_row.id, policy_name=policy["name"],
            approvals_required=need, approvals_have=0,
            reasons=["An approver rejected this workflow approval step"],
        )

    approvals = (
        db.query(Approval)
        .filter(Approval.execution_id == execution_id, Approval.decision == "approved")
        .all()
    )
    distinct_reviewers = {a.reviewer_id for a in approvals if a.reviewer_id}
    have = len(distinct_reviewers) or len(approvals)

    if have >= need:
        return WorkflowApprovalDecision(
            outcome="allow", policy_id=policy_row.id, policy_name=policy["name"],
            approvals_required=need, approvals_have=have,
        )
    return WorkflowApprovalDecision(
        outcome="require_approval", policy_id=policy_row.id, policy_name=policy["name"],
        approvals_required=need, approvals_have=have,
        reasons=[f"{have}/{need} required approvals"],
    )


def promote_next(db: Session, *, project_id, org_id) -> str | None:
    """
    A slot just freed. Dispatch the oldest waiting run, if the policy allows.

    Called from the run pipeline's terminal paths. Returns the run id it
    started, or None. Best-effort by construction: a failure to promote must
    never turn a run that just *succeeded* into a failure, so the caller wraps
    this and the queue is drained by the next completion instead.
    """
    from app.models.run import Run

    decision = check_concurrency(db, project_id=project_id, org_id=org_id)
    if not decision.admitted:
        return None

    nxt = (
        db.query(Run)
        .filter(Run.project_id == project_id, Run.status.in_(QUEUED_STATUSES))
        .order_by(Run.created_at)
        .first()
    )
    if not nxt:
        return None

    from app.tasks.run_tasks import trigger_run_until_approval
    trigger_run_until_approval.delay(str(nxt.id))
    return str(nxt.id)
