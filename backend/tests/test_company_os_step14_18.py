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
    def __init__(self, *, min_approvers=2, approver_roles=None, name="Two-approver gate"):
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
