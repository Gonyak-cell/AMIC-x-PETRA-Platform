"""Gemini File API 기반 VDR 문서 분류 서비스.

기존 2차 심사(텍스트 샘플 5000자 → LLM) 대신 Gemini File API를 통해
전체 문서를 1M 토큰 컨텍스트로 전달하여 분류 정확도를 높인다.

흐름:
  Blob Storage → 임시 파일 → Gemini File API 업로드
  → generate_content([file_ref, prompt]) → JSON 파싱 → 폴더 재배치
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import tempfile
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import VdrClassificationStatus, VdrFolderCategory
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder

logger = logging.getLogger(__name__)

_CONFIDENCE_THRESHOLD = 0.6
_CLASSIFY_TIMEOUT = 120.0

# 12개 카테고리 (vdr_classification_service와 동일)
_CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "CORPORATE": "기업 일반 자료 — 정관, 등기부등본, 주주명부, 이사회 의사록, 조직도",
    "FINANCIAL": "재무 자료 — 재무제표, 감사보고서, 시산표, 원가분석, 예산",
    "LEGAL": "법률 자료 — 계약서, NDA, 소송 자료, 법률 의견서, 인허가 문서",
    "TAX": "세무 자료 — 세무신고서, 세금계산서, 이전가격 보고서, 세무조정",
    "HR": "인사/노무 — 취업규칙, 급여대장, 근로계약서, 노사협의, 퇴직금",
    "TECHNICAL": "기술/IT — 시스템 구성도, 기술 문서, 소프트웨어 라이선스, 특허 기술",
    "COMMERCIAL": "영업/마케팅 — 매출 분석, 고객 목록, 유통 계약, 마케팅 전략",
    "REAL_ESTATE": "부동산/자산 — 등기부, 감정평가서, 임대차 계약, 시설 관리",
    "ENVIRONMENT": "환경 — 환경영향평가, 오염 검사, 폐기물 관리, 환경 인허가",
    "IP": "지식재산권 — 특허, 상표, 저작권, 영업비밀, 기술이전 계약",
    "INSURANCE": "보험 — 보험증권, 보상 내역, 리스크 평가, 배상책임",
    "MARKET_RESEARCH": "시장자료 — 산업 분석, 경쟁사 분석, 시장 규모, 트렌드 보고서",
}

_VALID_CATEGORIES = set(_CATEGORY_DESCRIPTIONS.keys())

_CLASSIFICATION_PROMPT = """\
당신은 M&A 실사(Due Diligence) VDR(Virtual Data Room) 문서를 분류하는 전문가입니다.
첨부된 문서 전체를 분석하여 가장 적합한 카테고리 하나를 선택하세요.

카테고리 목록:
{categories}

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트를 추가하지 마세요.
{{"category": "카테고리_영문키", "confidence": 0.0~1.0}}
"""


def _build_category_list() -> str:
    """LLM 프롬프트용 카테고리 목록 텍스트."""
    return "\n".join(f"- {k}: {v}" for k, v in _CATEGORY_DESCRIPTIONS.items())


def _parse_response(raw: str) -> tuple[str | None, float]:
    """Gemini JSON 응답 파싱 → (category, confidence)."""
    try:
        json_match = re.search(r"\{[^{}]*\}", raw)
        if not json_match:
            return None, 0.0
        data = json.loads(json_match.group())
        category = data.get("category", "").upper()
        confidence = float(data.get("confidence", 0.0))
        if category not in _VALID_CATEGORIES:
            return None, 0.0
        return category, confidence
    except (json.JSONDecodeError, ValueError, TypeError):
        return None, 0.0


async def classify_with_file_api(
    db: AsyncSession,
    document_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> VdrClassificationStatus | None:
    """Gemini File API로 전체 문서 기반 분류를 시도한다.

    Returns:
        CLASSIFIED — 분류 성공 (폴더 이동 완료)
        None — Gemini 분류 실패/불확실 → 호출자가 기존 LLM 폴백 사용
    """
    from app.core.blob_storage import blob_client
    from app.core.config import settings

    # 1. 문서 조회
    stmt = select(VdrDocument).where(
        VdrDocument.id == document_id,
        VdrDocument.transaction_id == transaction_id,
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        return None

    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        logger.warning("GOOGLE_API_KEY 미설정 — Gemini 분류 건너뜀")
        return None

    # 2. Blob → 임시 파일 다운로드
    await blob_client.ensure_initialized()
    tmp_dir = Path(tempfile.gettempdir()) / "gemini_classify"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{document_id}_{doc.stored_name}"

    try:
        await blob_client.download_blob_to_file(doc.stored_name, tmp_path)
    except Exception:
        logger.exception("Blob 다운로드 실패: doc=%s", document_id)
        return None

    try:
        # 3. Gemini File API 업로드 + 분류 호출
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        def _sync_classify() -> str:
            uploaded = genai.upload_file(
                path=str(tmp_path),
                display_name=doc.original_name or "untitled",
            )
            model = genai.GenerativeModel(settings.GEMINI_CLASSIFICATION_MODEL)
            prompt = _CLASSIFICATION_PROMPT.format(categories=_build_category_list())
            response = model.generate_content([uploaded, prompt])
            return response.text

        raw = await asyncio.wait_for(
            asyncio.to_thread(_sync_classify),
            timeout=_CLASSIFY_TIMEOUT,
        )
    except TimeoutError:
        logger.warning("Gemini 분류 타임아웃 (%ss): doc=%s", _CLASSIFY_TIMEOUT, document_id)
        return None
    except Exception:
        logger.exception("Gemini 분류 호출 실패: doc=%s", document_id)
        return None
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    # 4. 응답 파싱
    category_str, confidence = _parse_response(raw)
    if category_str is None or confidence < _CONFIDENCE_THRESHOLD:
        logger.info(
            "Gemini 분류 불확실 (category=%s, confidence=%.2f): doc=%s",
            category_str,
            confidence,
            document_id,
        )
        return None

    # 5. 폴더 이동
    target_category = VdrFolderCategory(category_str)
    target_folder = await _resolve_folder(db, transaction_id, target_category)
    if target_folder is None:
        logger.warning("Gemini 분류 결과 폴더 없음: category=%s, txn=%s", category_str, transaction_id)
        return None

    doc.folder_id = target_folder.id
    doc.classification_status = VdrClassificationStatus.CLASSIFIED
    doc.classification_score = int(confidence * 100)
    doc.manual_review_needed = False
    await db.flush()

    logger.info(
        "Gemini 분류 성공: doc=%s → %s (confidence=%.2f)",
        document_id,
        category_str,
        confidence,
    )
    return VdrClassificationStatus.CLASSIFIED


async def _resolve_folder(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    category: VdrFolderCategory,
) -> VdrFolder | None:
    """카테고리에 해당하는 최상위 VDR 폴더 조회."""
    stmt = (
        select(VdrFolder)
        .where(
            VdrFolder.transaction_id == transaction_id,
            VdrFolder.category == category,
            VdrFolder.parent_id.is_(None),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
