"""
Agent — an AI actor in this platform.

`department_id` / `team_id` (added for Company OS, step 10) are additive and
nullable: an agent with neither set keeps EXACTLY today's behavior — available
org-wide within the existing access rules, resolved and authorized by the
existing pod/skill/run pipeline exactly as before. Nothing in that pipeline
reads these two columns.

An agent that IS explicitly assigned a department/team is, by convention,
scoped to that department/team's work only in the NEW Company OS surfaces:
Company Desk's "agent activity" view, and a workflow `agent_task` node that
opts in to department filtering (see `workflow_engine._run_agent_task`). This
is a least-privilege default for the new surfaces, not a new restriction on
the SDLC pipeline — a scoped agent can still be used in pods/runs exactly as
an unscoped one always could.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        Index("ix_agents_user_org", "user_id", "org_id"),
        Index("ix_agents_department", "department_id"),
        Index("ix_agents_team", "team_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    # Company OS, step 10 — nullable, additive. NULL = org-wide, today's behavior.
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    repo_connection_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("connections.id"))
    default_branch: Mapped[str] = mapped_column(String(255), default="main")
    branch_prefix: Mapped[str] = mapped_column(String(100), default="agent/")
    llm_model: Mapped[str] = mapped_column(String(100), default="claude-sonnet-4-6")
    max_iterations: Mapped[int] = mapped_column(Integer, default=10)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="agents")
    org = relationship("Organization", foreign_keys=[org_id])
    department = relationship("Department", foreign_keys=[department_id])
    team = relationship("Team", foreign_keys=[team_id])
    agent_skills = relationship("AgentSkill", back_populates="agent", cascade="all, delete-orphan")
    pod_agents = relationship("PodAgent", back_populates="agent")


class AgentSkill(Base):
    __tablename__ = "agent_skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"))
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"))
    priority: Mapped[int] = mapped_column(Integer, default=0)

    agent = relationship("Agent", back_populates="agent_skills")
    skill = relationship("Skill", back_populates="agent_skills")
