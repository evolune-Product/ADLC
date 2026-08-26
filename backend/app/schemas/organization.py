import uuid
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

# The role list is no longer a hardcoded Literal — it is the catalogue in
# `app/services/org_roles.py`, which is why these are `str` here rather than a
# closed type. A `Literal` would need editing here every time a role is added;
# the actual validation (is this a real, invitable role?) happens in the
# router against `org_roles.INVITABLE_ROLES`, which is the single source of
# truth the DB CHECK constraint is also generated from.
OrgRole = str
InviteRole = str
InviteStatus = Literal['pending', 'accepted', 'expired', 'revoked']


class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class OrgUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    avatar_url: Optional[str] = None


class OrgOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    avatar_url: Optional[str] = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    role: Optional[str] = None  # populated by query join

    model_config = {"from_attributes": True}


class OrgMemberOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    user_id: uuid.UUID
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_avatar: Optional[str] = None
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class OrgMemberUpdate(BaseModel):
    role: InviteRole


class InvitationCreate(BaseModel):
    email: str
    role: InviteRole = "member"


class InvitationOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    invited_by: uuid.UUID
    email: str
    role: str
    token: str
    status: str
    expires_at: Optional[datetime] = None
    created_at: datetime
    accepted_at: Optional[datetime] = None
    invite_url: Optional[str] = None  # populated at creation

    model_config = {"from_attributes": True}
