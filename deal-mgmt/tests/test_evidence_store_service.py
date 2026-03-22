from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk
from app.models.enums import TransactionSide, VdrDocumentStatus, VdrFolderCategory
from app.models.evidence_record import EvidenceRecord
from app.models.ldd_report import LDDReport
from app.models.transaction import Transaction
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.models.vdr_text_cache import VdrTextCache
from app.services.evidence_store_service import (
    build_document_chunk_lookup,
    build_platform_evidence_records,
    replace_document_chunks,
    replace_platform_evidence_records,
)
from app.services.ldd_source_controls import build_ldd_evidence_records
from app.services.text_extraction_service import TextExtractionService

pytestmark = pytest.mark.anyio


async def _make_txn(db: AsyncSession) -> Transaction:
    txn = Transaction(
        name="Evidence Test Txn",
        code_name=f"EV-{uuid.uuid4().hex[:8].upper()}",
        side=TransactionSide.SELL,
        target_company_name="Target Co",
        client_name="Client Co",
        lead_advisor_email="advisor@example.com",
    )
    db.add(txn)
    await db.flush()
    return txn


async def _make_vdr_doc(db: AsyncSession, txn: Transaction) -> VdrDocument:
    folder = VdrFolder(
        transaction_id=txn.id,
        name="Legal",
        category=VdrFolderCategory.LEGAL,
        is_required=False,
    )
    db.add(folder)
    await db.flush()

    doc = VdrDocument(
        transaction_id=txn.id,
        folder_id=folder.id,
        original_name="shareholders_agreement.pdf",
        stored_name="shareholders_agreement.pdf",
        file_path="/tmp/shareholders_agreement.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        sha256_hash="abc123",
        status=VdrDocumentStatus.ACTIVE,
    )
    db.add(doc)
    await db.flush()
    return doc


async def _make_ldd_report(db: AsyncSession, txn: Transaction) -> LDDReport:
    report = LDDReport(
        transaction_id=txn.id,
        title="LDD Report",
        report_type="FULL",
        status="DRAFT",
    )
    db.add(report)
    await db.flush()
    return report


async def test_replace_document_chunks_and_lookup(async_session: AsyncSession) -> None:
    txn = await _make_txn(async_session)
    doc = await _make_vdr_doc(async_session, txn)
    cache = VdrTextCache(
        vdr_document_id=doc.id,
        sha256_hash=doc.sha256_hash or "",
        file_type="pdf",
        extracted_text="Sample text",
        text_length=11,
        is_valid=True,
    )
    async_session.add(cache)
    await async_session.flush()

    lookup = await replace_document_chunks(
        async_session,
        transaction_id=txn.id,
        vdr_document_id=doc.id,
        vdr_text_cache_id=cache.id,
        chunks=[
            {
                "chunk_id": "page-3",
                "locator_type": "page",
                "page": 3,
                "ordinal": 1,
                "text": "Investor consent is required.",
            },
            {
                "chunk_id": "paragraph-2",
                "locator_type": "paragraph",
                "paragraph": 2,
                "ordinal": 2,
                "text": "Board approval is required.",
            },
        ],
    )

    rows = (await async_session.execute(select(DocumentChunk).order_by(DocumentChunk.ordinal))).scalars().all()

    assert len(rows) == 2
    assert rows[0].page_reference == "Page 3"
    assert rows[1].page_reference == "Paragraph 2"
    assert lookup[(str(doc.id), "page-3")] == rows[0].id


async def test_build_platform_evidence_records_links_common_chunk_rows(async_session: AsyncSession) -> None:
    txn = await _make_txn(async_session)
    doc = await _make_vdr_doc(async_session, txn)
    report = await _make_ldd_report(async_session, txn)

    await replace_document_chunks(
        async_session,
        transaction_id=txn.id,
        vdr_document_id=doc.id,
        vdr_text_cache_id=None,
        chunks=[
            {
                "chunk_id": "page-3",
                "locator_type": "page",
                "page": 3,
                "ordinal": 1,
                "text": "Investor consent is required.",
            }
        ],
    )
    chunk_lookup = await build_document_chunk_lookup(async_session, vdr_document_ids=[doc.id])

    ldd_records = build_ldd_evidence_records(
        transaction_id=str(txn.id),
        report_id=str(report.id),
        evidence_ledger={
            "by_item_id": {
                "CONTRACT-04": {
                    "item_id": "CONTRACT-04",
                    "section_type": "CONTRACTS",
                    "confidence": 0.81,
                    "unresolved_refs": [],
                    "documents": [
                        {
                            "reference": "shareholders_agreement.pdf",
                            "document_id": str(doc.id),
                            "original_name": "shareholders_agreement.pdf",
                            "primary_workstream": "LDD",
                            "workstream_tags": ["LDD"],
                            "evidence_kind": "DIRECT_CONTRACT",
                            "directness": "DIRECT",
                            "page_reference": "Page 3",
                            "chunk_id": "page-3",
                            "snippet": "Investor consent is required.",
                            "locator": {"locator_type": "page", "page": 3},
                            "requires_manual_review": False,
                            "include_for_ldd": True,
                        }
                    ],
                }
            }
        },
        analysis_phase="FINAL",
    )

    platform_records = build_platform_evidence_records(
        transaction_id=txn.id,
        artifact_type="LDD_REPORT",
        artifact_id=report.id,
        workstream="LDD",
        source_records=ldd_records,
        document_chunk_lookup=chunk_lookup,
    )
    await replace_platform_evidence_records(
        async_session,
        artifact_type="LDD_REPORT",
        artifact_id=report.id,
        records=platform_records,
    )

    rows = (await async_session.execute(select(EvidenceRecord))).scalars().all()

    assert len(rows) == 1
    assert rows[0].document_chunk_id is not None
    assert rows[0].artifact_type == "LDD_REPORT"
    assert rows[0].workstream == "LDD"


async def test_text_extraction_service_cache_hit_backfills_document_chunks(async_session: AsyncSession) -> None:
    txn = await _make_txn(async_session)
    doc = await _make_vdr_doc(async_session, txn)
    cache = VdrTextCache(
        vdr_document_id=doc.id,
        sha256_hash=doc.sha256_hash or "",
        file_type="pdf",
        extracted_text="[Page 3]\nInvestor consent is required.",
        chunks_json=[
            {
                "chunk_id": "page-3",
                "locator_type": "page",
                "page": 3,
                "ordinal": 1,
                "text": "Investor consent is required.",
            }
        ],
        ddrl_sections=["CONTRACTS"],
        text_length=39,
        is_valid=True,
    )
    async_session.add(cache)
    await async_session.flush()

    service = TextExtractionService()
    parsed = await service._get_or_extract(async_session, doc)

    rows = (await async_session.execute(select(DocumentChunk))).scalars().all()

    assert parsed.metadata["chunks"][0]["chunk_id"] == "page-3"
    assert len(rows) == 1
    assert rows[0].chunk_id == "page-3"
    assert rows[0].vdr_document_id == doc.id
