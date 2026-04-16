from __future__ import annotations

import re
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.enums import (
    DealStructure,
    DealType,
    TransactionPhase,
    TransactionSide,
    TransactionStatus,
)

_GARBLED_TEXT_ERROR = "Text appears garbled. Please verify your input method and retry."
_QUESTION_RUN_PATTERN = re.compile(r"\?{3,}")


def _validate_transaction_text(value: str | None) -> str | None:
    if value is None:
        return value

    normalized = value.strip()
    if not normalized:
        return value

    if "\ufffd" in normalized or _QUESTION_RUN_PATTERN.search(normalized):
        raise ValueError(_GARBLED_TEXT_ERROR)

    return value


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code_name: str
    name: str
    deal_type: DealType
    side: TransactionSide
    phase: TransactionPhase
    status: TransactionStatus
    target_company_name: str
    target_corp_code: str | None = None
    client_name: str
    estimated_deal_value: Decimal | None = None
    currency: str = "KRW"
    deal_structure: DealStructure | None = None
    investment_type: str | None = None
    industry: str | None = None
    lead_advisor_email: str
    deal_captain_email: str | None = None
    target_close_date: str | None = None
    sale_process: str | None = None
    control_transfer: str | None = None
    target_stake: Decimal | None = None
    new_share_ratio: Decimal | None = None
    old_share_ratio: Decimal | None = None
    valuation_basis: str | None = None
    cross_border: str | None = None
    target_buyer_types: list[str] | None = None
    exclusivity: bool | None = None
    exclusivity_deadline: str | None = None
    fdd_deal_id: str | None = None
    im_document_id: str | None = None
    notes: str | None = None
    corporate_info: dict | None = None
    financial_summary: dict | None = None
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime

    @field_serializer(
        "estimated_deal_value",
        "target_stake",
        "new_share_ratio",
        "old_share_ratio",
    )
    @classmethod
    def _serialize_decimal(cls, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class TransactionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    deal_type: DealType
    side: TransactionSide
    target_company_name: str = Field(..., min_length=1, max_length=200)
    target_corp_code: str | None = Field(None, max_length=20)
    client_name: str = Field(..., min_length=1, max_length=200)
    estimated_deal_value: Decimal | None = None
    currency: str = Field("KRW", max_length=3)
    deal_structure: DealStructure | None = None
    investment_type: str | None = Field(None, max_length=50)
    industry: str | None = Field(None, max_length=100)
    lead_advisor_email: str = Field(
        ...,
        max_length=255,
        pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
    )
    deal_captain_email: str | None = Field(
        None,
        max_length=255,
        pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
    )
    target_close_date: str | None = Field(None, max_length=10)
    sale_process: str | None = Field(None, max_length=30)
    control_transfer: str | None = Field(None, max_length=20)
    target_stake: Decimal | None = Field(None, ge=0, le=100)
    new_share_ratio: Decimal | None = Field(None, ge=0, le=100)
    old_share_ratio: Decimal | None = Field(None, ge=0, le=100)
    valuation_basis: str | None = Field(None, max_length=30)
    cross_border: str | None = Field(None, max_length=20)
    target_buyer_types: list[str] | None = None
    exclusivity: bool | None = None
    exclusivity_deadline: str | None = Field(None, max_length=10)
    notes: str | None = None

    @field_validator("name", "target_company_name", "client_name")
    @classmethod
    def validate_transaction_text(cls, value: str) -> str:
        return _validate_transaction_text(value) or value


class CorporateInfoUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company_name: str | None = Field(None, max_length=200)
    representative_name: str | None = Field(None, max_length=200)
    business_registration_number: str | None = Field(None, max_length=30)
    corporate_registration_number: str | None = Field(None, max_length=30)
    head_office_address: str | None = Field(None, max_length=500)
    business_type: str | None = Field(None, max_length=200)
    business_item: str | None = Field(None, max_length=200)

    @field_validator(
        "company_name",
        "representative_name",
        "business_registration_number",
        "corporate_registration_number",
        "head_office_address",
        "business_type",
        "business_item",
    )
    @classmethod
    def validate_corporate_info_text(cls, value: str | None) -> str | None:
        return _validate_transaction_text(value)


class TransactionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    deal_type: DealType | None = None
    side: TransactionSide | None = None
    target_company_name: str | None = Field(None, min_length=1, max_length=200)
    target_corp_code: str | None = Field(None, max_length=20)
    client_name: str | None = Field(None, min_length=1, max_length=200)
    estimated_deal_value: Decimal | None = None
    currency: str | None = Field(None, max_length=3)
    deal_structure: DealStructure | None = None
    investment_type: str | None = Field(None, max_length=50)
    industry: str | None = Field(None, max_length=100)
    lead_advisor_email: str | None = Field(
        None,
        max_length=255,
        pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
    )
    deal_captain_email: str | None = Field(
        None,
        max_length=255,
        pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
    )
    target_close_date: str | None = Field(None, max_length=10)
    sale_process: str | None = Field(None, max_length=30)
    control_transfer: str | None = Field(None, max_length=20)
    target_stake: Decimal | None = Field(None, ge=0, le=100)
    new_share_ratio: Decimal | None = Field(None, ge=0, le=100)
    old_share_ratio: Decimal | None = Field(None, ge=0, le=100)
    valuation_basis: str | None = Field(None, max_length=30)
    cross_border: str | None = Field(None, max_length=20)
    target_buyer_types: list[str] | None = None
    exclusivity: bool | None = None
    exclusivity_deadline: str | None = Field(None, max_length=10)
    notes: str | None = None
    fdd_deal_id: str | None = None
    im_document_id: str | None = None
    corporate_info: CorporateInfoUpdate | None = None

    @field_validator("name", "target_company_name", "client_name")
    @classmethod
    def validate_transaction_text(cls, value: str | None) -> str | None:
        return _validate_transaction_text(value)


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    total: int
    limit: int
    offset: int
