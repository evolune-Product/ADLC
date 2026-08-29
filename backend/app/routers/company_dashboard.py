"""
Company home dashboard — Company OS step 20.

Answers "how is the company doing", not "what do I need to act on right now"
(that is `desk.py` — see its module docstring and PulsePage's precedent for
why the two must stay separate pages). Every number here is a real
aggregate query against rows this platform already writes — Work,
WorkflowExecution/WorkflowExecutionStep, CompanyApi, Message, and
`metering_service`'s own usage accounting. No invented metrics, no
hardcoded placeholders: a block with nothing to show renders empty and says
so, the same rule Pulse's trust block follows.

Role scoping (spec: owner/admin org-wide, department_head their department's
slice, ordinary member only what's relevant to them) reuses the exact
patterns `_helpers.py` already established rather than inventing a fourth
access check:
  - owner/admin                → org-wide (`is_domain_admin` with any domain
    string; owner/admin carry `domains == "*"`)
  - heads >=1 department        → union of the departments they head
  - everyone else (`member`)    → only Work/executions assigned to or
    requested by them
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company_api import CompanyApi
from app.models.department import Department
from app.models.user import User
from app.models.work import Work
from app.models.workflow import Workflow, WorkflowExecution, WorkflowExecutionStep
from app.models.workspace import Channel, Message
from app.routers._helpers import OrgContext, get_optional_org, is_domain_admin
from app.routers.auth import get_current_user
from app.services import metering_service, workspace_service

router = APIRouter()


def _require_org(org_ctx: Optional[OrgContext]) -> OrgContext:
    if org_ctx is None:
        raise HTTPException(status_code=400, detail="The company dashboard requires an org context (X-Org-ID header)")
    return org_ctx


def _resolve_scope(db: Session, org_ctx: OrgContext, user_id: uuid.UUID) -> dict:
    """Returns {'level': 'org'|'department'|'member', 'department_ids': [...] | None}."""
    if is_domain_admin(org_ctx, "org_structure") or org_ctx.role in ("owner", "admin"):
        return {"level": "org", "department_ids": None}

    headed = (
        db.query(Department.id)
        .filter(Department.organization_id == org_ctx.org_id, Department.head_user_id == user_id)
        .all()
    )
    if headed:
        return {"level": "department", "department_ids": [d.id for d in headed]}

    return {"level": "member", "department_ids": None}


@router.get("/company-dashboard")
def get_company_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    scope = _resolve_scope(db, ctx, current_user.id)
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=30)

    # ── Work activity ───────────────────────────────────────────────────────
    work_q = db.query(Work).filter(Work.organization_id == ctx.org_id)
    if scope["level"] == "department":
        work_q = work_q.filter(Work.department_id.in_(scope["department_ids"]))
    elif scope["level"] == "member":
        work_q = work_q.filter(or_(
            Work.requester_user_id == current_user.id,
            Work.assigned_user_id == current_user.id,
        ))

    work_by_status = dict(
        work_q.with_entities(Work.status, func.count(Work.id)).group_by(Work.status).all()
    )
    pending_approvals_work = work_by_status.get("awaiting_approval", 0)

    # ── Workflow executions ────────────────────────────────────────────────
    exec_q = db.query(WorkflowExecution).join(Workflow, Workflow.id == WorkflowExecution.workflow_id).filter(
        WorkflowExecution.organization_id == ctx.org_id
    )
    if scope["level"] == "department":
        exec_q = exec_q.filter(Workflow.department_id.in_(scope["department_ids"]))
    elif scope["level"] == "member":
        exec_q = exec_q.filter(Workflow.created_by == current_user.id)

    exec_by_status = dict(
        exec_q.with_entities(WorkflowExecution.status, func.count(WorkflowExecution.id))
        .group_by(WorkflowExecution.status).all()
    )
    pending_approvals_workflow = exec_by_status.get("awaiting_approval", 0)

    # ── Workflow health (per workflow, real success/failure counts) ───────────
    wf_q = db.query(Workflow).filter(Workflow.organization_id == ctx.org_id)
    if scope["level"] == "department":
        wf_q = wf_q.filter(Workflow.department_id.in_(scope["department_ids"]))
    elif scope["level"] == "member":
        wf_q = wf_q.filter(Workflow.created_by == current_user.id)
    workflows = wf_q.all()

    workflow_health = []
    for wf in workflows:
        rows = (
            db.query(WorkflowExecution.status, func.count(WorkflowExecution.id))
            .filter(WorkflowExecution.workflow_id == wf.id)
            .group_by(WorkflowExecution.status)
            .all()
        )
        by_status = dict(rows)
        total = sum(by_status.values())
        if total == 0:
            continue
        workflow_health.append({
            "workflow_id": str(wf.id), "name": wf.name,
            "total_executions": total,
            "completed": by_status.get("completed", 0),
            "failed": by_status.get("failed", 0),
            "success_rate": round(100 * by_status.get("completed", 0) / total, 1),
        })

    # ── Agent activity (real WorkflowExecutionStep rows, last 30 days) ────────
    agent_step_q = (
        db.query(func.count(WorkflowExecutionStep.id))
        .join(WorkflowExecution, WorkflowExecution.id == WorkflowExecutionStep.execution_id)
        .join(Workflow, Workflow.id == WorkflowExecution.workflow_id)
        .filter(
            Workflow.organization_id == ctx.org_id,
            WorkflowExecutionStep.node_type == "agent_task",
            WorkflowExecutionStep.started_at >= window_start,
        )
    )
    if scope["level"] == "department":
        agent_step_q = agent_step_q.filter(Workflow.department_id.in_(scope["department_ids"]))
    elif scope["level"] == "member":
        agent_step_q = agent_step_q.filter(Workflow.created_by == current_user.id)
    agent_tasks_last_30d = agent_step_q.scalar() or 0

    # ── Integration health (real CompanyApi status counts, org-wide asset) ────
    integration_health = None
    if scope["level"] in ("org", "department"):
        rows = (
            db.query(CompanyApi.status, func.count(CompanyApi.id))
            .filter(CompanyApi.organization_id == ctx.org_id)
            .group_by(CompanyApi.status)
            .all()
        )
        integration_health = dict(rows)

    # ── Recent conversations (real Message rows in channels visible to caller) ─
    channel_ids = [
        c.id for c in db.query(Channel.id).filter(workspace_service.visible_channels_filter(current_user, ctx)).all()
    ]
    recent_messages = []
    if channel_ids:
        rows = (
            db.query(Message)
            .filter(Message.channel_id.in_(channel_ids), Message.is_deleted.is_(False))
            .order_by(Message.created_at.desc())
            .limit(5)
            .all()
        )
        recent_messages = [
            {
                "id": str(m.id), "channel_id": str(m.channel_id),
                "preview": (m.body or "")[:140],
                "kind": m.kind,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in rows
        ]

    # ── Usage / billing (reuses metering_service, never a second cost ledger) ─
    quota = metering_service.check_quota(db, user_id=current_user.id, org_id=ctx.org_id)

    return {
        "scope": scope["level"],
        "department_ids": [str(d) for d in scope["department_ids"]] if scope["department_ids"] else None,
        "work": {
            "by_status": work_by_status,
            "total": sum(work_by_status.values()),
        },
        "workflow_executions": {
            "by_status": exec_by_status,
            "total": sum(exec_by_status.values()),
        },
        "pending_approvals": pending_approvals_work + pending_approvals_workflow,
        "pending_approvals_breakdown": {
            "work": pending_approvals_work,
            "workflow": pending_approvals_workflow,
        },
        "agent_activity": {"agent_task_runs_last_30d": agent_tasks_last_30d},
        "workflow_health": workflow_health,
        "integration_health": integration_health,
        "recent_conversations": recent_messages,
        "usage": quota.as_dict(),
        "generated_at": now.isoformat(),
    }
