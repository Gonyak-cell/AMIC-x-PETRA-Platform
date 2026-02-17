import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.deal import (
    DealPhase,
    DealStatus,
    DealStructure,
    DealType,
    DefinitionStatus,
    IndustryType,
    InvestmentType,
    SellerType,
    SnapshotStatus,
)

# ── Deal ──────────────────────────────────────────────────


class DealCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    target_company_name: str = Field(..., min_length=1, max_length=255)
    deal_type: DealType = DealType.COMPLETION_ACCOUNTS
    base_currency: str = Field(default="KRW", max_length=10)
    reference_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    created_by: str = Field(default="system", max_length=100)

    # Workflow fields (optional at creation)
    client_name: str | None = Field(default=None, max_length=255)
    client_contact_name: str | None = Field(default=None, max_length=255)
    client_contact_email: str | None = Field(default=None, max_length=255)
    team_partner_id: uuid.UUID | None = None
    team_manager_id: uuid.UUID | None = None
    scope_qoe: bool = True
    scope_nwc: bool = True
    scope_debt: bool = True
    industry: IndustryType = IndustryType.GENERAL

    # Deal classification
    deal_structure: DealStructure | None = None
    investment_type: InvestmentType | None = None
    seller_type: SellerType | None = None


class DealUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    deal_type: DealType | None = None
    base_currency: str | None = Field(default=None, max_length=10)
    reference_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    status: DealStatus | None = None

    # Workflow fields
    client_name: str | None = Field(default=None, max_length=255)
    client_contact_name: str | None = Field(default=None, max_length=255)
    client_contact_email: str | None = Field(default=None, max_length=255)
    target_company_name: str | None = Field(default=None, max_length=255)
    team_partner_id: uuid.UUID | None = None
    team_manager_id: uuid.UUID | None = None
    scope_qoe: bool | None = None
    scope_nwc: bool | None = None
    scope_debt: bool | None = None
    industry: IndustryType | None = None
    current_phase: DealPhase | None = None

    # Deal classification
    deal_structure: DealStructure | None = None
    investment_type: InvestmentType | None = None
    seller_type: SellerType | None = None


class DealRead(BaseModel):
    id: uuid.UUID
    name: str
    deal_type: DealType
    base_currency: str
    reference_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    status: DealStatus
    created_by: str
    created_at: datetime
    updated_at: datetime

    # Workflow fields
    client_name: str | None = None
    client_contact_name: str | None = None
    client_contact_email: str | None = None
    target_company_name: str | None = None
    team_partner_id: uuid.UUID | None = None
    team_manager_id: uuid.UUID | None = None
    scope_qoe: bool = True
    scope_nwc: bool = True
    scope_debt: bool = True
    industry: IndustryType = IndustryType.GENERAL
    current_phase: DealPhase = DealPhase.MOU

    # Deal classification
    deal_structure: DealStructure | None = None
    investment_type: InvestmentType | None = None
    seller_type: SellerType | None = None

    model_config = {"from_attributes": True}


# ── Deal Definition ───────────────────────────────────────


class DefinitionData(BaseModel):
    """SPA/LOI 정의를 설정값으로 표현하는 스키마."""

    cash: dict[str, list[str]] = Field(
        default_factory=lambda: {"include": [], "exclude": []},
        description="Cash 정의: 포함/제외 계정 목록",
    )
    debt: dict[str, list[str]] = Field(
        default_factory=lambda: {"include": [], "exclude": []},
        description="Debt 정의: 포함/제외 계정 목록",
    )
    debt_like: list[dict[str, Any]] = Field(
        default_factory=list,
        description="debt-like 항목 목록 [{item, category, rationale}]",
    )
    cash_like: list[dict[str, Any]] = Field(
        default_factory=list,
        description="cash-like 항목 목록",
    )
    nwc: dict[str, list[str]] = Field(
        default_factory=lambda: {"include": [], "exclude": []},
        description="NWC 정의: 포함/제외 계정 목록",
    )
    target_nwc: dict[str, Any] = Field(
        default_factory=lambda: {"method": "6M_AVG", "value": None},
        description="Target NWC(peg) 산정 방법 및 값",
    )
    lease_ifrs16: dict[str, bool] = Field(
        default_factory=lambda: {"include_in_debt": False},
        description="IFRS 16 리스부채 Net Debt 포함 여부",
    )


class DealDefinitionCreate(BaseModel):
    definition_data: DefinitionData


class DealDefinitionRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    version: int
    definition_data: dict[str, Any]
    status: DefinitionStatus
    approved_by: str | None
    approved_at: datetime | None
    hash: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DealDefinitionApprove(BaseModel):
    approved_by: str = Field(..., min_length=1, max_length=100)


# ── Deal Snapshot ─────────────────────────────────────────


class DealSnapshotCreate(BaseModel):
    definition_version_id: uuid.UUID


class DealSnapshotRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    definition_version_id: uuid.UUID
    engine_version: str
    input_hash: str
    result_hash: str | None
    status: SnapshotStatus
    created_at: datetime

    model_config = {"from_attributes": True}
