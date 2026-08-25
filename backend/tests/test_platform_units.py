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
        provider, key, is_byo, _url = llm_service.resolve_credentials(
            "openai", "sk-customer", "claude-opus-5")
        assert (provider, key, is_byo) == ("openai", "sk-customer", True)

    def test_platform_key_used_when_no_byo(self):
        _, _, is_byo, _url = llm_service.resolve_credentials(None, None, "claude-opus-5")
        assert is_byo is False

    def test_a_keyless_provider_is_still_the_workspace_own(self):
        # A local Ollama has no credential, but it is the customer's hardware.
        # Billing it as platform spend would charge them for their own GPUs.
        _p, key, is_byo, _url = llm_service.resolve_credentials("ollama", None, "llama3.3")
        assert key == "" and is_byo is True

    def test_credential_carries_the_endpoint(self):
        # Fifteen vendors share one client; the base URL is what separates them.
        _p, _k, _b, url = llm_service.resolve_credentials("groq", "gsk_x", "llama-3.3-70b-versatile")
        assert url == "https://api.groq.com/openai/v1"

    def test_a_stored_base_url_beats_the_catalogue_default(self):
        _p, _k, _b, url = llm_service.resolve_credentials(
            "openai", "sk-x", "gpt-5", byo_base_url="https://gateway.internal/v1/")
        assert url == "https://gateway.internal/v1"


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


# ═══════════════════════════════════════════════════════════════════════════════
# Source reader
#
# The scoring half is a port of AgentRead's read.ts and is asserted against the
# same weights, so a drift in either direction shows up here rather than in a
# customer's run trace.
#
# The URL-safety half matters more than the scoring. This service fetches
# arbitrary user-supplied URLs from inside the perimeter, which is textbook SSRF
# territory — these tests are the guard's regression suite.
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceReaderUrlSafety:
    def test_private_and_local_addresses_are_refused(self):
        from app.services import reader_service as r
        blocked = [
            "http://localhost:8000/",
            "http://127.0.0.1/",
            "http://10.0.0.5/internal",
            "http://192.168.1.1/",
            "http://172.16.0.1/",
            # The cloud metadata endpoint — the single most valuable SSRF target
            # there is, and the reason this guard exists at all.
            "http://169.254.169.254/latest/meta-data/",
        ]
        for url in blocked:
            with pytest.raises(r.ReadError):
                r._assert_public_url(r.normalize_url(url))

    def test_non_http_schemes_are_refused(self):
        from app.services import reader_service as r
        for url in ["file:///etc/passwd", "gopher://x/", "ftp://example.com/"]:
            with pytest.raises(r.ReadError):
                r.normalize_url(url)

    def test_bare_host_is_upgraded_to_https(self):
        from app.services import reader_service as r
        assert r.normalize_url("example.com").startswith("https://")

    def test_empty_url_is_refused(self):
        from app.services import reader_service as r
        with pytest.raises(r.ReadError):
            r.normalize_url("   ")


class TestSourceReaderUrlExtraction:
    def test_finds_urls_in_order_without_duplicates(self):
        from app.services.reader_service import extract_urls
        text = "See https://a.example/spec and https://b.example/x, then https://a.example/spec again."
        assert extract_urls(text) == ["https://a.example/spec", "https://b.example/x"]

    def test_trailing_sentence_punctuation_is_not_part_of_the_url(self):
        from app.services.reader_service import extract_urls
        assert extract_urls("Read https://a.example/page.") == ["https://a.example/page"]

    def test_assets_and_badges_are_skipped(self):
        """Reading a PNG or a build badge back costs tokens and returns nothing."""
        from app.services.reader_service import extract_urls
        text = ("https://x.example/logo.png https://img.shields.io/badge/a "
                "https://x.example/real-doc")
        assert extract_urls(text) == ["https://x.example/real-doc"]

    def test_the_limit_is_enforced(self):
        from app.services.reader_service import extract_urls
        text = " ".join(f"https://e{i}.example/p" for i in range(20))
        assert len(extract_urls(text, limit=3)) == 3

    def test_no_urls_is_an_empty_list_not_an_error(self):
        from app.services.reader_service import extract_urls
        assert extract_urls("A ticket with no links at all.") == []
        assert extract_urls("") == []


class TestSourceReaderScoring:
    """The weights, held to the values in agentread-main/src/lib/engine/read.ts."""

    def test_penalty_weights_match_the_source_engine(self):
        from app.services import reader_service as r
        assert (r.PENALTY_LOW_REDUCTION, r.PENALTY_SCRIPT_HEAVY, r.PENALTY_JS_ONLY_PRICE,
                r.PENALTY_DISABLED_CTA, r.PENALTY_LAZY_CONTENT, r.PENALTY_NO_LLMS_TXT,
                r.PENALTY_THIN_CONTENT) == (15, 10, 20, 15, 8, 7, 25)

    def test_risk_thresholds_match_the_source_engine(self):
        from app.services import reader_service as r
        assert (r.RISK_LOW_AT, r.RISK_MEDIUM_AT) == (75, 55)

    def test_token_estimate_is_four_chars_per_token(self):
        from app.services.reader_service import estimate_tokens
        assert estimate_tokens("x" * 400) == 100
        # Never zero: a costed thing that estimates as free is worse than a
        # rough estimate.
        assert estimate_tokens("") == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Single sign-on
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def fake_idp():
    """
    A discovered identity provider, without the network.

    `discover()` caches by issuer, so priming the cache is the honest seam here:
    the tests below are about state, PKCE and URL construction, and none of them
    should fail because a build machine has no outbound DNS.
    """
    from app.services import sso_service
    issuer = "https://idp.example"
    sso_service._discovery_cache[issuer] = (time.monotonic(), {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/authorize",
        "token_endpoint": f"{issuer}/token",
        "jwks_uri": f"{issuer}/keys",
        "userinfo_endpoint": f"{issuer}/userinfo",
        "code_challenge_methods_supported": ["S256"],
    })
    yield issuer
    sso_service._discovery_cache.pop(issuer, None)


