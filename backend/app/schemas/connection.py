import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ConnectionCreate(BaseModel):
    name: str
    type: str  # github | gitlab | jira | github_actions
    workspace_url: Optional[str] = None  # Jira base URL
    access_token: Optional[str] = None   # Jira API token or GitHub PAT
    email: Optional[str] = None          # Jira account email


class ConnectionUpdate(BaseModel):
    name: Optional[str] = None
    workspace_url: Optional[str] = None


class ConnectionOut(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    status: str
    workspace_url: Optional[str] = None
    # ORM stores as metadata_ (to avoid SQLAlchemy reserved word); output as metadata
    metadata: dict = Field(default={}, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
