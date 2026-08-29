"""
Generic workflow engine — a new, separate, general-purpose capability.

This does NOT touch, migrate, or replace the existing SDLC pipeline
(sprint -> dev -> qa -> review -> approval -> deploy, driven by Run/RunStep
and the two-Celery-task approval-gate pattern in app/tasks/run_tasks.py).
That pipeline keeps running exactly as it does today. "The existing SDLC run
becomes a specialized workflow type" (a framing used in the wider company-OS
spec) is a FUTURE integration, intentionally out of scope here.

`Workflow.definition` shape (JSONB):
    {
      "start_node_id": "n1",
      "nodes": [
        {
          "id": "n1",
          "type": "trigger" | "human_task" | "agent_task" | "api_call" |
                  "condition" | "approval" | "notification" | "webhook" |
                  "transform" | "delay" | "sub_workflow" | "completion",
          "config": {...},
          # linear:
          "next": "n2",
          # or a list for a plain fan-out (engine always takes next[0] today —
          # true parallel branches are not attempted this session):
          "next": ["n2"],
          # or a branch for "condition" nodes:
          "next": {"field": "path.to.value", "branches": {"true_val": "n2", "false_val": "n3"}, "default": "n4"}
        },
        ...
      ]
    }

Kept deliberately simple — a linear/branching walk over a small node list,
not a general DAG scheduler with parallel joins.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text,
    Boolean, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

TRIGGER_TYPES = ("manual", "work_created")

EXECUTION_STATUSES = (
    "pending", "running", "awaiting_approval", "completed", "failed", "cancelled",
)

NODE_TYPES = (
    "trigger", "human_task", "agent_task", "api_call", "condition",
    "approval", "notification", "webhook", "transform", "delay",
    "sub_workflow", "completion",
)

STEP_STATUSES = ("pending", "running", "waiting", "completed", "failed", "skipped")


class Workflow(Base):
    __tablename__ = "workflows"
    __table_args__ = (
        CheckConstraint("trigger_type IN " + str(TRIGGER_TYPES), name="workflows_trigger_type_check"),
        Index("ix_workflows_org", "organization_id"),
        Index("ix_workflows_department", "department_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False, default="manual", server_default="manual")
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    org = relationship("Organization")
    department = relationship("Department")
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    __table_args__ = (
        CheckConstraint("status IN " + str(EXECUTION_STATUSES), name="workflow_executions_status_check"),
        Index("ix_workflow_executions_workflow", "workflow_id"),
        Index("ix_workflow_executions_org", "organization_id"),
        Index("ix_workflow_executions_work", "work_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    work_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_items.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", server_default="pending")
    current_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    workflow = relationship("Workflow", back_populates="executions")
    org = relationship("Organization")
    work = relationship("Work")
    steps = relationship(
        "WorkflowExecutionStep", back_populates="execution",
        cascade="all, delete-orphan", order_by="WorkflowExecutionStep.started_at",
    )


class WorkflowExecutionStep(Base):
    __tablename__ = "workflow_execution_steps"
    __table_args__ = (
        CheckConstraint("node_type IN " + str(NODE_TYPES), name="workflow_execution_steps_node_type_check"),
        CheckConstraint("status IN " + str(STEP_STATUSES), name="workflow_execution_steps_status_check"),
        Index("ix_workflow_execution_steps_execution", "execution_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    node_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    input: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    execution = relationship("WorkflowExecution", back_populates="steps")
