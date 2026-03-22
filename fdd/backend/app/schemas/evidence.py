import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.evidence import SourceType

# ── EvidenceLink ─────────────────────────────────────────


class EvidenceLinkCreate(BaseModel):
    target_type: str = Field(
        ..., min_length=1, max_length=100, description="산출물 유형"
    )
    target_id: uuid.UUID = Field(..., description="산출물 레코드 PK")
    source_type: SourceType = Field(..., description="원본 유형")
    source_id: str = Field(..., min_length=1, max_length=255, description="원본 식별자")
    source_detail: dict[str, Any] | None = Field(
        default=None, description="세부 위치 (sheet, page, row 등)"
    )
    transaction_id: str | None = Field(default=None, max_length=255)
    filter_hash: str | None = Field(default=None, max_length=64)
    engine_version: str | None = Field(default=None, max_length=20)
    snapshot_id: uuid.UUID | None = Field(default=None, description="스냅샷 ID")


class EvidenceLinkRead(BaseModel):
    id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    source_type: SourceType
    source_id: str
    source_detail: dict[str, Any] | None
    transaction_id: str | None
    filter_hash: str | None
    engine_version: str | None
    deal_id: uuid.UUID
    snapshot_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceLinkBulkCreate(BaseModel):
    """엔진 함수가 반환하는 EvidenceLink 목록을 한 번에 저장."""

    links: list[EvidenceLinkCreate] = Field(..., min_length=1)


class EvidenceExportRecord(BaseModel):
    workstream: str = "FDD"
    section_type: str | None = None
    item_id: str | None = None
    vdr_document_id: uuid.UUID | None = None
    reference_label: str
    original_name: str | None = None
    primary_workstream: str | None = "FDD"
    workstream_tags: list[str] = Field(default_factory=lambda: ["FDD"])
    evidence_kind: str | None = None
    directness: str | None = None
    confidence: float = 1.0
    relevance_score: float = 1.0
    source_page: str | None = None
    source_snippet: str | None = None
    evidence_locator: dict[str, Any] | None = None
    requires_manual_review: bool = False
    is_foreign_workstream: bool = False
    is_unresolved_reference: bool = False
    used_in_draft: bool = True
    used_in_final: bool = False
    analysis_phase: str = "DRAFT"
    ordinal: int = 0
    chunk_id: str | None = None


class EvidenceExportResponse(BaseModel):
    artifact_type: str = "FDD_REPORT"
    artifact_id: uuid.UUID | None = None
    external_artifact_ref: str | None = None
    default_workstream: str = "FDD"
    records: list[EvidenceExportRecord] = Field(default_factory=list)
