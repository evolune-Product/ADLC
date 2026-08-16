"""
AI Sprint Planner.

Tickets sync in from Jira/Linear, but composing a sprint from the backlog was
entirely manual — no competitor in the governed-execution category does this
(see documents/PRODUCT_STRATEGY.md Horizon 4, §5.14). A SprintPlan is one
planning run: given a project's backlog and a stated capacity, the agent
estimates complexity per ticket, detects dependencies between tickets in the
same backlog, and proposes which tickets fit this sprint.

A SprintPlan is a snapshot, not a live document — replanning creates a new one
rather than mutating the last, so a team can see how the plan changed and
still show a stakeholder last week's version.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SprintPlan(Base):
    __tablename__ = "sprint_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    capacity_points: Mapped[int] = mapped_column(Integer, nullable=False)
    committed_points: Mapped[int] = mapped_column(Integer, default=0)
    # 'on_track' | 'at_risk' | 'blocked' — at_risk means committed_points is
    # close to or over capacity, blocked means an included ticket depends on
    # one that didn't make the cut.
    health: Mapped[str] = mapped_column(String(20), default="on_track")
    summary: Mapped[str | None] = mapped_column(Text)
    written_back: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project")
    estimates = relationship("TicketEstimate", back_populates="sprint_plan",
                             cascade="all, delete-orphan", order_by="TicketEstimate.story_points.desc()")


class TicketEstimate(Base):
    __tablename__ = "ticket_estimates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sprint_plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sprint_plans.id", ondelete="CASCADE"))
    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"))
    story_points: Mapped[int] = mapped_column(Integer, nullable=False)
    complexity_reasoning: Mapped[str | None] = mapped_column(Text)
    # Jira/Linear ids (Ticket.jira_id) of other backlog tickets this one
    # depends on — not database ids, since that's what the model reasons in
    # and what a human recognises on the board.
    depends_on: Mapped[list] = mapped_column(JSONB, default=list)
    included_in_sprint: Mapped[bool] = mapped_column(default=False)
    # 'on_track' | 'at_risk' | 'blocked' — blocked means depends_on includes a
    # ticket not selected for this sprint.
    risk: Mapped[str] = mapped_column(String(20), default="on_track")

    sprint_plan = relationship("SprintPlan", back_populates="estimates")
    ticket = relationship("Ticket")