class TestSsoState:
    """
    The `state` parameter is a signed JWT rather than a row in Redis, which is
    what lets a callback land on a different worker than the one that started
    the flow. It is also the only thing binding the PKCE verifier and the nonce
    to this particular sign-in, so tampering and expiry both have to be fatal.
    """

    def test_state_round_trips_the_connection_nonce_and_verifier(self, fake_idp):
        from app.services import sso_service
        url = sso_service.authorize_url("11111111-1111-1111-1111-111111111111",
                                        fake_idp, "client-abc")
        from urllib.parse import parse_qs, urlparse
        state = parse_qs(urlparse(url).query)["state"][0]
        claims = sso_service.read_state(state)
        assert claims["cid"] == "11111111-1111-1111-1111-111111111111"
        assert claims["nonce"] and claims["verifier"]

    def test_a_tampered_state_is_refused(self):
        from app.services import sso_service
        with pytest.raises(sso_service.SsoError):
            sso_service.read_state("not.a.jwt")

    def test_an_expired_state_is_refused(self):
        from jose import jwt
        from app.config import settings
        from app.services import sso_service
        stale = jwt.encode({"cid": "x", "nonce": "n", "verifier": "v",
                            "exp": int(time.time()) - 5},
                           settings.jwt_secret, algorithm="HS256")
        with pytest.raises(sso_service.SsoError):
            sso_service.read_state(stale)

    def test_pkce_challenge_is_s256_not_plain(self, fake_idp):
        """`plain` would make PKCE decorative — the whole point is that an
        intercepted authorization code is useless without the verifier."""
        from urllib.parse import parse_qs, urlparse
        from app.services import sso_service
        url = sso_service.authorize_url("cid", fake_idp, "client")
        q = parse_qs(urlparse(url).query)
        assert q["code_challenge_method"] == ["S256"]
        assert q["code_challenge"][0] != q["state"][0]

    def test_two_flows_never_share_a_verifier(self, fake_idp):
        from urllib.parse import parse_qs, urlparse
        from app.services import sso_service
        seen = set()
        for _ in range(5):
            url = sso_service.authorize_url("cid", fake_idp, "client")
            state = parse_qs(urlparse(url).query)["state"][0]
            seen.add(sso_service.read_state(state)["verifier"])
        assert len(seen) == 5

    def test_redirect_uri_points_at_the_api_not_the_spa(self):
        """The code exchange uses the client secret, so it can never happen in
        a browser."""
        from app.config import settings
        from app.services import sso_service
        assert sso_service.redirect_uri().startswith(settings.api_base_url.rstrip("/"))
        assert sso_service.redirect_uri().endswith("/auth/sso/callback")

    def test_domain_extraction_is_case_insensitive(self):
        from app.services.sso_service import domain_of
        assert domain_of("Person@ACME.com") == "acme.com"
        assert domain_of("  a@b.co.uk ") == "b.co.uk"


# ═══════════════════════════════════════════════════════════════════════════════
# MCP server
# ═══════════════════════════════════════════════════════════════════════════════

class TestMcpServer:
    def test_every_tool_has_a_handler(self):
        from app.routers import mcp
        assert set(mcp.HANDLERS) == {t["name"] for t in mcp.TOOLS}

    def test_the_manifest_does_not_leak_internal_scope_bookkeeping(self):
        from app.routers import mcp
        assert all("scope" not in t for t in mcp._public_tools())
        assert all("inputSchema" in t and "description" in t for t in mcp._public_tools())

    def test_approval_needs_a_scope_that_starting_work_does_not_grant(self):
        """
        The invariant the whole design rests on: a key that can start a run must
        not be able to wave it through. If these two ever collapse to the same
        scope, the approval gate stops meaning anything for API callers.
        """
        from app.routers import mcp
        by_name = {t["name"]: t["scope"] for t in mcp.TOOLS}
        assert by_name["start_run"] == "runs:write"
        assert by_name["approve_run"] == "runs:approve"
        assert by_name["start_run"] != by_name["approve_run"]

    def test_only_the_utility_tool_is_unscoped(self):
        from app.routers import mcp
        unscoped = [t["name"] for t in mcp.TOOLS if not t["scope"]]
        assert unscoped == ["read_url"], "every tool that touches tenant data must carry a scope"

    def test_approve_tool_description_warns_the_model(self):
        """The description is the only guardrail between an eager agent and a
        production deploy, so it has to actually say so."""
        from app.routers import mcp
        text = next(t for t in mcp.TOOLS if t["name"] == "approve_run")["description"].lower()
        assert "audit log" in text
        assert "production" in text

    def test_jsonrpc_error_codes_are_the_standard_ones(self):
        from app.routers import mcp
        assert (mcp.PARSE_ERROR, mcp.INVALID_REQUEST, mcp.METHOD_NOT_FOUND,
                mcp.INVALID_PARAMS, mcp.INTERNAL_ERROR) == (-32700, -32600, -32601, -32602, -32603)


# ═══════════════════════════════════════════════════════════════════════════════
# Ticket write-back
#
# The invariant under test is not "does it post a comment" — that needs a real
# Jira. It is that write-back can never hurt a run, and that a status move is
# opt-in while narration is not.
# ═══════════════════════════════════════════════════════════════════════════════

