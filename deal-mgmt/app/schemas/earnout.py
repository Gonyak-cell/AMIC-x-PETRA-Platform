from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.enums import EarnoutMetric, EarnoutStatus


class EarnoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    title: str
    description: str | None = None
    metric: EarnoutMetric
    target_value: Decimal
    actual_value: Decimal | None = None
    currency: str
    measurement_start: str | None = None
    measurement_end: str | None = None
    payment_amount: Decimal | None = None
    payment_date: str | None = None
    status: EarnoutStatus
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("target_value", "actual_value", "payment_amount")
    @classmethod
    def _serialize_decimal(cls, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class EarnoutCreate(BaseModel):
    title: str = Field(..., max_length=300)
    description: str | None = None
    metric: EarnoutMetric
    target_value: Decimal = Field(..., ge=0)
    currency: str = Field("KRW", max_length=10)
    measurement_start: str | None = Field(None, max_length=10)
    measurement_end: str | None = Field(None, max_length=10)
    payment_amount: Decimal | None = Field(None, ge=0)
    notes: str | None = None


class EarnoutUpdate(BaseModel):
    title: str | None = Field(None, max_length=300)
    description: str | None = None
    metric: EarnoutMetric | None = None
    target_value: Decimal | None = Field(None, ge=0)
    actual_value: Decimal | None = Field(None, ge=0)
    currency: str | None = Field(None, max_length=10)
    measurement_start: str | None = Field(None, max_length=10)
    measurement_end: str | None = Field(None, max_length=10)
    payment_amount: Decimal | None = Field(None, ge=0)
    payment_date: str | None = Field(None, max_length=10)
    status: EarnoutStatus | None = None
    notes: str | None = None


class EarnoutSummary(BaseModel):
    total: int
    total_target: Decimal
    total_actual: Decimal
    total_payment: Decimal
    by_status: dict[str, int]

    @field_serializer("total_target", "total_actual", "total_payment")
    @classmethod
    def _serialize_decimal(cls, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None
