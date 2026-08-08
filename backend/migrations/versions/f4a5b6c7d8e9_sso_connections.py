"""SSO — per-organisation OIDC identity providers

Adds: sso_connections.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "sso_connections",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),

        sa.Column("label", sa.String(100), nullable=False, server_default="SSO"),
        sa.Column("issuer", sa.Text, nullable=False),
        sa.Column("client_id", sa.Text, nullable=False),
        # Fernet-encrypted before insert, like every other secret here.
        sa.Column("client_secret", sa.Text, nullable=False),

        sa.Column("email_domains", JSONB, nullable=False, server_default="[]"),
        sa.Column("default_role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("enforced", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),

        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

        # One identity provider per organisation. Two would make "which IdP
        # does this email go to" ambiguous for the org's own domains.
        sa.UniqueConstraint("org_id", name="uq_sso_org"),
    )


def downgrade() -> None:
    op.drop_table("sso_connections")
