"""Personas — persona-driven simulated user testing (v1, step 1/2)

Adds: personas.

Revision ID: 3c5aea39d4b8
Revises: b91c2d3e4f5a
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "3c5aea39d4b8"
down_revision = "b91c2d3e4f5a"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "personas",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("entry_url", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_personas_user_org", "personas", ["user_id", "org_id"])


def downgrade() -> None:
    op.drop_index("ix_personas_user_org", table_name="personas")
    op.drop_table("personas")
