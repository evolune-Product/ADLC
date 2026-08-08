import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.organization import OrgMember, SsoConnection
from app.models.user import User
from app.services import sso_service
from app.services.encryption import decrypt_token

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

log = logging.getLogger(__name__)

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
bearer_scheme = HTTPBearer()

# ---------------------------------------------------------------------------
# Pydantic schemas (local to auth — no separate schemas file needed yet)
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    org_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    org_name: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_access_token(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Dependency: get_current_user
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = _decode_token(credentials.credentials)
    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        email=body.email,
        name=body.name,
        hashed_password=_hash_password(body.password),
        org_name=body.org_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    # Checked before the password, and before we look the user up: an
    # organisation that has turned on enforcement is saying "this domain signs
    # in through us", and a password path that still works alongside it is not
    # enforcement, it is a suggestion.
    enforced = _sso_for_email(db, body.email)
    if enforced and enforced.enforced:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your organisation requires signing in with {enforced.label}.",
        )

    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not _verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = _create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/refresh")
def refresh():
    # Placeholder — full implementation in Phase 2 (refresh-token rotation)
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet")


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------

@router.get("/google")
def google_login():
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
def google_callback(code: str, db: Session = Depends(get_db)):
    try:
        with httpx.Client() as client:
            # Exchange auth code for access token
            token_resp = client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            })
            token_resp.raise_for_status()
            google_token = token_resp.json()

            # Fetch Google user profile
            userinfo_resp = client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {google_token['access_token']}"},
            )
            userinfo_resp.raise_for_status()
            google_user = userinfo_resp.json()
    except httpx.HTTPError:
        return RedirectResponse(f"{settings.frontend_url}/login?error=google_failed")

    email = google_user.get("email")
    if not email:
        return RedirectResponse(f"{settings.frontend_url}/login?error=no_email")

    # Find existing user or create one
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            name=google_user.get("name"),
            avatar_url=google_user.get("picture"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Sync avatar from Google if not already set
        if google_user.get("picture") and not user.avatar_url:
            user.avatar_url = google_user["picture"]
            db.commit()

    jwt_token = _create_access_token(user.id)
    return RedirectResponse(f"{settings.frontend_url}/auth/google/callback?token={jwt_token}")


# ---------------------------------------------------------------------------
# GitHub OAuth
# ---------------------------------------------------------------------------

@router.get("/github")
def github_login():
    if not settings.github_client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "user:email",
    }
    return RedirectResponse(f"{GITHUB_AUTH_URL}?{urlencode(params)}")


