"""ExchangeRate (환율) Pydantic 스키마."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.exchange_rate import RateSource, RateType


class ExchangeRateCreate(BaseModel):
    from_currency: str = Field(..., max_length=10)
    to_currency: str = Field(..., max_length=10)
    rate_type: RateType
    rate: Decimal = Field(..., gt=Decimal("0"))
    effective_date: date
    period_key: str | None = Field(default=None, max_length=7)


class ExchangeRateBulkCreate(BaseModel):
    """벌크 환율 등록."""

    rates: list[ExchangeRateCreate] = Field(..., min_length=1)


class ExchangeRateUpdate(BaseModel):
    rate: Decimal | None = Field(default=None, gt=Decimal("0"))
    period_key: str | None = None


class ExchangeRateRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    from_currency: str
    to_currency: str
    rate_type: RateType
    rate: Decimal
    effective_date: date
    period_key: str | None
    source: RateSource
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}
