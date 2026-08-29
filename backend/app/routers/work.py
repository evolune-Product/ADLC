"""
Work router — generic, non-engineering work requests.

Routes
------
GET    /work/                → list, filterable by department/team/status/assignee
POST   /work/                → create a work request
GET    /work/{id}            → get one
PUT    /work/{id}            → update mutable fields
POST   /work/{id}/assign     → assign to a user and/or agent
PUT    /work/{id}/status     → move status, valid-transition enforced
DELETE /work/{id}            → cancel (soft — sets status to cancelled)

Tenant isolation: every query filters by `organization_id` from OrgContext —
never a bare user_id. Requires an org context; Work is an org-scoped concept
(a personal workspace has no departments/teams to route it through).
"""
import datetime as dt
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agent import Agent
from app.models.department import Department, Team
from app.models.user import User
from app.models.work import Work
from app.routers._helpers import OrgContext, can_write, get_optional_org
from app.routers.auth import get_current_user
from app.schemas.work import WorkAssign, WorkCreate, WorkOut, WorkStatusUpdate, WorkUpdate
from app.services.work_service import InvalidTransition, apply_transition

router = APIRouter()


def _require_org(org_ctx: Optional[OrgContext]) -> OrgContext:
    if org_ctx is None:
        raise HTTPException(status_code=400, detail="This action requires an org context (X-Org-ID header)")
    return org_ctx


def _get_work_or_404(db: Session, org_ctx: OrgContext, work_id: uuid.UUID) -> Work:
    work = db.query(Work).filter(Work.id == work_id, Work.organization_id == org_ctx.org_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work item not found")
    return work


def _validate_dept_team(db: Session, org_ctx: OrgContext, department_id, team_id) -> None:
    if department_id is not None:
        dept = db.query(Department).filter(
            Department.id == department_id, Department.organization_id == org_ctx.org_id,
        ).first()
        if not dept:
            raise HTTPException(status_code=422, detail="department_id does not belong to this organization")
    if team_id is not None:
        team = db.query(Team).filter(
            Team.id == team_id, Team.organization_id == org_ctx.org_id,
        ).first()
        if not team:
            raise HTTPException(status_code=422, detail="team_id does not belong to this organization")
        if department_id is not None and str(team.department_id) != str(department_id):
            raise HTTPException(status_code=422, detail="team_id does not belong to department_id")


def _validate_assignee(db: Session, org_ctx: OrgContext, assigned_agent_id) -> None:
    if assigned_agent_id is not None:
        agent = db.query(Agent).filter(Agent.id == assigned_agent_id, Agent.org_id == org_ctx.org_id).first()
        if not agent:
            raise HTTPException(status_code=422, detail="assigned_agent_id does not belong to this organization")


@router.get("/", response_model=List[WorkOut])
def list_work(
    department_id: Optional[uuid.UUID] = None,
    team_id: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = None,
    assigned_user_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    q = db.query(Work).filter(Work.organization_id == org_ctx.org_id)
    if department_id:
        q = q.filter(Work.department_id == department_id)
    if team_id:
        q = q.filter(Work.team_id == team_id)
    if status_filter:
        q = q.filter(Work.status == status_filter)
    if assigned_user_id:
        q = q.filter(Work.assigned_user_id == assigned_user_id)
    return q.order_by(Work.created_at.desc()).all()


@router.post("/", response_model=WorkOut, status_code=status.HTTP_201_CREATED)
def create_work(
    body: WorkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    if not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Read-only role cannot open a work request")
    _validate_dept_team(db, org_ctx, body.department_id, body.team_id)
    _validate_assignee(db, org_ctx, body.assigned_agent_id)

    initial_status = "new"
    if body.assigned_user_id or body.assigned_agent_id:
        initial_status = "assigned"

    work = Work(
        organization_id=org_ctx.org_id,
        department_id=body.department_id,
        team_id=body.team_id,
        requester_user_id=current_user.id,
        type=body.type,
        title=body.title,
        description=body.description,
        priority=body.priority,
        context=body.context or {},
        status=initial_status,
        assigned_user_id=body.assigned_user_id,
        assigned_agent_id=body.assigned_agent_id,
    )
    db.add(work)
    db.commit()
    db.refresh(work)
    return work


@router.get("/{work_id}", response_model=WorkOut)
def get_work(
    work_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    return _get_work_or_404(db, org_ctx, work_id)


@router.put("/{work_id}", response_model=WorkOut)
def update_work(
    work_id: uuid.UUID,
    body: WorkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    if not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Read-only role cannot update a work request")
    work = _get_work_or_404(db, org_ctx, work_id)
    data = body.model_dump(exclude_unset=True)
    dept = data.get("department_id", work.department_id)
    team = data.get("team_id", work.team_id)
    if "department_id" in data or "team_id" in data:
        _validate_dept_team(db, org_ctx, dept, team)
    for field, value in data.items():
        setattr(work, field, value)
    db.commit()
    db.refresh(work)
    return work


@router.post("/{work_id}/assign", response_model=WorkOut)
def assign_work(
    work_id: uuid.UUID,
    body: WorkAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    if not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Read-only role cannot assign a work request")
    work = _get_work_or_404(db, org_ctx, work_id)
    _validate_assignee(db, org_ctx, body.assigned_agent_id)
    if body.assigned_user_id is not None:
        work.assigned_user_id = body.assigned_user_id
    if body.assigned_agent_id is not None:
        work.assigned_agent_id = body.assigned_agent_id
    if work.status == "new" and (work.assigned_user_id or work.assigned_agent_id):
        work.status = apply_transition(work.status, "assigned")
    db.commit()
    db.refresh(work)
    return work


@router.put("/{work_id}/status", response_model=WorkOut)
def update_work_status(
    work_id: uuid.UUID,
    body: WorkStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    if not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Read-only role cannot change work item status")
    work = _get_work_or_404(db, org_ctx, work_id)
    try:
        work.status = apply_transition(work.status, body.status)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if body.approval_state is not None:
        work.approval_state = body.approval_state
    if work.status in ("completed", "failed", "cancelled") and work.completed_at is None:
        work.completed_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    db.refresh(work)
    return work


@router.delete("/{work_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_work(
    work_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    if not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Read-only role cannot cancel a work request")
    work = _get_work_or_404(db, org_ctx, work_id)
    try:
        work.status = apply_transition(work.status, "cancelled")
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    work.completed_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
