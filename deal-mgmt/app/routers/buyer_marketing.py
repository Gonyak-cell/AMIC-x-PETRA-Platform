"""매수자 마케팅 활동 로그 + DART 연동 + Excel 내보내기 라우터.

내부적으로 meeting_logs 테이블을 사용 (080 마이그레이션 이후 통합).
기존 marketing-log API 응답 형식(MarketingLogOut)은 호환 유지.
"""

from __future__ import annotations

import io
import logging
import re
import urllib.parse
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.database import get_db
from app.core.dependencies import get_kiis_client
from app.core.rate_limiter import dart_rate_limiter, export_rate_limiter
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.buyer_candidate import BuyerCandidate
from app.models.consortium_mapping import ConsortiumMapping
from app.models.enums import AuditAction, MarketingStage, MeetingChannel, MeetingPhase, MeetingStatus
from app.models.meeting_log import MeetingLog
from app.schemas.marketing_log import (
    BuyerStageSummary,
    DartFinancialSummaryOut,
    MarketingLogCreate,
    MarketingLogOut,
    MarketingLogUpdate,
)
from app.services import audit_service, transaction_service
from app.services.buyer_export_service import build_buyer_excel
from app.services.buyer_status_service import (
    auto_advance_buyer_status,
    check_status_after_delete,
    get_advance_target,
    sync_transaction_short_list_memberships,
)
from app.services.platform_settings_service import get_or_create_settings
from app.services.protocols import KIISClientProtocol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions/{txn_id}", tags=["Buyer Marketing"])

# 마케팅 단계 라벨 (title 자동 생성용)
_STAGE_LABELS: dict[MarketingStage, str] = {
    MarketingStage.IDENTIFIED: "매수자 식별",
    MarketingStage.TEASER_SENT: "Teaser 배포",
    MarketingStage.NDA_SIGNED: "NDA 체결",
    MarketingStage.IM_DISTRIBUTED: "IM 배포",
    MarketingStage.QNA_COMPLETED: "Q&A 완료",
    MarketingStage.MGMT_PRESENTATION: "경영진 프레젠테이션",
    MarketingStage.LOI_RECEIVED: "LOI 접수",
    MarketingStage.DD_IN_PROGRESS: "DD 진행",
}

# MarketingLogUpdate 필드 → MeetingLog 필드 매핑
_FIELD_MAP: dict[str, str] = {
    "stage": "marketing_stage",
    "log_date": "meeting_date",
    "content": "summary",
}


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


def _to_marketing_out(log: MeetingLog) -> MarketingLogOut:
    """MeetingLog → MarketingLogOut 호환 변환."""
    return MarketingLogOut.model_validate(
        {
            "id": log.id,
            "buyer_id": log.buyer_id,
            "transaction_id": log.transaction_id,
            "stage": log.marketing_stage,
            "log_date": log.meeting_date,
            "content": log.summary,
            "created_by_email": log.created_by_email,
            "created_at": log.created_at,
            "updated_at": log.updated_at,
        }
    )


# ── 마케팅 로그 읽기 (meeting_logs 테이블 호환 레이어) ────
# ⚠️ DEPRECATED: 080 마이그레이션 이후 meeting-logs API로 대체됨.
#    MaterialTracker 등 buyer별 마케팅 히스토리 읽기 전용으로만 유지.
#    모든 활동 기록 CRUD는 /transactions/{txn_id}/meeting-logs API 사용.


