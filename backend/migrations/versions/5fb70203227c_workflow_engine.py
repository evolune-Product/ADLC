"""Workflow engine — workflows, workflow_executions, workflow_execution_steps;
routing_confidence/routing_reasoning columns on work_items.

New, additive tables plus two nullable columns on the existing work_items
table (routing_service's decision, kept visible per spec item 48 — "never
hide what will happen"). The existing SDLC pipeline (runs/run_steps) is not
touched by this migration at all.

Revision ID: a1b2c3d4e5f6
Revises: c3d4e5a1b2c3
Create Date: 2026-08-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "5fb70203227c"
down_revision = "c3d4e5a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("work_items", sa.Column("routing_confidence", sa.String(20), nullable=True))
    op.add_column("work_items", sa.Column("routing_reasoning", sa.Text(), nullable=True))

    op.create_table(
        "workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trigger_type", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("definition", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("trigger_type IN ('manual','work_created')", name="workflows_trigger_type_check"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflows_org", "workflows", ["organization_id"])
    op.create_index("ix_workflows_department", "workflows", ["department_id"])

    op.create_table(
        "workflow_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("current_node_id", sa.String(100), nullable=True),
        sa.Column("context", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','running','awaiting_approval','completed','failed','cancelled')",
            name="workflow_executions_status_check",
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_id"], ["work_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_executions_workflow", "workflow_executions", ["workflow_id"])
    op.create_index("ix_workflow_executions_org", "workflow_executions", ["organization_id"])
    op.create_index("ix_workflow_executions_work", "workflow_executions", ["work_id"])

    op.create_table(
        "workflow_execution_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", sa.String(100), nullable=False),
        sa.Column("node_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("input", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("output", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "node_type IN ('trigger','human_task','agent_task','api_call','condition',"
            "'approval','notification','webhook','transform','delay','sub_workflow','completion')",
            name="workflow_execution_steps_node_type_check",
        ),
        sa.CheckConstraint(
            "status IN ('pending','running','waiting','completed','failed','skipped')",
            name="workflow_execution_steps_status_check",
        ),
        sa.ForeignKeyConstraint(["execution_id"], ["workflow_executions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_execution_steps_execution", "workflow_execution_steps", ["execution_id"])


def downgrade() -> None:
    op.drop_index("ix_workflow_execution_steps_execution", table_name="workflow_execution_steps")
    op.drop_table("workflow_execution_steps")

    op.drop_index("ix_workflow_executions_work", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_org", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_workflow", table_name="workflow_executions")
    op.drop_table("workflow_executions")

    op.drop_index("ix_workflows_department", table_name="workflows")
    op.drop_index("ix_workflows_org", table_name="workflows")
    op.drop_table("workflows")

    op.drop_column("work_items", "routing_reasoning")
    op.drop_column("work_items", "routing_confidence")
