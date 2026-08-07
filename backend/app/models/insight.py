"""
Insight models — the evidence the platform produces about its own work.

ReviewFinding  structured output of the Reviewer agent (what competitors can't show)
RunFeedback    thumbs up/down + comment; feeds agent scorecards and the data moat
Deployment     one row per environment promotion — the deploy history timeline
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class ReviewFinding(Base):
    __tablename__ = "review_findings"
    __table_args__ = (
        Index("ix_findings_run", "run_id", "severity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"))
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)

    severity: Mapped[str] = mapped_column(String(20), default="info")   # info | low | medium | high | critical
    category: Mapped[str] = mapped_column(String(50), default="quality")  # security | correctness | tests | style | performance | quality
    file_path: Mapped[str | None] = mapped_column(Text)
    line: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text)
    posted_to_vcs: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RunFeedback(Base):
    __tablename__ = "run_feedback"
    __table_args__ = (
        Index("ix_feedback_run", "run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    agent_role: Mapped[str | None] = mapped_column(String(50))

    rating: Mapped[int] = mapped_column(Integer, default=0)     # +1 / -1
    category: Mapped[str | None] = mapped_column(String(50))    # wrong_approach | missing_tests | style | scope_creep | good
    comment: Mapped[str | None] = mapped_column(Text)
    # Human edits after the fact are the strongest quality signal we can capture
    human_edits_loc: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Deployment(Base):
    __tablename__ = "deployments"
    __table_args__ = (
        Index("ix_deployments_project_env", "project_id", "environment", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))

    environment: Mapped[str] = mapped_column(String(50))
    branch: Mapped[str | None] = mapped_column(String(255))
    sha: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="succeeded")  # succeeded | failed | rolled_back
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approver_count: Mapped[int] = mapped_column(Integer, default=0)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("approval_policies.id", ondelete="SET NULL"), nullable=True)
    message: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
