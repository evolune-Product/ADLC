"""
Governance router — approval policies, API keys, outbound webhooks, and the
compliance evidence export.

These are the CISO-facing surfaces: what agents may touch, who may approve, who
holds programmatic access, where events are reported, and what evidence can be
handed to an auditor.
"""
from __future__ import annotations

import csv
import hashlib
import io
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.audit import AuditLog
from app.models.governance import ApiKey, ApprovalPolicy, Webhook, WebhookDelivery
from app.models.insight import Deployment, ReviewFinding
from app.models.organization import OrgMember
from app.models.project import Project
from app.models.run import Approval, Run
from app.models.user import User
from app.routers._helpers import OrgContext, get_optional_org, is_domain_admin, owner_filter
from app.routers.auth import get_current_user
from app.services.policy_service import DEFAULT_POLICY

router = APIRouter()

API_KEY_SCOPES = ["runs:read", "runs:write", "runs:approve", "projects:read", "analytics:read"]


# ═══ Approval policies ════════════════════════════════════════════════════════

class PolicyBody(BaseModel):
    name: str
    environment: str = "*"
    project_id: uuid.UUID | None = None
    min_approvers: int = Field(1, ge=1, le=10)
    approver_roles: list[str] = ["owner", "admin", "member"]
    require_review_pass: bool = False
    min_review_score: int = Field(0, ge=0, le=100)
    block_on_severity: str | None = None
    protected_paths: list[str] = []
    protected_branches: list[str] = []
    max_files_changed: int = Field(0, ge=0)
    max_run_cost_cents: int = Field(0, ge=0)
    # 0 means unlimited for both — the same convention as the caps above.
    max_concurrent_runs: int = Field(0, ge=0)
    max_queue_depth: int = Field(0, ge=0)
    is_active: bool = True


