"""
Work — the generic, non-engineering work request.

This is deliberately NOT a replacement for Ticket/Run. Ticket is a synced
Jira/Linear issue that flows through the SDLC pipeline (sprint -> dev -> qa ->
review -> approval -> deploy) via Run. Work is the opposite shape: a request a
person in ANY department (support, sales, ops, HR, finance...) opens directly
on the platform with no tracker sync and no code-pipeline machinery behind it.
The two coexist; neither imports or depends on the other's model.

`assigned_agent_id` points at the same `agents` table the SDLC pipeline uses
(app.models.agent.Agent) — an AI agent that already exists as a first-class
actor in this platform can be handed generic work too, rather than this
module inventing a second notion of "agent".

`workflow_id` is a bare column with no workflow engine behind it yet, on
purpose — this session builds the entity and its status machine only. See
ADLC_PROJECT_OVERVIEW.md "Recommended next steps" for the workflow engine.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

WORK_STATUSES = (
    "new", "triaged", "assigned", "in_progress", "awaiting_input",
    "awaiting_approval", "completed", "failed", "cancelled",
)

# The valid-transition graph enforced by the service layer (not the DB — a
# CHECK constraint can validate a single row's value, not a transition
# between two values across an UPDATE). Terminal states have no outgoing
# edges.
VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "new": ("triaged", "assigned", "cancelled"),
    "triaged": ("assigned", "cancelled"),
    "assigned": ("in_progress", "triaged", "cancelled"),
    "in_progress": ("awaiting_input", "awaiting_approval", "completed", "failed", "cancelled"),
    "awaiting_input": ("in_progress", "cancelled"),
    "awaiting_approval": ("in_progress", "completed", "failed", "cancelled"),
    "completed": (),
    "failed": ("triaged", "assigned"),
    "cancelled": (),
}


class Work(Base):
    __tablename__ = "work_items"
    __table_args__ = (
        CheckConstraint("status IN " + str(WORK_STATUSES), name="work_items_status_check"),
        Index("ix_work_items_org", "organization_id"),
        Index("ix_work_items_org_status", "organization_id", "status"),
        Index("ix_work_items_department", "department_id"),
        Index("ix_work_items_team", "team_id"),
        Index("ix_work_items_assignee", "assigned_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    requester_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    type: Mapped[str] = mapped_column(String(50), nullable=False, default="generic_request")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str | None] = mapped_column(String(20))
    context: Mapped[dict] = mapped_column(JSONB, default=dict)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="new", server_default="new")

    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )

    # No workflow engine yet — a plain string/UUID slot a future engine can
    # populate without a schema change.
    workflow_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approval_state: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # routing_service.route_work's decision, kept visible on the row itself —
    # per spec item 48 ("never hide what will happen") the reasoning behind
    # where a request landed (or why it didn't) must be inspectable, not just
    # logged. confidence is "explicit" | "matched" | "unmatched".
    routing_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    routing_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    org = relationship("Organization")
    department = relationship("Department")
    team = relationship("Team")
    requester = relationship("User", foreign_keys=[requester_user_id])
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    assigned_agent = relationship("Agent", foreign_keys=[assigned_agent_id])
