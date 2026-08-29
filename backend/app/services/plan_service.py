"""
Plan enforcement and usage tracking service.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import User, UsageLimit
from app.core.plans import get_resource_limit, FREE_TIER_LIMITS


class PlanService:
    """Service for plan enforcement and usage tracking."""

    @staticmethod
    def check_resource_limit(
        user: User,
        resource_type: str,
        db: Session,
    ) -> None:
        """
        Check if user can create a new resource of the given type.

        Raises HTTPException 402 if limit exceeded.

        Args:
            user: User attempting to create resource
            resource_type: One of: projects, agents, pods, skills,
                          github_connections, jira_connections, deployed_projects
            db: Database session
        """
        limit = get_resource_limit(user, resource_type)

        # No limit (unlimited plan)
        if limit is None:
            return

        # Get current usage
        usage = db.query(UsageLimit).filter(UsageLimit.user_id == user.id).first()
        if not usage:
            # Create usage record if doesn't exist
            usage = UsageLimit(user_id=user.id)
            db.add(usage)
            db.commit()
            db.refresh(usage)

        # Get current count
        count_field = f"{resource_type}_count"
        current_count = getattr(usage, count_field, 0)

        # Check limit
        if current_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "plan_limit_exceeded",
                    "message": f"Your Free plan allows {limit} {resource_type}. Upgrade to Teams for unlimited access.",
                    "resource_type": resource_type,
                    "current": current_count,
                    "limit": limit,
                }
            )

    @staticmethod
    def increment_usage(
        user_id,
        resource_type: str,
        db: Session,
    ) -> None:
        """
        Increment usage counter for a resource type.

        Args:
            user_id: User ID
            resource_type: Resource type to increment
            db: Database session
        """
        usage = db.query(UsageLimit).filter(UsageLimit.user_id == user_id).first()
        if not usage:
            usage = UsageLimit(user_id=user_id)
            db.add(usage)

        count_field = f"{resource_type}_count"
        current = getattr(usage, count_field, 0)
        setattr(usage, count_field, current + 1)
        db.commit()

    @staticmethod
    def decrement_usage(
        user_id,
        resource_type: str,
        db: Session,
    ) -> None:
        """
        Decrement usage counter for a resource type.

        Args:
            user_id: User ID
            resource_type: Resource type to decrement
            db: Database session
        """
        usage = db.query(UsageLimit).filter(UsageLimit.user_id == user_id).first()
        if usage:
            count_field = f"{resource_type}_count"
            current = getattr(usage, count_field, 0)
            setattr(usage, count_field, max(0, current - 1))
            db.commit()

    @staticmethod
    def get_usage_summary(
        user_id,
        db: Session,
    ) -> dict:
        """
        Get usage summary for a user (Free tier dashboard).

        Returns:
            {
                "projects": {"used": 1, "limit": 1},
                "agents": {"used": 3, "limit": 5},
                ...
            }
        """
        usage = db.query(UsageLimit).filter(UsageLimit.user_id == user_id).first()
        if not usage:
            usage = UsageLimit(user_id=user_id)
            db.add(usage)
            db.commit()
            db.refresh(usage)

        return {
            "projects": {
                "used": usage.projects_count,
                "limit": FREE_TIER_LIMITS["projects"]
            },
            "agents": {
                "used": usage.agents_count,
                "limit": FREE_TIER_LIMITS["agents"]
            },
            "pods": {
                "used": usage.pods_count,
                "limit": FREE_TIER_LIMITS["pods"]
            },
            "skills": {
                "used": usage.skills_count,
                "limit": FREE_TIER_LIMITS["skills"]
            },
            "github_connections": {
                "used": usage.github_connections_count,
                "limit": FREE_TIER_LIMITS["github_connections"]
            },
            "jira_connections": {
                "used": usage.jira_connections_count,
                "limit": FREE_TIER_LIMITS["jira_connections"]
            },
            "deployed_projects": {
                "used": usage.deployed_projects_count,
                "limit": FREE_TIER_LIMITS["deployed_projects"]
            },
        }


# Singleton instance
plan_service = PlanService()
