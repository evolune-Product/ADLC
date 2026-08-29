"""
Teams router — teams live under a department, membership is many-to-many.

Routes
------
GET    /departments/{department_id}/teams                         → list teams
POST   /departments/{department_id}/teams                         → create a team
GET    /departments/{department_id}/teams/{team_id}                → get one team
PUT    /departments/{department_id}/teams/{team_id}                → update a team
DELETE /departments/{department_id}/teams/{team_id}                → archive a team
GET    /departments/{department_id}/teams/{team_id}/members        → list members
POST   /departments/{department_id}/teams/{team_id}/members        → add a member
DELETE /departments/{department_id}/teams/{team_id}/members/{user_id} → remove a member

Mounted under the same `/departments` prefix as `departments.py` (a separate
APIRouter, included second in main.py) so a team's URL nests under its
department the way the resource itself does, without one file growing to
cover two related-but-distinct resources.

organization_id is checked directly on every Team/TeamMember query — never
only by joining through Department — the same redundant-but-required
tenant-isolation shape the Team model itself declares.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.department import Team, TeamMember
from app.models.user import User
from app.routers._helpers import (
    OrgContext, can_write, get_optional_org, is_department_head, is_domain_admin, is_team_lead,
)
from app.routers.auth import get_current_user
from app.schemas.department import TeamCreate, TeamMemberAdd, TeamMemberOut, TeamOut, TeamUpdate
from app.services.department_service import (
    get_department_or_404, get_team_or_404, unique_team_slug,
)

router = APIRouter()

_DOMAIN = "org_structure"


def _require_org(org_ctx: Optional[OrgContext]) -> OrgContext:
    if org_ctx is None:
        raise HTTPException(status_code=400, detail="This action requires an org context (X-Org-ID header)")
    return org_ctx


def _team_scoped_or_404(db: Session, ctx: OrgContext, department_id: uuid.UUID, team_id: uuid.UUID) -> Team:
    team = db.query(Team).filter(
        Team.id == team_id,
        Team.department_id == department_id,
        Team.organization_id == ctx.org_id,
    ).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def _can_manage_team(ctx: OrgContext, db: Session, department_id: uuid.UUID, team_id: Optional[uuid.UUID]) -> bool:
    if is_domain_admin(ctx, _DOMAIN) or is_department_head(ctx, db, department_id, ctx.user_id):
        return True
    return bool(team_id) and is_team_lead(ctx, db, team_id, ctx.user_id)


@router.get("/{department_id}/teams", response_model=List[TeamOut])
def list_teams(
    department_id: uuid.UUID,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    if not get_department_or_404(db, ctx.org_id, department_id):
        raise HTTPException(status_code=404, detail="Department not found")
    q = db.query(Team).filter(Team.department_id == department_id, Team.organization_id == ctx.org_id)
    if status_filter:
        q = q.filter(Team.status == status_filter)
    return q.order_by(Team.created_at.desc()).all()


@router.post("/{department_id}/teams", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
def create_team(
    department_id: uuid.UUID,
    body: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    dept = get_department_or_404(db, ctx.org_id, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    if not can_write(ctx) or not (is_domain_admin(ctx, _DOMAIN) or is_department_head(ctx, db, department_id, ctx.user_id)):
        raise HTTPException(status_code=403, detail="Admin, owner or the department head can create a team")
    team = Team(
        department_id=dept.id,
        organization_id=ctx.org_id,
        name=body.name,
        slug=unique_team_slug(db, dept.id, body.name),
        description=body.description,
    )
    db.add(team)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Team slug collision, retry")
    db.refresh(team)
    return team


@router.get("/{department_id}/teams/{team_id}", response_model=TeamOut)
def get_team(
    department_id: uuid.UUID,
    team_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    return _team_scoped_or_404(db, ctx, department_id, team_id)


@router.put("/{department_id}/teams/{team_id}", response_model=TeamOut)
def update_team(
    department_id: uuid.UUID,
    team_id: uuid.UUID,
    body: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    team = _team_scoped_or_404(db, ctx, department_id, team_id)
    if not can_write(ctx) or not _can_manage_team(ctx, db, department_id, team_id):
        raise HTTPException(status_code=403, detail="Not authorized to update this team")
    if body.name is not None and body.name != team.name:
        team.slug = unique_team_slug(db, department_id, body.name)
        team.name = body.name
    if body.description is not None:
        team.description = body.description
    if body.status is not None:
        if body.status not in ("active", "archived"):
            raise HTTPException(status_code=422, detail="status must be 'active' or 'archived'")
        if not (is_domain_admin(ctx, _DOMAIN) or is_department_head(ctx, db, department_id, ctx.user_id)):
            raise HTTPException(status_code=403, detail="Admin, owner or the department head can change status")
        team.status = body.status
    db.commit()
    db.refresh(team)
    return team


@router.delete("/{department_id}/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_team(
    department_id: uuid.UUID,
    team_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    team = _team_scoped_or_404(db, ctx, department_id, team_id)
    if not (is_domain_admin(ctx, _DOMAIN) or is_department_head(ctx, db, department_id, ctx.user_id)):
        raise HTTPException(status_code=403, detail="Admin, owner or the department head can archive this team")
    team.status = "archived"
    db.commit()


@router.get("/{department_id}/teams/{team_id}/members", response_model=List[TeamMemberOut])
def list_team_members(
    department_id: uuid.UUID,
    team_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    _team_scoped_or_404(db, ctx, department_id, team_id)
    return db.query(TeamMember).filter(TeamMember.team_id == team_id).order_by(TeamMember.joined_at.asc()).all()


@router.post("/{department_id}/teams/{team_id}/members", response_model=TeamMemberOut, status_code=status.HTTP_201_CREATED)
def add_team_member(
    department_id: uuid.UUID,
    team_id: uuid.UUID,
    body: TeamMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    _team_scoped_or_404(db, ctx, department_id, team_id)
    if not can_write(ctx) or not _can_manage_team(ctx, db, department_id, team_id):
        raise HTTPException(status_code=403, detail="Not authorized to manage this team's membership")
    if body.role_in_team not in ("lead", "member"):
        raise HTTPException(status_code=422, detail="role_in_team must be 'lead' or 'member'")
    member = TeamMember(team_id=team_id, user_id=body.user_id, role_in_team=body.role_in_team)
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User is already a member of this team")
    db.refresh(member)
    return member


@router.delete("/{department_id}/teams/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    department_id: uuid.UUID,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    _team_scoped_or_404(db, ctx, department_id, team_id)
    if not can_write(ctx) or not _can_manage_team(ctx, db, department_id, team_id):
        raise HTTPException(status_code=403, detail="Not authorized to manage this team's membership")
    member = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Membership not found")
    db.delete(member)
    db.commit()
