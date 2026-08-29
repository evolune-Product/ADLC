import uuid
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv, io

from app.database import get_db
from app.models.audit import AuditLog
from app.routers.auth import get_current_user
from app.routers._helpers import get_optional_org, OrgContext
from app.models.user import User

router = APIRouter()


def _log_out(log: AuditLog) -> dict:
    return {
        "id":            str(log.id),
        "user_id":       str(log.user_id) if log.user_id else None,
        "action":        log.action,
        "entity_type":   log.entity_type,
        "entity_id":     str(log.entity_id) if log.entity_id else None,
        "org_id":        str(log.org_id) if log.org_id else None,
        "department_id": str(log.department_id) if log.department_id else None,
        "team_id":       str(log.team_id) if log.team_id else None,
        "metadata":      log.metadata_,
        "created_at":    log.created_at.isoformat() if log.created_at else None,
    }


def _build_audit_query(db: Session, current_user: User, org_ctx: Optional[OrgContext]):
    """
    In org context: show all org members' audit logs — matched on `org_id`
    where the row carries one (every row written since step 19: the HTTP
    middleware from the X-Org-ID header, event-sourced rows explicitly), and
    falls back to the user-membership match for older/HTTP rows with no
    org_id so nothing written before this migration disappears from the view.
    In personal context: show only the current user's logs.
    """
    if org_ctx:
        from app.models.organization import OrgMember
        member_ids = db.query(OrgMember.user_id).filter(
            OrgMember.org_id == org_ctx.org_id
        ).subquery()
        return db.query(AuditLog).filter(
            (AuditLog.org_id == org_ctx.org_id) | AuditLog.user_id.in_(member_ids)
        )
    return db.query(AuditLog).filter(AuditLog.user_id == current_user.id)


def _apply_common_filters(
    q, *, action, entity_type, department_id, team_id, since, until,
):
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if department_id:
        q = q.filter(AuditLog.department_id == department_id)
    if team_id:
        q = q.filter(AuditLog.team_id == team_id)
    if since:
        since_utc = since.replace(tzinfo=timezone.utc) if since.tzinfo is None else since
        q = q.filter(AuditLog.created_at >= since_utc)
    if until:
        until_utc = until.replace(tzinfo=timezone.utc) if until.tzinfo is None else until
        q = q.filter(AuditLog.created_at <= until_utc)
    return q


@router.get("")
def list_audit_logs(
    action: Optional[str]      = Query(None, description="Filter by action substring"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    since: Optional[datetime]  = Query(None, description="ISO-8601 start timestamp"),
    limit: int                 = Query(50, le=200),
    skip: int                  = Query(0, ge=0),
    db: Session                = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    q = _build_audit_query(db, current_user, org_ctx)
    q = _apply_common_filters(
        q, action=action, entity_type=entity_type, department_id=None, team_id=None,
        since=since, until=None,
    )

    total = q.count()
    logs  = q.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip":  skip,
        "limit": limit,
        "items": [_log_out(l) for l in logs],
    }


@router.get("/timeline")
def get_audit_timeline(
    action: Optional[str]         = Query(None, description="Filter by action substring"),
    entity_type: Optional[str]    = Query(None, description="Filter by entity type"),
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by department"),
    team_id: Optional[uuid.UUID]  = Query(None, description="Filter by team"),
    since: Optional[datetime]     = Query(None, description="ISO-8601 start timestamp"),
    until: Optional[datetime]     = Query(None, description="ISO-8601 end timestamp"),
    limit: int                    = Query(100, le=500),
    skip: int                     = Query(0, ge=0),
    db: Session                   = Depends(get_db),
    current_user: User            = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Company OS step 19 — the unified, filterable activity timeline.

    Same `audit_logs` table `GET /audit` already reads, richer filters
    (department, team, an end of the date range as well as a start). Not a
    second data source the frontend has to merge: every row this returns
    already came from either AuditMiddleware (an HTTP mutation) or
    `app.services.audit_service.record()` (a workflow-execution status
    transition, a workflow-approval-policy decision, or a real CompanyApi/
    ToolGrant invocation — see workflow_engine.py, policy_service.py and
    company_api_service.py). One table, one query surface, one list.
    """
    if department_id or team_id:
        # Both are org-scoped concepts — filtering by one outside an org
        # context (personal workspace) can never match a row, so make that
        # explicit rather than silently returning an empty page.
        if org_ctx is None:
            raise HTTPException(status_code=400, detail="department_id/team_id filters require an org context (X-Org-ID header)")

    q = _build_audit_query(db, current_user, org_ctx)
    q = _apply_common_filters(
        q, action=action, entity_type=entity_type,
        department_id=department_id, team_id=team_id, since=since, until=until,
    )

    total = q.count()
    logs  = q.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip":  skip,
        "limit": limit,
        "items": [_log_out(l) for l in logs],
    }


@router.get("/export")
def export_audit_csv(
    action: Optional[str]      = Query(None),
    entity_type: Optional[str] = Query(None),
    db: Session                = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """Download audit log as CSV."""
    q = _build_audit_query(db, current_user, org_ctx)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    logs = q.order_by(AuditLog.created_at.desc()).limit(5000).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "action", "entity_type", "entity_id", "created_at"])
    for log in logs:
        writer.writerow([
            str(log.id),
            log.action,
            log.entity_type or "",
            str(log.entity_id) if log.entity_id else "",
            log.created_at.isoformat() if log.created_at else "",
        ])
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )
