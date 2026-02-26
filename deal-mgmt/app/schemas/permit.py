"""인허가 분석 Pydantic 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    PermitAnalysisStatus,
    PermitFilingType,
    PermitRequirementStatus,
    PermitTimingType,
)

# ── 공통 서브 모델 ──────────────────────────────────────────

class ExistingPermit(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    issuer: str = Field(..., min_length=1, max_length=200)
    reg_number: str | None = Field(None, max_length=100)


class RequiredDocument(BaseModel):
    name: str
    description: str | None = None


# ── PermitAnalysis ──────────────────────────────────────────

class PermitAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    status: PermitAnalysisStatus
    business_types: list[str] | None = None
    existing_permits: list[ExistingPermit] | None = None
    analysis_method: str | None = None
    llm_cost_usd: float | None = None
    analysis_notes: str | None = None
    analyzed_by_email: str | None = None
    created_at: datetime
    updated_at: datetime


class PermitAnalyzeRequest(BaseModel):
    """인허가 분석 실행 요청."""
    business_types: list[str] = Field(..., min_length=1)
    existing_permits: list[ExistingPermit] = Field(default_factory=list)


# ── PermitRequirement ───────────────────────────────────────

class PermitRequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    transaction_id: uuid.UUID
    permit_name: str
    regulatory_body: str
    legal_basis: str | None = None
    filing_type: PermitFilingType
    timing_type: PermitTimingType
    pre_filing_deadline_days: int | None = None
    post_filing_deadline_days: int | None = None
    calculated_deadline: str | None = None
    required_documents: list[RequiredDocument] | None = None
    status: PermitRequirementStatus
    source: str
    confidence: float | None = None
    compliance_item_id: uuid.UUID | None = None
    notes: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PermitRequirementCreate(BaseModel):
    """인허가 요건 수동 추가."""
    permit_name: str = Field(..., min_length=1, max_length=300)
    regulatory_body: str = Field(..., min_length=1, max_length=200)
    legal_basis: str | None = Field(None, max_length=500)
    filing_type: PermitFilingType
    timing_type: PermitTimingType
    pre_filing_deadline_days: int | None = None
    post_filing_deadline_days: int | None = None
    required_documents: list[RequiredDocument] | None = None
    notes: str | None = None


class PermitRequirementUpdate(BaseModel):
    """인허가 요건 수정."""
    status: PermitRequirementStatus | None = None
    notes: str | None = None
    required_documents: list[RequiredDocument] | None = None


# ── KB 참조 ─────────────────────────────────────────────────

class IndustryOption(BaseModel):
    code: str
    label: str
    sub_categories: list[str] | None = None
