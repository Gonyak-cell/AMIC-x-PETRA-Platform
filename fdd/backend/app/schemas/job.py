"""Job Pydantic 스키마 — FDD-1801, FDD-1802."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.job import JobStatus, JobType


class JobCreate(BaseModel):
    job_type: JobType
    deal_id: uuid.UUID | None = None
    input_params: dict[str, Any] | None = None
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=600, ge=30, le=3600)


class JobRead(BaseModel):
    id: uuid.UUID
    job_type: JobType
    status: JobStatus
    deal_id: uuid.UUID | None
    user_id: uuid.UUID | None
    input_params: dict[str, Any] | None
    output_result: dict[str, Any] | None
    error_message: str | None
    progress_percent: int
    progress_message: str | None
    retry_count: int
    max_retries: int
    started_at: datetime | None
    completed_at: datetime | None
    timeout_seconds: int
    created_at: datetime

    model_config = {"from_attributes": True}


class JobProgress(BaseModel):
    id: uuid.UUID
    status: JobStatus
    progress_percent: int
    progress_message: str | None
    retry_count: int
    started_at: datetime | None
    elapsed_seconds: float | None = None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobRead]
    total: int
