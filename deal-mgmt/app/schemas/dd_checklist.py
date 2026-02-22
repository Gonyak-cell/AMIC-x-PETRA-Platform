from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DDChecklistStatus, DDWorkstream


class DDChecklistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    workstream: DDWorkstream
    title: str
    description: str | None = None
    assignee_email: str | None = None
    status: DDChecklistStatus
    due_date: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class DDChecklistCreate(BaseModel):
    workstream: DDWorkstream
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    assignee_email: str | None = Field(None, max_length=255)
    due_date: str | None = Field(None, max_length=10)
    notes: str | None = None


class DDChecklistUpdate(BaseModel):
    workstream: DDWorkstream | None = None
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    assignee_email: str | None = Field(None, max_length=255)
    status: DDChecklistStatus | None = None
    due_date: str | None = Field(None, max_length=10)
    notes: str | None = None


class DDWorkstreamSummary(BaseModel):
    workstream: DDWorkstream
    total: int
    completed: int
    in_progress: int
    not_started: int


class DDChecklistSummary(BaseModel):
    total: int
    by_workstream: list[DDWorkstreamSummary]
    overall_completion_pct: float
