import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    trigger_type: str = "manual"
    definition: dict
    is_active: bool = True


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    trigger_type: Optional[str] = None
    definition: Optional[dict] = None
    is_active: Optional[bool] = None


class WorkflowOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    name: str
    description: Optional[str] = None
    trigger_type: str
    definition: dict
    is_active: bool
    version: int
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowExecuteRequest(BaseModel):
    work_id: Optional[uuid.UUID] = None
    initial_context: dict = {}


class WorkflowExecutionOut(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    organization_id: uuid.UUID
    work_id: Optional[uuid.UUID] = None
    status: str
    current_node_id: Optional[str] = None
    context: dict
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    model_config = {"from_attributes": True}


class WorkflowExecutionStepOut(BaseModel):
    id: uuid.UUID
    execution_id: uuid.UUID
    node_id: str
    node_type: str
    status: str
    input: dict
    output: Optional[dict] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WorkflowExecutionDetailOut(WorkflowExecutionOut):
    steps: list[WorkflowExecutionStepOut] = []
