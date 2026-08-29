"""
BYO API integration registry — the execution path.

`call_endpoint` is what unblocks the workflow engine's `api_call` node
(step 12 of the Company OS spec): a customer configures a `CompanyApi` (base
URL + auth) and one or more `CompanyApiEndpoint`s under it, and this module
is the only place that actually makes the outbound HTTP call.

SSRF — non-negotiable
----------------------
A CompanyApi's `base_url` is customer-supplied and this function calls it
from the server. That is exactly the SSRF primitive `reader_service` and
`plugin_verify` already guard against, so this reuses the same guard rather
than writing a second one: `reader_service._assert_public_url`, gated by
`deployment_mode` the same way `plugin_verify._guard` gates it (private/
loopback/link-local/reserved addresses refused by resolved IP in `cloud`
mode; the guard is off in `self_hosted` mode, where the internal host is the
whole point). Redirects are never followed on a call — `follow_redirects=False`.

Encryption
----------
`auth_config` secrets are Fernet-encrypted with the exact same
`encrypt_token`/`decrypt_token` pair `ModelCredential` and `Connection` use.
Decrypted only here, just-in-time, and never logged or returned.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.company_api import CompanyApi, CompanyApiEndpoint
from app.services.encryption import decrypt_token
from app.services.reader_service import ReadError, _assert_public_url, normalize_url
from app.services.tool_grants import can_use_tool

log = logging.getLogger(__name__)

# Same convention as plugin_verify.VERIFY_TIMEOUT_S — bounded, and never
# trusted blindly from the row (a customer could set an absurd value).
MAX_TIMEOUT_S = 60.0
MAX_RETRIES = 5
MAX_RESPONSE_BYTES = 64 * 1024  # 64KB, per spec — avoid a runaway response

# auth_types the schema accepts (see app/models/company_api.py::AUTH_TYPES)
# minus the ones with no implemented flow yet. The router validates a create/
# update against this set so 'oauth2' fails loudly at creation, not on first call.
SUPPORTED_AUTH_TYPES = {"none", "api_key", "bearer", "basic"}


class CompanyApiError(RuntimeError):
    """Raised for any condition that should stop the call before it reaches
    the network, or that the caller (workflow engine) should surface loudly
    rather than silently swallow."""


def _guard(url: str) -> str:
    """Normalize (scheme/host validation) and, in cloud mode, SSRF-check the
    URL. Returns the normalized URL — callers should request that, not the
    raw one, so a scheme-less or malformed URL never reaches httpx."""
    normalized = normalize_url(url)
    if settings.deployment_mode == "self_hosted":
        return normalized
    _assert_public_url(normalized)
    return normalized


def _load_api(db: Session, company_api_id, org_id) -> CompanyApi:
    api = (
        db.query(CompanyApi)
        .filter(CompanyApi.id == company_api_id, CompanyApi.organization_id == org_id)
        .first()
    )
    if not api:
        raise CompanyApiError("No company API with that id in this organization")
    return api


def _build_auth(api: CompanyApi) -> tuple[dict, httpx.Auth | None]:
    """Decrypt auth_config just-in-time and return (headers, httpx auth)."""
    cfg = api.auth_config or {}
    headers: dict[str, str] = {}
    auth: httpx.Auth | None = None

    if api.auth_type == "none":
        pass
    elif api.auth_type == "api_key":
        header = cfg.get("header") or "X-API-Key"
        value = cfg.get("value")
        if not value:
            raise CompanyApiError("api_key auth is configured with no key stored")
        headers[header] = decrypt_token(value)
    elif api.auth_type == "bearer":
        token = cfg.get("token")
        if not token:
            raise CompanyApiError("bearer auth is configured with no token stored")
        headers["Authorization"] = f"Bearer {decrypt_token(token)}"
    elif api.auth_type == "basic":
        username = cfg.get("username") or ""
        password = cfg.get("password")
        if not password:
            raise CompanyApiError("basic auth is configured with no password stored")
        auth = httpx.BasicAuth(username, decrypt_token(password))
    elif api.auth_type == "oauth2":
        # Documented boundary, not a fake integration — see module docstring
        # in app/models/company_api.py. Fails loudly rather than sending an
        # unauthenticated request that looks like it worked.
        raise CompanyApiError(
            "oauth2 auth_type is accepted by the schema for future use but has "
            "no implemented flow yet — this call cannot be authenticated."
        )
    else:
        raise CompanyApiError(f"Unknown auth_type '{api.auth_type}'")

    return headers, auth


def _check_authorization(
    db: Session, api: CompanyApi, org_id, *, agent_id, department_id, team_id, workflow_id,
) -> None:
    if not can_use_tool(
        db, org_id, company_api_id=api.id,
        agent_id=agent_id, department_id=department_id, team_id=team_id, workflow_id=workflow_id,
    ):
        raise CompanyApiError(
            f"This caller is not on the allow-list for company API '{api.name}' "
            f"(ToolGrant scoping is active for it)."
        )


def call_endpoint(
    db: Session,
    company_api_id,
    endpoint_id,
    org_id,
    *,
    body: dict | None = None,
    path_params: dict | None = None,
    agent_id=None,
    department_id=None,
    team_id=None,
    workflow_id=None,
) -> dict:
    """
    Execute one configured endpoint for real. Returns
    {status_code, body, duration_ms, ok}. Never returns or logs auth_config.

    Raises CompanyApiError for any pre-flight failure (not found, disabled,
    unauthorized, SSRF-guard rejection, unsupported auth). Network-level
    failures after retries are exhausted are also raised as CompanyApiError
    so a workflow `api_call` node fails the execution loudly rather than
    hanging or silently no-opping.
    """
    api = _load_api(db, company_api_id, org_id)  # tenant-scoped load — never cross-org

    if api.status != "active":
        raise CompanyApiError(f"Company API '{api.name}' is disabled")

    endpoint = (
        db.query(CompanyApiEndpoint)
        .filter(CompanyApiEndpoint.id == endpoint_id, CompanyApiEndpoint.company_api_id == api.id)
        .first()
    )
    if not endpoint:
        raise CompanyApiError("No endpoint with that id on this company API")

    _check_authorization(
        db, api, org_id,
        agent_id=agent_id, department_id=department_id, team_id=team_id, workflow_id=workflow_id,
    )

    path = endpoint.path
    for key, value in (path_params or {}).items():
        path = path.replace("{" + key + "}", str(value))

    url = urljoin(api.base_url.rstrip("/") + "/", path.lstrip("/"))
    try:
        url = _guard(url)  # SSRF guard — resolved-IP check, redirects never followed below
    except ReadError as exc:
        raise CompanyApiError(str(exc)) from exc

    headers, auth = _build_auth(api)
    if api.default_headers:
        headers.update(api.default_headers)

    timeout = min(float(api.timeout_seconds or 20), MAX_TIMEOUT_S)
    retries = max(0, min(int(api.retry_count or 0), MAX_RETRIES))

    started = time.monotonic()
    last_exc: Exception | None = None
    response: httpx.Response | None = None

    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        for attempt in range(retries + 1):
            try:
                response = client.request(
                    endpoint.method, url, headers=headers, auth=auth,
                    json=body if body is not None else None,
                )
                break
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_exc = exc
                if attempt < retries:
                    # Bounded backoff, same order of magnitude as plugin_verify's
                    # single-shot convention — this is the only place in the
                    # codebase that retries an outbound call, so it stays simple.
                    time.sleep(min(0.5 * (2 ** attempt), 4.0))
                    continue

    duration_ms = int((time.monotonic() - started) * 1000)

    if response is None:
        raise CompanyApiError(
            f"Could not reach '{api.name}' after {retries + 1} attempt(s): "
            f"{type(last_exc).__name__ if last_exc else 'unknown error'}"
        )

    raw = response.content[:MAX_RESPONSE_BYTES]
    try:
        parsed_body: Any = response.json() if raw else None
    except Exception:
        parsed_body = raw.decode("utf-8", errors="replace")

    return {
        "status_code": response.status_code,
        "ok": 200 <= response.status_code < 300,
        "body": parsed_body,
        "duration_ms": duration_ms,
        "truncated": len(response.content) > MAX_RESPONSE_BYTES,
    }


def test_connection(db: Session, company_api_id, org_id) -> dict:
    """
    Lightweight real connectivity check — same spirit as
    `/providers/credentials/{p}/test`: a real request, not a shrug.

    Makes a bare GET to base_url itself (no endpoint chosen) with the
    configured auth. Any HTTP response at all (even 404/401) proves the host
    is reachable and TLS/DNS work; only a transport-level failure or the SSRF
    guard counts as "unreachable".
    """
    api = _load_api(db, company_api_id, org_id)

    if api.status != "active":
        return {"ok": False, "detail": f"'{api.name}' is disabled"}

    try:
        headers, auth = _build_auth(api)
    except CompanyApiError as exc:
        return {"ok": False, "detail": str(exc)}

    if api.default_headers:
        headers.update(api.default_headers)

    try:
        base_url = _guard(api.base_url)
    except ReadError as exc:
        return {"ok": False, "detail": str(exc)}

    timeout = min(float(api.timeout_seconds or 20), MAX_TIMEOUT_S)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            r = client.get(base_url, headers=headers, auth=auth)
        return {
            "ok": True,
            "detail": f"Reached '{api.name}' — HTTP {r.status_code}",
            "status_code": r.status_code,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except httpx.TimeoutException:
        return {"ok": False, "detail": f"'{api.name}' did not respond within {int(timeout)}s"}
    except httpx.RequestError as exc:
        return {"ok": False, "detail": f"Could not reach '{api.name}': {type(exc).__name__}"}
