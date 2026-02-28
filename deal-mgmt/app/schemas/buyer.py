from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BuyerCandidateStatus, BuyerTier, BuyerType, DealRole


class BuyerCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    company_name: str
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    buyer_type: BuyerType
    status: BuyerCandidateStatus
    tier: BuyerTier | None = None
    corp_code: str | None = None
    deal_role: DealRole | None = None
    ioi_value: Decimal | None = None
    ioi_date: str | None = None
    loi_value: Decimal | None = None
    loi_date: str | None = None
    final_offer_value: Decimal | None = None
    rejection_reason: str | None = None
    notes: str | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime


class BuyerCandidateCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    contact_name: str | None = Field(None, max_length=100)
    contact_email: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=20)
    buyer_type: BuyerType
    tier: BuyerTier | None = None
    corp_code: str | None = Field(None, max_length=8)
    deal_role: DealRole | None = None
    notes: str | None = None
    extra_data: dict | None = None


class BuyerCandidateUpdate(BaseModel):
    company_name: str | None = Field(None, min_length=1, max_length=200)
    contact_name: str | None = Field(None, max_length=100)
    contact_email: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=20)
    buyer_type: BuyerType | None = None
    status: BuyerCandidateStatus | None = None
    tier: BuyerTier | None = None
    corp_code: str | None = Field(None, max_length=8)
    deal_role: DealRole | None = None
    ioi_value: Decimal | None = None
    ioi_date: str | None = Field(None, max_length=10)
    loi_value: Decimal | None = None
    loi_date: str | None = Field(None, max_length=10)
    final_offer_value: Decimal | None = None
    rejection_reason: str | None = None
    notes: str | None = None
    extra_data: dict | None = None


class BuyerPipelineSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    by_tier: dict[str, int] = Field(default_factory=dict)
    avg_ioi_value: Decimal | None = None
    avg_loi_value: Decimal | None = None
