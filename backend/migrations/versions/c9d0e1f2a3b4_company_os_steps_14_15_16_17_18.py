"""Company OS steps 14, 15-16, 17-18 — memory hierarchy, chat/workflow
integration, workflow-approval-policy gating

Adds:
  - memory_chunks: organization_id / department_id / team_id (nullable),
    project_id made nullable, scope CHECK — the Company > Department > Team >
    Project memory hierarchy (see app/models/memory.py, app/services/memory_service.py)
  - channels: department_id / team_id (nullable) — department/team channels,
    same "about" shape as project_id/run_id/ticket_id (see app/models/workspace.py)
  - approvals: run_id made nullable, execution_id added (nullable, FK
    workflow_executions), one-target CHECK — real per-approver records for a
    workflow `approval` node's optional ApprovalPolicy gate (see
    app/models/run.py, app/services/policy_service.py)

Revision ID: c9d0e1f2a3b4
Revises: b7c8d9e0f1a2
Create Date: 2026-08-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c9d0e1f2a3b4"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # ── step 14: memory hierarchy ────────────────────────────────────────
    op.alter_column("memory_chunks", "project_id", nullable=True)
    op.add_column("memory_chunks", sa.Column(
        "organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    ))
    op.add_column("memory_chunks", sa.Column(
        "department_id", UUID, sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=True
    ))
    op.add_column("memory_chunks", sa.Column(
        "team_id", UUID, sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True
    ))
    op.create_index("ix_memory_org", "memory_chunks", ["organization_id"])
    op.create_index("ix_memory_department", "memory_chunks", ["department_id"])
    op.create_index("ix_memory_team", "memory_chunks", ["team_id"])
    op.create_check_constraint(
        "memory_chunks_scope_check",
        "memory_chunks",
        "project_id IS NOT NULL OR department_id IS NOT NULL OR team_id IS NOT NULL OR organization_id IS NOT NULL",
    )

    # ── steps 15-16: department/team channels ────────────────────────────
    op.add_column("channels", sa.Column(
        "department_id", UUID, sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=True
    ))
    op.add_column("channels", sa.Column(
        "team_id", UUID, sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True
    ))
    op.create_index("ix_channels_department", "channels", ["department_id"])
    op.create_index("ix_channels_team", "channels", ["team_id"])

    # ── steps 17-18: workflow-approval-node policy gating ────────────────
    op.alter_column("approvals", "run_id", nullable=True)
    op.add_column("approvals", sa.Column(
        "execution_id", UUID, sa.ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=True
    ))
    op.create_index("ix_approvals_execution", "approvals", ["execution_id"])
    op.create_check_constraint(
        "approvals_one_target_check",
        "approvals",
        "(run_id IS NOT NULL AND execution_id IS NULL) OR (run_id IS NULL AND execution_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("approvals_one_target_check", "approvals", type_="check")
    op.drop_index("ix_approvals_execution", table_name="approvals")
    op.drop_column("approvals", "execution_id")
    op.alter_column("approvals", "run_id", nullable=False)

    op.drop_index("ix_channels_team", table_name="channels")
    op.drop_index("ix_channels_department", table_name="channels")
    op.drop_column("channels", "team_id")
    op.drop_column("channels", "department_id")

    op.drop_constraint("memory_chunks_scope_check", "memory_chunks", type_="check")
    op.drop_index("ix_memory_team", table_name="memory_chunks")
    op.drop_index("ix_memory_department", table_name="memory_chunks")
    op.drop_index("ix_memory_org", table_name="memory_chunks")
    op.drop_column("memory_chunks", "team_id")
    op.drop_column("memory_chunks", "department_id")
    op.drop_column("memory_chunks", "organization_id")
    op.alter_column("memory_chunks", "project_id", nullable=False)
