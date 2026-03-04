"""Email preference service — Phase 5.

Implements upsert pattern: GET returns default if not found,
PUT creates or updates.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email_preference import EmailPreference

_DEFAULT_PREFS = {
    "deal_updates": False,
    "watchlist_alerts": False,
    "im_completion": False,
    "weekly_digest": False,
}


def get_email_preferences(db: Session, *, user_id: uuid.UUID) -> EmailPreference | dict:
    """Get email preferences for a user. Returns default dict if not found."""
    stmt = select(EmailPreference).where(EmailPreference.user_id == user_id)
    pref = db.scalar(stmt)
    if pref is None:
        return dict(_DEFAULT_PREFS)
    return pref


def upsert_email_preferences(
    db: Session,
    *,
    user_id: uuid.UUID,
    deal_updates: bool,
    watchlist_alerts: bool,
    im_completion: bool,
    weekly_digest: bool,
) -> EmailPreference:
    """Create or update email preferences for a user."""
    stmt = select(EmailPreference).where(EmailPreference.user_id == user_id)
    pref = db.scalar(stmt)

    if pref is None:
        pref = EmailPreference(
            user_id=user_id,
            deal_updates=deal_updates,
            watchlist_alerts=watchlist_alerts,
            im_completion=im_completion,
            weekly_digest=weekly_digest,
        )
        db.add(pref)
    else:
        pref.deal_updates = deal_updates
        pref.watchlist_alerts = watchlist_alerts
        pref.im_completion = im_completion
        pref.weekly_digest = weekly_digest

    db.commit()
    db.refresh(pref)
    return pref
