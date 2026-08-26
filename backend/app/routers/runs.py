import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.run import Run, RunStep, Approval
from app.models.project import Project
from app.schemas.run import RunCreate, RunOut, RunStepOut, ApproveBody
from app.routers.auth import get_current_user
from app.routers._helpers import OrgContext, can_write, get_optional_org, owner_filter
from app.models.user import User
from app.services.notification_service import emit_run_event
from app.services import policy_service

router = APIRouter()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _step_out(s: RunStep) -> RunStepOut:
    return RunStepOut(
        id=s.id,
        run_id=s.run_id,
        agent_role=s.agent_role,
        step_name=s.step_name,
        status=s.status,
        input=s.input,
        output=s.output,
        log=s.log,
        duration_ms=s.duration_ms,
        created_at=s.created_at,
    )


def _run_out(r: Run) -> RunOut:
    deploy_targets = []
    if r.project and r.project.deploy_targets:
        deploy_targets = r.project.deploy_targets
    return RunOut(
        id=r.id,
        project_id=r.project_id,
        ticket_id=r.ticket_id,
        pod_id=r.pod_id,
        status=r.status,
        branch_name=r.branch_name,
        pr_url=r.pr_url,
        pr_number=r.pr_number,
        current_step=r.current_step,
        error_message=r.error_message,
        retry_count=r.retry_count,
        current_env_index=r.current_env_index if r.current_env_index is not None else -1,
        deploy_targets=deploy_targets,
        steps=[_step_out(s) for s in r.steps],
        started_at=r.started_at,
        completed_at=r.completed_at,
        created_at=r.created_at,
    )


