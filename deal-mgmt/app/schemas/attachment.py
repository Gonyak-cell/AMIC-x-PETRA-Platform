"""범용 첨부파일 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    entity_type: str
    entity_id: str | None = None
    # file_path 제거 — 서버 절대 경로 API 노출 방지 (SEC-01)
    file_name: str
    file_size_bytes: int
    mime_type: str
    description: str | None = None
    uploaded_by_email: str | None = None
    created_at: datetime
    updated_at: datetime


class AttachmentListResponse(BaseModel):
    items: list[AttachmentOut]
    total: int
