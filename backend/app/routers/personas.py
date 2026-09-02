"""
Personas router — CRUD for the Persona resource.

A Persona is a named, reusable simulated user: a free-text goal/behavior plus
a starting URL. `agents/simulation_agent.py` is what actually drives a
browser as one; this router only manages the definitions, the same
"resource CRUD, org-scoped" shape every other builder resource (Skill, Agent,
Pod) already uses in this codebase — see `routers/skills.py` for the pattern
this mirrors line for line.

Routes
------
GET    /personas/           → list personas visible to the caller
POST   /personas/           → create a persona
GET    /personas/{id}       → get one persona
PUT    /personas/{id}       → update a persona
DELETE /personas/{id}       → delete a persona
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.persona import Persona
from app.models.user import User
from app.routers._helpers import OrgContext, can_write, get_optional_org, get_or_404, is_domain_admin, owner_filter
from app.routers.auth import get_current_user

router = APIRouter()


class PersonaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    entry_url: str = Field(..., min_length=1)
    project_id: Optional[uuid.UUID] = None


class PersonaUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    entry_url: Optional[str] = Field(None, min_length=1)
    project_id: Optional[uuid.UUID] = None


def _out(p: Persona) -> dict:
    return {
        "id": str(p.id),
        "user_id": str(p.user_id),
        "org_id": str(p.org_id) if p.org_id else None,
        "project_id": str(p.project_id) if p.project_id else None,
        "name": p.name,
        "description": p.description,
        "entry_url": p.entry_url,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("/")
def list_personas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    personas = (
        db.query(Persona)
        .filter(owner_filter(Persona, current_user, org_ctx))
        .order_by(Persona.created_at.desc())
        .all()
    )
    return [_out(p) for p in personas]


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_persona(
    body: PersonaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot create resources")
    persona = Persona(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        **body.model_dump(),
    )
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return _out(persona)


@router.get("/{persona_id}")
def get_persona(
    persona_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    persona = get_or_404(Persona, persona_id, current_user.id, db, "Persona", org_ctx)
    return _out(persona)


@router.put("/{persona_id}")
def update_persona(
    persona_id: uuid.UUID,
    body: PersonaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot update resources")
    persona = get_or_404(Persona, persona_id, current_user.id, db, "Persona", org_ctx)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(persona, field, value)
    db.commit()
    db.refresh(persona)
    return _out(persona)


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(
    persona_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and not is_domain_admin(org_ctx, "engineering"):
        raise HTTPException(status_code=403, detail="Admin or owner access required to delete")
    persona = get_or_404(Persona, persona_id, current_user.id, db, "Persona", org_ctx)
    db.delete(persona)
    db.commit()
