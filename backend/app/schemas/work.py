import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WorkCreate(BaseModel):
    department_id: Optional[uuid.UUID] = None
    team_id: Optional[uuid.UUID] = None
    type: str = "generic_request"
    title: str
    description: Optional[str] = None
    priority: Optional[str] = None
    context: dict = {}
    assigned_user_id: Optional[uuid.UUID] = None
    assigned_agent_id: Optional[uuid.UUID] = None


class WorkUpdate(BaseModel):
    department_id: Optional[uuid.UUID] = None
    team_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    context: Optional[dict] = None


class WorkAssign(BaseModel):
    assigned_user_id: Optional[uuid.UUID] = None
    assigned_agent_id: Optional[uuid.UUID] = None


class WorkStatusUpdate(BaseModel):
    status: str
    approval_state: Optional[str] = None


class WorkOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    team_id: Optional[uuid.UUID] = None
    requester_user_id: uuid.UUID
    type: str
    title: str
    description: Optional[str] = None
    priority: Optional[str] = None
    context: dict
    status: str
    assigned_user_id: Optional[uuid.UUID] = None
    assigned_agent_id: Optional[uuid.UUID] = None
    workflow_id: Optional[str] = None
    approval_state: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
