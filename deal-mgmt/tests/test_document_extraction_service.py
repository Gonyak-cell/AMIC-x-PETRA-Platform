"""document_extraction_service 단위 테스트.

LLM 호출은 모두 mock 처리하여 외부 의존 없이 파이프라인 로직을 검증한다.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attachment import Attachment
from app.models.bid import Bid
from app.models.buyer_candidate import BuyerCandidate
from app.models.contract import Contract
from app.models.engagement import Engagement
from app.models.enums import (
    BidType,
    BuyerCandidateStatus,
    BuyerType,
    DocExtractionCategory,
    EngagementType,
    ExtractionStatus,
    MarketingDocType,
    NdaPartyType,
    NdaType,
    TransactionSide,
    ValuationMethod,
    VdrDocumentStatus,
    VdrFolderCategory,
)
from app.models.marketing_material import MarketingMaterial
from app.models.nda import NDA
from app.models.transaction import Transaction
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.ralph.parsers.base import ParsedFile
from app.services.document_extraction_service import (
    _STRING_LIMITS,
    _extract_json,
    _safe_enum_value,
    _safe_set_field,
    classify_document,
    confirm_extraction,
    create_extraction,
    extract_fields,
    get_extraction,
    has_active_extraction,
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


async def _make_attachment(
    db: AsyncSession,
    txn: Transaction,
    *,
    entity_type: str,
    entity_id: str | None = None,
    vdr_doc: VdrDocument | None = None,
    file_name: str = "uploaded.pdf",
    mime_type: str = "application/pdf",
) -> Attachment:
    attachment = Attachment(
        transaction_id=txn.id,
        entity_type=entity_type,
        entity_id=entity_id,
        file_path=f"/tmp/{file_name}",
        file_name=file_name,
        file_size_bytes=2048,
        mime_type=mime_type,
        vdr_document_id=vdr_doc.id if vdr_doc else None,
        uploaded_by_email="upload@example.com",
    )
    db.add(attachment)
    await db.flush()
    return attachment


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


# ── _safe_enum_value ─────────────────────────────────────────


class TestSafeEnumValue:
    def test_none_returns_none(self) -> None:
        assert _safe_enum_value(BidType, None) is None

    def test_valid_string(self) -> None:
        result = _safe_enum_value(BidType, "LOI")
        assert result == BidType.LOI

    def test_invalid_string_returns_none(self) -> None:
        result = _safe_enum_value(BidType, "NONEXISTENT")
        assert result is None

    def test_valid_nda_type(self) -> None:
        result = _safe_enum_value(NdaType, "MUTUAL")
        assert result == NdaType.MUTUAL

    def test_valid_valuation_method(self) -> None:
        result = _safe_enum_value(ValuationMethod, "DCF")
        assert result == ValuationMethod.DCF

    def test_empty_string_returns_none(self) -> None:
        result = _safe_enum_value(BidType, "")
        assert result is None


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


# ── has_active_extraction ────────────────────────────────────


class TestHasActiveExtraction:
    async def test_detects_pending(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        await create_extraction(async_session, txn.id, vdr_doc.id)

        result = await has_active_extraction(async_session, vdr_doc.id)
        assert result is not None

    async def test_detects_completed(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        result = await has_active_extraction(async_session, vdr_doc.id)
        assert result is not None

    async def test_allows_retry_after_failed(self, async_session: AsyncSession) -> None:
        """FAILED 상태는 활성으로 간주하지 않아 재시도를 허용한다."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.FAILED
        await async_session.flush()

        result = await has_active_extraction(async_session, vdr_doc.id)
        assert result is None

    async def test_isolation_by_vdr_doc(self, async_session: AsyncSession) -> None:
        """다른 VDR 문서의 추출은 감지하지 않는다."""
        txn = await _make_txn(async_session)
        vdr_doc1 = await _make_vdr_doc(async_session, txn)
        vdr_doc2 = await _make_vdr_doc(async_session, txn)
        await create_extraction(async_session, txn.id, vdr_doc1.id)

        result = await has_active_extraction(async_session, vdr_doc2.id)
        assert result is None

    async def test_no_extraction_returns_none(self, async_session: AsyncSession) -> None:
        result = await has_active_extraction(async_session, uuid.uuid4())
        assert result is None


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

    async def test_extract_engagement_contract_fields(self) -> None:
        parsed = ParsedFile(source_path="/tmp/engagement.pdf", file_type="pdf")
        parsed.text = "Engagement agreement " * 150
        response = (
            '{"type": "EXCLUSIVE", "counterparty_name": "Client Co", '
            '"service_scope_summary": "Sell-side advisory", '
            '"fee_structure": {"retainer_fee": 100000000}}'
        )
        llm = _mock_llm_client(response)

        result = await extract_fields(parsed, DocExtractionCategory.ENGAGEMENT_CONTRACT, llm)

        assert result["type"] == "EXCLUSIVE"
        assert result["counterparty_name"] == "Client Co"
        assert result["fee_structure"]["retainer_fee"] == 100000000

    async def test_extract_teaser_im_fields(self) -> None:
        parsed = ParsedFile(source_path="/tmp/im.pdf", file_type="pdf")
        parsed.text = "Information memorandum " * 150
        response = '{"doc_type": "IM", "title": "Project Alpha IM", "project_code": "ALPHA"}'
        llm = _mock_llm_client(response)

        result = await extract_fields(parsed, DocExtractionCategory.TEASER_IM, llm)

        assert result["doc_type"] == "IM"
        assert result["title"] == "Project Alpha IM"
        assert result["project_code"] == "ALPHA"

    async def test_extract_registry_docs_fields(self) -> None:
        parsed = ParsedFile(source_path="/tmp/registry.pdf", file_type="pdf")
        parsed.text = "법인등기부등본 문서 내용 " * 200
        response = '{"company_name": "테스트 주식회사", "corporate_registration_number": "110111-1234567"}'
        llm = _mock_llm_client(response)

        result = await extract_fields(parsed, DocExtractionCategory.REGISTRY_DOCS, llm)

        assert result["company_name"] == "테스트 주식회사"
        assert result["corporate_registration_number"] == "110111-1234567"
        llm.call_with_model.assert_awaited()

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

    async def test_confirm_nda_invalid_nda_type_ignored(self, async_session: AsyncSession) -> None:
        """무효한 nda_type 문자열은 무시되고 기본값이 유지된다."""
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
                "counterparty_name": "테스트사",
                "buyer_candidate_id": str(buyer.id),
                "nda_type": "INVALID_TYPE",
            },
            target_model="nda",
            target_id=None,
            create_new=True,
            user_email="test@example.com",
        )
        nda = await async_session.get(NDA, updated.target_id)
        assert nda is not None
        assert nda.nda_type == NdaType.MUTUAL  # 무효값 무시 → 기본값

    async def test_confirm_nda_update_valid_nda_type(self, async_session: AsyncSession) -> None:
        """기존 NDA의 nda_type을 유효한 값으로 변경할 수 있다."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        buyer = await _make_buyer(async_session, txn)

        nda = NDA(
            transaction_id=txn.id,
            buyer_candidate_id=buyer.id,
            counterparty_name="기존 상대방",
            nda_type=NdaType.MUTUAL,
        )
        async_session.add(nda)
        await async_session.flush()

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"nda_type": "ONE_WAY"},
            target_model="nda",
            target_id=nda.id,
            create_new=False,
            user_email="test@example.com",
        )
        await async_session.refresh(nda)
        assert nda.nda_type == NdaType.ONE_WAY

    # ── confirm_extraction + _apply_to_bid ───────────────────────

    async def test_confirm_creates_client_nda_without_buyer(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        updated = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={
                "party_type": "CLIENT",
                "counterparty_name": "Client Co",
                "nda_type": "MUTUAL",
            },
            target_model="nda",
            target_id=None,
            create_new=True,
            user_email="test@example.com",
        )

        nda = await async_session.get(NDA, updated.target_id)
        assert nda is not None
        assert nda.party_type == NdaPartyType.CLIENT
        assert nda.buyer_candidate_id is None
        assert nda.counterparty_name == "Client Co"


class TestConfirmEngagement:
    async def test_confirm_creates_engagement(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        updated = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={
                "type": "EXCLUSIVE",
                "counterparty_name": "Client Co",
                "signed_at": "2026-03-01",
                "expires_at": "2026-12-31",
                "service_scope_summary": "Sell-side advisory",
                "fee_structure": {
                    "retainer_fee": 100000000,
                    "success_fee_rate": 3.5,
                },
                "notes": "Key coverage terms",
            },
            target_model="engagement",
            target_id=None,
            create_new=True,
            user_email="test@example.com",
        )

        engagement = await async_session.get(Engagement, updated.target_id)
        assert engagement is not None
        assert engagement.type == EngagementType.EXCLUSIVE
        assert engagement.counterparty_name == "Client Co"
        assert engagement.service_scope_summary == "Sell-side advisory"
        assert engagement.fee_structure["retainer_fee"] == 100000000
        assert engagement.fee_structure["success_fee_rate"] == 3.5


class TestConfirmMarketingMaterial:
    async def test_confirm_creates_uploaded_marketing_material(self, async_session: AsyncSession) -> None:
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        attachment = await _make_attachment(
            async_session,
            txn,
            entity_type="MARKETING_MATERIAL",
            entity_id="IM",
            vdr_doc=vdr_doc,
            file_name="project-alpha-im.pdf",
        )

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        updated = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={
                "doc_type": "IM",
                "title": "Project Alpha IM",
                "project_code": "ALPHA",
            },
            target_model="marketing_material",
            target_id=None,
            create_new=True,
            user_email="test@example.com",
        )

        material = await async_session.get(MarketingMaterial, updated.target_id)
        assert material is not None
        assert material.doc_type == MarketingDocType.IM
        assert material.source_mode == "UPLOADED"
        assert material.attachment_id == attachment.id
        assert material.file_name == attachment.file_name
        assert material.status.value == "READY"
        assert material.quality_status == "SKIPPED"


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

    async def test_confirm_bid_null_bid_type_defaults_loi(self, async_session: AsyncSession) -> None:
        """bid_type=None 전달 시 LOI 기본값으로 폴백한다."""
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
                "bid_type": None,
                "proposed_amount": 10000000000,
            },
            target_model="bid",
            target_id=None,
            create_new=True,
            user_email="test@example.com",
        )
        bid = await async_session.get(Bid, updated.target_id)
        assert bid is not None
        assert bid.bid_type == BidType.LOI  # None → LOI 폴백

    async def test_confirm_bid_explicit_bid_type(self, async_session: AsyncSession) -> None:
        """명시적 bid_type 전달 시 해당 값으로 설정된다."""
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
                "bid_type": "FINAL_OFFER",
            },
            target_model="bid",
            target_id=None,
            create_new=True,
            user_email="test@example.com",
        )
        bid = await async_session.get(Bid, updated.target_id)
        assert bid is not None
        assert bid.bid_type == BidType.FINAL_OFFER

    async def test_confirm_bid_update_bid_type(self, async_session: AsyncSession) -> None:
        """기존 Bid의 bid_type을 업데이트할 수 있다."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        buyer = await _make_buyer(async_session, txn)

        bid = Bid(
            transaction_id=txn.id,
            buyer_candidate_id=buyer.id,
            bid_type=BidType.LOI,
        )
        async_session.add(bid)
        await async_session.flush()

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"bid_type": "FINAL_OFFER"},
            target_model="bid",
            target_id=bid.id,
            create_new=False,
            user_email="test@example.com",
        )
        await async_session.refresh(bid)
        assert bid.bid_type == BidType.FINAL_OFFER

    async def test_confirm_bid_update_valuation_method(self, async_session: AsyncSession) -> None:
        """기존 Bid에 valuation_method를 설정할 수 있다."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        buyer = await _make_buyer(async_session, txn)

        bid = Bid(
            transaction_id=txn.id,
            buyer_candidate_id=buyer.id,
            bid_type=BidType.LOI,
        )
        async_session.add(bid)
        await async_session.flush()

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"valuation_method": "DCF"},
            target_model="bid",
            target_id=bid.id,
            create_new=False,
            user_email="test@example.com",
        )
        await async_session.refresh(bid)
        assert bid.valuation_method == ValuationMethod.DCF

    async def test_confirm_bid_invalid_bid_type_ignored(self, async_session: AsyncSession) -> None:
        """무효한 bid_type은 무시되고 기존 값이 유지된다."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        buyer = await _make_buyer(async_session, txn)

        bid = Bid(
            transaction_id=txn.id,
            buyer_candidate_id=buyer.id,
            bid_type=BidType.LOI,
        )
        async_session.add(bid)
        await async_session.flush()

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"bid_type": "NONEXISTENT_TYPE"},
            target_model="bid",
            target_id=bid.id,
            create_new=False,
            user_email="test@example.com",
        )
        await async_session.refresh(bid)
        assert bid.bid_type == BidType.LOI  # 무효값 무시 → 기존값 유지


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
                "currency": "KRW",
                "contract_type": "SPA",
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
        assert contract.ai_risk_flags["currency"] == "KRW"
        assert contract.ai_risk_flags["contract_type"] == "SPA"

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

    async def test_confirm_contract_risk_flags_merge(self, async_session: AsyncSession) -> None:
        """기존 ai_risk_flags에 새 플래그를 머지한다 (기존 키 보존)."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)

        contract = Contract(
            transaction_id=txn.id,
            title="기존 계약서",
            ai_risk_flags={"rw_cap_amount": 500000000, "currency": "KRW"},
        )
        async_session.add(contract)
        await async_session.flush()

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={
                "rw_cap_percentage": 15,
                "contract_type": "SPA",
            },
            target_model="contract",
            target_id=contract.id,
            create_new=False,
            user_email="test@example.com",
        )
        await async_session.refresh(contract)
        assert contract.ai_risk_flags["rw_cap_amount"] == 500000000  # 기존 유지
        assert contract.ai_risk_flags["currency"] == "KRW"  # 기존 유지
        assert contract.ai_risk_flags["rw_cap_percentage"] == 15  # 새로 추가
        assert contract.ai_risk_flags["contract_type"] == "SPA"  # 새로 추가


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

    async def test_reconfirm_changes_target(self, async_session: AsyncSession) -> None:
        """CONFIRMED 상태에서 다른 target_model로 재확정할 수 있다."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)

        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        await async_session.flush()

        # 1차 확정: transaction
        first = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"company_name": "테스트사"},
            target_model="transaction",
            target_id=None,
            create_new=False,
            user_email="first@example.com",
        )
        assert first.status == ExtractionStatus.CONFIRMED
        assert first.target_model == "transaction"

        # 2차 확정 (재확정): contract로 변경
        second = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={"counterparty_name": "변경 상대방"},
            target_model="contract",
            target_id=None,
            create_new=True,
            user_email="second@example.com",
        )
        assert second.status == ExtractionStatus.CONFIRMED
        assert second.target_model == "contract"
        assert second.target_id is not None
        assert second.reviewed_by_email == "second@example.com"


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
                download_blob_to_file=AsyncMock(),
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
            from app.services.document_extraction_service import _run_pipeline_core

            await _run_pipeline_core(async_session, ext.id, MagicMock(), 0.0)

        await async_session.refresh(ext)
        assert ext.status == ExtractionStatus.COMPLETED
        assert ext.doc_category == DocExtractionCategory.NDA
        assert ext.extracted_data is not None
        assert ext.extracted_data["counterparty_name"] == "테스트사"

    async def test_pipeline_registry_docs_runs_extraction(self, async_session: AsyncSession) -> None:
        """REGISTRY_DOCS 분류도 추출 단계까지 진행한다."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        await async_session.commit()

        mock_parsed = ParsedFile(source_path="/tmp/registry.pdf", file_type="pdf")
        mock_parsed.text = "법인등기부등본 문서 내용 " * 200

        classify_resp = '{"category": "REGISTRY_DOCS", "confidence": 0.99}'
        extract_resp = '{"company_name": "테스트 주식회사", "representative_name": "홍길동"}'

        llm = _mock_llm_client()
        llm.call_with_model = AsyncMock(side_effect=[classify_resp, extract_resp])
        llm.call = AsyncMock(return_value=extract_resp)

        with (
            patch(
                "app.services.document_extraction_service.blob_client",
                ensure_initialized=AsyncMock(),
                download_blob_to_file=AsyncMock(),
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
            from app.services.document_extraction_service import _run_pipeline_core

            await _run_pipeline_core(async_session, ext.id, MagicMock(), 0.0)

        await async_session.refresh(ext)
        assert ext.status == ExtractionStatus.COMPLETED
        assert ext.doc_category == DocExtractionCategory.REGISTRY_DOCS
        assert ext.extracted_data is not None
        assert ext.extracted_data["company_name"] == "테스트 주식회사"
        assert ext.error_message is None

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
                download_blob_to_file=AsyncMock(),
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
            from app.services.document_extraction_service import _run_pipeline_core

            await _run_pipeline_core(async_session, ext.id, MagicMock(), 0.0)

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
                download_blob_to_file=AsyncMock(),
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
            from app.services.document_extraction_service import _run_pipeline_core

            await _run_pipeline_core(async_session, ext.id, MagicMock(), 0.0)

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
                download_blob_to_file=AsyncMock(),
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
            from app.services.document_extraction_service import _run_pipeline_core

            await _run_pipeline_core(async_session, ext.id, MagicMock(), 0.0)

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
                download_blob_to_file=AsyncMock(),
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
            from app.services.document_extraction_service import _run_pipeline_core

            await _run_pipeline_core(async_session, ext.id, MagicMock(), 0.0)

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
            from app.services.document_extraction_service import _run_pipeline_core

            await _run_pipeline_core(async_session, ext.id, MagicMock(), 0.0)

        # 파싱 호출 없음 (COMPLETED이므로 스킵)
        mock_parse.assert_not_called()

    async def test_pipeline_empty_extraction_sets_error_message(self, async_session: AsyncSession) -> None:
        """LLM이 빈 결과를 반환하면 COMPLETED + error_message 힌트가 설정된다."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        await async_session.commit()

        mock_parsed = ParsedFile(source_path="/tmp/nda.pdf", file_type="pdf")
        mock_parsed.text = "NDA 문서 " * 200

        classify_resp = '{"category": "NDA", "confidence": 0.90}'
        # LLM이 파싱 불가능한 응답 → extract_fields가 {} 반환
        extract_resp = "no json content here"

        llm = _mock_llm_client()
        llm.call_with_model = AsyncMock(return_value=classify_resp)
        llm.call = AsyncMock(return_value=extract_resp)

        with (
            patch(
                "app.services.document_extraction_service.blob_client",
                ensure_initialized=AsyncMock(),
                download_blob_to_file=AsyncMock(),
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
            from app.services.document_extraction_service import _run_pipeline_core

            await _run_pipeline_core(async_session, ext.id, MagicMock(), 0.0)

        await async_session.refresh(ext)
        assert ext.status == ExtractionStatus.COMPLETED
        assert ext.extracted_data == {}
        assert ext.error_message is not None
        assert "구조화 데이터" in ext.error_message

    async def test_pipeline_classification_failure_tracks_cost(self, async_session: AsyncSession) -> None:
        """분류 LLM 호출 실패 → FAILED + llm_cost_usd 기록."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        await async_session.commit()

        mock_parsed = ParsedFile(source_path="/tmp/test.pdf", file_type="pdf")
        mock_parsed.text = "문서 내용 " * 200

        llm = _mock_llm_client()
        llm.total_cost_usd = 0.005  # mini 모델 시도 비용
        # 분류 호출 시 모든 모델 실패
        llm.call_with_model = AsyncMock(side_effect=RuntimeError("mini model failed"))
        llm.call = AsyncMock(side_effect=RuntimeError("primary model failed"))

        with (
            patch(
                "app.services.document_extraction_service.blob_client",
                ensure_initialized=AsyncMock(),
                download_blob_to_file=AsyncMock(),
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
            from app.services.document_extraction_service import _run_pipeline_core

            await _run_pipeline_core(async_session, ext.id, MagicMock(), 0.0)

        await async_session.refresh(ext)
        assert ext.status == ExtractionStatus.FAILED
        assert "분류" in (ext.error_message or "")
        assert ext.llm_cost_usd == 0.005  # 비용이 기록됨

    async def test_pipeline_extraction_failure_tracks_cost(self, async_session: AsyncSession) -> None:
        """추출 LLM 호출 실패 → FAILED + llm_cost_usd 기록."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        await async_session.commit()

        mock_parsed = ParsedFile(source_path="/tmp/nda.pdf", file_type="pdf")
        mock_parsed.text = "NDA 비밀유지계약서 " * 200

        classify_resp = '{"category": "NDA", "confidence": 0.92}'
        llm = _mock_llm_client()
        llm.total_cost_usd = 0.01
        llm.call_with_model = AsyncMock(return_value=classify_resp)
        # 추출 호출 시 실패
        llm.call = AsyncMock(side_effect=RuntimeError("extraction failed"))

        with (
            patch(
                "app.services.document_extraction_service.blob_client",
                ensure_initialized=AsyncMock(),
                download_blob_to_file=AsyncMock(),
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
            from app.services.document_extraction_service import _run_pipeline_core

            await _run_pipeline_core(async_session, ext.id, MagicMock(), 0.0)

        await async_session.refresh(ext)
        assert ext.status == ExtractionStatus.FAILED
        assert "추출" in (ext.error_message or "")
        assert ext.llm_cost_usd == 0.01  # 비용이 기록됨

    async def test_pipeline_timeout_marks_failed(self, async_session: AsyncSession) -> None:
        """파이프라인 타임아웃 → FAILED."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        await async_session.commit()

        from app.services.document_extraction_service import run_extraction_pipeline

        async def _hang_forever(_sf: object, _eid: object, _s: object, _t0: object) -> None:
            import asyncio

            await asyncio.sleep(999)

        with (
            patch(
                "app.services.document_extraction_service._run_pipeline_inner",
                side_effect=_hang_forever,
            ),
            patch(
                "app.services.document_extraction_service._PIPELINE_TIMEOUT",
                0.05,
            ),
            patch(
                "app.services.document_extraction_service.mark_extraction_failed",
                new_callable=AsyncMock,
            ) as mock_mark_failed,
        ):
            await run_extraction_pipeline(ext.id, async_session.get_bind())  # type: ignore[arg-type]

        mock_mark_failed.assert_called_once()
        call_args = mock_mark_failed.call_args
        assert call_args[1].get("extraction_id", call_args[0][1]) == ext.id
        assert "시간이 초과" in str(call_args)


# ── _safe_set_field 테스트 ─────────────────────────────────────


class TestSafeSetField:
    """_safe_set_field 유틸리티 단위 테스트."""

    def test_normal_string_within_limit(self) -> None:
        """제한 이내의 문자열은 그대로 설정된다."""
        obj = MagicMock()
        _safe_set_field(obj, "counterparty_name", "AMIC Partners")
        assert obj.counterparty_name == "AMIC Partners"

    def test_string_exceeds_limit_truncated(self) -> None:
        """제한 초과 문자열은 잘린다."""
        obj = MagicMock()
        long_name = "A" * 250  # counterparty_name 제한: 200
        _safe_set_field(obj, "counterparty_name", long_name)
        assert obj.counterparty_name == "A" * 200

    def test_currency_truncated_to_3(self) -> None:
        """currency 필드는 3자로 제한."""
        obj = MagicMock()
        _safe_set_field(obj, "currency", "USDX")
        assert obj.currency == "USD"

    def test_non_string_value_passes_through(self) -> None:
        """숫자 등 비문자열은 truncation 없이 전달."""
        obj = MagicMock()
        _safe_set_field(obj, "exclusivity_period_days", 90)
        assert obj.exclusivity_period_days == 90

    def test_unknown_field_no_limit(self) -> None:
        """_STRING_LIMITS에 없는 필드는 제한 없이 설정."""
        obj = MagicMock()
        long_val = "X" * 1000
        _safe_set_field(obj, "unknown_field", long_val)
        assert obj.unknown_field == long_val

    def test_date_field_truncated_to_10(self) -> None:
        """날짜 필드(signed_at 등)는 10자로 제한."""
        obj = MagicMock()
        _safe_set_field(obj, "signed_at", "2026-01-01 extra text")
        assert obj.signed_at == "2026-01-01"
        assert len(obj.signed_at) == 10

    def test_string_limits_dict_exists(self) -> None:
        """주요 필드가 _STRING_LIMITS에 정의되어 있다."""
        assert "counterparty_name" in _STRING_LIMITS
        assert "currency" in _STRING_LIMITS
        assert "signed_at" in _STRING_LIMITS

    # ── 타입 강제 변환 테스트 ──

    def test_int_field_string_coerced(self) -> None:
        """Integer 필드에 문자열이 오면 int로 변환된다."""
        obj = MagicMock()
        _safe_set_field(obj, "confidentiality_period_months", "12")
        assert obj.confidentiality_period_months == 12

    def test_int_field_int_passes_through(self) -> None:
        """Integer 필드에 int가 오면 그대로 전달."""
        obj = MagicMock()
        _safe_set_field(obj, "exclusivity_period_days", 30)
        assert obj.exclusivity_period_days == 30

    def test_int_field_invalid_string_skipped(self) -> None:
        """Integer 필드에 변환 불가 문자열이 오면 setattr 건너뜀."""
        obj = MagicMock()
        _safe_set_field(obj, "confidentiality_period_months", "약 12개월")
        # setattr이 호출되지 않으므로 MagicMock 기본값(MagicMock 인스턴스) 유지
        assert not isinstance(obj.confidentiality_period_months, (int, str))

    def test_numeric_field_string_coerced(self) -> None:
        """Numeric 필드에 문자열이 오면 float로 변환된다."""
        obj = MagicMock()
        _safe_set_field(obj, "amount", "50000000000")
        assert obj.amount == 50000000000.0

    def test_numeric_field_number_passes_through(self) -> None:
        """Numeric 필드에 숫자가 오면 그대로 전달."""
        obj = MagicMock()
        _safe_set_field(obj, "amount", 50000000000)
        assert obj.amount == 50000000000

    def test_numeric_field_invalid_string_skipped(self) -> None:
        """Numeric 필드에 변환 불가 문자열이 오면 setattr 건너뜀."""
        obj = MagicMock()
        _safe_set_field(obj, "amount", "약 500억원")
        assert not isinstance(obj.amount, (int, float, str))


# ── UUID 파싱 한국어 에러 테스트 ────────────────────────────────


class TestUuidParsingKoreanError:
    """UUID 형식 오류 시 한국어 ValueError가 발생하는지 검증."""

    async def test_nda_invalid_uuid_raises_korean_error(self, async_session: AsyncSession) -> None:
        """NDA 생성 시 잘못된 UUID → 한국어 ValueError."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        ext.extracted_data = {"counterparty_name": "Test"}
        await async_session.commit()

        with pytest.raises(ValueError, match="buyer_candidate_id 형식이 올바르지 않습니다"):
            await confirm_extraction(
                db=async_session,
                extraction_id=ext.id,
                confirmed_data={"buyer_candidate_id": "not-a-uuid"},
                target_model="nda",
                target_id=None,
                create_new=True,
                user_email="test@amic.kr",
            )

    async def test_bid_invalid_uuid_raises_korean_error(self, async_session: AsyncSession) -> None:
        """Bid 생성 시 잘못된 UUID → 한국어 ValueError."""
        txn = await _make_txn(async_session)
        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        ext.extracted_data = {"proposed_amount": 1000}
        await async_session.commit()

        with pytest.raises(ValueError, match="buyer_candidate_id 형식이 올바르지 않습니다"):
            await confirm_extraction(
                db=async_session,
                extraction_id=ext.id,
                confirmed_data={"buyer_candidate_id": "invalid-uuid-format"},
                target_model="bid",
                target_id=None,
                create_new=True,
                user_email="test@amic.kr",
            )

    async def test_nda_create_with_string_overflow_truncated(self, async_session: AsyncSession) -> None:
        """NDA 생성 시 counterparty_name 초과 → 200자로 잘림."""
        txn = await _make_txn(async_session)
        buyer = BuyerCandidate(
            transaction_id=txn.id,
            company_name="TestCo",
            buyer_type=BuyerType.STRATEGIC,
            status=BuyerCandidateStatus.IDENTIFIED,
        )
        async_session.add(buyer)
        await async_session.flush()

        vdr_doc = await _make_vdr_doc(async_session, txn)
        ext = await create_extraction(async_session, txn.id, vdr_doc.id)
        ext.status = ExtractionStatus.COMPLETED
        ext.extracted_data = {"counterparty_name": "A" * 250}
        await async_session.commit()

        result = await confirm_extraction(
            db=async_session,
            extraction_id=ext.id,
            confirmed_data={
                "buyer_candidate_id": str(buyer.id),
                "counterparty_name": "B" * 250,
            },
            target_model="nda",
            target_id=None,
            create_new=True,
            user_email="test@amic.kr",
        )
        assert result.target_id is not None
        nda = await async_session.get(NDA, result.target_id)
        assert nda is not None
        assert len(nda.counterparty_name) == 200
