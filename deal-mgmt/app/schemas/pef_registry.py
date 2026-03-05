"""PEF 펀드 레지스트리 스키마."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

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


class GpProfileOut(BaseModel):
    """GP 프로필 요약 (FI 추천 응답에 포함)."""

    model_config = ConfigDict(from_attributes=True)

    raw_name: str
    min_threshold: Decimal | None = None
    portfolio_sectors: list[str] | None = None
    portfolio_companies: list[str] | None = None
    recent_pef_count: int | None = None
    total_pef_count: int | None = None

    @field_serializer("min_threshold")
    @classmethod
    def _serialize_threshold(cls, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class GpProfileListItemOut(BaseModel):
    """GP 프로필 목록 항목 — KIIS GP Research 연결용."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    raw_name: str
    logo_url: str | None = None
    total_committed_sum: Decimal | None = None
    recent_pef_count: int | None = None
    total_pef_count: int | None = None
    portfolio_sectors: list[str] | None = None
    portfolio_companies: list[str] | None = None
    yearly_pef_counts: dict[str, int] | None = None

    @field_serializer("total_committed_sum")
    @classmethod
    def _serialize_sum(cls, v: Decimal | None) -> float | None:
        return float(v) if v is not None else None


class FIRecommendationV2(BaseModel):
    """GP 프로필 기반 Tier 분류가 포함된 FI 추천."""

    gp_name: str
    gp_profile: GpProfileOut | None = None
    tier: Literal[1, 2]  # 1 = 최소기준점 + 키워드, 2 = 최소기준점만 or 프로필 없음
    min_fund_size: Decimal
    matching_funds: list[PefFundOut]
    total_committed_sum: Decimal
    fund_count: int
    match_reason: str

    @field_serializer("min_fund_size", "total_committed_sum")
    @classmethod
    def _serialize_decimal(cls, v: Decimal) -> float:
        return float(v)
