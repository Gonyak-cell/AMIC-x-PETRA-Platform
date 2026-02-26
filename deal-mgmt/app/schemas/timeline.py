from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TimelineEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    event_type: str
    title: str
    description: str | None = None
    event_date: str
    is_auto_generated: bool
    created_by: str | None = None
    created_at: datetime


class TimelineEventCreate(BaseModel):
    event_type: str = Field(..., max_length=50)
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    event_date: str = Field(..., max_length=10)


class TimelineResponse(BaseModel):
    items: list[TimelineEventOut]
    total: int


# ── Gantt Timeline ────────────────────────────────────────


class PhaseBar(BaseModel):
    phase: str
    label: str
    start_date: str | None = None
    end_date: str | None = None
    status: str  # "completed" | "active" | "upcoming"
    order: int


class GanttMilestone(BaseModel):
    label: str
    date: str
    type: str  # "PHASE_TRANSITION" | "DOCUMENT_SIGNED" | "CUSTOM"


class GanttResponse(BaseModel):
    phases: list[PhaseBar]
    milestones: list[GanttMilestone]
    target_close_date: str | None = None
    deal_start_date: str
