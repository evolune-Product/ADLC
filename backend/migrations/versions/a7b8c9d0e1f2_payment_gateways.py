"""Payment gateways — Razorpay and PayPal alongside Stripe

Adds: subscriptions.payment_provider, .razorpay_subscription_id,
.paypal_subscription_id, .paypal_payer_id.

Purely additive. Every existing subscription row implicitly stayed on Stripe
(or unconfigured), and `payment_provider` starts NULL for all of them — the
billing router treats a NULL provider on an active paid plan as "assume
Stripe" for backward compatibility, so no existing subscription needs its
gateway inferred by this migration.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-26
"""
from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("payment_provider", sa.String(20), nullable=True))
    op.add_column("subscriptions", sa.Column("razorpay_subscription_id", sa.String(255), nullable=True))
    op.add_column("subscriptions", sa.Column("paypal_subscription_id", sa.String(255), nullable=True))
    op.add_column("subscriptions", sa.Column("paypal_payer_id", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("subscriptions", "paypal_payer_id")
    op.drop_column("subscriptions", "paypal_subscription_id")
    op.drop_column("subscriptions", "razorpay_subscription_id")
    op.drop_column("subscriptions", "payment_provider")
