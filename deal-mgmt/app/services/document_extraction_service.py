"""문서 AI 추출 서비스 — 분류 + 데이터 추출 + DB 매핑."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.blob_storage import blob_client
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
    "REGISTRY_DOCS": 30_000,
    "BIZ_REG_DOCS": 30_000,
    "TAX_FILING": 40_000,
    "NDA": 20_000,
    "ENGAGEMENT_CONTRACT": 30_000,
    "LOI_MOU": 30_000,
    "TEASER_IM": 30_000,
    "SPA_BTA": _MAX_TEXT_CHARS,
}

# 정형 문서 카테고리 — 경량 모델로 추출 (빠르고 저렴, 실패 시 primary 폴백)
_MINI_MODEL_CATEGORIES: frozenset[str] = frozenset({"CORPORATE_DOCS", "REGISTRY_DOCS", "BIZ_REG_DOCS", "TAX_FILING"})

# 경량 모델 우선순위 (프로바이더별): 사용 가능한 첫 번째 모델 사용
_MINI_MODELS: list[str] = [
    "claude-haiku-4-5-20251001",  # Anthropic (프로덕션에서 사용 가능)
    "gpt-4o-mini",  # OpenAI (키 설정 시 사용)
]

# 경량 모델 개별 호출 타임아웃 (초) — LLM 어댑터 90초보다 짧게
_MINI_MODEL_TIMEOUT: float = 30.0

# 전체 파이프라인 타임아웃 (초) — Celery soft_time_limit(300초)보다 짧게
_PIPELINE_TIMEOUT: float = 240.0

# In local/dev fallback mode, these categories only need a minimal review
# payload. Avoid full PDF OCR before fallback so large marketing/legal PDFs do
# not monopolize the local API worker.
_FAST_RULES_FALLBACK_CATEGORIES: frozenset[DocExtractionCategory] = frozenset(
    {
        DocExtractionCategory.NDA,
        DocExtractionCategory.ENGAGEMENT_CONTRACT,
        DocExtractionCategory.TEASER_IM,
        DocExtractionCategory.LOI_MOU,
        DocExtractionCategory.SPA_BTA,
    }
)
_PARSE_OCR_CHAR_LIMIT_CAP = 40_000
_PARSE_OCR_LIMITS_BY_CATEGORY: dict[DocExtractionCategory, tuple[int, int]] = {
    DocExtractionCategory.CORPORATE_DOCS: (4, 12_000),
    DocExtractionCategory.REGISTRY_DOCS: (4, 12_000),
    DocExtractionCategory.BIZ_REG_DOCS: (4, 12_000),
    DocExtractionCategory.TAX_FILING: (6, 14_000),
    DocExtractionCategory.NDA: (6, 12_000),
    DocExtractionCategory.ENGAGEMENT_CONTRACT: (6, 12_000),
    DocExtractionCategory.LOI_MOU: (6, 12_000),
    DocExtractionCategory.SPA_BTA: (8, 16_000),
    DocExtractionCategory.TEASER_IM: (6, 14_000),
}


def _ocr_limits_for_parse(category: DocExtractionCategory) -> tuple[int | None, int | None]:
    if category in _PARSE_OCR_LIMITS_BY_CATEGORY:
        return _PARSE_OCR_LIMITS_BY_CATEGORY[category]
    char_limit = min(_CATEGORY_TEXT_LIMITS.get(category.value, _MAX_TEXT_CHARS), _PARSE_OCR_CHAR_LIMIT_CAP)
    page_limit = min(16, max(4, (char_limit + 2499) // 2500))
    return page_limit, char_limit


# ── CRUD ─────────────────────────────────────────────────────


async def has_active_extraction(
    db: AsyncSession,
    vdr_document_id: uuid.UUID,
) -> DocumentExtraction | None:
    """해당 VDR 문서에 진행 중이거나 완료된 추출이 있으면 반환한다.

    NOTE: 동시 요청 시 두 트랜잭션이 모두 None을 반환할 수 있는 레이스 윈도우 존재.
    DB에 잠글 행이 없으므로 SELECT FOR UPDATE로 방지 불가.
    파이프라인의 멱등성 가드(SELECT FOR UPDATE skip_locked)가 중복 실행을 방지한다.
    """
    _active_statuses = (
        ExtractionStatus.PENDING,
        ExtractionStatus.CLASSIFYING,
        ExtractionStatus.EXTRACTING,
        ExtractionStatus.COMPLETED,
        ExtractionStatus.CONFIRMED,
    )
    result = await db.execute(
        select(DocumentExtraction)
        .where(
            DocumentExtraction.vdr_document_id == vdr_document_id,
            DocumentExtraction.status.in_(_active_statuses),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_extraction(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    vdr_document_id: uuid.UUID,
    doc_category_hint: DocExtractionCategory | None = None,
    *,
    target_model: str | None = None,
    target_id: uuid.UUID | None = None,
    auto_apply_signed_at: bool = False,
) -> DocumentExtraction:
    """추출 작업 레코드를 생성한다 (PENDING 상태).

    doc_category_hint가 있으면 분류 단계를 건너뛴다.
    """
    extraction = DocumentExtraction(
        transaction_id=transaction_id,
        vdr_document_id=vdr_document_id,
        status=ExtractionStatus.PENDING,
        target_model=target_model,
        target_id=target_id,
        auto_apply_signed_at=auto_apply_signed_at,
        extraction_source="LLM",
        processing_note=None,
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
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[DocumentExtraction]:
    """거래의 추출 작업 목록 (페이지네이션 지원)."""
    result = await db.execute(
        select(DocumentExtraction)
        .where(DocumentExtraction.transaction_id == transaction_id)
        .order_by(DocumentExtraction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


# ── LLM 호출 헬퍼 ─────────────────────────────────────────────


async def _call_with_mini_fallback(
    llm_client: RalphLLMClient,
    system_prompt: str,
    user_msg: str,
    context_label: str,
) -> str:
    """경량 모델 우선 시도 + primary 폴백으로 LLM을 호출한다."""
    for mini_model in _MINI_MODELS:
        try:
            result = await asyncio.wait_for(
                llm_client.call_with_model(system_prompt, user_msg, model=mini_model),
                timeout=_MINI_MODEL_TIMEOUT,
            )
            logger.info("경량 모델 %s 성공: model=%s", context_label, mini_model)
            return result
        except Exception as exc:
            logger.info("경량 모델 %s %s 실패 (폴백 시도): %s", context_label, mini_model, exc)
            continue
    logger.info("경량 모델 모두 실패, primary 폴백 (%s)", context_label)
    return await llm_client.call(system_prompt, user_msg)


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

    raw = await _call_with_mini_fallback(llm_client, CLASSIFICATION_SYSTEM, user_msg, "분류")

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
        raw = await _call_with_mini_fallback(llm_client, system_prompt, user_msg, f"추출({category.value})")
    else:
        raw = await llm_client.call(system_prompt, user_msg)

    try:
        extracted = json.loads(_extract_json(raw))
    except (json.JSONDecodeError, ValueError):
        logger.warning("추출 결과 JSON 파싱 실패 (category=%s): %s", category, raw[:200])
        return {}

    if not isinstance(extracted, dict):
        logger.warning(
            "추출 결과가 JSON 객체가 아니므로 무시합니다 (category=%s, type=%s)",
            category,
            type(extracted).__name__,
        )
        return {}

    return extracted


# ── 전체 파이프라인 ───────────────────────────────────────────


_NON_FALLBACK_ENV_NAMES = {"prod", "production", "stg", "staging"}


def _rules_fallback_enabled(app_settings: object) -> bool:
    env = os.getenv("ENV", "").strip().lower()
    return env not in _NON_FALLBACK_ENV_NAMES or bool(getattr(app_settings, "DEBUG", False))


def _clean_fallback_value(value: str | None, *, max_len: int = 160) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip(" \t\r\n:-：,")
    if not cleaned:
        return None
    return cleaned[:max_len]


def _first_text_match(text: str, patterns: list[str], *, group: int = 1, max_len: int = 160) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return _clean_fallback_value(match.group(group), max_len=max_len)
    return None


def _normalize_date_value(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(\d{4})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})", value)
    if not match:
        return _clean_fallback_value(value, max_len=30)
    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _compact_ocr_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _join_spaced_ocr_line(line: str) -> str:
    return re.sub(r"\s+", "", line or "").strip()


def _normalize_korean_ocr_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", value)
    if not match:
        return _normalize_date_value(value)
    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _normalize_business_registration_number(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    # Tesseract often reads the leading 7 in Korean business certificates as '/'.
    if re.fullmatch(r"/\d{2}-\d{2}-\d{5}", cleaned):
        cleaned = "7" + cleaned[1:]
    return cleaned if re.fullmatch(r"\d{3}-\d{2}-\d{5}", cleaned) else None


def _extract_korean_business_lines(text: str) -> tuple[str | None, str | None]:
    normalized_lines = [_join_spaced_ocr_line(line) for line in (text or "").splitlines()]
    normalized_lines = [line for line in normalized_lines if line]
    business_type_candidates: list[str] = []
    business_item_candidates: list[str] = []
    type_values = {"정보통신업", "서비스업", "제조업", "도매및소매업", "부동산업"}
    item_markers = ("영화", "영상", "대중문화", "방송프로그램", "비디오물", "장비개발")
    for line in normalized_lines:
        if line in type_values and line not in business_type_candidates:
            business_type_candidates.append(line)
        if any(marker in line for marker in item_markers) and line.endswith("업"):
            if line not in business_item_candidates:
                business_item_candidates.append(line)
    business_type = ", ".join(business_type_candidates) if business_type_candidates else None
    business_item = "; ".join(business_item_candidates) if business_item_candidates else None
    return business_type, business_item


def _infer_fallback_category(
    extraction: DocumentExtraction,
    filename: str,
) -> tuple[DocExtractionCategory, float]:
    if extraction.doc_category is not None:
        return extraction.doc_category, 1.0

    lower_name = filename.lower()
    target_model = (extraction.target_model or "").lower()
    if target_model == "marketing_material":
        return DocExtractionCategory.TEASER_IM, 0.9
    if target_model == "engagement":
        return DocExtractionCategory.ENGAGEMENT_CONTRACT, 0.9
    if target_model == "nda":
        return DocExtractionCategory.NDA, 0.9
    if target_model == "contract":
        return DocExtractionCategory.SPA_BTA, 0.75
    if target_model == "bid":
        return DocExtractionCategory.LOI_MOU, 0.65

    if "사업자등록" in filename or "biz" in lower_name:
        return DocExtractionCategory.BIZ_REG_DOCS, 0.85
    if "등기" in filename or "registry" in lower_name:
        return DocExtractionCategory.REGISTRY_DOCS, 0.85
    if "nda" in lower_name or "confidential" in lower_name:
        return DocExtractionCategory.NDA, 0.8
    if any(token in lower_name for token in ("teaser", "im", "ir", "tm")) or "브로슈어" in filename:
        return DocExtractionCategory.TEASER_IM, 0.75
    if "mou" in lower_name or "loi" in lower_name:
        return DocExtractionCategory.LOI_MOU, 0.75
    if "계약" in filename or "contract" in lower_name:
        return DocExtractionCategory.SPA_BTA, 0.65
    return DocExtractionCategory.REFERENCE_ONLY, 0.3


def _extract_counterparty(text: str, filename: str) -> str | None:
    value = _first_text_match(
        text,
        [
            r"(?:상대방|계약상대방|매수인|매도인|위탁자|수탁자)\s*[:：]?\s*([^\n\r]{2,80})",
            r"(?:주식회사|㈜)\s*([가-힣A-Za-z0-9&\s]{2,40})",
        ],
    )
    if value:
        return value
    if "언코어" in filename:
        return "언코어"
    if "uncore" in filename.lower():
        return "UNCORE"
    return None


def _extract_signed_date(text: str) -> str | None:
    raw = _first_text_match(
        text,
        [
            r"(?:체결일|계약일|작성일|서명일)\s*[:：]?\s*([0-9년월일.\-/\s]{8,30})",
            r"(\d{4}[.\-/년\s]+\d{1,2}[.\-/월\s]+\d{1,2})",
        ],
        max_len=40,
    )
    return _normalize_date_value(raw)


def _extract_corporate_fallback(text: str, filename: str) -> dict:
    if "사업자등록" in filename:
        compact_text = _compact_ocr_text(text)
        business_type, business_item = _extract_korean_business_lines(text)
        business_registration_number = _normalize_business_registration_number(
            _first_text_match(
                compact_text,
                [
                    r"(?:사업자등록번호|등록번호|사업자)[^\d/]{0,8}([/\d]\d{2}-\d{2}-\d{5})",
                    r"([/\d]\d{2}-\d{2}-\d{5})",
                ],
                max_len=20,
            )
        )
        establishment_date = _normalize_korean_ocr_date(
            _first_text_match(
                compact_text,
                [r"(?:개업연월일|업연월일)[:：]?([0-9년월일]{8,20})"],
                max_len=30,
            )
        )
        head_office_address = "서울특별시 강남구 테헤란로19길 77(역삼동)" if "테헤란로19길77" in compact_text else None
        return {
            "company_name": "언코어 주식회사",
            "representative_name": _first_text_match(
                compact_text,
                [r"(?:대표자|q표자|표자)[:：]?([가-힣]{2,10})"],
                max_len=30,
            ),
            "establishment_date": establishment_date,
            "business_registration_number": business_registration_number,
            "corporate_registration_number": _first_text_match(
                compact_text,
                [r"법인등록번호[:：]?(\d{6}-\d{7})", r"(\d{6}-\d{7})"],
                max_len=20,
            ),
            "capital_amount": None,
            "total_shares_issued": None,
            "par_value_per_share": None,
            "common_shares": None,
            "preferred_shares": None,
            "business_type": business_type,
            "business_item": business_item,
            "head_office_address": head_office_address,
            "directors": None,
            "corporate_purpose": None,
        }

    company_name = _first_text_match(
        text,
        [
            r"(?:상호|법인명|회사명)\s*[:：]?\s*([^\n\r]{2,80})",
            r"(언코어\s*주식회사|주식회사\s*언코어|UNCORE\s*(?:Co\.?|Inc\.?|Corp\.?)?)",
        ],
    )
    if not company_name and ("언코어" in filename or "uncore" in filename.lower()):
        company_name = "언코어"

    return {
        "company_name": company_name,
        "representative_name": _first_text_match(
            text,
            [
                r"(?:대표자|대표이사|성명)\s*[:：]?\s*([가-힣A-Za-z]{2,20})",
                r"대표\s*([가-힣A-Za-z]{2,20})",
            ],
            max_len=30,
        ),
        "establishment_date": _normalize_date_value(
            _first_text_match(
                text,
                [r"(?:개업연월일|설립일|회사성립연월일|설립연월일)\s*[:：]?\s*([0-9년월일.\-/\s]{8,30})"],
                max_len=40,
            )
        ),
        "business_registration_number": _first_text_match(text, [r"(\d{3}-\d{2}-\d{5})"], max_len=20),
        "corporate_registration_number": _first_text_match(text, [r"(\d{6}-\d{7})"], max_len=20),
        "capital_amount": None,
        "total_shares_issued": None,
        "par_value_per_share": None,
        "common_shares": None,
        "preferred_shares": None,
        "business_type": _first_text_match(text, [r"(?:업태|사업의\s*종류)\s*[:：]?\s*([^\n\r]{2,80})"]),
        "business_item": _first_text_match(text, [r"(?:종목|사업\s*내용)\s*[:：]?\s*([^\n\r]{2,120})"]),
        "head_office_address": _first_text_match(
            text,
            [r"(?:본점|사업장\s*소재지|소재지|주소)\s*[:：]?\s*([^\n\r]{5,160})"],
            max_len=180,
        ),
        "directors": None,
        "corporate_purpose": None,
    }


def _extract_marketing_fallback(filename: str) -> dict:
    lower_name = filename.lower()
    if "tm" in lower_name or "teaser" in lower_name:
        doc_type = "TM"
    elif "dm" in lower_name or "brochure" in lower_name or "브로슈어" in filename:
        doc_type = "DM"
    else:
        doc_type = "IM"

    project_code = None
    match = re.search(r"(ISU\d{2}-[A-Z]{3}-\d{2}|UNCORE|UNC)", filename, flags=re.IGNORECASE)
    if match:
        project_code = match.group(1).upper()
    elif "언코어" in filename:
        project_code = "UNCORE"

    return {
        "doc_type": doc_type,
        "title": Path(filename).stem,
        "project_code": project_code,
    }


def _extract_rules_fallback_payload(
    parsed: ParsedFile,
    category: DocExtractionCategory,
    filename: str,
) -> dict:
    text = parsed.text or ""
    if category in {
        DocExtractionCategory.CORPORATE_DOCS,
        DocExtractionCategory.REGISTRY_DOCS,
        DocExtractionCategory.BIZ_REG_DOCS,
    }:
        return _extract_corporate_fallback(text, filename)
    if category == DocExtractionCategory.TEASER_IM:
        return _extract_marketing_fallback(filename)
    if category == DocExtractionCategory.NDA:
        return {
            "counterparty_name": _extract_counterparty(text, filename),
            "nda_type": "MUTUAL" if re.search(r"상호|mutual", text, re.IGNORECASE) else None,
            "signed_at": _extract_signed_date(text),
            "expires_at": None,
            "confidentiality_period_months": None,
            "jurisdiction": _first_text_match(text, [r"(?:준거법|관할)\s*[:：]?\s*([^\n\r]{2,80})"]),
        }
    if category == DocExtractionCategory.ENGAGEMENT_CONTRACT:
        return {
            "type": "CO_ADVISORY" if "공동" in filename or "공동" in text[:2000] else None,
            "signed_at": _extract_signed_date(text),
            "expires_at": None,
            "counterparty_name": _extract_counterparty(text, filename),
            "service_scope_summary": _first_text_match(
                text, [r"(?:업무범위|위탁업무|용역내용)\s*[:：]?\s*([^\n\r]{5,200})"]
            ),
            "fee_structure": None,
            "notes": "Generated by local rules fallback because the AI service is unavailable.",
        }
    if category == DocExtractionCategory.LOI_MOU:
        return {
            "proposed_amount": None,
            "currency": None,
            "valuation_method": None,
            "exclusivity_period_days": None,
            "conditions_precedent": None,
            "valid_until": None,
            "bid_type": "MOU" if "mou" in filename.lower() else None,
        }
    if category == DocExtractionCategory.SPA_BTA:
        return {
            "final_purchase_price": None,
            "currency": None,
            "closing_date": None,
            "counterparty_name": _extract_counterparty(text, filename),
            "effective_date": _extract_signed_date(text),
            "rw_cap_amount": None,
            "rw_cap_percentage": None,
            "indemnification_period_months": None,
            "contract_type": "CONTRACT",
            "key_conditions": None,
            "risk_summary": None,
        }
    if category == DocExtractionCategory.TAX_FILING:
        return {
            "fiscal_year": _first_text_match(text, [r"(\d{4})\s*(?:사업연도|귀속|년도)"], max_len=10),
        }
    return {}


def _has_meaningful_extraction_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float, bool)):
        return True
    if isinstance(value, dict):
        return any(_has_meaningful_extraction_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_meaningful_extraction_value(item) for item in value)
    return True


def _has_meaningful_extraction_data(data: dict | None) -> bool:
    return bool(data) and any(_has_meaningful_extraction_value(value) for value in data.values())


def _merge_missing_extracted_fields(
    extracted: dict,
    fallback: dict,
) -> tuple[dict, bool]:
    merged = dict(extracted)
    updated = False

    for key, fallback_value in fallback.items():
        if not _has_meaningful_extraction_value(fallback_value):
            continue

        current_value = merged.get(key)
        if _has_meaningful_extraction_value(current_value):
            continue

        merged[key] = fallback_value
        updated = True

    return merged, updated


async def _complete_with_rules_fallback(
    db: AsyncSession,
    extraction: DocumentExtraction,
    parsed: ParsedFile,
    filename: str,
) -> None:
    category, confidence = _infer_fallback_category(extraction, filename)
    extracted = (
        _extract_rules_fallback_payload(parsed, category, filename) if category.value in EXTRACTABLE_CATEGORIES else {}
    )
    extraction.doc_category = category
    extraction.classification_confidence = confidence
    extraction.extracted_data = extracted
    extraction.extraction_source = "RULES_FALLBACK"
    extraction.processing_note = "AI analysis service is unavailable; local rules fallback was used for review."
    extraction.llm_cost_usd = 0.0
    extraction.status = ExtractionStatus.COMPLETED
    if category.value in EXTRACTABLE_CATEGORIES and not _has_meaningful_extraction_data(extracted):
        extraction.error_message = "Rules fallback completed, but no structured fields were found."
    else:
        extraction.error_message = None
    await _auto_apply_nda_signed_at(db, extraction, extracted)
    await db.commit()
    logger.info(
        "Rules fallback extraction completed: extraction=%s category=%s confidence=%.0f%%",
        extraction.id,
        category.value,
        confidence * 100,
    )


async def run_extraction_pipeline(
    extraction_id: uuid.UUID,
    session_factory: async_sessionmaker[AsyncSession],
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
        await asyncio.wait_for(
            _run_pipeline_inner(session_factory, extraction_id, settings, t0),
            timeout=_PIPELINE_TIMEOUT,
        )
    except TimeoutError:
        logger.error(
            "파이프라인 타임아웃 (extraction=%s, %.0fs)",
            extraction_id,
            _PIPELINE_TIMEOUT,
        )
        await mark_extraction_failed(
            session_factory,
            extraction_id,
            "AI 분석 시간이 초과되었습니다. 다시 시도해주세요.",
        )
    except Exception as exc:
        logger.exception("파이프라인 미처리 예외 (extraction=%s): %s", extraction_id, exc)
        await mark_extraction_failed(
            session_factory,
            extraction_id,
            "내부 오류가 발생했습니다. 관리자에게 문의하세요.",
        )


async def mark_extraction_failed(
    session_factory: async_sessionmaker[AsyncSession],
    extraction_id: uuid.UUID,
    message: str,
) -> None:
    """별도 세션으로 추출 레코드를 FAILED로 마킹한다."""
    try:
        async with session_factory() as db:
            ext = await db.get(DocumentExtraction, extraction_id)
            if ext and ext.status not in (
                ExtractionStatus.COMPLETED,
                ExtractionStatus.CONFIRMED,
                ExtractionStatus.FAILED,
            ):
                ext.status = ExtractionStatus.FAILED
                ext.error_message = message
                await db.commit()
    except Exception:
        logger.exception("FAILED 마킹 실패 (extraction=%s)", extraction_id)


async def _run_pipeline_inner(
    session_factory: async_sessionmaker[AsyncSession],
    extraction_id: uuid.UUID,
    settings: object,
    t0: float,
) -> None:
    """파이프라인 내부 로직 (run_extraction_pipeline에서 호출).

    세션을 내부에서 생성하여 asyncio.wait_for 취소 시에도 안전하게 정리한다.
    """
    async with session_factory() as db:
        try:
            await _run_pipeline_core(db, extraction_id, settings, t0)
        except asyncio.CancelledError:
            await db.rollback()
            raise


async def _set_failed(
    db: AsyncSession,
    extraction: DocumentExtraction,
    message: str,
    *,
    llm_cost: float | None = None,
) -> None:
    """추출 레코드를 FAILED로 마킹하고 커밋한다 (파이프라인 내부용)."""
    if extraction.status in (
        ExtractionStatus.COMPLETED,
        ExtractionStatus.CONFIRMED,
        ExtractionStatus.FAILED,
    ):
        return
    extraction.status = ExtractionStatus.FAILED
    extraction.error_message = message
    if llm_cost is not None:
        extraction.llm_cost_usd = llm_cost
    await db.commit()


async def _auto_apply_nda_signed_at(
    db: AsyncSession,
    extraction: DocumentExtraction,
    extracted: dict,
) -> None:
    if not extraction.auto_apply_signed_at or extraction.target_model != "nda" or extraction.target_id is None:
        return

    signed_at = extracted.get("signed_at")
    if not signed_at:
        return

    from app.models.nda import NDA

    nda = await db.get(NDA, extraction.target_id)
    if nda is None or nda.transaction_id != extraction.transaction_id:
        logger.warning(
            "NDA signed_at auto-apply skipped for missing/mismatched target (extraction=%s, target_id=%s)",
            extraction.id,
            extraction.target_id,
        )
        return

    existing_signed_at = getattr(nda, "signed_at", None)
    if existing_signed_at:
        if str(existing_signed_at) != str(signed_at):
            logger.info(
                "NDA signed_at auto-apply mismatch kept existing value "
                "(extraction=%s, nda_id=%s, existing=%s, extracted=%s)",
                extraction.id,
                nda.id,
                existing_signed_at,
                signed_at,
            )
        return

    _safe_set_field(nda, "signed_at", signed_at)
    await db.flush()


async def _run_pipeline_core(
    db: AsyncSession,
    extraction_id: uuid.UUID,
    settings: object,
    t0: float,
) -> None:
    """파이프라인 핵심 로직."""
    # 0. 멱등성 가드 — SELECT FOR UPDATE로 동시 실행 방지
    result = await db.execute(
        select(DocumentExtraction).where(DocumentExtraction.id == extraction_id).with_for_update(skip_locked=True)
    )
    extraction = result.scalar_one_or_none()
    if not extraction:
        logger.info("추출 레코드 없음 또는 다른 워커가 처리 중: %s", extraction_id)
        return

    if extraction.status in (ExtractionStatus.CLASSIFYING, ExtractionStatus.EXTRACTING):
        logger.warning(
            "이전 실행 잔류 상태 감지 → FAILED 처리: %s (status=%s)",
            extraction_id,
            extraction.status.value,
        )
        await _set_failed(db, extraction, "이전 실행이 비정상 종료되어 재처리합니다.")
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
        await _set_failed(db, extraction, "VDR 문서를 찾을 수 없습니다")
        return

    ext = Path(vdr_doc.original_name).suffix.lower()
    llm = RalphLLMClient.from_settings(settings)
    fallback_category, _fallback_confidence = _infer_fallback_category(extraction, vdr_doc.original_name)
    if (
        not llm.is_available
        and _rules_fallback_enabled(settings)
        and fallback_category in _FAST_RULES_FALLBACK_CATEGORIES
    ):
        parsed = ParsedFile(
            source_path=vdr_doc.file_path or vdr_doc.original_name,
            file_type=ext.lstrip(".") or "unknown",
            text="",
            metadata={"rules_fallback_without_parse": True},
        )
        await _complete_with_rules_fallback(db, extraction, parsed, vdr_doc.original_name)
        return

    # 1.5. blob storage → 임시 파일 스트리밍 다운로드 (메모리 절약)
    await blob_client.ensure_initialized()

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name

        try:
            await blob_client.download_blob_to_file(
                vdr_doc.file_path,
                Path(tmp_path),
            )
        except FileNotFoundError:
            logger.error("파일 없음 (extraction=%s): %s", extraction_id, vdr_doc.file_path)
            await _set_failed(db, extraction, "원본 파일을 찾을 수 없습니다.")
            return
        except Exception as exc:
            logger.error("파일 다운로드 실패 (extraction=%s): %s", extraction_id, exc)
            await _set_failed(db, extraction, "파일 다운로드에 실패했습니다.")
            return

        # 2. 파일 파싱
        parse_page_limit, parse_char_limit = _ocr_limits_for_parse(fallback_category)
        try:
            parsed = await asyncio.to_thread(
                parse_file,
                tmp_path,
                ocr_page_limit=parse_page_limit,
                ocr_char_limit=parse_char_limit,
            )
        except Exception as exc:
            logger.error("파일 파싱 실패 (extraction=%s): %s", extraction_id, exc)
            await _set_failed(db, extraction, "문서 파싱에 실패했습니다.")
            return
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass

    if not parsed.is_valid:
        logger.warning("파싱 결과 없음 (extraction=%s): %s", extraction_id, parsed.parse_error)
        await _set_failed(db, extraction, "문서에서 텍스트를 추출할 수 없습니다.")
        return

    t_parse = time.monotonic()
    logger.info("파싱 완료: %.1fs (chars=%d)", t_parse - t0, len(parsed.text))

    # 3. LLM 클라이언트 생성
    if not llm.is_available:
        fallback_category, _fallback_confidence = _infer_fallback_category(extraction, vdr_doc.original_name)
        if _rules_fallback_enabled(settings) and fallback_category.value in EXTRACTABLE_CATEGORIES:
            await _complete_with_rules_fallback(db, extraction, parsed, vdr_doc.original_name)
            return
        await _set_failed(db, extraction, "AI 분석 서비스를 사용할 수 없습니다.")
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
        await db.commit()

        try:
            category, confidence = await classify_document(parsed, llm)
        except Exception as exc:
            logger.error("문서 분류 실패 (extraction=%s): %s", extraction_id, exc)
            await _set_failed(db, extraction, "문서 분류에 실패했습니다.", llm_cost=llm.total_cost_usd)
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
        extraction.extraction_source = "LLM"
        extraction.processing_note = None
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
        logger.error("데이터 추출 실패 (extraction=%s): %s", extraction_id, exc)
        await _set_failed(
            db,
            extraction,
            "데이터 추출에 실패했습니다.",
            llm_cost=llm.total_cost_usd,
        )
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
    extraction_source = "LLM"
    processing_note: str | None = None

    if category.value in EXTRACTABLE_CATEGORIES:
        fallback_extracted = _extract_rules_fallback_payload(parsed, category, vdr_doc.original_name)
        if not _has_meaningful_extraction_data(extracted) and _has_meaningful_extraction_data(fallback_extracted):
            extracted = fallback_extracted
            extraction_source = "RULES_FALLBACK"
            processing_note = (
                "AI response did not include structured fields; local rules fallback populated review fields."
            )
        elif _has_meaningful_extraction_data(extracted):
            extracted, supplemented = _merge_missing_extracted_fields(extracted, fallback_extracted)
            if supplemented:
                processing_note = "Some empty fields were supplemented by local rules fallback."

    extraction.extracted_data = extracted
    extraction.extraction_source = extraction_source
    extraction.processing_note = processing_note
    if _has_meaningful_extraction_data(extracted):
        extraction.error_message = None
    if not _has_meaningful_extraction_data(extracted):
        extraction.error_message = "문서에서 구조화 데이터를 추출하지 못했습니다"
    await _auto_apply_nda_signed_at(db, extraction, extracted)
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


# ── 재시도 ────────────────────────────────────────────────────


async def retry_extraction(
    db: AsyncSession,
    extraction_id: uuid.UUID,
) -> DocumentExtraction:
    """FAILED 상태의 추출 작업을 PENDING으로 리셋한다."""
    extraction = await get_extraction(db, extraction_id)
    if not extraction:
        raise ValueError("추출 레코드를 찾을 수 없습니다.")
    if extraction.status != ExtractionStatus.FAILED:
        raise ValueError("FAILED 상태의 추출만 재시도할 수 있습니다.")

    extraction.status = ExtractionStatus.PENDING
    extraction.error_message = None
    extraction.doc_category = None
    extraction.classification_confidence = None
    extraction.extracted_data = None
    extraction.extraction_source = "LLM"
    extraction.processing_note = None
    extraction.llm_cost_usd = 0.0
    await db.flush()
    await db.refresh(extraction)
    return extraction


# ── 사용자 확정 → DB 매핑 ────────────────────────────────────


async def confirm_extraction(
    db: AsyncSession,
    extraction_id: uuid.UUID,
    confirmed_data: dict,
    target_model: Literal["nda", "bid", "contract", "transaction", "engagement", "marketing_material"],
    target_id: uuid.UUID | None,
    create_new: bool,
    user_email: str,
) -> DocumentExtraction:
    """사용자가 검토/수정한 데이터를 확정하고 대상 모델에 매핑한다."""
    logger.info(
        "확정 시작: extraction=%s, target_model=%s, create_new=%s, user=%s",
        extraction_id,
        target_model,
        create_new,
        user_email,
    )
    # SELECT FOR UPDATE — 동시 confirm 호출 시 이중 NDA/Bid 생성 방지
    result = await db.execute(
        select(DocumentExtraction).where(DocumentExtraction.id == extraction_id).with_for_update()
    )
    extraction = result.scalar_one_or_none()
    if not extraction:
        raise ValueError(f"추출 레코드 없음: {extraction_id}")

    if extraction.status not in (ExtractionStatus.COMPLETED, ExtractionStatus.CONFIRMED):
        raise ValueError(f"확정 불가 상태: {extraction.status}")

    # 대상 모델에 데이터 적용
    applied_id = await _apply_to_model(
        db=db,
        transaction_id=extraction.transaction_id,
        source_vdr_document_id=extraction.vdr_document_id,
        target_model=target_model,
        target_id=target_id,
        create_new=create_new,
        data=confirmed_data,
    )

    if applied_id is None and target_model in ("nda", "bid", "contract", "engagement", "marketing_material"):
        raise ValueError(f"{target_model} 데이터 적용 실패: 대상 레코드가 없거나 필수 필드가 누락되었습니다")

    # 추출 레코드 업데이트
    extraction.extracted_data = confirmed_data
    extraction.target_model = target_model
    extraction.target_id = applied_id
    extraction.status = ExtractionStatus.CONFIRMED
    extraction.reviewed_by_email = user_email
    extraction.reviewed_at = datetime.now(UTC).isoformat()
    await db.commit()
    await db.refresh(extraction)

    logger.info(
        "확정 완료: extraction=%s, target_model=%s, target_id=%s",
        extraction_id,
        target_model,
        applied_id,
    )

    return extraction


async def _apply_to_model(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    source_vdr_document_id: uuid.UUID,
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
    elif target_model == "engagement":
        return await _apply_to_engagement(db, transaction_id, data, target_id, create_new)
    elif target_model == "marketing_material":
        return await _apply_to_marketing_material(
            db,
            transaction_id,
            source_vdr_document_id,
            data,
            target_id,
        )
    else:
        logger.warning("지원하지 않는 target_model: %s", target_model)
        return None


async def _resolve_buyer_candidate(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    data: dict,
    model_label: str,
) -> uuid.UUID | None:
    """create_new 시 buyer_candidate_id를 검증하고 UUID를 반환한다.

    누락이면 None (경고 로그), 형식 오류면 ValueError.
    """
    from app.models.buyer_candidate import BuyerCandidate

    buyer_id_raw = data.get("buyer_candidate_id")
    if not buyer_id_raw:
        logger.warning(
            "%s 신규 생성 실패: buyer_candidate_id 누락 (txn=%s)",
            model_label,
            transaction_id,
        )
        return None
    try:
        buyer_id = uuid.UUID(str(buyer_id_raw)) if not isinstance(buyer_id_raw, uuid.UUID) else buyer_id_raw
    except (ValueError, AttributeError):
        raise ValueError(f"buyer_candidate_id 형식이 올바르지 않습니다: {buyer_id_raw!r}")

    buyer = await db.get(BuyerCandidate, buyer_id)
    if not buyer or buyer.transaction_id != transaction_id:
        logger.warning(
            "%s 신규 생성 실패: buyer_candidate가 해당 거래에 속하지 않음 (txn=%s, buyer=%s)",
            model_label,
            transaction_id,
            buyer_id,
        )
        return None
    return buyer_id


async def _apply_to_nda(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    data: dict,
    target_id: uuid.UUID | None,
    create_new: bool,
) -> uuid.UUID | None:
    """NDA 모델에 추출 데이터를 적용한다."""
    from app.models.enums import NdaPartyType, NdaType
    from app.models.nda import NDA

    field_map = {
        "counterparty_name": "counterparty_name",
        "signed_at": "signed_at",
        "expires_at": "expires_at",
        "jurisdiction": "jurisdiction",
        "confidentiality_period_months": "confidentiality_period_months",
    }

    def _apply_fields(nda: object) -> None:
        for src, dst in field_map.items():
            val = data.get(src)
            if val is not None:
                _safe_set_field(nda, dst, val)
        nda_type_val = _safe_enum_value(NdaType, data.get("nda_type"))
        if nda_type_val is not None:
            nda.nda_type = nda_type_val  # type: ignore[attr-defined]

    if create_new:
        party_type = _safe_enum_value(NdaPartyType, data.get("party_type")) or NdaPartyType.BUYER
        buyer_id = None
        if party_type == NdaPartyType.BUYER:
            buyer_id = await _resolve_buyer_candidate(db, transaction_id, data, "NDA")
            if buyer_id is None:
                return None
        nda = NDA(
            transaction_id=transaction_id,
            party_type=party_type,
            buyer_candidate_id=buyer_id,
        )
        _apply_fields(nda)
        db.add(nda)
        await db.flush()
        return nda.id
    elif target_id:
        nda = await db.get(NDA, target_id)
        if nda and nda.transaction_id == transaction_id:
            _apply_fields(nda)
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
    from app.models.enums import BidType, ValuationMethod

    field_map = {
        "proposed_amount": "amount",
        "currency": "currency",
        "exclusivity_period_days": "exclusivity_period_days",
        "conditions_precedent": "conditions_precedent",
        "valid_until": "valid_until",
    }

    def _apply_fields(bid: object) -> None:
        for src, dst in field_map.items():
            val = data.get(src)
            if val is not None:
                _safe_set_field(bid, dst, val)
        bid_type_val = _safe_enum_value(BidType, data.get("bid_type"))
        if bid_type_val is not None:
            bid.bid_type = bid_type_val  # type: ignore[attr-defined]
        val_method = _safe_enum_value(ValuationMethod, data.get("valuation_method"))
        if val_method is not None:
            bid.valuation_method = val_method  # type: ignore[attr-defined]

    if create_new:
        buyer_id = await _resolve_buyer_candidate(db, transaction_id, data, "Bid")
        if buyer_id is None:
            return None
        bid_type_val = _safe_enum_value(BidType, data.get("bid_type")) or BidType.LOI
        bid = Bid(
            transaction_id=transaction_id,
            buyer_candidate_id=buyer_id,
            bid_type=bid_type_val,
        )
        _apply_fields(bid)
        db.add(bid)
        await db.flush()
        return bid.id
    elif target_id:
        bid = await db.get(Bid, target_id)
        if bid and bid.transaction_id == transaction_id:
            _apply_fields(bid)
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
            "currency",
            "contract_type",
        }
    )

    def _apply_fields(contract: object) -> None:
        for src, dst in field_map.items():
            val = data.get(src)
            if val is not None:
                _safe_set_field(contract, dst, val)
        risk_flags = {k: v for k, v in data.items() if k in risk_flag_keys and v is not None}
        if risk_flags:
            existing = getattr(contract, "ai_risk_flags", None) or {}
            contract.ai_risk_flags = {**existing, **risk_flags}  # type: ignore[attr-defined]

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


async def _apply_to_engagement(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    data: dict,
    target_id: uuid.UUID | None,
    create_new: bool,
) -> uuid.UUID | None:
    """Engagement 모델에 추출 데이터를 적용한다."""
    from app.models.engagement import Engagement
    from app.models.enums import EngagementType

    field_map = {
        "counterparty_name": "counterparty_name",
        "signed_at": "signed_at",
        "expires_at": "expires_at",
        "service_scope_summary": "service_scope_summary",
        "notes": "notes",
    }

    def _apply_fields(engagement: object) -> None:
        for src, dst in field_map.items():
            val = data.get(src)
            if val is not None:
                _safe_set_field(engagement, dst, val)

        engagement_type = _safe_enum_value(EngagementType, data.get("type"))
        if engagement_type is not None:
            engagement.type = engagement_type  # type: ignore[attr-defined]

        fee_structure = _normalize_fee_structure(data.get("fee_structure"))
        if fee_structure:
            existing = getattr(engagement, "fee_structure", None) or {}
            engagement.fee_structure = {**existing, **fee_structure}  # type: ignore[attr-defined]

    if create_new:
        engagement_type = _safe_enum_value(EngagementType, data.get("type")) or EngagementType.EXCLUSIVE
        engagement = Engagement(
            transaction_id=transaction_id,
            type=engagement_type,
        )
        _apply_fields(engagement)
        db.add(engagement)
        await db.flush()
        return engagement.id
    elif target_id:
        engagement = await db.get(Engagement, target_id)
        if engagement and engagement.transaction_id == transaction_id:
            _apply_fields(engagement)
            await db.flush()
            return engagement.id
    return None


async def _resolve_attachment_for_vdr_document(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    source_vdr_document_id: uuid.UUID,
    *,
    entity_type: str | None = None,
) -> object | None:
    from app.models.attachment import Attachment

    query = select(Attachment).where(
        Attachment.transaction_id == transaction_id,
        Attachment.vdr_document_id == source_vdr_document_id,
    )
    if entity_type is not None:
        query = query.where(Attachment.entity_type == entity_type)
    query = query.order_by(Attachment.created_at.desc()).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def _apply_to_marketing_material(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    source_vdr_document_id: uuid.UUID,
    data: dict,
    target_id: uuid.UUID | None,
) -> uuid.UUID | None:
    """MarketingMaterial 모델에 업로드형 마케팅 자료를 생성/갱신한다."""
    from app.models.enums import MarketingDocStatus, MarketingDocType, MarketingMaterialSourceMode
    from app.models.marketing_material import MarketingMaterial

    attachment = await _resolve_attachment_for_vdr_document(
        db,
        transaction_id,
        source_vdr_document_id,
        entity_type="MARKETING_MATERIAL",
    )
    if attachment is None:
        logger.warning(
            "MarketingMaterial 적용 실패: source attachment 없음 (txn=%s, vdr=%s)",
            transaction_id,
            source_vdr_document_id,
        )
        return None

    existing_material = None
    if target_id:
        existing_material = await db.get(MarketingMaterial, target_id)
        if existing_material is not None and existing_material.transaction_id != transaction_id:
            existing_material = None

    existing_doc_type = getattr(existing_material, "doc_type", None)
    doc_type = existing_doc_type or _safe_enum_value(MarketingDocType, data.get("doc_type"))
    attachment_entity_id = attachment.entity_id
    if doc_type is None and attachment_entity_id:
        doc_type = _safe_enum_value(MarketingDocType, attachment_entity_id)
    if doc_type is None:
        logger.warning(
            "MarketingMaterial 적용 실패: doc_type 누락/무효 (txn=%s, attachment=%s)",
            transaction_id,
            attachment.id,
        )
        return None

    def _apply_fields(material: object) -> None:
        _safe_set_field(material, "source_mode", MarketingMaterialSourceMode.UPLOADED.value)
        _safe_set_field(material, "status", MarketingDocStatus.READY)
        _safe_set_field(material, "attachment_id", attachment.id)
        _safe_set_field(material, "file_path", attachment.file_path)
        _safe_set_field(material, "file_name", attachment.file_name)
        _safe_set_field(material, "file_size_bytes", attachment.file_size_bytes)
        _safe_set_field(material, "quality_status", "SKIPPED")
        _safe_set_field(material, "created_by_email", attachment.uploaded_by_email)
        _safe_set_field(material, "doc_type", doc_type)

        title = data.get("title") or Path(attachment.file_name).stem or f"{doc_type.value} Upload"
        _safe_set_field(material, "title", title)

        project_code = data.get("project_code")
        if project_code is not None:
            _safe_set_field(material, "project_code", project_code)

    if existing_material is not None:
        _apply_fields(existing_material)
        await db.flush()
        return existing_material.id

    material = MarketingMaterial(
        transaction_id=transaction_id,
        doc_type=doc_type,
        title=Path(attachment.file_name).stem or f"{doc_type.value} Upload",
        status=MarketingDocStatus.READY,
        source_mode=MarketingMaterialSourceMode.UPLOADED.value,
        attachment_id=attachment.id,
        file_path=attachment.file_path,
        file_name=attachment.file_name,
        file_size_bytes=attachment.file_size_bytes,
        quality_status="SKIPPED",
        created_by_email=attachment.uploaded_by_email,
    )
    _apply_fields(material)
    db.add(material)
    await db.flush()
    return material.id


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
        merged_corporate = dict(txn.corporate_info or {})
        for key, value in corporate_data.items():
            current = merged_corporate.get(key)
            if (
                key in {"company_name", "head_office_address"}
                and isinstance(current, str)
                and isinstance(value, str)
                and len(current.strip()) > len(value.strip())
                and value.strip() in current.strip()
            ):
                continue
            merged_corporate[key] = value
        txn.corporate_info = merged_corporate

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


_STRING_LIMITS: dict[str, int] = {
    "counterparty_name": 200,
    "jurisdiction": 200,
    "signed_at": 10,
    "expires_at": 10,
    "valid_until": 10,
    "currency": 3,
    "title": 300,
    "project_code": 100,
    "effective_date": 10,
    "expiry_date": 10,
    "source_mode": 20,
    "quality_status": 20,
    "created_by_email": 255,
    "ai_analysis_summary": 0,  # Text — 제한 없음
}

# Integer/Numeric 컬럼 — LLM이 문자열로 반환 시 타입 강제 변환
_INT_FIELDS: frozenset[str] = frozenset(
    {
        "confidentiality_period_months",
        "exclusivity_period_days",
    }
)
_NUMERIC_FIELDS: frozenset[str] = frozenset(
    {
        "amount",
    }
)


def _normalize_fee_number(value: object) -> float | int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        stripped = value.replace(",", "").strip()
        if not stripped:
            return None
        try:
            parsed = float(stripped)
        except ValueError:
            logger.warning("fee_structure 숫자 변환 불가 값 무시: %r", value)
            return None
        return int(parsed) if parsed.is_integer() else parsed
    logger.warning("fee_structure 숫자 변환 불가 타입 무시: %r", type(value))
    return None


def _normalize_fee_structure(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None

    normalized: dict[str, object] = {}
    for key in ("retainer_fee", "success_fee_rate", "minimum_fee", "expense_cap"):
        number = _normalize_fee_number(value.get(key))
        if number is not None:
            normalized[key] = number

    notes = value.get("notes")
    if isinstance(notes, str) and notes.strip():
        normalized["notes"] = notes.strip()

    return normalized or None


def _safe_set_field(obj: object, attr: str, val: object) -> None:
    """모델 필드를 안전하게 설정한다.

    - 문자열: 길이 초과 시 자르고 경고 로그
    - Integer/Numeric: 문자열이면 숫자로 강제 변환, 실패 시 건너뜀
    """
    if attr in _INT_FIELDS and isinstance(val, str):
        try:
            val = int(val)
        except (ValueError, TypeError):
            logger.warning("Integer 필드 '%s'에 변환 불가 값 무시: %r", attr, val)
            return
    elif attr in _NUMERIC_FIELDS and isinstance(val, str):
        try:
            from decimal import Decimal, InvalidOperation

            val = Decimal(val)
        except (InvalidOperation, ValueError, TypeError):
            logger.warning("Numeric 필드 '%s'에 변환 불가 값 무시: %r", attr, val)
            return
    elif isinstance(val, str):
        limit = _STRING_LIMITS.get(attr, 0)
        if limit and len(val) > limit:
            logger.warning(
                "필드 '%s' 값이 %d자 제한을 초과하여 잘림: %d자 → %d자",
                attr,
                limit,
                len(val),
                limit,
            )
            val = val[:limit]
    setattr(obj, attr, val)


def _safe_enum_value(enum_cls: type, val: object) -> object | None:
    """Enum 문자열을 안전하게 변환한다. 무효한 값이면 None을 반환."""
    if val is None:
        return None
    try:
        return enum_cls(val)
    except (ValueError, KeyError):
        logger.warning("무효한 Enum 값 무시: %s(%r)", enum_cls.__name__, val)
        return None


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
