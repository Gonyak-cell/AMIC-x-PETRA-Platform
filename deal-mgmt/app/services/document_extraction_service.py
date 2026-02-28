"""문서 AI 추출 서비스 — 분류 + 데이터 추출 + DB 매핑."""

from __future__ import annotations

import asyncio
import json
import logging
import time
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

# 카테고리별 추출 텍스트 제한 (정형 문서는 앞부분에 핵심 정보 집중)
_CATEGORY_TEXT_LIMITS: dict[str, int] = {
    "CORPORATE_DOCS": 30_000,
    "TAX_FILING": 40_000,
    "NDA": 20_000,
    "LOI_MOU": 30_000,
    "SPA_BTA": _MAX_TEXT_CHARS,
}

# 정형 문서 카테고리 — 경량 모델로 추출 (빠르고 저렴, 실패 시 primary 폴백)
_MINI_MODEL_CATEGORIES: frozenset[str] = frozenset({"CORPORATE_DOCS", "TAX_FILING"})

# 경량 모델 우선순위 (프로바이더별): 사용 가능한 첫 번째 모델 사용
_MINI_MODELS: list[str] = [
    "claude-haiku-4-5-20251001",  # Anthropic (프로덕션에서 사용 가능)
    "gpt-4o-mini",  # OpenAI (키 설정 시 사용)
]

# 경량 모델 개별 호출 타임아웃 (초) — LLM 어댑터 90초보다 짧게
_MINI_MODEL_TIMEOUT: float = 30.0


# ── CRUD ─────────────────────────────────────────────────────


async def create_extraction(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    vdr_document_id: uuid.UUID,
    doc_category_hint: DocExtractionCategory | None = None,
) -> DocumentExtraction:
    """추출 작업 레코드를 생성한다 (PENDING 상태).

    doc_category_hint가 있으면 분류 단계를 건너뛴다.
    """
    extraction = DocumentExtraction(
        transaction_id=transaction_id,
        vdr_document_id=vdr_document_id,
        status=ExtractionStatus.PENDING,
    )
    if doc_category_hint:
        extraction.doc_category = doc_category_hint
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

    # 경량 모델 우선 시도 (개별 타임아웃 적용)
    raw = None
    for mini_model in _MINI_MODELS:
        try:
            raw = await asyncio.wait_for(
                llm_client.call_with_model(CLASSIFICATION_SYSTEM, user_msg, model=mini_model),
                timeout=_MINI_MODEL_TIMEOUT,
            )
            logger.info("경량 모델 분류 성공: model=%s", mini_model)
            break
        except Exception as exc:
            logger.debug("경량 모델 %s 분류 실패 (폴백 시도): %s", mini_model, exc)
            continue
    if raw is None:
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

    max_chars = _CATEGORY_TEXT_LIMITS.get(category.value, _MAX_TEXT_CHARS)
    doc_text = parsed.text[:max_chars]
    if not doc_text.strip():
        return {}

    user_msg = EXTRACTION_USER_TEMPLATE.format(document_text=doc_text)

    # 정형 문서: 경량 모델 우선 (빠르고 저렴), 실패 시 primary 폴백
    if category.value in _MINI_MODEL_CATEGORIES:
        raw = None
        for mini_model in _MINI_MODELS:
            try:
                raw = await asyncio.wait_for(
                    llm_client.call_with_model(system_prompt, user_msg, model=mini_model),
                    timeout=_MINI_MODEL_TIMEOUT,
                )
                logger.info("경량 모델 추출 성공: model=%s, category=%s", mini_model, category.value)
                break
            except Exception as exc:
                logger.debug("경량 모델 %s 추출 실패 (폴백 시도): %s", mini_model, exc)
                continue
        if raw is None:
            logger.info("경량 모델 모두 실패, primary 폴백 (category=%s)", category.value)
            raw = await llm_client.call(system_prompt, user_msg)
    else:
        raw = await llm_client.call(system_prompt, user_msg)

    try:
        return json.loads(_extract_json(raw))
    except (json.JSONDecodeError, ValueError):
        logger.warning("추출 결과 JSON 파싱 실패 (category=%s): %s", category, raw[:200])
        return {}


# ── 전체 파이프라인 ───────────────────────────────────────────


