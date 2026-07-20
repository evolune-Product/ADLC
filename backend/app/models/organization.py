import uuid
import secrets
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("OrgMember", back_populates="org", cascade="all, delete-orphan")
    invitations = relationship("OrgInvitation", back_populates="org", cascade="all, delete-orphan")


class OrgMember(Base):
    __tablename__ = "org_members"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id"),
        CheckConstraint("role IN ('owner','admin','member','viewer')", name="org_members_role_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    org = relationship("Organization", back_populates="members")
    user = relationship("User")


class OrgInvitation(Base):
    __tablename__ = "org_invitations"
    __table_args__ = (
        CheckConstraint("role IN ('admin','member','viewer')", name="org_invitations_role_check"),
        CheckConstraint("status IN ('pending','accepted','expired','revoked')", name="org_invitations_status_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    invited_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(48))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    org = relationship("Organization", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[invited_by])
