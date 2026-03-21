"""Shared persistence helpers for document chunks and evidence records."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk
from app.models.evidence_record import EvidenceRecord


def normalize_document_chunks(
    *,
    transaction_id: uuid.UUID,
    vdr_document_id: uuid.UUID,
    vdr_text_cache_id: uuid.UUID | None,
    chunks: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Normalize parser chunk metadata into table rows."""
    rows: list[dict[str, Any]] = []
    for ordinal, chunk in enumerate(chunks or [], start=1):
        rows.append(
            {
                "transaction_id": transaction_id,
                "vdr_document_id": vdr_document_id,
                "vdr_text_cache_id": vdr_text_cache_id,
                "chunk_id": str(chunk.get("chunk_id") or f"chunk-{ordinal}"),
                "ordinal": int(chunk.get("ordinal") or ordinal),
                "locator_type": chunk.get("locator_type"),
                "page": chunk.get("page"),
                "paragraph": chunk.get("paragraph"),
                "sheet": chunk.get("sheet"),
                "row": chunk.get("row"),
                "page_reference": _format_page_reference(chunk),
                "chunk_text": str(chunk.get("text", "") or "") or None,
            }
        )
    return rows


async def replace_document_chunks(
    db: AsyncSession,
    *,
    transaction_id: uuid.UUID,
    vdr_document_id: uuid.UUID,
    vdr_text_cache_id: uuid.UUID | None,
    chunks: list[dict[str, Any]] | None,
) -> dict[tuple[str, str], uuid.UUID]:
    """Replace normalized chunks for one VDR document and return a lookup."""
    rows = normalize_document_chunks(
        transaction_id=transaction_id,
        vdr_document_id=vdr_document_id,
        vdr_text_cache_id=vdr_text_cache_id,
        chunks=chunks,
    )
    await db.execute(delete(DocumentChunk).where(DocumentChunk.vdr_document_id == vdr_document_id))

    lookup: dict[tuple[str, str], uuid.UUID] = {}
    for row in rows:
        chunk = DocumentChunk(**row)
        db.add(chunk)
        await db.flush()
        lookup[(str(chunk.vdr_document_id), chunk.chunk_id)] = chunk.id
    return lookup


async def build_document_chunk_lookup(
    db: AsyncSession,
    *,
    vdr_document_ids: Iterable[uuid.UUID],
) -> dict[tuple[str, str], uuid.UUID]:
    """Return {(vdr_document_id, chunk_id): document_chunk_id} for quick joins."""
    ids = list(dict.fromkeys(vdr_document_ids))
    if not ids:
        return {}

    result = await db.execute(
        select(DocumentChunk.vdr_document_id, DocumentChunk.chunk_id, DocumentChunk.id).where(
            DocumentChunk.vdr_document_id.in_(ids)
        )
    )
    return {(str(doc_id), chunk_id): chunk_row_id for doc_id, chunk_id, chunk_row_id in result.all()}


def build_platform_evidence_records(
    *,
    transaction_id: uuid.UUID,
    artifact_type: str,
    artifact_id: uuid.UUID,
    workstream: str,
    source_records: list[dict[str, Any]],
    document_chunk_lookup: Mapping[tuple[str, str], uuid.UUID] | None = None,
) -> list[dict[str, Any]]:
    """Project workstream-specific evidence rows into the common table shape."""
    chunk_lookup = document_chunk_lookup or {}
    rows: list[dict[str, Any]] = []
    for record in source_records:
        vdr_document_id = _coerce_uuid(record.get("vdr_document_id"))
        chunk_id = str(record.get("chunk_id") or "") or None
        document_chunk_id = None
        if vdr_document_id and chunk_id:
            document_chunk_id = chunk_lookup.get((str(vdr_document_id), chunk_id))

        rows.append(
            {
                "transaction_id": transaction_id,
                "artifact_type": artifact_type,
                "artifact_id": artifact_id,
                "workstream": str(record.get("workstream") or workstream),
                "section_type": record.get("section_type"),
                "item_id": record.get("item_id"),
                "vdr_document_id": vdr_document_id,
                "document_chunk_id": document_chunk_id,
                "reference_label": record.get("reference_label", ""),
                "original_name": record.get("original_name"),
                "primary_workstream": record.get("primary_workstream"),
                "workstream_tags": list(record.get("workstream_tags") or []),
                "evidence_kind": record.get("evidence_kind"),
                "directness": record.get("directness"),
                "confidence": float(record.get("confidence", 0.0) or 0.0),
                "relevance_score": float(record.get("relevance_score", 0.0) or 0.0),
                "source_page": record.get("source_page"),
                "source_snippet": record.get("source_snippet"),
                "evidence_locator": record.get("evidence_locator"),
                "requires_manual_review": bool(record.get("requires_manual_review")),
                "is_foreign_workstream": bool(record.get("is_foreign_workstream")),
                "is_unresolved_reference": bool(record.get("is_unresolved_reference")),
                "used_in_draft": bool(record.get("used_in_draft")),
                "used_in_final": bool(record.get("used_in_final")),
                "analysis_phase": str(record.get("analysis_phase", "DRAFT") or "DRAFT"),
                "ordinal": int(record.get("ordinal", 0) or 0),
            }
        )
    return rows


async def replace_platform_evidence_records(
    db: AsyncSession,
    *,
    artifact_type: str,
    artifact_id: uuid.UUID,
    records: list[dict[str, Any]],
) -> None:
    """Replace common evidence rows for one generated artifact."""
    await db.execute(
        delete(EvidenceRecord).where(
            EvidenceRecord.artifact_type == artifact_type,
            EvidenceRecord.artifact_id == artifact_id,
        )
    )
    for record in records:
        db.add(EvidenceRecord(**record))
    await db.flush()


async def delete_platform_evidence_records(
    db: AsyncSession,
    *,
    artifact_type: str,
    artifact_id: uuid.UUID,
) -> None:
    """Delete common evidence rows for one generated artifact."""
    await db.execute(
        delete(EvidenceRecord).where(
            EvidenceRecord.artifact_type == artifact_type,
            EvidenceRecord.artifact_id == artifact_id,
        )
    )
    await db.flush()


def _coerce_uuid(value: Any) -> uuid.UUID | None:
    if not value:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _format_page_reference(chunk: Mapping[str, Any]) -> str | None:
    if chunk.get("page") is not None:
        return f"Page {chunk['page']}"
    if chunk.get("sheet") is not None and chunk.get("row") is not None:
        return f"Sheet {chunk['sheet']} Row {chunk['row']}"
    if chunk.get("paragraph") is not None:
        return f"Paragraph {chunk['paragraph']}"
    if chunk.get("ordinal") is not None:
        return f"Chunk {chunk['ordinal']}"
    return None
