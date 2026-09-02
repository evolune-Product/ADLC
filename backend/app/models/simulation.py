"""
SimulationRun / SimulationFinding — persona-driven simulated user testing.

One SimulationRun is one pass of `agents/simulation_agent.py`: a persona,
a starting URL, and a bounded loop of "screenshot → ask the LLM what this
persona would do → act → repeat" (see that module for the loop itself). A
SimulationFinding is one thing the agent flagged along the way — something
that looked broken or left the persona confused — with enough context
(severity, a title, a description, reproduction steps, the screenshot at that
moment) for a human to triage it without re-running anything.

Findings are advisory, the same way `ReviewFinding` is (see `models/insight.py`):
nothing here can write code or ship a fix. `services/simulation_service.py` is
what turns a finding into a tracker comment + a workspace notification, and
that is the entire write path — there is no separate approval mechanism here,
because there is nothing here that needs approving yet.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

STATUSES = ("pending", "running", "completed", "failed")
SEVERITIES = ("critical", "high", "medium", "low")


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    __table_args__ = (
        Index("ix_simulation_runs_user_org", "user_id", "org_id"),
        Index("ix_simulation_runs_persona", "persona_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    persona_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"))
    # Optional: which existing ticket this simulation is testing. When set and
    # the owning project has a connected, write-back-enabled Jira/Linear
    # tracker, findings are posted as comments on this ticket via the same
    # add_comment()/comment() primitives writeback_service already uses — see
    # simulation_service.py's module docstring for why that is the write-back
    # shape rather than creating a brand-new tracker issue.
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True)

    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    steps_taken: Mapped[int] = mapped_column(Integer, default=0)
    max_steps: Mapped[int] = mapped_column(Integer, default=15)
    # The agent's own closing narrative: goal reached / stuck / step limit hit.
    summary: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    persona = relationship("Persona", back_populates="runs")
    ticket = relationship("Ticket")
    findings = relationship(
        "SimulationFinding", back_populates="run",
        cascade="all, delete-orphan", order_by="SimulationFinding.created_at",
    )


class SimulationFinding(Base):
    __tablename__ = "simulation_findings"
    __table_args__ = (
        Index("ix_simulation_findings_run", "simulation_run_id", "severity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulation_runs.id", ondelete="CASCADE"))

    severity: Mapped[str] = mapped_column(String(20), default="medium")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Ordered list of strings — "1. Clicked Sign Up", "2. Entered email", ...
    # JSONB list rather than one Text blob for the same reason
    # TicketEstimate.depends_on is a JSONB list: a UI can render each step
    # without re-parsing prose.
    reproduction_steps: Mapped[list] = mapped_column(JSONB, default=list)
    screenshot_path: Mapped[str | None] = mapped_column(Text)
    step_number: Mapped[int | None] = mapped_column(Integer)

    posted_to_tracker: Mapped[bool] = mapped_column(Boolean, default=False)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run = relationship("SimulationRun", back_populates="findings")
