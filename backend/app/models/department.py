"""
Departments and teams — the org-chart layer "company OS" needs that the SDLC
platform never did.

Engineering becomes one department among many, not a special case: the
existing sprint -> dev -> qa -> review -> approval -> deploy pipeline keeps
running exactly as it does today, entirely independent of whether a
Department row named "Engineering" exists. Nothing in the run/ticket/project
path reads Department or Team.

No fixed department list is hardcoded anywhere in this module — an org
creates whatever departments its own structure calls for (Engineering,
Sales, Support, Finance, ...); the platform imposes no catalogue.
"""
import re
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

STATUS_VALUES = ("active", "archived")


def slugify(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return s or "item"


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_departments_org_slug"),
        CheckConstraint(f"status IN {STATUS_VALUES}", name="departments_status_check"),
        Index("ix_departments_org", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(64))
    head_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    org = relationship("Organization", back_populates="departments")
    head = relationship("User", foreign_keys=[head_user_id])
    teams = relationship("Team", back_populates="department", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        # Slugs are unique within a department, not globally — two
        # departments can each have a "core" team.
        UniqueConstraint("department_id", "slug", name="uq_teams_department_slug"),
        CheckConstraint(f"status IN {STATUS_VALUES}", name="teams_status_check"),
        # organization_id is redundant with department.organization_id but
        # required in its own right: every tenant-isolation query on Team
        # filters organization_id directly rather than joining through
        # Department first, so a bug in the join can never leak another
        # tenant's team into a listing.
        Index("ix_teams_org", "organization_id"),
        Index("ix_teams_department", "department_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    department = relationship("Department", back_populates="teams")
    org = relationship("Organization")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    """A user's membership on a team. A user may belong to multiple teams —
    this is a plain join table, not a one-team-per-user FK."""
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_member_user"),
        CheckConstraint("role_in_team IN ('lead','member')", name="team_members_role_check"),
        Index("ix_team_members_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_in_team: Mapped[str] = mapped_column(String(20), nullable=False, default="member", server_default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team = relationship("Team", back_populates="members")
    user = relationship("User")
