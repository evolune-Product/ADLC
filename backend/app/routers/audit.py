import uuid
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
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
        "id":          str(log.id),
        "user_id":     str(log.user_id) if log.user_id else None,
        "action":      log.action,
        "entity_type": log.entity_type,
        "entity_id":   str(log.entity_id) if log.entity_id else None,
        "metadata":    log.metadata_,
        "created_at":  log.created_at.isoformat() if log.created_at else None,
    }


def _build_audit_query(db: Session, current_user: User, org_ctx: Optional[OrgContext]):
    """
    In org context: show all org members' audit logs.
    In personal context: show only the current user's logs.
    """
    if org_ctx:
        from app.models.organization import OrgMember
        member_ids = db.query(OrgMember.user_id).filter(
            OrgMember.org_id == org_ctx.org_id
        ).subquery()
        return db.query(AuditLog).filter(AuditLog.user_id.in_(member_ids))
    return db.query(AuditLog).filter(AuditLog.user_id == current_user.id)


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
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if since:
        since_utc = since.replace(tzinfo=timezone.utc) if since.tzinfo is None else since
        q = q.filter(AuditLog.created_at >= since_utc)

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
