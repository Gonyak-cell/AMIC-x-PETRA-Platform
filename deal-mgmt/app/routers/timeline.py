"""딜 타임라인 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.timeline import DealTimeline
from app.schemas.timeline import TimelineEventCreate, TimelineEventOut, TimelineResponse
from app.services import transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/timeline", tags=["Timeline"])


@router.get("", response_model=TimelineResponse)
async def list_timeline(
    txn_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)

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
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    event = DealTimeline(
        transaction_id=txn_id,
        is_auto_generated=False,
        created_by=claims.email,
        **body.model_dump(),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return TimelineEventOut.model_validate(event)


@router.delete("/{event_id}", status_code=204)
async def delete_timeline_event(
    txn_id: uuid.UUID,
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
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
    await db.delete(event)
    await db.commit()
