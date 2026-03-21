"""Shared import helpers for cross-workstream evidence ingestion."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.evidence_store_service import (
    build_document_chunk_lookup,
    build_platform_evidence_records,
    replace_platform_evidence_records,
)

_EXTERNAL_EVIDENCE_NAMESPACE = uuid.UUID("3f840aaf-3ef0-4f2e-9fd8-5b20c813f26f")


def resolve_external_artifact_id(
    *,
    transaction_id: uuid.UUID,
    artifact_type: str,
    artifact_id: uuid.UUID | None = None,
    external_artifact_ref: str | None = None,
) -> uuid.UUID:
    if artifact_id is not None:
        return artifact_id
    external_ref = (external_artifact_ref or "").strip()
    if not external_ref:
        raise ValueError("artifact_id or external_artifact_ref is required for evidence import.")
    return uuid.uuid5(
        _EXTERNAL_EVIDENCE_NAMESPACE,
        f"{transaction_id}:{artifact_type}:{external_ref}",
    )


async def import_artifact_evidence_records(
    db: AsyncSession,
    *,
    transaction_id: uuid.UUID,
    artifact_type: str,
    artifact_id: uuid.UUID,
    default_workstream: str,
    records: list[dict[str, Any]],
) -> int:
    vdr_document_ids = [record["vdr_document_id"] for record in records if record.get("vdr_document_id")]
    chunk_lookup = await build_document_chunk_lookup(db, vdr_document_ids=vdr_document_ids)
    platform_records = build_platform_evidence_records(
        transaction_id=transaction_id,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        workstream=default_workstream,
        source_records=records,
        document_chunk_lookup=chunk_lookup,
    )
    await replace_platform_evidence_records(
        db,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        records=platform_records,
    )
    return len(platform_records)
