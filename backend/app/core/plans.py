"""
Plan system constants and utilities.
"""

from app.models import User, Organization, UserPlanType, OrgPlanType


# ── Platform Admin ────────────────────────────────────────────────────────────
PLATFORM_ADMIN_EMAIL = "harshilhk@evolune.in"


# ── Free Tier Limits ──────────────────────────────────────────────────────────
FREE_TIER_LIMITS = {
    "projects": 1,
    "agents": 5,
    "pods": 1,
    "skills": 10,
    "github_connections": 1,
    "jira_connections": 1,
    "deployed_projects": 1,
}


# ── Helper Functions ──────────────────────────────────────────────────────────

def is_platform_admin(user: User) -> bool:
    """Check if user is platform admin."""
    return user.email == PLATFORM_ADMIN_EMAIL


def is_free_tier(user: User) -> bool:
    """Check if user is on free tier."""
    return user.plan_type == UserPlanType.free and not user.is_org_member


def is_legacy_org(org: Organization) -> bool:
    """Check if organization is legacy (grandfathered)."""
    return org.plan_type == OrgPlanType.legacy


def get_resource_limit(user: User, resource_type: str) -> int | None:
    """
    Get the limit for a resource type based on user's plan.

    Returns:
        int: limit count
        None: unlimited (Teams/Enterprise/Legacy)
    """
    # Platform admin = unlimited
    if is_platform_admin(user):
        return None

    # Org members inherit org limits
    if user.is_org_member:
        return None  # Org plans have no limits

    # Free tier users have limits
    if user.plan_type == UserPlanType.free:
        return FREE_TIER_LIMITS.get(resource_type)

    # Teams/Enterprise users (without org) = unlimited
    return None
