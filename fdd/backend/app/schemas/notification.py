"""Notification Pydantic schemas — Phase 5."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.notification import NotificationModule


class NotificationRead(BaseModel):
    id: uuid.UUID
    module: NotificationModule
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
    link: str | None

    model_config = {"from_attributes": True}


class NotificationCreate(BaseModel):
    """Internal-use schema for creating notifications programmatically."""

    user_id: uuid.UUID
    module: NotificationModule
    type: str
    title: str
    message: str
    link: str | None = None
