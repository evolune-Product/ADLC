from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.run import Run
from app.models.project import Project
from app.models.skill import Skill
from app.routers.auth import get_current_user
from app.routers._helpers import get_optional_org, owner_filter, OrgContext
from app.models.user import User

router = APIRouter()


def _run_summary(r: Run) -> dict:
    return {
        "id":           str(r.id),
        "project_id":   str(r.project_id),
        "status":       r.status,
        "branch_name":  r.branch_name,
        "pr_url":       r.pr_url,
        "pr_number":    r.pr_number,
        "current_step": r.current_step,
        "error_message":r.error_message,
        "retry_count":  r.retry_count,
        "started_at":   r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "created_at":   r.created_at.isoformat() if r.created_at else None,
    }


@router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """Return headline stats + last 10 runs for the dashboard."""
    user_projects = (
        db.query(Project)
        .filter(
            owner_filter(Project, current_user, org_ctx),
            Project.status == "active",
        )
        .all()
    )
    project_ids = [p.id for p in user_projects]

    active_runs = (
        db.query(Run)
        .filter(Run.project_id.in_(project_ids), Run.status.in_(["queued", "running"]))
        .count()
        if project_ids else 0
    )
    pending_approvals = (
        db.query(Run)
        .filter(Run.project_id.in_(project_ids), Run.status == "awaiting_approval")
        .count()
        if project_ids else 0
    )
    skills_count = (
        db.query(Skill)
        .filter(owner_filter(Skill, current_user, org_ctx), Skill.is_active == True)
        .count()
    )
    recent_runs = (
        db.query(Run)
        .filter(Run.project_id.in_(project_ids))
        .order_by(Run.created_at.desc())
        .limit(10)
        .all()
        if project_ids else []
    )

    return {
        "total_projects":    len(user_projects),
        "active_runs":       active_runs,
        "pending_approvals": pending_approvals,
        "skills_configured": skills_count,
        "recent_runs":       [_run_summary(r) for r in recent_runs],
    }
