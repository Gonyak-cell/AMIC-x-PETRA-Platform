"""수임계약 + 워킹그룹 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.engagement import Engagement
from app.models.enums import AuditAction
from app.models.working_group import WorkingGroupMember
from app.schemas.engagement import (
    EngagementCreate,
    EngagementOut,
    EngagementUpdate,
    WorkingGroupMemberCreate,
    WorkingGroupMemberOut,
    WorkingGroupMemberUpdate,
)
from app.services import audit_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}", tags=["Engagements"])


# ── Engagement CRUD ─────────────────────────────────────
@router.get("/engagements", response_model=list[EngagementOut])
async def list_engagements(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    q = select(Engagement).where(Engagement.transaction_id == txn_id).order_by(Engagement.created_at.desc())
    result = await db.execute(q)
    return [EngagementOut.model_validate(e) for e in result.scalars().all()]


@router.post("/engagements", response_model=EngagementOut, status_code=201)
async def create_engagement(
    txn_id: uuid.UUID,
    body: EngagementCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    eng = Engagement(transaction_id=txn_id, **body.model_dump())
    db.add(eng)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="Engagement",
        entity_id=eng.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(eng)
    return EngagementOut.model_validate(eng)


@router.patch("/engagements/{eng_id}", response_model=EngagementOut)
async def update_engagement(
    txn_id: uuid.UUID,
    eng_id: uuid.UUID,
    body: EngagementUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(Engagement).where(Engagement.id == eng_id, Engagement.transaction_id == txn_id)
    eng = (await db.execute(q)).scalar_one_or_none()
    if eng is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="수임계약을 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(eng, k, v)
    await audit_service.record(
        db,
        entity_type="Engagement",
        entity_id=eng.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value=update_data,
    )
    await db.commit()
    await db.refresh(eng)
    return EngagementOut.model_validate(eng)


@router.delete("/engagements/{eng_id}", status_code=204)
async def delete_engagement(
    txn_id: uuid.UUID,
    eng_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(Engagement).where(Engagement.id == eng_id, Engagement.transaction_id == txn_id)
    eng = (await db.execute(q)).scalar_one_or_none()
    if eng is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="수임계약을 찾을 수 없습니다")
    await audit_service.record(
        db,
        entity_type="Engagement",
        entity_id=eng.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(eng)
    await db.commit()


# ── Working Group CRUD ──────────────────────────────────
@router.get("/members", response_model=list[WorkingGroupMemberOut], tags=["Working Group"])
async def list_members(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    q = (
        select(WorkingGroupMember)
        .where(WorkingGroupMember.transaction_id == txn_id)
        .order_by(WorkingGroupMember.created_at)
    )
    result = await db.execute(q)
    return [WorkingGroupMemberOut.model_validate(m) for m in result.scalars().all()]


@router.post("/members", response_model=WorkingGroupMemberOut, status_code=201, tags=["Working Group"])
async def add_member(
    txn_id: uuid.UUID,
    body: WorkingGroupMemberCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    member = WorkingGroupMember(transaction_id=txn_id, **body.model_dump())
    db.add(member)
    try:
        await db.flush()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"이메일 '{body.email}'은(는) 이미 이 거래의 멤버입니다",
        )
    await audit_service.record(
        db,
        entity_type="WorkingGroupMember",
        entity_id=member.id,
        action=AuditAction.MEMBER_ADDED,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(member)
    return WorkingGroupMemberOut.model_validate(member)


@router.patch("/members/{member_id}", response_model=WorkingGroupMemberOut, tags=["Working Group"])
async def update_member(
    txn_id: uuid.UUID,
    member_id: uuid.UUID,
    body: WorkingGroupMemberUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(WorkingGroupMember).where(
        WorkingGroupMember.id == member_id, WorkingGroupMember.transaction_id == txn_id
    )
    member = (await db.execute(q)).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="멤버를 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(member, k, v)
    await audit_service.record(
        db,
        entity_type="WorkingGroupMember",
        entity_id=member.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value=update_data,
    )
    await db.commit()
    await db.refresh(member)
    return WorkingGroupMemberOut.model_validate(member)


@router.delete("/members/{member_id}", status_code=204, tags=["Working Group"])
async def remove_member(
    txn_id: uuid.UUID,
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(WorkingGroupMember).where(
        WorkingGroupMember.id == member_id, WorkingGroupMember.transaction_id == txn_id
    )
    member = (await db.execute(q)).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="멤버를 찾을 수 없습니다")
    await audit_service.record(
        db,
        entity_type="WorkingGroupMember",
        entity_id=member.id,
        action=AuditAction.MEMBER_REMOVED,
        actor_email=claims.email,
    )
    await db.delete(member)
    await db.commit()
