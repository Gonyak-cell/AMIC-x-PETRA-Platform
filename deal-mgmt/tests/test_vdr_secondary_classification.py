from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.enums import (
    DealType,
    TransactionPhase,
    TransactionSide,
    TransactionStatus,
    VdrClassificationStatus,
    VdrFolderCategory,
)
from app.models.transaction import Transaction
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.ralph.parsers.base import ParsedFile
from app.services.vdr_classification_service import classify_document_by_content

pytestmark = pytest.mark.anyio


async def _create_txn_with_folders(async_session):
    txn = Transaction(
        code_name=f"TEST-{uuid.uuid4().hex[:8].upper()}",
        name="VDR Secondary Classification Test",
        deal_type=DealType.SE,
        side=TransactionSide.SELL,
        phase=TransactionPhase.ENGAGEMENT,
        status=TransactionStatus.DRAFT,
        target_company_name="Target Co",
        client_name="Client Co",
        lead_advisor_email="advisor@example.com",
    )
    async_session.add(txn)
    await async_session.flush()

    custom_folder = VdrFolder(
        transaction_id=txn.id,
        name="Routing Review",
        category=VdrFolderCategory.CUSTOM,
        order_index=0,
        is_required=False,
    )
    financial_folder = VdrFolder(
        transaction_id=txn.id,
        name="Financial",
        category=VdrFolderCategory.FINANCIAL,
        order_index=1,
        is_required=True,
    )
    async_session.add_all([custom_folder, financial_folder])
    await async_session.flush()
    await async_session.commit()
    return txn, custom_folder, financial_folder


async def test_secondary_classification_moves_document_to_target_folder(async_session):
    txn, custom_folder, financial_folder = await _create_txn_with_folders(async_session)
    doc = VdrDocument(
        transaction_id=txn.id,
        folder_id=custom_folder.id,
        original_name="mystery_document.pdf",
        stored_name="mystery_document.pdf",
        file_path="/tmp/mystery_document.pdf",
        file_size_bytes=128,
        mime_type="application/pdf",
        classification_status=VdrClassificationStatus.PENDING_REVIEW,
        manual_review_needed=True,
    )
    async_session.add(doc)
    await async_session.commit()

    parsed = ParsedFile(
        source_path=doc.file_path,
        file_type="pdf",
        text="Revenue bridge and EBITDA adjustments for the fiscal year.",
    )
    llm_client = Mock()
    llm_client.call = AsyncMock(return_value='{"category": "FINANCIAL", "confidence": 0.92}')

    with (
        patch("app.ralph.parsers.parse_file", return_value=parsed),
        patch("app.ralph.llm_client.RalphLLMClient.from_settings", return_value=llm_client),
    ):
        result = await classify_document_by_content(async_session, doc.id, txn.id)

    await async_session.refresh(doc)
    assert result == VdrClassificationStatus.CLASSIFIED
    assert doc.classification_status == VdrClassificationStatus.CLASSIFIED
    assert doc.folder_id == financial_folder.id
    assert doc.manual_review_needed is False


async def test_secondary_classification_marks_manual_review_on_low_confidence(async_session):
    txn, custom_folder, _financial_folder = await _create_txn_with_folders(async_session)
    doc = VdrDocument(
        transaction_id=txn.id,
        folder_id=custom_folder.id,
        original_name="uncertain_document.pdf",
        stored_name="uncertain_document.pdf",
        file_path="/tmp/uncertain_document.pdf",
        file_size_bytes=128,
        mime_type="application/pdf",
        classification_status=VdrClassificationStatus.PENDING_REVIEW,
        manual_review_needed=False,
    )
    async_session.add(doc)
    await async_session.commit()

    parsed = ParsedFile(
        source_path=doc.file_path,
        file_type="pdf",
        text="General notes without a clear workstream signal.",
    )
    llm_client = Mock()
    llm_client.call = AsyncMock(return_value='{"category": "FINANCIAL", "confidence": 0.41}')

    with (
        patch("app.ralph.parsers.parse_file", return_value=parsed),
        patch("app.ralph.llm_client.RalphLLMClient.from_settings", return_value=llm_client),
    ):
        result = await classify_document_by_content(async_session, doc.id, txn.id)

    await async_session.refresh(doc)
    assert result == VdrClassificationStatus.MANUAL_REVIEW
    assert doc.classification_status == VdrClassificationStatus.MANUAL_REVIEW
    assert doc.folder_id == custom_folder.id
    assert doc.manual_review_needed is True
