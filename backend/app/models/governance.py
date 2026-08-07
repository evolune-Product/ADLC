"""
Governance models — the control-plane primitives.

ApprovalPolicy  what must be true before a run may deploy to an environment
ApiKey          scoped, hashed programmatic access (public API + CI)
Webhook         signed outbound events so customers can wire their own systems
WebhookDelivery delivery attempt log (evidence + debugging)
"""
import uuid
import secrets
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class ApprovalPolicy(Base):
    """
    Scoped org-wide (project_id NULL) or per-project. The most specific
    matching policy for an environment wins; see services/policy_service.py.
    """
    __tablename__ = "approval_policies"
    __table_args__ = (
        Index("ix_policies_scope", "org_id", "project_id", "environment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)

    name: Mapped[str] = mapped_column(String(255))
    environment: Mapped[str] = mapped_column(String(50), default="*")     # '*' | dev | qa | staging | production

    # Gate conditions
    min_approvers: Mapped[int] = mapped_column(Integer, default=1)
    approver_roles: Mapped[list] = mapped_column(JSONB, default=lambda: ["owner", "admin", "member"])
    require_review_pass: Mapped[bool] = mapped_column(Boolean, default=False)
    min_review_score: Mapped[int] = mapped_column(Integer, default=0)      # 0–100, reviewer agent score
    block_on_severity: Mapped[str | None] = mapped_column(String(20))      # block if any finding >= this severity
    auto_approve_below_risk: Mapped[int] = mapped_column(Integer, default=0)  # 0 disables auto-approve

    # Blast-radius controls
    protected_paths: Mapped[list] = mapped_column(JSONB, default=list)     # glob patterns agents may not touch
    protected_branches: Mapped[list] = mapped_column(JSONB, default=list)
    max_files_changed: Mapped[int] = mapped_column(Integer, default=0)     # 0 = unlimited
    max_run_cost_cents: Mapped[int] = mapped_column(Integer, default=0)    # 0 = plan default

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_api_keys_prefix", "prefix"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)

    name: Mapped[str] = mapped_column(String(255))
    prefix: Mapped[str] = mapped_column(String(16))          # shown in UI: adlc_live_ab12…
    hashed_key: Mapped[str] = mapped_column(Text)            # sha256 of the full key — raw key never stored
    scopes: Mapped[list] = mapped_column(JSONB, default=lambda: ["runs:read"])
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)

    url: Mapped[str] = mapped_column(Text)
    secret: Mapped[str] = mapped_column(String(64), default=lambda: secrets.token_hex(24))
    events: Mapped[list] = mapped_column(JSONB, default=lambda: ["run.completed", "run.failed", "run.awaiting_approval"])
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("ix_webhook_deliveries_hook", "webhook_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("webhooks.id", ondelete="CASCADE"))
    event: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status_code: Mapped[int | None] = mapped_column(Integer)
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
