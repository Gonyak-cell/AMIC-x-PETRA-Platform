"""ExchangeRate (환율) API — Sprint 16."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.models.deal import Deal
from app.models.exchange_rate import ExchangeRate, RateType
from app.schemas.exchange_rate import (
    ExchangeRateBulkCreate,
    ExchangeRateCreate,
    ExchangeRateRead,
    ExchangeRateUpdate,
)

router = APIRouter(
    prefix="/deals/{deal_id}/exchange-rates",
    tags=["exchange-rates"],
)


def _get_deal_or_404(db: Session, deal_id: uuid.UUID) -> Deal:
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.post("/", response_model=ExchangeRateRead, status_code=201)
def create_exchange_rate(
    deal_id: uuid.UUID,
    body: ExchangeRateCreate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """환율 등록."""
    _get_deal_or_404(db, deal_id)

    rate = ExchangeRate(
        deal_id=deal_id,
        from_currency=body.from_currency,
        to_currency=body.to_currency,
        rate_type=body.rate_type,
        rate=body.rate,
        effective_date=body.effective_date,
        period_key=body.period_key,
        created_by=current_user.email,
    )
    db.add(rate)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Duplicate exchange rate for this currency pair, type, and date",
        )
    db.refresh(rate)
    return rate


@router.post("/bulk", response_model=list[ExchangeRateRead], status_code=201)
def create_exchange_rates_bulk(
    deal_id: uuid.UUID,
    body: ExchangeRateBulkCreate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """환율 벌크 등록."""
    _get_deal_or_404(db, deal_id)

    rates = []
    for item in body.rates:
        rate = ExchangeRate(
            deal_id=deal_id,
            from_currency=item.from_currency,
            to_currency=item.to_currency,
            rate_type=item.rate_type,
            rate=item.rate,
            effective_date=item.effective_date,
            period_key=item.period_key,
            created_by=current_user.email,
        )
        db.add(rate)
        rates.append(rate)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Duplicate exchange rate found in bulk upload",
        )

    for r in rates:
        db.refresh(r)
    return rates


@router.get("/", response_model=list[ExchangeRateRead])
def list_exchange_rates(
    deal_id: uuid.UUID,
    from_currency: str | None = Query(default=None),
    to_currency: str | None = Query(default=None),
    rate_type: RateType | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """환율 목록 조회 (필터 지원)."""
    _get_deal_or_404(db, deal_id)

    stmt = select(ExchangeRate).where(ExchangeRate.deal_id == deal_id)
    if from_currency:
        stmt = stmt.where(ExchangeRate.from_currency == from_currency)
    if to_currency:
        stmt = stmt.where(ExchangeRate.to_currency == to_currency)
    if rate_type:
        stmt = stmt.where(ExchangeRate.rate_type == rate_type)
    if date_from:
        stmt = stmt.where(ExchangeRate.effective_date >= date_from)
    if date_to:
        stmt = stmt.where(ExchangeRate.effective_date <= date_to)

    stmt = stmt.order_by(ExchangeRate.effective_date.desc())
    return list(db.scalars(stmt).all())


@router.get("/{rate_id}", response_model=ExchangeRateRead)
def get_exchange_rate(
    deal_id: uuid.UUID,
    rate_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """환율 단건 조회."""
    rate = db.get(ExchangeRate, rate_id)
    if rate is None or rate.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Exchange rate not found")
    return rate


@router.put("/{rate_id}", response_model=ExchangeRateRead)
def update_exchange_rate(
    deal_id: uuid.UUID,
    rate_id: uuid.UUID,
    body: ExchangeRateUpdate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """환율 수정."""
    rate = db.get(ExchangeRate, rate_id)
    if rate is None or rate.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Exchange rate not found")

    _UPDATABLE_FIELDS = {"rate", "period_key"}
    for field, value in body.model_dump(exclude_unset=True).items():
        if field not in _UPDATABLE_FIELDS:
            continue
        setattr(rate, field, value)

    db.commit()
    db.refresh(rate)
    return rate


@router.delete("/{rate_id}", status_code=204)
def delete_exchange_rate(
    deal_id: uuid.UUID,
    rate_id: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """환율 삭제."""
    rate = db.get(ExchangeRate, rate_id)
    if rate is None or rate.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Exchange rate not found")

    db.delete(rate)
    db.commit()
