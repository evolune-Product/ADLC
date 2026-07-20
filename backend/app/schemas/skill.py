import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SkillCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None  # dev | qa | devops | planning | custom
    md_content: str
    version: str = "1.0.0"


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    md_content: Optional[str] = None
    version: Optional[str] = None
    is_active: Optional[bool] = None


class SkillOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    md_content: str
    version: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
