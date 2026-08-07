"""
Notification fan-out — in-app bell, email, Slack, and signed webhooks.

The approval gate is the product's differentiator and it is worthless if the
reviewer never learns their approval is needed: "human approvals routed to
mobile, Slack, email or webhook" is a named primitive of every 2026 agent
control plane. One call here reaches every channel the recipient enabled, and
every delivery failure is swallowed — a broken Slack webhook must never fail a
run.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.models.notification import Notification, NotificationSetting
from app.models.organization import OrgMember
from app.models.user import User
from app.services import email_service, slack_service, webhook_service

log = logging.getLogger(__name__)

SEVERITY_BY_TYPE = {
    "run.awaiting_approval": "warning",
    "run.failed": "critical",
    "run.completed": "info",
    "run.blocked": "warning",
    "quota.exceeded": "warning",
    "quota.warning": "info",
    "policy.blocked": "warning",
    "member.joined": "info",
    "deploy.succeeded": "info",
    "deploy.failed": "critical",
}


def _settings_for(db: Session, user_id, org_id) -> NotificationSetting:
    row = (
        db.query(NotificationSetting)
        .filter(NotificationSetting.user_id == user_id)
        .filter(NotificationSetting.org_id == org_id)
        .first()
    )
    if row:
        return row
    row = NotificationSetting(user_id=user_id, org_id=org_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _wants(prefs: NotificationSetting, event_type: str) -> bool:
    events = prefs.events or []
    return not events or event_type in events


def notify_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    org_id: uuid.UUID | None,
    type: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
    payload: dict | None = None,
) -> Notification:
    """Write the in-app record, then fan out to whichever channels are enabled."""
    note = Notification(
        user_id=user_id,
        org_id=org_id,
        type=type,
        title=title,
        body=body,
        link=link,
        severity=SEVERITY_BY_TYPE.get(type, "info"),
        payload=payload or {},
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    try:
        prefs = _settings_for(db, user_id, org_id)
        if not _wants(prefs, type):
            return note

        url = f"{settings.frontend_url.rstrip('/')}{link}" if link else settings.frontend_url

        if prefs.email_enabled:
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.email:
                email_service.send(
                    to=user.email,
                    subject=title,
                    body_text=f"{body or ''}\n\n{url}",
                    body_html=email_service.render(title, body or "", url, note.severity),
                )

        if prefs.slack_enabled and prefs.slack_webhook_url:
            slack_service.post(prefs.slack_webhook_url, title=title, body=body or "", url=url,
                               severity=note.severity)
    except Exception:
        log.exception("Notification fan-out failed for user %s", user_id)

    return note


def notify_org(
    db: Session,
    *,
    org_id: uuid.UUID | None,
    fallback_user_id: uuid.UUID,
    type: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
    payload: dict | None = None,
    roles: list[str] | None = None,
) -> list[Notification]:
    """
    Notify everyone in the org who could act on this (default: owners/admins/
    members — viewers cannot approve, so paging them is noise). Personal
    workspaces fall back to the single owner.
    """
    if not org_id:
        return [notify_user(db, user_id=fallback_user_id, org_id=None, type=type,
                            title=title, body=body, link=link, payload=payload)]

    wanted = roles or ["owner", "admin", "member"]
    members = (
        db.query(OrgMember)
        .filter(OrgMember.org_id == org_id, OrgMember.role.in_(wanted))
        .all()
    )
    out = [
        notify_user(db, user_id=m.user_id, org_id=org_id, type=type,
                    title=title, body=body, link=link, payload=payload)
        for m in members
    ]

    # Outbound webhooks are org-level, not per-user: fire once.
    try:
        webhook_service.dispatch(
            db, org_id=org_id, event=type,
            payload={"title": title, "body": body, "link": link, **(payload or {})},
        )
    except Exception:
        log.exception("Webhook dispatch failed for org %s", org_id)

    return out


def unread_count(db: Session, user_id: uuid.UUID) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.read_at.is_(None))
        .count()
    )
