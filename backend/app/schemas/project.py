import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class DeployTargetSchema(BaseModel):
    env: str
    branch: str


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    repo_connection_id: Optional[uuid.UUID] = None
    repo_name: Optional[str] = None
    jira_connection_id: Optional[uuid.UUID] = None
    jira_project_key: Optional[str] = None
    pod_id: Optional[uuid.UUID] = None
    context_md: Optional[str] = None
    deploy_targets: List[DeployTargetSchema] = []


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    repo_connection_id: Optional[uuid.UUID] = None
    repo_name: Optional[str] = None
    jira_connection_id: Optional[uuid.UUID] = None
    jira_project_key: Optional[str] = None
    pod_id: Optional[uuid.UUID] = None
    context_md: Optional[str] = None
    deploy_targets: Optional[List[DeployTargetSchema]] = None
    # {"enabled": bool, "status_map": {milestone: status name}} — see
    # services/writeback_service.py. Free-form because every tracker names its
    # columns differently and validating against a fixed vocabulary would just
    # lock out the teams whose workflow is not Jira's default.
    writeback: Optional[dict] = None
    status: Optional[str] = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    repo_connection_id: Optional[uuid.UUID] = None
    repo_name: Optional[str] = None
    jira_connection_id: Optional[uuid.UUID] = None
    jira_project_key: Optional[str] = None
    pod_id: Optional[uuid.UUID] = None
    pod_name: Optional[str] = None
    context_md: Optional[str] = None
    deploy_targets: List[Any] = []
    writeback: dict = {}
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
