"""
Catalog models — templates and the skill marketplace.

Template         a reusable skill / agent / pod definition (built-in or user-made)
MarketplaceListing  a template published for others to install
MarketplaceInstall  install record (drives install counts and revenue share)
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, func, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Template(Base):
    __tablename__ = "templates"
    __table_args__ = (
        Index("ix_templates_kind_builtin", "kind", "is_builtin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)

    kind: Mapped[str] = mapped_column(String(20))          # skill | agent | pod
    slug: Mapped[str] = mapped_column(String(160), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    # payload shape depends on kind:
    #   skill → {md_content, category}
    #   agent → {role, llm_model, skills:[slug], config}
    #   pod   → {agents:[{role, template_slug, execution_order, on_failure, max_retries}]}
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    listing = relationship("MarketplaceListing", back_populates="template", uselist=False, cascade="all, delete-orphan")


class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("templates.id", ondelete="CASCADE"), unique=True)
    publisher_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    publisher_name: Mapped[str | None] = mapped_column(String(255))

    visibility: Mapped[str] = mapped_column(String(20), default="public")   # public | org | private
    price_cents: Mapped[int] = mapped_column(Integer, default=0)            # 0 = free
    revenue_share_pct: Mapped[int] = mapped_column(Integer, default=70)     # creator's cut
    install_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_sum: Mapped[int] = mapped_column(Integer, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)       # first-party / reviewed
    readme_md: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    template = relationship("Template", back_populates="listing")

    @property
    def rating(self) -> float:
        return round(self.rating_sum / self.rating_count, 2) if self.rating_count else 0.0


class MarketplaceInstall(Base):
    __tablename__ = "marketplace_installs"
    __table_args__ = (
        UniqueConstraint("listing_id", "user_id", "org_id", name="uq_install_owner"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("marketplace_listings.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    installed_resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    rating: Mapped[int | None] = mapped_column(Integer)
    review_comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
