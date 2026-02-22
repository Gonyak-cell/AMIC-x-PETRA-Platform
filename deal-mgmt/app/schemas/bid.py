from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BidStatus, BidType, ValuationMethod


class BidOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    buyer_candidate_id: uuid.UUID
    bid_type: BidType
    status: BidStatus
    amount: float | None = None
    currency: str = "KRW"
    valuation_method: ValuationMethod | None = None
    multiple: float | None = None
    submitted_at: str | None = None
    valid_until: str | None = None
    conditions: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class BidCreate(BaseModel):
    buyer_candidate_id: uuid.UUID
    bid_type: BidType
    amount: float | None = None
    currency: str = Field("KRW", max_length=3)
    valuation_method: ValuationMethod | None = None
    multiple: float | None = None
    submitted_at: str | None = Field(None, max_length=10)
    valid_until: str | None = Field(None, max_length=10)
    conditions: str | None = None
    notes: str | None = None


class BidUpdate(BaseModel):
    bid_type: BidType | None = None
    status: BidStatus | None = None
    amount: float | None = None
    currency: str | None = Field(None, max_length=3)
    valuation_method: ValuationMethod | None = None
    multiple: float | None = None
    submitted_at: str | None = Field(None, max_length=10)
    valid_until: str | None = Field(None, max_length=10)
    conditions: str | None = None
    notes: str | None = None


class BidComparisonItem(BaseModel):
    """비교 매트릭스 항목 — 매수자 + 최신 Bid."""

    buyer_id: uuid.UUID
    buyer_name: str
    buyer_type: str
    ioi: BidOut | None = None
    loi: BidOut | None = None
    final_offer: BidOut | None = None
