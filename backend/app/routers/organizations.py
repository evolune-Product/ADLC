"""
Organizations router
--------------------
Multi-tenant org management: create org, manage members, invite via token link.

Routes
------
POST   /orgs/                              Create org (creator becomes owner)
GET    /orgs/                              List orgs current user belongs to
GET    /orgs/{org_id}                      Get org detail (must be member)
PUT    /orgs/{org_id}                      Update org name/avatar (admin+)
DELETE /orgs/{org_id}                      Delete org + cascade (owner only)
GET    /orgs/{org_id}/members              List all members
PUT    /orgs/{org_id}/members/{user_id}    Update member role (admin+)
DELETE /orgs/{org_id}/members/{user_id}    Remove member (admin+)
POST   /orgs/{org_id}/leave               Current user leaves (owner must transfer first)
POST   /orgs/{org_id}/invitations          Create invite, return invite_url (admin+)
GET    /orgs/{org_id}/invitations          List pending invites (admin+)
DELETE /orgs/{org_id}/invitations/{inv_id} Revoke invite (admin+)
POST   /invitations/{token}/accept         Accept invite (authenticated; validates email match)
"""

import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import org_roles
from app.models.organization import Organization, OrgMember, OrgInvitation, SsoConnection
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.organization import (
    OrgCreate, OrgUpdate, OrgOut,
    OrgMemberOut, OrgMemberUpdate,
    InvitationCreate, InvitationOut,
)
from app.config import settings
from app.services import sso_service
from app.services.encryption import encrypt_token

router = APIRouter()
inv_router = APIRouter()   # mounted at /invitations


# ─── Slug generation ─────────────────────────────────────────────────────────

def _make_slug(name: str, db: Session) -> str:
    base = name.lower().replace(" ", "-")[:80]
    # keep only alphanumeric and hyphens
    import re
    base = re.sub(r"[^a-z0-9-]", "", base).strip("-") or "org"
    slug = base
    if db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base}-{secrets.token_hex(3)}"
    return slug


# ─── Member role helpers ──────────────────────────────────────────────────────

def _get_member(org_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> OrgMember | None:
    return db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_id == user_id,
    ).first()


def _require_member(org_id: uuid.UUID, current_user: User, db: Session) -> OrgMember:
    m = _get_member(org_id, current_user.id, db)
    if not m:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return m


def _require_admin(org_id: uuid.UUID, current_user: User, db: Session) -> OrgMember:
    m = _require_member(org_id, current_user, db)
    if m.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Admin or owner access required")
    return m


def _require_owner(org_id: uuid.UUID, current_user: User, db: Session) -> OrgMember:
    m = _require_member(org_id, current_user, db)
    if m.role != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    return m


def _org_out(org: Organization, role: str | None = None) -> OrgOut:
    return OrgOut(
        id=org.id,
        name=org.name,
        slug=org.slug,
        avatar_url=org.avatar_url,
        created_by=org.created_by,
        industry=org.industry,
        company_size=org.company_size,
        timezone=org.timezone,
        default_locale=org.default_locale,
        description=org.description,
        logo_url=org.logo_url,
        created_at=org.created_at,
        updated_at=org.updated_at,
        role=role,
    )


def _member_out(m: OrgMember) -> OrgMemberOut:
    return OrgMemberOut(
        id=m.id,
        org_id=m.org_id,
        user_id=m.user_id,
        user_name=m.user.name if m.user else None,
        user_email=m.user.email if m.user else None,
        user_avatar=m.user.avatar_url if m.user else None,
        role=m.role,
        joined_at=m.joined_at,
    )


def _inv_out(inv: OrgInvitation, invite_url: str | None = None) -> InvitationOut:
    return InvitationOut(
        id=inv.id,
        org_id=inv.org_id,
        invited_by=inv.invited_by,
        email=inv.email,
        role=inv.role,
        token=inv.token,
        status=inv.status,
        expires_at=inv.expires_at,
        created_at=inv.created_at,
        accepted_at=inv.accepted_at,
        invite_url=invite_url,
    )


