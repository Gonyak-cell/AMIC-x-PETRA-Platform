"""PEF 펀드 레지스트리 스키마."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer


class PefFundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pef_name: str
    legal_basis: str | None = None
    registration_date: str | None = None
    gp1: str | None = None
    gp2: str | None = None
    gp3: str | None = None
    total_committed_capital: Decimal | None = None

    @field_serializer("total_committed_capital")
    @classmethod
    def _serialize_capital(cls, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class PefCountOut(BaseModel):
    total: int


class FIRecommendation(BaseModel):
    gp_name: str
    min_fund_size: Decimal
    matching_funds: list[PefFundOut]
    total_committed_sum: Decimal
    fund_count: int
    match_reason: str

    @field_serializer("min_fund_size", "total_committed_sum")
    @classmethod
    def _serialize_decimal(cls, v: Decimal) -> str:
        return str(v)
