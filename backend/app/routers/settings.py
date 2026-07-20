from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.user import UserOut, UserUpdate, SettingsOut

router = APIRouter()


def _api_key_hint(key: str) -> str | None:
    if not key:
        return None
    if len(key) <= 10:
        return "*" * len(key)
    return key[:10] + "..." + key[-4:]


@router.get("", response_model=SettingsOut)
def get_settings(
    current_user: User = Depends(get_current_user),
):
    key = app_settings.anthropic_api_key
    return SettingsOut(
        user=UserOut.model_validate(current_user),
        llm_model="claude-sonnet-4-6",
        api_key_configured=bool(key),
        api_key_hint=_api_key_hint(key),
    )


@router.put("", response_model=UserOut)
def update_settings(
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.name is not None:
        current_user.name = body.name
    if body.org_name is not None:
        current_user.org_name = body.org_name
    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url
    db.commit()
    db.refresh(current_user)
    return UserOut.model_validate(current_user)
