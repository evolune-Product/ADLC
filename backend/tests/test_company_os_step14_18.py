"""
Unit tests for Company OS steps 14 (memory hierarchy), 15-16 (chat/workflow
integration), and 17-18 (workflow-approval-node policy gating).

Same zero-real-DB stub style as tests/test_workflow_engine.py and
tests/test_company_os.py: a `_StubSession`/`_StubQuery` pair keyed by model
class, so `db.query(Model).filter(...).all()` returns exactly the rows a test
hands it, with no Postgres round trip. Postgres coverage for the new columns
(memory_chunks.department_id/team_id/organization_id, channels.department_id/
team_id, approvals.execution_id) comes from `alembic upgrade head` and
`downgrade -1 && upgrade head` in CI, exactly as it does for every other
migration in this repo.
"""
from __future__ import annotations

import uuid

import pytest

from app.services import policy_service
from app.services.workspace_bridge import resolve_dept_team_mentions, _MENTION_TOKEN_RE
from app.routers.memory import _scope_label


# ── Stub SQLAlchemy plumbing (mirrors tests/test_workflow_engine.py) ──────────

class _StubQuery:
    def __init__(self, result=None):
        self._result = result if result is not None else []

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._result[0] if self._result else None

    def all(self):
        return self._result


class _StubSession:
    def __init__(self, by_model=None):
        self._by_model = by_model or {}

    def query(self, model, *_rest):
        return _StubQuery(self._by_model.get(model))


class _SequencedStubSession:
    """
    Like `_StubSession`, but for one model it returns a *sequence* of results,
    one per successive `.query(model)` call, rather than the same list every
    time.

    `evaluate_workflow_approval` queries `Approval` twice in a row — once
    filtered to rejections, once filtered to approvals — and the plain
    `_StubQuery.filter()` is a no-op (it does not actually evaluate the
    SQLAlchemy predicate), so a single shared list cannot represent "no
    rejections, N approvals" the way real Postgres would. This gives each
    call its own pre-filtered result instead, which is what the real,
    predicate-evaluating query would have returned.
    """
    def __init__(self, sequenced_model, results: list, by_model=None):
        self._sequenced_model = sequenced_model
        self._results = list(results)
        self._by_model = by_model or {}

    def query(self, model, *_rest):
        if model is self._sequenced_model and self._results:
            return _StubQuery(self._results.pop(0))
        return _StubQuery(self._by_model.get(model))


# ── memory hierarchy: _scope_label (router.py's pure classifier) ──────────────

class _Chunk:
    def __init__(self, *, project_id=None, team_id=None, department_id=None, organization_id=None):
        self.project_id = project_id
        self.team_id = team_id
        self.department_id = department_id
        self.organization_id = organization_id


class TestMemoryScopeLabel:
    def test_project_wins_when_project_id_set(self):
        c = _Chunk(project_id=uuid.uuid4(), team_id=uuid.uuid4(), department_id=uuid.uuid4())
        assert _scope_label(c) == "project"

    def test_team_when_no_project(self):
        c = _Chunk(team_id=uuid.uuid4(), department_id=uuid.uuid4())
        assert _scope_label(c) == "team"

    def test_department_when_no_project_or_team(self):
        c = _Chunk(department_id=uuid.uuid4(), organization_id=uuid.uuid4())
        assert _scope_label(c) == "department"

    def test_company_when_only_org_set(self):
        c = _Chunk(organization_id=uuid.uuid4())
        assert _scope_label(c) == "company"


class TestWriteNoteRequiresAScope:
    def test_raises_without_any_scope(self):
        from app.services.memory_service import write_note
        with pytest.raises(ValueError):
            write_note(db=None, title="x", content="y")  # no org/dept/team/project


# ── @department / @team mention resolution — deterministic, exact match ──────

class _Dept:
    def __init__(self, name, slug, org_id):
        self.id = uuid.uuid4()
        self.name = name
        self.slug = slug
        self.organization_id = org_id
        self.status = "active"