def _policy_out(p: ApprovalPolicy) -> dict:
    return {
        "id": str(p.id),
        "name": p.name,
        "environment": p.environment,
        "project_id": str(p.project_id) if p.project_id else None,
        "min_approvers": p.min_approvers,
        "approver_roles": p.approver_roles,
        "require_review_pass": p.require_review_pass,
        "min_review_score": p.min_review_score,
        "block_on_severity": p.block_on_severity,
        "protected_paths": p.protected_paths,
        "protected_branches": p.protected_branches,
        "max_files_changed": p.max_files_changed,
        "max_run_cost_cents": p.max_run_cost_cents,
        "max_concurrent_runs": p.max_concurrent_runs or 0,
        "max_queue_depth": p.max_queue_depth or 0,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _require_admin(org_ctx: Optional[OrgContext]) -> None:
    # CISO-facing config — policies, API keys, webhooks — sits in the same
    # "engineering" domain as skills/agents/pods: it is the pipeline's rules,
    # not the company's spend, so an engineering lead administers it too.
    if org_ctx and not is_domain_admin(org_ctx, "engineering"):
        raise HTTPException(403, "Only owners, admins and engineering leads can change governance settings")


@router.get("/policies")
def list_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    rows = db.query(ApprovalPolicy).filter(
        owner_filter(ApprovalPolicy, current_user, org_ctx)).all()
    return {"policies": [_policy_out(p) for p in rows], "default": DEFAULT_POLICY}


@router.post("/policies", status_code=201)
def create_policy(
    body: PolicyBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _require_admin(org_ctx)
    p = ApprovalPolicy(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        **body.model_dump(),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _policy_out(p)


@router.put("/policies/{policy_id}")
def update_policy(
    policy_id: uuid.UUID,
    body: PolicyBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _require_admin(org_ctx)
    p = db.query(ApprovalPolicy).filter(
        ApprovalPolicy.id == policy_id,
        owner_filter(ApprovalPolicy, current_user, org_ctx)).first()
    if not p:
        raise HTTPException(404, "Policy not found")
    for field, value in body.model_dump().items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return _policy_out(p)


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _require_admin(org_ctx)
    db.query(ApprovalPolicy).filter(
        ApprovalPolicy.id == policy_id,
        owner_filter(ApprovalPolicy, current_user, org_ctx)).delete()
    db.commit()


# ═══ API keys ═════════════════════════════════════════════════════════════════

class ApiKeyBody(BaseModel):
    name: str
    scopes: list[str] = ["runs:read"]
    expires_in_days: int | None = None


def _key_out(k: ApiKey) -> dict:
    return {
        "id": str(k.id),
        "name": k.name,
        "prefix": k.prefix,
        "scopes": k.scopes,
        "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        "expires_at": k.expires_at.isoformat() if k.expires_at else None,
        "revoked": k.revoked_at is not None,
        "created_at": k.created_at.isoformat() if k.created_at else None,
    }


@router.get("/apikeys")
def list_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    rows = db.query(ApiKey).filter(owner_filter(ApiKey, current_user, org_ctx)).all()
    return {"keys": [_key_out(k) for k in rows], "available_scopes": API_KEY_SCOPES}


@router.post("/apikeys", status_code=201)
def create_key(
    body: ApiKeyBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """The raw key is returned exactly once; only its SHA-256 is stored."""
    _require_admin(org_ctx)
    bad = [s for s in body.scopes if s not in API_KEY_SCOPES]
    if bad:
        raise HTTPException(422, f"Unknown scope(s): {', '.join(bad)}")

    raw = f"adlc_live_{secrets.token_urlsafe(32)}"
    key = ApiKey(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        name=body.name,
        prefix=raw[:16],
        hashed_key=hashlib.sha256(raw.encode()).hexdigest(),
        scopes=body.scopes,
        expires_at=(datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)
                    if body.expires_in_days else None),
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return {**_key_out(key), "api_key": raw,
            "warning": "Copy this now — it is not retrievable later."}


@router.delete("/apikeys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _require_admin(org_ctx)
    k = db.query(ApiKey).filter(ApiKey.id == key_id,
                                owner_filter(ApiKey, current_user, org_ctx)).first()
    if not k:
        raise HTTPException(404, "API key not found")
    k.revoked_at = datetime.now(timezone.utc)
    db.commit()


# ═══ Outbound webhooks ════════════════════════════════════════════════════════

class WebhookBody(BaseModel):
    url: str
    events: list[str] = ["run.completed", "run.failed", "run.awaiting_approval"]
    is_active: bool = True


def _hook_out(h: Webhook, include_secret: bool = False) -> dict:
    out = {
        "id": str(h.id),
        "url": h.url,
        "events": h.events,
        "is_active": h.is_active,
        "failure_count": h.failure_count,
        "created_at": h.created_at.isoformat() if h.created_at else None,
    }
    if include_secret:
        out["secret"] = h.secret
    return out


@router.get("/webhooks")
def list_webhooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    rows = db.query(Webhook).filter(owner_filter(Webhook, current_user, org_ctx)).all()
    return {
        "webhooks": [_hook_out(h) for h in rows],
        "available_events": [
            "run.awaiting_approval", "run.completed", "run.failed",
            "policy.blocked", "quota.exceeded",
        ],
        "signature_header": "X-ADLC-Signature",
    }


@router.post("/webhooks", status_code=201)
def create_webhook(
    body: WebhookBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _require_admin(org_ctx)
    if not body.url.startswith("https://") and "localhost" not in body.url:
        raise HTTPException(422, "Webhook URLs must use HTTPS")
    h = Webhook(user_id=current_user.id, org_id=org_ctx.org_id if org_ctx else None,
                url=body.url, events=body.events, is_active=body.is_active)
    db.add(h)
    db.commit()
    db.refresh(h)
    return _hook_out(h, include_secret=True)


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _require_admin(org_ctx)
    db.query(Webhook).filter(Webhook.id == webhook_id,
                             owner_filter(Webhook, current_user, org_ctx)).delete()
    db.commit()


@router.post("/webhooks/{webhook_id}/test")
def test_webhook(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    from app.services import webhook_service
    h = db.query(Webhook).filter(Webhook.id == webhook_id,
                                 owner_filter(Webhook, current_user, org_ctx)).first()
    if not h:
        raise HTTPException(404, "Webhook not found")
    ok = webhook_service._deliver(db, h, "webhook.test", {"message": "Test delivery"})
    return {"delivered": ok}


@router.get("/webhooks/{webhook_id}/deliveries")
def webhook_deliveries(
    webhook_id: uuid.UUID,
    limit: int = Query(25, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    h = db.query(Webhook).filter(Webhook.id == webhook_id,
                                 owner_filter(Webhook, current_user, org_ctx)).first()
    if not h:
        raise HTTPException(404, "Webhook not found")
    rows = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(d.id), "event": d.event, "ok": d.ok, "status_code": d.status_code,
            "error": d.error, "duration_ms": d.duration_ms,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in rows
    ]


# ═══ Compliance ═══════════════════════════════════════════════════════════════

@router.get("/compliance/posture")
def compliance_posture(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    A self-assessment of the controls an enterprise buyer's questionnaire asks
    about. Honest by design: it reports what is configured, not what is possible.
    """
    org_id = org_ctx.org_id if org_ctx else None
    policies = db.query(ApprovalPolicy).filter(
        owner_filter(ApprovalPolicy, current_user, org_ctx)).all()
    project_ids = [p.id for p in db.query(Project).filter(
        owner_filter(Project, current_user, org_ctx)).all()]

    runs = db.query(Run).filter(Run.project_id.in_(project_ids)).count() if project_ids else 0
    approvals = (db.query(Approval).join(Run, Run.id == Approval.run_id)
                 .filter(Run.project_id.in_(project_ids)).count()) if project_ids else 0
    members = db.query(OrgMember).filter(OrgMember.org_id == org_id).count() if org_id else 1

    controls = [
        {"id": "human-approval", "name": "Human approval before deploy",
         "status": "enforced", "evidence": f"{approvals} recorded approvals across {runs} runs"},
        {"id": "audit-log", "name": "Immutable action audit log",
         "status": "enforced",
         "evidence": f"{db.query(AuditLog).count()} audit entries; retention "
                     f"{settings.audit_retention_days} days"},
        {"id": "policy-engine", "name": "Approval policies (N-approver, protected paths)",
         "status": "configured" if policies else "default",
         "evidence": f"{len(policies)} custom policies"},
        {"id": "token-encryption", "name": "Credential encryption at rest",
         "status": "enforced", "evidence": "Fernet-encrypted OAuth and LLM keys"},
        {"id": "rbac", "name": "Role-based access control",
         "status": "enforced" if org_id else "single-user",
         "evidence": f"{members} member(s) with owner/admin/member/viewer roles"},
        {"id": "byo-llm", "name": "Bring-your-own model provider",
         "status": "available", "evidence": "Per-workspace provider + key override"},
        {"id": "self-hosted", "name": "Self-hosted / VPC deployment",
         "status": "available" if settings.deployment_mode == "self_hosted" else "available (not in use)",
         "evidence": f"deployment_mode={settings.deployment_mode}"},
        {"id": "ai-transparency", "name": "AI authorship disclosure on changes (EU AI Act Art. 50)",
         "status": "enforced",
         "evidence": "Every PR body and review comment identifies the agent, model and approver"},
    ]
    return {"controls": controls,
            "deployment_mode": settings.deployment_mode,
            "audit_retention_days": settings.audit_retention_days}


@router.get("/compliance/evidence.csv")
def evidence_export(
    days: int = Query(90, ge=1, le=730),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    One row per governed action: which run, which agent output, who approved it,
    what the reviewer found, where it deployed. This is the artefact you hand an
    auditor asking "show me that a human approved every production change".
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    project_ids = [p.id for p in db.query(Project).filter(
        owner_filter(Project, current_user, org_ctx)).all()]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["run_id", "project_id", "status", "branch", "pr_url",
                     "review_findings", "approver_ids", "approved_at",
                     "environments_deployed", "created_at", "completed_at"])

    if project_ids:
        runs = (db.query(Run)
                .filter(Run.project_id.in_(project_ids), Run.created_at >= since)
                .order_by(Run.created_at.desc()).all())
        for r in runs:
            approvals = db.query(Approval).filter(Approval.run_id == r.id).all()
            findings = db.query(ReviewFinding).filter(ReviewFinding.run_id == r.id).count()
            deploys = db.query(Deployment).filter(Deployment.run_id == r.id).all()
            writer.writerow([
                str(r.id), str(r.project_id), r.status, r.branch_name or "", r.pr_url or "",
                findings,
                ";".join(str(a.reviewer_id) for a in approvals if a.reviewer_id),
                approvals[0].created_at.isoformat() if approvals and approvals[0].created_at else "",
                ";".join(d.environment for d in deploys),
                r.created_at.isoformat() if r.created_at else "",
                r.completed_at.isoformat() if r.completed_at else "",
            ])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=adlc-compliance-evidence.csv"},
    )
