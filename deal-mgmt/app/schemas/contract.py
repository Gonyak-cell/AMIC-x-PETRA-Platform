from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ContractStatus, ContractType, SignatureStatus


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    contract_type: ContractType
    status: ContractStatus
    title: str
    description: str | None = None
    counterparty_name: str | None = None
    effective_date: str | None = None
    expiry_date: str | None = None
    current_version: int
    document_url: str | None = None
    seller_signature: SignatureStatus
    buyer_signature: SignatureStatus
    ai_analysis_summary: str | None = None
    ai_risk_flags: list[dict] | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("ai_risk_flags", mode="before")
    @classmethod
    def normalize_ai_risk_flags(cls, value):
        if value is None or isinstance(value, list):
            return value
        if isinstance(value, dict):
            clauses = value.get("clauses")
            if isinstance(clauses, list):
                return clauses
            return [
                {
                    "clause": str(value.get("clause") or value.get("contract_type") or "Contract"),
                    "risk_level": str(value.get("risk_level") or "INFO"),
                    "description": str(value.get("description") or value),
                }
            ]
        return None


class ContractCreate(BaseModel):
    contract_type: ContractType = ContractType.SPA
    title: str = Field(..., max_length=300)
    description: str | None = None
    counterparty_name: str | None = Field(None, max_length=200)
    effective_date: str | None = Field(None, max_length=10)
    expiry_date: str | None = Field(None, max_length=10)
    document_url: str | None = Field(None, max_length=500)
    notes: str | None = None


class ContractUpdate(BaseModel):
    contract_type: ContractType | None = None
    status: ContractStatus | None = None
    title: str | None = Field(None, max_length=300)
    description: str | None = None
    counterparty_name: str | None = Field(None, max_length=200)
    effective_date: str | None = Field(None, max_length=10)
    expiry_date: str | None = Field(None, max_length=10)
    document_url: str | None = Field(None, max_length=500)
    seller_signature: SignatureStatus | None = None
    buyer_signature: SignatureStatus | None = None
    notes: str | None = None


class ContractVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contract_id: uuid.UUID
    version_number: int
    changes_summary: str | None = None
    document_url: str
    created_by_email: str | None = None
    file_size_bytes: int | None = None
    file_name: str | None = None
    created_at: datetime
    updated_at: datetime


class ContractVersionCreate(BaseModel):
    changes_summary: str | None = None
    document_url: str = Field(..., max_length=500)
    created_by_email: str | None = Field(None, max_length=255)
    file_size_bytes: int | None = None
    file_name: str | None = Field(None, max_length=500)


class ContractSummary(BaseModel):
    total: int
    by_type: dict[str, int]
    by_status: dict[str, int]
    pending_signatures: int
    fully_executed: int


class AIRiskFlag(BaseModel):
    clause: str
    risk_level: str
    description: str


class AIAnalysisResult(BaseModel):
    status: str
    message: str
    clauses: list[AIRiskFlag]


# ── 협상 워크스페이스 ──────────────────────────────────


class NegotiationGanttItem(BaseModel):
    contract_id: uuid.UUID
    contract_type: str
    title: str
    status: str
    total_markups: int = 0
    open_issues: int = 0
    first_markup_at: str | None = None
    latest_markup_at: str | None = None
    created_at: str | None = None


class NegotiationGanttResponse(BaseModel):
    items: list[NegotiationGanttItem]
    transaction_start_date: str | None = None
    target_close_date: str | None = None


class MarkupComparisonResponse(BaseModel):
    version_a: int
    version_b: int
    markup_a_label: str | None = None
    markup_b_label: str | None = None
    markup_a_party: str | None = None
    markup_b_party: str | None = None
    markup_a_summary: str | None = None
    markup_b_summary: str | None = None
    key_changes_a: list[str] | None = None
    key_changes_b: list[str] | None = None
    additions: list[str]
    deletions: list[str]
    common: list[str]
