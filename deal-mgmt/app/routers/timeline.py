"""딜 타임라인 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.enums import AuditAction, TransactionPhase
from app.models.timeline import DealTimeline
from app.schemas.timeline import (
    GanttMilestone,
    GanttResponse,
    PhaseBar,
    TimelineEventCreate,
    TimelineEventOut,
    TimelineResponse,
)
from app.services import audit_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/timeline", tags=["Timeline"])


@router.get("", response_model=TimelineResponse)
async def list_timeline(
    txn_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    count_q = select(func.count()).select_from(DealTimeline).where(DealTimeline.transaction_id == txn_id)
    total = (await db.execute(count_q)).scalar_one()

    q = (
        select(DealTimeline)
        .where(DealTimeline.transaction_id == txn_id)
        .order_by(DealTimeline.event_date.desc(), DealTimeline.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(q)
    items = [TimelineEventOut.model_validate(e) for e in result.scalars().all()]
    return TimelineResponse(items=items, total=total)


@router.post("", response_model=TimelineEventOut, status_code=201)
async def add_timeline_event(
    txn_id: uuid.UUID,
    body: TimelineEventCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    event = DealTimeline(
        transaction_id=txn_id,
        is_auto_generated=False,
        created_by=claims.email,
        **body.model_dump(),
    )
    db.add(event)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="DealTimeline",
        entity_id=event.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(event)
    return TimelineEventOut.model_validate(event)


@router.delete("/{event_id}", status_code=204)
async def delete_timeline_event(
    txn_id: uuid.UUID,
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(DealTimeline).where(
        DealTimeline.id == event_id,
        DealTimeline.transaction_id == txn_id,
        DealTimeline.is_auto_generated.is_(False),
    )
    event = (await db.execute(q)).scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="이벤트를 찾을 수 없거나 자동 생성된 이벤트입니다",
        )
    await audit_service.record(
        db,
        entity_type="DealTimeline",
        entity_id=event.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(event)
    await db.commit()


# ── Phase 순서 및 레이블 매핑 ─────────────────────────────

_PHASE_ORDER: list[tuple[TransactionPhase, str]] = [
    (TransactionPhase.ENGAGEMENT, "수임"),
    (TransactionPhase.PREPARATION, "준비"),
    (TransactionPhase.MARKETING, "마케팅"),
    (TransactionPhase.BIDDING, "입찰"),
    (TransactionPhase.MAIN_DUE_DILIGENCE, "본실사"),
    (TransactionPhase.NEGOTIATION, "협상"),
    (TransactionPhase.CLOSING, "Closing"),
    (TransactionPhase.POST_CLOSING, "Post-Closing"),
]


@router.get("/gantt", response_model=GanttResponse)
async def get_gantt_timeline(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """딜 간트 타임라인 — phase별 시작/종료일 + 마일스톤."""
    txn = await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    # PHASE_TRANSITION 이벤트 조회 (날짜 오름차순)
    q = (
        select(DealTimeline)
        .where(
            DealTimeline.transaction_id == txn_id,
            DealTimeline.event_type == "PHASE_TRANSITION",
        )
        .order_by(DealTimeline.event_date.asc(), DealTimeline.created_at.asc())
    )
    transitions = (await db.execute(q)).scalars().all()

    # phase 전환 이벤트에서 각 phase의 시작일 추출
    # 타이틀 형식: "ENGAGEMENT → PREPARATION"
    phase_start_dates: dict[str, str] = {}
    for t in transitions:
        parts = t.title.split(" → ")
        if len(parts) == 2:
            to_phase = parts[1].strip()
            phase_start_dates[to_phase] = t.event_date

    # deal 생성일 = ENGAGEMENT 시작일
    deal_start = txn.created_at.strftime("%Y-%m-%d")

    # 현재 phase 인덱스
    current_phase_idx = next(
        (i for i, (p, _) in enumerate(_PHASE_ORDER) if p.value == txn.phase.value),
        0,
    )

    # phase 바 생성
    phases: list[PhaseBar] = []
    for idx, (phase_enum, label) in enumerate(_PHASE_ORDER):
        phase_val = phase_enum.value

        start = deal_start if idx == 0 else phase_start_dates.get(phase_val)

        if idx < current_phase_idx:
            # 완료된 phase: 다음 phase의 시작일 = 이 phase의 종료일
            next_phase_val = _PHASE_ORDER[idx + 1][0].value
            end = phase_start_dates.get(next_phase_val)
            phase_status = "completed"
        elif idx == current_phase_idx:
            end = None  # 진행 중
            phase_status = "active"
        else:
            phase_status = "upcoming"
            start = None
            end = None

        phases.append(
            PhaseBar(
                phase=phase_val,
                label=label,
                start_date=start,
                end_date=end,
                status=phase_status,
                order=idx + 1,
            )
        )

    # 주요 마일스톤 (PHASE_TRANSITION이 아닌 이벤트 중 주요 유형)
    milestone_types = {"DOCUMENT_SIGNED", "DEADLINE", "CUSTOM", "MEETING"}
    ms_q = (
        select(DealTimeline)
        .where(
            DealTimeline.transaction_id == txn_id,
            DealTimeline.event_type.in_(milestone_types),
        )
        .order_by(DealTimeline.event_date.asc())
    )
    ms_events = (await db.execute(ms_q)).scalars().all()
    milestones = [GanttMilestone(label=e.title, date=e.event_date, type=e.event_type) for e in ms_events]

    return GanttResponse(
        phases=phases,
        milestones=milestones,
        target_close_date=txn.target_close_date,
        deal_start_date=deal_start,
    )
