"""Notification service — Phase 5."""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.notification import Notification


def list_user_notifications(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int = 50,
) -> list[Notification]:
    """Return notifications for a user, newest first."""
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def mark_as_read(
    db: Session, *, notification_id: uuid.UUID, user_id: uuid.UUID
) -> Notification | None:
    """Mark a single notification as read. Returns None if not found or not owned."""
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        return None
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_as_read(db: Session, *, user_id: uuid.UUID) -> int:
    """Mark all unread notifications as read for a user. Returns count updated."""
    stmt = (
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount  # type: ignore[return-value]


def create_notification(
    db: Session,
    *,
    user_id: uuid.UUID,
    module: str,
    type: str,
    title: str,
    message: str,
    link: str | None = None,
) -> Notification:
    """Create a notification (used by other services)."""
    notification = Notification(
        user_id=user_id,
        module=module,
        type=type,
        title=title,
        message=message,
        link=link,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
