import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TicketOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    jira_id: str
    title: str
    description: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    jira_url: Optional[str] = None
    synced_at: datetime

    model_config = {"from_attributes": True}
