"""Query helpers for platform-wide evidence traceability APIs."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence_record import EvidenceRecord
from app.models.ldd_evidence_record import LDDEvidenceRecord


async def list_artifact_evidence(
    db: AsyncSession,
    *,
    transaction_id: uuid.UUID,
    artifact_type: str,
    artifact_id: uuid.UUID,
    workstream: str | None = None,
    section_type: str | None = None,
    item_id: str | None = None,
    analysis_phase: str | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Return evidence rows for one artifact, preferring the common table."""

    stmt: Select[tuple[EvidenceRecord]] = select(EvidenceRecord).where(
        EvidenceRecord.transaction_id == transaction_id,
        EvidenceRecord.artifact_type == artifact_type,
        EvidenceRecord.artifact_id == artifact_id,
    )
    if workstream:
        stmt = stmt.where(EvidenceRecord.workstream == workstream)
    if section_type:
        stmt = stmt.where(EvidenceRecord.section_type == section_type)
    if item_id:
        stmt = stmt.where(EvidenceRecord.item_id == item_id)
    if analysis_phase:
        stmt = stmt.where(EvidenceRecord.analysis_phase == analysis_phase)

    rows = (await db.execute(stmt.order_by(EvidenceRecord.ordinal, EvidenceRecord.created_at))).scalars().all()
    if rows:
        return [_serialize_common_record(row) for row in rows], False

    if artifact_type == "LDD_REPORT":
        fallback_rows = await _load_legacy_ldd_evidence(
            db,
            artifact_id=artifact_id,
            workstream=workstream,
            section_type=section_type,
            item_id=item_id,
            analysis_phase=analysis_phase,
        )
        if fallback_rows:
            return fallback_rows, True

    return [], False


def summarize_artifact_evidence(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build compact summary counters for one evidence response."""

    by_workstream: dict[str, int] = {}
    by_phase: dict[str, int] = {}
    for record in records:
        workstream = str(record.get("workstream") or "UNKNOWN")
        phase = str(record.get("analysis_phase") or "UNKNOWN")
        by_workstream[workstream] = by_workstream.get(workstream, 0) + 1
        by_phase[phase] = by_phase.get(phase, 0) + 1

    return {
        "total_records": len(records),
        "direct_count": sum(1 for record in records if record.get("directness") == "DIRECT"),
        "indirect_count": sum(1 for record in records if record.get("directness") == "INDIRECT"),
        "manual_review_count": sum(1 for record in records if record.get("requires_manual_review")),
        "foreign_count": sum(1 for record in records if record.get("is_foreign_workstream")),
        "unresolved_count": sum(1 for record in records if record.get("is_unresolved_reference")),
        "draft_count": sum(1 for record in records if record.get("used_in_draft")),
        "final_count": sum(1 for record in records if record.get("used_in_final")),
        "by_workstream": by_workstream,
        "by_phase": by_phase,
    }


async def _load_legacy_ldd_evidence(
    db: AsyncSession,
    *,
    artifact_id: uuid.UUID,
    workstream: str | None,
    section_type: str | None,
    item_id: str | None,
    analysis_phase: str | None,
) -> list[dict[str, Any]]:
    stmt: Select[tuple[LDDEvidenceRecord]] = select(LDDEvidenceRecord).where(
        LDDEvidenceRecord.ldd_report_id == artifact_id
    )
    if section_type:
        stmt = stmt.where(LDDEvidenceRecord.section_type == section_type)
    if item_id:
        stmt = stmt.where(LDDEvidenceRecord.item_id == item_id)
    if analysis_phase:
        stmt = stmt.where(LDDEvidenceRecord.analysis_phase == analysis_phase)

    rows = (await db.execute(stmt.order_by(LDDEvidenceRecord.ordinal, LDDEvidenceRecord.created_at))).scalars().all()
    serialized = [_serialize_legacy_ldd_record(row) for row in rows]
    if workstream:
        serialized = [record for record in serialized if record["workstream"] == workstream]
    return serialized


def _serialize_common_record(row: EvidenceRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "artifact_type": row.artifact_type,
        "artifact_id": row.artifact_id,
        "workstream": row.workstream,
        "section_type": row.section_type,
        "item_id": row.item_id,
        "vdr_document_id": row.vdr_document_id,
        "document_chunk_id": row.document_chunk_id,
        "reference_label": row.reference_label,
        "original_name": row.original_name,
        "primary_workstream": row.primary_workstream,
        "workstream_tags": list(row.workstream_tags or []),
        "evidence_kind": row.evidence_kind,
        "directness": row.directness,
        "confidence": row.confidence,
        "relevance_score": row.relevance_score,
        "source_page": row.source_page,
        "source_snippet": row.source_snippet,
        "evidence_locator": row.evidence_locator,
        "requires_manual_review": row.requires_manual_review,
        "is_foreign_workstream": row.is_foreign_workstream,
        "is_unresolved_reference": row.is_unresolved_reference,
        "used_in_draft": row.used_in_draft,
        "used_in_final": row.used_in_final,
        "analysis_phase": row.analysis_phase,
        "ordinal": row.ordinal,
    }


def _serialize_legacy_ldd_record(row: LDDEvidenceRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "artifact_type": "LDD_REPORT",
        "artifact_id": row.ldd_report_id,
        "workstream": "LDD",
        "section_type": row.section_type,
        "item_id": row.item_id,
        "vdr_document_id": row.vdr_document_id,
        "document_chunk_id": None,
        "reference_label": row.reference_label,
        "original_name": row.original_name,
        "primary_workstream": row.primary_workstream,
        "workstream_tags": list(row.workstream_tags or []),
        "evidence_kind": row.evidence_kind,
        "directness": row.directness,
        "confidence": row.confidence,
        "relevance_score": row.relevance_score,
        "source_page": row.source_page,
        "source_snippet": row.source_snippet,
        "evidence_locator": row.evidence_locator,
        "requires_manual_review": row.requires_manual_review,
        "is_foreign_workstream": row.is_foreign_workstream,
        "is_unresolved_reference": row.is_unresolved_reference,
        "used_in_draft": row.used_in_draft,
        "used_in_final": row.used_in_final,
        "analysis_phase": row.analysis_phase,
        "ordinal": row.ordinal,
    }
