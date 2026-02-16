import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.account_mapping import MappingConfidence, MappingStatus
from app.models.standard_line_item import FinancialStatement, LineItemCategory
from app.models.tie_out import TieOutStatus

# ── StandardLineItem ─────────────────────────────────────


class StandardLineItemRead(BaseModel):
    id: uuid.UUID
    code: str
    name_en: str
    name_ko: str
    category: LineItemCategory
    statement_type: FinancialStatement
    display_order: int
    parent_code: str | None
    is_subtotal: bool
    keywords: list[str] | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── AccountMapping ───────────────────────────────────────


class AccountMappingCreate(BaseModel):
    source_account_code: str = Field(..., min_length=1, max_length=50)
    source_account_name: str = Field(..., min_length=1, max_length=500)
    target_line_item_code: str = Field(..., min_length=1, max_length=50)
    confidence: MappingConfidence
    status: MappingStatus = MappingStatus.PROPOSED
    match_score: Decimal | None = None
    algorithm: str | None = None
    affected_amount: Decimal = Field(..., description="해당 계정 TB 잔액")


class AccountMappingUpdate(BaseModel):
    target_line_item_code: str | None = Field(default=None, max_length=50)
    status: MappingStatus | None = None
    rejection_reason: str | None = None


class AccountMappingApprove(BaseModel):
    approved_by: str = Field(..., min_length=1, max_length=100)


class AccountMappingRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    source_account_code: str
    source_account_name: str
    target_line_item_code: str
    confidence: MappingConfidence
    status: MappingStatus
    match_score: Decimal | None
    algorithm: str | None
    affected_amount: Decimal
    approved_by: str | None
    approved_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MappingBulkCreate(BaseModel):
    """매핑 일괄 저장 요청."""

    mappings: list[AccountMappingCreate] = Field(..., min_length=1)


# ── MappingSuggestion (매핑 제안 결과 DTO) ────────────────


class MappingSuggestion(BaseModel):
    """매핑 엔진이 반환하는 제안 결과 (DB 저장 전)."""

    source_account_code: str
    source_account_name: str
    suggested_target_code: str
    suggested_target_name_en: str
    suggested_target_name_ko: str
    confidence: MappingConfidence
    match_score: Decimal
    algorithm: str
    affected_amount: Decimal


# ── TieOutResult ─────────────────────────────────────────


class TieOutResultRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    snapshot_id: uuid.UUID
    statement_type: FinancialStatement
    status: TieOutStatus
    tb_total: Decimal
    reconstructed_total: Decimal
    variance: Decimal
    variance_percentage: Decimal
    unmapped_account_count: int
    unmapped_total: Decimal
    top_discrepancies: list[dict] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TieOutRun(BaseModel):
    """Tie-out 실행 요청."""

    snapshot_id: uuid.UUID
