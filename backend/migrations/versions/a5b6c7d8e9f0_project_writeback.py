"""Ticket write-back configuration on projects

Adds: projects.writeback (JSONB).

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a5b6c7d8e9f0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    # Defaults to an empty object, which reads as "not enabled" — existing
    # projects keep behaving exactly as they did until someone opts in.
    op.add_column(
        "projects",
        sa.Column("writeback", JSONB, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("projects", "writeback")
