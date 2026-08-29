import uuid
from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class UsageLimit(Base):
    __tablename__ = "usage_limits"
    __table_args__ = (
        UniqueConstraint("user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Usage counters
    projects_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    agents_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    pods_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    skills_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    github_connections_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    jira_connections_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    deployed_projects_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="usage_limits")
