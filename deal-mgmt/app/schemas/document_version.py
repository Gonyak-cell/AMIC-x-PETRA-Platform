"""문서 버전 관리 스키마 — DocumentMaster + DocumentRevision."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ── DocumentMaster ──────────────────────────────────────


class DocumentMasterCreate(BaseModel):
    doc_type: str = Field(..., description="DocumentType enum 값")
    doc_name: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    contract_id: uuid.UUID | None = None
    nda_id: uuid.UUID | None = None


class DocumentMasterUpdate(BaseModel):
    doc_name: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    is_archived: bool | None = None


class DocumentMasterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    doc_type: str
    doc_name: str
    description: str | None = None
    current_revision_number: int
    is_archived: bool
    contract_id: uuid.UUID | None = None
    nda_id: uuid.UUID | None = None
    created_by_email: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentMasterListResponse(BaseModel):
    items: list[DocumentMasterOut]
    total: int


# ── DocumentRevision ────────────────────────────────────


class DocumentRevisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    revision_number: int
    sha256_hash: str
    file_name: str
    file_size_bytes: int
    mime_type: str | None = None
    uploaded_by_email: str | None = None
    upload_source: str
    changes_summary: str | None = None
    prev_revision_id: uuid.UUID | None = None
    is_current: bool
    is_deleted: bool
    source_entity_type: str | None = None
    source_entity_id: str | None = None
    created_at: datetime
    updated_at: datetime


class RevisionListResponse(BaseModel):
    items: list[DocumentRevisionOut]
    total: int