class TestWritebackSafety:
    def test_a_raising_tracker_never_escapes_into_the_run(self, monkeypatch):
        """
        This is the whole point. `_emit` is called from inside the Celery task
        that owns a deploy; an exception escaping it would fail a run that has
        already been approved because Jira was down.
        """
        from app.services import writeback_service as w

        def explode(*a, **k):
            raise RuntimeError("Jira is on fire")

        monkeypatch.setattr(w, "_target", explode)
        run = types.SimpleNamespace(id="r1", project_id="p1", ticket_id="t1")
        w._emit(None, run, "running", "hello")   # must not raise

    def test_a_project_without_writeback_enabled_is_a_no_op(self):
        from app.services import writeback_service as w
        project = types.SimpleNamespace(writeback={})
        assert w._config(project) == {}
        assert not w._config(project).get("enabled")

    def test_failure_maps_to_no_status_by_default(self):
        """A failed run is not a ticket state. Moving someone's ticket to
        'Done' or 'Blocked' because an agent crashed is worse than silence."""
        from app.services.writeback_service import DEFAULT_STATUS_MAP
        assert DEFAULT_STATUS_MAP["failed"] == ""

    def test_an_empty_status_never_attempts_a_move(self):
        from app.services import writeback_service as w
        target = w.WritebackTarget(provider="jira", connection=None, ticket=None,
                                   status_map={"failed": ""})
        assert w._move(target, "failed") is False

    def test_only_the_last_environment_closes_the_ticket(self):
        """
        A ticket that flips to Done when dev deploys, then sits there while prod
        is still waiting at a gate, is worse than no write-back at all.
        """
        from app.services import writeback_service as w

        class FakeQuery:
            def __init__(self, project): self._p = project
            def filter(self, *a): return self
            def first(self): return self._p

        class FakeDb:
            def __init__(self, project): self._p = project
            def query(self, *a): return FakeQuery(self._p)

        project = types.SimpleNamespace(
            deploy_targets=[{"env": "dev"}, {"env": "qa"}, {"env": "prod"}])
        db = FakeDb(project)
        run = types.SimpleNamespace(id="r1", project_id="p1")

        assert w._is_last_environment(db, run, "prod") is True
        assert w._is_last_environment(db, run, "dev") is False
        assert w._is_last_environment(db, run, "qa") is False

    def test_a_project_with_no_deploy_targets_treats_any_deploy_as_final(self):
        from app.services import writeback_service as w

        class FakeDb:
            def query(self, *a): return self
            def filter(self, *a): return self
            def first(self): return types.SimpleNamespace(deploy_targets=[])

        run = types.SimpleNamespace(id="r1", project_id="p1")
        assert w._is_last_environment(FakeDb(), run, "prod") is True


class TestJiraAdf:
    """Jira Cloud rejects a plain string comment body — it wants Atlassian
    Document Format — and a URL that is not marked as a link is a URL somebody
    has to select and copy."""

    def test_urls_become_links(self):
        from app.services.jira_service import _adf
        doc = _adf("Opened https://github.com/a/b/pull/3 for review.")
        marks = [n for n in doc["content"][0]["content"] if n.get("marks")]
        assert len(marks) == 1
        assert marks[0]["marks"][0]["attrs"]["href"] == "https://github.com/a/b/pull/3"

    def test_blank_lines_are_dropped_but_a_body_is_always_produced(self):
        from app.services.jira_service import _adf
        assert len(_adf("one\n\n\ntwo")["content"]) == 2
        # An empty doc is a 400 from Jira, so there is always at least one node.
        assert _adf("")["content"]

    def test_shape_is_a_versioned_doc(self):
        from app.services.jira_service import _adf
        doc = _adf("hello")
        assert doc["type"] == "doc" and doc["version"] == 1


# ═══ Sprint planner ═══════════════════════════════════════════════════════════

class _FakeTicket:
    def __init__(self, jira_id):
        self.jira_id = jira_id
        self.id = jira_id  # stand-in; resolve_estimate never uses the real uuid shape


class TestSprintPlannerResolution:
    """resolve_estimate and plan_health are the two places a silent regression
    would either overcommit a sprint or hide a real blocker behind a green
    'on_track' banner — pinned independent of any DB session or LLM call."""

    def test_clamps_story_points_into_range(self):
        from app.services.sprint_planner_service import resolve_estimate
        by_id = {"A-1": _FakeTicket("A-1")}
        row = resolve_estimate({"jira_id": "A-1", "story_points": 999, "depends_on": []}, by_id, set())
        assert row["story_points"] == 21
        row = resolve_estimate({"jira_id": "A-1", "story_points": 0, "depends_on": []}, by_id, set())
        assert row["story_points"] == 1

    def test_unknown_ticket_id_is_dropped_not_guessed(self):
        from app.services.sprint_planner_service import resolve_estimate
        assert resolve_estimate({"jira_id": "GHOST-1", "story_points": 3, "depends_on": []}, {}, set()) is None

    def test_self_dependency_is_stripped(self):
        from app.services.sprint_planner_service import resolve_estimate
        by_id = {"A-1": _FakeTicket("A-1")}
        row = resolve_estimate({"jira_id": "A-1", "story_points": 3, "depends_on": ["A-1"]}, by_id, {"A-1"})
        assert row["depends_on"] == []

    def test_included_ticket_blocked_by_excluded_dependency(self):
        from app.services.sprint_planner_service import resolve_estimate
        by_id = {"A-1": _FakeTicket("A-1"), "A-2": _FakeTicket("A-2")}
        # A-1 depends on A-2, but only A-1 was selected for the sprint.
        row = resolve_estimate(
            {"jira_id": "A-1", "story_points": 3, "depends_on": ["A-2"], "include_in_sprint": True},
            by_id, included_ids={"A-1"},
        )
        assert row["included_in_sprint"] is True
        assert row["risk"] == "blocked"

    def test_included_ticket_not_blocked_when_dependency_also_included(self):
        from app.services.sprint_planner_service import resolve_estimate
        by_id = {"A-1": _FakeTicket("A-1"), "A-2": _FakeTicket("A-2")}
        row = resolve_estimate(
            {"jira_id": "A-1", "story_points": 3, "depends_on": ["A-2"], "include_in_sprint": True},
            by_id, included_ids={"A-1", "A-2"},
        )
        assert row["risk"] == "on_track"

    def test_excluded_ticket_is_never_blocked_regardless_of_dependencies(self):
        # Risk describes whether the sprint can execute, not the ticket's own
        # standing — a ticket that isn't in the sprint has nothing to block.
        from app.services.sprint_planner_service import resolve_estimate
        by_id = {"A-1": _FakeTicket("A-1"), "A-2": _FakeTicket("A-2")}
        row = resolve_estimate(
            {"jira_id": "A-1", "story_points": 3, "depends_on": ["A-2"], "include_in_sprint": False},
            by_id, included_ids=set(),
        )
        assert row["risk"] == "on_track"


