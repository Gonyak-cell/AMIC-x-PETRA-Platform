from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskCategory, RiskLikelihood, RiskSeverity, RiskStatus

# ── severity/likelihood → 점수 매핑 (5x4 매트릭스) ───
_SEVERITY_SCORE = {
    RiskSeverity.CRITICAL: 4,
    RiskSeverity.HIGH: 3,
    RiskSeverity.MEDIUM: 2,
    RiskSeverity.LOW: 1,
}

_LIKELIHOOD_SCORE = {
    RiskLikelihood.VERY_HIGH: 5,
    RiskLikelihood.HIGH: 4,
    RiskLikelihood.MEDIUM: 3,
    RiskLikelihood.LOW: 2,
    RiskLikelihood.VERY_LOW: 1,
}


def compute_risk_score(severity: RiskSeverity, likelihood: RiskLikelihood) -> float:
    """리스크 스코어 = severity × likelihood (1~20)."""
    return _SEVERITY_SCORE[severity] * _LIKELIHOOD_SCORE[likelihood]


class RiskItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    category: RiskCategory
    title: str
    description: str | None = None
    severity: RiskSeverity
    likelihood: RiskLikelihood
    risk_score: float | None = None
    mitigation_strategy: str | None = None
    owner_email: str | None = None
    status: RiskStatus
    due_date: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class RiskItemCreate(BaseModel):
    category: RiskCategory
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    severity: RiskSeverity = RiskSeverity.MEDIUM
    likelihood: RiskLikelihood = RiskLikelihood.MEDIUM
    mitigation_strategy: str | None = None
    owner_email: str | None = Field(None, max_length=255)
    due_date: str | None = Field(None, max_length=10)
    notes: str | None = None


class RiskItemUpdate(BaseModel):
    category: RiskCategory | None = None
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    severity: RiskSeverity | None = None
    likelihood: RiskLikelihood | None = None
    mitigation_strategy: str | None = None
    owner_email: str | None = Field(None, max_length=255)
    status: RiskStatus | None = None
    due_date: str | None = Field(None, max_length=10)
    notes: str | None = None


class RiskCategorySummary(BaseModel):
    category: RiskCategory
    total: int
    critical: int
    high: int
    medium: int
    low: int


class RiskMatrixCell(BaseModel):
    severity: RiskSeverity
    likelihood: RiskLikelihood
    count: int


class RiskSummary(BaseModel):
    total: int
    by_category: list[RiskCategorySummary]
    by_status: dict[str, int]
    matrix: list[RiskMatrixCell]
    avg_risk_score: float
    unmitigated_critical: int
