"""Transaction CRUD 비즈니스 로직."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuditAction, TransactionPhase, TransactionStatus
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services import audit_service


async def list_transactions(
    db: AsyncSession,
    *,
    search: str | None = None,
    side: str | None = None,
    phase: str | None = None,
    tx_status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Transaction], int]:
    """거래 목록 조회 (필터/검색/페이지네이션)."""
    base = select(Transaction).where(Transaction.is_deleted.is_(False))

    if search:
        pattern = f"%{search}%"
        base = base.where(
            Transaction.name.ilike(pattern)
            | Transaction.code_name.ilike(pattern)
            | Transaction.target_company_name.ilike(pattern)
            | Transaction.client_name.ilike(pattern)
        )
    if side:
        base = base.where(Transaction.side == side)
    if phase:
        base = base.where(Transaction.phase == phase)
    if tx_status:
        base = base.where(Transaction.status == tx_status)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    rows_q = base.order_by(Transaction.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(rows_q)
    return list(result.scalars().all()), total


async def get_transaction(db: AsyncSession, txn_id: uuid.UUID) -> Transaction:
    """단건 조회 — 없으면 404."""
    q = select(Transaction).where(Transaction.id == txn_id, Transaction.is_deleted.is_(False))
    row = (await db.execute(q)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="거래를 찾을 수 없습니다")
    return row


async def create_transaction(
    db: AsyncSession,
    body: TransactionCreate,
    actor_email: str | None = None,
) -> Transaction:
    """거래 생성."""
    # code_name 중복 체크
    exists = (
        await db.execute(
            select(Transaction.id).where(
                Transaction.code_name == body.code_name,
                Transaction.is_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"코드네임 '{body.code_name}'이(가) 이미 사용 중입니다",
        )

    txn = Transaction(
        **body.model_dump(),
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
        new_value=body.model_dump(),
    )
    await db.commit()
    await db.refresh(txn)
    return txn


async def update_transaction(
    db: AsyncSession,
    txn_id: uuid.UUID,
    body: TransactionUpdate,
    actor_email: str | None = None,
) -> Transaction:
    """거래 수정."""
    txn = await get_transaction(db, txn_id)
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return txn

    # code_name 변경 시 중복 체크
    if "code_name" in update_data and update_data["code_name"] != txn.code_name:
        exists = (
            await db.execute(
                select(Transaction.id).where(
                    Transaction.code_name == update_data["code_name"],
                    Transaction.is_deleted.is_(False),
                    Transaction.id != txn_id,
                )
            )
        ).scalar_one_or_none()
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"코드네임 '{update_data['code_name']}'이(가) 이미 사용 중입니다",
            )

    old_value = {k: getattr(txn, k) for k in update_data}
    for k, v in update_data.items():
        setattr(txn, k, v)

    await audit_service.record(
        db,
        entity_type="Transaction",
        entity_id=txn.id,
        action=AuditAction.UPDATE,
        actor_email=actor_email,
        old_value=old_value,
        new_value=update_data,
    )
    await db.commit()
    await db.refresh(txn)
    return txn


async def delete_transaction(
    db: AsyncSession,
    txn_id: uuid.UUID,
    actor_email: str | None = None,
) -> None:
    """소프트 삭제."""
    txn = await get_transaction(db, txn_id)
    txn.is_deleted = True

    await audit_service.record(
        db,
        entity_type="Transaction",
        entity_id=txn.id,
        action=AuditAction.DELETE,
        actor_email=actor_email,
    )
    await db.commit()
