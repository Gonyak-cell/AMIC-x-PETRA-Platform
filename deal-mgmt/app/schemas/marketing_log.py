"""마케팅 활동 로그 스키마 — Short-List 6단계 추적."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MarketingStage


class MarketingLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    buyer_id: uuid.UUID
    transaction_id: uuid.UUID
    stage: MarketingStage
    log_date: str
    content: str | None = None
    created_by_email: str | None = None
    created_at: datetime
    updated_at: datetime


class MarketingLogCreate(BaseModel):
    stage: MarketingStage
    log_date: str = Field(..., max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    content: str | None = Field(None, max_length=2000)


class MarketingLogUpdate(BaseModel):
    stage: MarketingStage | None = None
    log_date: str | None = Field(None, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    content: str | None = Field(None, max_length=2000)


class BuyerStageSummary(BaseModel):
    """매수자별 6단계 마케팅 완료 현황."""

    buyer_id: uuid.UUID
    stages: dict[str, str | None]  # stage -> latest log_date (null if not started)


class DartFinancialSummaryOut(BaseModel):
    """DART 재무 요약 응답 스키마."""

    revenue: Decimal | None = None
    operating_profit: Decimal | None = None
    net_income: Decimal | None = None
    debt_ratio: Decimal | None = None
    fiscal_year: str | None = None
