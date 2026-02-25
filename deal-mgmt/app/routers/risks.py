"""리스크 레지스터 라우터."""

from __future__ import annotations

import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.enums import AuditAction, RiskSeverity, RiskStatus
from app.models.risk_item import RiskItem
from app.schemas.risk import (
    RiskCategorySummary,
    RiskItemCreate,
    RiskItemOut,
    RiskItemUpdate,
    RiskMatrixCell,
    RiskSummary,
    compute_risk_score,
)
from app.services import audit_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/risks", tags=["Risks"])


@router.get("", response_model=list[RiskItemOut])
async def list_risks(
    txn_id: uuid.UUID,
    category: str | None = None,
    risk_status: str | None = Query(None, alias="status"),
    severity: str | None = None,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    q = select(RiskItem).where(RiskItem.transaction_id == txn_id)
    if category:
        q = q.where(RiskItem.category == category)
    if risk_status:
        q = q.where(RiskItem.status == risk_status)
    if severity:
        q = q.where(RiskItem.severity == severity)
    q = q.order_by(RiskItem.risk_score.desc().nullslast(), RiskItem.created_at)
    result = await db.execute(q)
    return [RiskItemOut.model_validate(r) for r in result.scalars().all()]


@router.get("/summary", response_model=RiskSummary)
async def risk_summary(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    q = select(RiskItem).where(RiskItem.transaction_id == txn_id)
    result = await db.execute(q)
    items = list(result.scalars().all())

    # by_category
    cat_map: dict[str, dict[str, int]] = {}
    for item in items:
        cat = item.category.value
        if cat not in cat_map:
            cat_map[cat] = {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0}
        cat_map[cat]["total"] += 1
        cat_map[cat][item.severity.value.lower()] += 1

    by_category = [RiskCategorySummary(category=cat, **counts) for cat, counts in cat_map.items()]

    # by_status
    status_counter = Counter(item.status.value for item in items)

    # matrix (severity × likelihood → count)
    matrix_counter: Counter[tuple[str, str]] = Counter()
    for item in items:
        matrix_counter[(item.severity.value, item.likelihood.value)] += 1
    matrix = [
        RiskMatrixCell(severity=sev, likelihood=lik, count=cnt)
        for (sev, lik), cnt in matrix_counter.items()
    ]

    # avg score & unmitigated critical
    scores = [item.risk_score for item in items if item.risk_score is not None]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    unmitigated_critical = sum(
        1
        for item in items
        if item.severity == RiskSeverity.CRITICAL
        and item.status not in (RiskStatus.MITIGATED, RiskStatus.CLOSED)
    )

    return RiskSummary(
        total=len(items),
        by_category=by_category,
        by_status=dict(status_counter),
        matrix=matrix,
        avg_risk_score=round(avg_score, 1),
        unmitigated_critical=unmitigated_critical,
    )


@router.post("", response_model=RiskItemOut, status_code=201)
async def create_risk(
    txn_id: uuid.UUID,
    body: RiskItemCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await transaction_service.get_transaction(db, txn_id)
    score = compute_risk_score(body.severity, body.likelihood)
    item = RiskItem(transaction_id=txn_id, risk_score=score, **body.model_dump())
    db.add(item)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="RiskItem",
        entity_id=item.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(item)
    return RiskItemOut.model_validate(item)


@router.get("/{item_id}", response_model=RiskItemOut)
async def get_risk(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await check_client_deal_access(db, txn_id, claims)
    q = select(RiskItem).where(RiskItem.id == item_id, RiskItem.transaction_id == txn_id)
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="리스크 항목을 찾을 수 없습니다")
    return RiskItemOut.model_validate(item)


@router.patch("/{item_id}", response_model=RiskItemOut)
async def update_risk(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    body: RiskItemUpdate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(RiskItem).where(RiskItem.id == item_id, RiskItem.transaction_id == txn_id)
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="리스크 항목을 찾을 수 없습니다")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(item, k, v)
    # severity 또는 likelihood 변경 시 risk_score 재계산
    if "severity" in update_data or "likelihood" in update_data:
        item.risk_score = compute_risk_score(item.severity, item.likelihood)
    await audit_service.record(
        db,
        entity_type="RiskItem",
        entity_id=item.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value={k: str(v) if v is not None else None for k, v in update_data.items()},
    )
    await db.commit()
    await db.refresh(item)
    return RiskItemOut.model_validate(item)


@router.delete("/{item_id}", status_code=204)
async def delete_risk(
    txn_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    q = select(RiskItem).where(RiskItem.id == item_id, RiskItem.transaction_id == txn_id)
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="리스크 항목을 찾을 수 없습니다")
    await audit_service.record(
        db,
        entity_type="RiskItem",
        entity_id=item.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(item)
    await db.commit()
