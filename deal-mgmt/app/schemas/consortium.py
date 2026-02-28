"""컨소시엄/공동투자 매핑 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConsortiumStatus


class ConsortiumMappingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    lead_buyer_id: uuid.UUID
    lead_buyer_name: str
    co_investor_buyer_id: uuid.UUID
    co_investor_buyer_name: str
    status: ConsortiumStatus
    equity_share_pct: Decimal | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ConsortiumMappingCreate(BaseModel):
    lead_buyer_id: uuid.UUID
    co_investor_buyer_id: uuid.UUID
    status: ConsortiumStatus = ConsortiumStatus.TAPPING
    equity_share_pct: Decimal | None = Field(None, ge=0, le=100)
    notes: str | None = None


class ConsortiumMappingUpdate(BaseModel):
    status: ConsortiumStatus | None = None
    equity_share_pct: Decimal | None = Field(None, ge=0, le=100)
    notes: str | None = None
