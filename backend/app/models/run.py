import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, Index, String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tickets.id"))
    pod_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pods.id"))
    status: Mapped[str] = mapped_column(String(50), default="queued")
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    branch_name: Mapped[str | None] = mapped_column(Text)
    pr_url: Mapped[str | None] = mapped_column(Text)
    pr_number: Mapped[int | None] = mapped_column(Integer)
    current_step: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    current_env_index: Mapped[int] = mapped_column(Integer, default=-1)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="runs")
    ticket = relationship("Ticket", back_populates="runs")
    steps = relationship("RunStep", back_populates="run", cascade="all, delete-orphan", order_by="RunStep.created_at")
    approvals = relationship("Approval", back_populates="run", cascade="all, delete-orphan")


class RunStep(Base):
    __tablename__ = "run_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"))
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"))
    agent_role: Mapped[str | None] = mapped_column(String(50))
    step_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str | None] = mapped_column(String(50))
    input: Mapped[dict] = mapped_column(JSONB, default=dict)
    output: Mapped[dict] = mapped_column(JSONB, default=dict)
    log: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run = relationship("Run", back_populates="steps")


class Approval(Base):
    """
    The one real approval-record table in the platform.

    Company OS steps 17-18 extend this to cover a workflow `approval` node's
    real per-approver records, rather than inventing a second Approval-shaped
    table: `run_id` is now nullable and `execution_id` (nullable, pointing at
    `workflow_executions`) is new. A CHECK enforces exactly one of the two is
    set, so `Approval.run_id`-scoped queries used by `policy_service.evaluate_deploy`
    for the existing deploy gate are completely unaffected — every pre-existing
    row already has run_id set and execution_id NULL. See
    `policy_service.evaluate_workflow_approval` for the workflow-node reader of
    the execution_id-scoped rows.
    """
    __tablename__ = "approvals"
    __table_args__ = (
        CheckConstraint(
            "(run_id IS NOT NULL AND execution_id IS NULL) OR (run_id IS NULL AND execution_id IS NOT NULL)",
            name="approvals_one_target_check",
        ),
        Index("ix_approvals_execution", "execution_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=True)
    execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=True
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    decision: Mapped[str | None] = mapped_column(String(50))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run = relationship("Run", back_populates="approvals")
    execution = relationship("WorkflowExecution")