async def run_extraction_pipeline(
    extraction_id: uuid.UUID,
    session_factory: object,
) -> None:
    """전체 추출 파이프라인을 실행한다 (Celery 태스크에서 호출).

    1. VDR 문서 로드 + 파싱
    2. LLM 문서 분류
    3. A유형 → LLM 데이터 추출
    4. 결과 DB 저장
    """
    from app.core.config import settings

    t0 = time.monotonic()

    try:
        async with session_factory() as db:
            await _run_pipeline_inner(db, extraction_id, settings, t0)
    except Exception as exc:
        logger.exception("파이프라인 미처리 예외 (extraction=%s): %s", extraction_id, exc)
        # FAILED 마킹 시도 (별도 세션)
        try:
            async with session_factory() as db:
                ext = await db.get(DocumentExtraction, extraction_id)
                if ext and ext.status not in (
                    ExtractionStatus.COMPLETED,
                    ExtractionStatus.CONFIRMED,
                    ExtractionStatus.FAILED,
                ):
                    ext.status = ExtractionStatus.FAILED
                    ext.error_message = "내부 오류가 발생했습니다. 관리자에게 문의하세요."
                    await db.commit()
        except Exception:
            logger.exception("FAILED 마킹 복구 실패 (extraction=%s)", extraction_id)


