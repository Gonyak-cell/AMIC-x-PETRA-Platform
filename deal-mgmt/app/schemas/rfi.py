"""RFI Pydantic 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.legal_document import DateStr
from app.models.enums import (
    RFICategory,
    RFIItemPriority,
    RFIItemStatus,
    RFISourceType,
    RFIStatus,
)


# ── RFI ────────────────────────────────────────────────────


class RFICreate(BaseModel):
    round_number: int = 1
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    recipient_name: str | None = Field(None, max_length=200)
    recipient_email: str | None = Field(None, max_length=255)
    recipient_company: str | None = Field(None, max_length=200)
    due_date: DateStr | None = Field(None)
    notes: str | None = None


class RFIUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    recipient_name: str | None = Field(None, max_length=200)
    recipient_email: str | None = Field(None, max_length=255)
    recipient_company: str | None = Field(None, max_length=200)
    due_date: DateStr | None = Field(None)
    notes: str | None = None


class RFIOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    round_number: int
    title: str
    description: str | None = None
    status: RFIStatus
    recipient_name: str | None = None
    recipient_email: str | None = None
    recipient_company: str | None = None
    due_date: str | None = None
    sent_at: datetime | None = None
    closed_at: datetime | None = None
    total_items: int
    responded_items: int
    accepted_items: int
    created_by_email: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class RFIDetailOut(RFIOut):
    """RFI 상세 — items 포함."""

    items: list[RFIItemOut] = []


# ── RFI Item ───────────────────────────────────────────────


class RFIItemCreate(BaseModel):
    category: RFICategory
    question: str = Field(..., min_length=1)
    question_detail: str | None = None
    priority: RFIItemPriority = RFIItemPriority.MEDIUM
    assignee_email: str | None = Field(None, max_length=255)
    due_date: DateStr | None = Field(None)
    source_type: RFISourceType = RFISourceType.MANUAL
    source_ref_id: uuid.UUID | None = None
    source_ref_key: str | None = Field(None, max_length=100)
    notes: str | None = None


class RFIItemBatchCreate(BaseModel):
    items: list[RFIItemCreate]


class RFIItemUpdate(BaseModel):
    category: RFICategory | None = None
    question: str | None = Field(None, min_length=1)
    question_detail: str | None = None
    priority: RFIItemPriority | None = None
    assignee_email: str | None = Field(None, max_length=255)
    due_date: DateStr | None = Field(None)
    notes: str | None = None


class RFIItemRespondInput(BaseModel):
    response: str = Field(..., min_length=1)
    response_documents: list[dict] | None = None


class RFIItemReviewInput(BaseModel):
    status: Literal["ACCEPTED", "CLARIFICATION_NEEDED"]
    reviewer_comment: str | None = None
    follow_up_question: str | None = None


class RFIChecklistMappingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfi_item_id: uuid.UUID
    target_module: str
    target_checklist_id: uuid.UUID | None = None
    target_item_id: uuid.UUID | None = None
    target_field_key: str | None = None
    synced: bool
    synced_at: datetime | None = None
    synced_value: str | None = None


class RFIItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfi_id: uuid.UUID
    transaction_id: uuid.UUID
    question_number: int
    category: RFICategory
    question: str
    question_detail: str | None = None
    priority: RFIItemPriority
    response: str | None = None
    response_documents: list[dict] | None = None
    responded_at: datetime | None = None
    responded_by: str | None = None
    reviewer_comment: str | None = None
    reviewer_email: str | None = None
    status: RFIItemStatus
    assignee_email: str | None = None
    due_date: str | None = None
    source_type: RFISourceType
    source_ref_id: uuid.UUID | None = None
    source_ref_key: str | None = None
    vdr_document_ids: list[str] | None = None
    notes: str | None = None
    follow_up_question: str | None = None
    checklist_mappings: list[RFIChecklistMappingOut] = []
    created_at: datetime
    updated_at: datetime


# Forward ref 해결
RFIDetailOut.model_rebuild()


# ── Summary ────────────────────────────────────────────────


class RFICategorySummary(BaseModel):
    category: RFICategory
    total: int
    responded: int
    accepted: int
    pending: int


class RFISummary(BaseModel):
    total_rfis: int
    total_items: int
    responded_items: int
    accepted_items: int
    overall_response_pct: float
    overdue_items: int
    by_category: list[RFICategorySummary]


# ── 자동 생성 ──────────────────────────────────────────────


class RFIAutoGenerateFromDDRequest(BaseModel):
    """DD 미완료 항목에서 RFI 자동 생성."""

    title: str = Field("DD 체크리스트 기반 RFI", max_length=300)


class RFIAutoGenerateResult(BaseModel):
    rfi_id: uuid.UUID
    items_created: int


# ── Excel ──────────────────────────────────────────────────


class RFIExcelImportResult(BaseModel):
    items_imported: int
    items_updated: int
    errors: list[str]


# ── 마감일 연장 ────────────────────────────────────────────


class RFIExtendDeadlineInput(BaseModel):
    due_date: DateStr = Field(...)