# ─── Org CRUD ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=OrgOut, status_code=status.HTTP_201_CREATED)
def create_org(
    body: OrgCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    slug = _make_slug(body.name, db)
    org = Organization(name=body.name, slug=slug, created_by=current_user.id)
    db.add(org)
    db.flush()
    member = OrgMember(org_id=org.id, user_id=current_user.id, role="owner")
    db.add(member)
    db.commit()
    db.refresh(org)
    return _org_out(org, role="owner")


@router.get("/", response_model=List[OrgOut])
def list_orgs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memberships = (
        db.query(OrgMember)
        .filter(OrgMember.user_id == current_user.id)
        .all()
    )
    result = []
    for m in memberships:
        org = db.query(Organization).filter(Organization.id == m.org_id).first()
        if org:
            result.append(_org_out(org, role=m.role))
    return result


@router.get("/roles")
def list_roles():
    """
    The role catalogue — label, description and category for every role a
    member can be invited as. Public to any authenticated user, not just
    admins: someone deciding *which* role to ask for needs to read the
    descriptions before they can ask.

    Registered before `/{org_id}` so FastAPI matches the literal path
    `/orgs/roles` rather than treating "roles" as an attempted UUID.
    """
    return {"roles": org_roles.catalog()}


@router.get("/{org_id}", response_model=OrgOut)
def get_org(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    m = _require_member(org_id, current_user, db)
    return _org_out(org, role=m.role)


@router.put("/{org_id}", response_model=OrgOut)
def update_org(
    org_id: uuid.UUID,
    body: OrgUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    m = _require_admin(org_id, current_user, db)
    if body.name is not None:
        org.name = body.name
    if body.avatar_url is not None:
        org.avatar_url = body.avatar_url
    if body.industry is not None:
        org.industry = body.industry
    if body.company_size is not None:
        org.company_size = body.company_size
    if body.timezone is not None:
        org.timezone = body.timezone
    if body.default_locale is not None:
        org.default_locale = body.default_locale
    if body.description is not None:
        org.description = body.description
    if body.logo_url is not None:
        org.logo_url = body.logo_url
    db.commit()
    db.refresh(org)
    return _org_out(org, role=m.role)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_org(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    _require_owner(org_id, current_user, db)
    db.delete(org)
    db.commit()


# ─── Members ──────────────────────────────────────────────────────────────────

@router.get("/{org_id}/members", response_model=List[OrgMemberOut])
def list_members(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_member(org_id, current_user, db)
    members = db.query(OrgMember).filter(OrgMember.org_id == org_id).all()
    return [_member_out(m) for m in members]


@router.put("/{org_id}/members/{target_user_id}", response_model=OrgMemberOut)
def update_member_role(
    org_id: uuid.UUID,
    target_user_id: uuid.UUID,
    body: OrgMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    actor = _require_admin(org_id, current_user, db)
    if body.role not in org_roles.INVITABLE_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"'{body.role}' is not an assignable role. Choose one from GET /orgs/roles.",
        )
    target = _get_member(org_id, target_user_id, db)
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    # Owner cannot be demoted by anyone except themselves transferring ownership
    if target.role == "owner":
        raise HTTPException(status_code=403, detail="Cannot change the owner's role; transfer ownership first")
    # Admin cannot promote to owner — ownership moves by transfer, never by a
    # role assignment, so "owner" is deliberately excluded from INVITABLE_ROLES
    # and this check is really just documentation of why that 422 fires above.
    # Admin cannot update another admin (only owner can)
    if actor.role == "admin" and target.role == "admin":
        raise HTTPException(status_code=403, detail="Admins cannot modify other admins")
    target.role = body.role
    db.commit()
    db.refresh(target)
    return _member_out(target)


@router.delete("/{org_id}/members/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    org_id: uuid.UUID,
    target_user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(org_id, current_user, db)
    target = _get_member(org_id, target_user_id, db)
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    if target.role == "owner":
        raise HTTPException(status_code=403, detail="Cannot remove the owner")
    db.delete(target)
    db.commit()


@router.post("/{org_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_org(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = _require_member(org_id, current_user, db)
    if m.role == "owner":
        raise HTTPException(
            status_code=403,
            detail="Owner cannot leave. Transfer ownership first.",
        )
    db.delete(m)
    db.commit()


# ─── Invitations ─────────────────────────────────────────────────────────────

@router.post("/{org_id}/invitations", response_model=InvitationOut, status_code=status.HTTP_201_CREATED)
def create_invitation(
    org_id: uuid.UUID,
    body: InvitationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(org_id, current_user, db)
    if body.role not in org_roles.INVITABLE_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"'{body.role}' is not an invitable role. Choose one from GET /orgs/roles.",
        )
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Revoke any existing pending invite for same email+org
    existing = db.query(OrgInvitation).filter(
        OrgInvitation.org_id == org_id,
        OrgInvitation.email == body.email.lower(),
        OrgInvitation.status == "pending",
    ).first()
    if existing:
        existing.status = "revoked"

    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    inv = OrgInvitation(
        org_id=org_id,
        invited_by=current_user.id,
        email=body.email.lower(),
        role=body.role,
        token=token,
        expires_at=expires_at,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    # Build invite URL from frontend_url setting
    invite_url = f"{settings.frontend_url}/invitations/{token}"
    return _inv_out(inv, invite_url=invite_url)


@router.get("/{org_id}/invitations", response_model=List[InvitationOut])
def list_invitations(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(org_id, current_user, db)
    invs = db.query(OrgInvitation).filter(
        OrgInvitation.org_id == org_id,
        OrgInvitation.status == "pending",
    ).order_by(OrgInvitation.created_at.desc()).all()
    return [_inv_out(i) for i in invs]


@router.delete("/{org_id}/invitations/{inv_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    org_id: uuid.UUID,
    inv_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(org_id, current_user, db)
    inv = db.query(OrgInvitation).filter(
        OrgInvitation.id == inv_id,
        OrgInvitation.org_id == org_id,
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    inv.status = "revoked"
    db.commit()


# ─── Accept invitation (mounted at /invitations/{token}/accept) ───────────────

@inv_router.post("/{token}/accept", response_model=OrgMemberOut)
def accept_invitation(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = db.query(OrgInvitation).filter(OrgInvitation.token == token).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")

    now = datetime.now(timezone.utc)

    # Check expiry
    if inv.expires_at and inv.expires_at.replace(tzinfo=timezone.utc) < now:
        inv.status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Invitation has expired")

    if inv.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Invitation is {inv.status}",
        )

    # Email must match (case-insensitive)
    if inv.email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=403,
            detail="This invitation was sent to a different email address",
        )

    # Check if already a member
    existing = _get_member(inv.org_id, current_user.id, db)
    if existing:
        raise HTTPException(status_code=409, detail="Already a member of this organization")

    member = OrgMember(
        org_id=inv.org_id,
        user_id=current_user.id,
        role=inv.role,
    )
    db.add(member)

    inv.status = "accepted"
    inv.accepted_at = now
    db.commit()
    db.refresh(member)
    return _member_out(member)


# ═══════════════════════════════════════════════════════════════════════════════
# Single sign-on
#
# Owner-only, because an SSO connection decides who can get into the
# organisation at all — that is a strictly larger power than any admin action,
# and an admin who can point the org at an IdP they control can let themselves
# in as anyone.
# ═══════════════════════════════════════════════════════════════════════════════

class SsoBody(BaseModel):
    label: str = Field("SSO", max_length=100)
    issuer: str
    client_id: str
    # Optional on update: an admin editing the domain list should not have to
    # re-enter a secret they cannot read back.
    client_secret: str | None = None
    email_domains: List[str] = []
    default_role: str = "member"
    enforced: bool = False
    enabled: bool = True


def _sso_out(conn: SsoConnection) -> dict:
    return {
        "id": str(conn.id),
        "label": conn.label,
        "issuer": conn.issuer,
        "client_id": conn.client_id,
        # The secret is never returned, only whether one is set. A settings page
        # that can echo a client secret is a settings page that leaks it.
        "client_secret_set": bool(conn.client_secret),
        "email_domains": conn.email_domains or [],
        "default_role": conn.default_role,
        "enforced": conn.enforced,
        "enabled": conn.enabled,
        "redirect_uri": sso_service.redirect_uri(),
        "last_login_at": conn.last_login_at.isoformat() if conn.last_login_at else None,
    }


@router.get("/{org_id}/sso")
def get_sso(org_id: uuid.UUID, db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)):
    _require_admin(org_id, current_user, db)
    conn = db.query(SsoConnection).filter(SsoConnection.org_id == org_id).first()
    if not conn:
        return {"configured": False, "redirect_uri": sso_service.redirect_uri()}
    return {"configured": True, **_sso_out(conn)}


@router.put("/{org_id}/sso")
def put_sso(org_id: uuid.UUID, body: SsoBody, db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)):
    _require_owner(org_id, current_user, db)

    domains = sorted({d.strip().lower().lstrip("@") for d in body.email_domains if d.strip()})
    if not domains:
        raise HTTPException(400, "Add at least one email domain, or nobody can be routed here.")

    # A domain can only be claimed once across the whole platform. Two orgs
    # claiming acme.com would make "which IdP does this user go to" a coin toss,
    # and the loser's users would land in the winner's tenant.
    clash = (
        db.query(SsoConnection)
        .filter(SsoConnection.org_id != org_id)
        .all()
    )
    for other in clash:
        overlap = set(domains) & {d.lower() for d in (other.email_domains or [])}
        if overlap:
            raise HTTPException(409, f"{', '.join(sorted(overlap))} is already claimed by another organisation.")

    # Fail here rather than on Monday morning: an unreachable issuer or a
    # missing JWKS is a typo, and the admin is looking at the form right now.
    try:
        sso_service.check_connection(body.issuer)
    except sso_service.SsoError as exc:
        raise HTTPException(400, str(exc))

    conn = db.query(SsoConnection).filter(SsoConnection.org_id == org_id).first()
    if not conn:
        if not body.client_secret:
            raise HTTPException(400, "A client secret is required to create a connection.")
        conn = SsoConnection(org_id=org_id)
        db.add(conn)

    conn.label = body.label or "SSO"
    conn.issuer = body.issuer.rstrip("/")
    conn.client_id = body.client_id
    if body.client_secret:
        conn.client_secret = encrypt_token(body.client_secret)
    conn.email_domains = domains
    conn.default_role = body.default_role if body.default_role in ("member", "admin") else "member"
    conn.enforced = body.enforced
    conn.enabled = body.enabled
    db.commit()
    db.refresh(conn)
    return {"configured": True, **_sso_out(conn)}


@router.delete("/{org_id}/sso", status_code=status.HTTP_204_NO_CONTENT)
def delete_sso(org_id: uuid.UUID, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    _require_owner(org_id, current_user, db)
    conn = db.query(SsoConnection).filter(SsoConnection.org_id == org_id).first()
    if conn:
        db.delete(conn)
        db.commit()
