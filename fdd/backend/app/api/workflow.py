"""Workflow API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.audit import AuditAction, AuditLog
from app.models.deal import Deal, DealPhase
from app.models.upload import UploadFile
from app.models.vdr import VdrFolder

router = APIRouter(prefix="/deals/{deal_id}/workflow", tags=["workflow"])


class WorkflowPhaseUpdate(BaseModel):
    """Request body for updating workflow phase."""

    target_phase: DealPhase


class PhaseStatus(BaseModel):
    """Completion status for a single workflow phase."""

    phase: DealPhase
    completed: bool


class WorkflowStatusResponse(BaseModel):
    """Full workflow status for a deal."""

    deal_id: UUID
    current_phase: DealPhase
    phases: list[PhaseStatus]


def _check_phase_completion(
    db: Session,
    deal: Deal,
    phase: DealPhase,
) -> bool:
    """Check whether a given phase is considered complete.

    Args:
        db: Database session.
        deal: Deal ORM object.
        phase: The phase to check.

    Returns:
        True if the phase requirements are met.
    """
    if phase == DealPhase.MOU:
        # MOU is complete when deal has basic info
        return bool(deal.client_name and deal.target_company_name)

    if phase == DealPhase.VDR_SETUP:
        # VDR setup is complete when folders exist
        folder_count = db.scalar(
            select(func.count())
            .select_from(VdrFolder)
            .where(VdrFolder.deal_id == deal.id)
        )
        return bool(folder_count and folder_count > 0)

    if phase == DealPhase.DATA_UPLOAD:
        # Data upload is complete when at least one file uploaded
        file_count = db.scalar(
            select(func.count())
            .select_from(UploadFile)
            .where(UploadFile.deal_id == deal.id)
        )
        return bool(file_count and file_count > 0)

    if phase == DealPhase.ANALYSIS:
        # Analysis is complete when scope flags have matching results
        # Simplified: check if deal has snapshots
        return False

    if phase == DealPhase.REPORTING:
        # Reporting is complete when report versions exist
        return False

    return False


@router.get("/", response_model=WorkflowStatusResponse)
def get_workflow_status(
    deal_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get workflow status for a deal.

    Returns the current phase and per-phase completion flags.

    Args:
        deal_id: Deal UUID.

    Returns:
        Workflow status with current phase and completion per phase.
    """
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    phases = [
        PhaseStatus(
            phase=phase,
            completed=_check_phase_completion(db, deal, phase),
        )
        for phase in DealPhase
    ]

    return WorkflowStatusResponse(
        deal_id=deal.id,
        current_phase=deal.current_phase,
        phases=phases,
    )


@router.put("/phase", response_model=WorkflowStatusResponse)
def update_workflow_phase(
    deal_id: UUID,
    body: WorkflowPhaseUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the workflow phase for a deal.

    Args:
        deal_id: Deal UUID.
        body: Target phase to transition to.

    Returns:
        Updated workflow status.
    """
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    old_phase = deal.current_phase
    deal.current_phase = body.target_phase

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="deal",
            entity_id=deal.id,
            action=AuditAction.UPDATE,
            actor=current_user.email,
            old_value={"current_phase": old_phase.value},
            new_value={"current_phase": body.target_phase.value},
        )
    )

    db.commit()
    db.refresh(deal)

    phases = [
        PhaseStatus(
            phase=phase,
            completed=_check_phase_completion(db, deal, phase),
        )
        for phase in DealPhase
    ]

    return WorkflowStatusResponse(
        deal_id=deal.id,
        current_phase=deal.current_phase,
        phases=phases,
    )
