"""
Admin router
------------
Platform admin endpoints for manual plan management and platform stats.
Only accessible by platform admin (harshilhk@evolune.in).

Routes
------
POST   /admin/users/{user_id}/set-plan      → manually set user plan type
POST   /admin/orgs/{org_id}/set-plan        → manually set organization plan type
GET    /admin/stats                         → platform-wide statistics
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User, UserPlanType
from app.models.organization import Organization, OrgPlanType
from app.routers.auth import get_current_user
from app.core.plans import is_platform_admin

router = APIRouter()


# ─── Request/Response Schemas ────────────────────────────────────────────────


class SetPlanRequest(BaseModel):
    plan_type: str


class PlatformStatsResponse(BaseModel):
    total_users: int
    total_organizations: int
    free_users: int
    teams_users: int
    enterprise_users: int
    teams_orgs: int
    enterprise_orgs: int
    legacy_orgs: int


# ─── Platform Admin Dependency ───────────────────────────────────────────────


def require_platform_admin(current_user: User = Depends(get_current_user)):
    """Dependency that ensures current user is platform admin."""
    if not is_platform_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required"
        )
    return current_user


# ─── Routes ──────────────────────────────────────────────────────────────────


@router.post("/admin/users/{user_id}/set-plan")
def set_user_plan(
    user_id: uuid.UUID,
    body: SetPlanRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    """
    Manually set a user's plan type (for testing or migrations).
    Platform admin only.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate plan type
    try:
        plan_type = UserPlanType(body.plan_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan type. Must be one of: free, teams, enterprise"
        )

    user.plan_type = plan_type
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "user_id": str(user.id),
        "email": user.email,
        "plan_type": user.plan_type.value,
    }


@router.post("/admin/orgs/{org_id}/set-plan")
def set_org_plan(
    org_id: uuid.UUID,
    body: SetPlanRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    """
    Manually set an organization's plan type (for testing or migrations).
    Platform admin only.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Validate plan type
    try:
        plan_type = OrgPlanType(body.plan_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan type. Must be one of: teams, enterprise, legacy"
        )

    org.plan_type = plan_type
    db.commit()
    db.refresh(org)

    return {
        "success": True,
        "org_id": str(org.id),
        "name": org.name,
        "plan_type": org.plan_type.value,
    }


@router.get("/admin/stats", response_model=PlatformStatsResponse)
def get_platform_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    """
    Get platform-wide statistics.
    Platform admin only.
    """
    total_users = db.query(User).count()
    total_orgs = db.query(Organization).count()

    free_users = db.query(User).filter(User.plan_type == UserPlanType.free).count()
    teams_users = db.query(User).filter(User.plan_type == UserPlanType.teams).count()
    enterprise_users = db.query(User).filter(User.plan_type == UserPlanType.enterprise).count()

    teams_orgs = db.query(Organization).filter(Organization.plan_type == OrgPlanType.teams).count()
    enterprise_orgs = db.query(Organization).filter(Organization.plan_type == OrgPlanType.enterprise).count()
    legacy_orgs = db.query(Organization).filter(Organization.plan_type == OrgPlanType.legacy).count()

    return PlatformStatsResponse(
        total_users=total_users,
        total_organizations=total_orgs,
        free_users=free_users,
        teams_users=teams_users,
        enterprise_users=enterprise_users,
        teams_orgs=teams_orgs,
        enterprise_orgs=enterprise_orgs,
        legacy_orgs=legacy_orgs,
    )
