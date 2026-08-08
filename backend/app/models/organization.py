import uuid
import secrets
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("OrgMember", back_populates="org", cascade="all, delete-orphan")
    invitations = relationship("OrgInvitation", back_populates="org", cascade="all, delete-orphan")


class OrgMember(Base):
    __tablename__ = "org_members"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id"),
        CheckConstraint("role IN ('owner','admin','member','viewer')", name="org_members_role_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    org = relationship("Organization", back_populates="members")
    user = relationship("User")


class OrgInvitation(Base):
    __tablename__ = "org_invitations"
    __table_args__ = (
        CheckConstraint("role IN ('admin','member','viewer')", name="org_invitations_role_check"),
        CheckConstraint("status IN ('pending','accepted','expired','revoked')", name="org_invitations_status_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    invited_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(48))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    org = relationship("Organization", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[invited_by])


class SsoConnection(Base):
    """
    An organisation's identity provider.

    OIDC only, deliberately. SAML is the other half of what enterprise buyers
    ask for, but every SAML library worth using pulls in `xmlsec`, which needs
    native libxmlsec1 headers at build time — and this platform's whole pitch
    includes running inside an air-gapped perimeter from a compose file. OIDC
    covers Okta, Entra ID, Google Workspace, Auth0, Keycloak and PingFederate
    over plain HTTPS with no native dependency at all. SAML-only IdPs are a
    real gap and are named as one on the public security page rather than
    quietly implied to work.

    Scoped per organisation, not global: a platform where one tenant's IdP
    config could authenticate into another tenant's data is not multi-tenant,
    it is a shared login page.
    """
    __tablename__ = "sso_connections"
    __table_args__ = (
        # One IdP per org. Two would mean an ambiguous route for the same email.
        UniqueConstraint("org_id", name="uq_sso_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))

    label: Mapped[str] = mapped_column(String(100), default="SSO")   # shown on the button: "Continue with Okta"
    issuer: Mapped[str] = mapped_column(Text)                        # https://acme.okta.com/oauth2/default
    client_id: Mapped[str] = mapped_column(Text)
    # Fernet-encrypted, same as every other secret in this database. Never
    # returned by any endpoint.
    client_secret: Mapped[str] = mapped_column(Text)

    # Which email domains this connection claims. A user typing
    # someone@acme.com on the login page is routed here.
    email_domains: Mapped[list] = mapped_column(JSONB, default=list)
    default_role: Mapped[str] = mapped_column(String(20), default="member")

    # When true, password sign-in is refused for the claimed domains — the
    # difference between offering SSO and actually governing access with it.
    enforced: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
