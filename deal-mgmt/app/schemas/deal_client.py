"""DealClient 스키마 — 고객-거래 접근 매핑."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DealClientCreate(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    organization: str | None = Field(default=None, max_length=200)


class DealClientOut(BaseModel):
    id: uuid.UUID
    transaction_id: uuid.UUID
    email: str
    display_name: str
    organization: str | None
    added_by_email: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ClientDealSummary(BaseModel):
    """관리자용 — 특정 이메일로 배정된 딜 요약."""

    id: uuid.UUID
    transaction_id: uuid.UUID
    transaction_name: str
    codename: str
    created_at: datetime