class _Team:
    def __init__(self, name, slug, org_id, department_id=None):
        self.id = uuid.uuid4()
        self.name = name
        self.slug = slug
        self.organization_id = org_id
        self.department_id = department_id
        self.status = "active"


class TestResolveDeptTeamMentions:
    def test_matches_department_slug_case_insensitively(self):
        from app.models.department import Department, Team
        org_id = uuid.uuid4()
        sales = _Dept("Sales", "sales", org_id)
        db = _StubSession({Department: [sales], Team: []})
        hits = resolve_dept_team_mentions(db, "@Sales please follow up with Acme", org_id)
        assert len(hits) == 1
        assert hits[0][0] == "department"
        assert hits[0][1] is sales

    def test_matches_team_name_not_just_slug(self):
        from app.models.department import Department, Team
        org_id = uuid.uuid4()
        core = _Team("Core Infra", "core-infra", org_id)
        db = _StubSession({Department: [], Team: [core]})
        hits = resolve_dept_team_mentions(db, "@core-infra can you take a look", org_id)
        assert len(hits) == 1
        assert hits[0][0] == "team"
        assert hits[0][1] is core

    def test_no_match_returns_empty_not_an_error(self):
        from app.models.department import Department, Team
        org_id = uuid.uuid4()
        db = _StubSession({Department: [_Dept("Finance", "finance", org_id)], Team: []})
        hits = resolve_dept_team_mentions(db, "@nonexistent please help", org_id)
        assert hits == []

    def test_plain_text_with_no_at_token_never_matches(self):
        from app.models.department import Department, Team
        org_id = uuid.uuid4()
        db = _StubSession({Department: [_Dept("Sales", "sales", org_id)], Team: []})
        hits = resolve_dept_team_mentions(db, "just a normal message about sales figures", org_id)
        assert hits == []  # "sales" with no @ is never a mention — deterministic, not NLU

    def test_no_org_id_returns_empty(self):
        from app.models.department import Department, Team
        db = _StubSession({Department: [], Team: []})
        assert resolve_dept_team_mentions(db, "@sales help", None) == []

    def test_mention_token_regex_stops_at_word_boundary(self):
        matches = [m.group(1) for m in _MENTION_TOKEN_RE.finditer("@sales, please see @finance-team too.")]
        assert matches == ["sales", "finance-team"]


# ── workflow-approval-node policy gating (steps 17-18) ─────────────────────────

class _Policy:
    def __init__(self, *, min_approvers=2, approver_roles=None, name="Two-approver gate",
                 conditions=None):
        self.id = uuid.uuid4()
        self.name = name
        self.environment = "*"
        self.min_approvers = min_approvers
        self.approver_roles = approver_roles or ["owner", "admin", "member"]
        self.require_review_pass = False
        self.min_review_score = 0
        self.block_on_severity = None
        self.protected_paths = []
        self.protected_branches = []
        self.max_files_changed = 0
        self.max_run_cost_cents = 0
        self.max_concurrent_runs = 0
        self.max_queue_depth = 0
        self.conditions = conditions or []


class _Approval:
    def __init__(self, *, reviewer_id, decision):
        self.execution_id = uuid.uuid4()
        self.reviewer_id = reviewer_id
        self.decision = decision


