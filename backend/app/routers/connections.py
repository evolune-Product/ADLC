"""
Connections router
------------------
CRUD for every external system a workspace connects — GitHub, GitLab, Jira,
Linear, and everything else in the plugin catalogue (Slack, Datadog, Stripe,
Figma, ...). This used to be two separate features: a narrow, hand-rolled
"Connections" surface for the four providers the run pipeline depends on, and
a much broader "Plugins" catalogue with its own connect/verify endpoints that
happened to write into this exact same table. They're merged here — one
create/verify code path for all of it, driven by `app/services/plugins.py`'s
catalogue rather than a type-by-type if/elif chain.

Two things that motivated folding Plugins into Connections rather than the
reverse:
  - The catalogue's verification (`plugin_verify.verify`) is correct for
    every provider, including GitLab and Linear — the old inline branching
    here routed GitLab through the GitHub client (wrong API entirely) and
    didn't handle Linear at all (silently saved as "pending", never checked).
  - The catalogue already carries the honest `depth` label, capabilities list,
    and scopes needed for the connect form — duplicating that per-type here
    would just be a second copy that drifts.

Routes
------
GET    /connections/                  → list all connections
POST   /connections/                  → connect anything in the catalogue
                                         (verified against the vendor before saving)
GET    /connections/{id}              → get a single connection
PUT    /connections/{id}              → update name / workspace_url
DELETE /connections/{id}              → remove a connection
POST   /connections/{id}/test         → re-verify credentials, update status
GET    /connections/{id}/repos        → list repos (GitHub/GitLab only)
GET    /connections/{id}/projects     → list Jira projects (Jira only)

Tokens (and, for webhook-based plugins, the webhook URL itself — anyone
holding it can post into the channel) are Fernet-encrypted at rest and never
returned in any response.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.connection import Connection
from app.models.user import User
from app.routers._helpers import OrgContext, get_optional_org, get_or_404, is_domain_admin, owner_filter
from app.routers.auth import get_current_user
from app.schemas.connection import ConnectionCreate, ConnectionOut, ConnectionUpdate
from app.services import github_service, jira_service, plugin_verify, plugins
from app.services.encryption import decrypt_token, encrypt_token
from app.services.gitlab_service import GitLabClient, GitLabError

router = APIRouter()


def _require_engineering_admin(org_ctx: Optional[OrgContext]) -> None:
    """
    A connection is a credential to a system the pipeline reads or writes.
    Same domain as plugin management always was — the merge should not make
    this any less guarded than the catalogue side already was, and it should
    close the gap the old Connections endpoint had (no admin check at all, so
    any member could wire up a GitHub token the whole org's pipeline then
    trusted).
    """
    if org_ctx and not is_domain_admin(org_ctx, "engineering"):
        raise HTTPException(status_code=403,
                            detail="Only owners, admins and engineering leads can manage connections")


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
    """
    Connect anything in the catalogue. A failed verification still saves the
    connection with status="error" and the vendor's reason attached — someone
    who pasted a token with one missing scope should be able to fix the scope
    and re-verify, not retype the whole form.
    """
    _require_engineering_admin(org_ctx)

    spec = plugins.get(body.type)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Unknown connection type '{body.type}'")

    if plugins.requires_token(body.type) and not body.access_token:
        raise HTTPException(status_code=422,
                            detail=f"{spec.get('token_label', 'Token')} is required")
    if plugins.requires_url(body.type) and not body.workspace_url:
        raise HTTPException(status_code=422,
                            detail=f"{spec.get('url_label', 'URL')} is required")
    if plugins.requires_user(body.type) and not body.email:
        raise HTTPException(status_code=422,
                            detail=f"{spec.get('user_label', 'Username')} is required")

    result = plugin_verify.verify(body.type, token=body.access_token, url=body.workspace_url,
                                  user=body.email, extra=body.extra)

    metadata = {"depth": spec["depth"], "verified_detail": result.detail}
    if result.display_name:
        metadata["display_name"] = result.display_name
    if body.email:
        metadata["email"] = body.email
    if body.extra:
        metadata["extra"] = body.extra

    # A webhook URL is as much a secret as a token — anyone holding it can post
    # into the channel — so it's encrypted the same way rather than left in
    # the plaintext workspace_url column.
    is_webhook = spec["auth"] == plugins.AUTH_WEBHOOK
    connection = Connection(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        name=body.name or spec["label"],
        type=body.type,
        status="connected" if result.ok else "error",
        access_token=encrypt_token(body.access_token or body.workspace_url or "")
                     if (body.access_token or is_webhook) else None,
        workspace_url=body.workspace_url if not is_webhook else None,
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
    _require_engineering_admin(org_ctx)
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
    _require_engineering_admin(org_ctx)
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
    """
    Re-run the vendor check. Tokens expire and get revoked; a status from
    months ago is not evidence a credential still works.
    """
    conn = get_or_404(Connection, connection_id, current_user.id, db, "Connection", org_ctx)
    spec = plugins.get(conn.type)
    if not spec:
        raise HTTPException(status_code=422, detail=f"'{conn.type}' is not a known connection type")

    secret = None
    if conn.access_token:
        try:
            secret = decrypt_token(conn.access_token)
        except Exception:
            conn.status = "error"
            db.commit()
            raise HTTPException(status_code=500, detail="Stored credential could not be decrypted")

    is_webhook = spec["auth"] == plugins.AUTH_WEBHOOK
    result = plugin_verify.verify(
        conn.type,
        token=None if is_webhook else secret,
        url=secret if is_webhook else conn.workspace_url,
        user=(conn.metadata_ or {}).get("email"),
        extra=(conn.metadata_ or {}).get("extra"),
    )

    conn.status = "connected" if result.ok else "error"
    meta = dict(conn.metadata_ or {})
    meta["verified_detail"] = result.detail
    if result.display_name:
        meta["display_name"] = result.display_name
    conn.metadata_ = meta
    db.commit()
    return {"success": result.ok, "status": conn.status, "detail": result.detail}


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
    token = decrypt_token(conn.access_token)

    if conn.type == "gitlab":
        # Previously routed through github_service regardless of type — the
        # wrong API entirely for a GitLab PAT/self-hosted host. GitLabClient
        # already exists (dev_agent/review_agent/memory_service use it) and
        # normalizes to the same shape github_service.get_repos returns, so
        # the onboarding wizard's repo picker doesn't need to know which host
        # answered.
        try:
            projects = GitLabClient(token, host=conn.workspace_url).list_projects()
        except GitLabError as e:
            raise HTTPException(status_code=502, detail=str(e))
        return [
            {"id": p["id"], "name": p["name"], "full_name": p["full_name"],
             "private": p["private"], "default_branch": p["default_branch"], "description": ""}
            for p in projects
        ]

    return github_service.get_repos(token)


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
