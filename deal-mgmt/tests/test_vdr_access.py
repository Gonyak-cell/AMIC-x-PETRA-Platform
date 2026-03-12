"""VDR 접근 추적 서비스 테스트."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.buyer_candidate import BuyerCandidate
from app.models.enums import BuyerCandidateStatus, BuyerType, VdrAccessAction
from app.models.transaction import Transaction
from app.models.vdr_access_log import VdrAccessLog
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.services import vdr_access_service

# ── 헬퍼: 테스트 데이터 생성 ──────────────────────────────────


async def _create_transaction(db: AsyncSession) -> Transaction:
    txn = Transaction(
        id=uuid.uuid4(),
        code_name=f"SE-TEST-{uuid.uuid4().hex[:6].upper()}",
        name="VDR Access Test",
        deal_type="SE",
        side="SELL",
        target_company_name="테스트 기업",
        client_name="테스트 고객",
        lead_advisor_email="test@example.com",
    )
    db.add(txn)
    await db.flush()
    return txn


async def _create_folder(db: AsyncSession, txn_id: uuid.UUID) -> VdrFolder:
    folder = VdrFolder(
        id=uuid.uuid4(),
        transaction_id=txn_id,
        name="테스트 폴더",
        category="CORPORATE",
        order_index=0,
        is_required=False,
    )
    db.add(folder)
    await db.flush()
    return folder


async def _create_document(
    db: AsyncSession,
    txn_id: uuid.UUID,
    folder_id: uuid.UUID,
) -> VdrDocument:
    doc_id = uuid.uuid4()
    doc = VdrDocument(
        id=doc_id,
        transaction_id=txn_id,
        folder_id=folder_id,
        original_name="test.pdf",
        stored_name=f"{doc_id.hex}.pdf",
        file_path="vdr/test.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        sha256_hash="abc123",
        status="ACTIVE",
    )
    db.add(doc)
    await db.flush()
    return doc


async def _create_buyer(
    db: AsyncSession,
    txn_id: uuid.UUID,
    name: str = "테스트 매수자",
) -> BuyerCandidate:
    buyer = BuyerCandidate(
        id=uuid.uuid4(),
        transaction_id=txn_id,
        company_name=name,
        buyer_type=BuyerType.STRATEGIC,
        status=BuyerCandidateStatus.IDENTIFIED,
    )
    db.add(buyer)
    await db.flush()
    return buyer


async def _create_access_log(
    db: AsyncSession,
    txn_id: uuid.UUID,
    *,
    document_id: uuid.UUID | None = None,
    folder_id: uuid.UUID | None = None,
    buyer_id: uuid.UUID | None = None,
    action: VdrAccessAction = VdrAccessAction.VIEW,
    user_email: str = "viewer@example.com",
) -> VdrAccessLog:
    log = VdrAccessLog(
        id=uuid.uuid4(),
        transaction_id=txn_id,
        document_id=document_id,
        folder_id=folder_id,
        user_email=user_email,
        user_id="test-user",
        action=action,
        buyer_id=buyer_id,
    )
    db.add(log)
    await db.flush()
    return log


# ── 테스트 ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_access_creates_log(async_session: AsyncSession) -> None:
    """record_access가 VdrAccessLog 레코드를 정상적으로 생성하는지 확인."""
    txn = await _create_transaction(async_session)
    folder = await _create_folder(async_session, txn.id)
    doc = await _create_document(async_session, txn.id, folder.id)
    await async_session.commit()

    await vdr_access_service.record_access(
        async_session,
        transaction_id=txn.id,
        document_id=doc.id,
        folder_id=folder.id,
        user_email="test@example.com",
        user_id="test-user-id",
        action=VdrAccessAction.DOWNLOAD,
        ip_address="127.0.0.1",
        user_agent="TestAgent/1.0",
    )

    logs, total = await vdr_access_service.get_access_logs(async_session, txn.id)
    assert total == 1
    assert logs[0].user_email == "test@example.com"
    assert logs[0].action == VdrAccessAction.DOWNLOAD
    assert logs[0].document_id == doc.id


@pytest.mark.asyncio
async def test_get_access_logs_filters_by_buyer(async_session: AsyncSession) -> None:
    """buyer_id 필터가 정상 동작하는지 확인."""
    txn = await _create_transaction(async_session)
    folder = await _create_folder(async_session, txn.id)
    doc = await _create_document(async_session, txn.id, folder.id)
    buyer_a = await _create_buyer(async_session, txn.id, "매수자 A")
    buyer_b = await _create_buyer(async_session, txn.id, "매수자 B")

    # buyer_a: 2건, buyer_b: 1건
    await _create_access_log(async_session, txn.id, document_id=doc.id, buyer_id=buyer_a.id)
    await _create_access_log(async_session, txn.id, document_id=doc.id, buyer_id=buyer_a.id)
    await _create_access_log(async_session, txn.id, document_id=doc.id, buyer_id=buyer_b.id)
    await async_session.commit()

    logs_a, total_a = await vdr_access_service.get_access_logs(async_session, txn.id, buyer_id=buyer_a.id)
    assert total_a == 2
    assert len(logs_a) == 2

    _logs_b, total_b = await vdr_access_service.get_access_logs(async_session, txn.id, buyer_id=buyer_b.id)
    assert total_b == 1


@pytest.mark.asyncio
async def test_get_access_logs_filters_by_action(async_session: AsyncSession) -> None:
    """action 필터가 정상 동작하는지 확인."""
    txn = await _create_transaction(async_session)
    folder = await _create_folder(async_session, txn.id)
    doc = await _create_document(async_session, txn.id, folder.id)

    await _create_access_log(async_session, txn.id, document_id=doc.id, action=VdrAccessAction.VIEW)
    await _create_access_log(async_session, txn.id, document_id=doc.id, action=VdrAccessAction.DOWNLOAD)
    await _create_access_log(async_session, txn.id, document_id=doc.id, action=VdrAccessAction.DOWNLOAD)
    await async_session.commit()

    _logs_view, total_view = await vdr_access_service.get_access_logs(
        async_session, txn.id, action=VdrAccessAction.VIEW
    )
    assert total_view == 1

    _logs_dl, total_dl = await vdr_access_service.get_access_logs(
        async_session, txn.id, action=VdrAccessAction.DOWNLOAD
    )
    assert total_dl == 2


@pytest.mark.asyncio
async def test_get_buyer_activity_summary(async_session: AsyncSession) -> None:
    """매수자별 VDR 활동 요약이 정상적으로 집계되는지 확인."""
    txn = await _create_transaction(async_session)
    folder = await _create_folder(async_session, txn.id)
    doc1 = await _create_document(async_session, txn.id, folder.id)
    doc2 = await _create_document(async_session, txn.id, folder.id)
    buyer = await _create_buyer(async_session, txn.id, "테스트 매수자")

    # doc1: VIEW 2회 + DOWNLOAD 1회, doc2: VIEW 1회
    await _create_access_log(
        async_session,
        txn.id,
        document_id=doc1.id,
        buyer_id=buyer.id,
        action=VdrAccessAction.VIEW,
    )
    await _create_access_log(
        async_session,
        txn.id,
        document_id=doc1.id,
        buyer_id=buyer.id,
        action=VdrAccessAction.VIEW,
    )
    await _create_access_log(
        async_session,
        txn.id,
        document_id=doc1.id,
        buyer_id=buyer.id,
        action=VdrAccessAction.DOWNLOAD,
    )
    await _create_access_log(
        async_session,
        txn.id,
        document_id=doc2.id,
        buyer_id=buyer.id,
        action=VdrAccessAction.VIEW,
    )
    await async_session.commit()

    summaries = await vdr_access_service.get_buyer_activity_summary(async_session, txn.id)
    assert len(summaries) == 1

    s = summaries[0]
    assert s["buyer_id"] == buyer.id
    assert s["buyer_name"] == "테스트 매수자"
    assert s["unique_documents_accessed"] == 2
    assert s["total_views"] == 3
    assert s["total_downloads"] == 1
    assert s["last_access_at"] is not None


@pytest.mark.asyncio
async def test_get_document_access_logs(async_session: AsyncSession) -> None:
    """특정 문서의 접근 이력만 필터되는지 확인."""
    txn = await _create_transaction(async_session)
    folder = await _create_folder(async_session, txn.id)
    doc1 = await _create_document(async_session, txn.id, folder.id)
    doc2 = await _create_document(async_session, txn.id, folder.id)

    # doc1: 2건, doc2: 1건
    await _create_access_log(async_session, txn.id, document_id=doc1.id)
    await _create_access_log(async_session, txn.id, document_id=doc1.id)
    await _create_access_log(async_session, txn.id, document_id=doc2.id)
    await async_session.commit()

    logs, total = await vdr_access_service.get_document_access_logs(async_session, txn.id, doc1.id)
    assert total == 2
    assert len(logs) == 2
    assert all(log.document_id == doc1.id for log in logs)
