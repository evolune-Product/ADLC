import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class PodAgentCreate(BaseModel):
    agent_id: uuid.UUID
    execution_order: int
    count: int = 1
    on_failure: str = "retry"   # retry | escalate | stop
    max_retries: int = 3


class PodCreate(BaseModel):
    name: str
    description: Optional[str] = None
    agents: List[PodAgentCreate] = []


class PodUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    agents: Optional[List[PodAgentCreate]] = None


class PodAgentOut(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str
    agent_role: str
    execution_order: int
    count: int
    on_failure: str
    max_retries: int

    model_config = {"from_attributes": True}


class PodOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    is_active: bool
    agents: List[PodAgentOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