class TestSprintPlanHealth:
    def test_blocked_beats_at_risk(self):
        from app.services.sprint_planner_service import plan_health
        # Even at 0% committed, one blocked ticket makes the sprint unable to proceed as planned.
        assert plan_health(capacity_points=20, committed_points=0, any_blocked=True) == "blocked"

    def test_at_risk_at_ninety_percent_capacity(self):
        from app.services.sprint_planner_service import plan_health
        assert plan_health(capacity_points=20, committed_points=18, any_blocked=False) == "at_risk"
        assert plan_health(capacity_points=20, committed_points=17, any_blocked=False) == "on_track"

    def test_zero_capacity_never_divides_by_zero(self):
        from app.services.sprint_planner_service import plan_health
        assert plan_health(capacity_points=0, committed_points=0, any_blocked=False) == "on_track"


class TestReviewerSuggestion:
    def test_ranks_by_file_frequency(self):
        from app.services.reviewer_suggestion_service import rank
        authors = {
            "a.py": ["alice", "alice", "bob"],
            "b.py": ["alice", "carol"],
        }
        # alice touched both files (counted once per file), bob and carol touched one each
        assert rank(authors, exclude=set()) == ["alice", "bob"]

    def test_excludes_given_logins(self):
        from app.services.reviewer_suggestion_service import rank
        authors = {"a.py": ["alice", "bob", "bot-agent"]}
        assert rank(authors, exclude={"alice", "bot-agent"}) == ["bob"]

    def test_caps_at_max_reviewers(self):
        from app.services.reviewer_suggestion_service import rank
        authors = {"a.py": ["alice"], "b.py": ["bob"], "c.py": ["carol"]}
        result = rank(authors, exclude=set(), max_reviewers=2)
        assert len(result) == 2

    def test_empty_history_returns_empty(self):
        from app.services.reviewer_suggestion_service import rank
        assert rank({}, exclude=set()) == []

    def test_ties_broken_alphabetically_for_determinism(self):
        from app.services.reviewer_suggestion_service import rank
        authors = {"a.py": ["zed"], "b.py": ["amy"]}
        assert rank(authors, exclude=set(), max_reviewers=2) == ["amy", "zed"]


# ═══ Workspace — the collaboration layer ══════════════════════════════════════
#
# The chat surface is the one place in the product where an *absence* of a check
# is invisible until it is a breach: a broadcast channel anyone can post to
# still looks like a working channel, and a mention parser that matches the
# wrong principal still looks like a delivered message. These pin the rules that
# have no UI symptom when they break.

class _StubQuery:
    """Minimal SQLAlchemy query stand-in — filter() chains, first() answers."""
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


class TestChannelSlugs:
    def test_slug_is_lowercase_and_dashed(self):
        from app.services.workspace_service import slugify
        assert slugify("Payments Squad") == "payments-squad"

    def test_punctuation_collapses_to_single_dash(self):
        from app.services.workspace_service import slugify
        assert slugify("QA / Release  ->  prod!") == "qa-release-prod"

    def test_leading_and_trailing_separators_are_trimmed(self):
        from app.services.workspace_service import slugify
        assert slugify("  #general  ") == "general"

    def test_empty_name_still_yields_a_usable_slug(self):
        # A NULL or all-punctuation name must not produce an empty slug — the
        # partial unique index would then collide every such channel together.
        from app.services.workspace_service import slugify
        assert slugify("!!!").startswith("channel-")
        assert slugify("") != ""


