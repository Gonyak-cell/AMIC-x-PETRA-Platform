"""Engagement and Working Group APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.engagement import Engagement
from app.models.enums import AuditAction, WorkingGroupRole
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

_WORKING_GROUP_MANAGER_ROLES = {"ADMIN", "MANAGER"}
_SELF_EDITABLE_MEMBER_FIELDS = {"organization", "phone"}
_WORKING_GROUP_ROLE_DISPLAY_ORDER = (
    WorkingGroupRole.LEAD_ADVISOR,
    WorkingGroupRole.LEGAL_COUNSEL,
    WorkingGroupRole.ACCOUNTING_ADVISOR,
    WorkingGroupRole.VALUATION_ADVISOR,
    WorkingGroupRole.TAX_ADVISOR,
    WorkingGroupRole.INDUSTRY_EXPERT,
    WorkingGroupRole.OTHER,
)


def _normalize_person_name(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def _can_manage_working_group(claims: JWTClaims) -> bool:
    return claims.role in _WORKING_GROUP_MANAGER_ROLES


def _is_own_working_group_member(
    claims: JWTClaims,
    member: WorkingGroupMember,
) -> bool:
    claim_email = (claims.email or "").strip().casefold()
    member_email = (member.email or "").strip().casefold()
    if claim_email and member_email and claim_email == member_email:
        return True

    claim_name = _normalize_person_name(claims.display_name)
    return bool(claim_name) and claim_name == _normalize_person_name(member.name)


def _require_working_group_manager(claims: JWTClaims) -> None:
    if _can_manage_working_group(claims):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="워킹 그룹 변경은 어드민 또는 매니저만 할 수 있습니다.",
    )


def _build_member_update_data(
    body: WorkingGroupMemberUpdate,
    claims: JWTClaims,
    member: WorkingGroupMember,
) -> dict[str, object]:
    update_data = body.model_dump(exclude_unset=True)

    if _can_manage_working_group(claims):
        return update_data

    if not _is_own_working_group_member(claims, member):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인 워킹 그룹 정보만 수정할 수 있습니다.",
        )

    filtered = {key: value for key, value in update_data.items() if key in _SELF_EDITABLE_MEMBER_FIELDS}
    if len(filtered) != len(update_data):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인 워킹 그룹 정보는 소속과 연락처만 수정할 수 있습니다.",
        )
    return filtered


@router.get("/engagements", response_model=list[EngagementOut])
async def list_engagements(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    query = select(Engagement).where(Engagement.transaction_id == txn_id).order_by(Engagement.created_at.desc())
    result = await db.execute(query)
    return [EngagementOut.model_validate(item) for item in result.scalars().all()]


@router.post("/engagements", response_model=EngagementOut, status_code=201)
async def create_engagement(
    txn_id: uuid.UUID,
    body: EngagementCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    engagement = Engagement(transaction_id=txn_id, **body.model_dump())
    db.add(engagement)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="Engagement",
        entity_id=engagement.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(engagement)
    return EngagementOut.model_validate(engagement)


@router.patch("/engagements/{eng_id}", response_model=EngagementOut)
async def update_engagement(
    txn_id: uuid.UUID,
    eng_id: uuid.UUID,
    body: EngagementUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    query = select(Engagement).where(
        Engagement.id == eng_id,
        Engagement.transaction_id == txn_id,
    )
    engagement = (await db.execute(query)).scalar_one_or_none()
    if engagement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="계약 정보를 찾을 수 없습니다.",
        )

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(engagement, key, value)

    await audit_service.record(
        db,
        entity_type="Engagement",
        entity_id=engagement.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value=update_data,
    )
    await db.commit()
    await db.refresh(engagement)
    return EngagementOut.model_validate(engagement)


@router.delete("/engagements/{eng_id}", status_code=204)
async def delete_engagement(
    txn_id: uuid.UUID,
    eng_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    query = select(Engagement).where(
        Engagement.id == eng_id,
        Engagement.transaction_id == txn_id,
    )
    engagement = (await db.execute(query)).scalar_one_or_none()
    if engagement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="계약 정보를 찾을 수 없습니다.",
        )

    await audit_service.record(
        db,
        entity_type="Engagement",
        entity_id=engagement.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(engagement)
    await db.commit()


@router.get("/members", response_model=list[WorkingGroupMemberOut], tags=["Working Group"])
async def list_members(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    role_priority = case(
        *(
            (WorkingGroupMember.role == role, priority)
            for priority, role in enumerate(_WORKING_GROUP_ROLE_DISPLAY_ORDER)
        ),
        else_=len(_WORKING_GROUP_ROLE_DISPLAY_ORDER),
    )
    query = (
        select(WorkingGroupMember)
        .where(WorkingGroupMember.transaction_id == txn_id)
        .order_by(role_priority, WorkingGroupMember.created_at.asc())
    )
    result = await db.execute(query)
    return [WorkingGroupMemberOut.model_validate(item) for item in result.scalars().all()]


@router.post("/members", response_model=WorkingGroupMemberOut, status_code=201, tags=["Working Group"])
async def add_member(
    txn_id: uuid.UUID,
    body: WorkingGroupMemberCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    _require_working_group_manager(claims)
    await transaction_service.get_transaction(db, txn_id)

    member = WorkingGroupMember(transaction_id=txn_id, **body.model_dump())
    db.add(member)
    try:
        await db.flush()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"이메일 '{body.email}'은 이미 이 거래의 워킹 그룹 멤버입니다.",
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
    claims: JWTClaims = Depends(get_jwt_claims),
):
    query = select(WorkingGroupMember).where(
        WorkingGroupMember.id == member_id,
        WorkingGroupMember.transaction_id == txn_id,
    )
    member = (await db.execute(query)).scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="워킹 그룹 멤버를 찾을 수 없습니다.",
        )

    update_data = _build_member_update_data(body, claims, member)
    for key, value in update_data.items():
        setattr(member, key, value)

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
    claims: JWTClaims = Depends(get_jwt_claims),
):
    _require_working_group_manager(claims)
    query = select(WorkingGroupMember).where(
        WorkingGroupMember.id == member_id,
        WorkingGroupMember.transaction_id == txn_id,
    )
    member = (await db.execute(query)).scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="워킹 그룹 멤버를 찾을 수 없습니다.",
        )

    await audit_service.record(
        db,
        entity_type="WorkingGroupMember",
        entity_id=member.id,
        action=AuditAction.MEMBER_REMOVED,
        actor_email=claims.email,
    )
    await db.delete(member)
    await db.commit()
