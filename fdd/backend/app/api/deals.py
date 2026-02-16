import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.auth.rbac import Permission
from app.core.errors import ErrorCode
from app.core.exceptions import NotFoundError, ValidationError
from app.database import get_db
from app.models.audit import AuditAction, AuditLog
from app.models.deal import (
    Deal,
    DealDefinition,
    DealSnapshot,
    DefinitionStatus,
)
from app.schemas.deal import (
    DealCreate,
    DealDefinitionApprove,
    DealDefinitionCreate,
    DealDefinitionRead,
    DealRead,
    DealSnapshotCreate,
    DealSnapshotRead,
    DealUpdate,
)
from app.services import snapshot_service
from app.utils.hashing import hash_json

router = APIRouter()


# ── Deals ─────────────────────────────────────────────────


@router.post("/deals", response_model=DealRead, status_code=201)
def create_deal(
    body: DealCreate,
    current_user: CurrentUser = require_permission(Permission.DEAL_CREATE),
    db: Session = Depends(get_db),
):
    deal = Deal(**body.model_dump())
    db.add(deal)
    db.flush()

    db.add(
        AuditLog(
            deal_id=deal.id,
            entity_type="deal",
            entity_id=deal.id,
            action=AuditAction.CREATE,
            actor=current_user.email,
            new_value=body.model_dump(mode="json"),
        )
    )

    db.commit()
    db.refresh(deal)
    return deal


