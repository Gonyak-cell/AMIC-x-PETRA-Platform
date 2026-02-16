"""Consolidation (연결 분석) API — Sprint 16."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.core.exceptions import FDDError
from app.database import get_db
from app.models.deal import Deal
from app.models.entity import Entity
from app.schemas.consolidation import (
    ConsolidationRequest,
    ConsolidationResultRead,
    EliminationEntryRead,
    EntitySummary,
)
from app.services.consolidation.consolidation_service import run_consolidation

router = APIRouter(
    prefix="/deals/{deal_id}/consolidation",
    tags=["consolidation"],
)


def _get_deal_or_404(db: Session, deal_id: uuid.UUID) -> Deal:
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.post("/run", response_model=ConsolidationResultRead)
def run_consolidation_api(
    deal_id: uuid.UUID,
    body: ConsolidationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """멀티 엔티티 연결 분석을 실행한다.

    엔티티별 TB 데이터를 집계하고, FX 변환 + IC 제거 + 소수지분을 반영한다.
    """
    _get_deal_or_404(db, deal_id)

    ic_pairs = None
    if body.ic_pairs:
        ic_pairs = [
            (ic.debit_entity, ic.credit_entity, ic.category, ic.amount)
            for ic in body.ic_pairs
        ]

    try:
        result, _evidence = run_consolidation(db, deal_id, ic_pairs)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FDDError as e:
        raise HTTPException(status_code=400, detail=e.detail)

    return ConsolidationResultRead(
        consolidated_totals=result.consolidated_totals,
        entity_subtotals=result.entity_subtotals,
        eliminations=[
            EliminationEntryRead(
                description=e.description,
                debit_entity=e.debit_entity,
                credit_entity=e.credit_entity,
                amount=e.amount,
                account_category=e.account_category,
            )
            for e in result.eliminations
        ],
        elimination_total=result.elimination_total,
        minority_interest=result.minority_interest,
        warnings=result.warnings,
    )


@router.get("/entities-summary", response_model=list[EntitySummary])
def get_entities_summary(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """연결 분석용 엔티티 요약 목록을 조회한다."""
    _get_deal_or_404(db, deal_id)

    stmt = (
        select(Entity)
        .where(Entity.deal_id == deal_id, Entity.is_active.is_(True))
        .order_by(Entity.entity_type, Entity.code)
    )
    entities = list(db.scalars(stmt).all())

    return [
        EntitySummary(
            id=str(e.id),
            code=e.code,
            name=e.name,
            entity_type=e.entity_type.value,
            functional_currency=e.functional_currency,
            ownership_pct=e.ownership_pct,
        )
        for e in entities
    ]
