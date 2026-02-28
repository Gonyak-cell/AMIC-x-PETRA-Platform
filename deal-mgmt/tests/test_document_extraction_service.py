"""document_extraction_service 단위 테스트.

LLM 호출은 모두 mock 처리하여 외부 의존 없이 파이프라인 로직을 검증한다.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bid import Bid
from app.models.buyer_candidate import BuyerCandidate
from app.models.contract import Contract
from app.models.enums import (
    BidType,
    BuyerCandidateStatus,
    BuyerType,
    DocExtractionCategory,
    ExtractionStatus,
    TransactionSide,
    VdrDocumentStatus,
    VdrFolderCategory,
)
from app.models.nda import NDA
from app.models.transaction import Transaction
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.ralph.parsers.base import ParsedFile
from app.services.document_extraction_service import (
    _extract_json,
    classify_document,
    confirm_extraction,
    create_extraction,
    extract_fields,
    get_extraction,
    list_extractions,
)

pytestmark = pytest.mark.anyio


# ── 헬퍼 ──────────────────────────────────────────────────────


async def _make_txn(db: AsyncSession) -> Transaction:
    """테스트용 Transaction 생성."""
    txn = Transaction(
        name="Test Txn",
        code_name=f"T-{uuid.uuid4().hex[:8]}",
        side=TransactionSide.SELL,
        target_company_name="대상기업",
        client_name="의뢰기업",
        lead_advisor_email="test@example.com",
    )
    db.add(txn)
    await db.flush()
    return txn


async def _make_vdr_doc(db: AsyncSession, txn: Transaction) -> VdrDocument:
    """테스트용 VdrDocument 생성 (VdrFolder 포함)."""
    folder = VdrFolder(
        transaction_id=txn.id,
        name="테스트폴더",
        category=VdrFolderCategory.CORPORATE,
        is_required=False,
    )
    db.add(folder)
    await db.flush()
    doc = VdrDocument(
        transaction_id=txn.id,
        folder_id=folder.id,
        original_name="test.pdf",
        stored_name="stored_test.pdf",
        file_path="/tmp/test.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        status=VdrDocumentStatus.ACTIVE,
    )
    db.add(doc)
    await db.flush()
    return doc


async def _make_buyer(db: AsyncSession, txn: Transaction) -> BuyerCandidate:
    """테스트용 BuyerCandidate 생성."""
    buyer = BuyerCandidate(
        transaction_id=txn.id,
        company_name="매수후보사",
        buyer_type=BuyerType.STRATEGIC,
        status=BuyerCandidateStatus.IDENTIFIED,
    )
    db.add(buyer)
    await db.flush()
    return buyer


def _mock_llm_client(response: str = '{"category": "NDA", "confidence": 0.95}') -> MagicMock:
    """LLM 클라이언트 mock — call/call_with_model이 응답 문자열 반환."""
    client = MagicMock()
    client.is_available = True
    client.total_cost_usd = 0.001
    client.call = AsyncMock(return_value=response)
    client.call_with_model = AsyncMock(return_value=response)
    return client


# ── _extract_json ────────────────────────────────────────────


class TestExtractJson:
    def test_extract_from_json_block(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        assert _extract_json(text) == '{"key": "value"}'

    def test_extract_from_code_block(self) -> None:
        text = '```\n{"key": "value"}\n```'
        assert _extract_json(text) == '{"key": "value"}'

    def test_extract_from_braces(self) -> None:
        text = 'some text {"key": "value"} more text'
        assert _extract_json(text) == '{"key": "value"}'

    def test_plain_json(self) -> None:
        text = '{"key": "value"}'
        assert _extract_json(text) == '{"key": "value"}'

    def test_no_json(self) -> None:
        text = "no json here"
        assert _extract_json(text) == "no json here"


# ── CRUD ─────────────────────────────────────────────────────


class TestExtractionCrud:
    async def test_create_extraction_pending(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        assert ext.status == ExtractionStatus.PENDING
        assert ext.transaction_id == txn.id
        assert ext.vdr_document_id == vdr_doc.id
        assert ext.doc_category is None

    async def test_create_with_hint(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)

        ext = await create_extraction(async_session, txn.id, vdr_doc.id, DocExtractionCategory.NDA)
        assert ext.doc_category == DocExtractionCategory.NDA

    async def test_get_extraction(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)

        fetched = await get_extraction(async_session, ext.id)
        assert fetched is not None
        assert fetched.id == ext.id

    async def test_get_extraction_not_found(self, async_session: AsyncSession) -> None:
        result = await get_extraction(async_session, uuid.uuid4())
        assert result is None

    async def test_list_extractions(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        await create_extraction(async_session, txn.id, vdr_doc.id)
        await create_extraction(async_session, txn.id, vdr_doc.id)

        items = await list_extractions(async_session, txn.id)
        assert len(items) == 2

    async def test_list_extractions_isolation(self, async_session: AsyncSession) -> None:
        txn1 = await _make_txn(async_session)
        txn2 = await _make_txn(async_session)
        vdr1 = await _make_vdr_doc(async_session, txn1)
        vdr2 = await _make_vdr_doc(async_session, txn2)
        await create_extraction(async_session, txn1.id, vdr1.id)
        await create_extraction(async_session, txn2.id, vdr2.id)

        items = await list_extractions(async_session, txn1.id)
        assert len(items) == 1
        assert items[0].transaction_id == txn1.id


# ── classify_document ────────────────────────────────────────


class TestClassifyDocument:
    async def test_classify_nda(self) -> None:
        parsed = ParsedFile(source_path="/tmp/test.pdf", file_type="pdf")
        parsed.text = "비밀유지계약서 " * 100
        llm = _mock_llm_client('{"category": "NDA", "confidence": 0.95}')

        cat, conf = await classify_document(parsed, llm)
        assert cat == DocExtractionCategory.NDA
        assert conf == pytest.approx(0.95)

    async def test_classify_empty_text(self) -> None:
        parsed = ParsedFile(source_path="/tmp/empty.pdf", file_type="pdf")
        parsed.text = "   "

        llm = _mock_llm_client()
        cat, conf = await classify_document(parsed, llm)
        assert cat == DocExtractionCategory.REFERENCE_ONLY
        assert conf == 0.5

    async def test_classify_invalid_json_fallback(self) -> None:
        parsed = ParsedFile(source_path="/tmp/test.pdf", file_type="pdf")
        parsed.text = "some text content " * 50
        llm = _mock_llm_client("not a json response")

        cat, conf = await classify_document(parsed, llm)
        assert cat == DocExtractionCategory.REFERENCE_ONLY
        assert conf == 0.3

    async def test_classify_unknown_category_fallback(self) -> None:
        parsed = ParsedFile(source_path="/tmp/test.pdf", file_type="pdf")
        parsed.text = "some text content " * 50
        llm = _mock_llm_client('{"category": "UNKNOWN_TYPE", "confidence": 0.8}')

        cat, conf = await classify_document(parsed, llm)
        assert cat == DocExtractionCategory.REFERENCE_ONLY
        assert conf == 0.3

    async def test_classify_confidence_clamped(self) -> None:
        parsed = ParsedFile(source_path="/tmp/test.pdf", file_type="pdf")
        parsed.text = "계약서 내용 " * 50
        llm = _mock_llm_client('{"category": "SPA_BTA", "confidence": 1.5}')

        cat, conf = await classify_document(parsed, llm)
        assert cat == DocExtractionCategory.SPA_BTA
        assert conf == 1.0


# ── extract_fields ───────────────────────────────────────────


class TestExtractFields:
    async def test_extract_nda_fields(self) -> None:
        parsed = ParsedFile(source_path="/tmp/nda.pdf", file_type="pdf")
        parsed.text = "NDA 문서 내용 " * 100
        response = '{"counterparty_name": "테스트사", "nda_type": "MUTUAL"}'
        llm = _mock_llm_client(response)

        result = await extract_fields(parsed, DocExtractionCategory.NDA, llm)
        assert result["counterparty_name"] == "테스트사"
        assert result["nda_type"] == "MUTUAL"

    async def test_extract_reference_only_skipped(self) -> None:
        parsed = ParsedFile(source_path="/tmp/ref.pdf", file_type="pdf")
        parsed.text = "참고 문서"
        llm = _mock_llm_client()

        result = await extract_fields(parsed, DocExtractionCategory.REFERENCE_ONLY, llm)
        assert result == {}

    async def test_extract_empty_text_returns_empty(self) -> None:
        parsed = ParsedFile(source_path="/tmp/empty.pdf", file_type="pdf")
        parsed.text = "   "
        llm = _mock_llm_client()

        result = await extract_fields(parsed, DocExtractionCategory.NDA, llm)
        assert result == {}

    async def test_extract_invalid_json_returns_empty(self) -> None:
        parsed = ParsedFile(source_path="/tmp/test.pdf", file_type="pdf")
        parsed.text = "NDA 문서 " * 100
        llm = _mock_llm_client("invalid json response")

        result = await extract_fields(parsed, DocExtractionCategory.NDA, llm)
        assert result == {}


# ── confirm_extraction + _apply_to_nda ───────────────────────


class TestConfirmNda:
    async def test_confirm_creates_nda(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        buyer = await _make_buyer(async_session, txn)

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        ext.extracted_data = {"counterparty_name": "테스트사"}
        await async_session.flush()

        updated = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={
                "counterparty_name": "테스트사",
                "buyer_candidate_id": str(buyer.id),
                "jurisdiction": "서울중앙지방법원",
            },
            target_model="nda",
            target_id=None,
            create_new=True,
            user_email="test@example.com",
        )
        assert updated.status == ExtractionStatus.CONFIRMED
        assert updated.target_model == "nda"
        assert updated.target_id is not None

        nda = await async_session.get(NDA, updated.target_id)
        assert nda is not None
        assert nda.counterparty_name == "테스트사"
        assert nda.jurisdiction == "서울중앙지방법원"

    async def test_confirm_nda_update_existing(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        buyer = await _make_buyer(async_session, txn)

        nda = NDA(
            transaction_id=txn.id,
            buyer_candidate_id=buyer.id,
            counterparty_name="기존 상대방",
        )
        async_session.add(nda)
        await async_session.flush()

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        updated = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"counterparty_name": "변경된 상대방"},
            target_model="nda",
            target_id=nda.id,
            create_new=False,
            user_email="test@example.com",
        )
        assert updated.target_id == nda.id

        await async_session.refresh(nda)
        assert nda.counterparty_name == "변경된 상대방"

    async def test_confirm_nda_null_guard(self, async_session: AsyncSession) -> None:
        """data에 없는 필드는 기존 값을 덮어쓰지 않는다."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        buyer = await _make_buyer(async_session, txn)

        nda = NDA(
            transaction_id=txn.id,
            buyer_candidate_id=buyer.id,
            counterparty_name="기존 상대방",
            jurisdiction="서울중앙지방법원",
        )
        async_session.add(nda)
        await async_session.flush()

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        # jurisdiction 키를 보내지 않으면 기존값 유지
        await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"counterparty_name": "신규 상대방"},
            target_model="nda",
            target_id=nda.id,
            create_new=False,
            user_email="test@example.com",
        )
        await async_session.refresh(nda)
        assert nda.counterparty_name == "신규 상대방"
        assert nda.jurisdiction == "서울중앙지방법원"  # 덮어쓰지 않음

    async def test_confirm_nda_create_no_buyer_fails(self, async_session: AsyncSession) -> None:
        """buyer_candidate_id 없이 create_new=True → ValueError."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        with pytest.raises(ValueError, match="데이터 적용 실패"):
            await confirm_extraction(
                db=async_session,
                extraction_id=ext.id,
                confirmed_data={"counterparty_name": "테스트사"},
                target_model="nda",
                target_id=None,
                create_new=True,
                user_email="test@example.com",
            )

    async def test_confirm_nda_cross_txn_buyer_fails(self, async_session: AsyncSession) -> None:
        """다른 거래의 buyer_candidate_id로 NDA 생성 → ValueError."""
        txn1 = await _make_txn(async_session)
        txn2 = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn1)
        buyer_other = await _make_buyer(async_session, txn2)

        ext = await create_extraction(async_session, txn1.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        with pytest.raises(ValueError, match="데이터 적용 실패"):
            await confirm_extraction(
                db=async_session,
                extraction_id=ext.id,
                confirmed_data={
                    "counterparty_name": "테스트사",
                    "buyer_candidate_id": str(buyer_other.id),
                },
                target_model="nda",
                target_id=None,
                create_new=True,
                user_email="test@example.com",
            )


# ── confirm_extraction + _apply_to_bid ───────────────────────


class TestConfirmBid:
    async def test_confirm_creates_bid(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        buyer = await _make_buyer(async_session, txn)

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        updated = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={
                "buyer_candidate_id": str(buyer.id),
                "proposed_amount": 50000000000,
                "currency": "KRW",
            },
            target_model="bid",
            target_id=None,
            create_new=True,
            user_email="test@example.com",
        )
        assert updated.target_id is not None

        bid = await async_session.get(Bid, updated.target_id)
        assert bid is not None
        assert bid.bid_type == BidType.LOI  # 기본값
        assert bid.currency == "KRW"

    async def test_confirm_bid_update_existing(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        buyer = await _make_buyer(async_session, txn)

        bid = Bid(
            transaction_id=txn.id,
            buyer_candidate_id=buyer.id,
            bid_type=BidType.LOI,
            currency="KRW",
        )
        async_session.add(bid)
        await async_session.flush()

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        updated = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"proposed_amount": 99999999999, "valid_until": "2026-12-31"},
            target_model="bid",
            target_id=bid.id,
            create_new=False,
            user_email="test@example.com",
        )
        assert updated.target_id == bid.id

        await async_session.refresh(bid)
        assert bid.valid_until == "2026-12-31"

    async def test_confirm_bid_null_guard(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        buyer = await _make_buyer(async_session, txn)

        bid = Bid(
            transaction_id=txn.id,
            buyer_candidate_id=buyer.id,
            bid_type=BidType.LOI,
            currency="USD",
            valid_until="2026-06-30",
        )
        async_session.add(bid)
        await async_session.flush()

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        # currency만 보내면 valid_until 유지
        await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"currency": "EUR"},
            target_model="bid",
            target_id=bid.id,
            create_new=False,
            user_email="test@example.com",
        )
        await async_session.refresh(bid)
        assert bid.currency == "EUR"
        assert bid.valid_until == "2026-06-30"


# ── confirm_extraction + _apply_to_contract ──────────────────


class TestConfirmContract:
    async def test_confirm_creates_contract(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        updated = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={
                "counterparty_name": "매수인",
                "closing_date": "2026-12-31",
                "risk_summary": "주요 리스크 없음",
            },
            target_model="contract",
            target_id=None,
            create_new=True,
            user_email="test@example.com",
        )
        assert updated.target_id is not None

        contract = await async_session.get(Contract, updated.target_id)
        assert contract is not None
        assert contract.title == "AI 추출 계약서"
        assert contract.counterparty_name == "매수인"
        assert contract.expiry_date == "2026-12-31"  # closing_date → expiry_date
        assert contract.ai_analysis_summary == "주요 리스크 없음"

    async def test_confirm_contract_with_risk_flags(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        updated = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={
                "rw_cap_amount": 1000000000,
                "rw_cap_percentage": 20,
                "key_conditions": ["주요 조건1"],
            },
            target_model="contract",
            target_id=None,
            create_new=True,
            user_email="test@example.com",
        )
        contract = await async_session.get(Contract, updated.target_id)
        assert contract is not None
        assert contract.ai_risk_flags is not None
        assert contract.ai_risk_flags["rw_cap_amount"] == 1000000000
        assert contract.ai_risk_flags["rw_cap_percentage"] == 20

    async def test_confirm_contract_null_guard(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)

        contract = Contract(
            transaction_id=txn.id,
            title="기존 계약서",
            counterparty_name="기존 상대방",
            ai_analysis_summary="기존 분석",
        )
        async_session.add(contract)
        await async_session.flush()

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        # counterparty_name만 보내면 ai_analysis_summary 유지
        await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"counterparty_name": "신규 상대방"},
            target_model="contract",
            target_id=contract.id,
            create_new=False,
            user_email="test@example.com",
        )
        await async_session.refresh(contract)
        assert contract.counterparty_name == "신규 상대방"
        assert contract.ai_analysis_summary == "기존 분석"  # 덮어쓰지 않음

    async def test_confirm_contract_custom_title(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        updated = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"title": "주식매매계약서"},
            target_model="contract",
            target_id=None,
            create_new=True,
            user_email="test@example.com",
        )
        contract = await async_session.get(Contract, updated.target_id)
        assert contract is not None
        assert contract.title == "주식매매계약서"


# ── confirm_extraction + _apply_to_transaction ───────────────


class TestConfirmTransaction:
    async def test_confirm_corporate_docs(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        updated = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={
                "company_name": "테스트주식회사",
                "representative_name": "홍길동",
                "capital_amount": 500000000,
            },
            target_model="transaction",
            target_id=None,
            create_new=False,
            user_email="test@example.com",
        )
        assert updated.status == ExtractionStatus.CONFIRMED

        await async_session.refresh(txn)
        assert txn.corporate_info is not None
        assert txn.corporate_info["company_name"] == "테스트주식회사"
        assert txn.corporate_info["representative_name"] == "홍길동"

    async def test_confirm_financial_data(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={
                "fiscal_year": "2025",
                "revenue": 10000000000,
                "net_income": 1000000000,
            },
            target_model="transaction",
            target_id=None,
            create_new=False,
            user_email="test@example.com",
        )
        await async_session.refresh(txn)
        assert txn.financial_summary is not None
        assert txn.financial_summary["revenue"] == 10000000000

    async def test_confirm_transaction_merge(self, async_session: AsyncSession) -> None:
        """기존 corporate_info에 새 데이터를 머지한다."""
        txn = await _make_txn(async_session)
        txn.corporate_info = {"company_name": "기존회사"}
        await async_session.flush()

        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"representative_name": "신규 대표"},
            target_model="transaction",
            target_id=None,
            create_new=False,
            user_email="test@example.com",
        )
        await async_session.refresh(txn)
        assert txn.corporate_info["company_name"] == "기존회사"  # 기존 유지
        assert txn.corporate_info["representative_name"] == "신규 대표"  # 새로 추가


# ── confirm_extraction 에러 케이스 ───────────────────────────


class TestConfirmErrors:
    async def test_confirm_nonexistent_extraction(self, async_session: AsyncSession) -> None:
        with pytest.raises(ValueError, match="추출 레코드 없음"):
            await confirm_extraction(
                db=async_session,
                extraction_id=uuid.uuid4(),
                confirmed_data={},
                target_model="nda",
                target_id=None,
                create_new=False,
                user_email="test@example.com",
            )

    async def test_confirm_pending_status_fails(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)

        with pytest.raises(ValueError, match="확정 불가 상태"):
            await confirm_extraction(
                db=async_session,
                extraction_id=ext.id,
                confirmed_data={},
                target_model="nda",
                target_id=None,
                create_new=False,
                user_email="test@example.com",
            )

    async def test_confirm_unsupported_model(self, async_session: AsyncSession) -> None:
        """지원하지 않는 target_model → 정상 완료 (target_id=None)."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        updated = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"some_key": "value"},
            target_model="unknown_model",
            target_id=None,
            create_new=False,
            user_email="test@example.com",
        )
        assert updated.status == ExtractionStatus.CONFIRMED
        assert updated.target_id is None


