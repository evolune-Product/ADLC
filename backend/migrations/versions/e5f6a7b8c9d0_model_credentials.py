"""Model credentials — one workspace, many provider keys

Adds: model_credentials.

Replaces the single Subscription.byo_llm_provider/byo_llm_key pair, which
forced a workspace to pick one model vendor for every agent. The old columns
are deliberately left in place and still read as a fallback, so an existing
workspace keeps working without a data migration.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "model_credentials",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        # Not an enum and not a CHECK: the provider catalogue is a dict literal
        # that is expected to grow, and a migration per new vendor would defeat
        # the point of it being a registry.
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("label", sa.String(120), nullable=True),
        sa.Column("api_key", sa.Text, nullable=True),
        sa.Column("masked_hint", sa.String(32), nullable=True),
        sa.Column("base_url", sa.Text, nullable=True),
        sa.Column("default_model", sa.String(120), nullable=True),
        sa.Column("price_overrides", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("status_detail", sa.Text, nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("org_id", "user_id", "provider", name="uq_model_cred_provider"),
    )
    op.create_index("ix_model_credentials_owner", "model_credentials", ["user_id", "org_id"])


def downgrade() -> None:
    op.drop_index("ix_model_credentials_owner", table_name="model_credentials")
    op.drop_table("model_credentials")
