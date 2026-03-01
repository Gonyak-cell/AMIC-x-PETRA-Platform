"""매수자 마케팅 활동 로그 + DART 연동 + Excel 내보내기 라우터."""

from __future__ import annotations

import io
import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.database import get_db
from app.core.dependencies import get_kiis_client
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.buyer_candidate import BuyerCandidate
from app.models.buyer_marketing_log import BuyerMarketingLog
from app.models.consortium_mapping import ConsortiumMapping
from app.models.enums import AuditAction, BuyerTier, MarketingStage
from app.schemas.marketing_log import (
    BuyerStageSummary,
    DartFinancialSummaryOut,
    MarketingLogCreate,
    MarketingLogOut,
    MarketingLogUpdate,
)
from app.services import audit_service, transaction_service
from app.services.buyer_export_service import build_buyer_excel
from app.services.platform_settings_service import get_or_create_settings
from app.services.protocols import KIISClientProtocol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions/{txn_id}", tags=["Buyer Marketing"])


# ── 헬퍼 ────────────────────────────────────────────────


async def _get_buyer(db: AsyncSession, txn_id: uuid.UUID, buyer_id: uuid.UUID) -> BuyerCandidate:
    q = select(BuyerCandidate).where(
        BuyerCandidate.id == buyer_id,
        BuyerCandidate.transaction_id == txn_id,
    )
    buyer = (await db.execute(q)).scalar_one_or_none()
    if buyer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="매수자 후보를 찾을 수 없습니다")
    return buyer


# ── 마케팅 로그 CRUD ──────────────────────────────────────


