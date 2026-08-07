"""
Notifications router — the bell, the preferences, and the Slack test button.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notification import Notification, NotificationSetting
from app.models.user import User
from app.routers._helpers import OrgContext, get_optional_org
from app.routers.auth import get_current_user
from app.services import slack_service

router = APIRouter()


class SettingsBody(BaseModel):
    email_enabled: bool | None = None
    slack_enabled: bool | None = None
    slack_webhook_url: str | None = None
    digest_enabled: bool | None = None
    events: list[str] | None = None


class SlackTestBody(BaseModel):
    webhook_url: str


def _out(n: Notification) -> dict:
    return {
        "id": str(n.id),
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "link": n.link,
        "severity": n.severity,
        "payload": n.payload,
        "read": n.read_at is not None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("")
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.read_at.is_(None))
    rows = q.order_by(Notification.created_at.desc()).limit(limit).all()
    unread = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.read_at.is_(None))
        .count()
    )
    return {"notifications": [_out(n) for n in rows], "unread_count": unread}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not n:
        raise HTTPException(404, "Notification not found")
    n.read_at = n.read_at or datetime.now(timezone.utc)
    db.commit()
    return _out(n)


@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.read_at.is_(None))
        .update({Notification.read_at: now}, synchronize_session=False)
    )
    db.commit()
    return {"marked_read": updated}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.id == notification_id, Notification.user_id == current_user.id
    ).delete()
    db.commit()


# ── Preferences ───────────────────────────────────────────────────────────────

def _get_settings(db: Session, user_id, org_id) -> NotificationSetting:
    row = (
        db.query(NotificationSetting)
        .filter(NotificationSetting.user_id == user_id, NotificationSetting.org_id == org_id)
        .first()
    )
    if not row:
        row = NotificationSetting(user_id=user_id, org_id=org_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    s = _get_settings(db, current_user.id, org_ctx.org_id if org_ctx else None)
    return {
        "email_enabled": s.email_enabled,
        "slack_enabled": s.slack_enabled,
        "slack_webhook_configured": bool(s.slack_webhook_url),
        "slack_webhook_url": s.slack_webhook_url,
        "digest_enabled": s.digest_enabled,
        "events": s.events or [],
        "available_events": [
            "run.awaiting_approval", "run.completed", "run.failed",
            "policy.blocked", "quota.exceeded", "member.joined",
        ],
    }


@router.put("/settings")
def update_settings(
    body: SettingsBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    s = _get_settings(db, current_user.id, org_ctx.org_id if org_ctx else None)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return {"updated": True, "slack_enabled": s.slack_enabled, "email_enabled": s.email_enabled}


@router.post("/test-slack")
def test_slack(body: SlackTestBody):
    ok = slack_service.test(body.webhook_url)
    if not ok:
        raise HTTPException(400, "Slack rejected the test message — check the webhook URL")
    return {"delivered": True}
