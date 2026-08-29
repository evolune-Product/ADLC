"""
Departments router
-------------------
CRUD for the Department resource — the org-chart layer "company OS" needs
that the SDLC platform never had. Fully user-configurable per organisation:
no fixed department list is hardcoded anywhere here, an org creates whatever
its own structure calls for.

Routes
------
GET    /departments/              → list departments in the current org
POST   /departments/              → create a department
GET    /departments/{id}          → get one department
PUT    /departments/{id}          → update name/description/icon/status
POST   /departments/{id}/archive  → archive (soft, reversible via PUT status)
PUT    /departments/{id}/head     → assign/clear the department head

Every route requires an org context (`X-Org-ID` header) — a department is
inherently an organisation concept, unlike Skill/Agent/Pod which also have a
personal-workspace mode. There is no "personal department".
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.department import Department
from app.models.user import User
from app.routers._helpers import (
    OrgContext, can_write, get_optional_org, is_domain_admin, is_department_head,
)
from app.routers.auth import get_current_user
from app.schemas.department import DepartmentCreate, DepartmentOut, DepartmentUpdate
from app.services.department_service import get_department_or_404, unique_department_slug

router = APIRouter()

# Departments have no router-declared `domains` entry in org_roles.py — only
# owner/admin (domains == "*") pass is_domain_admin for any string, so this
# is really "is a full org admin", spelled out for readability at each call
# site the way every other router names its own domain.
_DOMAIN = "org_structure"


def _require_org(org_ctx: Optional[OrgContext]) -> OrgContext:
    if org_ctx is None:
        raise HTTPException(
            status_code=400,
            detail="This action requires an org context (X-Org-ID header)",
        )
    return org_ctx


@router.get("/", response_model=List[DepartmentOut])
def list_departments(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    q = db.query(Department).filter(Department.organization_id == ctx.org_id)
    if status_filter:
        q = q.filter(Department.status == status_filter)
    return q.order_by(Department.created_at.desc()).all()


@router.post("/", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(
    body: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    if not can_write(ctx):
        raise HTTPException(status_code=403, detail="Read-only role cannot create a department")
    if not is_domain_admin(ctx, _DOMAIN):
        raise HTTPException(status_code=403, detail="Admin or owner access required to create a department")
    slug = unique_department_slug(db, ctx.org_id, body.name)
    dept = Department(
        organization_id=ctx.org_id,
        name=body.name,
        slug=slug,
        description=body.description,
        icon=body.icon,
        head_user_id=body.head_user_id,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/{department_id}", response_model=DepartmentOut)
def get_department(
    department_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    dept = get_department_or_404(db, ctx.org_id, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.put("/{department_id}", response_model=DepartmentOut)
def update_department(
    department_id: uuid.UUID,
    body: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    dept = get_department_or_404(db, ctx.org_id, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    # A department head may run their own department's day-to-day fields;
    # only an org admin may reassign the headship itself (handled below by
    # the dedicated /head endpoint, deliberately excluded from this one).
    if not (is_domain_admin(ctx, _DOMAIN) or is_department_head(ctx, db, department_id, ctx.user_id)):
        raise HTTPException(status_code=403, detail="Admin, owner or the department head can update this department")
    if body.name is not None:
        dept.name = body.name
    if body.description is not None:
        dept.description = body.description
    if body.icon is not None:
        dept.icon = body.icon
    if body.status is not None:
        if body.status not in ("active", "archived"):
            raise HTTPException(status_code=422, detail="status must be 'active' or 'archived'")
        # Only an admin/owner may archive — a department head archiving their
        # own department out from under their team is not a "manage my team"
        # action, it is an org-structure decision.
        if not is_domain_admin(ctx, _DOMAIN):
            raise HTTPException(status_code=403, detail="Admin or owner access required to change status")
        dept.status = body.status
    db.commit()
    db.refresh(dept)
    return dept


@router.post("/{department_id}/archive", response_model=DepartmentOut)
def archive_department(
    department_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    if not is_domain_admin(ctx, _DOMAIN):
        raise HTTPException(status_code=403, detail="Admin or owner access required to archive")
    dept = get_department_or_404(db, ctx.org_id, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    dept.status = "archived"
    db.commit()
    db.refresh(dept)
    return dept


class HeadAssignBody(BaseModel):
    head_user_id: Optional[uuid.UUID] = None


@router.put("/{department_id}/head", response_model=DepartmentOut)
def assign_head(
    department_id: uuid.UUID,
    body: HeadAssignBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    if not is_domain_admin(ctx, _DOMAIN):
        raise HTTPException(status_code=403, detail="Admin or owner access required to assign a department head")
    dept = get_department_or_404(db, ctx.org_id, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    if body.head_user_id is not None:
        member = db.query(User).filter(User.id == body.head_user_id).first()
        if not member:
            raise HTTPException(status_code=404, detail="User not found")
    dept.head_user_id = body.head_user_id
    db.commit()
    db.refresh(dept)
    return dept
