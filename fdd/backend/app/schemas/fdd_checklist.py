"""FDD 체크리스트 Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.fdd_checklist import (
    ChecklistCategory,
    ChecklistItemStatus,
    ChecklistSeverity,
    ChecklistStatus,
)


# ── Request Schemas ──────────────────────────────────────────────────────


class ChecklistItemUpdate(BaseModel):
    """사용자가 체크리스트 항목을 리뷰/수정할 때."""

    status: ChecklistItemStatus
    user_correction: str | None = None
    user_amount: Decimal | None = None


class ChecklistBulkItem(BaseModel):
    item_id: UUID
    status: ChecklistItemStatus
    user_correction: str | None = None
    user_amount: Decimal | None = None


class ChecklistBulkUpdate(BaseModel):
    """여러 항목을 한번에 업데이트."""

    items: list[ChecklistBulkItem]


class ChecklistFinalizeRequest(BaseModel):
    notes: str | None = None


class AnalysisRunCreate(BaseModel):
    """수동 분석 실행 요청."""

    file_ids: list[UUID] | None = Field(
        default=None,
        description="분석할 파일 ID 목록. None이면 VDR의 모든 COMPLETED 파일 사용.",
    )
    cross_verify_enabled: bool = Field(
        default=False,
        description="교차검증 활성화. True이면 LLM 에이전트 결과를 다른 프로바이더로 검증.",
    )


# ── Response Schemas ─────────────────────────────────────────────────────


class VdrLinkRead(BaseModel):
    id: UUID
    upload_file_id: UUID | None = None
    vdr_folder_id: UUID | None = None
    evidence_link_id: UUID | None = None
    source_detail: dict | None = None
    description: str | None = None
    upload_filename: str | None = None
    folder_name: str | None = None

    model_config = {"from_attributes": True}


class ChecklistItemRead(BaseModel):
    id: UUID
    category: ChecklistCategory
    order_index: int
    title: str
    description: str
    auto_finding: str | None = None
    auto_amount: str | None = None  # Decimal → str for JSON
    user_correction: str | None = None
    user_amount: str | None = None
    status: ChecklistItemStatus
    severity: ChecklistSeverity | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    vdr_links: list[VdrLinkRead] = Field(default_factory=list)
    metadata: dict | None = None

    model_config = {"from_attributes": True}


class ChecklistRead(BaseModel):
    id: UUID
    deal_id: UUID
    version: int
    status: ChecklistStatus
    items: list[ChecklistItemRead] = Field(default_factory=list)
    notes: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    finalized_at: datetime | None = None

    # 요약 통계
    total_items: int = 0
    confirmed_count: int = 0
    corrected_count: int = 0
    flagged_count: int = 0
    pending_count: int = 0

    model_config = {"from_attributes": True}


class AnalysisRunRead(BaseModel):
    id: UUID
    deal_id: UUID
    trigger: str
    status: str
    input_file_ids: list[str] | None = None
    output_checklist_id: UUID | None = None
    progress_percent: int = 0
    error_message: str | None = None
    cross_verify_summary: dict | None = None
    qa_result: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
