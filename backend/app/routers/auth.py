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
from app.models.user import User

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

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
