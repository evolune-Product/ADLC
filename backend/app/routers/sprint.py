"""
AI Sprint Planner router. See services/sprint_planner_service.py for the why.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents._common import byo_llm
from app.database import get_db
from app.models.project import Project
from app.models.sprint import SprintPlan
from app.routers._helpers import OrgContext, get_optional_org, get_or_404
from app.routers.auth import get_current_user
from app.services import metering_service, sprint_planner_service
from app.models.user import User

router = APIRouter()


class SprintPlanRequest(BaseModel):
    capacity_points: int = Field(..., ge=1, le=500)
    write_back: bool = False


def _estimate_out(e):
    return {
        "id": str(e.id), "ticket_id": str(e.ticket_id),
        "jira_id": e.ticket.jira_id, "title": e.ticket.title,
        "story_points": e.story_points, "complexity_reasoning": e.complexity_reasoning,
        "depends_on": e.depends_on, "included_in_sprint": e.included_in_sprint, "risk": e.risk,
    }


def _plan_out(plan: SprintPlan):
    return {
        "id": str(plan.id), "project_id": str(plan.project_id),
        "capacity_points": plan.capacity_points, "committed_points": plan.committed_points,
        "health": plan.health, "summary": plan.summary, "written_back": plan.written_back,
        "created_at": plan.created_at.isoformat(),
        "estimates": [_estimate_out(e) for e in plan.estimates],
    }


@router.get("/projects/{project_id}/sprint-plan")
def latest_sprint_plan(
    project_id: uuid.UUID, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    project = get_or_404(Project, project_id, current_user.id, db, "Project", org_ctx)
    plan = (db.query(SprintPlan).filter(SprintPlan.project_id == project.id)
            .order_by(SprintPlan.created_at.desc()).first())
    return _plan_out(plan) if plan else None


@router.get("/projects/{project_id}/sprint-plan/backlog")
def sprint_backlog(
    project_id: uuid.UUID, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    project = get_or_404(Project, project_id, current_user.id, db, "Project", org_ctx)
    tickets = sprint_planner_service.backlog(db, project.id)
    return {"count": len(tickets), "tickets": [
        {"id": str(t.id), "jira_id": t.jira_id, "title": t.title,
         "type": t.type, "priority": t.priority} for t in tickets
    ]}


@router.post("/projects/{project_id}/sprint-plan")
def create_sprint_plan(
    project_id: uuid.UUID, body: SprintPlanRequest, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    project = get_or_404(Project, project_id, current_user.id, db, "Project", org_ctx)

    quota = metering_service.check_quota(db, project.user_id, project.org_id)
    if not quota.allowed:
        raise HTTPException(402, quota.reason or "Plan limit reached.")

    provider, key = byo_llm(db, project.user_id, project.org_id)
    try:
        plan = sprint_planner_service.plan_sprint(
            db, project, capacity_points=body.capacity_points,
            user_id=project.user_id, org_id=project.org_id,
            byo_provider=provider, byo_key=key,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    if body.write_back:
        sprint_planner_service.write_back_estimates(db, plan)

    return _plan_out(plan)


@router.post("/projects/{project_id}/sprint-plan/{plan_id}/write-back")
def write_back_sprint_plan(
    project_id: uuid.UUID, plan_id: uuid.UUID, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    project = get_or_404(Project, project_id, current_user.id, db, "Project", org_ctx)
    plan = db.query(SprintPlan).filter(SprintPlan.id == plan_id, SprintPlan.project_id == project.id).first()
    if not plan:
        raise HTTPException(404, "Sprint plan not found")
    posted = sprint_planner_service.write_back_estimates(db, plan)
    return {"posted": posted}
