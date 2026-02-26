"""문서 AI 추출 서비스 — 분류 + 데이터 추출 + DB 매핑."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_extraction import DocumentExtraction
from app.models.enums import (
    DocExtractionCategory,
    ExtractionStatus,
)
from app.models.vdr_document import VdrDocument
from app.ralph.llm_client import RalphLLMClient
from app.ralph.parsers import parse_file
from app.ralph.parsers.base import ParsedFile
from app.services.extraction_prompts import (
    CLASSIFICATION_SYSTEM,
    CLASSIFICATION_USER_TEMPLATE,
    EXTRACTABLE_CATEGORIES,
    EXTRACTION_PROMPTS,
    EXTRACTION_USER_TEMPLATE,
)

logger = logging.getLogger(__name__)

# 추출 시 텍스트 최대 길이 (토큰 비용 제어)
_MAX_TEXT_CHARS = 100_000
_PREVIEW_CHARS = 2_000


# ── CRUD ─────────────────────────────────────────────────────


async def create_extraction(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    vdr_document_id: uuid.UUID,
) -> DocumentExtraction:
    """추출 작업 레코드를 생성한다 (PENDING 상태)."""
    extraction = DocumentExtraction(
        transaction_id=transaction_id,
        vdr_document_id=vdr_document_id,
        status=ExtractionStatus.PENDING,
    )
    db.add(extraction)
    await db.flush()
    await db.refresh(extraction)
    return extraction


async def get_extraction(
    db: AsyncSession,
    extraction_id: uuid.UUID,
) -> DocumentExtraction | None:
    """추출 작업 단일 조회."""
    result = await db.execute(select(DocumentExtraction).where(DocumentExtraction.id == extraction_id))
    return result.scalar_one_or_none()


async def list_extractions(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[DocumentExtraction]:
    """거래의 모든 추출 작업 목록."""
    result = await db.execute(
        select(DocumentExtraction)
        .where(DocumentExtraction.transaction_id == transaction_id)
        .order_by(DocumentExtraction.created_at.desc())
    )
    return list(result.scalars().all())


# ── 분류 ─────────────────────────────────────────────────────


async def classify_document(
    parsed: ParsedFile,
    llm_client: RalphLLMClient,
) -> tuple[DocExtractionCategory, float]:
    """문서를 9개 카테고리 중 하나로 분류한다.

    mini 모델 우선 사용 (비용 최소화).
    """
    preview = parsed.summary(max_chars=_PREVIEW_CHARS)
    if not preview.strip():
        return DocExtractionCategory.REFERENCE_ONLY, 0.5

    user_msg = CLASSIFICATION_USER_TEMPLATE.format(text_preview=preview)

    # mini 모델 우선 시도
    try:
        raw = await llm_client.call_with_model(CLASSIFICATION_SYSTEM, user_msg, model="gpt-4o-mini")
    except Exception:
        raw = await llm_client.call(CLASSIFICATION_SYSTEM, user_msg)

    # JSON 파싱
    try:
        data = json.loads(_extract_json(raw))
        category_str = data.get("category", "REFERENCE_ONLY")
        confidence = float(data.get("confidence", 0.5))
    except (json.JSONDecodeError, ValueError):
        logger.warning("분류 결과 JSON 파싱 실패: %s", raw[:200])
        return DocExtractionCategory.REFERENCE_ONLY, 0.3

    # Enum 변환
    try:
        category = DocExtractionCategory(category_str)
    except ValueError:
        category = DocExtractionCategory.REFERENCE_ONLY
        confidence = 0.3

    return category, min(max(confidence, 0.0), 1.0)


# ── 추출 ─────────────────────────────────────────────────────


async def extract_fields(
    parsed: ParsedFile,
    category: DocExtractionCategory,
    llm_client: RalphLLMClient,
) -> dict:
    """카테고리별 전용 프롬프트로 구조화 데이터를 추출한다."""
    system_prompt = EXTRACTION_PROMPTS.get(category.value)
    if not system_prompt:
        return {}

    doc_text = parsed.text[:_MAX_TEXT_CHARS]
    if not doc_text.strip():
        return {}

    user_msg = EXTRACTION_USER_TEMPLATE.format(document_text=doc_text)

    raw = await llm_client.call(system_prompt, user_msg)

    try:
        return json.loads(_extract_json(raw))
    except (json.JSONDecodeError, ValueError):
        logger.warning("추출 결과 JSON 파싱 실패 (category=%s): %s", category, raw[:200])
        return {}


# ── 전체 파이프라인 ───────────────────────────────────────────


async def run_extraction_pipeline(
    extraction_id: uuid.UUID,
    session_factory,
) -> None:
    """전체 추출 파이프라인을 실행한다 (Celery 태스크에서 호출).

    1. VDR 문서 로드 + 파싱
    2. LLM 문서 분류
    3. A유형 → LLM 데이터 추출
    4. 결과 DB 저장
    """
    from app.core.config import settings

    async with session_factory() as db:
        # 1. 추출 레코드 + VDR 문서 로드
        extraction = await get_extraction(db, extraction_id)
        if not extraction:
            logger.error("추출 레코드 없음: %s", extraction_id)
            return

        vdr_doc = await db.get(VdrDocument, extraction.vdr_document_id)
        if not vdr_doc:
            extraction.status = ExtractionStatus.FAILED
            extraction.error_message = "VDR 문서를 찾을 수 없습니다"
            await db.commit()
            return

        # 상태: CLASSIFYING
        extraction.status = ExtractionStatus.CLASSIFYING
        await db.commit()

        # 2. 파일 파싱
        try:
            parsed = parse_file(vdr_doc.file_path)
        except Exception as exc:
            extraction.status = ExtractionStatus.FAILED
            extraction.error_message = f"파일 파싱 실패: {exc}"
            await db.commit()
            return

        if not parsed.is_valid:
            extraction.status = ExtractionStatus.FAILED
            extraction.error_message = f"파싱 결과 없음: {parsed.parse_error or '텍스트/표 없음'}"
            await db.commit()
            return

        # 3. LLM 클라이언트 생성
        llm = RalphLLMClient.from_settings(settings)
        if not llm.is_available:
            extraction.status = ExtractionStatus.FAILED
            extraction.error_message = "사용 가능한 LLM 프로바이더가 없습니다"
            await db.commit()
            return

        # 4. 분류
        try:
            category, confidence = await classify_document(parsed, llm)
        except Exception as exc:
            extraction.status = ExtractionStatus.FAILED
            extraction.error_message = f"문서 분류 실패: {exc}"
            await db.commit()
            return

        extraction.doc_category = category
        extraction.classification_confidence = confidence

        # 5. REFERENCE_ONLY 또는 향후 확장 카테고리 → 추출 건너뜀
        if category.value not in EXTRACTABLE_CATEGORIES:
            extraction.status = ExtractionStatus.COMPLETED
            extraction.llm_cost_usd = llm.total_cost_usd
            await db.commit()
            logger.info(
                "분류 완료 (추출 불필요): %s → %s (%.0f%%)",
                vdr_doc.original_name,
                category.value,
                confidence * 100,
            )
            return

        # 6. 상태: EXTRACTING
        extraction.status = ExtractionStatus.EXTRACTING
        await db.commit()

        # 7. 데이터 추출
        try:
            extracted = await extract_fields(parsed, category, llm)
        except Exception as exc:
            extraction.status = ExtractionStatus.FAILED
            extraction.error_message = f"데이터 추출 실패: {exc}"
            extraction.llm_cost_usd = llm.total_cost_usd
            await db.commit()
            return

        # 8. 결과 저장
        extraction.extracted_data = extracted
        extraction.status = ExtractionStatus.COMPLETED
        extraction.llm_cost_usd = llm.total_cost_usd
        await db.commit()

        logger.info(
            "추출 완료: %s → %s (%.0f%%, $%.4f)",
            vdr_doc.original_name,
            category.value,
            confidence * 100,
            llm.total_cost_usd,
        )


# ── 사용자 확정 → DB 매핑 ────────────────────────────────────


async def confirm_extraction(
    db: AsyncSession,
    extraction_id: uuid.UUID,
    confirmed_data: dict,
    target_model: str,
    target_id: uuid.UUID | None,
    create_new: bool,
    user_email: str,
) -> DocumentExtraction:
    """사용자가 검토/수정한 데이터를 확정하고 대상 모델에 매핑한다."""
    extraction = await get_extraction(db, extraction_id)
    if not extraction:
        raise ValueError(f"추출 레코드 없음: {extraction_id}")

    if extraction.status not in (ExtractionStatus.COMPLETED, ExtractionStatus.CONFIRMED):
        raise ValueError(f"확정 불가 상태: {extraction.status}")

    # 대상 모델에 데이터 적용
    applied_id = await _apply_to_model(
        db=db,
        transaction_id=extraction.transaction_id,
        target_model=target_model,
        target_id=target_id,
        create_new=create_new,
        data=confirmed_data,
    )

    # 추출 레코드 업데이트
    extraction.extracted_data = confirmed_data
    extraction.target_model = target_model
    extraction.target_id = applied_id
    extraction.status = ExtractionStatus.CONFIRMED
    extraction.reviewed_by_email = user_email
    extraction.reviewed_at = datetime.now(UTC).isoformat()
    await db.commit()
    await db.refresh(extraction)

    return extraction


async def _apply_to_model(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    target_model: str,
    target_id: uuid.UUID | None,
    create_new: bool,
    data: dict,
) -> uuid.UUID | None:
    """추출 데이터를 대상 모델에 적용한다."""
    if target_model == "nda":
        return await _apply_to_nda(db, transaction_id, data, target_id, create_new)
    elif target_model == "bid":
        return await _apply_to_bid(db, transaction_id, data, target_id, create_new)
    elif target_model == "contract":
        return await _apply_to_contract(db, transaction_id, data, target_id, create_new)
    elif target_model == "transaction":
        return await _apply_to_transaction(db, transaction_id, data)
    else:
        logger.warning("지원하지 않는 target_model: %s", target_model)
        return None


async def _apply_to_nda(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    data: dict,
    target_id: uuid.UUID | None,
    create_new: bool,
) -> uuid.UUID | None:
    """NDA 모델에 추출 데이터를 적용한다."""
    from app.models.nda import NDA

    field_map = {
        "counterparty_name": "counterparty_name",
        "nda_type": "nda_type",
        "signed_at": "signed_at",
        "expires_at": "expires_at",
        "jurisdiction": "jurisdiction",
        "confidentiality_period_months": "confidentiality_period_months",
    }

    if target_id and not create_new:
        nda = await db.get(NDA, target_id)
        if nda:
            for src, dst in field_map.items():
                val = data.get(src)
                if val is not None:
                    setattr(nda, dst, val)
            await db.flush()
            return nda.id
    return None


async def _apply_to_bid(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    data: dict,
    target_id: uuid.UUID | None,
    create_new: bool,
) -> uuid.UUID | None:
    """Bid 모델에 추출 데이터를 적용한다."""
    from app.models.bid import Bid

    if target_id and not create_new:
        bid = await db.get(Bid, target_id)
        if bid:
            if data.get("proposed_amount") is not None:
                bid.amount = data["proposed_amount"]
            if data.get("currency"):
                bid.currency = data["currency"]
            if data.get("valuation_method"):
                bid.valuation_method = data["valuation_method"]
            if data.get("exclusivity_period_days") is not None:
                bid.exclusivity_period_days = data["exclusivity_period_days"]
            if data.get("conditions_precedent"):
                bid.conditions_precedent = data["conditions_precedent"]
            if data.get("valid_until"):
                bid.valid_until = data["valid_until"]
            await db.flush()
            return bid.id
    return None


async def _apply_to_contract(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    data: dict,
    target_id: uuid.UUID | None,
    create_new: bool,
) -> uuid.UUID | None:
    """Contract 모델에 추출 데이터를 적용한다."""
    from app.models.contract import Contract

    if target_id and not create_new:
        contract = await db.get(Contract, target_id)
        if contract:
            if data.get("counterparty_name"):
                contract.counterparty_name = data["counterparty_name"]
            if data.get("effective_date"):
                contract.effective_date = data["effective_date"]
            if data.get("closing_date"):
                contract.expiry_date = data["closing_date"]
            # AI 분석 전용 필드 활용
            contract.ai_analysis_summary = data.get("risk_summary")
            contract.ai_risk_flags = {
                k: v
                for k, v in data.items()
                if k
                in (
                    "rw_cap_amount",
                    "rw_cap_percentage",
                    "indemnification_period_months",
                    "key_conditions",
                    "final_purchase_price",
                )
                and v is not None
            } or None
            await db.flush()
            return contract.id
    return None


async def _apply_to_transaction(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    data: dict,
) -> uuid.UUID | None:
    """Transaction 모델에 등기부등본/세무신고서 데이터를 적용한다.

    corporate_info 또는 financial_summary JSONB 필드에 저장.
    """
    from app.models.transaction import Transaction

    txn = await db.get(Transaction, transaction_id)
    if not txn:
        return None

    # 등기부등본/사업자등록증 데이터 (CORPORATE_DOCS)
    corporate_keys = {
        "company_name",
        "representative_name",
        "establishment_date",
        "business_registration_number",
        "corporate_registration_number",
        "capital_amount",
        "total_shares_issued",
        "par_value_per_share",
        "common_shares",
        "preferred_shares",
        "business_type",
        "business_item",
        "head_office_address",
        "directors",
        "corporate_purpose",
    }
    corporate_data = {k: v for k, v in data.items() if k in corporate_keys and v is not None}
    if corporate_data:
        txn.corporate_info = {**(txn.corporate_info or {}), **corporate_data}

    # 세무신고서 데이터 (TAX_FILING)
    financial_keys = {
        "fiscal_year",
        "revenue",
        "cost_of_goods_sold",
        "gross_profit",
        "sga_expenses",
        "operating_income",
        "non_operating_income",
        "non_operating_expenses",
        "income_before_tax",
        "corporate_tax",
        "net_income",
        "total_assets",
        "total_liabilities",
        "total_equity",
    }
    financial_data = {k: v for k, v in data.items() if k in financial_keys and v is not None}
    if financial_data:
        txn.financial_summary = {**(txn.financial_summary or {}), **financial_data}

    await db.flush()
    return txn.id


# ── 유틸리티 ─────────────────────────────────────────────────


def _extract_json(text: str) -> str:
    """LLM 응답에서 JSON 부분만 추출한다."""
    # ```json ... ``` 블록 추출
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()

    # { ... } 블록 추출
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]

    return text.strip()