class TestBroadcastChannelIsReadOnly:
    """
    The WhatsApp-Channel shape: admins publish, everyone else reads.

    This asymmetry is the entire reason the `broadcast` kind exists. Enforced in
    the service, never only in the UI — a UI-only rule is a suggestion.
    """
    def _channel(self, kind):
        return types.SimpleNamespace(id="c1", kind=kind, is_archived=False)

    def test_ordinary_member_cannot_post_to_broadcast(self, monkeypatch):
        from app.services import workspace_service as ws
        monkeypatch.setattr(ws, "is_member", lambda db, c, u: types.SimpleNamespace(role="member"))
        allowed, reason = ws.can_post(None, self._channel("broadcast"), "u1")
        assert allowed is False
        assert "admin" in reason.lower()

    def test_admin_can_post_to_broadcast(self, monkeypatch):
        from app.services import workspace_service as ws
        monkeypatch.setattr(ws, "is_member", lambda db, c, u: types.SimpleNamespace(role="admin"))
        allowed, _ = ws.can_post(None, self._channel("broadcast"), "u1")
        assert allowed is True

    def test_non_member_cannot_post_to_broadcast(self, monkeypatch):
        from app.services import workspace_service as ws
        monkeypatch.setattr(ws, "is_member", lambda db, c, u: None)
        allowed, _ = ws.can_post(None, self._channel("broadcast"), "u1")
        assert allowed is False

    def test_ordinary_member_can_post_to_a_normal_channel(self, monkeypatch):
        from app.services import workspace_service as ws
        monkeypatch.setattr(ws, "is_member", lambda db, c, u: types.SimpleNamespace(role="member"))
        allowed, _ = ws.can_post(None, self._channel("channel"), "u1")
        assert allowed is True

    def test_archived_channel_rejects_everyone(self, monkeypatch):
        from app.services import workspace_service as ws
        monkeypatch.setattr(ws, "is_member", lambda db, c, u: types.SimpleNamespace(role="owner"))
        ch = types.SimpleNamespace(id="c1", kind="channel", is_archived=True)
        allowed, reason = ws.can_post(None, ch, "u1")
        assert allowed is False and "archived" in reason.lower()

    def test_non_member_cannot_post_to_private(self, monkeypatch):
        from app.services import workspace_service as ws
        monkeypatch.setattr(ws, "is_member", lambda db, c, u: None)
        allowed, _ = ws.can_post(None, self._channel("private"), "u1")
        assert allowed is False


class TestChannelReadAccess:
    def test_public_channels_are_readable_without_membership(self, monkeypatch):
        from app.services import workspace_service as ws
        monkeypatch.setattr(ws, "is_member", lambda db, c, u: None)
        for kind in ("channel", "broadcast"):
            ch = types.SimpleNamespace(id="c1", kind=kind)
            assert ws.can_read(None, ch, "u1") is True

    def test_private_and_dms_require_membership(self, monkeypatch):
        from app.services import workspace_service as ws
        monkeypatch.setattr(ws, "is_member", lambda db, c, u: None)
        for kind in ("private", "dm", "group_dm"):
            ch = types.SimpleNamespace(id="c1", kind=kind)
            assert ws.can_read(None, ch, "u1") is False


class TestMentionParsing:
    """
    Mentions are parsed once at write time and stored on the row. A parser that
    resolves the wrong principal sends work to the wrong agent, so the
    agent-before-human precedence is pinned here rather than left to import order.
    """
    def _channel(self):
        return types.SimpleNamespace(id="c1", user_id="u1", kind="channel")

    def _db(self, agents=(), users=()):
        from app.models.agent import Agent
        return _StubSession({Agent: list(agents)})

    def test_plain_text_has_no_mentions(self):
        from app.services import workspace_service as ws
        out = ws.parse_mentions(self._db(), "shipping this today", self._channel(), None)
        assert out == {"users": [], "agents": [], "channel": False, "here": False}

    def test_at_channel_and_at_here_are_broadcast_flags(self):
        from app.services import workspace_service as ws
        db = self._db()
        assert ws.parse_mentions(db, "@channel heads up", self._channel(), None)["channel"] is True
        assert ws.parse_mentions(db, "@here quick one", self._channel(), None)["here"] is True

    def test_agent_is_matched_by_name_slug(self, monkeypatch):
        from app.services import workspace_service as ws
        from app.models.agent import Agent
        agent = types.SimpleNamespace(id="a1", name="QA Bot", role="qa", is_active=True)
        db = _StubSession({Agent: [agent]})
        monkeypatch.setattr(ws, "_workspace_users", lambda *a, **k: [])
        out = ws.parse_mentions(db, "@qa-bot please check PROJ-1", self._channel(), None)
        assert out["agents"] == ["a1"]

    def test_agent_is_matched_by_role(self, monkeypatch):
        from app.services import workspace_service as ws
        from app.models.agent import Agent
        agent = types.SimpleNamespace(id="a1", name="Sentinel", role="qa", is_active=True)
        db = _StubSession({Agent: [agent]})
        monkeypatch.setattr(ws, "_workspace_users", lambda *a, **k: [])
        assert ws.parse_mentions(db, "@qa take a look", self._channel(), None)["agents"] == ["a1"]

    def test_agent_wins_over_a_user_with_the_same_handle(self, monkeypatch):
        # "@qa please look" in a channel that has a QA agent means the agent.
        # If this ever flips, mentions silently stop starting runs.
        from app.services import workspace_service as ws
        from app.models.agent import Agent
        agent = types.SimpleNamespace(id="a1", name="qa", role="qa", is_active=True)
        user = types.SimpleNamespace(id="u9", email="qa@acme.com", name="Quinn")
        db = _StubSession({Agent: [agent]})
        monkeypatch.setattr(ws, "_workspace_users", lambda *a, **k: [user])
        out = ws.parse_mentions(db, "@qa please look", self._channel(), None)
        assert out["agents"] == ["a1"]
        assert out["users"] == []

    def test_user_matched_on_email_local_part(self, monkeypatch):
        from app.services import workspace_service as ws
        user = types.SimpleNamespace(id="u9", email="priya@acme.com", name="Priya R")
        monkeypatch.setattr(ws, "_workspace_users", lambda *a, **k: [user])
        out = ws.parse_mentions(self._db(), "@priya can you review?", self._channel(), None)
        assert out["users"] == ["u9"]

    def test_trailing_punctuation_is_not_part_of_the_handle(self, monkeypatch):
        from app.services import workspace_service as ws
        user = types.SimpleNamespace(id="u9", email="dev@acme.com", name="Dev")
        monkeypatch.setattr(ws, "_workspace_users", lambda *a, **k: [user])
        out = ws.parse_mentions(self._db(), "ping @dev.", self._channel(), None)
        assert out["users"] == ["u9"]

    def test_email_addresses_do_not_create_phantom_mentions(self, monkeypatch):
        # "mail me at foo@bar.com" must not mention anyone called `bar.com`.
        from app.services import workspace_service as ws
        monkeypatch.setattr(ws, "_workspace_users", lambda *a, **k: [])
        out = ws.parse_mentions(self._db(), "mail me at foo@bar.com", self._channel(), None)
        assert out["users"] == [] and out["agents"] == []