@router.get("/github/callback")
def github_callback(code: str, db: Session = Depends(get_db)):
    try:
        with httpx.Client() as client:
            # Exchange auth code for access token
            token_resp = client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            token_resp.raise_for_status()
            github_token = token_resp.json().get("access_token")
            if not github_token:
                return RedirectResponse(f"{settings.frontend_url}/login?error=github_failed")

            auth_headers = {
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            }

            # Fetch GitHub user profile
            user_resp = client.get(GITHUB_USER_URL, headers=auth_headers)
            user_resp.raise_for_status()
            github_user = user_resp.json()

            # GitHub may have a null email if set to private — fetch from emails endpoint
            email = github_user.get("email")
            if not email:
                emails_resp = client.get(GITHUB_EMAILS_URL, headers=auth_headers)
                emails_resp.raise_for_status()
                primary = next(
                    (e["email"] for e in emails_resp.json() if e.get("primary") and e.get("verified")),
                    None,
                )
                email = primary

    except httpx.HTTPError:
        return RedirectResponse(f"{settings.frontend_url}/login?error=github_failed")

    if not email:
        return RedirectResponse(f"{settings.frontend_url}/login?error=no_email")

    # Find existing user or create one
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            name=github_user.get("name") or github_user.get("login"),
            avatar_url=github_user.get("avatar_url"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if github_user.get("avatar_url") and not user.avatar_url:
            user.avatar_url = github_user["avatar_url"]
            db.commit()

    jwt_token = _create_access_token(user.id)
    return RedirectResponse(f"{settings.frontend_url}/auth/github/callback?token={jwt_token}")


# ---------------------------------------------------------------------------
# Single sign-on (OIDC)
#
# Three endpoints, in the order a user meets them:
#   GET /auth/sso/lookup?email=   does this address belong to an org with SSO?
#   GET /auth/sso/start?email=    send them to their identity provider
#   GET /auth/sso/callback        the IdP sends them back here
#
# The callback lives on the API rather than the SPA because the code exchange
# uses the client secret. See services/sso_service.py.
# ---------------------------------------------------------------------------

def _sso_for_email(db: Session, email: str) -> SsoConnection | None:
    """The enabled connection that claims this address's domain, if any."""
    domain = sso_service.domain_of(email or "")
    if not domain:
        return None
    for conn in db.query(SsoConnection).filter(SsoConnection.enabled.is_(True)).all():
        if domain in [d.lower() for d in (conn.email_domains or [])]:
            return conn
    return None


@router.get("/sso/lookup")
def sso_lookup(email: str, db: Session = Depends(get_db)):
    """
    Whether to show "Continue with SSO" for this address.

    Deliberately says nothing about whether the *account* exists — only whether
    the domain is configured. Answering the first question would turn the login
    page into a user-enumeration oracle.
    """
    conn = _sso_for_email(db, email)
    if not conn:
        return {"sso": False}
    return {"sso": True, "label": conn.label, "enforced": conn.enforced}


@router.get("/sso/start")
def sso_start(email: str, db: Session = Depends(get_db)):
    conn = _sso_for_email(db, email)
    if not conn:
        return RedirectResponse(f"{settings.frontend_url}/login?error=sso_not_configured")
    try:
        url = sso_service.authorize_url(str(conn.id), conn.issuer, conn.client_id)
    except sso_service.SsoError as exc:
        log.warning("SSO start failed for org %s: %s", conn.org_id, exc)
        return RedirectResponse(f"{settings.frontend_url}/login?error=sso_unavailable")
    return RedirectResponse(url)


@router.get("/sso/callback")
def sso_callback(
    db: Session = Depends(get_db),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    def fail(reason: str):
        return RedirectResponse(f"{settings.frontend_url}/login?error={reason}")

    if error:
        log.info("IdP returned an error: %s (%s)", error, error_description)
        return fail("sso_denied")
    if not code or not state:
        return fail("sso_invalid")

    try:
        claims_state = sso_service.read_state(state)
        conn = (
            db.query(SsoConnection)
            .filter(SsoConnection.id == uuid.UUID(claims_state["cid"]))
            .first()
        )
        if not conn or not conn.enabled:
            return fail("sso_not_configured")

        tokens = sso_service.exchange_code(
            issuer=conn.issuer,
            client_id=conn.client_id,
            client_secret=decrypt_token(conn.client_secret),
            code=code,
            verifier=claims_state["verifier"],
        )
        id_token = tokens.get("id_token")
        if not id_token:
            return fail("sso_invalid")

        claims = sso_service.verify_id_token(
            issuer=conn.issuer, client_id=conn.client_id,
            id_token=id_token, nonce=claims_state["nonce"],
        )
        email, name, picture = sso_service.profile_from(
            claims, issuer=conn.issuer, access_token=tokens.get("access_token")
        )
    except sso_service.SsoError as exc:
        log.warning("SSO callback failed: %s", exc)
        return fail("sso_failed")
    except Exception:
        log.exception("Unexpected SSO callback failure")
        return fail("sso_failed")

    # The IdP is authoritative about who someone is; it is not authoritative
    # about which organisation they may enter. Re-check the domain against the
    # connection that started this flow, so a misconfigured IdP that will
    # authenticate anybody cannot become a way into someone else's tenant.
    if sso_service.domain_of(email) not in [d.lower() for d in (conn.email_domains or [])]:
        log.warning("SSO identity %s is outside the domains claimed by org %s", email, conn.org_id)
        return fail("sso_domain")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Just-in-time provisioning. No password is set: this account can only
        # ever be reached through the identity provider that created it.
        user = User(email=email, name=name, avatar_url=picture)
        db.add(user)
        db.flush()
    elif picture and not user.avatar_url:
        user.avatar_url = picture

    membership = (
        db.query(OrgMember)
        .filter(OrgMember.org_id == conn.org_id, OrgMember.user_id == user.id)
        .first()
    )
    if not membership:
        db.add(OrgMember(org_id=conn.org_id, user_id=user.id, role=conn.default_role))

    conn.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    token = _create_access_token(user.id)
    return RedirectResponse(f"{settings.frontend_url}/auth/sso/callback?token={token}")
