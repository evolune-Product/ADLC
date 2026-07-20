import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class AgentSkillOut(BaseModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    skill_name: str
    priority: int

    model_config = {"from_attributes": True}


class AgentCreate(BaseModel):
    name: str
    role: str                              # sprint | dev | qa | devops | custom
    description: Optional[str] = None
    repo_connection_id: Optional[uuid.UUID] = None
    default_branch: str = "main"
    branch_prefix: str = "agent/"
    llm_model: str = "claude-sonnet-4-6"
    max_iterations: int = 10
    skill_ids: List[uuid.UUID] = []        # ordered list — index = priority


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    repo_connection_id: Optional[uuid.UUID] = None
    default_branch: Optional[str] = None
    branch_prefix: Optional[str] = None
    llm_model: Optional[str] = None
    max_iterations: Optional[int] = None
    is_active: Optional[bool] = None
    skill_ids: Optional[List[uuid.UUID]] = None


class AgentOut(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    description: Optional[str] = None
    repo_connection_id: Optional[uuid.UUID] = None
    default_branch: str
    branch_prefix: str
    llm_model: str
    max_iterations: int
    is_active: bool
    skills: List[AgentSkillOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
