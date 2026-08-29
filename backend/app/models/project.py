import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_user_org", "user_id", "org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(String(100))
    repo_connection_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("connections.id"))
    repo_name: Mapped[str | None] = mapped_column(String(255))
    jira_connection_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("connections.id"))
    jira_project_key: Mapped[str | None] = mapped_column(String(50))
    # "jira" | "github" | "gitlab" — when not "jira", tickets sync from the
    # repo already on `repo_connection_id`/`repo_name` instead of a separate
    # tracker connection, so a solo project doesn't need a Jira/Linear account
    # just to try the pipeline.
    ticket_source: Mapped[str] = mapped_column(String(20), default="jira", server_default="jira")
    pod_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pods.id"))
    context_md: Mapped[str | None] = mapped_column(Text)
    deploy_targets: Mapped[list] = mapped_column(JSONB, default=list)
    # Ticket write-back: {"enabled": bool, "status_map": {milestone: status name}}.
    # Off by default — moving someone's ticket between columns is an opinionated
    # act, and a platform that starts doing it unasked is a platform people turn
    # the integration off for. See services/writeback_service.py.
    writeback: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="projects")
    org = relationship("Organization", foreign_keys=[org_id])
    pod = relationship("Pod", back_populates="projects")
    tickets = relationship("Ticket", back_populates="project", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="project", cascade="all, delete-orphan")
