import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    org_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    org_name: Optional[str] = None
    avatar_url: Optional[str] = None


class SettingsOut(BaseModel):
    user: UserOut
    llm_model: str
    api_key_configured: bool
    api_key_hint: Optional[str] = None


class LLMStatusOut(BaseModel):
    model: str
    api_key_configured: bool
    api_key_hint: Optional[str] = None
