"""AI 기반 초기 RFI 질의 자동 생성 서비스.

LLM을 활용하여 산업군/거래 목적/중점 영역에 따른 RFI 질의 초안을 생성한다.
RalphLLMClient 폴백 체인(Anthropic → OpenAI → Google)을 활용.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RFICategoryV2, RFIPriority
from app.models.rfi_item_v2 import RFIItemV2
from app.ralph.llm_client import RalphLLMClient

logger = logging.getLogger(__name__)

# ── 프롬프트 ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
당신은 M&A 자문 전문가입니다. 대상회사에 보낼 RFI(Request for Information) 질의 목록을 작성합니다.

## 규칙
1. 각 질의는 다음 JSON 형식으로 출력합니다:
   {"category": "...", "question_text": "...", "priority": "...", "target_doc": "...", "report_section_tag": "..."}
2. category는 다음 중 하나: FINANCIAL, LEGAL, OPERATIONAL, COMMERCIAL, HR, IT, ENVIRONMENTAL, INSURANCE, IP, REAL_ESTATE, VALUATION, CORPORATE, TAX, OTHER
3. priority는: HIGH, MEDIUM, LOW
4. target_doc은 해당 질의가 활용될 문서 (IM, TM, QoE, LDD, HR DD 등)
5. report_section_tag는 보고서 목차 매핑 (QoE, NWC, Revenue_Analysis, Contingent_Liabilities, Employment, IP_Portfolio 등)
6. 질문은 구체적이고 실무적이어야 합니다. 일반적/추상적 질문 금지.
7. 산업 특성과 거래 목적에 맞는 질문을 생성합니다.
8. 출력은 JSON 배열만 반환합니다. 추가 텍스트/설명 금지.

## 카테고리별 질의 수 가이드
- FINANCIAL: 8~12개 (핵심)
- LEGAL: 5~8개
- HR: 3~5개
- OPERATIONAL: 3~5개
- COMMERCIAL: 3~5개
- TAX: 2~4개
- 나머지: 산업 특성에 따라 1~3개
"""


def _build_user_prompt(
    industry: str,
    deal_purpose: str,
    focus_areas: list[str],
    additional_context: str,
) -> str:
    """사용자 프롬프트를 동적으로 구성한다."""
    parts = [
        "## 거래 정보",
        f"- 산업군: {industry}",
        f"- 거래 목적: {deal_purpose}",
    ]
    if focus_areas:
        parts.append(f"- 중점 분석 영역: {', '.join(focus_areas)}")
    if additional_context:
        parts.append(f"- 추가 컨텍스트: {additional_context}")

    parts.append("\n위 거래 정보를 기반으로 RFI 질의 목록을 JSON 배열로 생성하세요.")
    return "\n".join(parts)


# 유효한 enum 값 세트 (빠른 검증용)
_VALID_CATEGORIES = {e.value for e in RFICategoryV2}
_VALID_PRIORITIES = {e.value for e in RFIPriority}


def _parse_llm_response(raw: str) -> list[dict[str, str]]:
    """LLM 응답에서 JSON 배열을 추출하고 유효성을 검증한다."""
    # JSON 블록 추출 (```json ... ``` 또는 순수 JSON)
    text = raw.strip()
    if "```" in text:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start : end + 1]

    items: list[dict[str, str]] = json.loads(text)
    if not isinstance(items, list):
        raise ValueError("LLM 응답이 JSON 배열이 아닙니다")

    validated: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        question = item.get("question_text", "").strip()
        if not question:
            continue

        category = item.get("category", "OTHER").upper()
        if category not in _VALID_CATEGORIES:
            category = "OTHER"

        priority = item.get("priority", "MEDIUM").upper()
        if priority not in _VALID_PRIORITIES:
            priority = "MEDIUM"

        validated.append(
            {
                "category": category,
                "question_text": question,
                "priority": priority,
                "target_doc": item.get("target_doc", ""),
                "report_section_tag": item.get("report_section_tag", ""),
            }
        )

    return validated


async def generate_rfi_items(
    db: AsyncSession,
    txn_id: uuid.UUID,
    *,
    industry: str,
    deal_purpose: str,
    focus_areas: list[str],
    additional_context: str,
    created_by_email: str,
    llm_client: RalphLLMClient,
) -> tuple[int, float, str]:
    """AI로 RFI 질의를 생성하고 DB에 저장한다.

    Returns:
        (생성된 항목 수, 비용 USD, 사용 모델명)
    """
    user_prompt = _build_user_prompt(industry, deal_purpose, focus_areas, additional_context)

    cost_before = llm_client.total_cost_usd
    raw_response = await llm_client.call(SYSTEM_PROMPT, user_prompt, max_tokens=8192)
    cost_after = llm_client.total_cost_usd
    cost_delta = cost_after - cost_before

    # 마지막 호출에 사용된 모델 추출
    tracker = llm_client.cost_tracker
    model_used = "unknown"
    if tracker.usage_by_model:
        model_used = list(tracker.usage_by_model.keys())[-1]

    try:
        parsed = _parse_llm_response(raw_response)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("AI RFI 생성: LLM 응답 파싱 실패 (txn=%s): %s", txn_id, exc)
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail="AI 응답을 파싱할 수 없습니다. 다시 시도해 주세요.",
        ) from exc
    if not parsed:
        logger.warning("AI RFI 생성: 유효한 질의가 없습니다 (txn=%s)", txn_id)
        return 0, cost_delta, model_used

    # DB에 저장 — 각 item마다 현재 count 기반 채번 (rfi_v2_service._next_item_number 동일 로직)
    year = datetime.now(UTC).year
    created = 0
    for item_data in parsed:
        count_result = await db.execute(select(func.count(RFIItemV2.id)).where(RFIItemV2.transaction_id == txn_id))
        seq = (count_result.scalar() or 0) + 1
        item = RFIItemV2(
            id=uuid.uuid4(),
            transaction_id=txn_id,
            item_number=f"RFI-{year}-{seq:03d}",
            category=RFICategoryV2(item_data["category"]),
            priority=RFIPriority(item_data["priority"]),
            target_doc=item_data.get("target_doc") or None,
            question_text=item_data["question_text"],
            report_section_tag=item_data.get("report_section_tag") or None,
            created_by_email=created_by_email,
        )
        db.add(item)
        await db.flush()  # 다음 채번을 위해 즉시 flush
        created += 1
    logger.info(
        "AI RFI 생성 완료: txn=%s, items=%d, cost=$%.4f, model=%s",
        txn_id,
        created,
        cost_delta,
        model_used,
    )

    return created, cost_delta, model_used
