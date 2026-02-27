"""QoE (Quality of Earnings) API — FDD-501/502/503.

Reported EBITDA 계산, 조정항목 관리, Bridge 재계산 엔드포인트.
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
from app.schemas.qoe import (
    AdjustmentItemApprove,
    AdjustmentItemCreate,
    AdjustmentItemRead,
    AdjustmentItemUpdate,
    QoEBridgeSummary,
    QoECalculationRead,
    QoERunRequest,
)
from app.services.qoe.qoe_service import (
    add_manual_adjustment,
    approve_adjustment,
    get_qoe_calculation,
    list_qoe_calculations,
    recalculate_bridge,
    run_qoe_calculation,
    update_adjustment,
)

router = APIRouter()


# ── QoE Calculation ──────────────────────────────────────


@router.post(
    "/deals/{deal_id}/qoe/calculate",
    response_model=QoECalculationRead,
    status_code=201,
)
@limiter.limit("5/minute")
def calculate_qoe(
    request: Request,
    deal_id: uuid.UUID,
    body: QoERunRequest,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """QoE(Adjusted EBITDA) 계산을 실행한다."""
    deal = db.get(Deal, deal_id)
    if not deal:
        raise NotFoundError("Deal", str(deal_id))

    snapshot = db.get(DealSnapshot, body.snapshot_id)
    if not snapshot or snapshot.deal_id != deal_id:
        raise NotFoundError("DealSnapshot", str(body.snapshot_id))

    return run_qoe_calculation(db, deal_id, body.snapshot_id)


@router.get(
    "/deals/{deal_id}/qoe",
    response_model=list[QoECalculationRead],
)
def list_qoe(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """딜의 모든 QoE 계산 결과를 조회한다."""
    deal = db.get(Deal, deal_id)
    if not deal:
        raise NotFoundError("Deal", str(deal_id))

    return list_qoe_calculations(db, deal_id)


@router.get(
    "/deals/{deal_id}/qoe/{qoe_id}",
    response_model=QoECalculationRead,
)
def get_qoe(
    deal_id: uuid.UUID,
    qoe_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """특정 QoE 계산 결과를 조회한다."""
    qoe = get_qoe_calculation(db, deal_id, qoe_id)
    if not qoe:
        raise NotFoundError("QoECalculation", str(qoe_id))
    return qoe


# ── QoE Bridge ───────────────────────────────────────────


@router.get(
    "/deals/{deal_id}/qoe/{qoe_id}/bridge",
    response_model=QoEBridgeSummary,
)
def get_qoe_bridge(
    deal_id: uuid.UUID,
    qoe_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """QoE Bridge 요약을 조회한다."""
    qoe = get_qoe_calculation(db, deal_id, qoe_id)
    if not qoe:
        raise NotFoundError("QoECalculation", str(qoe_id))

    return QoEBridgeSummary(
        reported_ebitda=qoe.reported_ebitda,
        adjustments=[
            AdjustmentItemRead.model_validate(a)
            for a in sorted(qoe.adjustments, key=lambda x: x.display_order)
        ],
        total_adjustments=qoe.total_adjustments,
        adjusted_ebitda=qoe.adjusted_ebitda,
        balance_check_error=qoe.balance_check_error,
        is_balanced=qoe.balance_check_error == 0,
    )


@router.post(
    "/deals/{deal_id}/qoe/{qoe_id}/recalculate",
    response_model=QoECalculationRead,
)
def recalculate_qoe_bridge(
    deal_id: uuid.UUID,
    qoe_id: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """APPROVED 조정항목 기준으로 Bridge를 재계산한다."""
    qoe = get_qoe_calculation(db, deal_id, qoe_id)
    if not qoe:
        raise NotFoundError("QoECalculation", str(qoe_id))

    return recalculate_bridge(db, qoe_id)


# ── Adjustment Items ─────────────────────────────────────


@router.post(
    "/deals/{deal_id}/qoe/{qoe_id}/adjustments",
    response_model=AdjustmentItemRead,
    status_code=201,
)
def create_adjustment(
    deal_id: uuid.UUID,
    qoe_id: uuid.UUID,
    body: AdjustmentItemCreate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """수동 조정항목을 추가한다."""
    return add_manual_adjustment(db, deal_id, qoe_id, body)


@router.put(
    "/deals/{deal_id}/qoe/{qoe_id}/adjustments/{adjustment_id}",
    response_model=AdjustmentItemRead,
)
def update_adjustment_endpoint(
    deal_id: uuid.UUID,
    qoe_id: uuid.UUID,
    adjustment_id: uuid.UUID,
    body: AdjustmentItemUpdate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """조정항목을 수정한다."""
    return update_adjustment(db, deal_id, adjustment_id, body)


@router.post(
    "/deals/{deal_id}/qoe/{qoe_id}/adjustments/{adjustment_id}/approve",
    response_model=AdjustmentItemRead,
)
def approve_adjustment_endpoint(
    deal_id: uuid.UUID,
    qoe_id: uuid.UUID,
    adjustment_id: uuid.UUID,
    body: AdjustmentItemApprove,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """조정항목을 승인한다."""
    return approve_adjustment(db, deal_id, adjustment_id, body)