@router.get("/deals", response_model=list[DealRead])
def list_deals(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = require_permission(Permission.DEAL_READ),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Deal)
        .where(Deal.is_deleted == False)  # noqa: E712
        .offset(skip)
        .limit(limit)
        .order_by(Deal.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.get("/deals/{deal_id}", response_model=DealRead)
def get_deal(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deal = db.get(Deal, deal_id)
    if deal is None or deal.is_deleted:
        raise NotFoundError("Deal", str(deal_id))
    return deal


@router.put("/deals/{deal_id}", response_model=DealRead)
def update_deal(
    deal_id: uuid.UUID,
    body: DealUpdate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise NotFoundError("Deal", str(deal_id))

    # Whitelist of fields allowed for update — prevents arbitrary attribute injection
    _UPDATABLE_FIELDS = {
        "name", "deal_type", "base_currency", "reference_date",
        "period_start", "period_end", "status",
        "client_name", "client_contact_name", "client_contact_email",
        "target_company_name", "team_partner_id", "team_manager_id",
        "scope_qoe", "scope_nwc", "scope_debt", "industry", "current_phase",
    }

    old_values = {}
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key not in _UPDATABLE_FIELDS:
            continue
        old_values[key] = getattr(deal, key)
        setattr(deal, key, value)

    db.add(
        AuditLog(
            deal_id=deal.id,
            entity_type="deal",
            entity_id=deal.id,
            action=AuditAction.UPDATE,
            actor=current_user.email,
            old_value=old_values,
            new_value=update_data,
        )
    )

    db.commit()
    db.refresh(deal)
    return deal


@router.delete("/deals/{deal_id}", status_code=204)
def delete_deal(
    deal_id: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """Soft delete — marks deal as deleted without removing data."""
    deal = db.get(Deal, deal_id)
    if deal is None or deal.is_deleted:
        raise NotFoundError("Deal", str(deal_id))

    deal.is_deleted = True
    deal.deleted_at = datetime.now(UTC)

    db.add(
        AuditLog(
            deal_id=deal.id,
            entity_type="deal",
            entity_id=deal.id,
            action=AuditAction.UPDATE,
            actor=current_user.email,
            old_value={"is_deleted": False},
            new_value={"is_deleted": True},
        )
    )

    db.commit()
    return None


# ── Deal Definitions ──────────────────────────────────────


@router.post(
    "/deals/{deal_id}/definitions",
    response_model=DealDefinitionRead,
    status_code=201,
)
def create_definition(
    deal_id: uuid.UUID,
    body: DealDefinitionCreate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise NotFoundError("Deal", str(deal_id))

    # Determine next version number
    stmt = (
        select(DealDefinition.version)
        .where(DealDefinition.deal_id == deal_id)
        .order_by(DealDefinition.version.desc())
        .limit(1)
    )
    latest_version = db.scalar(stmt)
    next_version = (latest_version or 0) + 1

    definition_dict = body.definition_data.model_dump()
    definition_hash = hash_json(definition_dict)

    definition = DealDefinition(
        deal_id=deal_id,
        version=next_version,
        definition_data=definition_dict,
        hash=definition_hash,
    )
    db.add(definition)
    db.flush()

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="deal_definition",
            entity_id=definition.id,
            action=AuditAction.CREATE,
            actor=current_user.email,
            new_value={"version": next_version, "hash": definition_hash},
        )
    )

    db.commit()
    db.refresh(definition)
    return definition


@router.get("/deals/{deal_id}/definitions", response_model=list[DealDefinitionRead])
def list_definitions(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(DealDefinition)
        .where(DealDefinition.deal_id == deal_id)
        .order_by(DealDefinition.version.desc())
    )
    return list(db.scalars(stmt).all())


@router.get(
    "/deals/{deal_id}/definitions/{version}",
    response_model=DealDefinitionRead,
)
def get_definition(
    deal_id: uuid.UUID,
    version: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(DealDefinition).where(
        DealDefinition.deal_id == deal_id,
        DealDefinition.version == version,
    )
    definition = db.scalar(stmt)
    if definition is None:
        raise NotFoundError("DealDefinition", f"deal={deal_id} v{version}")
    return definition


@router.put(
    "/deals/{deal_id}/definitions/{version}/approve",
    response_model=DealDefinitionRead,
)
def approve_definition(
    deal_id: uuid.UUID,
    version: int,
    body: DealDefinitionApprove,
    current_user: CurrentUser = require_permission(Permission.DEFINITION_APPROVE),
    db: Session = Depends(get_db),
):
    stmt = select(DealDefinition).where(
        DealDefinition.deal_id == deal_id,
        DealDefinition.version == version,
    )
    definition = db.scalar(stmt)
    if definition is None:
        raise NotFoundError("DealDefinition", f"deal={deal_id} v{version}")

    if definition.status == DefinitionStatus.LOCKED:
        raise ValidationError(
            ErrorCode.DATA_VALIDATION,
            "Definition is already locked",
        )

    old_status = definition.status.value
    definition.status = DefinitionStatus.APPROVED
    definition.approved_by = body.approved_by
    definition.approved_at = datetime.now(UTC)

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="deal_definition",
            entity_id=definition.id,
            action=AuditAction.APPROVE,
            actor=current_user.email,
            old_value={"status": old_status},
            new_value={"status": "APPROVED"},
        )
    )

    db.commit()
    db.refresh(definition)
    return definition


# ── Deal Snapshots ────────────────────────────────────────


@router.post(
    "/deals/{deal_id}/snapshots",
    response_model=DealSnapshotRead,
    status_code=201,
)
def create_snapshot(
    deal_id: uuid.UUID,
    body: DealSnapshotCreate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise NotFoundError("Deal", str(deal_id))

    try:
        snapshot = snapshot_service.create_snapshot(
            db, deal_id, body.definition_version_id
        )
    except ValueError as e:
        raise ValidationError(
            ErrorCode.DATA_VALIDATION,
            str(e),
        ) from e

    return snapshot


@router.get("/deals/{deal_id}/snapshots", response_model=list[DealSnapshotRead])
def list_snapshots(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(DealSnapshot)
        .where(DealSnapshot.deal_id == deal_id)
        .order_by(DealSnapshot.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.get(
    "/deals/{deal_id}/snapshots/{snapshot_id}",
    response_model=DealSnapshotRead,
)
def get_snapshot(
    deal_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    snapshot = db.get(DealSnapshot, snapshot_id)
    if snapshot is None or snapshot.deal_id != deal_id:
        raise NotFoundError("DealSnapshot", str(snapshot_id))
    return snapshot


# ── Cross-Module Summary ─────────────────────────────────


@router.get("/deals/{deal_id}/summary")
def get_deal_summary(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deal의 FDD 분석 요약을 반환한다 — 크로스모듈 참조용.

    IM 백엔드가 FDD 결과를 참조할 때 사용.
    """
    from app.models import NetDebtCalculation, NWCCalculation, QoECalculation
    from app.models.debt import DebtStatus
    from app.models.nwc import NWCStatus
    from app.models.qoe import QoEStatus

    deal = db.get(Deal, deal_id)
    if deal is None:
        raise NotFoundError("Deal", str(deal_id))

    summary: dict = {
        "deal_id": str(deal_id),
        "deal_name": deal.name,
        "industry": deal.industry.value if deal.industry else "general",
        "status": deal.status.value,
        "qoe": None,
        "nwc": None,
        "debt": None,
    }

    # QoE — use select() API for consistency
    qoe = db.scalar(
        select(QoECalculation)
        .where(QoECalculation.deal_id == deal_id, QoECalculation.status == QoEStatus.APPROVED)
        .order_by(QoECalculation.created_at.desc())
        .limit(1)
    )
    if qoe:
        summary["qoe"] = {
            "reported_ebitda": str(qoe.reported_ebitda),
            "adjusted_ebitda": str(qoe.adjusted_ebitda),
            "total_adjustments": str(qoe.total_adjustments),
        }

    # NWC
    nwc = db.scalar(
        select(NWCCalculation)
        .where(NWCCalculation.deal_id == deal_id, NWCCalculation.status == NWCStatus.APPROVED)
        .order_by(NWCCalculation.created_at.desc())
        .limit(1)
    )
    if nwc:
        summary["nwc"] = {
            "net_working_capital": str(nwc.net_working_capital),
            "peg_target": str(nwc.peg_target),
            "peg_method": nwc.peg_method.value if nwc.peg_method else None,
        }

    # Net Debt
    debt = db.scalar(
        select(NetDebtCalculation)
        .where(NetDebtCalculation.deal_id == deal_id, NetDebtCalculation.status == DebtStatus.APPROVED)
        .order_by(NetDebtCalculation.created_at.desc())
        .limit(1)
    )
    if debt:
        summary["debt"] = {
            "net_debt": str(debt.net_debt),
            "adjusted_net_debt": str(debt.adjusted_net_debt),
            "gross_debt": str(debt.gross_debt),
        }

    return summary