@router.get(
    "/buyers/{buyer_id}/marketing-logs",
    response_model=list[MarketingLogOut],
)
async def list_marketing_logs(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    stage: MarketingStage | None = Query(None),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[MarketingLogOut]:
    await check_client_deal_access(db, txn_id, claims)
    await _get_buyer(db, txn_id, buyer_id)

    q = select(BuyerMarketingLog).where(
        BuyerMarketingLog.buyer_id == buyer_id,
        BuyerMarketingLog.transaction_id == txn_id,
    )
    if stage:
        q = q.where(BuyerMarketingLog.stage == stage)
    q = q.order_by(BuyerMarketingLog.log_date.desc(), BuyerMarketingLog.created_at.desc())
    result = await db.execute(q)
    return [MarketingLogOut.model_validate(r) for r in result.scalars().all()]


@router.post(
    "/buyers/{buyer_id}/marketing-logs",
    response_model=MarketingLogOut,
    status_code=201,
)
async def create_marketing_log(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    body: MarketingLogCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> MarketingLogOut:
    await check_client_deal_access(db, txn_id, claims)
    await _get_buyer(db, txn_id, buyer_id)
    log = BuyerMarketingLog(
        buyer_id=buyer_id,
        transaction_id=txn_id,
        stage=body.stage,
        log_date=body.log_date,
        content=body.content,
        created_by_email=claims.email,
    )
    db.add(log)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="BuyerMarketingLog",
        entity_id=log.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(log)
    return MarketingLogOut.model_validate(log)


@router.patch(
    "/buyers/{buyer_id}/marketing-logs/{log_id}",
    response_model=MarketingLogOut,
)
async def update_marketing_log(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    log_id: uuid.UUID,
    body: MarketingLogUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> MarketingLogOut:
    await check_client_deal_access(db, txn_id, claims)
    q = select(BuyerMarketingLog).where(
        BuyerMarketingLog.id == log_id,
        BuyerMarketingLog.buyer_id == buyer_id,
        BuyerMarketingLog.transaction_id == txn_id,
    )
    log = (await db.execute(q)).scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="마케팅 로그를 찾을 수 없습니다")

    update_data = body.model_dump(exclude_unset=True)
    old_value = {k: getattr(log, k) for k in update_data}
    for k, v in update_data.items():
        setattr(log, k, v)

    await audit_service.record(
        db,
        entity_type="BuyerMarketingLog",
        entity_id=log.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        old_value=old_value,
        new_value=update_data,
    )
    await db.commit()
    await db.refresh(log)
    return MarketingLogOut.model_validate(log)


@router.delete(
    "/buyers/{buyer_id}/marketing-logs/{log_id}",
    status_code=204,
)
async def delete_marketing_log(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> None:
    await check_client_deal_access(db, txn_id, claims)
    q = select(BuyerMarketingLog).where(
        BuyerMarketingLog.id == log_id,
        BuyerMarketingLog.buyer_id == buyer_id,
        BuyerMarketingLog.transaction_id == txn_id,
    )
    log = (await db.execute(q)).scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="마케팅 로그를 찾을 수 없습니다")
    await audit_service.record(
        db,
        entity_type="BuyerMarketingLog",
        entity_id=log.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
        old_value={
            "stage": log.stage,
            "log_date": log.log_date,
            "content": log.content,
        },
    )
    await db.delete(log)
    await db.commit()


# ── 마케팅 단계 요약 ─────────────────────────────────────


@router.get(
    "/buyers/{buyer_id}/marketing-stage-summary",
    response_model=BuyerStageSummary,
)
async def marketing_stage_summary(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> BuyerStageSummary:
    """매수자별 6단계 마케팅 완료 현황 — 각 단계별 최신 일자."""
    await check_client_deal_access(db, txn_id, claims)
    await _get_buyer(db, txn_id, buyer_id)

    q = (
        select(BuyerMarketingLog.stage, func.max(BuyerMarketingLog.log_date).label("latest"))
        .where(
            BuyerMarketingLog.buyer_id == buyer_id,
            BuyerMarketingLog.transaction_id == txn_id,
        )
        .group_by(BuyerMarketingLog.stage)
    )
    result = await db.execute(q)

    stage_map: dict[str, str | None] = {s.value: None for s in MarketingStage}
    for row in result.all():
        stage_key = row.stage.value if isinstance(row.stage, MarketingStage) else str(row.stage)
        stage_map[stage_key] = row.latest

    return BuyerStageSummary(buyer_id=buyer_id, stages=stage_map)


# ── Short-List 전체 마케팅 현황 ──────────────────────────


@router.get(
    "/short-list/marketing-overview",
    response_model=list[BuyerStageSummary],
)
async def short_list_marketing_overview(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[BuyerStageSummary]:
    """Tier-1/2/3 매수자 전원의 마케팅 단계 완료 현황."""
    await check_client_deal_access(db, txn_id, claims)

    # Short-List = tier IS NOT NULL AND tier != NOT_TARGET
    buyers_q = select(BuyerCandidate.id).where(
        BuyerCandidate.transaction_id == txn_id,
        BuyerCandidate.tier.isnot(None),
        BuyerCandidate.tier != BuyerTier.NOT_TARGET,
    )
    buyer_result = await db.execute(buyers_q)
    buyer_ids = [row[0] for row in buyer_result.all()]

    if not buyer_ids:
        return []

    # 서브쿼리로 IN 절 최적화 (파라미터 리스트 대신 DB가 직접 실행)
    short_list_subq = buyers_q.scalar_subquery()
    logs_q = (
        select(
            BuyerMarketingLog.buyer_id,
            BuyerMarketingLog.stage,
            func.max(BuyerMarketingLog.log_date).label("latest"),
        )
        .where(
            BuyerMarketingLog.transaction_id == txn_id,
            BuyerMarketingLog.buyer_id.in_(short_list_subq),
        )
        .group_by(BuyerMarketingLog.buyer_id, BuyerMarketingLog.stage)
    )
    logs_result = await db.execute(logs_q)

    # buyer_id → stage → latest_date 매핑
    buyer_stages: dict[uuid.UUID, dict[str, str | None]] = {}
    for bid in buyer_ids:
        buyer_stages[bid] = {s.value: None for s in MarketingStage}

    for row in logs_result.all():
        bid = row.buyer_id
        stage_val = row.stage.value if isinstance(row.stage, MarketingStage) else str(row.stage)
        if bid in buyer_stages:
            buyer_stages[bid][stage_val] = row.latest

    return [BuyerStageSummary(buyer_id=bid, stages=stages) for bid, stages in buyer_stages.items()]


# ── DART 연동 ────────────────────────────────────────────


@router.get("/buyers/dart-search")
async def dart_company_search(
    txn_id: uuid.UUID,
    q: str = Query(..., min_length=1, alias="q"),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
    kiis: KIISClientProtocol = Depends(get_kiis_client),
) -> list[dict]:
    """DART 기업 typeahead 검색 — KIIS 서비스 경유."""
    await check_client_deal_access(db, txn_id, claims)

    try:
        results = await kiis.search_company(q)
        return results[:20]  # 최대 20건 반환
    except Exception:
        logger.warning("DART 기업 검색 실패: query=%s", q, exc_info=True)
        return []


@router.get("/buyers/{buyer_id}/dart-summary", response_model=DartFinancialSummaryOut)
async def dart_financial_summary(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
    kiis: KIISClientProtocol = Depends(get_kiis_client),
) -> DartFinancialSummaryOut:
    """매수자의 DART 재무 요약 — corp_code 기반."""
    await check_client_deal_access(db, txn_id, claims)
    buyer = await _get_buyer(db, txn_id, buyer_id)

    if not buyer.corp_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="corp_code가 설정되지 않았습니다. 회사명으로 DART 기업을 먼저 매핑하세요.",
        )

    try:
        summary = await kiis.get_financial_summary(buyer.corp_code)
        return DartFinancialSummaryOut(**summary)
    except Exception:
        logger.warning("DART 재무 요약 조회 실패: corp_code=%s", buyer.corp_code, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="KIIS DART 서비스 응답 실패",
        )


# ── Excel 내보내기 ───────────────────────────────────────


@router.get("/buyers/export-excel")
async def export_buyers_excel(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> StreamingResponse:
    """Long-List 전체를 Excel로 내보내기 (19열: 역할/컨소시엄/마케팅 포함)."""
    await check_client_deal_access(db, txn_id, claims)
    txn = await transaction_service.get_transaction(db, txn_id)

    q = select(BuyerCandidate).where(BuyerCandidate.transaction_id == txn_id).order_by(BuyerCandidate.created_at)
    result = await db.execute(q)
    buyers = list(result.scalars().all())

    # 마케팅 최신 stage/log_date 집계
    mkt_q = (
        select(
            BuyerMarketingLog.buyer_id,
            BuyerMarketingLog.stage,
            func.max(BuyerMarketingLog.log_date).label("latest_date"),
        )
        .where(BuyerMarketingLog.transaction_id == txn_id)
        .group_by(BuyerMarketingLog.buyer_id, BuyerMarketingLog.stage)
    )
    mkt_result = await db.execute(mkt_q)
    # buyer_id → (latest_stage, latest_date) — 전체 중 최신 1개
    marketing_latest: dict[uuid.UUID, tuple[str | None, str | None]] = {}
    for row in mkt_result.all():
        bid = row.buyer_id
        stage_val = row.stage.value if isinstance(row.stage, MarketingStage) else str(row.stage)
        date_val = row.latest_date
        existing = marketing_latest.get(bid)
        if existing is None or (date_val and (existing[1] is None or date_val > existing[1])):
            marketing_latest[bid] = (stage_val, date_val)

    # 컨소시엄 관계 — buyer_id별 관련 회사명 수집
    lead_bc = aliased(BuyerCandidate)
    co_bc = aliased(BuyerCandidate)
    cons_q = (
        select(
            ConsortiumMapping.lead_buyer_id,
            ConsortiumMapping.co_investor_buyer_id,
            lead_bc.company_name,
            co_bc.company_name,
        )
        .join(lead_bc, ConsortiumMapping.lead_buyer_id == lead_bc.id)
        .join(co_bc, ConsortiumMapping.co_investor_buyer_id == co_bc.id)
        .where(ConsortiumMapping.transaction_id == txn_id)
    )
    cons_result = await db.execute(cons_q)
    consortium_map: dict[uuid.UUID, list[str]] = {}
    for row in cons_result.all():
        lead_id, co_id, lead_name, co_name = row[0], row[1], row[2], row[3]
        consortium_map.setdefault(lead_id, []).append(co_name)
        consortium_map.setdefault(co_id, []).append(lead_name)

    # 플랫폼 설정에서 테이블 스타일 조회 (실패 시 DEFAULT 폴백)
    try:
        platform_settings = await get_or_create_settings(db)
        table_style = platform_settings.table_style
    except Exception:
        logger.warning("플랫폼 설정 조회 실패 — DEFAULT 스타일로 폴백")
        table_style = "DEFAULT"

    wb = build_buyer_excel(
        buyers,
        txn.code_name or txn.name,
        marketing_latest=marketing_latest,
        consortium_map=consortium_map,
        table_style=table_style,
    )
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    safe_name = re.sub(r"[^\w\s\-.]", "_", txn.code_name or txn.name)
    filename = f"Long-List_{safe_name}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
