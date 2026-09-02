"""
Persona — a named simulated user the QA pipeline can drive through the app.

WHY THIS EXISTS
Today's QA stage (`agents/qa_agent.py`) reads a PR diff and asks an LLM whether
the code looks right. It never runs the application. A Persona is the missing
half: a free-text description of who is using the product and what they are
trying to do ("a first-time user trying to sign up and hit the free trial"),
plus the URL they land on first. `agents/simulation_agent.py` drives a real
browser as this persona and files what it finds — see that module's docstring.

Org/project-scoped like Skill and Project: `user_id` + nullable `org_id`
follows the exact ownership shape `owner_filter` already expects everywhere
else in this codebase, so Persona CRUD needs no new access-control code.
`project_id` is an optional narrowing — a persona built for one product can be
kept out of every other project's picker — not a requirement, since the
simplest use (a solo workspace testing one URL) has no project at all.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Persona(Base):
    __tablename__ = "personas"
    __table_args__ = (
        Index("ix_personas_user_org", "user_id", "org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Free-text natural-language goal/behavior, e.g. "a first-time user trying
    # to sign up and hit the free trial." This is handed to the LLM verbatim
    # on every step of the simulation loop — it is the persona's entire brief.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    entry_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project")
    runs = relationship("SimulationRun", back_populates="persona", cascade="all, delete-orphan")
