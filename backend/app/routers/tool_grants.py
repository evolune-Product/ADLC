"""
Tool grants router — CRUD for `ToolGrant` (step 11), the allow-list that
scopes which agents/departments/teams/workflows may use a connected plugin
or `CompanyApi`. See `app/services/tool_grants.py` for the
default-open-until-scoped semantics this table encodes.

Managing grants is an access-control action — same authority level as
connecting the underlying plugin/CompanyApi in the first place
(engineering-domain admin), not opened to every writer.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.integration import GRANTEE_TYPES, ToolGrant
from app.models.user import User
from app.routers._helpers import OrgContext, get_optional_org, is_domain_admin
from app.routers.auth import get_current_user

router = APIRouter()


def _require_engineering_admin(org_ctx: Optional[OrgContext]) -> None:
    if org_ctx and not is_domain_admin(org_ctx, "engineering"):
        raise HTTPException(
            status_code=403,
            detail="Only owners, admins and engineering leads can manage tool grants",
        )


def _require_org(org_ctx: Optional[OrgContext]) -> OrgContext:
    if not org_ctx:
        raise HTTPException(status_code=400, detail="Tool grants require an org context (X-Org-ID header)")
    return org_ctx


class ToolGrantBody(BaseModel):
    plugin_key: str | None = None
    company_api_id: uuid.UUID | None = None
    grantee_type: str
    grantee_id: uuid.UUID

    @model_validator(mode="after")
    def _exactly_one_target(self):
        if bool(self.plugin_key) == bool(self.company_api_id):
            raise ValueError("Exactly one of plugin_key / company_api_id must be set")
        return self


def _out(g: ToolGrant) -> dict:
    return {
        "id": str(g.id),
        "plugin_key": g.plugin_key,
        "company_api_id": str(g.company_api_id) if g.company_api_id else None,
        "grantee_type": g.grantee_type,
        "grantee_id": str(g.grantee_id),
        "granted_by": str(g.granted_by) if g.granted_by else None,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }


@router.get("/tool-grants")
def list_tool_grants(
    plugin_key: str | None = None,
    company_api_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """List grants, optionally filtered to one plugin or CompanyApi target —
    the shape the settings UI needs to render "who can use this tool"."""
    org_ctx = _require_org(org_ctx)
    q = db.query(ToolGrant).filter(ToolGrant.organization_id == org_ctx.org_id)
    if plugin_key:
        q = q.filter(ToolGrant.plugin_key == plugin_key)
    if company_api_id:
        q = q.filter(ToolGrant.company_api_id == company_api_id)
    return {"tool_grants": [_out(g) for g in q.all()]}


@router.post("/tool-grants", status_code=status.HTTP_201_CREATED)
def create_tool_grant(
    body: ToolGrantBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    _require_engineering_admin(org_ctx)

    if body.grantee_type not in GRANTEE_TYPES:
        raise HTTPException(status_code=422, detail=f"grantee_type must be one of {GRANTEE_TYPES}")

    existing = (
        db.query(ToolGrant)
        .filter(
            ToolGrant.organization_id == org_ctx.org_id,
            ToolGrant.plugin_key == body.plugin_key,
            ToolGrant.company_api_id == body.company_api_id,
            ToolGrant.grantee_type == body.grantee_type,
            ToolGrant.grantee_id == body.grantee_id,
        )
        .first()
    )
    if existing:
        return _out(existing)  # idempotent — re-granting the same tuple is a no-op, not an error

    grant = ToolGrant(
        organization_id=org_ctx.org_id,
        plugin_key=body.plugin_key,
        company_api_id=body.company_api_id,
        grantee_type=body.grantee_type,
        grantee_id=body.grantee_id,
        granted_by=current_user.id,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return _out(grant)


@router.delete("/tool-grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tool_grant(
    grant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    _require_engineering_admin(org_ctx)
    grant = (
        db.query(ToolGrant)
        .filter(ToolGrant.id == grant_id, ToolGrant.organization_id == org_ctx.org_id)
        .first()
    )
    if not grant:
        raise HTTPException(status_code=404, detail="Tool grant not found")
    db.delete(grant)
    db.commit()
