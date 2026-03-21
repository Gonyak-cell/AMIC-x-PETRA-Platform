from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk
from app.models.enums import LDDReportStatus, LDDReportType, TransactionSide, VdrDocumentStatus, VdrFolderCategory
from app.models.ldd_evidence_record import LDDEvidenceRecord
from app.models.ldd_report import LDDReport
from app.models.transaction import Transaction
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.services.evidence_store_service import replace_platform_evidence_records

pytestmark = pytest.mark.anyio


async def _make_txn(db: AsyncSession) -> Transaction:
    txn = Transaction(
        name="Evidence API Txn",
        code_name=f"EA-{uuid.uuid4().hex[:8].upper()}",
        side=TransactionSide.SELL,
        target_company_name="Target Co",
        client_name="Client Co",
        lead_advisor_email="test@example.com",
    )
    db.add(txn)
    await db.flush()
    return txn


async def _make_ldd_report(db: AsyncSession, txn: Transaction) -> LDDReport:
    report = LDDReport(
        transaction_id=txn.id,
        title="LDD Report",
        report_type=LDDReportType.FULL,
        status=LDDReportStatus.DRAFT,
    )
    db.add(report)
    await db.flush()
    return report


async def _make_vdr_doc(db: AsyncSession, txn: Transaction) -> VdrDocument:
    folder = VdrFolder(
        transaction_id=txn.id,
        name="Financial",
        category=VdrFolderCategory.FINANCIAL,
        is_required=False,
    )
    db.add(folder)
    await db.flush()

    doc = VdrDocument(
        transaction_id=txn.id,
        folder_id=folder.id,
        original_name="qoe_report.xlsx",
        stored_name="qoe_report.xlsx",
        file_path="/tmp/qoe_report.xlsx",
        file_size_bytes=1024,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        sha256_hash="qoe-report",
        status=VdrDocumentStatus.ACTIVE,
    )
    db.add(doc)
    await db.flush()
    return doc


async def test_get_artifact_evidence_returns_common_rows(client, async_session: AsyncSession) -> None:
    txn = await _make_txn(async_session)
    report = await _make_ldd_report(async_session, txn)
    await replace_platform_evidence_records(
        async_session,
        artifact_type="LDD_REPORT",
        artifact_id=report.id,
        records=[
            {
                "transaction_id": txn.id,
                "artifact_type": "LDD_REPORT",
                "artifact_id": report.id,
                "workstream": "LDD",
                "section_type": "CONTRACTS",
                "item_id": "CONTRACT-01",
                "vdr_document_id": None,
                "document_chunk_id": None,
                "reference_label": "shareholders_agreement.pdf",
                "original_name": "shareholders_agreement.pdf",
                "primary_workstream": "LDD",
                "workstream_tags": ["LDD"],
                "evidence_kind": "DIRECT_CONTRACT",
                "directness": "DIRECT",
                "confidence": 0.91,
                "relevance_score": 0.91,
                "source_page": "Page 3",
                "source_snippet": "Investor consent is required.",
                "evidence_locator": {"page": 3},
                "requires_manual_review": False,
                "is_foreign_workstream": False,
                "is_unresolved_reference": False,
                "used_in_draft": True,
                "used_in_final": False,
                "analysis_phase": "DRAFT",
                "ordinal": 1,
            }
        ],
    )
    await async_session.commit()

    resp = await client.get(f"/api/v1/transactions/{txn.id}/evidence/LDD_REPORT/{report.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["used_legacy_fallback"] is False
    assert data["summary"]["total_records"] == 1
    assert data["summary"]["direct_count"] == 1
    assert data["records"][0]["reference_label"] == "shareholders_agreement.pdf"


async def test_get_artifact_evidence_falls_back_to_legacy_ldd_rows(client, async_session: AsyncSession) -> None:
    txn = await _make_txn(async_session)
    report = await _make_ldd_report(async_session, txn)
    async_session.add(
        LDDEvidenceRecord(
            ldd_report_id=report.id,
            transaction_id=txn.id,
            item_id="CONTRACT-02",
            section_type="CONTRACTS",
            reference_label="legacy_reference.docx",
            original_name="legacy_reference.docx",
            primary_workstream="LDD",
            workstream_tags=["LDD"],
            evidence_kind="DIRECT_LEGAL",
            directness="DIRECT",
            confidence=0.75,
            relevance_score=0.75,
            source_page="Page 2",
            chunk_id="page-2",
            source_snippet="Legacy evidence snippet",
            evidence_locator={"page": 2},
            requires_manual_review=False,
            is_foreign_workstream=False,
            is_unresolved_reference=False,
            used_in_draft=True,
            used_in_final=False,
            analysis_phase="DRAFT",
            ordinal=1,
        )
    )
    await async_session.commit()

    resp = await client.get(f"/api/v1/transactions/{txn.id}/evidence/LDD_REPORT/{report.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["used_legacy_fallback"] is True
    assert data["summary"]["total_records"] == 1
    assert data["records"][0]["reference_label"] == "legacy_reference.docx"
    assert data["records"][0]["document_chunk_id"] is None


async def test_import_artifact_evidence_creates_queryable_common_rows(client, async_session: AsyncSession) -> None:
    txn = await _make_txn(async_session)
    doc = await _make_vdr_doc(async_session, txn)
    chunk = DocumentChunk(
        transaction_id=txn.id,
        vdr_document_id=doc.id,
        vdr_text_cache_id=None,
        chunk_id="sheet-1-row-4",
        ordinal=1,
        locator_type="sheet_row",
        sheet="QoE",
        row=4,
        page_reference="Sheet QoE Row 4",
        chunk_text="Net working capital normalized adjustment is KRW 1,200 million.",
    )
    async_session.add(chunk)
    await async_session.commit()

    import_resp = await client.post(
        f"/api/v1/transactions/{txn.id}/evidence/import",
        json={
            "artifact_type": "FDD_REPORT",
            "external_artifact_ref": "fdd-run-001",
            "default_workstream": "FDD",
            "records": [
                {
                    "section_type": "WORKING_CAPITAL",
                    "item_id": "NWC-01",
                    "vdr_document_id": str(doc.id),
                    "reference_label": "qoe_report.xlsx",
                    "original_name": "qoe_report.xlsx",
                    "primary_workstream": "FDD",
                    "workstream_tags": ["FDD"],
                    "evidence_kind": "FINANCIAL_SUPPORT",
                    "directness": "INDIRECT",
                    "confidence": 0.88,
                    "relevance_score": 0.88,
                    "source_page": "Sheet QoE Row 4",
                    "source_snippet": "Net working capital normalized adjustment is KRW 1,200 million.",
                    "evidence_locator": {"sheet": "QoE", "row": 4},
                    "analysis_phase": "FINAL",
                    "used_in_draft": False,
                    "used_in_final": True,
                    "chunk_id": "sheet-1-row-4",
                }
            ],
        },
    )
    assert import_resp.status_code == 202
    artifact_id = import_resp.json()["artifact_id"]

    query_resp = await client.get(f"/api/v1/transactions/{txn.id}/evidence/FDD_REPORT/{artifact_id}")
    assert query_resp.status_code == 200
    data = query_resp.json()
    assert data["used_legacy_fallback"] is False
    assert data["summary"]["total_records"] == 1
    assert data["summary"]["by_workstream"]["FDD"] == 1
    assert data["records"][0]["item_id"] == "NWC-01"
    assert data["records"][0]["document_chunk_id"] == str(chunk.id)
