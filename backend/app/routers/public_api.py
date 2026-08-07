"""
Public API v1 — API-key authenticated endpoints for CI and customer automation.

This is what makes the platform scriptable: trigger a run from a CI job, poll
its status, approve from a ChatOps bot, pull analytics into an internal
dashboard. Scopes are enforced per key, so a CI token can start runs without
being able to approve its own work — which is the whole point of the gate.

Auth: `Authorization: Bearer adlc_live_…`
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.governance import ApiKey
from app.models.project import Project
from app.models.run import Approval, Run
from app.services import analytics_service, metering_service

router = APIRouter()


class TriggerBody(BaseModel):
    project_id: uuid.UUID
    ticket_id: uuid.UUID | None = None
    pod_id: uuid.UUID | None = None


class ApproveBody(BaseModel):
    decision: str = "approved"
    comment: str | None = None


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_api_key(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> ApiKey:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing API key. Use: Authorization: Bearer adlc_live_…")
    raw = authorization.split(" ", 1)[1].strip()
    hashed = hashlib.sha256(raw.encode()).hexdigest()

    key = db.query(ApiKey).filter(ApiKey.hashed_key == hashed).first()
    if not key:
        raise HTTPException(401, "Invalid API key")
    if key.revoked_at:
        raise HTTPException(401, "API key has been revoked")
    if key.expires_at and key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(401, "API key has expired")

    key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return key


def require_scope(scope: str):
    def _dep(key: ApiKey = Depends(get_api_key)) -> ApiKey:
        if scope not in (key.scopes or []):
            raise HTTPException(403, f"API key is missing the '{scope}' scope")
        return key
    return _dep


def _scoped_projects(db: Session, key: ApiKey) -> list[uuid.UUID]:
    q = db.query(Project)
    rows = (q.filter(Project.org_id == key.org_id).all() if key.org_id
            else q.filter(Project.user_id == key.user_id, Project.org_id.is_(None)).all())
    return [p.id for p in rows]


def _run_out(r: Run) -> dict:
    return {
        "id": str(r.id),
        "project_id": str(r.project_id),
        "ticket_id": str(r.ticket_id) if r.ticket_id else None,
        "status": r.status,
        "current_step": r.current_step,
        "branch": r.branch_name,
        "pr_url": r.pr_url,
        "error": r.error_message,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/whoami")
def whoami(key: ApiKey = Depends(get_api_key)):
    return {"key_name": key.name, "prefix": key.prefix, "scopes": key.scopes,
            "org_id": str(key.org_id) if key.org_id else None}


@router.get("/projects")
def list_projects(
    db: Session = Depends(get_db),
    key: ApiKey = Depends(require_scope("projects:read")),
):
    ids = _scoped_projects(db, key)
    rows = db.query(Project).filter(Project.id.in_(ids)).all() if ids else []
    return [
        {"id": str(p.id), "name": p.name, "repo": p.repo_name,
         "pod_id": str(p.pod_id) if p.pod_id else None, "status": p.status}
        for p in rows
    ]


@router.get("/runs")
def list_runs(
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    key: ApiKey = Depends(require_scope("runs:read")),
):
    ids = _scoped_projects(db, key)
    if not ids:
        return []
    q = db.query(Run).filter(Run.project_id.in_(ids))
    if status:
        q = q.filter(Run.status == status)
    return [_run_out(r) for r in q.order_by(Run.created_at.desc()).limit(limit).all()]


@router.get("/runs/{run_id}")
def get_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    key: ApiKey = Depends(require_scope("runs:read")),
):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run or run.project_id not in _scoped_projects(db, key):
        raise HTTPException(404, "Run not found")
    return _run_out(run)


@router.post("/runs", status_code=201)
def trigger_run(
    body: TriggerBody,
    db: Session = Depends(get_db),
    key: ApiKey = Depends(require_scope("runs:write")),
):
    """Start a run from CI. Quota is enforced here, not just in the UI."""
    project = db.query(Project).filter(Project.id == body.project_id).first()
    if not project or project.id not in _scoped_projects(db, key):
        raise HTTPException(404, "Project not found")

    pod_id = body.pod_id or project.pod_id
    if not pod_id:
        raise HTTPException(422, "No pod configured for this project")

    quota = metering_service.check_quota(db, project.user_id, project.org_id)
    if not quota.allowed:
        raise HTTPException(402, quota.reason or "Plan limit reached")

    run = Run(project_id=project.id, ticket_id=body.ticket_id, pod_id=pod_id,
              status="queued", triggered_by=key.user_id)
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        from app.tasks.run_tasks import trigger_run_until_approval
        trigger_run_until_approval.delay(str(run.id))
    except Exception as exc:
        run.status = "failed"
        run.error_message = f"Failed to dispatch task: {exc}"
        db.commit()

    return _run_out(run)


@router.post("/runs/{run_id}/approve")
def approve_run(
    run_id: uuid.UUID,
    body: ApproveBody,
    db: Session = Depends(get_db),
    key: ApiKey = Depends(require_scope("runs:approve")),
):
    """
    Approve or request changes programmatically (ChatOps, a change-management
    system). Deliberately a separate scope from `runs:write`: a CI token that can
    trigger work must not be able to wave its own work through.
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run or run.project_id not in _scoped_projects(db, key):
        raise HTTPException(404, "Run not found")
    if run.status != "awaiting_approval":
        raise HTTPException(400, f"Run is not awaiting approval (status: {run.status})")
    if body.decision not in ("approved", "changes_requested"):
        raise HTTPException(422, "decision must be 'approved' or 'changes_requested'")

    db.add(Approval(run_id=run.id, reviewer_id=key.user_id,
                    decision=body.decision,
                    comment=body.comment or f"via API key {key.prefix}"))
    db.commit()

    try:
        from app.tasks.run_tasks import resume_after_approval
        resume_after_approval.delay(str(run.id), body.decision, body.comment)
    except Exception as exc:
        raise HTTPException(503, f"Could not dispatch resume task: {exc}")

    db.refresh(run)
    return _run_out(run)


@router.get("/analytics/summary")
def analytics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    key: ApiKey = Depends(require_scope("analytics:read")),
):
    return analytics_service.summary(db, _scoped_projects(db, key), days=days)