class TestEvaluateWorkflowApproval:
    def test_missing_policy_denies_loudly(self):
        from app.models.governance import ApprovalPolicy
        from app.models.run import Approval
        db = _StubSession({ApprovalPolicy: [], Approval: []})
        decision = policy_service.evaluate_workflow_approval(db, execution_id=uuid.uuid4(), policy_id=uuid.uuid4())
        assert decision.outcome == "deny"
        assert "does not exist" in decision.reasons[0]

    def test_role_not_permitted_denies_before_counting_votes(self):
        from app.models.governance import ApprovalPolicy
        from app.models.run import Approval
        policy = _Policy(min_approvers=1, approver_roles=["owner"])
        db = _StubSession({ApprovalPolicy: [policy], Approval: []})
        decision = policy_service.evaluate_workflow_approval(
            db, execution_id=uuid.uuid4(), policy_id=policy.id, approver_role="member",
        )
        assert decision.outcome == "deny"
        assert "not permitted" in decision.reasons[0]

    def test_one_rejection_denies_regardless_of_approvals(self):
        from app.models.governance import ApprovalPolicy
        from app.models.run import Approval
        policy = _Policy(min_approvers=1)
        rejection = _Approval(reviewer_id=uuid.uuid4(), decision="rejected")
        # Sequenced: first Approval query (rejections) sees the rejection;
        # the second (approvals) would never even need to run.
        db = _SequencedStubSession(Approval, [[rejection], []], by_model={ApprovalPolicy: [policy]})
        decision = policy_service.evaluate_workflow_approval(db, execution_id=uuid.uuid4(), policy_id=policy.id)
        assert decision.outcome == "deny"

    def test_below_min_approvers_requires_more_approval(self):
        from app.models.governance import ApprovalPolicy
        from app.models.run import Approval
        policy = _Policy(min_approvers=2)
        one_vote = _Approval(reviewer_id=uuid.uuid4(), decision="approved")
        # First Approval query (rejections) sees none; second (approvals) sees one.
        db = _SequencedStubSession(Approval, [[], [one_vote]], by_model={ApprovalPolicy: [policy]})
        decision = policy_service.evaluate_workflow_approval(db, execution_id=uuid.uuid4(), policy_id=policy.id)
        assert decision.outcome == "require_approval"
        assert decision.approvals_have == 1
        assert decision.approvals_required == 2

    def test_meeting_min_approvers_allows(self):
        from app.models.governance import ApprovalPolicy
        from app.models.run import Approval
        policy = _Policy(min_approvers=2)
        votes = [_Approval(reviewer_id=uuid.uuid4(), decision="approved") for _ in range(2)]
        db = _SequencedStubSession(Approval, [[], votes], by_model={ApprovalPolicy: [policy]})
        decision = policy_service.evaluate_workflow_approval(db, execution_id=uuid.uuid4(), policy_id=policy.id)
        assert decision.outcome == "allow"
        assert decision.approvals_have == 2

    def test_duplicate_reviewer_only_counts_once(self):
        from app.models.governance import ApprovalPolicy
        from app.models.run import Approval
        policy = _Policy(min_approvers=2)
        same_reviewer = uuid.uuid4()
        votes = [_Approval(reviewer_id=same_reviewer, decision="approved") for _ in range(3)]
        db = _SequencedStubSession(Approval, [[], votes], by_model={ApprovalPolicy: [policy]})
        decision = policy_service.evaluate_workflow_approval(db, execution_id=uuid.uuid4(), policy_id=policy.id)
        assert decision.outcome == "require_approval"
        assert decision.approvals_have == 1

    def test_outcome_is_always_one_of_the_three_spec_values(self):
        from app.models.governance import ApprovalPolicy
        from app.models.run import Approval
        policy = _Policy(min_approvers=1)
        for rejection_rows, approval_rows in ([[], []], [[], [_Approval(reviewer_id=uuid.uuid4(), decision="approved")]]):
            db = _SequencedStubSession(Approval, [rejection_rows, approval_rows], by_model={ApprovalPolicy: [policy]})
            decision = policy_service.evaluate_workflow_approval(db, execution_id=uuid.uuid4(), policy_id=policy.id)
            assert decision.outcome in ("allow", "deny", "require_approval")


# ── conditional escalation: monetary thresholds, risk-level rules ─────────────

class _Work:
    def __init__(self, *, amount_cents=None, risk_level=None, department_id=None,
                 team_id=None, work_type=None):
        context = {}
        if amount_cents is not None:
            context["amount_cents"] = amount_cents
        if risk_level is not None:
            context["risk_level"] = risk_level
        self.context = context
        self.department_id = department_id
        self.team_id = team_id
        self.type = work_type


