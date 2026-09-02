"""Simulation runs and findings — persona-driven simulated user testing (v1, step 2/2)

Adds: simulation_runs, simulation_findings.

Revision ID: f3338312ddf0
Revises: 3c5aea39d4b8
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f3338312ddf0"
down_revision = "3c5aea39d4b8"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "simulation_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("persona_id", UUID, sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticket_id", UUID, sa.ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_url", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("steps_taken", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_steps", sa.Integer, nullable=False, server_default="15"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_simulation_runs_user_org", "simulation_runs", ["user_id", "org_id"])
    op.create_index("ix_simulation_runs_persona", "simulation_runs", ["persona_id", "created_at"])

    op.create_table(
        "simulation_findings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("simulation_run_id", UUID, sa.ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("reproduction_steps", JSONB, nullable=False, server_default="[]"),
        sa.Column("screenshot_path", sa.Text, nullable=True),
        sa.Column("step_number", sa.Integer, nullable=True),
        sa.Column("posted_to_tracker", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("notified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_simulation_findings_run", "simulation_findings", ["simulation_run_id", "severity"])


def downgrade() -> None:
    op.drop_index("ix_simulation_findings_run", table_name="simulation_findings")
    op.drop_table("simulation_findings")
    op.drop_index("ix_simulation_runs_persona", table_name="simulation_runs")
    op.drop_index("ix_simulation_runs_user_org", table_name="simulation_runs")
    op.drop_table("simulation_runs")
