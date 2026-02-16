"""Net Debt 관련 Pydantic 스키마 — EPIC-07."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.debt import DebtItemStatus, DebtItemType, DebtStatus

# -- Debt Item ---------------------------------------------------


class DebtItemCreate(BaseModel):
    """수동 Debt/Cash 항목 추가 요청."""

    item_type: DebtItemType
    description: str = Field(..., min_length=1, max_length=500)
    amount: Decimal
    source_account_code: str | None = None
    source_account_name: str | None = None


class DebtItemUpdate(BaseModel):
    """Debt 항목 수정 요청."""

    item_type: DebtItemType | None = None
    description: str | None = Field(default=None, max_length=500)
    amount: Decimal | None = None
    status: DebtItemStatus | None = None
    rejection_reason: str | None = None


class DebtItemApprove(BaseModel):
    """Debt 항목 승인 요청."""

    approved_by: str = Field(..., min_length=1, max_length=100)


class DebtItemRead(BaseModel):
    id: uuid.UUID
    net_debt_calculation_id: uuid.UUID
    deal_id: uuid.UUID
    item_type: DebtItemType
    description: str
    amount: Decimal
    source_account_code: str | None
    source_account_name: str | None
    detection_method: str
    confidence_score: Decimal | None
    status: DebtItemStatus
    approved_by: str | None
    approved_at: datetime | None
    rejection_reason: str | None
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# -- Net Debt Calculation ----------------------------------------


class NetDebtRunRequest(BaseModel):
    """Net Debt 계산 실행 요청."""

    snapshot_id: uuid.UUID
    include_lease_liabilities: bool = False
    include_deferred_revenue: bool = False


class NetDebtCalculationRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    snapshot_id: uuid.UUID
    gross_debt: Decimal
    cash_and_equivalents: Decimal
    net_debt: Decimal
    debt_like_total: Decimal
    cash_like_total: Decimal
    adjusted_net_debt: Decimal
    include_lease_liabilities: bool
    include_deferred_revenue: bool
    balance_check_error: Decimal
    category_breakdown: dict
    engine_version: str
    status: DebtStatus
    items: list[DebtItemRead]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# -- Net Debt Bridge Summary ------------------------------------


class NetDebtBridgeSummary(BaseModel):
    """Net Debt Bridge 요약 (프론트엔드 표시용)."""

    gross_debt: Decimal
    cash_and_equivalents: Decimal
    net_debt: Decimal
    debt_like_items: list[DebtItemRead]
    cash_like_items: list[DebtItemRead]
    debt_like_total: Decimal
    cash_like_total: Decimal
    adjusted_net_debt: Decimal
    balance_check_error: Decimal
    is_balanced: bool
