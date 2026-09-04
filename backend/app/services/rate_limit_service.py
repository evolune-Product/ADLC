"""
Redis-backed rate limiting — closes the gap Company OS step 24's security
review named and left open: "grepped the whole backend (ratelimit, rate_limit,
slowapi, throttle) — nothing exists anywhere in this codebase, on any surface,
old or new." See `middleware/rate_limit_middleware.py` for where this is
actually applied to every request.

Fixed-window counters via INCR+EXPIRE, not a sliding log — O(1) per request,
one round trip, and precise enough for what this defends against (a leaked API
key, a runaway webhook retry loop, credential stuffing against /auth/login),
none of which need sub-window precision to stop. A request at the edge of two
windows can technically get slightly more than `limit` through in the worst
case; that imprecision is the trade for not keeping a sorted set per caller.

Fails OPEN, not closed: if Redis itself is unreachable, requests pass through
uncounted rather than the whole API going down because a rate limiter's own
dependency did. The same trade this codebase already makes for embeddings
(falls back to a local vector), Stripe (falls back to simulated checkout), and
the execution sandbox (an infra failure there is "skipped", never "failed") —
an availability control must never become a new single point of failure.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from redis import asyncio as aioredis

from app.config import settings

log = logging.getLogger(__name__)

_client: aioredis.Redis | None = None


def _get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _client


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int          # seconds until the current window resets


async def check(key: str, *, limit: int, window_seconds: int = 60) -> RateLimitResult:
    """One counter per (key, current window). `key` should already encode the
    tier — two different limits must never share a counter. `limit <= 0`
    means unlimited, the same convention `ApprovalPolicy`'s caps already use.
    """
    if limit <= 0:
        return RateLimitResult(allowed=True, limit=0, remaining=0, retry_after=0)

    now = time.time()
    bucket = int(now) // window_seconds
    redis_key = f"ratelimit:{key}:{bucket}"
    retry_after = window_seconds - (int(now) % window_seconds)

    try:
        client = _get_client()
        count = await client.incr(redis_key)
        if count == 1:
            await client.expire(redis_key, window_seconds)
    except Exception as exc:                      # noqa: BLE001 — see module docstring: fail open
        log.warning("Rate limiter Redis error, failing open: %s", exc)
        return RateLimitResult(allowed=True, limit=limit, remaining=limit, retry_after=0)

    if count > limit:
        return RateLimitResult(allowed=False, limit=limit, remaining=0, retry_after=retry_after)
    return RateLimitResult(allowed=True, limit=limit, remaining=max(0, limit - count),
                            retry_after=retry_after)


async def aclose() -> None:
    """Release the pooled connection. Not required for correctness — mainly
    useful so a test suite doesn't leak open connections across runs.

    Always drops the cached client, even if closing it raises — a redis-asyncio
    connection is bound to the event loop that created it, so a caller that
    tears down and later starts a *different* loop (every `asyncio.run()` does
    this) would otherwise find `_get_client()` handing back a client wired to
    a now-dead loop, wrapped in a `try/finally` that failed to clear it."""
    global _client
    if _client is None:
        return
    client, _client = _client, None
    try:
        await client.aclose()
    except Exception as exc:                        # noqa: BLE001
        log.debug("Ignoring error while closing the rate-limit Redis client: %s", exc)
