"""PEF 펀드 레지스트리 스키마."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


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


class FIRecommendation(BaseModel):
    gp_name: str
    matching_funds: list[PefFundOut]
    total_committed_sum: Decimal
    fund_count: int
