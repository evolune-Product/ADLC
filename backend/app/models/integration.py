"""
Model credentials — one workspace, many provider keys.

`Subscription.byo_llm_provider` / `byo_llm_key` held exactly one key for a
whole workspace, which forces a choice the product should not be forcing. Teams
do not use one model for everything: Claude or GPT for the Dev agent where the
diff has to be right, something cheap and fast for QA where the job is running
tests and reading output, a local Ollama for anything that must not leave the
building. One key per workspace makes that impossible to express.

So credentials are rows, keyed by provider, and an agent's `llm_model` picks
which one gets used. The old single-key fields still work and are still read as
a fallback (see `llm_service.resolve_credentials`) so no existing workspace
breaks — but nothing new writes to them.

Secrets here follow the same rule as `connections.access_token`: Fernet-encrypted
before insert, decrypted only in the service layer at call time, never returned
by any endpoint in any form. `masked_hint` exists so the UI can show
`sk-ant-…4f2a` and let someone confirm *which* key is installed without the
API ever handing back the key itself.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ModelCredential(Base):
    __tablename__ = "model_credentials"
    __table_args__ = (
        # One credential per provider per workspace. Two keys for the same
        # vendor in one workspace is an ambiguous lookup at call time, and the
        # legitimate version of that need (prod vs sandbox) is two workspaces.
        UniqueConstraint("org_id", "user_id", "provider", name="uq_model_cred_provider"),
        Index("ix_model_credentials_owner", "user_id", "org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Same dual-ownership shape as every other resource: org_id set = org
    # workspace, org_id NULL + user_id = personal workspace.
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )

    # A key from `llm_providers.PROVIDERS`. Not a DB enum and not a CHECK
    # constraint: the catalogue is expected to grow, and a migration per new
    # vendor would defeat the point of the registry being a dict literal.
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str | None] = mapped_column(String(120))

    # Fernet-encrypted. Nullable because a local Ollama or an unauthenticated
    # internal gateway legitimately has no credential.
    api_key: Mapped[str | None] = mapped_column(Text)
    # Shown in the UI so someone can tell two keys apart. Last four characters
    # only — enough to identify, useless to an attacker.
    masked_hint: Mapped[str | None] = mapped_column(String(32))

    # Required for Azure and every self-hosted deployment, where the endpoint
    # is something only the customer knows.
    base_url: Mapped[str | None] = mapped_column(Text)

    # The model used when an agent names this provider without naming a model.
    default_model: Mapped[str | None] = mapped_column(String(120))

    # Per-model rate overrides, in cents per million tokens:
    #   {"gpt-5": {"input": 300, "output": 1500}}
    # Cost attribution is only honest when the numbers are real, and this
    # platform has published prices for a minority of the twenty-odd providers
    # it can reach. Rather than invent them, a workspace on a negotiated or
    # committed-spend contract enters its own — which is the more accurate
    # figure anyway.
    price_overrides: Mapped[dict] = mapped_column(JSONB, default=dict)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Result of the last verification call. `status` is unknown | ok | error —
    # a key is never assumed to work just because it was saved.
    status: Mapped[str] = mapped_column(String(20), default="unknown")
    status_detail: Mapped[str | None] = mapped_column(Text)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])


def mask(secret: str | None) -> str | None:
    """`sk-ant-api03-…9f2a` — identify without disclosing."""
    if not secret:
        return None
    tail = secret[-4:] if len(secret) >= 4 else ""
    head = secret[:7] if len(secret) > 12 else ""
    return f"{head}…{tail}" if head else f"…{tail}"
