from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

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
    is_short_listed: bool = False
    ioi_value: Decimal | None = None
    ioi_date: str | None = None
    loi_value: Decimal | None = None
    loi_date: str | None = None
    final_offer_value: Decimal | None = None
    rejection_reason: str | None = None
    notes: str | None = None
    extra_data: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("ioi_value", "loi_value", "final_offer_value")
    @classmethod
    def _serialize_decimal(cls, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class BuyerCandidateCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    contact_name: str | None = Field(None, max_length=100)
    contact_email: str | None = Field(
        None, max_length=255, pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    )
    contact_phone: str | None = Field(None, max_length=20)
    buyer_type: BuyerType
    tier: BuyerTier | None = None
    corp_code: str | None = Field(None, max_length=8)
    deal_role: DealRole | None = None
    notes: str | None = Field(None, max_length=5000)
    extra_data: dict[str, Any] | None = None

    @field_validator("extra_data")
    @classmethod
    def validate_extra_data_size(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None:
            if len(v) > 50:
                msg = "extra_data는 최대 50개 키까지 허용됩니다"
                raise ValueError(msg)
            import json

            if len(json.dumps(v, ensure_ascii=False).encode("utf-8")) > 10240:
                msg = "extra_data must be under 10KB"
                raise ValueError(msg)
        return v


class BuyerCandidateUpdate(BaseModel):
    company_name: str | None = Field(None, min_length=1, max_length=200)
    contact_name: str | None = Field(None, max_length=100)
    contact_email: str | None = Field(
        None, max_length=255, pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    )
    contact_phone: str | None = Field(None, max_length=20)
    buyer_type: BuyerType | None = None
    status: BuyerCandidateStatus | None = None
    tier: BuyerTier | None = None
    corp_code: str | None = Field(None, max_length=8)
    deal_role: DealRole | None = None
    is_short_listed: bool | None = None
    ioi_value: Decimal | None = None
    ioi_date: str | None = Field(None, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    loi_value: Decimal | None = None
    loi_date: str | None = Field(None, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    final_offer_value: Decimal | None = None
    rejection_reason: str | None = None
    notes: str | None = Field(None, max_length=5000)
    extra_data: dict[str, Any] | None = None

    @field_validator("extra_data")
    @classmethod
    def validate_extra_data_size(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None:
            if len(v) > 50:
                msg = "extra_data는 최대 50개 키까지 허용됩니다"
                raise ValueError(msg)
            import json

            if len(json.dumps(v, ensure_ascii=False).encode("utf-8")) > 10240:
                msg = "extra_data must be under 10KB"
                raise ValueError(msg)
        return v


class BuyerPipelineSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    by_tier: dict[str, int] = Field(default_factory=dict)
    avg_ioi_value: Decimal | None = None
    avg_loi_value: Decimal | None = None

    @field_serializer("avg_ioi_value", "avg_loi_value")
    @classmethod
    def _serialize_decimal(cls, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class BiddingSummary(BaseModel):
    total_bidders: int
    bid_submitted: int
    bid_not_submitted: int
    bid_dropped: int
