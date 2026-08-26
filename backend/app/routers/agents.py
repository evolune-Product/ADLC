"""
Agents router
-------------
CRUD for the Agent resource. Agents are LLM-powered actors composed of
ordered Skill bindings. They are grouped into Pods to execute SDLC runs.

Routes
------
GET    /agents/                  → list all agents for the current user / org
POST   /agents/                  → create a new agent (with skill bindings)
GET    /agents/{id}              → get a single agent
PUT    /agents/{id}              → update an agent (replaces skill bindings)
PATCH  /agents/{id}/toggle       → flip is_active
DELETE /agents/{id}              → delete an agent
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agent import Agent, AgentSkill
from app.models.skill import Skill
from app.models.user import User
from app.routers._helpers import OrgContext, can_write, get_optional_org, get_or_404, is_domain_admin, owner_filter
from app.routers.auth import get_current_user
from app.schemas.agent import AgentCreate, AgentOut, AgentSkillOut, AgentUpdate

router = APIRouter()


# ─── Private helpers ─────────────────────────────────────────────────────────

def _agent_out(agent: Agent) -> AgentOut:
    """Serialize an Agent ORM object, sorting skills by priority."""
    skills = sorted(agent.agent_skills, key=lambda x: x.priority)
    return AgentOut(
        id=agent.id,
        name=agent.name,
        role=agent.role,
        description=agent.description,
        repo_connection_id=agent.repo_connection_id,
        default_branch=agent.default_branch,
        branch_prefix=agent.branch_prefix,
        llm_model=agent.llm_model,
        max_iterations=agent.max_iterations,
        is_active=agent.is_active,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        skills=[
            AgentSkillOut(
                id=as_.id,
                skill_id=as_.skill_id,
                skill_name=as_.skill.name,
                priority=as_.priority,
            )
            for as_ in skills
        ],
    )


def _sync_skills(agent: Agent, skill_ids: List[uuid.UUID], db: Session) -> None:
    """Replace all skill bindings with the ordered list of skill_ids."""
    for existing in agent.agent_skills:
        db.delete(existing)
    db.flush()
    for priority, skill_id in enumerate(skill_ids):
        if db.query(Skill).filter(Skill.id == skill_id).first():
            db.add(AgentSkill(agent_id=agent.id, skill_id=skill_id, priority=priority))


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[AgentOut])
def list_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    agents = (
        db.query(Agent)
        .filter(owner_filter(Agent, current_user, org_ctx))
        .order_by(Agent.created_at.desc())
        .all()
    )
    return [_agent_out(a) for a in agents]


@router.post("/", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
def create_agent(
    body: AgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot create resources")
    data = body.model_dump(exclude={"skill_ids"})
    agent = Agent(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        **data,
    )
    db.add(agent)
    db.flush()
    _sync_skills(agent, body.skill_ids, db)
    db.commit()
    db.refresh(agent)
    return _agent_out(agent)


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    return _agent_out(get_or_404(Agent, agent_id, current_user.id, db, "Agent", org_ctx))


@router.put("/{agent_id}", response_model=AgentOut)
def update_agent(
    agent_id: uuid.UUID,
    body: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot update resources")
    agent = get_or_404(Agent, agent_id, current_user.id, db, "Agent", org_ctx)
    data = body.model_dump(exclude_unset=True)
    skill_ids = data.pop("skill_ids", None)

    for field, value in data.items():
        setattr(agent, field, value)

    if skill_ids is not None:
        _sync_skills(agent, skill_ids, db)

    db.commit()
    db.refresh(agent)
    return _agent_out(agent)


@router.patch("/{agent_id}/toggle", response_model=AgentOut)
def toggle_agent(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Viewers cannot update resources")
    agent = get_or_404(Agent, agent_id, current_user.id, db, "Agent", org_ctx)
    agent.is_active = not agent.is_active
    db.commit()
    db.refresh(agent)
    return _agent_out(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and not is_domain_admin(org_ctx, "engineering"):
        raise HTTPException(status_code=403, detail="Admin or owner access required to delete")
    agent = get_or_404(Agent, agent_id, current_user.id, db, "Agent", org_ctx)
    db.delete(agent)
    db.commit()
