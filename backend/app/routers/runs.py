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
from app.routers._helpers import get_optional_org, owner_filter, OrgContext
from app.models.user import User
from app.services.notification_service import emit_run_event

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
    if org_ctx and org_ctx.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot trigger runs")
    _assert_project_access(body.project_id, current_user, db, org_ctx)

    run = Run(
        project_id=body.project_id,
        ticket_id=body.ticket_id,
        pod_id=body.pod_id,
        status="queued",
        triggered_by=current_user.id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Dispatch Celery task
    try:
        from app.tasks.run_tasks import trigger_run_until_approval
        trigger_run_until_approval.delay(str(run.id))
    except Exception as e:
        run.status = "failed"
        run.error_message = f"Failed to dispatch task: {str(e)}"
        db.commit()

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

    if not run.pr_number:
        raise HTTPException(status_code=404, detail="No PR associated with this run")

    project = db.query(Project).filter(Project.id == run.project_id).first()
    if not project or not project.repo_connection_id or not project.repo_name:
        raise HTTPException(status_code=422, detail="Project has no repository configured")

    from app.models.connection import Connection
    from app.services.encryption import decrypt_token
    from github import Github

    conn = db.query(Connection).filter(Connection.id == project.repo_connection_id).first()
    if not conn or not conn.access_token:
        raise HTTPException(status_code=422, detail="Repository connection not found")

    try:
        token = decrypt_token(conn.access_token)
        repo  = Github(token).get_repo(project.repo_name)
        pr    = repo.get_pull(run.pr_number)
        return [
            {
                "filename":  f.filename,
                "status":    f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "patch":     f.patch or "",
            }
            for f in list(pr.get_files())[:20]  # cap at 20 files
        ]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch PR diff: {str(e)}")


@router.post("/runs/{run_id}/approve", response_model=RunOut)
def approve_run(
    run_id: uuid.UUID,
    body: ApproveBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if org_ctx and org_ctx.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot approve runs")
    _assert_project_access(run.project_id, current_user, db, org_ctx)

    if run.status != "awaiting_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run is not awaiting approval (status: {run.status})",
        )

    if body.decision not in ("approved", "changes_requested"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="decision must be 'approved' or 'changes_requested'",
        )

    # Record approval
    approval = Approval(
        run_id=run_id,
        reviewer_id=current_user.id,
        decision=body.decision,
        comment=body.comment,
    )
    db.add(approval)
    db.commit()

    # Dispatch resume task
    try:
        from app.tasks.run_tasks import resume_after_approval
        resume_after_approval.delay(str(run_id), body.decision, body.comment)
    except Exception as e:
        run.status = "failed"
        run.error_message = f"Failed to dispatch resume task: {str(e)}"
        db.commit()

    db.refresh(run)
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
    if org_ctx and org_ctx.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot retry runs")
    _assert_project_access(original.project_id, current_user, db, org_ctx)

    new_run = Run(
        project_id=original.project_id,
        ticket_id=original.ticket_id,
        pod_id=original.pod_id,
        status="queued",
        triggered_by=current_user.id,
        retry_count=original.retry_count + 1,
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)

    try:
        from app.tasks.run_tasks import trigger_run_until_approval
        trigger_run_until_approval.delay(str(new_run.id))
    except Exception as e:
        new_run.status = "failed"
        new_run.error_message = f"Failed to dispatch task: {str(e)}"
        db.commit()

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
    if org_ctx and org_ctx.role == "viewer":
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
