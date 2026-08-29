"""
Workflow engine and routing-service unit tests — zero real DB, same stub
style as tests/test_company_os.py and tests/test_platform_units.py. Postgres
coverage for the new tables comes from `alembic upgrade head` /
`downgrade -1 && upgrade head` in CI, exactly as it does for every other
migration in this repo.
"""
from __future__ import annotations

import uuid

import pytest

from app.services.routing_service import RoutingDecision, route_work
from app.services.workflow_engine import _get_path, _render_template, _resolve_next


# ── Stub SQLAlchemy plumbing ─────────────────────────────────────────────────

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


class _Dept:
    def __init__(self, name, org_id):
        self.id = uuid.uuid4()
        self.name = name
        self.organization_id = org_id
        self.status = "active"


class _Work:
    def __init__(self, title="", description="", department_id=None):
        self.title = title
        self.description = description
        self.department_id = department_id
        self.organization_id = uuid.uuid4()


# ── routing_service ──────────────────────────────────────────────────────────

class TestRouteWork:
    def test_explicit_department_wins(self):
        db = _StubSession()
        dept_id = uuid.uuid4()
        work = _Work(title="anything", department_id=dept_id)
        decision = route_work(db, work)
        assert decision.confidence == "explicit"
        assert decision.department_id == dept_id

    def test_matches_department_by_name_in_title(self):
        from app.models.department import Department
        work = _Work(title="Need help from Marketing with the launch copy")
        marketing = _Dept("Marketing", work.organization_id)
        sales = _Dept("Sales", work.organization_id)
        db = _StubSession({Department: [sales, marketing]})
        decision = route_work(db, work)
        assert decision.confidence == "matched"
        assert decision.department_id == marketing.id

    def test_matches_case_insensitively_in_description(self):
        from app.models.department import Department
        work = _Work(title="Quarterly numbers", description="please loop in FINANCE for review")
        finance = _Dept("Finance", work.organization_id)
        db = _StubSession({Department: [finance]})
        decision = route_work(db, work)
        assert decision.confidence == "matched"
        assert decision.department_id == finance.id

    def test_unmatched_leaves_department_none_with_a_reason(self):
        from app.models.department import Department
        work = _Work(title="Something nobody has a department for")
        support = _Dept("Support", work.organization_id)
        db = _StubSession({Department: [support]})
        decision = route_work(db, work)
        assert decision.confidence == "unmatched"
        assert decision.department_id is None
        assert decision.reasoning  # never silent

    def test_blank_text_is_unmatched_not_an_error(self):
        db = _StubSession()
        work = _Work(title="", description=None)
        decision = route_work(db, work)
        assert decision.confidence == "unmatched"
        assert decision.department_id is None

    def test_decision_never_mutates_the_work_row(self):
        from app.models.department import Department
        work = _Work(title="Talk to Sales about renewal")
        sales = _Dept("Sales", work.organization_id)
        db = _StubSession({Department: [sales]})
        route_work(db, work)
        assert work.department_id is None  # caller applies the decision, not route_work


# ── workflow_engine pure helpers ─────────────────────────────────────────────

class TestGetPath:
    def test_walks_nested_dict(self):
        assert _get_path({"a": {"b": {"c": 42}}}, "a.b.c") == 42

    def test_missing_key_returns_none(self):
        assert _get_path({"a": {}}, "a.b.c") is None

    def test_none_path_returns_none(self):
        assert _get_path({"a": 1}, None) is None

    def test_non_dict_intermediate_returns_none(self):
        assert _get_path({"a": 1}, "a.b") is None


class TestResolveNext:
    def test_string_next(self):
        assert _resolve_next({"next": "n2"}, {}) == "n2"

    def test_list_next_takes_first(self):
        assert _resolve_next({"next": ["n2", "n3"]}, {}) == "n2"

    def test_empty_list_next_is_none(self):
        assert _resolve_next({"next": []}, {}) is None

    def test_no_next_key_is_none(self):
        assert _resolve_next({}, {}) is None

    def test_branch_matches_field_value(self):
        node = {"next": {"field": "risk", "branches": {"low": "n_ok", "high": "n_review"}}}
        assert _resolve_next(node, {"risk": "high"}) == "n_review"
        assert _resolve_next(node, {"risk": "low"}) == "n_ok"

    def test_branch_falls_back_to_default(self):
        node = {"next": {"field": "risk", "branches": {"low": "n_ok"}, "default": "n_fallback"}}
        assert _resolve_next(node, {"risk": "unknown"}) == "n_fallback"

    def test_branch_with_no_default_and_no_match_is_none(self):
        node = {"next": {"field": "risk", "branches": {"low": "n_ok"}}}
        assert _resolve_next(node, {"risk": "unknown"}) is None


class TestRenderTemplate:
    def test_substitutes_top_level_key(self):
        assert _render_template("Hello {{name}}", {"name": "Ada"}) == "Hello Ada"

    def test_substitutes_nested_path(self):
        assert _render_template("{{a.b}}", {"a": {"b": "x"}}) == "x"

    def test_missing_key_becomes_empty_string(self):
        assert _render_template("[{{missing}}]", {}) == "[]"

    def test_no_placeholders_is_unchanged(self):
        assert _render_template("plain text", {"x": 1}) == "plain text"

    def test_never_evaluates_arbitrary_code(self):
        # The placeholder pattern only matches \w and '.' — anything shaped
        # like code (quotes, parens) simply doesn't match the regex and is
        # returned completely unchanged rather than being evaluated as
        # Python (there is no eval() anywhere in this function).
        payload = "{{__import__('os').system('x')}}"
        assert _render_template(payload, {}) == payload