@router.get(
    "/buyers/{buyer_id}/marketing-logs",
    response_model=list[MarketingLogOut],
    deprecated=True,
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

    q = select(MeetingLog).where(
        MeetingLog.buyer_id == buyer_id,
        MeetingLog.transaction_id == txn_id,
        MeetingLog.meeting_phase == MeetingPhase.MARKETING,
    )
    if stage:
        q = q.where(MeetingLog.marketing_stage == stage)
    q = q.order_by(MeetingLog.meeting_date.desc(), MeetingLog.created_at.desc())
    result = await db.execute(q)
    return [_to_marketing_out(r) for r in result.scalars().all()]


@router.post(
    "/buyers/{buyer_id}/marketing-logs",
    response_model=MarketingLogOut,
    status_code=201,
    deprecated=True,
)
async def create_marketing_log(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    body: MarketingLogCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> MarketingLogOut:
    await check_client_deal_access(db, txn_id, claims)
    buyer = await _get_buyer(db, txn_id, buyer_id)

    label = _STAGE_LABELS.get(body.stage, body.stage.value)
    title = f"{label} — {body.content[:50]}" if body.content else label

    log = MeetingLog(
        buyer_id=buyer_id,
        transaction_id=txn_id,
        meeting_phase=MeetingPhase.MARKETING,
        title=title[:300],
        meeting_date=body.log_date,
        channel=MeetingChannel.EMAIL,
        status=MeetingStatus.COMPLETED,
        summary=body.content,
        marketing_stage=body.stage,
        attendee_count=0,
        created_by_email=claims.email,
    )
    db.add(log)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="MeetingLog",
        entity_id=log.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    # 마케팅 스테이지에 대응하는 buyer.status 자동 승격 (실패 격리)
    advance_target = get_advance_target(body.stage)
    if advance_target is not None:
        try:
            await auto_advance_buyer_status(db, buyer, advance_target, claims.email)
        except Exception:
            logger.warning("auto_advance failed for buyer %s", buyer_id, exc_info=True)
    await db.commit()
    await db.refresh(log)
    return _to_marketing_out(log)


@router.patch(
    "/buyers/{buyer_id}/marketing-logs/{log_id}",
    response_model=MarketingLogOut,
    deprecated=True,
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
    await transaction_service.get_transaction(db, txn_id)
    q = select(MeetingLog).where(
        MeetingLog.id == log_id,
        MeetingLog.buyer_id == buyer_id,
        MeetingLog.transaction_id == txn_id,
        MeetingLog.meeting_phase == MeetingPhase.MARKETING,
    )
    log = (await db.execute(q)).scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="마케팅 로그를 찾을 수 없습니다")

    update_data = body.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    for k in update_data:
        ml_field = _FIELD_MAP.get(k, k)
        v = getattr(log, ml_field)
        old_value[k] = v.value if hasattr(v, "value") and not isinstance(v, str) else v
    for k, v in update_data.items():
        ml_field = _FIELD_MAP.get(k, k)
        setattr(log, ml_field, v)

    # title 자동 재생성
    if "stage" in update_data or "content" in update_data:
        stage = log.marketing_stage
        content = log.summary
        label = _STAGE_LABELS.get(stage, stage.value) if stage else ""
        log.title = (f"{label} — {content[:50]}" if content else label)[:300]

    await audit_service.record(
        db,
        entity_type="MeetingLog",
        entity_id=log.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        old_value=old_value,
        new_value=update_data,
    )

    # 마케팅 스테이지 변경 시 buyer status 자동 승격
    if "stage" in update_data and log.marketing_stage:
        buyer = await _get_buyer(db, txn_id, buyer_id)
        advance_target = get_advance_target(log.marketing_stage)
        if advance_target is not None:
            try:
                await auto_advance_buyer_status(db, buyer, advance_target, claims.email)
            except Exception:
                logger.warning("auto_advance failed for buyer %s", buyer_id, exc_info=True)

    await db.commit()
    await db.refresh(log)
    return _to_marketing_out(log)


@router.delete(
    "/buyers/{buyer_id}/marketing-logs/{log_id}",
    status_code=204,
    deprecated=True,
)
async def delete_marketing_log(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> None:
    await check_client_deal_access(db, txn_id, claims)
    await transaction_service.get_transaction(db, txn_id)
    q = select(MeetingLog).where(
        MeetingLog.id == log_id,
        MeetingLog.buyer_id == buyer_id,
        MeetingLog.transaction_id == txn_id,
        MeetingLog.meeting_phase == MeetingPhase.MARKETING,
    )
    log = (await db.execute(q)).scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="마케팅 로그를 찾을 수 없습니다")
    # 삭제되는 스테이지 정보를 먼저 캡처
    deleted_stage = log.marketing_stage
    await audit_service.record(
        db,
        entity_type="MeetingLog",
        entity_id=log.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
        old_value={
            "stage": deleted_stage.value if hasattr(deleted_stage, "value") else str(deleted_stage),
            "log_date": log.meeting_date,
            "content": log.summary,
        },
    )
    # 자동 승격 트리거 스테이지 삭제 시 감사 경고 기록
    if deleted_stage:
        await check_status_after_delete(db, buyer_id, deleted_stage, claims.email)
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
    """매수자별 8단계 마케팅 완료 현황 — 각 단계별 최신 일자."""
    await check_client_deal_access(db, txn_id, claims)
    await _get_buyer(db, txn_id, buyer_id)

    q = (
        select(MeetingLog.marketing_stage, func.max(MeetingLog.meeting_date).label("latest"))
        .where(
            MeetingLog.buyer_id == buyer_id,
            MeetingLog.transaction_id == txn_id,
            MeetingLog.meeting_phase == MeetingPhase.MARKETING,
            MeetingLog.marketing_stage.is_not(None),
        )
        .group_by(MeetingLog.marketing_stage)
    )
    result = await db.execute(q)

    stage_map: dict[str, str | None] = {s.value: None for s in MarketingStage}
    for row in result.all():
        stage_key = (
            row.marketing_stage.value if isinstance(row.marketing_stage, MarketingStage) else str(row.marketing_stage)
        )
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
    """Short-List(is_short_listed=True) 매수자 전원의 마케팅 단계 완료 현황."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await sync_transaction_short_list_memberships(db, txn_id)

    # Short-List = is_short_listed 플래그 기반
    buyers_q = select(BuyerCandidate.id).where(
        BuyerCandidate.transaction_id == txn_id,
        BuyerCandidate.is_short_listed.is_(True),
    )
    buyer_result = await db.execute(buyers_q)
    buyer_ids = [row[0] for row in buyer_result.all()]

    if not buyer_ids:
        return []

    # 서브쿼리로 IN 절 최적화
    short_list_subq = buyers_q.scalar_subquery()
    logs_q = (
        select(
            MeetingLog.buyer_id,
            MeetingLog.marketing_stage,
            func.max(MeetingLog.meeting_date).label("latest"),
        )
        .where(
            MeetingLog.transaction_id == txn_id,
            MeetingLog.buyer_id.in_(short_list_subq),
            MeetingLog.meeting_phase == MeetingPhase.MARKETING,
            MeetingLog.marketing_stage.is_not(None),
        )
        .group_by(MeetingLog.buyer_id, MeetingLog.marketing_stage)
    )
    logs_result = await db.execute(logs_q)

    # buyer_id → stage → latest_date 매핑
    buyer_stages: dict[uuid.UUID, dict[str, str | None]] = {}
    for bid in buyer_ids:
        buyer_stages[bid] = {s.value: None for s in MarketingStage}

    for row in logs_result.all():
        bid = row.buyer_id
        stage_val = (
            row.marketing_stage.value if isinstance(row.marketing_stage, MarketingStage) else str(row.marketing_stage)
        )
        if bid in buyer_stages:
            buyer_stages[bid][stage_val] = row.latest

    return [BuyerStageSummary(buyer_id=bid, stages=stages) for bid, stages in buyer_stages.items()]


# ── DART 연동 ────────────────────────────────────────────


@router.get("/buyers/dart-search", response_model=list[dict])
async def dart_company_search(
    txn_id: uuid.UUID,
    q: str = Query(..., min_length=1, max_length=100, alias="q"),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
    kiis: KIISClientProtocol = Depends(get_kiis_client),
) -> list[dict]:
    """DART 기업 typeahead 검색 — KIIS 서비스 경유."""
    await check_client_deal_access(db, txn_id, claims)
    await transaction_service.get_transaction(db, txn_id)
    dart_rate_limiter.check(claims.email)

    try:
        results = await kiis.search_company(q)
        return results[:20]  # 최대 20건 반환
    except Exception:
        logger.warning("DART 기업 검색 실패", exc_info=True)
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
    export_rate_limiter.check(claims.email)
    txn = await transaction_service.get_transaction(db, txn_id)

    q = select(BuyerCandidate).where(BuyerCandidate.transaction_id == txn_id).order_by(BuyerCandidate.created_at)
    result = await db.execute(q)
    buyers = list(result.scalars().all())

    # 마케팅 최신 stage/meeting_date 집계 (meeting_logs 기반)
    mkt_q = (
        select(
            MeetingLog.buyer_id,
            MeetingLog.marketing_stage,
            func.max(MeetingLog.meeting_date).label("latest_date"),
        )
        .where(
            MeetingLog.transaction_id == txn_id,
            MeetingLog.meeting_phase == MeetingPhase.MARKETING,
            MeetingLog.marketing_stage.is_not(None),
        )
        .group_by(MeetingLog.buyer_id, MeetingLog.marketing_stage)
    )
    mkt_result = await db.execute(mkt_q)
    # buyer_id → (latest_stage, latest_date) — 전체 중 최신 1개
    marketing_latest: dict[uuid.UUID, tuple[str | None, str | None]] = {}
    for row in mkt_result.all():
        bid = row.buyer_id
        stage_val = (
            row.marketing_stage.value if isinstance(row.marketing_stage, MarketingStage) else str(row.marketing_stage)
        )
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

    try:
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
    except Exception:
        logger.exception("Excel 내보내기 실패: txn_id=%s", txn_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Excel 파일 생성 중 오류가 발생했습니다",
        )

    safe_name = re.sub(r"[^\w\s\-.]", "_", txn.code_name or txn.name, flags=re.ASCII)
    filename = f"Long-List_{safe_name}.xlsx"
    encoded_filename = urllib.parse.quote(filename)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded_filename}"),
        },
    )
