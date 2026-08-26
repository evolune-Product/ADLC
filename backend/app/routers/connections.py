"""
Connections router
------------------
CRUD and utility endpoints for GitHub, GitLab, and Jira connections.
Tokens are Fernet-encrypted at rest; never returned in API responses.

Routes
------
GET    /connections/                  → list all connections
POST   /connections/                  → add a new connection (tests it immediately)
GET    /connections/{id}              → get a single connection
PUT    /connections/{id}              → update name / workspace_url
DELETE /connections/{id}              → remove a connection
POST   /connections/{id}/test         → re-test credentials, update status
GET    /connections/{id}/repos        → list repos (GitHub/GitLab only)
GET    /connections/{id}/projects     → list Jira projects (Jira only)
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.connection import Connection
from app.models.user import User
from app.routers._helpers import OrgContext, can_write, get_optional_org, get_or_404, is_domain_admin, owner_filter
from app.routers.auth import get_current_user
from app.schemas.connection import ConnectionCreate, ConnectionOut, ConnectionUpdate
from app.services import github_service, jira_service
from app.services.encryption import decrypt_token, encrypt_token

router = APIRouter()


@router.get("/", response_model=List[ConnectionOut])
def list_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    return (
        db.query(Connection)
        .filter(owner_filter(Connection, current_user, org_ctx))
        .all()
    )


@router.post("/", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED)
def create_connection(
    body: ConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot create resources")

    if body.type == "jira":
        if not body.workspace_url or not body.access_token or not body.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="workspace_url, access_token, and email are required for Jira",
            )
        result = jira_service.test_connection(body.workspace_url, body.email, body.access_token)
        conn_status = "connected" if result["success"] else "error"
        metadata = {"email": body.email, "display_name": result.get("display_name", "")}

    elif body.type in ("github", "gitlab"):
        if not body.access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="access_token (Personal Access Token) is required",
            )
        ok = github_service.test_connection(body.access_token)
        conn_status = "connected" if ok else "error"
        user_info = github_service.get_user_info(body.access_token) if ok else {}
        metadata = {
            "login": user_info.get("login", ""),
            "avatar_url": user_info.get("avatar_url", ""),
        }
    else:
        conn_status = "pending"
        metadata = {}

    connection = Connection(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        name=body.name,
        type=body.type,
        status=conn_status,
        access_token=encrypt_token(body.access_token) if body.access_token else None,
        workspace_url=body.workspace_url,
        metadata_=metadata,
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


@router.get("/{connection_id}", response_model=ConnectionOut)
def get_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    return get_or_404(Connection, connection_id, current_user.id, db, "Connection", org_ctx)


@router.put("/{connection_id}", response_model=ConnectionOut)
def update_connection(
    connection_id: uuid.UUID,
    body: ConnectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot update resources")
    conn = get_or_404(Connection, connection_id, current_user.id, db, "Connection", org_ctx)
    if body.name is not None:
        conn.name = body.name
    if body.workspace_url is not None:
        conn.workspace_url = body.workspace_url
    db.commit()
    db.refresh(conn)
    return conn


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and not is_domain_admin(org_ctx, "engineering"):
        raise HTTPException(status_code=403, detail="Admin or owner access required to delete")
    conn = get_or_404(Connection, connection_id, current_user.id, db, "Connection", org_ctx)
    db.delete(conn)
    db.commit()


@router.post("/{connection_id}/test")
def test_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    conn = get_or_404(Connection, connection_id, current_user.id, db, "Connection", org_ctx)
    if not conn.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No token stored for this connection",
        )
    token = decrypt_token(conn.access_token)

    if conn.type in ("github", "gitlab"):
        success = github_service.test_connection(token)
    elif conn.type == "jira":
        email = conn.metadata_.get("email", "")
        result = jira_service.test_connection(conn.workspace_url or "", email, token)
        success = result["success"]
    else:
        success = False

    conn.status = "connected" if success else "error"
    db.commit()
    return {"success": success, "status": conn.status}


@router.get("/{connection_id}/repos")
def get_repos(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    conn = get_or_404(Connection, connection_id, current_user.id, db, "Connection", org_ctx)
    if conn.type not in ("github", "gitlab"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only GitHub/GitLab connections have repos",
        )
    if not conn.access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No token stored")
    return github_service.get_repos(decrypt_token(conn.access_token))


@router.get("/{connection_id}/projects")
def get_jira_projects(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    conn = get_or_404(Connection, connection_id, current_user.id, db, "Connection", org_ctx)
    if conn.type != "jira":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Jira connections have projects",
        )
    if not conn.access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No token stored")
    token = decrypt_token(conn.access_token)
    email = conn.metadata_.get("email", "")
    return jira_service.get_projects(conn.workspace_url or "", email, token)
