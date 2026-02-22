from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ClosingCategory, ClosingConditionStatus


class ClosingChecklistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    category: ClosingCategory
    title: str
    description: str | None = None
    status: ClosingConditionStatus
    responsible_party: str | None = None
    responsible_email: str | None = None
    due_date: str | None = None
    completed_date: str | None = None
    document_url: str | None = None
    notes: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class ClosingChecklistCreate(BaseModel):
    category: ClosingCategory
    title: str = Field(..., max_length=300)
    description: str | None = None
    responsible_party: str | None = Field(None, max_length=200)
    responsible_email: str | None = Field(None, max_length=255)
    due_date: str | None = Field(None, max_length=10)
    document_url: str | None = Field(None, max_length=500)
    notes: str | None = None
    sort_order: int = 0


class ClosingChecklistUpdate(BaseModel):
    category: ClosingCategory | None = None
    title: str | None = Field(None, max_length=300)
    description: str | None = None
    status: ClosingConditionStatus | None = None
    responsible_party: str | None = Field(None, max_length=200)
    responsible_email: str | None = Field(None, max_length=255)
    due_date: str | None = Field(None, max_length=10)
    completed_date: str | None = Field(None, max_length=10)
    document_url: str | None = Field(None, max_length=500)
    notes: str | None = None
    sort_order: int | None = None


class ClosingChecklistSummary(BaseModel):
    total: int
    by_category: dict[str, int]
    by_status: dict[str, int]
    completion_rate: float
