"""Sprint plans — AI sprint planning, story-point estimation, dependency graph

Adds: sprint_plans, ticket_estimates.

Revision ID: b2c3d4e5f6a7
Revises: a5b6c7d8e9f0
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b2c3d4e5f6a7"
down_revision = "a5b6c7d8e9f0"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "sprint_plans",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("capacity_points", sa.Integer, nullable=False),
        sa.Column("committed_points", sa.Integer, nullable=False, server_default="0"),
        sa.Column("health", sa.String(20), nullable=False, server_default="on_track"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("written_back", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sprint_plans_project", "sprint_plans", ["project_id", "created_at"])

    op.create_table(
        "ticket_estimates",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("sprint_plan_id", UUID, sa.ForeignKey("sprint_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticket_id", UUID, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("story_points", sa.Integer, nullable=False),
        sa.Column("complexity_reasoning", sa.Text, nullable=True),
        sa.Column("depends_on", JSONB, nullable=False, server_default="[]"),
        sa.Column("included_in_sprint", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("risk", sa.String(20), nullable=False, server_default="on_track"),
    )
    op.create_index("ix_ticket_estimates_plan", "ticket_estimates", ["sprint_plan_id"])
    op.create_index("ix_ticket_estimates_ticket", "ticket_estimates", ["ticket_id"])


def downgrade() -> None:
    op.drop_index("ix_ticket_estimates_ticket", table_name="ticket_estimates")
    op.drop_index("ix_ticket_estimates_plan", table_name="ticket_estimates")
    op.drop_table("ticket_estimates")
    op.drop_index("ix_sprint_plans_project", table_name="sprint_plans")
    op.drop_table("sprint_plans")
