"""재무모델 + 체크리스트 Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import (
    FinancialModelStatus,
    FinancialModelType,
    FMChecklistCategory,
    FMChecklistItemStatus,
    FMChecklistSeverity,
    FMChecklistStatus,
)

# ── FinancialModel ────────────────────────────────────────────────────────


class FinancialModelCreate(BaseModel):
    model_type: FinancialModelType
    title: str = Field(..., min_length=1, max_length=300)
    vdr_document_ids: list[str] = Field(default_factory=list)
    parameters: dict | None = None
    enable_ralph_loop: bool = Field(False)
    ralph_max_iterations: int = Field(2, ge=1, le=5)
    ralph_max_cost_usd: float = Field(15.0, ge=1.0, le=50.0)


class FinancialModelOut(BaseModel):
    id: UUID
    transaction_id: UUID
    model_type: FinancialModelType
    title: str
    version: int
    status: FinancialModelStatus
    error_message: str | None
    parameters: dict | None
    vdr_document_ids: list | None
    file_path: str | None
    file_name: str | None
    file_size_bytes: int | None
    ralph_session_id: UUID | None
    ralph_score: float | None
    created_by_email: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── FMChecklist ───────────────────────────────────────────────────────────


class FMChecklistItemOut(BaseModel):
    id: UUID
    checklist_id: UUID
    category: FMChecklistCategory
    order_index: int
    title: str
    description: str
    auto_finding: str | None
    auto_value: str | None
    user_correction: str | None
    user_value: str | None
    status: FMChecklistItemStatus
    severity: FMChecklistSeverity | None
    unit: str | None
    field_type: str | None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    source_vdr_doc_id: UUID | None
    source_vdr_doc_name: str | None
    source_location: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    extra_metadata: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FMChecklistOut(BaseModel):
    id: UUID
    financial_model_id: UUID
    version: int
    status: FMChecklistStatus
    notes: str | None
    finalized_at: datetime | None
    finalized_by: str | None
    created_at: datetime
    updated_at: datetime
    items: list[FMChecklistItemOut] = []

    # 요약 통계 (서비스에서 계산하여 주입)
    total_items: int = 0
    confirmed_count: int = 0
    corrected_count: int = 0
    flagged_count: int = 0
    pending_count: int = 0
    not_applicable_count: int = 0

    model_config = {"from_attributes": True}


class FMChecklistItemUpdate(BaseModel):
    status: FMChecklistItemStatus
    user_correction: str | None = None
    user_value: str | None = None


class FMChecklistBulkItem(BaseModel):
    item_id: UUID
    status: FMChecklistItemStatus
    user_correction: str | None = None
    user_value: str | None = None


class FMChecklistBulkUpdate(BaseModel):
    items: list[FMChecklistBulkItem]


class FMChecklistFinalizeRequest(BaseModel):
    notes: str | None = None
