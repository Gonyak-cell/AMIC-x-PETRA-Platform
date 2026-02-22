from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PMICategory, PMIPriority, PMITaskStatus


class PMITaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    category: PMICategory
    title: str
    description: str | None = None
    status: PMITaskStatus
    priority: PMIPriority
    assignee_name: str | None = None
    assignee_email: str | None = None
    start_date: str | None = None
    due_date: str | None = None
    completed_date: str | None = None
    dependency_ids: list[str] | None = None
    notes: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PMITaskCreate(BaseModel):
    category: PMICategory
    title: str = Field(..., max_length=300)
    description: str | None = None
    priority: PMIPriority = PMIPriority.MEDIUM
    assignee_name: str | None = Field(None, max_length=200)
    assignee_email: str | None = Field(None, max_length=255)
    start_date: str | None = Field(None, max_length=10)
    due_date: str | None = Field(None, max_length=10)
    dependency_ids: list[str] | None = None
    notes: str | None = None
    sort_order: int = 0


class PMITaskUpdate(BaseModel):
    category: PMICategory | None = None
    title: str | None = Field(None, max_length=300)
    description: str | None = None
    status: PMITaskStatus | None = None
    priority: PMIPriority | None = None
    assignee_name: str | None = Field(None, max_length=200)
    assignee_email: str | None = Field(None, max_length=255)
    start_date: str | None = Field(None, max_length=10)
    due_date: str | None = Field(None, max_length=10)
    completed_date: str | None = Field(None, max_length=10)
    dependency_ids: list[str] | None = None
    notes: str | None = None
    sort_order: int | None = None


class PMISummary(BaseModel):
    total: int
    by_category: dict[str, int]
    by_status: dict[str, int]
    by_priority: dict[str, int]
    completion_rate: float
