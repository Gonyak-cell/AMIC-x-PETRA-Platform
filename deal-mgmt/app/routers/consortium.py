"""컨소시엄/공동투자 매핑 CRUD 라우터."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.buyer_candidate import BuyerCandidate
from app.models.consortium_mapping import ConsortiumMapping
from app.models.enums import AuditAction, ConsortiumStatus, DealRole
from app.schemas.consortium import ConsortiumMappingCreate, ConsortiumMappingOut, ConsortiumMappingUpdate
from app.services import audit_service, transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions/{txn_id}/consortium", tags=["Consortium"])

# ── 상태 전이 규칙 ────────────────────────────────────────
_VALID_TRANSITIONS: dict[ConsortiumStatus, set[ConsortiumStatus]] = {
    ConsortiumStatus.TAPPING: {ConsortiumStatus.CONFIRMED, ConsortiumStatus.DROPPED},
    ConsortiumStatus.CONFIRMED: {ConsortiumStatus.DROPPED},
    ConsortiumStatus.DROPPED: set(),  # 종료 상태
}


# ── 헬퍼 ────────────────────────────────────────────────


def _build_out(mapping: ConsortiumMapping, lead_name: str, co_name: str) -> dict:
    """ORM 객체 + 조인된 회사명 → ConsortiumMappingOut dict."""
    return {
        "id": mapping.id,
        "transaction_id": mapping.transaction_id,
        "lead_buyer_id": mapping.lead_buyer_id,
        "lead_buyer_name": lead_name,
        "co_investor_buyer_id": mapping.co_investor_buyer_id,
        "co_investor_buyer_name": co_name,
        "status": mapping.status,
        "equity_share_pct": mapping.equity_share_pct,
        "notes": mapping.notes,
        "created_at": mapping.created_at,
        "updated_at": mapping.updated_at,
    }


async def _validate_buyer_in_txn(
    db: AsyncSession,
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    label: str,
) -> BuyerCandidate:
    """buyer가 해당 txn에 속하는지 검증."""
    q = select(BuyerCandidate).where(
        BuyerCandidate.id == buyer_id,
        BuyerCandidate.transaction_id == txn_id,
    )
    buyer = (await db.execute(q)).scalar_one_or_none()
    if buyer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{label} 매수자(id={buyer_id})를 이 거래에서 찾을 수 없습니다",
        )
    return buyer


# ── 전체 조회 ────────────────────────────────────────────


@router.get("/", response_model=list[ConsortiumMappingOut])
async def list_consortium_mappings(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[ConsortiumMappingOut]:
    """딜 내 모든 컨소시엄 매핑 조회."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    lead = aliased(BuyerCandidate)
    co = aliased(BuyerCandidate)

    q = (
        select(ConsortiumMapping, lead.company_name, co.company_name)
        .join(lead, ConsortiumMapping.lead_buyer_id == lead.id)
        .join(co, ConsortiumMapping.co_investor_buyer_id == co.id)
        .where(ConsortiumMapping.transaction_id == txn_id)
        .order_by(ConsortiumMapping.created_at.desc())
    )
    result = await db.execute(q)

    return [ConsortiumMappingOut(**_build_out(row[0], row[1], row[2])) for row in result.all()]


# ── 생성 ────────────────────────────────────────────────


