"""
Applies rate_limit_service to every request. Three tiers, chosen by path:

  auth     /auth/login, /auth/register — the strictest, always IP-keyed. There
           is no credential yet for an attacker at this stage, which is
           exactly the tier that stops credential stuffing.
  api      /v1/* (public API) and /mcp — the metered, cost-bearing surface a
           leaked key or a runaway CI script can hammer.
  default  everything else — a generous floor so ordinary use is unaffected.

Runs before the route handler regardless of where it sits relative to the
other middleware added in main.py — Starlette dispatches all BaseHTTPMiddleware
before the endpoint either way, so getting this ahead of AuditMiddleware or
CORS is a nice-to-have (fewer wasted DB writes on a request about to be
rejected), never a correctness requirement.
"""
from __future__ import annotations

import hashlib

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.services import rate_limit_service

_AUTH_PATHS = ("/auth/login", "/auth/register")
_METERED_PREFIXES = ("/v1/", "/mcp")


def client_ip(request: Request) -> str:
    # nginx is the only thing between the internet and this container in
    # every deployment topology this repo ships — the same trust posture
    # AuditMiddleware already takes on the X-Org-ID header it reads unchecked.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _bearer_identity(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    # Hashed, not stored raw, and truncated — this is a rate-limit bucket key,
    # not a credential lookup, so it does not need to be reversible or the
    # full digest. Works uniformly for a JWT or an adlc_live_… API key without
    # this middleware having to parse or validate either.
    return "tok:" + hashlib.sha256(token.encode()).hexdigest()[:24]


def resolve_tier(path: str) -> tuple[str, int, int]:
    """(tier name, requests per window, window seconds)."""
    if path in _AUTH_PATHS:
        return "auth", settings.rate_limit_auth_per_minute, 60
    if path.startswith(_METERED_PREFIXES):
        return "api", settings.rate_limit_api_per_minute, 60
    return "default", settings.rate_limit_default_per_minute, 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled:
            return await call_next(request)

        tier, limit, window = resolve_tier(request.url.path)
        # auth is always IP-keyed, even if a (stale/invalid) bearer token is
        # present — the whole point of this tier is defending the moment
        # before a caller has a valid credential.
        identity = ("ip:" + client_ip(request)) if tier == "auth" else (
            _bearer_identity(request) or ("ip:" + client_ip(request))
        )

        result = await rate_limit_service.check(f"{tier}:{identity}", limit=limit, window_seconds=window)
        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded ({result.limit}/min). "
                                    f"Try again in {result.retry_after}s."},
                headers={"Retry-After": str(result.retry_after)},
            )

        response = await call_next(request)
        if result.limit:
            response.headers["X-RateLimit-Limit"] = str(result.limit)
            response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        return response
