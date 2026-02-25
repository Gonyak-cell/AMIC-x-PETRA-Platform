"""계약 마크업 버전 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ContractMarkupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contract_id: uuid.UUID
    meeting_id: uuid.UUID | None = None
    version_label: str
    version_number: int
    source_party: str | None = None
    file_path: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    changes_summary: str | None = None
    key_changes: list[str] | None = None
    created_by_email: str | None = None
    created_at: datetime
    updated_at: datetime


class ContractMarkupCreate(BaseModel):
    """multipart/form-data와 함께 사용 — file은 UploadFile로 별도 수신."""
    meeting_id: uuid.UUID | None = None
    version_label: str = Field(..., min_length=1, max_length=100)
    source_party: str | None = None
    changes_summary: str | None = None
    key_changes: list[str] | None = None


class ContractMarkupListResponse(BaseModel):
    items: list[ContractMarkupOut]
    total: int
