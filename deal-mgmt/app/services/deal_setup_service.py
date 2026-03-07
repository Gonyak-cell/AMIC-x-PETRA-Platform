"""딜 셋업 AI 에이전트 — 서비스 로직.

자연어/엑셀 → LLM → JSON 미리보기 → 사용자 확인 → DB 벌크 저장.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.buyer_candidate import BuyerCandidate
from app.models.dd_checklist import DDChecklist
from app.models.enums import (
    BuyerCandidateStatus,
    BuyerType,
    DDChecklistStatus,
    TransactionPhase,
    TransactionStatus,
)
from app.models.timeline import DealTimeline
from app.models.transaction import Transaction
from app.ralph.llm_client import RalphLLMClient
from app.schemas.deal_setup import (
    DealSetupConfirm,
    DealSetupPreview,
    DealSetupResult,
)
from app.services import audit_service
from app.services.deal_setup_prompts import (
    DEAL_SETUP_EXCEL_USER_TEMPLATE,
    DEAL_SETUP_SYSTEM,
    DEAL_SETUP_USER_TEMPLATE,
)
from app.services.transaction_service import _generate_code_name

logger = logging.getLogger(__name__)


def _parse_llm_json(text: str) -> dict:
    """LLM 응답에서 JSON을 추출한다.

    마크다운 코드 펜스(```json ... ```) 제거 후 파싱.
    """
    # 마크다운 펜스 제거
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.replace("```", "").strip()
    return json.loads(cleaned)


async def generate_deal_setup_preview(
    description: str,
    *,
    llm_client: RalphLLMClient,
) -> DealSetupPreview:
    """자연어 설명으로 딜 구조 미리보기를 생성한다."""
    user_prompt = DEAL_SETUP_USER_TEMPLATE.format(description=description)
    return await _call_llm_and_parse(user_prompt, llm_client=llm_client)


async def generate_deal_setup_from_excel(
    file_bytes: bytes,
    *,
    llm_client: RalphLLMClient,
) -> DealSetupPreview:
    """엑셀 파일을 파싱하여 딜 구조 미리보기를 생성한다."""
    from app.ralph.parsers.excel_parser import parse_excel

    parsed = parse_excel(file_bytes)
    excel_text = parsed.text if hasattr(parsed, "text") else str(parsed)
    user_prompt = DEAL_SETUP_EXCEL_USER_TEMPLATE.format(excel_text=excel_text[:8000])
    return await _call_llm_and_parse(user_prompt, llm_client=llm_client)


async def _call_llm_and_parse(
    user_prompt: str,
    *,
    llm_client: RalphLLMClient,
) -> DealSetupPreview:
    """LLM 호출 → JSON 파싱 → DealSetupPreview 반환."""
    cost_before = llm_client.total_cost_usd

    raw_text = await llm_client.call(DEAL_SETUP_SYSTEM, user_prompt)
    cost_after = llm_client.total_cost_usd
    cost_usd = cost_after - cost_before

    # 사용된 모델 추정 (마지막 호출 기반)
    tracker = llm_client.cost_tracker
    model_used = "unknown"
    if tracker.usage_by_model:
        model_used = list(tracker.usage_by_model.keys())[-1]

    try:
        data = _parse_llm_json(raw_text)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("LLM JSON 파싱 실패, 1회 재시도: %s", exc)
        # 1회 재시도
        raw_text = await llm_client.call(DEAL_SETUP_SYSTEM, user_prompt)
        cost_usd = llm_client.total_cost_usd - cost_before
        data = _parse_llm_json(raw_text)

    data["cost_usd"] = round(cost_usd, 6)
    data["model_used"] = model_used

    return DealSetupPreview.model_validate(data)


async def confirm_deal_setup(
    db: AsyncSession,
    preview: DealSetupConfirm,
    *,
    actor_email: str,
) -> DealSetupResult:
    """미리보기 확인 → DB에 Transaction + DD Checklist + Timeline + Buyers 벌크 저장."""
    from app.models.enums import AuditAction

    txn_data = preview.transaction
    year = datetime.now().year
    code_name = await _generate_code_name(db, txn_data.deal_type, txn_data.name, year)

    # 1. Transaction 생성
    txn = Transaction(
        code_name=code_name,
        name=txn_data.name,
        deal_type=txn_data.deal_type,
        side=txn_data.side,
        target_company_name=txn_data.target_company_name,
        client_name=txn_data.client_name,
        estimated_deal_value=(
            Decimal(str(txn_data.estimated_deal_value)) if txn_data.estimated_deal_value is not None else None
        ),
        currency=txn_data.currency,
        deal_structure=txn_data.deal_structure,
        industry=txn_data.industry,
        target_close_date=txn_data.target_close_date,
        notes=txn_data.notes,
        lead_advisor_email=preview.lead_advisor_email,
        phase=TransactionPhase.ENGAGEMENT,
        status=TransactionStatus.DRAFT,
    )
    db.add(txn)
    await db.flush()

    await audit_service.record(
        db,
        entity_type="Transaction",
        entity_id=txn.id,
        action=AuditAction.CREATE,
        actor_email=actor_email,
        new_value={"code_name": code_name, "name": txn_data.name, "source": "AI_SETUP"},
    )

    # 2. DD Checklist 벌크 INSERT
    dd_count = 0
    for item in preview.dd_checklist:
        db.add(
            DDChecklist(
                transaction_id=txn.id,
                workstream=item.workstream,
                title=item.title,
                description=item.description,
                due_date=item.due_date,
                status=DDChecklistStatus.NOT_STARTED,
            )
        )
        dd_count += 1

    # 3. Timeline 벌크 INSERT
    tl_count = 0
    for item in preview.timeline:
        db.add(
            DealTimeline(
                transaction_id=txn.id,
                event_type=item.event_type,
                title=item.title,
                description=item.description,
                event_date=item.event_date,
                is_auto_generated=True,
                created_by=actor_email,
            )
        )
        tl_count += 1

    # 4. Buyer Candidates 벌크 INSERT
    buyer_count = 0
    for item in preview.buyer_candidates:
        db.add(
            BuyerCandidate(
                transaction_id=txn.id,
                company_name=item.company_name,
                buyer_type=item.buyer_type or BuyerType.OTHER,
                status=BuyerCandidateStatus.IDENTIFIED,
                tier=item.tier,
                notes=item.notes,
            )
        )
        buyer_count += 1

    await db.commit()
    await db.refresh(txn)

    return DealSetupResult(
        transaction_id=txn.id,
        dd_checklist_count=dd_count,
        timeline_count=tl_count,
        buyer_count=buyer_count,
    )
