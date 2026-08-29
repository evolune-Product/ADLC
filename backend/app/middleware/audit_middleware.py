"""
Starlette middleware that auto-logs every successful mutation
(POST / PUT / PATCH / DELETE with 2xx response) to the audit_logs table.
Failures are silently swallowed so audit errors never break the API.
"""
from __future__ import annotations

import re
import uuid
import logging

from jose import jwt, JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.database import SessionLocal
from app.models.audit import AuditLog

log = logging.getLogger(__name__)

AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

_SKIP_PATHS = {"/health", "/"}

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I
)

# (path_regex, entity_type, fixed_verb | None)
# First match wins; fixed_verb overrides the HTTP-method verb default.
_ENTITY_PATTERNS: list[tuple[re.Pattern, str, str | None]] = [
    (re.compile(r"^/runs/[^/]+/approve"),            "run",        "approved"),
    (re.compile(r"^/runs/[^/]+/cancel"),             "run",        "cancelled"),
    (re.compile(r"^/runs/[^/]+/retry"),              "run",        "retried"),
    (re.compile(r"^/runs"),                          "run",        None),
    (re.compile(r"^/projects/[^/]+/tickets/[^/]+/sync"), "ticket", "synced"),
    (re.compile(r"^/projects/[^/]+/tickets"),        "ticket",     None),
    (re.compile(r"^/projects/[^/]+/archive"),        "project",    "archived"),
    (re.compile(r"^/projects"),                      "project",    None),
    (re.compile(r"^/pods"),                          "pod",        None),
    (re.compile(r"^/agents"),                        "agent",      None),
    (re.compile(r"^/skills"),                        "skill",      None),
    (re.compile(r"^/connections"),                   "connection", None),
    (re.compile(r"^/settings"),                      "settings",   "updated"),
    (re.compile(r"^/auth/register"),                 "user",       "registered"),
    (re.compile(r"^/auth/login"),                    "user",       "logged_in"),
]

_METHOD_VERB: dict[str, str] = {
    "POST":   "created",
    "PUT":    "updated",
    "PATCH":  "updated",
    "DELETE": "deleted",
}


def _action_and_entity(method: str, path: str) -> tuple[str, str | None]:
    for pattern, entity_type, fixed_verb in _ENTITY_PATTERNS:
        if pattern.match(path):
            verb = fixed_verb or _METHOD_VERB.get(method, "mutated")
            return f"{entity_type}.{verb}", entity_type
    return f"api.{method.lower()}", None


def _first_uuid_in_path(path: str) -> uuid.UUID | None:
    m = _UUID_RE.search(path)
    if m:
        try:
            return uuid.UUID(m.group())
        except ValueError:
            pass
    return None


def _user_id_from_request(request: Request) -> uuid.UUID | None:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(auth[7:], settings.jwt_secret, algorithms=["HS256"])
        sub = payload.get("sub")
        return uuid.UUID(sub) if sub else None
    except (JWTError, ValueError):
        return None


def _org_id_from_request(request: Request) -> uuid.UUID | None:
    """Best-effort org tag for the row, from the same `X-Org-ID` header every
    org-scoped router already requires. Not itself an authorization check —
    a 2xx response on an org-scoped route already means `get_optional_org`
    validated the caller is a member of this org; a non-org route simply
    leaves this column null."""
    raw = request.headers.get("x-org-id")
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if request.method not in AUDIT_METHODS:
            return response

        path = request.url.path
        if path in _SKIP_PATHS or path.startswith("/socket.io"):
            return response

        if not (200 <= response.status_code < 300):
            return response

        try:
            action, entity_type = _action_and_entity(request.method, path)
            org_id = _org_id_from_request(request)
            db = SessionLocal()
            try:
                db.add(AuditLog(
                    user_id=_user_id_from_request(request),
                    action=action,
                    entity_type=entity_type,
                    entity_id=_first_uuid_in_path(path),
                    org_id=org_id,
                    metadata_={
                        "method": request.method,
                        "path":   path,
                        "status": response.status_code,
                    },
                ))
                db.commit()
            finally:
                db.close()
        except Exception:
            log.debug("Audit log write failed (non-fatal)", exc_info=True)

        return response
