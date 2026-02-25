"""미팅 액션아이템 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActionItemStatus, NegotiationIssuePriority


class MeetingActionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meeting_id: uuid.UUID
    title: str
    description: str | None = None
    assignee_email: str | None = None
    assignee_name: str | None = None
    due_date: str | None = None
    status: ActionItemStatus
    priority: NegotiationIssuePriority | None = None
    created_at: datetime
    updated_at: datetime


class MeetingActionItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    assignee_email: str | None = None
    assignee_name: str | None = None
    due_date: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: ActionItemStatus = ActionItemStatus.PENDING
    priority: NegotiationIssuePriority | None = None


class MeetingActionItemUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    assignee_email: str | None = None
    assignee_name: str | None = None
    due_date: str | None = None
    status: ActionItemStatus | None = None
    priority: NegotiationIssuePriority | None = None


class MeetingActionItemListResponse(BaseModel):
    items: list[MeetingActionItemOut]
    total: int
