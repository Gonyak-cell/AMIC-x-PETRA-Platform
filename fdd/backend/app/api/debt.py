"""Net Debt API — FDD-701/702/703/704.

Net Debt 계산, 항목 관리, Bridge 재계산 엔드포인트.
"""

import uuid

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

limiter = Limiter(key_func=get_remote_address)

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.auth.rbac import Permission
from app.core.exceptions import NotFoundError
from app.database import get_db
from app.models.deal import Deal, DealSnapshot
from app.schemas.debt import (
    DebtItemApprove,
    DebtItemCreate,
    DebtItemRead,
    DebtItemUpdate,
    NetDebtBridgeSummary,
    NetDebtCalculationRead,
    NetDebtRunRequest,
)
from app.services.debt.debt_service import (
    add_manual_debt_item,
    approve_debt_item,
    get_net_debt_calculation,
    list_net_debt_calculations,
    recalculate_net_debt,
    run_net_debt_calculation,
    update_debt_item,
)

router = APIRouter()


# -- Net Debt Calculation -------------------------------------------


@router.post(
    "/deals/{deal_id}/debt/calculate",
    response_model=NetDebtCalculationRead,
    status_code=201,
)
@limiter.limit("5/minute")
def calculate_debt(
    request: Request,
    deal_id: uuid.UUID,
    body: NetDebtRunRequest,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """Net Debt 계산을 실행한다."""
    deal = db.get(Deal, deal_id)
    if not deal:
        raise NotFoundError("Deal", str(deal_id))

    snapshot = db.get(DealSnapshot, body.snapshot_id)
    if not snapshot or snapshot.deal_id != deal_id:
        raise NotFoundError("DealSnapshot", str(body.snapshot_id))

    return run_net_debt_calculation(
        db,
        deal_id,
        body.snapshot_id,
        include_lease_liabilities=body.include_lease_liabilities,
        include_deferred_revenue=body.include_deferred_revenue,
    )


@router.get(
    "/deals/{deal_id}/debt",
    response_model=list[NetDebtCalculationRead],
)
def list_debt(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """딜의 모든 Net Debt 계산 결과를 조회한다."""
    deal = db.get(Deal, deal_id)
    if not deal:
        raise NotFoundError("Deal", str(deal_id))

    return list_net_debt_calculations(db, deal_id)


@router.get(
    "/deals/{deal_id}/debt/{calc_id}",
    response_model=NetDebtCalculationRead,
)
def get_debt(
    deal_id: uuid.UUID,
    calc_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """특정 Net Debt 계산 결과를 조회한다."""
    calc = get_net_debt_calculation(db, deal_id, calc_id)
    if not calc:
        raise NotFoundError("NetDebtCalculation", str(calc_id))
    return calc


# -- Net Debt Bridge ------------------------------------------------


@router.get(
    "/deals/{deal_id}/debt/{calc_id}/bridge",
    response_model=NetDebtBridgeSummary,
)
def get_debt_bridge(
    deal_id: uuid.UUID,
    calc_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Net Debt Bridge 요약을 조회한다."""
    calc = get_net_debt_calculation(db, deal_id, calc_id)
    if not calc:
        raise NotFoundError("NetDebtCalculation", str(calc_id))

    debt_like = [
        DebtItemRead.model_validate(i)
        for i in sorted(calc.items, key=lambda x: x.display_order)
        if i.item_type.value == "DEBT_LIKE"
    ]
    cash_like = [
        DebtItemRead.model_validate(i)
        for i in sorted(calc.items, key=lambda x: x.display_order)
        if i.item_type.value == "CASH_LIKE"
    ]

    return NetDebtBridgeSummary(
        gross_debt=calc.gross_debt,
        cash_and_equivalents=calc.cash_and_equivalents,
        net_debt=calc.net_debt,
        debt_like_items=debt_like,
        cash_like_items=cash_like,
        debt_like_total=calc.debt_like_total,
        cash_like_total=calc.cash_like_total,
        adjusted_net_debt=calc.adjusted_net_debt,
        balance_check_error=calc.balance_check_error,
        is_balanced=calc.balance_check_error == 0,
    )


@router.post(
    "/deals/{deal_id}/debt/{calc_id}/recalculate",
    response_model=NetDebtCalculationRead,
)
def recalculate_debt(
    deal_id: uuid.UUID,
    calc_id: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """APPROVED 항목 기준으로 Net Debt를 재계산한다."""
    calc = get_net_debt_calculation(db, deal_id, calc_id)
    if not calc:
        raise NotFoundError("NetDebtCalculation", str(calc_id))

    return recalculate_net_debt(db, calc_id)


# -- Debt Items -----------------------------------------------------


@router.post(
    "/deals/{deal_id}/debt/{calc_id}/items",
    response_model=DebtItemRead,
    status_code=201,
)
def create_debt_item(
    deal_id: uuid.UUID,
    calc_id: uuid.UUID,
    body: DebtItemCreate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """수동 Debt/Cash 항목을 추가한다."""
    return add_manual_debt_item(db, deal_id, calc_id, body)


@router.put(
    "/deals/{deal_id}/debt/{calc_id}/items/{item_id}",
    response_model=DebtItemRead,
)
def update_debt_item_endpoint(
    deal_id: uuid.UUID,
    calc_id: uuid.UUID,
    item_id: uuid.UUID,
    body: DebtItemUpdate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """Debt 항목을 수정한다."""
    return update_debt_item(db, deal_id, item_id, body)


@router.post(
    "/deals/{deal_id}/debt/{calc_id}/items/{item_id}/approve",
    response_model=DebtItemRead,
)
def approve_debt_item_endpoint(
    deal_id: uuid.UUID,
    calc_id: uuid.UUID,
    item_id: uuid.UUID,
    body: DebtItemApprove,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """Debt 항목을 승인한다."""
    return approve_debt_item(db, deal_id, item_id, body)
