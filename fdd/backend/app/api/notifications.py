"""Notifications API — Phase 5 Portal endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.schemas.notification import NotificationRead
from app.services.notification.notification_service import (
    list_user_notifications,
    mark_all_as_read,
    mark_as_read,
)

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """사용자별 알림 목록을 조회한다."""
    return list_user_notifications(db, user_id=current_user.id)


# NOTE: /read-all must be defined BEFORE /{notification_id}/read
# to avoid FastAPI matching "read-all" as a path parameter.
@router.patch("/notifications/read-all")
def read_all_notifications(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """모든 알림을 읽음 처리한다."""
    count = mark_all_as_read(db, user_id=current_user.id)
    return {"updated": count}


@router.patch(
    "/notifications/{notification_id}/read", response_model=NotificationRead
)
def read_notification(
    notification_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """단일 알림을 읽음 처리한다."""
    notification = mark_as_read(
        db, notification_id=notification_id, user_id=current_user.id
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification
