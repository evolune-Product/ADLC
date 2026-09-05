"""
Simulations router — start a persona-driven simulation run and poll it.

Routes
------
POST   /simulations/           → start a run for a persona + URL (kicks off a
                                  Celery task; follows the same fire-and-poll
                                  shape `POST /runs` already uses)
GET    /simulations/           → list past runs (optionally filter by persona/status)
GET    /simulations/{id}       → poll one run's status and list its findings
GET    /simulations/{id}/findings/{finding_id}/screenshot
                                → the screenshot captured at that finding's step

`GET /simulations/{id}` is the only endpoint the frontend actually polls
(`useSimulations.ts` mirrors `useRuns.ts`'s `refetchInterval` pattern) — there
is no WebSocket event stream for simulations in v1, unlike SDLC runs.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.persona import Persona
from app.models.project import Project
from app.models.simulation import SimulationFinding, SimulationRun
from app.models.ticket import Ticket
from app.models.user import User
from app.routers._helpers import OrgContext, can_write, get_optional_org, get_or_404, owner_filter
from app.routers.auth import get_current_user

router = APIRouter()


class SimulationCreate(BaseModel):
    persona_id: uuid.UUID
    target_url: str = Field(..., min_length=1)
    ticket_id: Optional[uuid.UUID] = None
    max_steps: int = Field(15, ge=1, le=50)


def _finding_out(f: SimulationFinding) -> dict:
    return {
        "id": str(f.id),
        "simulation_run_id": str(f.simulation_run_id),
        "severity": f.severity,
        "title": f.title,
        "description": f.description,
        "reproduction_steps": f.reproduction_steps or [],
        "screenshot_path": f.screenshot_path,
        "step_number": f.step_number,
        "posted_to_tracker": f.posted_to_tracker,
        "notified": f.notified,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


def _run_out(run: SimulationRun, *, include_findings: bool = False) -> dict:
    out = {
        "id": str(run.id),
        "user_id": str(run.user_id),
        "org_id": str(run.org_id) if run.org_id else None,
        "persona_id": str(run.persona_id),
        "persona_name": run.persona.name if run.persona else None,
        "ticket_id": str(run.ticket_id) if run.ticket_id else None,
        "ticket_jira_id": run.ticket.jira_id if run.ticket else None,
        "ticket_url": run.ticket.jira_url if run.ticket else None,
        "target_url": run.target_url,
        "status": run.status,
        "steps_taken": run.steps_taken,
        "max_steps": run.max_steps,
        "summary": run.summary,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finding_count": len(run.findings) if include_findings else None,
    }
    if include_findings:
        out["findings"] = [_finding_out(f) for f in run.findings]
    return out


@router.get("/")
def list_simulations(
    persona_id: Optional[uuid.UUID] = None,
    run_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    query = db.query(SimulationRun).filter(owner_filter(SimulationRun, current_user, org_ctx))
    if persona_id:
        query = query.filter(SimulationRun.persona_id == persona_id)
    if run_status:
        query = query.filter(SimulationRun.status == run_status)
    runs = query.order_by(SimulationRun.created_at.desc()).all()
    return [_run_out(r) for r in runs]


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_simulation(
    body: SimulationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot start a simulation")

    persona = get_or_404(Persona, body.persona_id, current_user.id, db, "Persona", org_ctx)

    ticket_id = None
    if body.ticket_id:
        ticket = db.query(Ticket).filter(Ticket.id == body.ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        project = db.query(Project).filter(Project.id == ticket.project_id).first()
        if not project or not db.query(Project).filter(
            Project.id == project.id, owner_filter(Project, current_user, org_ctx)
        ).first():
            raise HTTPException(status_code=404, detail="Ticket not found")
        ticket_id = ticket.id

    run = SimulationRun(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        persona_id=persona.id,
        ticket_id=ticket_id,
        target_url=body.target_url,
        max_steps=body.max_steps,
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    from app.tasks.simulation_tasks import task_run_simulation
    task_run_simulation.delay(str(run.id))

    return _run_out(run, include_findings=True)


@router.get("/{simulation_id}")
def get_simulation(
    simulation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    run = get_or_404(SimulationRun, simulation_id, current_user.id, db, "Simulation run", org_ctx)
    return _run_out(run, include_findings=True)


@router.get("/{simulation_id}/findings/{finding_id}/screenshot")
def get_finding_screenshot(
    simulation_id: uuid.UUID,
    finding_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    # get_or_404 does the ownership check; the finding is then looked up
    # scoped to that already-verified run so this can never serve a file
    # belonging to a run outside the caller's org/workspace.
    run = get_or_404(SimulationRun, simulation_id, current_user.id, db, "Simulation run", org_ctx)
    finding = (
        db.query(SimulationFinding)
        .filter(SimulationFinding.id == finding_id, SimulationFinding.simulation_run_id == run.id)
        .first()
    )
    if not finding or not finding.screenshot_path:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    path = Path(finding.screenshot_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Screenshot file no longer exists on disk")
    # A plain Response reading the whole file, not FileResponse — these are
    # small (one browser-viewport PNG), so nothing here needs Range-request
    # seeking, and Starlette's FileResponse Range-header parser had a real
    # unauthenticated quadratic-time DoS (fixed upstream, but this sidesteps
    # the whole code path rather than depending on staying ahead of it for an
    # endpoint that never needed it).
    return Response(content=path.read_bytes(), media_type="image/png")
