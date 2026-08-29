"""
Department/Team service — the write path shared by both routers.

Slugs are generated server-side from `name` (see `Department.slugify` /
`Team.slugify`) and de-duplicated the same way `organizations.py::_make_slug`
already does for orgs: try the base slug, fall back to a short random suffix
on collision. Kept here rather than duplicated in both routers because
Department and Team share the exact same uniqueness shape (unique within a
parent, not globally).
"""
import secrets
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.department import Department, Team, TeamMember, slugify


def unique_department_slug(db: Session, organization_id: uuid.UUID, name: str) -> str:
    base = slugify(name)
    slug = base
    while db.query(Department).filter(
        Department.organization_id == organization_id, Department.slug == slug
    ).first():
        slug = f"{base}-{secrets.token_hex(3)}"
    return slug


def unique_team_slug(db: Session, department_id: uuid.UUID, name: str) -> str:
    base = slugify(name)
    slug = base
    while db.query(Team).filter(
        Team.department_id == department_id, Team.slug == slug
    ).first():
        slug = f"{base}-{secrets.token_hex(3)}"
    return slug


def get_department_or_404(db: Session, organization_id: uuid.UUID, department_id: uuid.UUID) -> Optional[Department]:
    return db.query(Department).filter(
        Department.id == department_id,
        Department.organization_id == organization_id,
    ).first()


def get_team_or_404(db: Session, organization_id: uuid.UUID, team_id: uuid.UUID) -> Optional[Team]:
    return db.query(Team).filter(
        Team.id == team_id,
        Team.organization_id == organization_id,
    ).first()
