import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ticket import Ticket
from app.models.project import Project
from app.models.connection import Connection
from app.schemas.ticket import TicketOut
from app.routers.auth import get_current_user
from app.routers._helpers import OrgContext, can_write, get_optional_org, owner_filter
from app.models.user import User
from app.services import gitlab_service, github_service, jira_service, writeback_service
from app.services.encryption import decrypt_token

router = APIRouter()


class TicketCloseBody(BaseModel):
    note: Optional[str] = None
    status: Optional[str] = None  # defaults to "Done"


def _ticket_out(t: Ticket) -> TicketOut:
    return TicketOut(
        id=t.id,
        project_id=t.project_id,
        jira_id=t.jira_id,
        title=t.title,
        description=t.description,
        type=t.type,
        priority=t.priority,
        status=t.status,
        assignee=t.assignee,
        jira_url=t.jira_url,
        synced_at=t.synced_at,
    )


def _get_project(
    project_id: uuid.UUID,
    current_user: User,
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


@router.get("/projects/{project_id}/tickets", response_model=List[TicketOut])
def list_tickets(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _get_project(project_id, current_user, db, org_ctx)
    tickets = (
        db.query(Ticket)
        .filter(Ticket.project_id == project_id)
        .order_by(Ticket.synced_at.desc())
        .all()
    )
    return [_ticket_out(t) for t in tickets]


@router.post("/projects/{project_id}/tickets/sync", response_model=List[TicketOut])
def sync_tickets(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot sync tickets")
    project = _get_project(project_id, current_user, db, org_ctx)

    source = project.ticket_source or "jira"
    if source in ("github", "gitlab"):
        # No separate tracker connection needed — reuse the repo connection
        # already on the project, so a solo project doesn't need a Jira/Linear
        # account just to try the pipeline.
        if not project.repo_connection_id or not project.repo_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No repository connected for this project",
            )
        conn = db.query(Connection).filter(Connection.id == project.repo_connection_id).first()
        if not conn:
            raise HTTPException(status_code=404, detail="Repository connection not found")
        raw_token = decrypt_token(conn.access_token) if conn.access_token else ""
        try:
            if source == "github":
                issues = github_service.list_issues(raw_token, project.repo_name)
            else:
                issues = gitlab_service.GitLabClient(raw_token, host=conn.workspace_url).list_issues(project.repo_name)
        except gitlab_service.GitLabError as e:
            raise HTTPException(status_code=502, detail=str(e))
    else:
        if not project.jira_connection_id or not project.jira_project_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Jira connection configured for this project",
            )

        conn = db.query(Connection).filter(Connection.id == project.jira_connection_id).first()
        if not conn:
            raise HTTPException(status_code=404, detail="Jira connection not found")

        email = conn.metadata_.get("email", "")
        raw_token = decrypt_token(conn.access_token) if conn.access_token else ""

        try:
            issues = jira_service.sync_tickets(conn.workspace_url, email, raw_token, project.jira_project_key)
        except jira_service.JiraError as e:
            raise HTTPException(status_code=502, detail=str(e))

    now = datetime.now(timezone.utc)

    for issue in issues:
        existing = (
            db.query(Ticket)
            .filter(Ticket.project_id == project_id, Ticket.jira_id == issue["jira_id"])
            .first()
        )
        if existing:
            existing.title = issue["title"]
            existing.description = issue["description"]
            existing.type = issue["type"]
            existing.priority = issue["priority"]
            existing.status = issue["status"]
            existing.assignee = issue["assignee"]
            existing.jira_url = issue["jira_url"]
            existing.raw_payload = issue["raw_payload"]
            existing.synced_at = now
        else:
            db.add(Ticket(
                project_id=project_id,
                jira_id=issue["jira_id"],
                title=issue["title"],
                description=issue["description"],
                type=issue["type"],
                priority=issue["priority"],
                status=issue["status"],
                assignee=issue["assignee"],
                jira_url=issue["jira_url"],
                raw_payload=issue["raw_payload"],
            ))

    db.commit()
    tickets = (
        db.query(Ticket)
        .filter(Ticket.project_id == project_id)
        .order_by(Ticket.synced_at.desc())
        .all()
    )
    return [_ticket_out(t) for t in tickets]


@router.get("/projects/{project_id}/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(
    project_id: uuid.UUID,
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _get_project(project_id, current_user, db, org_ctx)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.project_id == project_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _ticket_out(ticket)


@router.post("/projects/{project_id}/tickets/{ticket_id}/close")
def close_ticket(
    project_id: uuid.UUID,
    ticket_id: uuid.UUID,
    body: TicketCloseBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    A human confirms the work is actually done and closes the ticket
    themselves — the platform never does this automatically. Posts a comment
    naming who closed it and attempts a transition to the target status
    (default "Done"); works regardless of whether passive run write-back is
    enabled for this project, since this is a deliberate action, not a
    milestone the platform narrates on its own.
    """
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot close tickets")

    project = _get_project(project_id, current_user, db, org_ctx)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.project_id == project_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    target_status = (body.status or "Done").strip() or "Done"
    try:
        result = writeback_service.close_ticket(
            db, project, ticket,
            closed_by=current_user.name or current_user.email,
            note=body.note, status=target_status,
        )
    except writeback_service.WritebackError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if result["moved"]:
        ticket.status = target_status
        db.commit()
        db.refresh(ticket)

    return {**_ticket_out(ticket).model_dump(), **result}
