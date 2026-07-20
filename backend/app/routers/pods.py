"""
Pods router
-----------
CRUD for the Pod resource. A Pod is an ordered collection of Agents that
executes together as a workflow when a Run is triggered.

Routes
------
GET    /pods/                    → list all pods for the current user / org
POST   /pods/                    → create a pod (with agent bindings)
GET    /pods/{id}                → get a single pod
PUT    /pods/{id}                → update a pod (replaces agent bindings)
DELETE /pods/{id}                → delete a pod
POST   /pods/{id}/duplicate      → copy a pod and all its agent bindings
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agent import Agent
from app.models.pod import Pod, PodAgent
from app.models.user import User
from app.routers._helpers import get_or_404, get_optional_org, owner_filter, OrgContext
from app.routers.auth import get_current_user
from app.schemas.pod import PodAgentOut, PodCreate, PodOut, PodUpdate

router = APIRouter()


# ─── Private helpers ─────────────────────────────────────────────────────────

def _pod_out(pod: Pod) -> PodOut:
    """Serialize a Pod ORM object, sorting agents by execution_order."""
    return PodOut(
        id=pod.id,
        name=pod.name,
        description=pod.description,
        is_active=pod.is_active,
        created_at=pod.created_at,
        updated_at=pod.updated_at,
        agents=[
            PodAgentOut(
                id=pa.id,
                agent_id=pa.agent_id,
                agent_name=pa.agent.name,
                agent_role=pa.agent.role,
                execution_order=pa.execution_order,
                count=pa.count,
                on_failure=pa.on_failure,
                max_retries=pa.max_retries,
            )
            for pa in sorted(pod.pod_agents, key=lambda x: x.execution_order)
        ],
    )


def _sync_agents(pod: Pod, agents: list, db: Session) -> None:
    """Replace all agent bindings with the new ordered list."""
    for pa in pod.pod_agents:
        db.delete(pa)
    db.flush()
    for item in agents:
        if db.query(Agent).filter(Agent.id == item.agent_id).first():
            db.add(PodAgent(
                pod_id=pod.id,
                agent_id=item.agent_id,
                execution_order=item.execution_order,
                count=item.count,
                on_failure=item.on_failure,
                max_retries=item.max_retries,
            ))


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[PodOut])
def list_pods(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    pods = (
        db.query(Pod)
        .filter(owner_filter(Pod, current_user, org_ctx))
        .order_by(Pod.created_at.desc())
        .all()
    )
    return [_pod_out(p) for p in pods]


@router.post("/", response_model=PodOut, status_code=status.HTTP_201_CREATED)
def create_pod(
    body: PodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and org_ctx.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot create resources")
    pod = Pod(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        name=body.name,
        description=body.description,
    )
    db.add(pod)
    db.flush()
    _sync_agents(pod, body.agents, db)
    db.commit()
    db.refresh(pod)
    return _pod_out(pod)


@router.get("/{pod_id}", response_model=PodOut)
def get_pod(
    pod_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    return _pod_out(get_or_404(Pod, pod_id, current_user.id, db, "Pod", org_ctx))


@router.put("/{pod_id}", response_model=PodOut)
def update_pod(
    pod_id: uuid.UUID,
    body: PodUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and org_ctx.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot update resources")
    pod = get_or_404(Pod, pod_id, current_user.id, db, "Pod", org_ctx)
    data = body.model_dump(exclude_unset=True)
    agents = data.pop("agents", None)

    for field, value in data.items():
        setattr(pod, field, value)

    if agents is not None:
        _sync_agents(pod, body.agents, db)

    db.commit()
    db.refresh(pod)
    return _pod_out(pod)


@router.delete("/{pod_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pod(
    pod_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and org_ctx.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Admin or owner access required to delete")
    pod = get_or_404(Pod, pod_id, current_user.id, db, "Pod", org_ctx)
    db.delete(pod)
    db.commit()


@router.post("/{pod_id}/duplicate", response_model=PodOut, status_code=status.HTTP_201_CREATED)
def duplicate_pod(
    pod_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if org_ctx and org_ctx.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot create resources")
    pod = get_or_404(Pod, pod_id, current_user.id, db, "Pod", org_ctx)
    new_pod = Pod(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        name=f"{pod.name} (copy)",
        description=pod.description,
    )
    db.add(new_pod)
    db.flush()
    for pa in pod.pod_agents:
        db.add(PodAgent(
            pod_id=new_pod.id,
            agent_id=pa.agent_id,
            execution_order=pa.execution_order,
            count=pa.count,
            on_failure=pa.on_failure,
            max_retries=pa.max_retries,
        ))
    db.commit()
    db.refresh(new_pod)
    return _pod_out(new_pod)