# ── run_extraction_pipeline ──────────────────────────────────


class TestPipeline:
    async def test_pipeline_full_nda(self, async_session: AsyncSession) -> None:
        """NDA 문서의 전체 파이프라인 (분류→추출→완료)."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        await async_session.commit()

        mock_parsed = ParsedFile(source_path="/tmp/nda.pdf", file_type="pdf")
        mock_parsed.text = "NDA 비밀유지계약서 " * 200

        classify_resp = '{"category": "NDA", "confidence": 0.92}'
        extract_resp = '{"counterparty_name": "테스트사", "nda_type": "MUTUAL"}'

        llm = _mock_llm_client()
        # call_with_model: 분류에 사용, call: 추출에 사용
        llm.call_with_model = AsyncMock(return_value=classify_resp)
        llm.call = AsyncMock(return_value=extract_resp)

        with (
            patch(
                "app.services.document_extraction_service.blob_client",
                ensure_initialized=AsyncMock(),
                download_blob=AsyncMock(return_value=b"fake pdf bytes"),
            ),
            patch(
                "app.services.document_extraction_service.parse_file",
                return_value=mock_parsed,
            ),
            patch(
                "app.services.document_extraction_service.RalphLLMClient.from_settings",
                return_value=llm,
            ),
        ):
            from app.services.document_extraction_service import _run_pipeline_inner

            await _run_pipeline_inner(async_session, ext.id, MagicMock(), 0.0)

        await async_session.refresh(ext)
        assert ext.status == ExtractionStatus.COMPLETED
        assert ext.doc_category == DocExtractionCategory.NDA
        assert ext.extracted_data is not None
        assert ext.extracted_data["counterparty_name"] == "테스트사"

    async def test_pipeline_reference_only_no_extraction(self, async_session: AsyncSession) -> None:
        """REFERENCE_ONLY 분류 → 추출 건너뜀."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        await async_session.commit()

        mock_parsed = ParsedFile(source_path="/tmp/ref.pdf", file_type="pdf")
        mock_parsed.text = "참고 문서 내용 " * 200

        llm = _mock_llm_client()
        llm.call_with_model = AsyncMock(return_value='{"category": "REFERENCE_ONLY", "confidence": 0.85}')

        with (
            patch(
                "app.services.document_extraction_service.blob_client",
                ensure_initialized=AsyncMock(),
                download_blob=AsyncMock(return_value=b"fake pdf bytes"),
            ),
            patch(
                "app.services.document_extraction_service.parse_file",
                return_value=mock_parsed,
            ),
            patch(
                "app.services.document_extraction_service.RalphLLMClient.from_settings",
                return_value=llm,
            ),
        ):
            from app.services.document_extraction_service import _run_pipeline_inner

            await _run_pipeline_inner(async_session, ext.id, MagicMock(), 0.0)

        await async_session.refresh(ext)
        assert ext.status == ExtractionStatus.COMPLETED
        assert ext.doc_category == DocExtractionCategory.REFERENCE_ONLY
        assert ext.extracted_data is None  # 추출 건너뜀

    async def test_pipeline_hint_skips_classification(self, async_session: AsyncSession) -> None:
        """doc_category hint가 있으면 분류 건너뛰기."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id, DocExtractionCategory.NDA)
        await async_session.commit()

        mock_parsed = ParsedFile(source_path="/tmp/nda.pdf", file_type="pdf")
        mock_parsed.text = "NDA 비밀유지계약서 " * 200

        extract_resp = '{"counterparty_name": "테스트사"}'
        llm = _mock_llm_client(extract_resp)

        with (
            patch(
                "app.services.document_extraction_service.blob_client",
                ensure_initialized=AsyncMock(),
                download_blob=AsyncMock(return_value=b"fake pdf bytes"),
            ),
            patch(
                "app.services.document_extraction_service.parse_file",
                return_value=mock_parsed,
            ),
            patch(
                "app.services.document_extraction_service.RalphLLMClient.from_settings",
                return_value=llm,
            ),
        ):
            from app.services.document_extraction_service import _run_pipeline_inner

            await _run_pipeline_inner(async_session, ext.id, MagicMock(), 0.0)

        await async_session.refresh(ext)
        assert ext.status == ExtractionStatus.COMPLETED
        assert ext.classification_confidence == 1.0  # hint 사용

        # classify는 호출되지 않음 (call_with_model은 extract에서만 사용)
        # call이 추출에서 호출됨
        assert llm.call.call_count >= 1

    async def test_pipeline_parse_failure(self, async_session: AsyncSession) -> None:
        """파일 파싱 실패 → FAILED."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        await async_session.commit()

        with (
            patch(
                "app.services.document_extraction_service.blob_client",
                ensure_initialized=AsyncMock(),
                download_blob=AsyncMock(return_value=b"fake pdf bytes"),
            ),
            patch(
                "app.services.document_extraction_service.parse_file",
                side_effect=RuntimeError("파싱 에러"),
            ),
            patch(
                "app.services.document_extraction_service.RalphLLMClient.from_settings",
                return_value=_mock_llm_client(),
            ),
        ):
            from app.services.document_extraction_service import _run_pipeline_inner

            await _run_pipeline_inner(async_session, ext.id, MagicMock(), 0.0)

        await async_session.refresh(ext)
        assert ext.status == ExtractionStatus.FAILED
        assert "파싱" in (ext.error_message or "")

    async def test_pipeline_llm_unavailable(self, async_session: AsyncSession) -> None:
        """LLM 클라이언트 사용 불가 → FAILED."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        await async_session.commit()

        mock_parsed = ParsedFile(source_path="/tmp/test.pdf", file_type="pdf")
        mock_parsed.text = "문서 내용 " * 100

        llm = _mock_llm_client()
        llm.is_available = False

        with (
            patch(
                "app.services.document_extraction_service.blob_client",
                ensure_initialized=AsyncMock(),
                download_blob=AsyncMock(return_value=b"fake pdf bytes"),
            ),
            patch(
                "app.services.document_extraction_service.parse_file",
                return_value=mock_parsed,
            ),
            patch(
                "app.services.document_extraction_service.RalphLLMClient.from_settings",
                return_value=llm,
            ),
        ):
            from app.services.document_extraction_service import _run_pipeline_inner

            await _run_pipeline_inner(async_session, ext.id, MagicMock(), 0.0)

        await async_session.refresh(ext)
        assert ext.status == ExtractionStatus.FAILED
        assert "AI 분석 서비스" in (ext.error_message or "")

    async def test_pipeline_idempotent_skip(self, async_session: AsyncSession) -> None:
        """이미 COMPLETED인 추출은 스킵한다."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.commit()

        with (
            patch(
                "app.services.document_extraction_service.parse_file",
            ) as mock_parse,
            patch(
                "app.services.document_extraction_service.RalphLLMClient.from_settings",
                return_value=_mock_llm_client(),
            ),
        ):
            from app.services.document_extraction_service import _run_pipeline_inner

            await _run_pipeline_inner(async_session, ext.id, MagicMock(), 0.0)

        # 파싱 호출 없음 (COMPLETED이므로 스킵)
        mock_parse.assert_not_called()
