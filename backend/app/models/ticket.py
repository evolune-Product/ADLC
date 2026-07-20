import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (UniqueConstraint("project_id", "jira_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    jira_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(String(50))
    priority: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str | None] = mapped_column(String(100))
    assignee: Mapped[str | None] = mapped_column(String(255))
    jira_url: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="tickets")
    runs = relationship("Run", back_populates="ticket")
