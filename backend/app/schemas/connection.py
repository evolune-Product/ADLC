import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ConnectionCreate(BaseModel):
    # Optional: defaults to the catalogue's display label (app/services/plugins.py)
    # when omitted, matching how a plain "Connect" click behaves for every entry.
    name: Optional[str] = None
    type: str  # any key in the plugin catalogue: github | gitlab | jira | linear | slack | ...
    access_token: Optional[str] = None   # PAT / API key / bot token
    workspace_url: Optional[str] = None  # host or site URL for token+url plugins;
                                          # for webhook plugins this IS the secret (see router)
    email: Optional[str] = None          # basic-auth username (Jira/Confluence, etc.)
    extra: Optional[str] = None          # secondary field a few plugins need (e.g. Telegram chat ID)


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
