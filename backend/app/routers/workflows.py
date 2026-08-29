"""
Workflow router — CRUD for Workflow, plus execute/resume for
WorkflowExecution. The engine itself lives in services/workflow_engine.py.

Tenant isolation: every query filters organization_id from OrgContext.
Workflow is org-scoped only (no personal-workspace flavor — a solo user has
no departments/workflows to automate).
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.department import Department
from app.models.user import User
from app.models.work import Work
from app.models.workflow import Workflow, WorkflowExecution
from app.routers._helpers import OrgContext, can_write, get_optional_org
from app.routers.auth import get_current_user
from app.schemas.workflow import (
    WorkflowCreate, WorkflowExecuteRequest, WorkflowExecutionDetailOut,
    WorkflowExecutionOut, WorkflowOut, WorkflowUpdate,
)
from app.services import workflow_engine

router = APIRouter()


def _require_org(org_ctx: Optional[OrgContext]) -> OrgContext:
    if org_ctx is None:
        raise HTTPException(status_code=400, detail="This action requires an org context (X-Org-ID header)")
    return org_ctx


def _get_workflow_or_404(db: Session, org_ctx: OrgContext, workflow_id: uuid.UUID) -> Workflow:
    wf = db.query(Workflow).filter(Workflow.id == workflow_id, Workflow.organization_id == org_ctx.org_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


def _validate_definition(definition: dict) -> None:
    if not isinstance(definition, dict):
        raise HTTPException(status_code=422, detail="definition must be an object")
    nodes = definition.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise HTTPException(status_code=422, detail="definition.nodes must be a non-empty list")
    ids = set()
    for n in nodes:
        if not isinstance(n, dict) or "id" not in n or "type" not in n:
            raise HTTPException(status_code=422, detail="every node needs an 'id' and a 'type'")
        ids.add(n["id"])
    start = definition.get("start_node_id")
    if not start or start not in ids:
        raise HTTPException(status_code=422, detail="definition.start_node_id must reference an existing node id")


@router.get("/", response_model=List[WorkflowOut])
def list_workflows(
    department_id: Optional[uuid.UUID] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    q = db.query(Workflow).filter(Workflow.organization_id == org_ctx.org_id)
    if department_id:
        q = q.filter(Workflow.department_id == department_id)
    if is_active is not None:
        q = q.filter(Workflow.is_active == is_active)
    return q.order_by(Workflow.created_at.desc()).all()


@router.post("/", response_model=WorkflowOut, status_code=status.HTTP_201_CREATED)
def create_workflow(
    body: WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    if not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Read-only role cannot create a workflow")
    _validate_definition(body.definition)
    if body.department_id is not None:
        dept = db.query(Department).filter(
            Department.id == body.department_id, Department.organization_id == org_ctx.org_id,
        ).first()
        if not dept:
            raise HTTPException(status_code=422, detail="department_id does not belong to this organization")

    wf = Workflow(
        organization_id=org_ctx.org_id,
        department_id=body.department_id,
        name=body.name,
        description=body.description,
        trigger_type=body.trigger_type,
        definition=body.definition,
        is_active=body.is_active,
        version=1,
        created_by=current_user.id,
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


@router.get("/{workflow_id}", response_model=WorkflowOut)
def get_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    return _get_workflow_or_404(db, org_ctx, workflow_id)


@router.put("/{workflow_id}", response_model=WorkflowOut)
def update_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    if not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Read-only role cannot update a workflow")
    wf = _get_workflow_or_404(db, org_ctx, workflow_id)
    data = body.model_dump(exclude_unset=True)
    if "definition" in data:
        _validate_definition(data["definition"])
        wf.version += 1
    if "department_id" in data and data["department_id"] is not None:
        dept = db.query(Department).filter(
            Department.id == data["department_id"], Department.organization_id == org_ctx.org_id,
        ).first()
        if not dept:
            raise HTTPException(status_code=422, detail="department_id does not belong to this organization")
    for field, value in data.items():
        setattr(wf, field, value)
    db.commit()
    db.refresh(wf)
    return wf


@router.post("/{workflow_id}/deactivate", response_model=WorkflowOut)
def deactivate_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    if not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Read-only role cannot deactivate a workflow")
    wf = _get_workflow_or_404(db, org_ctx, workflow_id)
    wf.is_active = False
    db.commit()
    db.refresh(wf)
    return wf


@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionOut, status_code=status.HTTP_201_CREATED)
def execute_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    if not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Read-only role cannot execute a workflow")
    wf = _get_workflow_or_404(db, org_ctx, workflow_id)
    if not wf.is_active:
        raise HTTPException(status_code=409, detail="Workflow is not active")

    work = None
    if body.work_id is not None:
        work = db.query(Work).filter(Work.id == body.work_id, Work.organization_id == org_ctx.org_id).first()
        if not work:
            raise HTTPException(status_code=422, detail="work_id does not belong to this organization")

    execution = workflow_engine.start_execution(db, wf, work=work, initial_context=body.initial_context)
    return execution


@router.get("/{workflow_id}/executions", response_model=List[WorkflowExecutionOut])
def list_workflow_executions(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    _get_workflow_or_404(db, org_ctx, workflow_id)
    return (
        db.query(WorkflowExecution)
        .filter(WorkflowExecution.workflow_id == workflow_id, WorkflowExecution.organization_id == org_ctx.org_id)
        .order_by(WorkflowExecution.started_at.desc())
        .all()
    )


@router.get("/executions/{execution_id}", response_model=WorkflowExecutionDetailOut)
def get_workflow_execution(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_ctx = _require_org(org_ctx)
    execution = db.query(WorkflowExecution).filter(
        WorkflowExecution.id == execution_id, WorkflowExecution.organization_id == org_ctx.org_id,
    ).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.post("/executions/{execution_id}/resume", response_model=WorkflowExecutionOut)
def resume_workflow_execution(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Manually resume an execution waiting on a human_task/approval node —
    same authorization rigor as any other state-mutating action. Normally
    resume happens automatically when the linked Work item's status moves
    to "completed" (see routers/work.py); this exists for an operator who
    needs to nudge a stuck execution without touching the Work item.
    """
    org_ctx = _require_org(org_ctx)
    if not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Read-only role cannot resume a workflow execution")
    execution = db.query(WorkflowExecution).filter(
        WorkflowExecution.id == execution_id, WorkflowExecution.organization_id == org_ctx.org_id,
    ).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.status not in ("running", "awaiting_approval"):
        raise HTTPException(status_code=409, detail=f"Execution is '{execution.status}', not waiting on anything")
    return workflow_engine.resume_execution(db, execution)