async def _run_pipeline_inner(
    db: AsyncSession,
    extraction_id: uuid.UUID,
    settings: object,
    t0: float,
) -> None:
    """파이프라인 내부 로직 (run_extraction_pipeline에서 호출)."""
    # 0. 멱등성 가드 — SELECT FOR UPDATE로 동시 실행 방지
    result = await db.execute(
        select(DocumentExtraction).where(DocumentExtraction.id == extraction_id).with_for_update(skip_locked=True)
    )
    extraction = result.scalar_one_or_none()
    if not extraction:
        logger.info("추출 레코드 없음 또는 다른 워커가 처리 중: %s", extraction_id)
        return

    if extraction.status != ExtractionStatus.PENDING:
        logger.info(
            "추출 이미 처리됨, 스킵: %s (status=%s)",
            extraction_id,
            extraction.status.value,
        )
        return

    vdr_doc = await db.get(VdrDocument, extraction.vdr_document_id)
    if not vdr_doc:
        extraction.status = ExtractionStatus.FAILED
        extraction.error_message = "VDR 문서를 찾을 수 없습니다"
        await db.commit()
        return

    # 2. 파일 파싱
    try:
        parsed = parse_file(vdr_doc.file_path)
    except Exception as exc:
        logger.error("파일 파싱 실패 (extraction=%s): %s", extraction_id, exc)
        extraction.status = ExtractionStatus.FAILED
        extraction.error_message = "문서 파싱에 실패했습니다."
        await db.commit()
        return

    if not parsed.is_valid:
        logger.warning("파싱 결과 없음 (extraction=%s): %s", extraction_id, parsed.parse_error)
        extraction.status = ExtractionStatus.FAILED
        extraction.error_message = "문서에서 텍스트를 추출할 수 없습니다."
        await db.commit()
        return

    t_parse = time.monotonic()
    logger.info("파싱 완료: %.1fs (chars=%d)", t_parse - t0, len(parsed.text))

    # 3. LLM 클라이언트 생성
    llm = RalphLLMClient.from_settings(settings)
    if not llm.is_available:
        extraction.status = ExtractionStatus.FAILED
        extraction.error_message = "AI 분석 서비스를 사용할 수 없습니다."
        await db.commit()
        return

    # 4. 분류 (doc_category가 이미 설정된 경우 = hint → 건너뛰기)
    was_hint = extraction.doc_category is not None
    if extraction.doc_category:
        category = extraction.doc_category
        confidence = 1.0
        extraction.classification_confidence = confidence
        logger.info(
            "분류 건너뛰기 (hint): %s → %s",
            vdr_doc.original_name,
            category.value,
        )
    else:
        extraction.status = ExtractionStatus.CLASSIFYING
        await db.flush()

        try:
            category, confidence = await classify_document(parsed, llm)
        except Exception as exc:
            logger.error("문서 분류 실패 (extraction=%s): %s", extraction_id, exc)
            extraction.status = ExtractionStatus.FAILED
            extraction.error_message = "문서 분류에 실패했습니다."
            await db.commit()
            return

        extraction.doc_category = category
        extraction.classification_confidence = confidence

    t_classify = time.monotonic()
    logger.info(
        "분류 완료: %.1fs (skip=%s, category=%s, confidence=%.0f%%)",
        t_classify - t_parse,
        was_hint,
        category.value,
        confidence * 100,
    )

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
    await db.flush()

    # 7. 데이터 추출
    try:
        extracted = await extract_fields(parsed, category, llm)
    except Exception as exc:
        logger.error("데이터 추출 실패 (extraction=%s): %s", extraction_id, exc)
        extraction.status = ExtractionStatus.FAILED
        extraction.error_message = "데이터 추출에 실패했습니다."
        extraction.llm_cost_usd = llm.total_cost_usd
        await db.commit()
        return

    t_extract = time.monotonic()
    max_chars = _CATEGORY_TEXT_LIMITS.get(category.value, _MAX_TEXT_CHARS)
    use_mini = category.value in _MINI_MODEL_CATEGORIES
    logger.info(
        "추출 완료: %.1fs (model=%s, chars=%d/%d)",
        t_extract - t_classify,
        "mini" if use_mini else "primary",
        min(len(parsed.text), max_chars),
        max_chars,
    )

    # 8. 결과 저장
    extraction.extracted_data = extracted
    extraction.status = ExtractionStatus.COMPLETED
    extraction.llm_cost_usd = llm.total_cost_usd
    await db.commit()

    logger.info(
        "전체 파이프라인 완료: %.1fs — %s → %s (%.0f%%, $%.4f)",
        time.monotonic() - t0,
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

    if applied_id is None and target_model in ("nda", "bid", "contract"):
        raise ValueError(
            f"{target_model} 데이터 적용 실패: 대상 레코드가 없거나 필수 필드(buyer_candidate_id)가 누락되었습니다"
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

    if create_new:
        buyer_id_raw = data.get("buyer_candidate_id")
        if not buyer_id_raw:
            logger.warning("NDA 신규 생성 실패: buyer_candidate_id 누락")
            return None
        buyer_id = uuid.UUID(str(buyer_id_raw)) if not isinstance(buyer_id_raw, uuid.UUID) else buyer_id_raw
        from app.models.buyer_candidate import BuyerCandidate

        buyer = await db.get(BuyerCandidate, buyer_id)
        if not buyer or buyer.transaction_id != transaction_id:
            logger.warning("NDA 신규 생성 실패: buyer_candidate가 해당 거래에 속하지 않음")
            return None
        nda = NDA(transaction_id=transaction_id, buyer_candidate_id=buyer_id)
        for src, dst in field_map.items():
            val = data.get(src)
            if val is not None:
                setattr(nda, dst, val)
        db.add(nda)
        await db.flush()
        return nda.id
    elif target_id:
        nda = await db.get(NDA, target_id)
        if nda and nda.transaction_id == transaction_id:
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

    field_map = {
        "proposed_amount": "amount",
        "currency": "currency",
        "valuation_method": "valuation_method",
        "exclusivity_period_days": "exclusivity_period_days",
        "conditions_precedent": "conditions_precedent",
        "valid_until": "valid_until",
    }

    if create_new:
        buyer_id_raw = data.get("buyer_candidate_id")
        if not buyer_id_raw:
            logger.warning("Bid 신규 생성 실패: buyer_candidate_id 누락")
            return None
        buyer_id = uuid.UUID(str(buyer_id_raw)) if not isinstance(buyer_id_raw, uuid.UUID) else buyer_id_raw
        from app.models.buyer_candidate import BuyerCandidate

        buyer = await db.get(BuyerCandidate, buyer_id)
        if not buyer or buyer.transaction_id != transaction_id:
            logger.warning("Bid 신규 생성 실패: buyer_candidate가 해당 거래에 속하지 않음")
            return None
        from app.models.enums import BidType

        bid_type_val = data.get("bid_type", BidType.LOI)
        bid = Bid(
            transaction_id=transaction_id,
            buyer_candidate_id=buyer_id,
            bid_type=bid_type_val,
        )
        for src, dst in field_map.items():
            val = data.get(src)
            if val is not None:
                setattr(bid, dst, val)
        db.add(bid)
        await db.flush()
        return bid.id
    elif target_id:
        bid = await db.get(Bid, target_id)
        if bid and bid.transaction_id == transaction_id:
            for src, dst in field_map.items():
                val = data.get(src)
                if val is not None:
                    setattr(bid, dst, val)
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

    field_map = {
        "counterparty_name": "counterparty_name",
        "effective_date": "effective_date",
        "closing_date": "expiry_date",
        "risk_summary": "ai_analysis_summary",
    }

    risk_flag_keys = frozenset(
        {
            "rw_cap_amount",
            "rw_cap_percentage",
            "indemnification_period_months",
            "key_conditions",
            "final_purchase_price",
        }
    )

    def _apply_fields(contract: object) -> None:
        for src, dst in field_map.items():
            val = data.get(src)
            if val is not None:
                setattr(contract, dst, val)
        risk_flags = {k: v for k, v in data.items() if k in risk_flag_keys and v is not None}
        if risk_flags:
            contract.ai_risk_flags = risk_flags  # type: ignore[attr-defined]

    if create_new:
        contract = Contract(
            transaction_id=transaction_id,
            title=data.get("title") or "AI 추출 계약서",
        )
        _apply_fields(contract)
        db.add(contract)
        await db.flush()
        return contract.id
    elif target_id:
        contract = await db.get(Contract, target_id)
        if contract and contract.transaction_id == transaction_id:
            _apply_fields(contract)
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
        end = text.find("```", start)
        return text[start:end].strip() if end != -1 else text[start:].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.find("```", start)
        return text[start:end].strip() if end != -1 else text[start:].strip()

    # { ... } 블록 추출
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]

    return text.strip()
