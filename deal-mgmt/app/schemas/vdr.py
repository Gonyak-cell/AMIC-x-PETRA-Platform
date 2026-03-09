"""VDR (Virtual Data Room) Pydantic 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import VdrClassificationStatus, VdrDocumentStatus, VdrFolderCategory

# ── 폴더 스키마 ───────────────────────────────────────────


class VdrFolderCreate(BaseModel):
    """VDR 폴더 생성 요청."""

    name: str = Field(..., min_length=1, max_length=255)
    category: VdrFolderCategory = VdrFolderCategory.CUSTOM
    parent_id: uuid.UUID | None = None
    description: str | None = Field(None, max_length=500)


class VdrFolderUpdate(BaseModel):
    """VDR 폴더 수정 요청 (부분 업데이트)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    order_index: int | None = None
    description: str | None = Field(None, max_length=500)


class VdrFolderOut(BaseModel):
    """VDR 폴더 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    category: VdrFolderCategory
    order_index: int
    is_required: bool
    description: str | None
    created_at: datetime
    updated_at: datetime


class VdrFolderTreeOut(VdrFolderOut):
    """트리 구조 응답 — 하위 폴더 + 문서 수 포함."""

    children: list[VdrFolderTreeOut] = []
    document_count: int = 0


class VdrInitRequest(BaseModel):
    """VDR 기본 폴더 구조 초기화 요청."""

    include_custom_folders: bool = False


# ── 문서 스키마 ───────────────────────────────────────────


class VdrDocumentOut(BaseModel):
    """VDR 문서(파일) 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    folder_id: uuid.UUID
    original_name: str
    file_size_bytes: int
    mime_type: str
    sha256_hash: str | None
    status: VdrDocumentStatus
    description: str | None
    uploaded_by_email: str | None
    classification_status: VdrClassificationStatus | None = None
    classification_score: int | None = None
    manual_review_needed: bool = False
    created_at: datetime
    updated_at: datetime


class VdrDocumentUpdate(BaseModel):
    """VDR 문서 수정 (설명, 폴더 이동)."""

    description: str | None = None
    folder_id: uuid.UUID | None = None


class VdrSummaryOut(BaseModel):
    """VDR 요약 통계."""

    total_folders: int = 0
    total_documents: int = 0
    total_size_bytes: int = 0
    initialized: bool = False


class VdrOverviewItem(BaseModel):
    """거래별 VDR 현황 — Overview 페이지용."""

    transaction_id: uuid.UUID
    transaction_name: str
    code_name: str
    phase: str
    status: str
    vdr_initialized: bool
    total_folders: int
    total_documents: int
    total_size_bytes: int
    last_upload_at: datetime | None


class VdrAutoUploadResult(BaseModel):
    """자동 라우팅 업로드 결과."""

    model_config = ConfigDict(from_attributes=True)

    document: VdrDocumentOut
    routed_folder: VdrFolderOut
    routed_category: VdrFolderCategory | None
    was_fallback: bool
    original_name_renamed: bool
    final_name: str


# ── Direct Upload 스키마 ──────────────────────────────────


class SuggestCategoryRequest(BaseModel):
    """파일명 기반 카테고리 추천 요청."""

    filename: str = Field(..., min_length=1, max_length=500)


class SuggestCategoryResponse(BaseModel):
    """파일명 기반 카테고리 추천 응답."""

    category: str | None = None
    folder_name: str | None = None


class FailedFileInfo(BaseModel):
    """Direct Upload 실패 파일 정보."""

    filename: str
    reason: str


class DirectUploadFileResult(BaseModel):
    """Direct Upload 개별 파일 분류 결과."""

    document: VdrDocumentOut
    routed_folder: VdrFolderOut
    routed_category: VdrFolderCategory | None
    classification_status: VdrClassificationStatus
    score: int
    was_fallback: bool


class DirectUploadBatchResult(BaseModel):
    """Direct Upload 다중 파일 배치 결과."""

    results: list[DirectUploadFileResult]
    pending_review_count: int
    total_uploaded: int
    failed_files: list[FailedFileInfo] = []


class ClassificationStatusOut(BaseModel):
    """2차 심사 상태 조회 응답."""

    document_id: uuid.UUID
    classification_status: VdrClassificationStatus
    routed_folder: VdrFolderOut | None = None
    routed_category: VdrFolderCategory | None = None
    manual_review_needed: bool


# ── Q&A 스키마 ────────────────────────────────────────────


class VdrQARequest(BaseModel):
    """VDR Q&A 질문 요청."""

    question: str = Field(..., min_length=1, max_length=2000)
    document_ids: list[uuid.UUID] | None = Field(None, description="참조할 문서 ID 리스트 (빈 값이면 전체 문서 대상)")
    conversation_id: str | None = Field(
        None,
        max_length=36,
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        description="대화 세션 ID (연속 질문 시 이전 conversation_id 전달)",
    )


class VdrQASourceOut(BaseModel):
    """Q&A 답변 참조 문서."""

    document_id: str
    document_name: str
    relevance: Literal["high", "medium", "low", "referenced"]  # fmt: skip


class VdrQAResponse(BaseModel):
    """VDR Q&A 답변 응답."""

    answer: str
    sources: list[VdrQASourceOut]
    conversation_id: str
    cost_usd: float | None = None
