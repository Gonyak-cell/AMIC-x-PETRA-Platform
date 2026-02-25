from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from app.models.enums import TransactionPhase, TransactionStatus


class PrerequisiteLevel(str, Enum):
    REQUIRED = "REQUIRED"
    RECOMMENDED = "RECOMMENDED"


class PhasePrerequisite(BaseModel):
    field: str
    label: str
    satisfied: bool
    level: PrerequisiteLevel = PrerequisiteLevel.REQUIRED


class PhaseCompletionStatus(BaseModel):
    current_phase: TransactionPhase
    prerequisites: list[PhasePrerequisite]
    all_met: bool
    required_met: bool = True
    has_warnings: bool = False
    can_advance: bool
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
