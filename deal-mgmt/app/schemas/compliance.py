from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ComplianceCategory, ComplianceStatus


class ComplianceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    category: ComplianceCategory
    requirement: str
    description: str | None = None
    jurisdiction: str | None = None
    regulatory_body: str | None = None
    assignee_email: str | None = None
    status: ComplianceStatus
    due_date: str | None = None
    filing_reference: str | None = None
    document_url: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ComplianceItemCreate(BaseModel):
    category: ComplianceCategory
    requirement: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    jurisdiction: str | None = Field(None, max_length=100)
    regulatory_body: str | None = Field(None, max_length=200)
    assignee_email: str | None = Field(None, max_length=255)
    due_date: str | None = Field(None, max_length=10)
    filing_reference: str | None = Field(None, max_length=200)
    document_url: str | None = Field(None, max_length=500)
    notes: str | None = None


class ComplianceItemUpdate(BaseModel):
    category: ComplianceCategory | None = None
    requirement: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    jurisdiction: str | None = Field(None, max_length=100)
    regulatory_body: str | None = Field(None, max_length=200)
    assignee_email: str | None = Field(None, max_length=255)
    status: ComplianceStatus | None = None
    due_date: str | None = Field(None, max_length=10)
    filing_reference: str | None = Field(None, max_length=200)
    document_url: str | None = Field(None, max_length=500)
    notes: str | None = None


class ComplianceCategorySummary(BaseModel):
    category: ComplianceCategory
    total: int
    approved: int
    flagged: int
    pending: int


class ComplianceSummary(BaseModel):
    total: int
    by_category: list[ComplianceCategorySummary]
    by_status: dict[str, int]
    compliance_rate: float
    flagged_count: int
    overdue_count: int