@router.post("/", response_model=ConsortiumMappingOut, status_code=201)
async def create_consortium_mapping(
    txn_id: uuid.UUID,
    body: ConsortiumMappingCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> ConsortiumMappingOut:
    """컨소시엄 매핑 생성."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    # 자기 참조 검증
    if body.lead_buyer_id == body.co_investor_buyer_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Lead와 Co-investor는 동일할 수 없습니다",
        )

    # 양쪽 buyer가 동일 txn에 속하는지 검증
    lead_buyer = await _validate_buyer_in_txn(db, txn_id, body.lead_buyer_id, "Lead")
    co_buyer = await _validate_buyer_in_txn(db, txn_id, body.co_investor_buyer_id, "Co-investor")

    # SOLE_BUYER 검증 — 단독 매수자는 컨소시엄 불가
    for buyer, label in [(lead_buyer, "Lead"), (co_buyer, "Co-investor")]:
        if buyer.deal_role == DealRole.SOLE_BUYER:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{label} 매수자({buyer.company_name})는 단독 매수자(SOLE_BUYER)로 설정되어 컨소시엄에 참여할 수 없습니다",
            )

    # 중복 검증
    dup_q = select(ConsortiumMapping).where(
        ConsortiumMapping.transaction_id == txn_id,
        ConsortiumMapping.lead_buyer_id == body.lead_buyer_id,
        ConsortiumMapping.co_investor_buyer_id == body.co_investor_buyer_id,
    )
    if (await db.execute(dup_q)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="동일 Lead-Co 쌍의 매핑이 이미 존재합니다",
        )

    mapping = ConsortiumMapping(
        transaction_id=txn_id,
        lead_buyer_id=body.lead_buyer_id,
        co_investor_buyer_id=body.co_investor_buyer_id,
        status=body.status,
        equity_share_pct=body.equity_share_pct,
        notes=body.notes,
    )
    db.add(mapping)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="동일 Lead-Co 쌍의 매핑이 이미 존재합니다",
        )

    await audit_service.record(
        db,
        entity_type="ConsortiumMapping",
        entity_id=mapping.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),  # Pydantic v2: UUID→str 직렬화
    )
    await db.commit()
    await db.refresh(mapping)

    return ConsortiumMappingOut(**_build_out(mapping, lead_buyer.company_name, co_buyer.company_name))


# ── 수정 ────────────────────────────────────────────────


@router.patch("/{mapping_id}", response_model=ConsortiumMappingOut)
async def update_consortium_mapping(
    txn_id: uuid.UUID,
    mapping_id: uuid.UUID,
    body: ConsortiumMappingUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> ConsortiumMappingOut:
    """상태/지분율/노트 수정."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    q = select(ConsortiumMapping).where(
        ConsortiumMapping.id == mapping_id,
        ConsortiumMapping.transaction_id == txn_id,
    )
    mapping = (await db.execute(q)).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="컨소시엄 매핑을 찾을 수 없습니다")

    update_data = body.model_dump(exclude_unset=True)
    old_value = {k: getattr(mapping, k) for k in update_data}
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="status는 null로 설정할 수 없습니다",
            )
        allowed = _VALID_TRANSITIONS.get(mapping.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"상태 전이 불가: {mapping.status.value} → {new_status.value}",
            )
    for k, v in update_data.items():
        setattr(mapping, k, v)

    await audit_service.record(
        db,
        entity_type="ConsortiumMapping",
        entity_id=mapping.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        old_value=old_value,
        new_value=update_data,
    )
    await db.commit()
    await db.refresh(mapping)

    # 회사명 조회 — aliased join으로 1회 쿼리
    lead = aliased(BuyerCandidate)
    co = aliased(BuyerCandidate)
    q = (
        select(ConsortiumMapping, lead.company_name, co.company_name)
        .join(lead, ConsortiumMapping.lead_buyer_id == lead.id)
        .join(co, ConsortiumMapping.co_investor_buyer_id == co.id)
        .where(ConsortiumMapping.id == mapping.id)
    )
    row = (await db.execute(q)).one()
    return ConsortiumMappingOut(**_build_out(row[0], row[1], row[2]))


# ── 삭제 ────────────────────────────────────────────────


@router.delete("/{mapping_id}", status_code=204)
async def delete_consortium_mapping(
    txn_id: uuid.UUID,
    mapping_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> None:
    """컨소시엄 매핑 삭제."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    q = select(ConsortiumMapping).where(
        ConsortiumMapping.id == mapping_id,
        ConsortiumMapping.transaction_id == txn_id,
    )
    mapping = (await db.execute(q)).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="컨소시엄 매핑을 찾을 수 없습니다")

    await audit_service.record(
        db,
        entity_type="ConsortiumMapping",
        entity_id=mapping.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
        old_value={
            "lead_buyer_id": mapping.lead_buyer_id,
            "co_investor_buyer_id": mapping.co_investor_buyer_id,
            "status": mapping.status,
            "equity_share_pct": mapping.equity_share_pct,
        },
    )
    await db.delete(mapping)
    await db.commit()


# ── 매수자별 컨소시엄 요약 ───────────────────────────────


@router.get("/summary/{buyer_id}", response_model=list[ConsortiumMappingOut])
async def buyer_consortium_summary(
    txn_id: uuid.UUID,
    buyer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[ConsortiumMappingOut]:
    """특정 매수자의 컨소시엄 관계 (Lead로서 + Co-investor로서)."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    lead = aliased(BuyerCandidate)
    co = aliased(BuyerCandidate)

    q = (
        select(ConsortiumMapping, lead.company_name, co.company_name)
        .join(lead, ConsortiumMapping.lead_buyer_id == lead.id)
        .join(co, ConsortiumMapping.co_investor_buyer_id == co.id)
        .where(
            ConsortiumMapping.transaction_id == txn_id,
            (ConsortiumMapping.lead_buyer_id == buyer_id) | (ConsortiumMapping.co_investor_buyer_id == buyer_id),
        )
        .order_by(ConsortiumMapping.created_at.desc())
    )
    result = await db.execute(q)
    return [ConsortiumMappingOut(**_build_out(row[0], row[1], row[2])) for row in result.all()]
