"""RFI V2 Pydantic 스키마 — 질의 원장 + 스레드 이력 기반."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import RFIAuthorRole, RFICategoryV2, RFIItemStatusV2, RFIPriority

# ── Thread ────────────────────────────────────────────────


class RFIThreadCreate(BaseModel):
    content_text: str = Field(..., min_length=1, max_length=10000)
    is_published: bool = True


class RFIThreadUpdate(BaseModel):
    is_published: bool


class RFIThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_id: uuid.UUID
    round_num: int
    author_email: str
    author_role: RFIAuthorRole
    content_text: str
    is_published: bool
    created_at: datetime


# ── Attachment ────────────────────────────────────────────


class RFIAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    thread_id: uuid.UUID | None
    item_id: uuid.UUID | None
    transaction_id: uuid.UUID
    vdr_index: str | None
    file_name: str
    file_url: str
    is_mapped: bool
    created_at: datetime


class RFIAttachmentMapInput(BaseModel):
    item_id: uuid.UUID | None = None
    thread_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def require_at_least_one(self) -> RFIAttachmentMapInput:
        if self.item_id is None and self.thread_id is None:
            raise ValueError("item_id 또는 thread_id 중 하나는 필수입니다")
        return self


# ── RFI Item ──────────────────────────────────────────────


class RFIItemCreateV2(BaseModel):
    category: RFICategoryV2
    question_text: str = Field(..., min_length=1, max_length=5000)
    priority: RFIPriority = RFIPriority.MEDIUM
    target_doc: str | None = Field(None, max_length=100)
    assignee_email: str | None = Field(None, max_length=255)
    due_date: str | None = Field(None, max_length=10)
    internal_memo: str | None = Field(None, max_length=5000)
    report_section_tag: str | None = Field(None, max_length=100)


class RFIItemUpdateV2(BaseModel):
    category: RFICategoryV2 | None = None
    question_text: str | None = Field(None, min_length=1, max_length=5000)
    priority: RFIPriority | None = None
    target_doc: str | None = Field(None, max_length=100)
    assignee_email: str | None = Field(None, max_length=255)
    due_date: str | None = Field(None, max_length=10)
    internal_memo: str | None = Field(None, max_length=5000)
    report_section_tag: str | None = Field(None, max_length=100)
    current_status: RFIItemStatusV2 | None = None
    version: int = Field(..., description="낙관적 락 — DB 버전과 일치해야 수정 가능")


class RFIItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    item_number: str
    category: RFICategoryV2
    priority: RFIPriority
    target_doc: str | None
    question_text: str
    current_status: RFIItemStatusV2
    internal_memo: str | None = None
    report_section_tag: str | None
    assignee_email: str | None
    due_date: str | None
    created_by_email: str | None
    version: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime | None
    threads: list[RFIThreadOut] = []
    attachments: list[RFIAttachmentOut] = []


class RFIItemListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    item_number: str
    category: RFICategoryV2
    priority: RFIPriority
    target_doc: str | None
    question_text: str
    current_status: RFIItemStatusV2
    report_section_tag: str | None
    assignee_email: str | None
    due_date: str | None
    version: int
    created_at: datetime
    updated_at: datetime | None
    thread_count: int = 0
    attachment_count: int = 0


class RFIItemListResponse(BaseModel):
    items: list[RFIItemListOut]
    total: int
    limit: int
    offset: int


# ── Dashboard ─────────────────────────────────────────────


class RFICategoryBreakdown(BaseModel):
    category: str
    total: int
    open: int
    answered: int
    closed: int
    clarification_needed: int
    response_pct: float


class RFIDashboardSummary(BaseModel):
    total_items: int
    status_counts: dict[str, int]
    category_breakdown: list[RFICategoryBreakdown]
    aging_items: list[RFIItemListOut]


# ── Excel ─────────────────────────────────────────────────


class RFIExcelImportResult(BaseModel):
    items_updated: int
    threads_created: int
    files_matched: int
    files_unmatched: int
    errors: list[dict[str, str | int]]
    conflicts: list[dict[str, str | int]]


# ── Report Bridge ─────────────────────────────────────────


class RFIVerifiedFact(BaseModel):
    original_question: str
    target_company_answers: list[str]
    referenced_vdr_files: list[str]


class RFIReportPayload(BaseModel):
    report_section: str
    verified_facts: list[RFIVerifiedFact]


# ── Batch Create ──────────────────────────────────────────


class RFIItemBatchCreate(BaseModel):
    items: list[RFIItemCreateV2] = Field(..., min_length=1)


# ── AI Generate ──────────────────────────────────────────


class RFIAutoGenerateRequest(BaseModel):
    """AI 초기 RFI 생성 요청."""

    industry: str = Field(..., min_length=1, max_length=200, description="산업군 (예: 제조업, IT, 헬스케어)")
    deal_purpose: str = Field(
        ..., min_length=1, max_length=500, description="거래 목적 (예: 경영권 인수, 소수 지분 투자)"
    )
    focus_areas: list[str] = Field(
        default_factory=list, max_length=20, description="중점 분석 영역 (예: 재무, 법률, 노무)"
    )
    additional_context: str = Field(default="", max_length=2000, description="추가 컨텍스트")

    @model_validator(mode="after")
    def validate_focus_area_lengths(self) -> RFIAutoGenerateRequest:
        for i, area in enumerate(self.focus_areas):
            if len(area) > 100:
                raise ValueError(f"focus_areas[{i}]는 100자 이내여야 합니다")
        return self


class RFIAutoGenerateResult(BaseModel):
    """AI 초기 RFI 생성 결과."""

    items_created: int
    cost_usd: float
    model_used: str
