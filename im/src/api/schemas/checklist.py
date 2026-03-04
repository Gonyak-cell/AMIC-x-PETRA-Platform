"""체크리스트 Pydantic 스키마.

체크리스트 조회/수정 API의 요청/응답 스키마를 정의한다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# 아이템 스키마
# ---------------------------------------------------------------------------


class ChecklistItemResponse(BaseModel):
    """체크리스트 아이템 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    checklist_id: UUID
    category: str
    field_key: str
    field_label: str
    field_type: str
    extracted_value: str | None
    confirmed_value: str | None
    unit: str | None
    source_vdr_doc_id: UUID | None
    source_vdr_doc_name: str | None
    source_location: str | None
    status: str
    confidence: float | None
    sort_order: int
    notes: str | None
    is_required: bool
    fiscal_year: int | None
    created_at: datetime
    updated_at: datetime


class ChecklistItemUpdate(BaseModel):
    """체크리스트 아이템 수정 요청."""

    confirmed_value: str | None = None
    status: str | None = Field(
        default=None,
        description="EXTRACTED | CONFIRMED | MODIFIED | MISSING | NOT_APPLICABLE",
    )
    notes: str | None = None


class ChecklistItemBatchUpdate(BaseModel):
    """일괄 수정 요청의 개별 항목."""

    item_id: UUID
    confirmed_value: str | None = None
    status: str | None = None
    notes: str | None = None


class ChecklistBatchUpdateRequest(BaseModel):
    """체크리스트 아이템 일괄 수정 요청."""

    items: list[ChecklistItemBatchUpdate] = Field(
        min_length=1,
        max_length=200,
    )


# ---------------------------------------------------------------------------
# 체크리스트 스키마
# ---------------------------------------------------------------------------


class ChecklistResponse(BaseModel):
    """체크리스트 전체 응답 (아이템 포함)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    transaction_id: UUID | None
    vdr_document_ids: list[str]
    status: str
    total_items: int
    confirmed_items: int
    missing_items: int
    extraction_task_id: str | None
    generation_task_id: str | None
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None
    items: list[ChecklistItemResponse]


class ChecklistSummaryResponse(BaseModel):
    """카테고리별 완료율 요약."""

    status: str
    total_items: int
    confirmed_items: int
    missing_items: int
    completion_pct: float = Field(description="전체 확인율 (%)")
    categories: list[CategorySummary]


class CategorySummary(BaseModel):
    """개별 카테고리 요약."""

    category: str
    total: int
    confirmed: int
    missing: int
    completion_pct: float


# Pydantic v2: forward reference 해결
ChecklistSummaryResponse.model_rebuild()


# ---------------------------------------------------------------------------
# VDR 기반 생성 요청
# ---------------------------------------------------------------------------


_VALID_IM_STYLES = {"TITAN", "COVENANT", "FULL", "TEASER", "DM", "CUSTOM"}


class CreateFromVdrRequest(BaseModel):
    """VDR 기반 IM 생성 시작 요청."""

    transaction_id: UUID = Field(description="deal-mgmt 거래 ID")
    vdr_document_ids: list[UUID] = Field(
        min_length=1,
        max_length=50,
        description="분석할 VDR 문서 ID 목록",
    )
    company_name: str = Field(min_length=1, max_length=200)
    project_name: str = Field(min_length=1, max_length=200)
    im_style: str = Field(default="FULL")
    industry: str = Field(default="general", max_length=50)

    @field_validator("im_style")
    @classmethod
    def _validate_im_style(cls, v: str) -> str:
        if v not in _VALID_IM_STYLES:
            raise ValueError(f"im_style은 {_VALID_IM_STYLES} 중 하나여야 합니다")
        return v


class CreateFromVdrResponse(BaseModel):
    """VDR 기반 IM 생성 시작 응답."""

    document_id: UUID
    checklist_id: UUID
    status: str = "EXTRACTING"
    extraction_task_id: str | None
    message: str = "VDR 문서 분석이 시작되었습니다."
