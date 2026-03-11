"""미팅 로그 라우터 — 마케팅/협상 공용 CRUD + 참석자 + 액션아이템."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.buyer_candidate import BuyerCandidate
from app.models.enums import AuditAction, MarketingStage, MeetingChannel, MeetingPhase, MeetingStatus
from app.models.meeting_action_item import MeetingActionItem
from app.models.meeting_attendee import MeetingAttendee
from app.models.meeting_log import MeetingLog
from app.schemas.meeting_action_item import (
    MeetingActionItemCreate,
    MeetingActionItemListResponse,
    MeetingActionItemOut,
    MeetingActionItemUpdate,
)
from app.schemas.meeting_log import (
    MeetingAttendeeCreate,
    MeetingAttendeeOut,
    MeetingAttendeeUpdate,
    MeetingLogCreate,
    MeetingLogDetail,
    MeetingLogListResponse,
    MeetingLogOut,
    MeetingLogSummary,
    MeetingLogUpdate,
)
from app.services import audit_service, buyer_status_service, transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions/{txn_id}/meeting-logs", tags=["Meeting Logs"])


# ── 미팅 로그 CRUD ──────────────────────────────────────


@router.get("", response_model=MeetingLogListResponse)
async def list_meeting_logs(
    txn_id: uuid.UUID,
    meeting_phase: MeetingPhase | None = None,
    status_filter: MeetingStatus | None = Query(None, alias="status"),
    channel: MeetingChannel | None = None,
    buyer_id: uuid.UUID | None = None,
    marketing_stage: MarketingStage | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    q = select(MeetingLog).where(MeetingLog.transaction_id == txn_id)
    count_q = select(func.count(MeetingLog.id)).where(MeetingLog.transaction_id == txn_id)

    if meeting_phase:
        q = q.where(MeetingLog.meeting_phase == meeting_phase)
        count_q = count_q.where(MeetingLog.meeting_phase == meeting_phase)
    if status_filter:
        q = q.where(MeetingLog.status == status_filter)
        count_q = count_q.where(MeetingLog.status == status_filter)
    if channel:
        q = q.where(MeetingLog.channel == channel)
        count_q = count_q.where(MeetingLog.channel == channel)
    if buyer_id:
        q = q.where(MeetingLog.buyer_id == buyer_id)
        count_q = count_q.where(MeetingLog.buyer_id == buyer_id)
    if marketing_stage:
        q = q.where(MeetingLog.marketing_stage == marketing_stage)
        count_q = count_q.where(MeetingLog.marketing_stage == marketing_stage)

    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(MeetingLog.meeting_date.desc(), MeetingLog.created_at.desc())
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    items = [MeetingLogOut.model_validate(m) for m in result.scalars().all()]
    return MeetingLogListResponse(items=items, total=total)


@router.get("/summary", response_model=MeetingLogSummary)
async def meeting_log_summary(
    txn_id: uuid.UUID,
    meeting_phase: MeetingPhase | None = None,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    base = MeetingLog.transaction_id == txn_id
    phase_filter = MeetingLog.meeting_phase == meeting_phase if meeting_phase else None

    # 총 건수
    count_q = select(func.count(MeetingLog.id)).where(base)
    if phase_filter is not None:
        count_q = count_q.where(phase_filter)
    total: int = (await db.execute(count_q)).scalar() or 0

    # status별 GROUP BY
    status_q = select(MeetingLog.status, func.count(MeetingLog.id).label("cnt")).where(base).group_by(MeetingLog.status)
    if phase_filter is not None:
        status_q = status_q.where(phase_filter)
    by_status: dict[str, int] = {row.status.value: row.cnt for row in (await db.execute(status_q)).all()}

    # channel별 GROUP BY
    channel_q = (
        select(MeetingLog.channel, func.count(MeetingLog.id).label("cnt")).where(base).group_by(MeetingLog.channel)
    )
    if phase_filter is not None:
        channel_q = channel_q.where(phase_filter)
    by_channel: dict[str, int] = {row.channel.value: row.cnt for row in (await db.execute(channel_q)).all()}

    return MeetingLogSummary(total=total, by_status=by_status, by_channel=by_channel)


@router.get("/{log_id}", response_model=MeetingLogDetail)
async def get_meeting_log(
    txn_id: uuid.UUID,
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await check_client_deal_access(db, txn_id, claims)
    log = await _get_log_or_404(db, txn_id, log_id)

    # 참석자 조회
    att_q = select(MeetingAttendee).where(MeetingAttendee.meeting_id == log_id).order_by(MeetingAttendee.created_at)
    attendees = [MeetingAttendeeOut.model_validate(a) for a in (await db.execute(att_q)).scalars().all()]

    # 액션아이템 조회
    ai_q = (
        select(MeetingActionItem).where(MeetingActionItem.meeting_id == log_id).order_by(MeetingActionItem.created_at)
    )
    action_items = [MeetingActionItemOut.model_validate(a) for a in (await db.execute(ai_q)).scalars().all()]

    detail = MeetingLogDetail.model_validate(log)
    detail.attendees = attendees
    detail.action_items = action_items
    return detail


@router.post("", response_model=MeetingLogOut, status_code=201)
async def create_meeting_log(
    txn_id: uuid.UUID,
    body: MeetingLogCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    # buyer_id가 지정된 경우 같은 거래 소속인지 검증
    if body.buyer_id is not None:
        buyer_q = select(BuyerCandidate).where(
            BuyerCandidate.id == body.buyer_id,
            BuyerCandidate.transaction_id == txn_id,
        )
        if not (await db.execute(buyer_q)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="해당 거래에 속하지 않는 매수자입니다",
            )

    attendees_data = body.attendees or []
    log_data = body.model_dump(exclude={"attendees"})
    log = MeetingLog(transaction_id=txn_id, created_by_email=claims.email, **log_data)
    log.attendee_count = len(attendees_data)
    db.add(log)
    await db.flush()

    # 참석자 인라인 생성
    for att in attendees_data:
        attendee = MeetingAttendee(meeting_id=log.id, **att.model_dump())
        db.add(attendee)

    await audit_service.record(
        db,
        entity_type="MeetingLog",
        entity_id=log.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value={"title": body.title, "phase": body.meeting_phase},
    )

    # 마케팅 단계 자동 승격: marketing_stage가 있고 buyer_id가 있으면 buyer status 승격
    # 실패 시 미팅 로그 자체는 유지 (부가 효과 격리)
    if body.marketing_stage and body.buyer_id:
        target = buyer_status_service.get_advance_target(body.marketing_stage)
        if target:
            buyer_q = select(BuyerCandidate).where(BuyerCandidate.id == body.buyer_id)
            buyer = (await db.execute(buyer_q)).scalar_one_or_none()
            if buyer:
                try:
                    await buyer_status_service.auto_advance_buyer_status(
                        db,
                        buyer,
                        target,
                        claims.email,
                    )
                except Exception:
                    logger.warning("auto_advance failed for buyer %s", body.buyer_id, exc_info=True)

    await db.commit()
    await db.refresh(log)
    return MeetingLogOut.model_validate(log)


@router.patch("/{log_id}", response_model=MeetingLogOut)
async def update_meeting_log(
    txn_id: uuid.UUID,
    log_id: uuid.UUID,
    body: MeetingLogUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await check_client_deal_access(db, txn_id, claims)
    log = await _get_log_or_404(db, txn_id, log_id)
    update_data = body.model_dump(exclude_unset=True)

    # P2: buyer_id 변경 시 같은 거래 소속 검증
    if "buyer_id" in update_data and update_data["buyer_id"] is not None:
        buyer_q = select(BuyerCandidate).where(
            BuyerCandidate.id == update_data["buyer_id"],
            BuyerCandidate.transaction_id == txn_id,
        )
        if not (await db.execute(buyer_q)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="해당 거래에 속하지 않는 매수자입니다",
            )

    old_value = {k: getattr(log, k) for k in update_data}
    for k, v in update_data.items():
        setattr(log, k, v)
    await audit_service.record(
        db,
        entity_type="MeetingLog",
        entity_id=log.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        old_value=old_value,
        new_value=update_data,
    )

    # marketing_stage 변경 시 buyer status 자동 승격 (실패 격리)
    if "marketing_stage" in update_data and log.marketing_stage and log.buyer_id:
        target = buyer_status_service.get_advance_target(log.marketing_stage)
        if target:
            buyer_q = select(BuyerCandidate).where(BuyerCandidate.id == log.buyer_id)
            buyer = (await db.execute(buyer_q)).scalar_one_or_none()
            if buyer:
                try:
                    await buyer_status_service.auto_advance_buyer_status(
                        db,
                        buyer,
                        target,
                        claims.email,
                    )
                except Exception:
                    logger.warning("auto_advance failed for buyer %s", log.buyer_id, exc_info=True)

    await db.commit()
    await db.refresh(log)
    return MeetingLogOut.model_validate(log)


@router.delete("/{log_id}", status_code=204)
async def delete_meeting_log(
    txn_id: uuid.UUID,
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await check_client_deal_access(db, txn_id, claims)
    log = await _get_log_or_404(db, txn_id, log_id)
    await audit_service.record(
        db,
        entity_type="MeetingLog",
        entity_id=log.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )

    # 마케팅 로그 삭제 시 buyer status 검토 경고 감사 로그
    if log.marketing_stage and log.buyer_id:
        await buyer_status_service.check_status_after_delete(
            db,
            log.buyer_id,
            log.marketing_stage,
            claims.email,
        )

    await db.delete(log)
    await db.commit()


# ── 참석자 CRUD ──────────────────────────────────────────


@router.post("/{log_id}/attendees", response_model=MeetingAttendeeOut, status_code=201)
async def add_attendee(
    txn_id: uuid.UUID,
    log_id: uuid.UUID,
    body: MeetingAttendeeCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    log = await _get_log_or_404(db, txn_id, log_id)

    # 이메일 기반 중복 참석 방지
    if body.email:
        dup_q = select(MeetingAttendee).where(
            MeetingAttendee.meeting_id == log_id,
            MeetingAttendee.email == body.email,
        )
        if (await db.execute(dup_q)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 등록된 참석자(이메일)입니다")

    attendee = MeetingAttendee(meeting_id=log_id, **body.model_dump())
    db.add(attendee)
    log.attendee_count = log.attendee_count + 1
    await db.flush()
    await audit_service.record(
        db,
        entity_type="MeetingAttendee",
        entity_id=attendee.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value={"name": body.name, "meeting_id": log_id},
    )
    await db.commit()
    await db.refresh(attendee)
    return MeetingAttendeeOut.model_validate(attendee)


@router.patch("/{log_id}/attendees/{att_id}", response_model=MeetingAttendeeOut)
async def update_attendee(
    txn_id: uuid.UUID,
    log_id: uuid.UUID,
    att_id: uuid.UUID,
    body: MeetingAttendeeUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await _get_log_or_404(db, txn_id, log_id)
    attendee = await _get_attendee_or_404(db, log_id, att_id)
    update_data = body.model_dump(exclude_unset=True)
    old_value = {k: getattr(attendee, k) for k in update_data}
    for k, v in update_data.items():
        setattr(attendee, k, v)
    await audit_service.record(
        db,
        entity_type="MeetingAttendee",
        entity_id=attendee.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        old_value=old_value,
        new_value=update_data,
    )
    await db.commit()
    await db.refresh(attendee)
    return MeetingAttendeeOut.model_validate(attendee)


@router.delete("/{log_id}/attendees/{att_id}", status_code=204)
async def remove_attendee(
    txn_id: uuid.UUID,
    log_id: uuid.UUID,
    att_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    log = await _get_log_or_404(db, txn_id, log_id)
    attendee = await _get_attendee_or_404(db, log_id, att_id)
    await audit_service.record(
        db,
        entity_type="MeetingAttendee",
        entity_id=attendee.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(attendee)
    log.attendee_count = max(0, log.attendee_count - 1)
    await db.commit()


# ── 액션아이템 CRUD ──────────────────────────────────────


@router.get("/{log_id}/action-items", response_model=MeetingActionItemListResponse)
async def list_action_items(
    txn_id: uuid.UUID,
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await check_client_deal_access(db, txn_id, claims)
    await _get_log_or_404(db, txn_id, log_id)
    q = select(MeetingActionItem).where(MeetingActionItem.meeting_id == log_id).order_by(MeetingActionItem.created_at)
    result = await db.execute(q)
    items = [MeetingActionItemOut.model_validate(a) for a in result.scalars().all()]
    return MeetingActionItemListResponse(items=items, total=len(items))


@router.post("/{log_id}/action-items", response_model=MeetingActionItemOut, status_code=201)
async def create_action_item(
    txn_id: uuid.UUID,
    log_id: uuid.UUID,
    body: MeetingActionItemCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await _get_log_or_404(db, txn_id, log_id)
    item = MeetingActionItem(meeting_id=log_id, **body.model_dump())
    db.add(item)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="MeetingActionItem",
        entity_id=item.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value={"title": body.title, "meeting_id": log_id},
    )
    await db.commit()
    await db.refresh(item)
    return MeetingActionItemOut.model_validate(item)


@router.patch("/{log_id}/action-items/{item_id}", response_model=MeetingActionItemOut)
async def update_action_item(
    txn_id: uuid.UUID,
    log_id: uuid.UUID,
    item_id: uuid.UUID,
    body: MeetingActionItemUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await _get_log_or_404(db, txn_id, log_id)
    item = await _get_action_item_or_404(db, log_id, item_id)
    update_data = body.model_dump(exclude_unset=True)
    old_value = {k: getattr(item, k) for k in update_data}
    for k, v in update_data.items():
        setattr(item, k, v)
    await audit_service.record(
        db,
        entity_type="MeetingActionItem",
        entity_id=item.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        old_value=old_value,
        new_value=update_data,
    )
    await db.commit()
    await db.refresh(item)
    return MeetingActionItemOut.model_validate(item)


@router.delete("/{log_id}/action-items/{item_id}", status_code=204)
async def delete_action_item(
    txn_id: uuid.UUID,
    log_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await _get_log_or_404(db, txn_id, log_id)
    item = await _get_action_item_or_404(db, log_id, item_id)
    await audit_service.record(
        db,
        entity_type="MeetingActionItem",
        entity_id=item.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(item)
    await db.commit()


# ── 헬퍼 ────────────────────────────────────────────────


async def _get_log_or_404(db: AsyncSession, txn_id: uuid.UUID, log_id: uuid.UUID) -> MeetingLog:
    q = select(MeetingLog).where(MeetingLog.id == log_id, MeetingLog.transaction_id == txn_id)
    log = (await db.execute(q)).scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="미팅 로그를 찾을 수 없습니다")
    return log


async def _get_attendee_or_404(db: AsyncSession, meeting_id: uuid.UUID, att_id: uuid.UUID) -> MeetingAttendee:
    q = select(MeetingAttendee).where(MeetingAttendee.id == att_id, MeetingAttendee.meeting_id == meeting_id)
    att = (await db.execute(q)).scalar_one_or_none()
    if att is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="참석자를 찾을 수 없습니다")
    return att


async def _get_action_item_or_404(db: AsyncSession, meeting_id: uuid.UUID, item_id: uuid.UUID) -> MeetingActionItem:
    q = select(MeetingActionItem).where(MeetingActionItem.id == item_id, MeetingActionItem.meeting_id == meeting_id)
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="액션아이템을 찾을 수 없습니다")
    return item
