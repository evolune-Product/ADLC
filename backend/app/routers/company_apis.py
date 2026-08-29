"""
Company APIs router — CRUD for the BYO API integration registry (step 12),
plus the two live actions: `/test` (connectivity check) and
`/endpoints/{id}/call` (the real outbound call, gated harder than everything
else here — see `_require_call_admin`).

Encrypted fields are masked on read, exactly like `ModelCredential` in
`integrations.py`: `mask()`/`has_key`-shaped output, never the secret itself.

Domain: engineering. A `CompanyApi` is access to a system the pipeline can
call, the same category `integrations.py` puts plugin connections in — not
billing (no spend happens here directly) and not "anyone with can_write"
(an unscoped writer connecting an arbitrary internal API with stored
credentials is exactly the surface `is_domain_admin` gates elsewhere).
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company_api import AUTH_TYPES, METHODS, CompanyApi, CompanyApiEndpoint
from app.models.integration import mask
from app.models.user import User
from app.routers._helpers import OrgContext, get_optional_org, is_domain_admin
from app.routers.auth import get_current_user
from app.services import company_api_service
from app.services.company_api_service import SUPPORTED_AUTH_TYPES, CompanyApiError
from app.services.encryption import encrypt_token

router = APIRouter()


def _require_engineering_admin(org_ctx: Optional[OrgContext]) -> None:
    """Creating/editing/deleting a CompanyApi (and its stored credentials) is
    the same authority level as connecting a plugin — see
    `integrations.py::_require_engineering_admin`, duplicated in spirit
    rather than imported because the two routers deliberately do not depend
    on each other."""
    if org_ctx and not is_domain_admin(org_ctx, "engineering"):
        raise HTTPException(
            status_code=403,
            detail="Only owners, admins and engineering leads can manage company API connections",
        )


def _require_call_admin(org_ctx: Optional[OrgContext]) -> None:
    """Actually invoking an endpoint is a meaningfully riskier action than
    configuring one — it makes a real outbound call, potentially with a
    stored secret, to wherever the customer pointed it. Gated the same as
    creation/deletion (engineering-domain admin) rather than opened to every
    writer, on top of the ToolGrant allow-list check inside the service
    layer itself."""
    if org_ctx and not is_domain_admin(org_ctx, "engineering"):
        raise HTTPException(
            status_code=403,
            detail="Only owners, admins and engineering leads can call a company API endpoint",
        )


def _scope(current_user: User, org_ctx: Optional[OrgContext]):
    from sqlalchemy import and_
    if org_ctx:
        return CompanyApi.organization_id == org_ctx.org_id
    # CompanyApi is org-scoped only — no personal-workspace shape, since a
    # BYO API registry with credentials belongs to a company, not a solo
    # user's private workspace. Mirrors the "needs an org" pattern
    # `require_org_role` already expresses elsewhere.
    raise HTTPException(status_code=400, detail="Company APIs require an org context (X-Org-ID header)")


# ── Bodies ──────────────────────────────────────────────────────────────────

class CompanyApiBody(BaseModel):
    name: str
    description: str | None = None
    base_url: str
    auth_type: str = "none"
    # api_key: {"header": "...", "value": "..."} plaintext value in, encrypted at rest
    # bearer:  {"token": "..."}
    # basic:   {"username": "...", "password": "..."}
    auth_config: dict = Field(default_factory=dict)
    default_headers: dict | None = None
    timeout_seconds: int = 20
    retry_count: int = 0
    status: str = "active"


class CompanyApiEndpointBody(BaseModel):
    name: str
    path: str
    method: str = "GET"
    description: str | None = None
    request_schema: dict | None = None
    response_schema: dict | None = None


class CallBody(BaseModel):
    body: dict | None = None
    path_params: dict | None = None
    agent_id: uuid.UUID | None = None
    workflow_id: uuid.UUID | None = None


# ── output shaping ───────────────────────────────────────────────────────────

_SECRET_FIELDS = {"value", "token", "password"}


def _mask_auth_config(auth_type: str, cfg: dict) -> dict:
    """Same convention as ModelCredential: never return the encrypted or raw
    secret, only a presence flag and (where meaningful) a masked hint."""
    if not cfg:
        return {}
    out: dict = {}
    for k, v in cfg.items():
        if k in _SECRET_FIELDS:
            out[k] = None
            out[f"{k}_set"] = bool(v)
        else:
            out[k] = v  # e.g. "header", "username" — not secret
    return out


def _api_out(api: CompanyApi) -> dict:
    return {
        "id": str(api.id),
        "name": api.name,
        "description": api.description,
        "base_url": api.base_url,
        "auth_type": api.auth_type,
        "auth_config": _mask_auth_config(api.auth_type, api.auth_config or {}),
        "default_headers": api.default_headers,
        "timeout_seconds": api.timeout_seconds,
        "retry_count": api.retry_count,
        "status": api.status,
        "created_at": api.created_at.isoformat() if api.created_at else None,
        "updated_at": api.updated_at.isoformat() if api.updated_at else None,
        "endpoint_count": len(api.endpoints or []),
    }


def _endpoint_out(e: CompanyApiEndpoint) -> dict:
    return {
        "id": str(e.id),
        "company_api_id": str(e.company_api_id),
        "name": e.name,
        "path": e.path,
        "method": e.method,
        "description": e.description,
        "request_schema": e.request_schema,
        "response_schema": e.response_schema,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _encrypt_auth_config(auth_type: str, cfg: dict, existing: dict | None) -> dict:
    """Encrypt whatever secret field this auth_type carries. An omitted
    secret on an update keeps the existing encrypted value — same "blank
    means keep it" rule as ModelCredential/plugin connections, since the API
    can never show a stored secret back for the caller to resend."""
    existing = existing or {}
    cfg = dict(cfg or {})
    for field in _SECRET_FIELDS:
        if field in cfg and cfg[field]:
            cfg[field] = encrypt_token(str(cfg[field]))
        elif field in existing:
            cfg[field] = existing[field]
    return cfg


def _get_api_or_404(db: Session, api_id: uuid.UUID, org_ctx: OrgContext) -> CompanyApi:
    api = (
        db.query(CompanyApi)
        .filter(CompanyApi.id == api_id, CompanyApi.organization_id == org_ctx.org_id)
        .first()
    )
    if not api:
        raise HTTPException(status_code=404, detail="Company API not found")
    return api


# ═══ CompanyApi CRUD ═══════════════════════════════════════════════════════

@router.get("/company-apis")
def list_company_apis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _scope(current_user, org_ctx)  # raises if no org context
    rows = db.query(CompanyApi).filter(CompanyApi.organization_id == org_ctx.org_id).all()
    return {"company_apis": [_api_out(a) for a in rows]}


@router.post("/company-apis", status_code=status.HTTP_201_CREATED)
def create_company_api(
    body: CompanyApiBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _scope(current_user, org_ctx)
    _require_engineering_admin(org_ctx)

    if body.auth_type not in AUTH_TYPES:
        raise HTTPException(status_code=422, detail=f"auth_type must be one of {AUTH_TYPES}")
    if body.auth_type not in SUPPORTED_AUTH_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"auth_type '{body.auth_type}' is accepted by the schema for future use "
                   f"but has no implemented flow yet — use one of {sorted(SUPPORTED_AUTH_TYPES)}",
        )
    if body.status not in ("active", "disabled"):
        raise HTTPException(status_code=422, detail="status must be 'active' or 'disabled'")

    api = CompanyApi(
        organization_id=org_ctx.org_id,
        name=body.name,
        description=body.description,
        base_url=body.base_url,
        auth_type=body.auth_type,
        auth_config=_encrypt_auth_config(body.auth_type, body.auth_config, None),
        default_headers=body.default_headers,
        timeout_seconds=body.timeout_seconds,
        retry_count=body.retry_count,
        created_by=current_user.id,
        status=body.status,
    )
    db.add(api)
    db.commit()
    db.refresh(api)
    return _api_out(api)


@router.get("/company-apis/{api_id}")
def get_company_api(
    api_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _scope(current_user, org_ctx)
    return _api_out(_get_api_or_404(db, api_id, org_ctx))


@router.put("/company-apis/{api_id}")
def update_company_api(
    api_id: uuid.UUID,
    body: CompanyApiBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _scope(current_user, org_ctx)
    _require_engineering_admin(org_ctx)
    api = _get_api_or_404(db, api_id, org_ctx)

    if body.auth_type not in AUTH_TYPES:
        raise HTTPException(status_code=422, detail=f"auth_type must be one of {AUTH_TYPES}")
    if body.auth_type not in SUPPORTED_AUTH_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"auth_type '{body.auth_type}' is accepted by the schema for future use "
                   f"but has no implemented flow yet — use one of {sorted(SUPPORTED_AUTH_TYPES)}",
        )

    api.name = body.name
    api.description = body.description
    api.base_url = body.base_url
    existing_cfg = api.auth_config if api.auth_type == body.auth_type else None
    api.auth_type = body.auth_type
    api.auth_config = _encrypt_auth_config(body.auth_type, body.auth_config, existing_cfg)
    api.default_headers = body.default_headers
    api.timeout_seconds = body.timeout_seconds
    api.retry_count = body.retry_count
    if body.status in ("active", "disabled"):
        api.status = body.status

    db.commit()
    db.refresh(api)
    return _api_out(api)


@router.delete("/company-apis/{api_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_api(
    api_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _scope(current_user, org_ctx)
    _require_engineering_admin(org_ctx)
    api = _get_api_or_404(db, api_id, org_ctx)
    db.delete(api)
    db.commit()


@router.post("/company-apis/{api_id}/test")
def test_company_api(
    api_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _scope(current_user, org_ctx)
    _get_api_or_404(db, api_id, org_ctx)  # 404s before touching the service layer
    return company_api_service.test_connection(db, api_id, org_ctx.org_id)


# ═══ CompanyApiEndpoint CRUD ═════════════════════════════════════════════════

@router.get("/company-apis/{api_id}/endpoints")
def list_endpoints(
    api_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _scope(current_user, org_ctx)
    api = _get_api_or_404(db, api_id, org_ctx)
    return {"endpoints": [_endpoint_out(e) for e in api.endpoints]}


@router.post("/company-apis/{api_id}/endpoints", status_code=status.HTTP_201_CREATED)
def create_endpoint(
    api_id: uuid.UUID,
    body: CompanyApiEndpointBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _scope(current_user, org_ctx)
    _require_engineering_admin(org_ctx)
    api = _get_api_or_404(db, api_id, org_ctx)

    if body.method not in METHODS:
        raise HTTPException(status_code=422, detail=f"method must be one of {METHODS}")

    endpoint = CompanyApiEndpoint(
        company_api_id=api.id,
        name=body.name,
        path=body.path,
        method=body.method,
        description=body.description,
        request_schema=body.request_schema,
        response_schema=body.response_schema,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return _endpoint_out(endpoint)


def _get_endpoint_or_404(db: Session, api_id: uuid.UUID, endpoint_id: uuid.UUID, org_ctx: OrgContext) -> CompanyApiEndpoint:
    api = _get_api_or_404(db, api_id, org_ctx)  # tenant check
    endpoint = (
        db.query(CompanyApiEndpoint)
        .filter(CompanyApiEndpoint.id == endpoint_id, CompanyApiEndpoint.company_api_id == api.id)
        .first()
    )
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return endpoint


@router.put("/company-apis/{api_id}/endpoints/{endpoint_id}")
def update_endpoint(
    api_id: uuid.UUID,
    endpoint_id: uuid.UUID,
    body: CompanyApiEndpointBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _scope(current_user, org_ctx)
    _require_engineering_admin(org_ctx)
    endpoint = _get_endpoint_or_404(db, api_id, endpoint_id, org_ctx)

    if body.method not in METHODS:
        raise HTTPException(status_code=422, detail=f"method must be one of {METHODS}")

    endpoint.name = body.name
    endpoint.path = body.path
    endpoint.method = body.method
    endpoint.description = body.description
    endpoint.request_schema = body.request_schema
    endpoint.response_schema = body.response_schema
    db.commit()
    db.refresh(endpoint)
    return _endpoint_out(endpoint)


@router.delete("/company-apis/{api_id}/endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_endpoint(
    api_id: uuid.UUID,
    endpoint_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _scope(current_user, org_ctx)
    _require_engineering_admin(org_ctx)
    endpoint = _get_endpoint_or_404(db, api_id, endpoint_id, org_ctx)
    db.delete(endpoint)
    db.commit()


@router.post("/company-apis/{api_id}/endpoints/{endpoint_id}/call")
def call_endpoint(
    api_id: uuid.UUID,
    endpoint_id: uuid.UUID,
    body: CallBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Make the real outbound call. Gated behind `_require_call_admin` — this is
    the single most consequential action in this router, capable of hitting
    an arbitrary customer-configured host with stored credentials — on top of
    the ToolGrant allow-list check `company_api_service.call_endpoint` itself
    performs for the given agent/workflow identity.
    """
    _scope(current_user, org_ctx)
    _require_call_admin(org_ctx)
    _get_endpoint_or_404(db, api_id, endpoint_id, org_ctx)  # tenant + existence check

    try:
        return company_api_service.call_endpoint(
            db, api_id, endpoint_id, org_ctx.org_id,
            body=body.body, path_params=body.path_params,
            agent_id=body.agent_id, workflow_id=body.workflow_id,
        )
    except CompanyApiError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
