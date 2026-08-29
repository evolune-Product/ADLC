import uuid
from typing import Optional
from pydantic import BaseModel


class DeskRequestCreate(BaseModel):
    title: str
    description: Optional[str] = None


class DepartmentSummaryOut(BaseModel):
    id: uuid.UUID
    name: str
    active_work_count: int
    member_count: int
