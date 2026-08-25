"""Run concurrency — max concurrent runs and bounded queue depth per policy

Adds: approval_policies.max_concurrent_runs, approval_policies.max_queue_depth.

Closes the "automations queueing" gap named in CLAUDE.md. Both default to 0
(unlimited) so every existing policy row keeps its current behaviour.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "approval_policies",
        sa.Column("max_concurrent_runs", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "approval_policies",
        sa.Column("max_queue_depth", sa.Integer(), nullable=False, server_default="0"),
    )
    # The queue lookup is "oldest queued run for this project", run once per
    # terminal event. Without this it is a sequential scan of every run the
    # project has ever had, on the hot path of every completion.
    op.create_index("ix_runs_project_status", "runs", ["project_id", "status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_runs_project_status", table_name="runs")
    op.drop_column("approval_policies", "max_queue_depth")
    op.drop_column("approval_policies", "max_concurrent_runs")
