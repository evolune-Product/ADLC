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

can_write / is_domain_admin
    The two access checks every router actually uses in practice. Backed by
    the role catalogue in `app/services/org_roles.py` — see that module for
    why access needs two independent checks (can this role write at all? does
    it administer *this* domain?) rather than the single rank ordering
    `require_org_role` below still offers for anything that still wants it.
"""

import uuid
from dataclasses import dataclass
from typing import Optional, Type, TypeVar

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.services import org_roles

T = TypeVar("T")

# Legacy numeric ordering. `require_org_role` below is the only consumer, and
# nothing in this codebase actually calls `require_org_role` — every real gate
# uses `can_write` / `is_domain_admin` instead, which express things a single
# rank cannot (a billing manager outranks nobody and administers one domain).
# Kept for API completeness rather than deleted out from under any caller a
# future router might add.
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


def can_write(org_ctx: Optional["OrgContext"]) -> bool:
    """
    Whether the caller may create or change anything at all.

    `None` (no `X-Org-ID` header — the personal-workspace path) always passes:
    a solo user is never restricted from their own resources. Inside an org,
    this is the single check every former `org_ctx.role == "viewer"` site in
    the codebase now makes — and because it is a set membership test against
    the role catalogue rather than a literal string comparison, a new
    read-only role (auditor, client_guest) is blocked here automatically
    without every call site needing to be told about it individually.
    """
    return org_roles.can_write(org_ctx.role if org_ctx else None)


def is_domain_admin(org_ctx: Optional["OrgContext"], domain: str) -> bool:
    """
    Whether the caller administers `domain` — the string a router declares for
    itself, e.g. `"engineering"` or `"billing"` — in this org.

    Replaces the old `org_ctx.role not in ("owner", "admin")` literal. Owner
    and admin still pass for every domain (they carry `domains == "*"` in the
    registry); a specialist role like `engineering_lead` or `billing_manager`
    passes only for the one domain it was actually given, which is the entire
    point of having specialist roles rather than a second flavour of admin.
    """
    return org_roles.is_domain_admin(org_ctx.role if org_ctx else None, domain)


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