class TestNotificationRecipients:
    """
    Who a message is allowed to interrupt. Mute and notify_level are the two
    settings that decide whether this product is liveable at 2am.
    """
    def _member(self, uid, notify_level="all", muted=False):
        return types.SimpleNamespace(user_id=uid, notify_level=notify_level, is_muted=muted)

    def _run(self, members, mentions, author="author"):
        from app.services import workspace_service as ws
        from app.models.workspace import ChannelMember
        db = _StubSession({ChannelMember: members})
        ch = types.SimpleNamespace(id="c1")
        return [m.user_id for m in ws._recipients(db, ch, mentions, author)]

    def test_author_never_notifies_themselves(self):
        members = [self._member("author"), self._member("u2")]
        assert self._run(members, {}) == ["u2"]

    def test_notify_none_is_absolute(self):
        members = [self._member("u2", notify_level="none")]
        assert self._run(members, {"users": ["u2"]}) == []

    def test_mentions_only_skips_ordinary_traffic(self):
        members = [self._member("u2", notify_level="mentions")]
        assert self._run(members, {}) == []

    def test_mentions_only_still_receives_a_direct_mention(self):
        members = [self._member("u2", notify_level="mentions")]
        assert self._run(members, {"users": ["u2"]}) == ["u2"]

    def test_muted_channel_is_pierced_by_a_direct_mention(self):
        # Mute means "do not interrupt me for chatter", not "never reach me".
        members = [self._member("u2", muted=True)]
        assert self._run(members, {"users": ["u2"]}) == ["u2"]

    def test_muted_channel_swallows_ordinary_traffic(self):
        members = [self._member("u2", muted=True)]
        assert self._run(members, {}) == []

    def test_at_channel_reaches_everyone_who_has_not_opted_out(self):
        members = [self._member("u2", muted=True), self._member("u3", notify_level="mentions")]
        assert sorted(self._run(members, {"channel": True})) == ["u2", "u3"]


class TestRunNarration:
    def test_only_human_meaningful_events_are_narrated(self):
        # The step firehose belongs on the run trace page, not in a channel a
        # human is trying to read.
        from app.services.workspace_bridge import NARRATED
        assert "run:step:log" not in NARRATED
        assert "run:step:started" not in NARRATED

    def test_the_events_a_team_must_see_are_all_present(self):
        from app.services.workspace_bridge import NARRATED
        for event in ("run:started", "run:awaiting_approval", "run:completed",
                      "run:failed", "run:policy:blocked"):
            assert event in NARRATED

    def test_approval_is_the_only_gate_severity_that_warns(self):
        from app.services.workspace_bridge import NARRATED
        assert NARRATED["run:awaiting_approval"][1] == "warning"
        assert NARRATED["run:failed"][1] == "critical"


class TestTicketKeyExtraction:
    def test_finds_a_standard_tracker_key(self):
        from app.services.workspace_bridge import _TICKET_RE
        assert _TICKET_RE.search("please pick up PROJ-214 today").group(1) == "PROJ-214"

    def test_matches_lowercase_as_typed_in_chat(self):
        from app.services.workspace_bridge import _TICKET_RE
        assert _TICKET_RE.search("proj-7 is broken") is not None

    def test_does_not_match_a_bare_number_or_a_date(self):
        from app.services.workspace_bridge import _TICKET_RE
        assert _TICKET_RE.search("deployed 214 changes") is None
        assert _TICKET_RE.search("on 2026-08") is None


class TestMessagePreviewIsBounded:
    def test_preview_is_truncated_to_the_column_width(self):
        # last_message_preview is String(280); an untruncated body would raise
        # on insert and take the whole message with it.
        from app.services.workspace_service import _preview
        assert len(_preview("x" * 5000, "user")) == 280

    def test_newlines_are_flattened_for_the_sidebar(self):
        from app.services.workspace_service import _preview
        assert "\n" not in _preview("line one\nline two", "user")

    def test_an_empty_system_message_still_reads_as_something(self):
        from app.services.workspace_service import _preview
        assert _preview("", "system") == "Run update"


# ═══ Run concurrency ══════════════════════════════════════════════════════════
#
# Devin's "automations queueing", as a policy rather than a queue setting. The
# rules with no visible symptom when they break: an unlimited default must stay
# unlimited, a run parked at the approval gate must not hold a slot, and a full
# queue must refuse rather than accept work that will never start.

class TestConcurrencyPolicyDefaults:
    def test_zero_limit_means_unlimited(self):
        from app.services import policy_service as ps
        d = ps.check_concurrency(None, project_id="p", org_id=None,
                                 policy={"max_concurrent_runs": 0})
        assert d.admitted is True and d.queued is False and d.limit == 0

    def test_missing_key_is_treated_as_unlimited(self):
        # A policy dict from before these columns existed must not start
        # silently throttling every project to zero.
        from app.services import policy_service as ps
        d = ps.check_concurrency(None, project_id="p", org_id=None, policy={})
        assert d.admitted is True

    def test_default_policy_carries_both_limits_unset(self):
        from app.services.policy_service import DEFAULT_POLICY
        assert DEFAULT_POLICY["max_concurrent_runs"] == 0
        assert DEFAULT_POLICY["max_queue_depth"] == 0


