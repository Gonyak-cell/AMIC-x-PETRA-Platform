"""Webhook Pydantic schemas — Phase 5."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WebhookConfigRead(BaseModel):
    id: uuid.UUID
    url: str
    events: list[str]
    is_active: bool
    secret: str | None
    created_at: datetime
    last_triggered_at: datetime | None

    model_config = {"from_attributes": True}


class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=500)
    events: list[str] = Field(..., min_length=1)
    secret: str | None = Field(default=None, max_length=255)


class WebhookUpdate(BaseModel):
    url: str | None = Field(default=None, max_length=500)
    events: list[str] | None = None
    is_active: bool | None = None
    secret: str | None = Field(default=None, max_length=255)


class WebhookTestResult(BaseModel):
    status: str
    message: str | None = None
