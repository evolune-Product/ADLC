import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class RunCreate(BaseModel):
    project_id: uuid.UUID
    ticket_id: Optional[uuid.UUID] = None
    pod_id: uuid.UUID


class ApproveBody(BaseModel):
    decision: str   # approved | changes_requested
    comment: Optional[str] = None


class RunStepOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    agent_role: Optional[str] = None
    step_name: Optional[str] = None
    status: Optional[str] = None
    input: Any = {}
    output: Any = {}
    log: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RunOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    ticket_id: Optional[uuid.UUID] = None
    pod_id: uuid.UUID
    status: str
    branch_name: Optional[str] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    current_env_index: int = -1
    deploy_targets: List[Any] = []
    steps: List[RunStepOut] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