class TestConcurrencySlotAccounting:
    """
    A run waiting at the approval gate must NOT hold a slot.

    If it did, three un-reviewed PRs would deadlock a project's whole pipeline
    until a human woke up — which is the exact failure mode a concurrency cap is
    supposed to prevent, not cause.
    """
    def test_awaiting_approval_does_not_occupy_a_slot(self):
        from app.services.policy_service import ACTIVE_STATUSES
        assert "awaiting_approval" not in ACTIVE_STATUSES
        assert "running" in ACTIVE_STATUSES

    def test_completed_and_failed_do_not_occupy_a_slot(self):
        from app.services.policy_service import ACTIVE_STATUSES
        assert "completed" not in ACTIVE_STATUSES
        assert "failed" not in ACTIVE_STATUSES

    def test_queued_is_the_waiting_state_not_the_active_one(self):
        from app.services.policy_service import ACTIVE_STATUSES, QUEUED_STATUSES
        assert "queued" in QUEUED_STATUSES
        assert "queued" not in ACTIVE_STATUSES


class TestConcurrencyDecisionShape:
    def test_decision_serialises_every_field_the_client_needs(self):
        from app.services.policy_service import ConcurrencyDecision
        d = ConcurrencyDecision(admitted=False, queued=True, running=3, waiting=1, limit=3)
        out = d.as_dict()
        assert set(out) == {"admitted", "queued", "reason", "running", "waiting", "limit"}

    def test_queued_and_refused_are_distinguishable(self):
        # The caller must be able to tell "wait" from "no" — one keeps the run,
        # the other deletes it and returns 429.
        from app.services.policy_service import ConcurrencyDecision
        queued = ConcurrencyDecision(admitted=False, queued=True)
        refused = ConcurrencyDecision(admitted=False, queued=False, reason="queue full")
        assert queued.reason is None
        assert refused.reason is not None and refused.queued is False


# ═══ Model provider catalogue ═════════════════════════════════════════════════
#
# A registry's failure mode is a typo: a wrong wire format sends the call to the
# wrong client, a missing base URL 500s at run time, a duplicate key silently
# shadows a provider. None of those have a UI symptom until someone's run fails.

class TestProviderCatalogue:
    def test_every_provider_key_is_unique(self):
        from app.services.llm_providers import PROVIDERS
        keys = [p["key"] for p in PROVIDERS]
        assert len(keys) == len(set(keys))

    def test_every_provider_declares_a_known_wire(self):
        from app.services.llm_providers import PROVIDERS
        assert {p["wire"] for p in PROVIDERS} <= {"anthropic", "openai", "google", "ollama"}

    def test_every_wire_has_a_client_in_llm_service(self):
        # The dispatch in complete() is a chain of elifs; a wire with no branch
        # raises only when someone finally selects that provider.
        from app.services import llm_service
        from app.services.llm_providers import PROVIDERS
        for wire in {p["wire"] for p in PROVIDERS}:
            assert hasattr(llm_service, f"_{wire}_complete"), f"no client for wire '{wire}'"

    def test_every_provider_has_an_endpoint_or_demands_one(self):
        from app.services import llm_providers as lp
        for p in lp.PROVIDERS:
            has_default = bool(p.get("base_url"))
            demands_one = lp.requires_base_url(p["key"])
            assert has_default or demands_one, f"{p['key']} can never be called"

    def test_every_provider_belongs_to_a_named_family(self):
        from app.services.llm_providers import FAMILIES, PROVIDERS
        for p in PROVIDERS:
            assert p["family"] in FAMILIES

    def test_catalog_never_loses_a_provider(self):
        from app.services.llm_providers import PROVIDERS, catalog
        listed = sum(len(g["providers"]) for g in catalog())
        assert listed == len(PROVIDERS)

    def test_self_hosted_providers_do_not_demand_a_key(self):
        # Ollama and LM Studio run without auth; requiring a key would make the
        # air-gapped path unusable.
        from app.services import llm_providers as lp
        assert lp.requires_key("ollama") is False
        assert lp.requires_key("lmstudio") is False

    def test_azure_demands_a_base_url(self):
        # Azure's endpoint is per-resource and per-deployment. Defaulting it
        # would send every Azure call to a host that does not exist.
        from app.services import llm_providers as lp
        assert lp.requires_base_url("azure") is True

    def test_unknown_provider_falls_back_to_the_openai_wire(self):
        # A provider added to the DB but not yet to the registry is far more
        # likely to be another OpenAI-compatible endpoint than anything else.
        from app.services.llm_providers import wire_for
        assert wire_for("some-new-vendor") == "openai"


class TestModelRouting:
    @pytest.mark.parametrize("model,provider", [
        ("claude-opus-5", "anthropic"),
        ("gpt-5", "openai"),
        ("gemini-2.5-pro", "google"),
        ("grok-4", "xai"),
        ("deepseek-reasoner", "deepseek"),
        ("codestral-latest", "mistral"),
        ("sonar-pro", "perplexity"),
        ("anthropic/claude-sonnet-4.5", "openrouter"),
    ])
    def test_model_ids_route_to_the_right_vendor(self, model, provider):
        from app.services.llm_service import provider_for_model
        assert provider_for_model(model) == provider


