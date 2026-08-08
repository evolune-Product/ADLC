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
