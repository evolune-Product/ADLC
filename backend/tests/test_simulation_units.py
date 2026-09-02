"""
Simulated Persona QA — unit tests for the pure/stub-testable logic.

Zero real DB, zero network, zero browser — same stub-session style as
tests/test_workflow_engine.py. Postgres coverage for the new tables
(personas, simulation_runs, simulation_findings) comes from `alembic upgrade
head` / `downgrade -1 && upgrade head` against the real local instance,
exactly as it does for every other migration in this repo, not from here.

What is deliberately NOT covered here: `simulation_agent._locate`/`_execute`
(need a real Playwright `Page`) and the LLM vision call itself (needs a real
model). Those were verified with a live end-to-end run instead — see the
task's final report. What IS covered: prompt construction, screenshot-path
handling, the LLM vision gate added to llm_service.complete(), and every
branch of the tracker write-back gating in simulation_service.py.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agents import simulation_agent
from app.models.connection import Connection
from app.models.persona import Persona
from app.models.project import Project
from app.models.ticket import Ticket
from app.services import llm_service, simulation_service


# ── Stub SQLAlchemy plumbing (same shape as test_workflow_engine.py) ──────────

class _StubQuery:
    def __init__(self, result=None):
        self._result = result if result is not None else []

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._result[0] if self._result else None

    def all(self):
        return self._result


class _StubSession:
    def __init__(self, by_model=None):
        self._by_model = by_model or {}
        self.committed = 0

    def query(self, model, *_rest):
        return _StubQuery(self._by_model.get(model))

    def commit(self):
        self.committed += 1

    def add(self, _obj):
        pass

    def refresh(self, _obj):
        pass


# ═══ simulation_agent._build_prompt ════════════════════════════════════════════

class TestBuildPrompt:
    def _persona(self):
        return SimpleNamespace(name="Skeptical Shopper", description="Wants to buy sneakers fast, bounces if confused.")

    def _run(self, max_steps=15):
        return SimpleNamespace(max_steps=max_steps)

    def test_first_step_has_no_history_placeholder(self):
        prompt = simulation_agent._build_prompt(self._persona(), self._run(), "https://shop.test", 1, [], "")
        assert "none yet" in prompt
        assert "Skeptical Shopper" in prompt
        assert "Wants to buy sneakers fast" in prompt
        assert "Step 1 of 15" in prompt
        assert "https://shop.test" in prompt

    def test_history_is_capped_to_the_most_recent_entries(self):
        # MAX_HISTORY_IN_PROMPT is 6 — with 9 entries only the last 6 (4..9) survive.
        transcript = [f"marker-{i}" for i in range(1, 10)]
        prompt = simulation_agent._build_prompt(self._persona(), self._run(), "https://shop.test", 10, transcript, "")
        for kept in range(4, 10):
            assert f"marker-{kept}" in prompt
        for dropped in range(1, 4):
            assert f"marker-{dropped}" not in prompt

    def test_last_action_note_is_surfaced_when_present(self):
        prompt = simulation_agent._build_prompt(self._persona(), self._run(), "https://shop.test", 2, [], "could not find Checkout")
        assert "NOTE: could not find Checkout" in prompt

    def test_no_note_block_when_nothing_failed(self):
        prompt = simulation_agent._build_prompt(self._persona(), self._run(), "https://shop.test", 2, [], "")
        assert "NOTE:" not in prompt


# ═══ simulation_agent screenshot storage ═══════════════════════════════════════

class TestScreenshotStorage:
    def test_creates_a_per_run_subdirectory(self, tmp_path, monkeypatch):
        monkeypatch.setattr(simulation_agent.settings, "simulation_screenshot_dir", str(tmp_path))
        run_id = uuid.uuid4()
        directory = simulation_agent._screenshot_dir(run_id)
        assert directory == tmp_path / str(run_id)
        assert directory.is_dir()

    def test_save_screenshot_writes_bytes_and_names_by_step(self, tmp_path, monkeypatch):
        monkeypatch.setattr(simulation_agent.settings, "simulation_screenshot_dir", str(tmp_path))
        run_id = uuid.uuid4()
        saved_path = simulation_agent._save_screenshot(run_id, 3, b"fake-png-bytes")
        saved = Path(saved_path)
        assert saved.exists()
        assert saved.read_bytes() == b"fake-png-bytes"
        assert saved.name == "step_03.png"


# ═══ llm_service vision gate ═══════════════════════════════════════════════════

class TestVisionGate:
    def test_vision_wires_are_exactly_anthropic_and_openai(self):
        assert llm_service._VISION_WIRES == {"anthropic", "openai"}

    def test_image_on_a_non_vision_wire_raises_before_any_network_call(self):
        # "llama-3.3-70b" routes to the ollama wire, which has no vision path
        # wired up — this must raise from the gate itself, not attempt to
        # reach a (possibly absent) local Ollama host.
        with pytest.raises(llm_service.LLMError, match="vision"):
            llm_service.complete(system="x", user="y", model="llama-3.3-70b", image_base64="ZmFrZQ==")


# ═══ simulation_service._comment_body ══════════════════════════════════════════

class TestCommentBody:
    def test_includes_severity_title_description_url_and_steps(self):
        run = SimpleNamespace(target_url="https://shop.test/checkout")
        finding = SimpleNamespace(
            severity="high", title="Checkout button does nothing",
            description="Clicking Pay does not advance the flow.",
            reproduction_steps=["Added item to cart", "Clicked Pay"],
        )
        body = simulation_service._comment_body(run, finding)
        assert "high" in body
        assert "Checkout button does nothing" in body
        assert "Clicking Pay does not advance the flow." in body
        assert "Added item to cart" in body
        assert "https://shop.test/checkout" in body

    def test_caps_steps_shown_to_the_last_eight(self):
        run = SimpleNamespace(target_url="https://x.test")
        finding = SimpleNamespace(
            severity="low", title="t", description="d",
            reproduction_steps=[f"step-{i}" for i in range(1, 12)],  # 11 entries
        )
        body = simulation_service._comment_body(run, finding)
        assert "step-11" in body
        assert "step-4" in body
        assert "step-3" not in body


# ═══ simulation_service._post_to_tracker (the write-back gating) ══════════════

class TestPostToTracker:
    def _run(self, ticket_id=None):
        return SimpleNamespace(ticket_id=ticket_id, target_url="https://x.test",
                               org_id=None, user_id=uuid.uuid4(), id=uuid.uuid4())

    def _finding(self):
        return SimpleNamespace(severity="medium", title="t", description="d", reproduction_steps=[])

    def test_no_ticket_linked_short_circuits(self):
        db = _StubSession()
        assert simulation_service._post_to_tracker(db, self._run(ticket_id=None), self._finding()) is False

    def test_ticket_id_set_but_ticket_row_missing(self):
        db = _StubSession({Ticket: []})
        assert simulation_service._post_to_tracker(db, self._run(ticket_id=uuid.uuid4()), self._finding()) is False

    def test_writeback_not_enabled_on_project(self):
        ticket = SimpleNamespace(id=uuid.uuid4(), project_id=uuid.uuid4(), jira_id="PROJ-1", raw_payload={})
        project = SimpleNamespace(id=ticket.project_id, writeback={}, jira_connection_id=None)
        db = _StubSession({Ticket: [ticket], Project: [project]})
        assert simulation_service._post_to_tracker(db, self._run(ticket_id=ticket.id), self._finding()) is False

    def test_no_connection_configured(self):
        ticket = SimpleNamespace(id=uuid.uuid4(), project_id=uuid.uuid4(), jira_id="PROJ-1", raw_payload={})
        project = SimpleNamespace(id=ticket.project_id, writeback={"enabled": True}, jira_connection_id=None)
        db = _StubSession({Ticket: [ticket], Project: [project]})
        assert simulation_service._post_to_tracker(db, self._run(ticket_id=ticket.id), self._finding()) is False

    def test_connection_not_connected(self):
        ticket = SimpleNamespace(id=uuid.uuid4(), project_id=uuid.uuid4(), jira_id="PROJ-1", raw_payload={})
        project = SimpleNamespace(id=ticket.project_id, writeback={"enabled": True}, jira_connection_id=uuid.uuid4())
        connection = SimpleNamespace(id=project.jira_connection_id, status="error", type="jira")
        db = _StubSession({Ticket: [ticket], Project: [project], Connection: [connection]})
        assert simulation_service._post_to_tracker(db, self._run(ticket_id=ticket.id), self._finding()) is False

    def test_unsupported_provider(self):
        ticket = SimpleNamespace(id=uuid.uuid4(), project_id=uuid.uuid4(), jira_id="PROJ-1", raw_payload={})
        project = SimpleNamespace(id=ticket.project_id, writeback={"enabled": True}, jira_connection_id=uuid.uuid4())
        connection = SimpleNamespace(id=project.jira_connection_id, status="connected", type="github")
        db = _StubSession({Ticket: [ticket], Project: [project], Connection: [connection]})
        assert simulation_service._post_to_tracker(db, self._run(ticket_id=ticket.id), self._finding()) is False

    def test_valid_jira_path_calls_add_comment_and_returns_its_result(self, monkeypatch):
        ticket = SimpleNamespace(id=uuid.uuid4(), project_id=uuid.uuid4(), jira_id="PROJ-1", raw_payload={})
        project = SimpleNamespace(id=ticket.project_id, writeback={"enabled": True}, jira_connection_id=uuid.uuid4())
        connection = SimpleNamespace(
            id=project.jira_connection_id, status="connected", type="jira",
            access_token="encrypted-blob", workspace_url="https://acme.atlassian.net",
            metadata_={"email": "bot@acme.com"},
        )
        db = _StubSession({Ticket: [ticket], Project: [project], Connection: [connection]})

        monkeypatch.setattr(simulation_service, "decrypt_token", lambda _t: "plain-token")
        calls = {}

        def fake_add_comment(workspace_url, email, token, issue_key, body):
            calls.update(workspace_url=workspace_url, email=email, token=token, issue_key=issue_key, body=body)
            return True

        monkeypatch.setattr(simulation_service.jira_service, "add_comment", fake_add_comment)

        result = simulation_service._post_to_tracker(db, self._run(ticket_id=ticket.id), self._finding())
        assert result is True
        assert calls["issue_key"] == "PROJ-1"
        assert calls["workspace_url"] == "https://acme.atlassian.net"
        assert calls["email"] == "bot@acme.com"
        assert calls["token"] == "plain-token"

    def test_linear_path_requires_a_remote_issue_id(self, monkeypatch):
        # raw_payload has no "id" key, so there is nothing to comment on Linear-side.
        ticket = SimpleNamespace(id=uuid.uuid4(), project_id=uuid.uuid4(), jira_id="ENG-9", raw_payload={})
        project = SimpleNamespace(id=ticket.project_id, writeback={"enabled": True}, jira_connection_id=uuid.uuid4())
        connection = SimpleNamespace(
            id=project.jira_connection_id, status="connected", type="linear",
            access_token="encrypted-blob", workspace_url=None, metadata_={},
        )
        db = _StubSession({Ticket: [ticket], Project: [project], Connection: [connection]})
        monkeypatch.setattr(simulation_service, "decrypt_token", lambda _t: "plain-token")
        assert simulation_service._post_to_tracker(db, self._run(ticket_id=ticket.id), self._finding()) is False


# ═══ simulation_service._notify ════════════════════════════════════════════════

class TestNotify:
    def test_notifies_with_severity_scoped_type_and_persona_name(self, monkeypatch):
        persona = SimpleNamespace(id=uuid.uuid4(), name="Skeptical Shopper")
        run = SimpleNamespace(persona_id=persona.id, org_id=None, user_id=uuid.uuid4(),
                              target_url="https://shop.test", id=uuid.uuid4())
        finding = SimpleNamespace(id=uuid.uuid4(), severity="critical",
                                  title="Broken checkout", description="Pay button is dead")
        db = _StubSession({Persona: [persona]})

        captured = {}

        def fake_notify_org(_db, **kwargs):
            captured.update(kwargs)
            return []

        monkeypatch.setattr(simulation_service.notifier, "notify_org", fake_notify_org)

        assert simulation_service._notify(db, run, finding) is True
        assert captured["type"] == "simulation.finding.critical"
        assert "Skeptical Shopper" in captured["body"]
        assert captured["link"] == f"/simulations/{run.id}"

    def test_a_notifier_exception_is_swallowed_and_returns_false(self, monkeypatch):
        persona = SimpleNamespace(id=uuid.uuid4(), name="Skeptical Shopper")
        run = SimpleNamespace(persona_id=persona.id, org_id=None, user_id=uuid.uuid4(),
                              target_url="https://shop.test", id=uuid.uuid4())
        finding = SimpleNamespace(id=uuid.uuid4(), severity="low", title="t", description="d")
        db = _StubSession({Persona: [persona]})

        def boom(_db, **_kwargs):
            raise RuntimeError("Slack is down")

        monkeypatch.setattr(simulation_service.notifier, "notify_org", boom)
        assert simulation_service._notify(db, run, finding) is False


# ═══ notifier severity map extension ═══════════════════════════════════════════

class TestNotifierSeverityMap:
    def test_all_four_finding_severities_are_registered(self):
        from app.services.notifier import SEVERITY_BY_TYPE
        assert SEVERITY_BY_TYPE["simulation.finding.critical"] == "critical"
        assert SEVERITY_BY_TYPE["simulation.finding.high"] == "warning"
        assert SEVERITY_BY_TYPE["simulation.finding.medium"] == "warning"
        assert SEVERITY_BY_TYPE["simulation.finding.low"] == "info"
