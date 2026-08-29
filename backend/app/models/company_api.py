"""
BYO API integration registry — a company connects its own internal or
third-party HTTP APIs and the workflow engine's `api_call` node can then
invoke them for real (see `app/services/company_api_service.py`).

This is deliberately NOT a second plugin registry. `plugins.py` covers
KNOWN vendors (GitHub, Slack, Jira, ...) with a hand-written verify recipe
per vendor. `CompanyApi` covers the opposite case: an arbitrary API a
customer's own company runs or subscribes to, that this platform has never
heard of and cannot write a bespoke recipe for — a base URL, an auth
scheme, and a set of named endpoints the customer defines themselves.

Secrets in `auth_config` are Fernet-encrypted the same way
`ModelCredential.api_key` / `Connection.access_token` are — see
`app/services/encryption.py`. Never logged, never returned by any endpoint.

`auth_type` starts with three real, simple schemes. `oauth2` is accepted by
the CHECK constraint as a documented future extension (a full authorization-
code + refresh-token flow is real design work, out of scope this session) —
creating a CompanyApi with `auth_type='oauth2'` is intentionally rejected at
the service/router layer until that flow exists, so nothing pretends to work.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

AUTH_TYPES = ("none", "api_key", "bearer", "basic", "oauth2")
# oauth2 is in the CHECK (schema future-proofed) but not implemented — see
# company_api_service.SUPPORTED_AUTH_TYPES, which the router enforces against.
STATUS_VALUES = ("active", "disabled")
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")


class CompanyApi(Base):
    __tablename__ = "company_apis"
    __table_args__ = (
        CheckConstraint(f"auth_type IN {AUTH_TYPES}", name="company_apis_auth_type_check"),
        CheckConstraint(f"status IN {STATUS_VALUES}", name="company_apis_status_check"),
        Index("ix_company_apis_org", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    auth_type: Mapped[str] = mapped_column(String(20), nullable=False, default="none", server_default="none")

    # api_key:  {"header": "X-API-Key", "value": "<fernet>"}
    # bearer:   {"token": "<fernet>"}
    # basic:    {"username": "...", "password": "<fernet>"}
    # oauth2:   reserved, not populated by any code path yet.
    # Secrets are Fernet-encrypted strings inside this JSONB, same convention
    # as every other credential store in this codebase.
    auth_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    default_headers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=20, server_default="20")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    org = relationship("Organization")
    endpoints = relationship("CompanyApiEndpoint", back_populates="company_api", cascade="all, delete-orphan")


class CompanyApiEndpoint(Base):
    __tablename__ = "company_api_endpoints"
    __table_args__ = (
        CheckConstraint(f"method IN {METHODS}", name="company_api_endpoints_method_check"),
        Index("ix_company_api_endpoints_api", "company_api_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_api_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_apis.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)  # relative to base_url
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET", server_default="GET")
    description: Mapped[str | None] = mapped_column(Text)
    # Informational only this session — not enforced against the actual
    # request/response at call time. A future step can validate against these.
    request_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company_api = relationship("CompanyApi", back_populates="endpoints")
