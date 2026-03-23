"""Routing triage queue and manual override persistence for VDR documents."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentNotFoundError
from app.models.enums import VdrDocumentStatus
from app.models.vdr_document import VdrDocument
from app.models.vdr_document_routing_override import VdrDocumentRoutingOverride
from app.models.vdr_folder import VdrFolder
from app.ralph.parsers.base import ParsedFile
from app.schemas.vdr import VdrDocumentOut, VdrRoutingOverrideUpsert, VdrRoutingQueueStatus
from app.services.text_extraction_service import TextExtractionService, VdrSourceFile
from app.services.workstream_router_service import (
    RoutedWorkstreamSource,
    WorkstreamRoutingOverride,
    normalize_workstream_tags,
    route_vdr_sources,
)


async def list_routing_overrides(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    *,
    document_ids: list[uuid.UUID] | None = None,
) -> list[VdrDocumentRoutingOverride]:
    stmt = select(VdrDocumentRoutingOverride).where(
        VdrDocumentRoutingOverride.transaction_id == transaction_id,
    )
    if document_ids is not None:
        if not document_ids:
            return []
        stmt = stmt.where(VdrDocumentRoutingOverride.vdr_document_id.in_(document_ids))
    stmt = stmt.order_by(VdrDocumentRoutingOverride.reviewed_at.desc(), VdrDocumentRoutingOverride.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_routing_override_map(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    *,
    document_ids: list[uuid.UUID] | None = None,
) -> dict[uuid.UUID, WorkstreamRoutingOverride]:
    overrides = await list_routing_overrides(db, transaction_id, document_ids=document_ids)
    return {override.vdr_document_id: _to_override_snapshot(override) for override in overrides}


async def upsert_routing_override(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    doc_id: uuid.UUID,
    body: VdrRoutingOverrideUpsert,
    *,
    reviewed_by_email: str | None,
) -> VdrDocumentRoutingOverride:
    await _get_active_document(db, transaction_id, doc_id)
    stmt = select(VdrDocumentRoutingOverride).where(
        VdrDocumentRoutingOverride.transaction_id == transaction_id,
        VdrDocumentRoutingOverride.vdr_document_id == doc_id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    tags = list(normalize_workstream_tags(body.primary_workstream, body.workstream_tags))
    if existing is None:
        existing = VdrDocumentRoutingOverride(
            transaction_id=transaction_id,
            vdr_document_id=doc_id,
            primary_workstream=body.primary_workstream,
            workstream_tags=tags,
        )
        db.add(existing)

    existing.primary_workstream = body.primary_workstream
    existing.workstream_tags = tags
    existing.override_note = body.override_note
    existing.reviewed_by_email = reviewed_by_email
    existing.reviewed_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(existing)
    return existing


async def delete_routing_override(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    doc_id: uuid.UUID,
) -> None:
    await _get_active_document(db, transaction_id, doc_id)
    stmt = select(VdrDocumentRoutingOverride).where(
        VdrDocumentRoutingOverride.transaction_id == transaction_id,
        VdrDocumentRoutingOverride.vdr_document_id == doc_id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        await db.delete(existing)
        await db.commit()


async def build_routing_queue(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    *,
    status_filter: VdrRoutingQueueStatus = "open",
) -> dict[str, Any]:
    rows = await _list_active_document_rows(db, transaction_id)
    if not rows:
        return {
            "summary": {
                "total_documents": 0,
                "returned_documents": 0,
                "open_documents": 0,
                "reviewed_documents": 0,
                "auto_routed_documents": 0,
                "by_effective_workstream": {},
            },
            "items": [],
        }

    doc_ids = [doc.id for doc, _folder in rows]
    source_files = await _build_routing_source_files(db, transaction_id, rows)
    auto_routed = route_vdr_sources(source_files)
    overrides = await get_routing_override_map(db, transaction_id, document_ids=doc_ids)
    effective_routed = route_vdr_sources(source_files, overrides=overrides)

    auto_by_id = {routed.source.vdr_document_id: routed for routed in auto_routed}
    effective_by_id = {routed.source.vdr_document_id: routed for routed in effective_routed}

    status_counts: Counter[str] = Counter()
    workstream_counts: Counter[str] = Counter()
    items: list[dict[str, Any]] = []

    for doc, folder in rows:
        auto_route = auto_by_id[doc.id]
        effective_route = effective_by_id[doc.id]
        routing_status = _get_routing_status(effective_route)

        status_counts[routing_status] += 1
        workstream_counts[effective_route.primary_workstream] += 1

        item = {
            "document": VdrDocumentOut.model_validate(doc).model_dump(mode="python"),
            "folder_name": folder.name,
            "folder_category": str(folder.category),
            "routing_status": routing_status,
            "auto_route": _serialize_routed_source(auto_route),
            "effective_route": _serialize_routed_source(effective_route),
        }
        if _matches_status_filter(routing_status, status_filter):
            items.append(item)

    return {
        "summary": {
            "total_documents": len(rows),
            "returned_documents": len(items),
            "open_documents": status_counts["OPEN_REVIEW"],
            "reviewed_documents": status_counts["OVERRIDDEN"],
            "auto_routed_documents": status_counts["AUTO_ROUTED"],
            "by_effective_workstream": dict(workstream_counts),
        },
        "items": items,
    }


async def _get_active_document(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    doc_id: uuid.UUID,
) -> VdrDocument:
    stmt = select(VdrDocument).where(
        VdrDocument.id == doc_id,
        VdrDocument.transaction_id == transaction_id,
        VdrDocument.status == VdrDocumentStatus.ACTIVE,
    )
    document = (await db.execute(stmt)).scalar_one_or_none()
    if document is None:
        raise DocumentNotFoundError("VDR document could not be found.")
    return document


async def _list_active_document_rows(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[tuple[VdrDocument, VdrFolder]]:
    stmt = (
        select(VdrDocument, VdrFolder)
        .join(VdrFolder, VdrDocument.folder_id == VdrFolder.id)
        .where(
            VdrDocument.transaction_id == transaction_id,
            VdrDocument.status == VdrDocumentStatus.ACTIVE,
        )
        .order_by(VdrDocument.created_at.desc())
    )
    return list((await db.execute(stmt)).all())


async def _build_routing_source_files(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    rows: list[tuple[VdrDocument, VdrFolder]],
) -> list[VdrSourceFile]:
    doc_ids = [doc.id for doc, _folder in rows]
    source_files = await TextExtractionService().extract_from_vdr_documents(
        db,
        transaction_id,
        document_ids=doc_ids,
        use_cache_only=True,
    )
    source_by_id = {source.vdr_document_id: source for source in source_files}

    for doc, folder in rows:
        if doc.id in source_by_id:
            continue
        source_files.append(_build_placeholder_source_file(doc, folder))

    return source_files


def _build_placeholder_source_file(doc: VdrDocument, folder: VdrFolder) -> VdrSourceFile:
    suffix = Path(doc.original_name).suffix.lower().lstrip(".") or "unknown"
    parsed = ParsedFile(
        source_path=doc.file_path or "",
        file_type=suffix,
        text="",
        metadata={},
        ddrl_sections=[],
        parse_error="routing_queue_placeholder",
    )
    return VdrSourceFile(
        parsed=parsed,
        vdr_document_id=doc.id,
        vdr_folder_id=folder.id,
        vdr_category=folder.category,
        original_name=doc.original_name,
    )


def _to_override_snapshot(override: VdrDocumentRoutingOverride) -> WorkstreamRoutingOverride:
    return WorkstreamRoutingOverride(
        primary_workstream=override.primary_workstream,
        workstream_tags=tuple(override.workstream_tags or []),
        override_note=override.override_note,
        reviewed_by_email=override.reviewed_by_email,
        reviewed_at=override.reviewed_at,
    )


def _serialize_routed_source(routed: RoutedWorkstreamSource) -> dict[str, Any]:
    return {
        "primary_workstream": routed.primary_workstream,
        "workstream_tags": list(routed.workstream_tags),
        "confidence": routed.confidence,
        "requires_manual_review": routed.requires_manual_review,
        "reasons": list(routed.reasons),
        "is_override": routed.is_override,
        "override_note": routed.override_note,
        "reviewed_by_email": routed.reviewed_by_email,
        "reviewed_at": routed.reviewed_at,
    }


def _get_routing_status(routed: RoutedWorkstreamSource) -> str:
    if routed.is_override:
        return "OVERRIDDEN"
    if routed.requires_manual_review:
        return "OPEN_REVIEW"
    return "AUTO_ROUTED"


def _matches_status_filter(routing_status: str, status_filter: VdrRoutingQueueStatus) -> bool:
    if status_filter == "all":
        return True
    if status_filter == "reviewed":
        return routing_status == "OVERRIDDEN"
    return routing_status == "OPEN_REVIEW"
