"""Schemas for platform-wide evidence traceability APIs."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ArtifactEvidenceRecordOut(BaseModel):
    id: UUID
    artifact_type: str
    artifact_id: UUID
    workstream: str
    section_type: str | None = None
    item_id: str | None = None
    vdr_document_id: UUID | None = None
    document_chunk_id: UUID | None = None
    reference_label: str
    original_name: str | None = None
    primary_workstream: str | None = None
    workstream_tags: list[str] = Field(default_factory=list)
    evidence_kind: str | None = None
    directness: str | None = None
    confidence: float = 0.0
    relevance_score: float = 0.0
    source_page: str | None = None
    source_snippet: str | None = None
    evidence_locator: dict | None = None
    requires_manual_review: bool = False
    is_foreign_workstream: bool = False
    is_unresolved_reference: bool = False
    used_in_draft: bool = False
    used_in_final: bool = False
    analysis_phase: str = "DRAFT"
    ordinal: int = 0


class ArtifactEvidenceSummaryOut(BaseModel):
    total_records: int = 0
    direct_count: int = 0
    indirect_count: int = 0
    manual_review_count: int = 0
    foreign_count: int = 0
    unresolved_count: int = 0
    draft_count: int = 0
    final_count: int = 0
    by_workstream: dict[str, int] = Field(default_factory=dict)
    by_phase: dict[str, int] = Field(default_factory=dict)


class ArtifactEvidenceOut(BaseModel):
    artifact_type: str
    artifact_id: UUID
    used_legacy_fallback: bool = False
    summary: ArtifactEvidenceSummaryOut
    records: list[ArtifactEvidenceRecordOut] = Field(default_factory=list)


class ArtifactEvidenceImportRecord(BaseModel):
    workstream: str | None = None
    section_type: str | None = None
    item_id: str | None = None
    vdr_document_id: UUID | None = None
    reference_label: str
    original_name: str | None = None
    primary_workstream: str | None = None
    workstream_tags: list[str] = Field(default_factory=list)
    evidence_kind: str | None = None
    directness: str | None = None
    confidence: float = 0.0
    relevance_score: float = 0.0
    source_page: str | None = None
    source_snippet: str | None = None
    evidence_locator: dict | None = None
    requires_manual_review: bool = False
    is_foreign_workstream: bool = False
    is_unresolved_reference: bool = False
    used_in_draft: bool = True
    used_in_final: bool = False
    analysis_phase: str = "DRAFT"
    ordinal: int = 0
    chunk_id: str | None = None


class ArtifactEvidenceImportRequest(BaseModel):
    artifact_type: str = "FDD_REPORT"
    artifact_id: UUID | None = None
    external_artifact_ref: str | None = None
    default_workstream: str = "FDD"
    records: list[ArtifactEvidenceImportRecord] = Field(default_factory=list)


class ArtifactEvidenceImportOut(BaseModel):
    artifact_type: str
    artifact_id: UUID
    imported_count: int = 0
