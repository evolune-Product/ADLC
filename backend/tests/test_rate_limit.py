"""
Tests for the Redis-backed rate limiter (app/services/rate_limit_service.py
and app/middleware/rate_limit_middleware.py).

Unlike the Docker-dependent parts of test_sandbox_service.py, these run
against a real Redis — this repo's own CI runs directly on the GitHub-hosted
runner's VM (no container wrapping the job) and Redis is cheap to expect
locally too (`redis-server`, no daemon-in-daemon complexity). The one thing
that must still be proven without a live Redis is the fail-open contract,
since that path only matters when Redis is UNREACHABLE — so that one test
points the client at a port nothing is listening on rather than mocking
anything.

Plain `def` tests wrapping `asyncio.run(...)`, not `pytest.mark.asyncio` —
`pytest-asyncio` is not a dependency this repo has, and CI's install step
(`pip install pytest ruff`) does not add it. Adding a new test-only dependency
for one file was a worse trade than a few lines of `asyncio.run`.
"""
from __future__ import annotations

import asyncio
import time
import uuid

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.config import settings
from app.middleware.rate_limit_middleware import RateLimitMiddleware, resolve_tier
from app.services import rate_limit_service as rl


def _redis_reachable() -> bool:
    async def _ping():
        client = rl._get_client()
        await client.ping()

    try:
        asyncio.run(_ping())
        return True
    except Exception:
        return False
    finally:
        try:
            asyncio.run(rl.aclose())
        except Exception:
            pass


REDIS_UP = _redis_reachable()
pytestmark = pytest.mark.skipif(not REDIS_UP, reason="no local Redis reachable")


@pytest.fixture(autouse=True)
def _fresh_client():
    # Each test uses a fresh uuid4 key prefix (see _key()) so parallel runs
    # and repeated runs against the same real Redis never see each other's
    # counters — a fixed-window counter is not reset between tests by
    # construction, so isolation has to come from the key, not the fixture.
    yield
    asyncio.run(rl.aclose())


def _key() -> str:
    return f"test:{uuid.uuid4().hex}"


def run(coro):
    """Run one async body to completion in its own event loop. Every test
    below that needs more than one `await rl.check(...)` wraps its whole
    sequence in a single call to this, rather than calling it once per await —
    a redis-asyncio client is bound to the loop that created it, so spreading
    related awaits across several separate `asyncio.run()` calls hands the
    second one a client wired to an already-closed loop. This bit a first
    draft of this file for real; see rate_limit_service.aclose()'s docstring."""
    return asyncio.run(coro)


# ═══ Core counter behaviour ═══════════════════════════════════════════════════

class TestCheck:
    def test_allows_under_the_limit(self):
        key = _key()

        async def body():
            result = None
            for _ in range(3):
                result = await rl.check(key, limit=5)
                assert result.allowed
            return result

        assert run(body()).remaining == 2

    def test_blocks_over_the_limit(self):
        key = _key()

        async def body():
            for _ in range(5):
                assert (await rl.check(key, limit=5)).allowed
            return await rl.check(key, limit=5)

        blocked = run(body())
        assert not blocked.allowed
        assert blocked.remaining == 0
        assert blocked.retry_after > 0

    def test_zero_limit_means_unlimited(self):
        key = _key()

        async def body():
            for _ in range(50):
                assert (await rl.check(key, limit=0)).allowed

        run(body())

    def test_different_keys_have_independent_counters(self):
        a, b = _key(), _key()

        async def body():
            for _ in range(5):
                await rl.check(a, limit=5)
            # b's counter must not have been touched by a's requests.
            return await rl.check(b, limit=5)

        result = run(body())
        assert result.allowed
        assert result.remaining == 4

    def test_new_window_resets_the_counter(self):
        key = _key()

        async def first_window():
            for _ in range(3):
                assert (await rl.check(key, limit=3, window_seconds=1)).allowed
            return await rl.check(key, limit=3, window_seconds=1)

        assert not run(first_window()).allowed
        time.sleep(1.1)
        assert run(rl.check(key, limit=3, window_seconds=1)).allowed


class TestFailsOpen:
    def test_unreachable_redis_allows_the_request(self, monkeypatch):
        monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:1/0")  # nothing listens here
        rl._client = None  # drop the cached real client so the bad URL takes effect
        try:
            result = run(rl.check(_key(), limit=1))
            assert result.allowed
        finally:
            rl._client = None  # do not leak the broken client into later tests


# ═══ Tier resolution ═══════════════════════════════════════════════════════════

class TestResolveTier:
    def test_login_is_the_auth_tier(self):
        tier, limit, window = resolve_tier("/auth/login")
        assert tier == "auth"
        assert limit == settings.rate_limit_auth_per_minute

    def test_register_is_the_auth_tier(self):
        assert resolve_tier("/auth/register")[0] == "auth"

    def test_public_api_is_the_api_tier(self):
        tier, limit, _ = resolve_tier("/v1/runs")
        assert tier == "api"
        assert limit == settings.rate_limit_api_per_minute

    def test_mcp_is_the_api_tier(self):
        assert resolve_tier("/mcp")[0] == "api"

    def test_everything_else_is_default(self):
        assert resolve_tier("/projects")[0] == "default"
        assert resolve_tier("/dashboard")[0] == "default"


# ═══ Middleware, end to end via a minimal Starlette app ═══════════════════════

def _make_app() -> Starlette:
    async def ok(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/projects", ok), Route("/auth/login", ok, methods=["POST"])])
    app.add_middleware(RateLimitMiddleware)
    return app


class TestMiddleware:
    # `with TestClient(...) as client:` matters here, not just style — that
    # context manager is what makes Starlette hold ONE event loop open for
    # every request made inside the block. A bare `TestClient(app)` used
    # without it can run each `.get()` in its own short-lived loop, which hits
    # the exact loop-bound-client trap `rate_limit_service.aclose()` and
    # `run()` above both exist to avoid — this bit a first draft of this file.

    def test_disabled_short_circuits_before_redis(self, monkeypatch):
        monkeypatch.setattr(settings, "rate_limit_enabled", False)
        with TestClient(_make_app()) as client:
            for _ in range(20):
                assert client.get("/projects").status_code == 200

    def test_exceeding_the_default_tier_returns_429_with_retry_after(self, monkeypatch):
        monkeypatch.setattr(settings, "rate_limit_enabled", True)
        monkeypatch.setattr(settings, "rate_limit_default_per_minute", 3)
        headers = {"Authorization": f"Bearer test-{uuid.uuid4().hex}"}  # unique identity per test run

        with TestClient(_make_app()) as client:
            for _ in range(3):
                resp = client.get("/projects", headers=headers)
                assert resp.status_code == 200
                assert "X-RateLimit-Remaining" in resp.headers

            blocked = client.get("/projects", headers=headers)
            assert blocked.status_code == 429
            assert "Retry-After" in blocked.headers

    def test_two_different_bearer_tokens_are_counted_separately(self, monkeypatch):
        monkeypatch.setattr(settings, "rate_limit_enabled", True)
        monkeypatch.setattr(settings, "rate_limit_default_per_minute", 1)
        tok_a = {"Authorization": f"Bearer a-{uuid.uuid4().hex}"}
        tok_b = {"Authorization": f"Bearer b-{uuid.uuid4().hex}"}

        with TestClient(_make_app()) as client:
            assert client.get("/projects", headers=tok_a).status_code == 200
            assert client.get("/projects", headers=tok_a).status_code == 429
            # A different caller must not have been consumed by tok_a's traffic.
            assert client.get("/projects", headers=tok_b).status_code == 200
