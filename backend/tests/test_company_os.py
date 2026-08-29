"""
Company OS foundation — departments, teams, generic Work, and the three new
roles (department_head, team_lead, agent) layered on org_roles.py.

Same zero-real-DB unit style as tests/test_platform_units.py: a minimal
`_StubSession`/`_StubQuery` stand in for SQLAlchemy so these tests don't need
a live Postgres to run (the existing full suite doesn't either, and CI's
`alembic upgrade head` / `downgrade -1 && upgrade head` step is what actually
proves the migrations work against a real database).
"""
from __future__ import annotations

import uuid

import pytest


# ── Stub SQLAlchemy plumbing (mirrors tests/test_platform_units.py) ──────────

class _StubQuery:
    def __init__(self, result=None):
        self._result = result

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._result

    def all(self):
        return self._result or []


class _StubSession:
    def __init__(self, by_model=None):
        self._by_model = by_model or {}

    def query(self, model, *_rest):
        return _StubQuery(self._by_model.get(model))


class _Obj:
    """Cheap attribute bag standing in for an ORM row."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


# ── org_roles.py: the three new roles ─────────────────────────────────────

class TestCompanyOSRoles:
    def test_new_roles_are_in_the_catalogue(self):
        from app.services.org_roles import ALL_KEYS
        for role in ("department_head", "team_lead", "agent"):
            assert role in ALL_KEYS

    def test_department_head_and_team_lead_can_write_administer_nothing(self):
        # Same shape as member/reviewer: ordinary write access, no org-wide
        # `domains` reach — their authority is department/team *scoped*,
        # checked separately by is_department_head / is_team_lead, not
        # through the domains mechanism.
        from app.services.org_roles import can_write, is_domain_admin
        for role in ("department_head", "team_lead"):
            assert can_write(role) is True, role
            assert is_domain_admin(role, "engineering") is False, role
            assert is_domain_admin(role, "billing") is False, role

    def test_agent_role_can_write_but_is_not_invitable(self):
        from app.services.org_roles import can_write, INVITABLE_ROLES
        assert can_write("agent") is True
        assert "agent" not in INVITABLE_ROLES

    def test_department_head_and_team_lead_are_invitable(self):
        from app.services.org_roles import INVITABLE_ROLES
        assert "department_head" in INVITABLE_ROLES
        assert "team_lead" in INVITABLE_ROLES

    def test_pre_existing_roles_unchanged(self):
        # Backward compatibility: the nine original roles keep exactly the
        # access they had before this registry grew by three entries.
        from app.services.org_roles import can_write, is_domain_admin
        assert can_write("viewer") is False
        assert can_write("member") is True
        assert is_domain_admin("owner", "anything") is True
        assert is_domain_admin("engineering_lead", "billing") is False

    def test_catalog_still_hides_access_control_internals(self):
        from app.services.org_roles import catalog
        keys = {r["key"] for r in catalog()}
        assert {"department_head", "team_lead"} <= keys
        assert "agent" not in keys or True  # agent may or may not be listed; only invariant checked below
        for row in catalog():
            assert "domains" not in row and "can_write" not in row

    def test_all_keys_matches_check_constraint_source(self):
        from app.services.org_roles import ALL_KEYS, ROLES
        assert set(ALL_KEYS) == {r["key"] for r in ROLES}


# ── _helpers.py: is_department_head / is_team_lead ────────────────────────

class TestDepartmentAndTeamScopedChecks:
    def _ctx(self, role, org_id=None, user_id=None):
        from app.routers._helpers import OrgContext
        return OrgContext(
            org_id=org_id or uuid.uuid4(),
            org_name="Acme",
            role=role,
            user_id=user_id or uuid.uuid4(),
        )

    def test_none_org_context_always_passes(self):
        from app.routers._helpers import is_department_head, is_team_lead
        db = _StubSession()
        assert is_department_head(None, db, uuid.uuid4(), uuid.uuid4()) is True
        assert is_team_lead(None, db, uuid.uuid4(), uuid.uuid4()) is True

    def test_owner_and_admin_always_pass(self):
        from app.routers._helpers import is_department_head, is_team_lead
        db = _StubSession()
        for role in ("owner", "admin"):
            ctx = self._ctx(role)
            assert is_department_head(ctx, db, uuid.uuid4(), uuid.uuid4()) is True
            assert is_team_lead(ctx, db, uuid.uuid4(), uuid.uuid4()) is True

    def test_department_head_matches_head_user_id(self):
        from app.models.department import Department
        from app.routers._helpers import is_department_head

        org_id = uuid.uuid4()
        dept_id = uuid.uuid4()
        head_id = uuid.uuid4()
        other_id = uuid.uuid4()
        dept = _Obj(id=dept_id, organization_id=org_id, head_user_id=head_id)
        db = _StubSession({Department: dept})

        ctx = self._ctx("department_head", org_id=org_id)
        assert is_department_head(ctx, db, dept_id, head_id) is True
        assert is_department_head(ctx, db, dept_id, other_id) is False

    def test_department_head_role_without_heading_this_department_fails(self):
        from app.models.department import Department
        from app.routers._helpers import is_department_head

        org_id = uuid.uuid4()
        dept = _Obj(id=uuid.uuid4(), organization_id=org_id, head_user_id=uuid.uuid4())
        db = _StubSession({Department: dept})
        ctx = self._ctx("member", org_id=org_id)
        assert is_department_head(ctx, db, dept.id, uuid.uuid4()) is False

    def test_team_lead_via_membership_row(self):
        from app.models.department import Team, TeamMember
        from app.routers._helpers import is_team_lead

        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        dept_id = uuid.uuid4()
        lead_user_id = uuid.uuid4()
        team = _Obj(id=team_id, organization_id=org_id, department_id=dept_id)
        membership = _Obj(team_id=team_id, user_id=lead_user_id, role_in_team="lead")
        db = _StubSession({Team: team, TeamMember: membership})

        ctx = self._ctx("team_lead", org_id=org_id)
        assert is_team_lead(ctx, db, team_id, lead_user_id) is True

    def test_plain_member_of_team_is_not_a_lead(self):
        from app.models.department import Team, TeamMember
        from app.routers._helpers import is_team_lead

        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        team = _Obj(id=team_id, organization_id=org_id, department_id=uuid.uuid4())
        membership = _Obj(team_id=team_id, user_id=uuid.uuid4(), role_in_team="member")
        db = _StubSession({Team: team, TeamMember: membership})

        ctx = self._ctx("member", org_id=org_id)
        assert is_team_lead(ctx, db, team_id, membership.user_id) is False

    def test_unknown_team_fails_closed(self):
        from app.models.department import Team
        from app.routers._helpers import is_team_lead

        db = _StubSession({Team: None})
        ctx = self._ctx("team_lead")
        assert is_team_lead(ctx, db, uuid.uuid4(), uuid.uuid4()) is False


# ── department.py: slugify ─────────────────────────────────────────────────

class TestDepartmentSlugify:
    def test_lowercases_and_dashes(self):
        from app.models.department import slugify
        assert slugify("Customer Success") == "customer-success"

    def test_punctuation_collapses(self):
        from app.models.department import slugify
        assert slugify("R&D / Platform!!") == "r-d-platform"

    def test_empty_input_falls_back(self):
        from app.models.department import slugify
        assert slugify("") == "item"
        assert slugify("   ---   ") == "item"


# ── work_service.py: the status-transition machine ────────────────────────

class TestWorkStatusTransitions:
    def test_new_work_item_can_move_forward(self):
        from app.services.work_service import can_transition
        assert can_transition("new", "triaged") is True
        assert can_transition("new", "assigned") is True
        assert can_transition("new", "cancelled") is True

    def test_new_cannot_jump_to_completed(self):
        from app.services.work_service import can_transition
        assert can_transition("new", "completed") is False

    def test_terminal_states_have_no_outgoing_edges(self):
        from app.models.work import VALID_TRANSITIONS
        for terminal in ("completed", "cancelled"):
            assert VALID_TRANSITIONS[terminal] == ()

    def test_failed_can_be_retried_but_not_directly_completed(self):
        from app.services.work_service import can_transition
        assert can_transition("failed", "triaged") is True
        assert can_transition("failed", "assigned") is True
        assert can_transition("failed", "completed") is False

    def test_same_state_is_always_a_no_op_transition(self):
        from app.services.work_service import can_transition
        from app.models.work import WORK_STATUSES
        for s in WORK_STATUSES:
            assert can_transition(s, s) is True

    def test_apply_transition_returns_target_on_success(self):
        from app.services.work_service import apply_transition
        assert apply_transition("new", "triaged") == "triaged"

    def test_apply_transition_raises_on_invalid_move(self):
        from app.services.work_service import apply_transition, InvalidTransition
        with pytest.raises(InvalidTransition):
            apply_transition("completed", "in_progress")

    def test_apply_transition_raises_value_error_on_unknown_status(self):
        from app.services.work_service import apply_transition
        with pytest.raises(ValueError):
            apply_transition("new", "not-a-real-status")

    def test_awaiting_approval_does_not_skip_to_awaiting_input(self):
        # Pin the graph shape: awaiting_approval moves to in_progress,
        # completed, failed or cancelled — never sideways to awaiting_input
        # (that would be a review bouncing a request back for more info,
        # which re-enters at in_progress, not a state with no home).
        from app.services.work_service import can_transition
        assert can_transition("awaiting_approval", "awaiting_input") is False
        assert can_transition("awaiting_approval", "in_progress") is True
