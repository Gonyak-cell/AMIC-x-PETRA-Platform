"""Settings API — Phase 5 Portal endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.schemas.email_preference import EmailPreferenceRead, EmailPreferenceUpdate
from app.services.settings.email_preference_service import (
    get_email_preferences,
    upsert_email_preferences,
)

router = APIRouter(tags=["settings"])


@router.get("/settings/email-preferences", response_model=EmailPreferenceRead)
def get_email_prefs(
    current_user: CurrentUser = require_permission(Permission.SETTINGS_READ),
    db: Session = Depends(get_db),
):
    """이메일 알림 설정을 조회한다."""
    prefs = get_email_preferences(db, user_id=current_user.id)
    if isinstance(prefs, dict):
        return prefs
    return EmailPreferenceRead.model_validate(prefs)


@router.put("/settings/email-preferences", response_model=EmailPreferenceRead)
def update_email_prefs(
    body: EmailPreferenceUpdate,
    current_user: CurrentUser = require_permission(Permission.SETTINGS_UPDATE),
    db: Session = Depends(get_db),
):
    """이메일 알림 설정을 변경한다."""
    pref = upsert_email_preferences(
        db,
        user_id=current_user.id,
        deal_updates=body.deal_updates,
        watchlist_alerts=body.watchlist_alerts,
        im_completion=body.im_completion,
        weekly_digest=body.weekly_digest,
    )
    return EmailPreferenceRead.model_validate(pref)
