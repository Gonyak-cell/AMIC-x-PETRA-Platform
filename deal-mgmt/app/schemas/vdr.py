"""VDR (Virtual Data Room) Pydantic 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import VdrDocumentStatus, VdrFolderCategory


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
