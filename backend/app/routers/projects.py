import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut
from app.routers.auth import get_current_user
from app.routers._helpers import get_optional_org, owner_filter, OrgContext
from app.models.user import User

router = APIRouter()


def _project_out(p: Project) -> ProjectOut:
    return ProjectOut(
        id=p.id,
        name=p.name,
        description=p.description,
        type=p.type,
        repo_connection_id=p.repo_connection_id,
        repo_name=p.repo_name,
        jira_connection_id=p.jira_connection_id,
        jira_project_key=p.jira_project_key,
        pod_id=p.pod_id,
        pod_name=p.pod.name if p.pod else None,
        context_md=p.context_md,
        deploy_targets=p.deploy_targets or [],
        status=p.status,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _get_project(
    project_id: uuid.UUID,
    current_user: User,
    db: Session,
    org_ctx: Optional[OrgContext],
) -> Project:
    from sqlalchemy import and_
    from app.routers._helpers import owner_filter
    p = db.query(Project).filter(
        Project.id == project_id,
        owner_filter(Project, current_user, org_ctx),
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


@router.get("/", response_model=List[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    projects = (
        db.query(Project)
        .filter(owner_filter(Project, current_user, org_ctx))
        .order_by(Project.created_at.desc())
        .all()
    )
    return [_project_out(p) for p in projects]


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and org_ctx.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot create resources")
    p = Project(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        name=body.name,
        description=body.description,
        type=body.type,
        repo_connection_id=body.repo_connection_id,
        repo_name=body.repo_name,
        jira_connection_id=body.jira_connection_id,
        jira_project_key=body.jira_project_key,
        pod_id=body.pod_id,
        context_md=body.context_md,
        deploy_targets=[dt.model_dump() for dt in body.deploy_targets],
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _project_out(p)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    return _project_out(_get_project(project_id, current_user, db, org_ctx))


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and org_ctx.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot update resources")
    p = _get_project(project_id, current_user, db, org_ctx)

    data = body.model_dump(exclude_unset=True)
    if "deploy_targets" in data and data["deploy_targets"] is not None:
        data["deploy_targets"] = [
            dt if isinstance(dt, dict) else dt.model_dump()
            for dt in (body.deploy_targets or [])
        ]
    for field, value in data.items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return _project_out(p)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and org_ctx.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Admin or owner access required to delete")
    p = _get_project(project_id, current_user, db, org_ctx)
    db.delete(p)
    db.commit()


@router.patch("/{project_id}/archive", response_model=ProjectOut)
def archive_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and org_ctx.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot update resources")
    p = _get_project(project_id, current_user, db, org_ctx)
    p.status = "archived"
    db.commit()
    db.refresh(p)
    return _project_out(p)