class _Execution:
    def __init__(self, work=None):
        self.id = uuid.uuid4()
        self.work = work


class TestResolveConditionOverride:
    """Pure-function tests — no DB, no stub session, matching how the rest of
    this file tests `_scope_label` and `resolve_dept_team_mentions` directly."""

    def test_no_conditions_is_no_override(self):
        assert policy_service.resolve_condition_override([], work=_Work(amount_cents=999_999)) is None

    def test_no_work_is_no_override_even_with_conditions(self):
        conditions = [{"field": "amount_cents", "operator": "gte", "value": 100, "min_approvers": 3}]
        assert policy_service.resolve_condition_override(conditions, work=None) is None

    def test_amount_over_threshold_matches(self):
        conditions = [{"field": "amount_cents", "operator": "gte", "value": 1_000_000, "min_approvers": 3}]
        work = _Work(amount_cents=1_500_000)
        assert policy_service.resolve_condition_override(conditions, work=work) == conditions[0]

    def test_amount_under_threshold_does_not_match(self):
        conditions = [{"field": "amount_cents", "operator": "gte", "value": 1_000_000, "min_approvers": 3}]
        work = _Work(amount_cents=500_000)
        assert policy_service.resolve_condition_override(conditions, work=work) is None

    def test_missing_amount_on_work_does_not_match_a_numeric_condition(self):
        conditions = [{"field": "amount_cents", "operator": "gte", "value": 1, "min_approvers": 3}]
        assert policy_service.resolve_condition_override(conditions, work=_Work()) is None

    def test_risk_level_eq_matches(self):
        conditions = [{"field": "risk_level", "operator": "eq", "value": "critical", "min_approvers": 4}]
        work = _Work(risk_level="critical")
        assert policy_service.resolve_condition_override(conditions, work=work) == conditions[0]

    def test_work_type_in_list_matches(self):
        conditions = [{"field": "work_type", "operator": "in", "value": ["expense", "purchase"],
                       "min_approvers": 2}]
        assert policy_service.resolve_condition_override(conditions, work=_Work(work_type="expense")) == conditions[0]

    def test_department_id_matches_as_a_string(self):
        dept_id = uuid.uuid4()
        conditions = [{"field": "department_id", "operator": "eq", "value": str(dept_id), "min_approvers": 2}]
        work = _Work(department_id=dept_id)
        assert policy_service.resolve_condition_override(conditions, work=work) == conditions[0]

    def test_most_restrictive_of_several_matching_conditions_wins(self):
        conditions = [
            {"field": "amount_cents", "operator": "gte", "value": 100_000, "min_approvers": 2},
            {"field": "amount_cents", "operator": "gte", "value": 1_000_000, "min_approvers": 5},
            {"field": "amount_cents", "operator": "gte", "value": 500_000, "min_approvers": 3},
        ]
        work = _Work(amount_cents=2_000_000)  # matches all three
        winner = policy_service.resolve_condition_override(conditions, work=work)
        assert winner["min_approvers"] == 5

    def test_non_matching_and_matching_conditions_mixed(self):
        conditions = [
            {"field": "risk_level", "operator": "eq", "value": "low", "min_approvers": 1},
            {"field": "risk_level", "operator": "eq", "value": "high", "min_approvers": 4},
        ]
        work = _Work(risk_level="high")
        winner = policy_service.resolve_condition_override(conditions, work=work)
        assert winner["min_approvers"] == 4

    def test_malformed_condition_is_skipped_not_a_crash(self):
        conditions = [
            {"field": "amount_cents", "operator": "gte", "value": "not-a-number", "min_approvers": 5},
            {"field": "amount_cents", "operator": "no-such-operator", "value": 1, "min_approvers": 5},
            {"operator": "gte", "value": 1, "min_approvers": 5},          # no field
            {"field": "amount_cents", "operator": "gte", "value": 1},    # no min_approvers
        ]
        work = _Work(amount_cents=1_000_000)
        assert policy_service.resolve_condition_override(conditions, work=work) is None


