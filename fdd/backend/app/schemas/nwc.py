"""NWC (Net Working Capital) 관련 Pydantic 스키마 — EPIC-06."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.nwc import NWCClassification, NWCStatus, PegMethod

# -- NWC Line Item -----------------------------------------------


class NWCLineItemRead(BaseModel):
    id: uuid.UUID
    nwc_calculation_id: uuid.UUID
    deal_id: uuid.UUID
    account_code: str
    account_name: str
    line_item_category: str
    classification: NWCClassification
    amount: Decimal
    monthly_amounts: dict
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NWCLineItemUpdate(BaseModel):
    """WC 항목 분류 변경 요청 — FDD-601."""

    classification: NWCClassification


# -- NWC Calculation ---------------------------------------------


class NWCRunRequest(BaseModel):
    """NWC 계산 실행 요청."""

    snapshot_id: uuid.UUID
    peg_method: PegMethod = PegMethod.LTM_AVERAGE
    custom_peg_value: Decimal | None = None


class NWCCalculationRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    snapshot_id: uuid.UUID
    total_current_assets: Decimal
    total_current_liabilities: Decimal
    net_working_capital: Decimal
    peg_method: PegMethod
    peg_target: Decimal
    peg_delta: Decimal
    monthly_trend: dict
    category_breakdown: dict
    engine_version: str
    status: NWCStatus
    line_items: list[NWCLineItemRead]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# -- NWC Peg Simulation -----------------------------------------


class PegSimulationRequest(BaseModel):
    """Peg 시나리오 시뮬레이션 요청 — FDD-603."""

    peg_method: PegMethod
    custom_value: Decimal | None = None


class PegSimulationResult(BaseModel):
    """단일 Peg 시나리오 결과."""

    method: PegMethod
    target_nwc: Decimal
    delta: Decimal
    description: str


class PegSimulationResponse(BaseModel):
    """Peg 6종 시뮬레이션 응답."""

    reference_nwc: Decimal
    scenarios: list[PegSimulationResult]


# -- NWC Summary -------------------------------------------------


class NWCSummary(BaseModel):
    """NWC 요약 (프론트엔드 표시용)."""

    net_working_capital: Decimal
    total_current_assets: Decimal
    total_current_liabilities: Decimal
    peg_method: PegMethod
    peg_target: Decimal
    peg_delta: Decimal
    above_line_items: list[NWCLineItemRead]
    below_line_items: list[NWCLineItemRead]
    is_above_target: bool
