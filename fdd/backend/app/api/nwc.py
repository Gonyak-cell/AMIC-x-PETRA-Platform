"""NWC (Net Working Capital) API — FDD-601/602/603.

NWC 계산, 항목 분류 관리, Peg 시뮬레이션 엔드포인트.
"""

import uuid

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

limiter = Limiter(key_func=get_remote_address)

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.core.exceptions import NotFoundError
from app.auth.rbac import Permission
from app.database import get_db
from app.models.deal import Deal, DealSnapshot
from app.schemas.nwc import (
    NWCCalculationRead,
    NWCLineItemRead,
    NWCLineItemUpdate,
    NWCRunRequest,
    NWCSummary,
    PegSimulationRequest,
    PegSimulationResponse,
    PegSimulationResult,
)
from app.services.nwc.nwc_service import (
    get_nwc_calculation,
    list_nwc_calculations,
    recalculate_peg,
    run_nwc_calculation,
    simulate_peg_scenarios,
    update_line_item_classification,
)

router = APIRouter()


# -- NWC Calculation ------------------------------------------------


@router.post(
    "/deals/{deal_id}/nwc/calculate",
    response_model=NWCCalculationRead,
    status_code=201,
)
@limiter.limit("5/minute")
def calculate_nwc(
    request: Request,
    deal_id: uuid.UUID,
    body: NWCRunRequest,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """NWC 계산을 실행한다."""
    deal = db.get(Deal, deal_id)
    if not deal:
        raise NotFoundError("Deal", str(deal_id))

    snapshot = db.get(DealSnapshot, body.snapshot_id)
    if not snapshot or snapshot.deal_id != deal_id:
        raise NotFoundError("DealSnapshot", str(body.snapshot_id))

    return run_nwc_calculation(
        db,
        deal_id,
        body.snapshot_id,
        peg_method=body.peg_method.value,
        custom_peg_value=body.custom_peg_value,
    )


@router.get(
    "/deals/{deal_id}/nwc",
    response_model=list[NWCCalculationRead],
)
def list_nwc(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """딜의 모든 NWC 계산 결과를 조회한다."""
    deal = db.get(Deal, deal_id)
    if not deal:
        raise NotFoundError("Deal", str(deal_id))

    return list_nwc_calculations(db, deal_id)


@router.get(
    "/deals/{deal_id}/nwc/{nwc_id}",
    response_model=NWCCalculationRead,
)
def get_nwc(
    deal_id: uuid.UUID,
    nwc_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """특정 NWC 계산 결과를 조회한다."""
    nwc = get_nwc_calculation(db, deal_id, nwc_id)
    if not nwc:
        raise NotFoundError("NWCCalculation", str(nwc_id))
    return nwc


# -- NWC Summary ----------------------------------------------------


@router.get(
    "/deals/{deal_id}/nwc/{nwc_id}/summary",
    response_model=NWCSummary,
)
def get_nwc_summary(
    deal_id: uuid.UUID,
    nwc_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """NWC 요약 정보를 조회한다."""
    nwc = get_nwc_calculation(db, deal_id, nwc_id)
    if not nwc:
        raise NotFoundError("NWCCalculation", str(nwc_id))

    above = [
        NWCLineItemRead.model_validate(li)
        for li in sorted(nwc.line_items, key=lambda x: x.display_order)
        if li.classification.value == "ABOVE_LINE"
    ]
    below = [
        NWCLineItemRead.model_validate(li)
        for li in sorted(nwc.line_items, key=lambda x: x.display_order)
        if li.classification.value == "BELOW_LINE"
    ]

    return NWCSummary(
        net_working_capital=nwc.net_working_capital,
        total_current_assets=nwc.total_current_assets,
        total_current_liabilities=nwc.total_current_liabilities,
        peg_method=nwc.peg_method,
        peg_target=nwc.peg_target,
        peg_delta=nwc.peg_delta,
        above_line_items=above,
        below_line_items=below,
        is_above_target=nwc.net_working_capital >= nwc.peg_target,
    )


# -- Peg Simulation -------------------------------------------------


@router.post(
    "/deals/{deal_id}/nwc/{nwc_id}/peg-simulate",
    response_model=PegSimulationResponse,
)
def simulate_pegs(
    deal_id: uuid.UUID,
    nwc_id: uuid.UUID,
    body: PegSimulationRequest | None = None,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """6종 Peg 시나리오를 시뮬레이션한다 — FDD-603."""
    nwc = get_nwc_calculation(db, deal_id, nwc_id)
    if not nwc:
        raise NotFoundError("NWCCalculation", str(nwc_id))

    custom_value = body.custom_value if body else None
    ref_nwc, results = simulate_peg_scenarios(db, nwc_id, custom_value)

    return PegSimulationResponse(
        reference_nwc=ref_nwc,
        scenarios=[
            PegSimulationResult(
                method=r.method,
                target_nwc=r.target_nwc,
                delta=r.delta,
                description=r.description,
            )
            for r in results
        ],
    )


@router.post(
    "/deals/{deal_id}/nwc/{nwc_id}/recalculate-peg",
    response_model=NWCCalculationRead,
)
def recalculate_nwc_peg(
    deal_id: uuid.UUID,
    nwc_id: uuid.UUID,
    body: PegSimulationRequest,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """Peg 방법을 변경하고 재계산한다."""
    nwc = get_nwc_calculation(db, deal_id, nwc_id)
    if not nwc:
        raise NotFoundError("NWCCalculation", str(nwc_id))

    return recalculate_peg(
        db,
        nwc_id,
        peg_method=body.peg_method.value,
        custom_value=body.custom_value,
    )


# -- Line Item Classification ----------------------------------------


@router.put(
    "/deals/{deal_id}/nwc/{nwc_id}/items/{item_id}",
    response_model=NWCLineItemRead,
)
def update_nwc_item(
    deal_id: uuid.UUID,
    nwc_id: uuid.UUID,
    item_id: uuid.UUID,
    body: NWCLineItemUpdate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """NWC 항목 분류를 변경한다 — FDD-601."""
    return update_line_item_classification(db, deal_id, item_id, body)
