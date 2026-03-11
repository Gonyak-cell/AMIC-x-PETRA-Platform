from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import TransactionPhase, TransactionStatus


class PhasePrerequisite(BaseModel):
    field: str
    label: str
    satisfied: bool


class PhaseCompletionStatus(BaseModel):
    current_phase: TransactionPhase
    prerequisites: list[PhasePrerequisite]
    all_met: bool
    can_advance: bool
    blocking_reasons: list[str] = []
    next_phase: TransactionPhase | None = None
    previous_phase: TransactionPhase | None = None


class PhaseTransitionRequest(BaseModel):
    to_phase: TransactionPhase
    notes: str | None = None


class PhaseTransitionResponse(BaseModel):
    from_phase: TransactionPhase
    to_phase: TransactionPhase
    success: bool
    message: str


class StatusChangeRequest(BaseModel):
    to_status: TransactionStatus
    reason: str | None = None


class StatusChangeResponse(BaseModel):
    from_status: TransactionStatus
    to_status: TransactionStatus
    success: bool
    message: str
