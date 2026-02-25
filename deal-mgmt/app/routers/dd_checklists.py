"""DD 워크스트림 체크리스트 라우터."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.dd_checklist import DDChecklist
from app.models.enums import AuditAction, DDChecklistStatus
from app.schemas.dd_checklist import (
    DDChecklistCreate,
    DDChecklistOut,
    DDChecklistSummary,
    DDChecklistUpdate,
    DDWorkstreamSummary,
)
from app.services import audit_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/dd-checklist", tags=["DD Checklist"])


@router.get("", response_model=list[DDChecklistOut])
async def list_checklist(
    txn_id: uuid.UUID,
    workstream: str | None = None,
    checklist_status: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    q = select(DDChecklist).where(DDChecklist.transaction_id == txn_id)
    if workstream:
        q = q.where(DDChecklist.workstream == workstream)
    if checklist_status:
        q = q.where(DDChecklist.status == checklist_status)
    q = q.order_by(DDChecklist.workstream, DDChecklist.created_at)
    result = await db.execute(q)
    return [DDChecklistOut.model_validate(c) for c in result.scalars().all()]


@router.get("/summary", response_model=DDChecklistSummary)
async def checklist_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    q = select(DDChecklist).where(DDChecklist.transaction_id == txn_id)
    result = await db.execute(q)
    items = list(result.scalars().all())

    ws_map: dict[str, dict[str, int]] = {}
    for item in items:
        ws = item.workstream.value
        if ws not in ws_map:
            ws_map[ws] = {"total": 0, "completed": 0, "in_progress": 0, "not_started": 0}
        ws_map[ws]["total"] += 1
        if item.status == DDChecklistStatus.COMPLETED:
            ws_map[ws]["completed"] += 1
        elif item.status == DDChecklistStatus.IN_PROGRESS:
            ws_map[ws]["in_progress"] += 1
        elif item.status == DDChecklistStatus.NOT_STARTED:
            ws_map[ws]["not_started"] += 1

    by_workstream = [DDWorkstreamSummary(workstream=ws, **counts) for ws, counts in ws_map.items()]
    total = len(items)
    completed = sum(1 for i in items if i.status == DDChecklistStatus.COMPLETED)
    pct = (completed / total * 100) if total > 0 else 0.0

    return DDChecklistSummary(total=total, by_workstream=by_workstream, overall_completion_pct=round(pct, 1))


@router.post("", response_model=DDChecklistOut, status_code=201)
async def create_checklist_item(
    txn_id: uuid.UUID,
    body: DDChecklistCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    item = DDChecklist(transaction_id=txn_id, **body.model_dump())
    db.add(item)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="DDChecklist",
        entity_id=item.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(item)
    return DDChecklistOut.model_validate(item)


@router.patch("/{item_id}", response_model=DDChecklistOut)
async def update_checklist_item(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    body: DDChecklistUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(DDChecklist).where(DDChecklist.id == item_id, DDChecklist.transaction_id == txn_id)
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="체크리스트 항목을 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(item, k, v)
    await audit_service.record(
        db,
        entity_type="DDChecklist",
        entity_id=item.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(item)
    return DDChecklistOut.model_validate(item)


@router.delete("/{item_id}", status_code=204)
async def delete_checklist_item(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(DDChecklist).where(DDChecklist.id == item_id, DDChecklist.transaction_id == txn_id)
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="체크리스트 항목을 찾을 수 없습니다")
    await audit_service.record(
        db,
        entity_type="DDChecklist",
        entity_id=item.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(item)
    await db.commit()