class TestConditionsWiredIntoWorkflowApproval:
    """The end-to-end path: a condition on the policy actually changes how
    many approvals `evaluate_workflow_approval` requires for THIS execution,
    without touching the policy's own base `min_approvers`."""

    def test_high_value_work_escalates_required_approvals(self):
        from app.models.governance import ApprovalPolicy
        from app.models.run import Approval
        from app.models.workflow import WorkflowExecution

        conditions = [{"field": "amount_cents", "operator": "gte", "value": 1_000_000, "min_approvers": 3}]
        policy = _Policy(min_approvers=1, conditions=conditions)
        execution = _Execution(work=_Work(amount_cents=2_000_000))
        one_vote = _Approval(reviewer_id=uuid.uuid4(), decision="approved")

        db = _SequencedStubSession(
            Approval, [[], [one_vote]],
            by_model={ApprovalPolicy: [policy], WorkflowExecution: [execution]},
        )
        decision = policy_service.evaluate_workflow_approval(
            db, execution_id=execution.id, policy_id=policy.id,
        )
        # One vote is not enough — the condition raised the bar from 1 to 3.
        assert decision.outcome == "require_approval"
        assert decision.approvals_required == 3

    def test_low_value_work_keeps_the_base_policy(self):
        from app.models.governance import ApprovalPolicy
        from app.models.run import Approval
        from app.models.workflow import WorkflowExecution

        conditions = [{"field": "amount_cents", "operator": "gte", "value": 1_000_000, "min_approvers": 3}]
        policy = _Policy(min_approvers=1, conditions=conditions)
        execution = _Execution(work=_Work(amount_cents=100))
        one_vote = _Approval(reviewer_id=uuid.uuid4(), decision="approved")

        db = _SequencedStubSession(
            Approval, [[], [one_vote]],
            by_model={ApprovalPolicy: [policy], WorkflowExecution: [execution]},
        )
        decision = policy_service.evaluate_workflow_approval(
            db, execution_id=execution.id, policy_id=policy.id,
        )
        assert decision.outcome == "allow"
        assert decision.approvals_required == 1

    def test_no_linked_work_item_never_escalates(self):
        from app.models.governance import ApprovalPolicy
        from app.models.run import Approval
        from app.models.workflow import WorkflowExecution

        conditions = [{"field": "amount_cents", "operator": "gte", "value": 1, "min_approvers": 9}]
        policy = _Policy(min_approvers=1, conditions=conditions)
        execution = _Execution(work=None)  # e.g. a manually-triggered workflow
        one_vote = _Approval(reviewer_id=uuid.uuid4(), decision="approved")

        db = _SequencedStubSession(
            Approval, [[], [one_vote]],
            by_model={ApprovalPolicy: [policy], WorkflowExecution: [execution]},
        )
        decision = policy_service.evaluate_workflow_approval(
            db, execution_id=execution.id, policy_id=policy.id,
        )
        assert decision.outcome == "allow"
        assert decision.approvals_required == 1

    def test_condition_can_narrow_which_roles_may_approve(self):
        from app.models.governance import ApprovalPolicy
        from app.models.run import Approval
        from app.models.workflow import WorkflowExecution

        conditions = [{"field": "amount_cents", "operator": "gte", "value": 1_000_000,
                       "min_approvers": 2, "approver_roles": ["owner"]}]
        policy = _Policy(min_approvers=1, approver_roles=["owner", "admin", "member"],
                          conditions=conditions)
        execution = _Execution(work=_Work(amount_cents=5_000_000))

        db = _StubSession({ApprovalPolicy: [policy], WorkflowExecution: [execution]})
        decision = policy_service.evaluate_workflow_approval(
            db, execution_id=execution.id, policy_id=policy.id, approver_role="member",
        )
        # "member" is allowed by the base policy but not by the escalated,
        # condition-narrowed role list — the condition must win.
        assert decision.outcome == "deny"
        assert "not permitted" in decision.reasons[0]
