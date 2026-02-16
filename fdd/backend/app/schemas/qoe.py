"""QoE (Quality of Earnings) 관련 Pydantic 스키마 — EPIC-05."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.qoe import AdjustmentCategory, AdjustmentStatus, QoEStatus

# ── Adjustment Item ──────────────────────────────────────


class AdjustmentItemCreate(BaseModel):
    """수동 조정항목 추가 요청."""

    category: AdjustmentCategory
    description: str = Field(..., min_length=1, max_length=500)
    amount: Decimal
    source_account_code: str | None = None
    source_account_name: str | None = None


class AdjustmentItemUpdate(BaseModel):
    """조정항목 수정 요청."""

    category: AdjustmentCategory | None = None
    description: str | None = Field(default=None, max_length=500)
    amount: Decimal | None = None
    status: AdjustmentStatus | None = None
    rejection_reason: str | None = None


class AdjustmentItemApprove(BaseModel):
    """조정항목 승인 요청."""

    approved_by: str = Field(..., min_length=1, max_length=100)


class AdjustmentItemRead(BaseModel):
    id: uuid.UUID
    qoe_calculation_id: uuid.UUID
    deal_id: uuid.UUID
    category: AdjustmentCategory
    description: str
    amount: Decimal
    detection_method: str
    confidence_score: Decimal | None
    source_account_code: str | None
    source_account_name: str | None
    source_entry_ids: list | None
    status: AdjustmentStatus
    approved_by: str | None
    approved_at: datetime | None
    rejection_reason: str | None
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── QoE Calculation ──────────────────────────────────────


class QoERunRequest(BaseModel):
    """QoE 계산 실행 요청."""

    snapshot_id: uuid.UUID


class QoECalculationRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    snapshot_id: uuid.UUID
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    sga: Decimal
    depreciation_amortization: Decimal
    other_operating: Decimal
    operating_income: Decimal
    reported_ebitda: Decimal
    total_adjustments: Decimal
    adjusted_ebitda: Decimal
    balance_check_error: Decimal
    category_breakdown: dict
    engine_version: str
    status: QoEStatus
    adjustments: list[AdjustmentItemRead]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── QoE Bridge Summary ──────────────────────────────────


class QoEBridgeSummary(BaseModel):
    """QoE Bridge 요약 (프론트엔드 표시용)."""

    reported_ebitda: Decimal
    adjustments: list[AdjustmentItemRead]
    total_adjustments: Decimal
    adjusted_ebitda: Decimal
    balance_check_error: Decimal
    is_balanced: bool
