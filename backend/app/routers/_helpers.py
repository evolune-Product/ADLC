"""
router helpers
--------------
Shared utilities used across all resource routers.

OrgContext
    Dataclass holding org_id, org_name, and the current user's role in that org.
    Populated by get_optional_org() when X-Org-ID header is present.

get_optional_org
    FastAPI dependency. Reads X-Org-ID header, validates membership,
    returns OrgContext or None (personal workspace mode).

require_org_role
    Dependency factory. Returns OrgContext, raising 403 if the user's role
    in the org doesn't meet the minimum required role.

owner_filter
    Single source of truth for scoping a SQLAlchemy query to either:
      - an org workspace  (org_id == ctx.org_id)
      - a personal workspace (user_id == current_user.id AND org_id IS NULL)

get_or_404
    Fetches a user-owned or org-owned DB record by id.
    Raises HTTP 404 if not found.
"""

import uuid
from dataclasses import dataclass
from typing import Optional, Type, TypeVar

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user

T = TypeVar("T")

_ROLE_RANK = {"viewer": 0, "member": 1, "admin": 2, "owner": 3}


@dataclass
class OrgContext:
    org_id: uuid.UUID
    org_name: str
    role: str


def get_optional_org(
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Optional[OrgContext]:
    """
    If X-Org-ID header is present, validate that the current user is a member
    of that org and return an OrgContext. Otherwise return None (personal mode).
    """
    if not x_org_id:
        return None

    try:
        org_uuid = uuid.UUID(x_org_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Org-ID header")

    from app.models.organization import Organization, OrgMember

    org = db.query(Organization).filter(Organization.id == org_uuid).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    member = db.query(OrgMember).filter(
        OrgMember.org_id == org_uuid,
        OrgMember.user_id == current_user.id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    return OrgContext(org_id=org_uuid, org_name=org.name, role=member.role)


def require_org_role(min_role: str):
    """
    Dependency factory that ensures the user has at least *min_role* in the org.
    Returns the OrgContext if satisfied, raises 403 otherwise.

    Usage:
        org_ctx: OrgContext = Depends(require_org_role("admin"))
    """
    def _dep(
        org_ctx: Optional[OrgContext] = Depends(get_optional_org),
    ) -> OrgContext:
        if org_ctx is None:
            raise HTTPException(
                status_code=400,
                detail="This action requires an org context (X-Org-ID header)",
            )
        if _ROLE_RANK.get(org_ctx.role, -1) < _ROLE_RANK.get(min_role, 0):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{min_role}' or higher is required",
            )
        return org_ctx
    return _dep


def owner_filter(model: Type[T], current_user, org_ctx: Optional[OrgContext]):
    """
    Returns a SQLAlchemy filter clause that scopes *model* rows to either:
      - the org workspace  → model.org_id == ctx.org_id
      - the personal workspace → model.user_id == current_user.id AND model.org_id IS NULL

    Usage:
        db.query(Skill).filter(owner_filter(Skill, current_user, org_ctx))
    """
    if org_ctx:
        return model.org_id == org_ctx.org_id  # type: ignore[attr-defined]
    return and_(
        model.user_id == current_user.id,   # type: ignore[attr-defined]
        model.org_id.is_(None),             # type: ignore[attr-defined]
    )


def get_or_404(
    model: Type[T],
    resource_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session,
    label: str = "Resource",
    org_ctx: Optional[OrgContext] = None,
) -> T:
    """
    Return the *model* row for the given id, scoped by owner_filter.
    Raises HTTP 404 if not found or not accessible.
    """

    class _FakeUser:
        id = user_id

    filt = owner_filter(model, _FakeUser(), org_ctx)
    obj = db.query(model).filter(model.id == resource_id, filt).first()  # type: ignore[attr-defined]
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{label} not found",
        )
    return obj
