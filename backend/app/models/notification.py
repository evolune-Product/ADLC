"""
Notifications — in-app bell, plus delivery preferences for email and Slack.

The approval gate is the product's core differentiator; it is worthless if the
reviewer never learns their approval is needed. Every run event that needs a
human writes a Notification row and fans out to the enabled channels.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "read_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)

    type: Mapped[str] = mapped_column(String(80))      # run.awaiting_approval | run.failed | run.completed | quota.exceeded | policy.blocked | member.joined
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(Text)     # relative frontend path, e.g. /runs/<id>
    severity: Mapped[str] = mapped_column(String(20), default="info")   # info | warning | critical
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationSetting(Base):
    """Per-user (optionally per-org) channel preferences."""
    __tablename__ = "notification_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)

    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    slack_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    slack_webhook_url: Mapped[str | None] = mapped_column(Text)
    digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True)   # weekly ROI digest
    # Which event types to deliver; empty list = all
    events: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