class TestPriceOverrides:
    def test_a_workspace_rate_beats_the_published_table(self):
        # Anyone on committed spend has a truer number than any public list.
        from app.services.llm_service import cost_millicents
        override = {"claude-opus-5": {"input": 100, "output": 200}}
        assert cost_millicents("claude-opus-5", 1_000_000, 0, override) == 100_000

    def test_an_override_for_another_model_is_ignored(self):
        from app.services.llm_service import cost_millicents
        plain = cost_millicents("claude-opus-5", 1_000_000, 0)
        with_other = cost_millicents("claude-opus-5", 1_000_000, 0, {"gpt-5": {"input": 1, "output": 1}})
        assert plain == with_other

    def test_a_malformed_override_falls_back_rather_than_crashing(self):
        # A half-filled override in the DB must not take down cost attribution.
        from app.services.llm_service import cost_millicents
        assert cost_millicents("claude-opus-5", 1000, 100, {"claude-opus-5": {"input": 5}}) > 0

    def test_unpriced_models_are_reported_as_unpriced(self):
        from app.services.llm_service import has_published_price
        assert has_published_price("claude-opus-5") is True
        assert has_published_price("some-vendor/some-model") is False


class TestGeminiSchemaFilter:
    """Gemini 400s on JSON Schema keys the other providers ignore. The agent
    tool schemas are written once and shared, so they are filtered on the way
    out rather than duplicated per vendor."""
    def test_unsupported_keys_are_stripped(self):
        from app.services.llm_service import _gemini_schema
        out = _gemini_schema({"type": "object", "additionalProperties": False, "title": "X"})
        assert "additionalProperties" not in out and "title" not in out

    def test_nested_properties_are_filtered_too(self):
        from app.services.llm_service import _gemini_schema
        out = _gemini_schema({"properties": {"a": {"type": "string", "default": "z"}}})
        assert "default" not in out["properties"]["a"]

    def test_array_items_are_filtered(self):
        from app.services.llm_service import _gemini_schema
        out = _gemini_schema({"type": "array", "items": {"type": "string", "const": "x"}})
        assert "const" not in out["items"]

    def test_the_meaningful_schema_survives(self):
        from app.services.llm_service import _gemini_schema
        out = _gemini_schema({"type": "object", "required": ["a"],
                              "properties": {"a": {"type": "string", "description": "keep"}}})
        assert out["required"] == ["a"]
        assert out["properties"]["a"]["description"] == "keep"


# ═══ Plugin catalogue ═════════════════════════════════════════════════════════

class TestPluginCatalogue:
    def test_every_plugin_key_is_unique(self):
        from app.services.plugins import PLUGINS
        keys = [p["key"] for p in PLUGINS]
        assert len(keys) == len(set(keys))

    def test_every_plugin_declares_an_honest_depth(self):
        # The depth is shown on the card. A catalogue of forty logos is worth
        # nothing if thirty-five only store a token and do not say so.
        from app.services.plugins import NATIVE, NOTIFY, PLUGINS, VERIFIED
        assert {p["depth"] for p in PLUGINS} <= {NATIVE, NOTIFY, VERIFIED}

    def test_the_natively_driven_plugins_are_exactly_the_ones_with_services(self):
        # If this list grows, a real service module has to grow with it.
        from app.services.plugins import NATIVE, PLUGINS
        native = {p["key"] for p in PLUGINS if p["depth"] == NATIVE}
        assert native == {"github", "gitlab", "jira", "linear"}

    def test_every_plugin_belongs_to_a_named_category(self):
        from app.services.plugins import CATEGORIES, PLUGINS
        for p in PLUGINS:
            assert p["category"] in CATEGORIES

    def test_every_plugin_has_a_verification_recipe(self):
        # A plugin with no check is a token nobody ever proved works.
        from app.services.plugins import PLUGINS
        for p in PLUGINS:
            assert p.get("verify"), f"{p['key']} has no verification recipe"

    def test_url_recipes_are_only_used_where_a_url_is_collected(self):
        # "{base}" with no URL field is a KeyError at connect time.
        from app.services import plugins as pl
        for p in pl.PLUGINS:
            if "{base}" in (p.get("verify", {}).get("url") or ""):
                assert pl.requires_url(p["key"]), f"{p['key']} interpolates a URL it never asks for"

    def test_catalog_never_loses_a_plugin(self):
        from app.services.plugins import PLUGINS, catalog
        listed = sum(len(g["plugins"]) for g in catalog())
        assert listed == len(PLUGINS)

    def test_catalog_never_leaks_verification_recipes(self):
        # They are internal, and publishing them invites probing vendors through us.
        from app.services.plugins import catalog
        for group in catalog():
            for plugin in group["plugins"]:
                assert "verify" not in plugin

    def test_counts_are_computed_not_claimed(self):
        from app.services.plugins import PLUGINS, counts
        c = counts()
        assert c["total"] == len(PLUGINS)
        assert c["native"] + c["notify"] + c["verified"] == c["total"]

    def test_webhook_plugins_ask_for_a_url_not_a_token(self):
        from app.services import plugins as pl
        for p in pl.PLUGINS:
            if p["auth"] == pl.AUTH_WEBHOOK:
                assert pl.requires_url(p["key"]) and not pl.requires_token(p["key"])


class TestPluginVerificationSafety:
    def test_a_verification_failure_is_a_status_not_an_exception(self):
        # Called from inside the connect handler; raising would 500 the request
        # that was about to store a perfectly recoverable bad token.
        from app.services import plugin_verify
        result = plugin_verify.verify("definitely-not-a-plugin", token="x")
        assert result.ok is False and "Unknown plugin" in result.detail

    def test_name_extraction_survives_a_vendor_changing_its_response(self):
        from app.services.plugin_verify import _dig
        assert _dig({"data": {"viewer": {"name": "Priya"}}}, "data.viewer.name") == "Priya"
        assert _dig({"data": {}}, "data.viewer.name") is None
        assert _dig(None, "a.b") is None

    def test_name_extraction_walks_into_a_list(self):
        from app.services.plugin_verify import _dig
        assert _dig({"items": [{"name": "first"}]}, "items.name") == "first"
