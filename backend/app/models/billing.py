"""
Billing models — subscriptions and metered usage.

A subscription belongs to either an org (team plans) or a user (personal
workspace). Quota enforcement reads `plan` + `included_runs` and compares
against UsageRecord rows in the current billing period.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Numeric, Boolean, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_owner", "user_id", "org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)

    plan: Mapped[str] = mapped_column(String(50), default="free")          # free | pro | enterprise
    status: Mapped[str] = mapped_column(String(50), default="active")      # active | past_due | canceled | trialing
    seats: Mapped[int] = mapped_column(Integer, default=1)

    # Snapshot of plan limits at subscribe time (so plan changes don't retro-apply)
    included_runs: Mapped[int] = mapped_column(Integer, default=25)
    overage_cents_per_run: Mapped[int] = mapped_column(Integer, default=0)
    max_projects: Mapped[int] = mapped_column(Integer, default=1)
    run_budget_cents: Mapped[int] = mapped_column(Integer, default=200)     # hard ceiling per single run

    # Which gateway this subscription is actually paid through right now —
    # stripe | razorpay | paypal | null (free plan, or applied directly with
    # no gateway configured). Set the moment checkout starts, not only once a
    # webhook confirms payment, because the cancel/portal endpoints need to
    # know which gateway's API to call and a subscription only ever has one
    # gateway active at a time — switching gateways means starting a new
    # checkout, not running two in parallel.
    payment_provider: Mapped[str | None] = mapped_column(String(20))

    # Stripe linkage (nullable — the platform runs fine without Stripe configured)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))
    stripe_price_id: Mapped[str | None] = mapped_column(String(255))

    # Razorpay linkage — the India rail. No customer-id equivalent to Stripe's:
    # Razorpay's subscription id is the only handle both the webhook and the
    # cancel endpoint need.
    razorpay_subscription_id: Mapped[str | None] = mapped_column(String(255))

    # PayPal linkage. `paypal_payer_id` is PayPal's id for the payer, returned
    # on subscription events — kept distinct from `paypal_subscription_id`
    # because a support ticket referencing "the payer" needs the payer id, not
    # the subscription id, to look someone up in the PayPal dashboard.
    paypal_subscription_id: Mapped[str | None] = mapped_column(String(255))
    paypal_payer_id: Mapped[str | None] = mapped_column(String(255))

    # Bring-your-own LLM key (Fernet-encrypted) — zero COGS path
    byo_llm_provider: Mapped[str | None] = mapped_column(String(50))
    byo_llm_key: Mapped[str | None] = mapped_column(Text)

    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UsageRecord(Base):
    """One row per metered event. `kind` = run | llm_call | seat | marketplace."""
    __tablename__ = "usage_records"
    __table_args__ = (
        Index("ix_usage_owner_created", "org_id", "user_id", "created_at"),
        Index("ix_usage_run", "run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=True)

    kind: Mapped[str] = mapped_column(String(50), default="run")
    agent_role: Mapped[str | None] = mapped_column(String(50))
    model: Mapped[str | None] = mapped_column(String(100))
    provider: Mapped[str | None] = mapped_column(String(50))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_millicents: Mapped[int] = mapped_column(Integer, default=0)   # integer math — no float drift
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    billable: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