def _assert_project_access(
    project_id: uuid.UUID,
    current_user,
    db: Session,
    org_ctx: Optional[OrgContext] = None,
) -> Project:
    p = db.query(Project).filter(
        Project.id == project_id,
        owner_filter(Project, current_user, org_ctx),
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


# ─── Global runs ─────────────────────────────────────────────────────────────

@router.get("/runs", response_model=List[RunOut])
def list_all_runs(
    run_status: Optional[str] = Query(None),
    project_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """List all runs across projects that belong to the current user / org."""
    user_projects = db.query(Project).filter(owner_filter(Project, current_user, org_ctx)).all()
    user_project_ids = [p.id for p in user_projects]

    q = db.query(Run).filter(Run.project_id.in_(user_project_ids))
    if project_id:
        q = q.filter(Run.project_id == project_id)
    if run_status:
        q = q.filter(Run.status == run_status)
    runs = q.order_by(Run.created_at.desc()).limit(100).all()
    return [_run_out(r) for r in runs]


@router.post("/runs", response_model=RunOut, status_code=status.HTTP_201_CREATED)
def create_run(
    body: RunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """Trigger a new agent run for a project ticket."""
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot trigger runs")
    _assert_project_access(body.project_id, current_user, db, org_ctx)

    run = create_and_dispatch_run(
        db,
        project_id=body.project_id,
        ticket_id=body.ticket_id,
        pod_id=body.pod_id,
        triggered_by=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
    )
    return _run_out(run)


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _assert_project_access(run.project_id, current_user, db, org_ctx)
    return _run_out(run)


@router.get("/runs/{run_id}/steps", response_model=List[RunStepOut])
def get_run_steps(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _assert_project_access(run.project_id, current_user, db, org_ctx)
    steps = db.query(RunStep).filter(RunStep.run_id == run_id).order_by(RunStep.created_at).all()
    return [_step_out(s) for s in steps]


@router.get("/runs/{run_id}/diff")
def get_run_diff(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """Return per-file patches for the PR associated with this run."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _assert_project_access(run.project_id, current_user, db, org_ctx)

    from app.services.pr_diff_service import DiffError, get_pr_files
    try:
        return get_pr_files(db, run)
    except DiffError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


def create_and_dispatch_run(
    db: Session,
    *,
    project_id: uuid.UUID,
    ticket_id: Optional[uuid.UUID],
    pod_id: uuid.UUID,
    triggered_by: uuid.UUID,
    org_id=None,
    retry_count: int = 0,
) -> Run:
    """
    Create a run and start it — or hold it in the queue if the project is at its
    concurrency limit.

    The single creation path, for the same reason `apply_run_decision` is the
    single approval path. A run can be started from the Runs page, from a chat
    mention, from CI through the public API, or by another agent over MCP, and a
    concurrency cap that only one of those four respects is not a cap.

    A run held back stays at `queued` and is simply not dispatched;
    `policy_service.promote_next` starts it when a slot frees. That is why the
    caller gets a `Run` back either way and should read `run.status` rather than
    assuming work began.
    """
    run = Run(
        project_id=project_id,
        ticket_id=ticket_id,
        pod_id=pod_id,
        status="queued",
        triggered_by=triggered_by,
        retry_count=retry_count,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    decision = policy_service.check_concurrency(
        db, project_id=project_id, org_id=org_id, exclude_run_id=run.id,
    )
    if decision.reason:
        # The queue itself is full. Refusing is kinder than accepting work that
        # would sit for hours, and it surfaces a misconfigured limit immediately.
        db.delete(run)
        db.commit()
        raise HTTPException(status_code=429, detail=decision.reason)

    if not decision.admitted:
        return run   # held at `queued`; promote_next will pick it up

    try:
        from app.tasks.run_tasks import trigger_run_until_approval
        trigger_run_until_approval.delay(str(run.id))
    except Exception as e:
        run.status = "failed"
        run.error_message = f"Failed to dispatch task: {str(e)}"
        db.commit()

    db.refresh(run)
    return run


def apply_run_decision(
    db: Session,
    *,
    run_id: uuid.UUID,
    decision: str,
    comment: Optional[str],
    current_user: User,
    org_ctx: Optional[OrgContext] = None,
) -> Run:
    """
    The approval gate, callable from anywhere.

    Extracted from the endpoint so the workspace chat surface can approve a run
    without reimplementing the checks. Two code paths that can release a deploy
    is one too many: the access check, the status check, the Approval row and
    the resume dispatch all have to be the same or the audit trail is fiction.

    Accepts the chat verbs (`approve` / `reject`) as aliases for the stored
    decision values, because `/reject` is what a human types and
    `changes_requested` is what the column holds.
    """
    decision = {"approve": "approved", "reject": "changes_requested"}.get(decision, decision)

    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot approve runs")
    _assert_project_access(run.project_id, current_user, db, org_ctx)

    if run.status != "awaiting_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run is not awaiting approval (status: {run.status})",
        )

    if decision not in ("approved", "changes_requested"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="decision must be 'approved' or 'changes_requested'",
        )

    approval = Approval(
        run_id=run_id,
        reviewer_id=current_user.id,
        decision=decision,
        comment=comment,
    )
    db.add(approval)
    db.commit()

    try:
        from app.tasks.run_tasks import resume_after_approval
        resume_after_approval.delay(str(run_id), decision, comment)
    except Exception as e:
        run.status = "failed"
        run.error_message = f"Failed to dispatch resume task: {str(e)}"
        db.commit()

    db.refresh(run)
    return run


@router.post("/runs/{run_id}/approve", response_model=RunOut)
def approve_run(
    run_id: uuid.UUID,
    body: ApproveBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    run = apply_run_decision(
        db, run_id=run_id, decision=body.decision, comment=body.comment,
        current_user=current_user, org_ctx=org_ctx,
    )
    return _run_out(run)


@router.post("/runs/{run_id}/retry", response_model=RunOut, status_code=status.HTTP_201_CREATED)
def retry_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    original = db.query(Run).filter(Run.id == run_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Run not found")
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot retry runs")
    _assert_project_access(original.project_id, current_user, db, org_ctx)

    new_run = create_and_dispatch_run(
        db,
        project_id=original.project_id,
        ticket_id=original.ticket_id,
        pod_id=original.pod_id,
        triggered_by=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        retry_count=original.retry_count + 1,
    )
    return _run_out(new_run)


@router.delete("/runs/{run_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot cancel runs")
    _assert_project_access(run.project_id, current_user, db, org_ctx)

    if run.status not in ("queued", "running"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only queued or running runs can be cancelled",
        )
    run.status       = "failed"
    run.error_message = "Cancelled by user"
    run.completed_at  = datetime.now(timezone.utc)
    db.commit()


# ─── Project-scoped runs ──────────────────────────────────────────────────────

@router.get("/projects/{project_id}/runs", response_model=List[RunOut])
def list_project_runs(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _assert_project_access(project_id, current_user, db, org_ctx)
    runs = (
        db.query(Run)
        .filter(Run.project_id == project_id)
        .order_by(Run.created_at.desc())
        .all()
    )
    return [_run_out(r) for r in runs]
