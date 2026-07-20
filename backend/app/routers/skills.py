"""
Skills router
-------------
CRUD for the Skill resource. Skills are markdown documents that describe a
capability (e.g. "write unit tests") and are injected into agent prompts.

Routes
------
GET    /skills/           → list all skills for the current user / org
POST   /skills/           → create a new skill
GET    /skills/{id}       → get a single skill
PUT    /skills/{id}       → update a skill
DELETE /skills/{id}       → delete a skill
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.skill import Skill
from app.models.user import User
from app.routers._helpers import get_or_404, get_optional_org, owner_filter, OrgContext
from app.routers.auth import get_current_user
from app.schemas.skill import SkillCreate, SkillOut, SkillUpdate

router = APIRouter()


@router.get("/", response_model=List[SkillOut])
def list_skills(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    return (
        db.query(Skill)
        .filter(owner_filter(Skill, current_user, org_ctx))
        .order_by(Skill.created_at.desc())
        .all()
    )


@router.post("/", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
def create_skill(
    body: SkillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and org_ctx.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot create resources")
    skill = Skill(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        **body.model_dump(),
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("/{skill_id}", response_model=SkillOut)
def get_skill(
    skill_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    return get_or_404(Skill, skill_id, current_user.id, db, "Skill", org_ctx)


@router.put("/{skill_id}", response_model=SkillOut)
def update_skill(
    skill_id: uuid.UUID,
    body: SkillUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and org_ctx.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot update resources")
    skill = get_or_404(Skill, skill_id, current_user.id, db, "Skill", org_ctx)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(skill, field, value)
    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(
    skill_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and org_ctx.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Admin or owner access required to delete")
    skill = get_or_404(Skill, skill_id, current_user.id, db, "Skill", org_ctx)
    db.delete(skill)
    db.commit()
