from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk
from app.models.enums import (
    FinancialModelStatus,
    FinancialModelType,
    FMChecklistCategory,
    FMChecklistItemStatus,
    FMChecklistStatus,
    TransactionSide,
    VdrDocumentStatus,
    VdrFolderCategory,
)
from app.models.evidence_record import EvidenceRecord
from app.models.financial_model import FinancialModel, FMChecklist, FMChecklistItem
from app.models.transaction import Transaction
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.services.evidence_store_service import replace_document_chunks
from app.services.financial_model_service import sync_financial_model_evidence

pytestmark = pytest.mark.anyio


async def _make_txn(db: AsyncSession) -> Transaction:
    txn = Transaction(
        name="FM Evidence Txn",
        code_name=f"FM-{uuid.uuid4().hex[:8].upper()}",
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
        name="Financial",
        category=VdrFolderCategory.FINANCIAL,
        is_required=False,
    )
    db.add(folder)
    await db.flush()

    doc = VdrDocument(
        transaction_id=txn.id,
        folder_id=folder.id,
        original_name="valuation_bridge.pdf",
        stored_name="valuation_bridge.pdf",
        file_path="/tmp/valuation_bridge.pdf",
        file_size_bytes=2048,
        mime_type="application/pdf",
        sha256_hash="valuation-bridge",
        status=VdrDocumentStatus.ACTIVE,
    )
    db.add(doc)
    await db.flush()
    return doc


async def _make_financial_model(db: AsyncSession, txn: Transaction) -> tuple[FinancialModel, FMChecklistItem]:
    fm = FinancialModel(
        transaction_id=txn.id,
        model_type=FinancialModelType.DCF,
        title="DCF Model",
        status=FinancialModelStatus.PENDING_REVIEW,
        created_by_email="advisor@example.com",
    )
    db.add(fm)
    await db.flush()

    checklist = FMChecklist(
        financial_model_id=fm.id,
        status=FMChecklistStatus.PENDING_REVIEW,
    )
    db.add(checklist)
    await db.flush()

    item = FMChecklistItem(
        checklist_id=checklist.id,
        category=FMChecklistCategory.DCF_PARAMETERS,
        order_index=0,
        title="Exit Multiple (EV/EBITDA)",
        description="Exit multiple assumption",
        field_type="number",
        unit="x",
        status=FMChecklistItemStatus.AUTO_GENERATED,
        auto_finding="Exit Multiple (EV/EBITDA) is 6.5x based on peer valuation analysis.",
        auto_value="6.5x",
        confidence=0.82,
    )
    db.add(item)
    await db.flush()
    return fm, item


async def test_sync_financial_model_evidence_persists_common_records(async_session: AsyncSession) -> None:
    txn = await _make_txn(async_session)
    doc = await _make_vdr_doc(async_session, txn)
    fm, item = await _make_financial_model(async_session, txn)

    item.source_vdr_doc_id = doc.id
    item.source_vdr_doc_name = doc.original_name
    item.source_location = "Page 7"
    item.extra_metadata = {
        "chunk_id": "page-7",
        "primary_workstream": "VALUATION",
        "workstream_tags": ["VALUATION"],
        "requires_manual_review": False,
    }
    await async_session.flush()

    await replace_document_chunks(
        async_session,
        transaction_id=txn.id,
        vdr_document_id=doc.id,
        vdr_text_cache_id=None,
        chunks=[
            {
                "chunk_id": "page-7",
                "locator_type": "page",
                "page": 7,
                "ordinal": 1,
                "text": item.auto_finding,
            }
        ],
    )

    row_count = await sync_financial_model_evidence(async_session, fm.id, txn.id)
    rows = (await async_session.execute(select(EvidenceRecord))).scalars().all()
    chunks = (await async_session.execute(select(DocumentChunk))).scalars().all()

    assert row_count == 1
    assert len(rows) == 1
    assert len(chunks) == 1
    assert rows[0].artifact_type == "FINANCIAL_MODEL"
    assert rows[0].artifact_id == fm.id
    assert rows[0].workstream == "VALUATION"
    assert rows[0].item_id == str(item.id)
    assert rows[0].document_chunk_id == chunks[0].id
    assert rows[0].source_page == "Page 7"
