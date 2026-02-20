"""PMI(Post-Merger Integration) 태스크 관리 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.models.enums import AuditAction, PMITaskStatus
from app.models.pmi_task import PMITask
from app.schemas.pmi import PMISummary, PMITaskCreate, PMITaskOut, PMITaskUpdate
from app.services import audit_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/pmi", tags=["PMI"])


@router.get("", response_model=list[PMITaskOut])
async def list_pmi_tasks(
    txn_id: uuid.UUID,
    category: str | None = None,
    priority: str | None = None,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    q = select(PMITask).where(PMITask.transaction_id == txn_id)
    if category:
        q = q.where(PMITask.category == category)
    if priority:
        q = q.where(PMITask.priority == priority)
    q = q.order_by(PMITask.sort_order, PMITask.created_at.desc())
    result = await db.execute(q)
    return [PMITaskOut.model_validate(t) for t in result.scalars().all()]


@router.get("/summary", response_model=PMISummary)
async def pmi_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    q = select(PMITask).where(PMITask.transaction_id == txn_id)
    result = await db.execute(q)
    items = list(result.scalars().all())

    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    completed = 0
    for item in items:
        by_category[item.category.value] = by_category.get(item.category.value, 0) + 1
        by_status[item.status.value] = by_status.get(item.status.value, 0) + 1
        by_priority[item.priority.value] = by_priority.get(item.priority.value, 0) + 1
        if item.status == PMITaskStatus.COMPLETED:
            completed += 1

    total = len(items)
    rate = (completed / total) if total > 0 else 0.0

    return PMISummary(
        total=total,
        by_category=by_category,
        by_status=by_status,
        by_priority=by_priority,
        completion_rate=round(rate, 3),
    )


@router.post("", response_model=PMITaskOut, status_code=201)
async def create_pmi_task(
    txn_id: uuid.UUID,
    body: PMITaskCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    task = PMITask(transaction_id=txn_id, **body.model_dump())
    db.add(task)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="PMITask",
        entity_id=task.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(task)
    return PMITaskOut.model_validate(task)


@router.patch("/{task_id}", response_model=PMITaskOut)
async def update_pmi_task(
    txn_id: uuid.UUID,
    task_id: uuid.UUID,
    body: PMITaskUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(PMITask).where(PMITask.id == task_id, PMITask.transaction_id == txn_id)
    task = (await db.execute(q)).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PMI 태스크를 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(task, k, v)
    await audit_service.record(
        db,
        entity_type="PMITask",
        entity_id=task.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(task)
    return PMITaskOut.model_validate(task)


@router.delete("/{task_id}", status_code=204)
async def delete_pmi_task(
    txn_id: uuid.UUID,
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    q = select(PMITask).where(PMITask.id == task_id, PMITask.transaction_id == txn_id)
    task = (await db.execute(q)).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PMI 태스크를 찾을 수 없습니다")
    await audit_service.record(
        db,
        entity_type="PMITask",
        entity_id=task.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(task)
    await db.commit()
