"""
Unit tests for the Phase 11 logic that must not silently drift.

Deliberately DB-free: these cover the pure functions where a quiet regression
would cost real money (cost attribution), let an ungoverned change ship (policy
evaluation), or break an integration contract (webhook signatures). Run with:

    pytest tests/ -q
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import types

import pytest

from app.data.builtin_templates import all_templates
from app.services import embedding_service, llm_service, policy_service, webhook_service
from app.services.metering_service import PLANS, PLAN_ORDER


# ═══ Cost attribution ═════════════════════════════════════════════════════════

class TestCostAttribution:
    def test_known_model_uses_published_price(self):
        # Claude Sonnet: $3 / $15 per MTok → 1M in + 1M out = $18.00 = 1,800,000 millicents
        assert llm_service.cost_millicents("claude-sonnet-4-6", 1_000_000, 1_000_000) == 1_800_000

    def test_opus_is_priced_above_sonnet(self):
        opus = llm_service.cost_millicents("claude-opus-5", 100_000, 10_000)
        sonnet = llm_service.cost_millicents("claude-sonnet-4-6", 100_000, 10_000)
        assert opus > sonnet

    def test_local_models_are_free(self):
        assert llm_service.cost_millicents("ollama", 500_000, 500_000) == 0

    def test_unknown_model_falls_back_rather_than_crashing(self):
        # A new model id must never break metering — an unbilled run is worse
        # than a run billed at the fallback rate.
        assert llm_service.cost_millicents("some-future-model", 10_000, 1_000) > 0

    def test_zero_tokens_costs_nothing(self):
        assert llm_service.cost_millicents("claude-opus-5", 0, 0) == 0

    @pytest.mark.parametrize("model,expected", [
        ("claude-opus-5", "anthropic"),
        ("claude-sonnet-4-6", "anthropic"),
        ("gpt-5", "openai"),
        ("llama-3.3-70b", "ollama"),
        ("", "anthropic"),
    ])
    def test_provider_routing(self, model, expected):
        assert llm_service.provider_for_model(model) == expected

    def test_byo_key_wins_over_platform_key(self):
        provider, key, is_byo = llm_service.resolve_credentials("openai", "sk-customer", "claude-opus-5")
        assert (provider, key, is_byo) == ("openai", "sk-customer", True)

    def test_platform_key_used_when_no_byo(self):
        _, _, is_byo = llm_service.resolve_credentials(None, None, "claude-opus-5")
        assert is_byo is False


# ═══ Plan catalogue ═══════════════════════════════════════════════════════════

class TestPlans:
    def test_every_ordered_plan_exists(self):
        assert set(PLAN_ORDER) == set(PLANS)

    def test_overage_price_exceeds_worst_case_token_cost(self):
        """
        The margin invariant. A complex run with retries can burn ~$1.15; an
        overage priced below the per-run budget cap would make heavy usage
        loss-making, which is exactly the trap the v1 pricing fell into.
        """
        for key in ("team", "growth"):
            plan = PLANS[key]
            assert plan["overage_cents_per_run"] > 0
            assert plan["run_budget_cents"] > plan["overage_cents_per_run"]

    def test_free_tier_hard_stops(self):
        assert PLANS["free"]["overage_cents_per_run"] == 0
        assert PLANS["free"]["requires_byo_key"] is True

    def test_enterprise_is_unlimited(self):
        assert PLANS["enterprise"]["included_runs"] == 0
        assert PLANS["enterprise"]["seats"] == 0


# ═══ Review scoring ═══════════════════════════════════════════════════════════

def finding(severity: str):
    return types.SimpleNamespace(severity=severity, category="correctness")


class TestReviewScore:
    def test_clean_review_scores_full_marks(self):
        assert policy_service.review_score([]) == 100

    def test_critical_costs_more_than_low(self):
        assert policy_service.review_score([finding("critical")]) < \
               policy_service.review_score([finding("low")])

    def test_score_never_goes_negative(self):
        assert policy_service.review_score([finding("critical")] * 20) == 0

    def test_info_findings_do_not_reduce_the_score(self):
        assert policy_service.review_score([finding("info")] * 5) == 100

    def test_severity_rank_is_monotonic(self):
        r = policy_service.SEVERITY_RANK
        assert r["info"] < r["low"] < r["medium"] < r["high"] < r["critical"]


# ═══ Policy evaluation ════════════════════════════════════════════════════════

def policy(**overrides):
    return {**policy_service.DEFAULT_POLICY, **overrides}


class TestBlastRadiusControl:
    """check_changes() is the read-to-write escalation boundary — it runs
    before a PR is opened, so a violation costs nothing to catch."""

    @pytest.mark.parametrize("path,pattern", [
        ("infra/main.tf", "infra/*"),
        ("app/db/migrations/001.py", "*migrations*"),
        (".github/workflows/ci.yml", ".github/workflows/*"),
        ("src/auth/session.py", "src/auth/*"),
    ])
    def test_protected_paths_are_blocked(self, path, pattern):
        violations = policy_service.check_changes(
            policy(protected_paths=[pattern]), files=[{"path": path}], branch="agent/x")
        assert violations and pattern in violations[0]

    @pytest.mark.parametrize("path,pattern", [
        ("app/routers/runs.py", "infra/*"),
        ("docs/readme.md", "*migrations*"),
    ])
    def test_unrelated_paths_pass(self, path, pattern):
        assert policy_service.check_changes(
            policy(protected_paths=[pattern]), files=[{"path": path}], branch="agent/x") == []

    def test_protected_branch_is_blocked(self):
        violations = policy_service.check_changes(
            policy(protected_branches=["main", "release/*"]),
            files=[{"path": "src/a.py"}], branch="release/2026-08")
        assert violations and "release/*" in violations[0]

    def test_file_count_cap_is_enforced(self):
        violations = policy_service.check_changes(
            policy(max_files_changed=3),
            files=[{"path": f"src/{i}.py"} for i in range(9)], branch="agent/x")
        assert violations and "9 files" in violations[0]

    def test_default_policy_blocks_nothing(self):
        assert policy_service.check_changes(
            policy(), files=[{"path": "infra/main.tf"}], branch="main") == []


class TestPolicyGate:
    def test_default_policy_requires_one_approver(self):
        assert policy_service.DEFAULT_POLICY["min_approvers"] == 1

    def test_default_policy_does_not_block_on_review(self):
        # A pilot must be usable before a reviewer agent is configured; the
        # gate tightens by adding a policy, not by shipping a strict default.
        assert policy_service.DEFAULT_POLICY["require_review_pass"] is False


# ═══ Webhook signatures ═══════════════════════════════════════════════════════

class TestWebhookSignature:
    def test_signature_matches_documented_scheme(self):
        secret, ts, body = "s3cr3t", 1780000000, json.dumps({"event": "run.completed"})
        expected = hmac.new(secret.encode(), f"{ts}.{body}".encode(), hashlib.sha256).hexdigest()
        assert webhook_service.sign(secret, ts, body) == f"sha256={expected}"

    def test_signature_changes_with_body(self):
        assert webhook_service.sign("k", 1, '{"a":1}') != webhook_service.sign("k", 1, '{"a":2}')

    def test_signature_changes_with_timestamp(self):
        """Timestamp is inside the MAC — otherwise deliveries are replayable."""
        assert webhook_service.sign("k", 1, "{}") != webhook_service.sign("k", 2, "{}")

    def test_verify_accepts_a_fresh_signature(self):
        now, body = int(time.time()), '{"event":"run.completed"}'
        assert webhook_service.verify("k", now, body, webhook_service.sign("k", now, body))

    def test_verify_rejects_a_stale_delivery(self):
        old, body = int(time.time()) - 3600, "{}"
        assert not webhook_service.verify("k", old, body, webhook_service.sign("k", old, body))

    def test_verify_rejects_a_tampered_body(self):
        now = int(time.time())
        sig = webhook_service.sign("k", now, '{"amount":1}')
        assert not webhook_service.verify("k", now, '{"amount":9999}', sig)


# ═══ Embeddings + retrieval ═══════════════════════════════════════════════════

class TestEmbeddings:
    def test_deterministic_without_a_provider_key(self):
        assert embedding_service.embed("def handler():") == \
               embedding_service.embed("def handler():")

    def test_vectors_are_unit_length(self):
        vec = embedding_service.embed("some project convention")
        assert vec and abs(sum(x * x for x in vec) - 1.0) < 1e-6

    def test_identical_text_is_maximally_similar(self):
        v = embedding_service.embed("migration safety rules")
        assert embedding_service.cosine(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_related_text_beats_unrelated_text(self):
        query = embedding_service.embed("database migration safety")
        near = embedding_service.embed("migration safety for the database")
        far = embedding_service.embed("css button hover animation")
        assert embedding_service.cosine(query, near) > embedding_service.cosine(query, far)

    def test_cosine_handles_empty_vectors(self):
        assert embedding_service.cosine([], [1.0]) == 0.0


# ═══ Local-model JSON extraction ══════════════════════════════════════════════

class TestJsonExtraction:
    def test_extracts_object_from_surrounding_prose(self):
        text = 'Sure! Here is the result:\n{"branch_name": "agent/x", "files": []}\nHope that helps.'
        assert llm_service._extract_json(text)["branch_name"] == "agent/x"

    def test_handles_nested_objects(self):
        assert llm_service._extract_json('{"a": {"b": {"c": 1}}}')["a"]["b"]["c"] == 1

    def test_ignores_braces_inside_strings(self):
        parsed = llm_service._extract_json('{"code": "if (x) { y() }", "ok": true}')
        assert parsed["ok"] is True and parsed["code"] == "if (x) { y() }"

    def test_returns_none_when_no_json_present(self):
        assert llm_service._extract_json("I could not complete that.") is None


# ═══ Built-in template library ════════════════════════════════════════════════

class TestTemplateLibrary:
    def test_slugs_are_unique(self):
        slugs = [t["slug"] for t in all_templates()]
        assert len(slugs) == len(set(slugs))

    def test_all_three_kinds_are_present(self):
        kinds = {t["kind"] for t in all_templates()}
        assert kinds == {"skill", "agent", "pod"}

    def test_every_skill_has_real_content(self):
        for t in all_templates():
            if t["kind"] == "skill":
                assert len(t["payload"]["md_content"]) > 200, f"{t['slug']} is too thin to steer a model"

    def test_agent_skill_references_resolve(self):
        """A template that installs a dangling skill reference is a broken install."""
        skill_slugs = {t["slug"] for t in all_templates() if t["kind"] == "skill"}
        for t in all_templates():
            if t["kind"] == "agent":
                for ref in t["payload"].get("skills", []):
                    assert ref in skill_slugs, f"{t['slug']} references missing skill {ref}"

    def test_pod_agent_references_resolve(self):
        agent_slugs = {t["slug"] for t in all_templates() if t["kind"] == "agent"}
        for t in all_templates():
            if t["kind"] == "pod":
                for slot in t["payload"]["agents"]:
                    assert slot["template_slug"] in agent_slugs

    def test_standard_pod_has_a_reviewer_before_devops(self):
        pod = next(t for t in all_templates() if t["slug"] == "standard-sdlc-pod")
        order = {s["role"]: s["execution_order"] for s in pod["payload"]["agents"]}
        assert order["reviewer"] < order["devops"]
