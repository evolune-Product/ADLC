import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey, func, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Pod(Base):
    __tablename__ = "pods"
    __table_args__ = (
        Index("ix_pods_user_org", "user_id", "org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="pods")
    org = relationship("Organization", foreign_keys=[org_id])
    pod_agents = relationship("PodAgent", back_populates="pod", cascade="all, delete-orphan", order_by="PodAgent.execution_order")
    projects = relationship("Project", back_populates="pod")


class PodAgent(Base):
    __tablename__ = "pod_agents"
    __table_args__ = (UniqueConstraint("pod_id", "agent_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pod_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pods.id", ondelete="CASCADE"))
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"))
    execution_order: Mapped[int] = mapped_column(Integer, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=1)
    on_failure: Mapped[str] = mapped_column(String(50), default="retry")
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    pod = relationship("Pod", back_populates="pod_agents")
    agent = relationship("Agent", back_populates="pod_agents")
