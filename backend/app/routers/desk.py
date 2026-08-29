"""
Company Desk — the command-center landing view.

GET  /desk           assembles pending work, pending approvals, recent
                      activity and a department summary, scoped to the
                      current OrgContext (or the personal workspace when no
                      X-Org-ID header is sent — departments/work items don't
                      exist outside an org, so those two sections come back
                      empty there rather than erroring).
POST /desk/request    plain, honest Work creation from free text. No NLU/
                      routing logic lives here — that is routing_service.py
                      (step 7), which this endpoint calls exactly the way
                      POST /work/ does, so a Desk-submitted request and a
                      Work-API-submitted request are routed identically.

Every query filters organization_id from OrgContext — never a bare user_id —
matching the rest of the Company OS routers.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import AuditLog
from app.models.department import Department, Team, TeamMember
from app.models.project import Project
from app.models.run import Run
from app.models.user import User
from app.models.work import Work
from app.routers._helpers import OrgContext, can_write, get_optional_org, owner_filter
from app.routers.audit import _build_audit_query, _log_out
from app.routers.auth import get_current_user
from app.schemas.desk import DeskRequestCreate
from app.schemas.work import WorkOut
from app.services.routing_service import route_work

router = APIRouter()


def _run_summary(r: Run) -> dict:
    return {
        "id": str(r.id),
        "project_id": str(r.project_id),
        "status": r.status,
        "pr_url": r.pr_url,
        "current_step": r.current_step,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("")
def get_desk(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    # ── Pending work assigned to me ────────────────────────────────────────
    pending_work: List[Work] = []
    department_summary: list[dict] = []

    if org_ctx:
        pending_work = (
            db.query(Work)
            .filter(
                Work.organization_id == org_ctx.org_id,
                Work.assigned_user_id == current_user.id,
                Work.status.in_(["assigned", "in_progress", "awaiting_input"]),
            )
            .order_by(Work.created_at.desc())
            .limit(50)
            .all()
        )

        departments = (
            db.query(Department)
            .filter(Department.organization_id == org_ctx.org_id, Department.status == "active")
            .order_by(Department.name)
            .all()
        )
        for dept in departments:
            active_work_count = (
                db.query(Work)
                .filter(
                    Work.organization_id == org_ctx.org_id,
                    Work.department_id == dept.id,
                    Work.status.notin_(["completed", "failed", "cancelled"]),
                )
                .count()
            )
            member_count = (
                db.query(TeamMember)
                .join(Team, Team.id == TeamMember.team_id)
                .filter(Team.department_id == dept.id)
                .count()
            )
            department_summary.append({
                "id": str(dept.id),
                "name": dept.name,
                "active_work_count": active_work_count,
                "member_count": member_count,
            })

    # ── Pending approvals — reuses the existing Run/governance path, not a
    # parallel notion of "approval". Work items awaiting_approval (including
    # ones the workflow engine's `approval` node created) are included too,
    # since they're real approval-shaped items a person needs to act on. ──
    project_ids = [p.id for p in db.query(Project.id).filter(owner_filter(Project, current_user, org_ctx)).all()]
    pending_run_approvals = (
        db.query(Run)
        .filter(Run.project_id.in_(project_ids), Run.status == "awaiting_approval")
        .order_by(Run.created_at.desc())
        .limit(20)
        .all()
        if project_ids else []
    )
    pending_work_approvals: List[Work] = []
    if org_ctx:
        pending_work_approvals = (
            db.query(Work)
            .filter(Work.organization_id == org_ctx.org_id, Work.status == "awaiting_approval")
            .order_by(Work.created_at.desc())
            .limit(20)
            .all()
        )

    # ── Recent activity — the existing AuditLog, same scoping audit.py uses ──
    recent_activity = (
        _build_audit_query(db, current_user, org_ctx)
        .order_by(AuditLog.created_at.desc())
        .limit(15)
        .all()
    )

    return {
        "pending_work": [WorkOut.model_validate(w).model_dump(mode="json") for w in pending_work],
        "pending_approvals": {
            "runs": [_run_summary(r) for r in pending_run_approvals],
            "work": [WorkOut.model_validate(w).model_dump(mode="json") for w in pending_work_approvals],
        },
        "recent_activity": [_log_out(l) for l in recent_activity],
        "department_summary": department_summary,
    }


@router.post("/request", response_model=WorkOut, status_code=status.HTTP_201_CREATED)
def create_desk_request(
    body: DeskRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Plain, honest creation — no AI/NLU here (that's a documented future
    step). Creates a Work(status="new", type="generic_request") row and runs
    it through the same rule-based routing every POST /work/ request gets.

    Work is an org-scoped concept (see work.py) — a free-text request typed
    from the personal workspace has no department structure to land in, so
    this requires an X-Org-ID header just like the Work API does.
    """
    if org_ctx is None:
        raise HTTPException(status_code=400, detail="This action requires an org context (X-Org-ID header)")
    if not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Read-only role cannot open a work request")

    work = Work(
        organization_id=org_ctx.org_id,
        requester_user_id=current_user.id,
        type="generic_request",
        title=body.title,
        description=body.description,
        status="new",
    )
    decision = route_work(db, work)
    if decision.department_id is not None:
        work.department_id = decision.department_id
    work.routing_confidence = decision.confidence
    work.routing_reasoning = decision.reasoning

    db.add(work)
    db.commit()
    db.refresh(work)
    return work
