from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TransactionPhase, TransactionSide, TransactionStatus


# ── Response ────────────────────────────────────────────
class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code_name: str
    name: str
    side: TransactionSide
    phase: TransactionPhase
    status: TransactionStatus
    target_company_name: str
    target_corp_code: str | None = None
    client_name: str
    estimated_deal_value: float | None = None
    currency: str = "KRW"
    deal_structure: str | None = None
    investment_type: str | None = None
    industry: str | None = None
    lead_advisor_email: str
    deal_captain_email: str | None = None
    target_close_date: str | None = None
    fdd_deal_id: str | None = None
    im_document_id: str | None = None
    notes: str | None = None
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime


# ── Create ──────────────────────────────────────────────
class TransactionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code_name: str = Field(..., min_length=1, max_length=100)
    side: TransactionSide
    target_company_name: str = Field(..., min_length=1, max_length=200)
    target_corp_code: str | None = Field(None, max_length=20)
    client_name: str = Field(..., min_length=1, max_length=200)
    estimated_deal_value: float | None = None
    currency: str = Field("KRW", max_length=3)
    deal_structure: str | None = Field(None, max_length=50)
    investment_type: str | None = Field(None, max_length=50)
    industry: str | None = Field(None, max_length=100)
    lead_advisor_email: str = Field(..., max_length=255)
    deal_captain_email: str | None = Field(None, max_length=255)
    target_close_date: str | None = Field(None, max_length=10)
    notes: str | None = None


# ── Update ──────────────────────────────────────────────
class TransactionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    code_name: str | None = Field(None, min_length=1, max_length=100)
    target_company_name: str | None = Field(None, min_length=1, max_length=200)
    target_corp_code: str | None = Field(None, max_length=20)
    client_name: str | None = Field(None, min_length=1, max_length=200)
    estimated_deal_value: float | None = None
    currency: str | None = Field(None, max_length=3)
    deal_structure: str | None = Field(None, max_length=50)
    investment_type: str | None = Field(None, max_length=50)
    industry: str | None = Field(None, max_length=100)
    lead_advisor_email: str | None = Field(None, max_length=255)
    deal_captain_email: str | None = Field(None, max_length=255)
    target_close_date: str | None = Field(None, max_length=10)
    notes: str | None = None


# ── List ────────────────────────────────────────────────
class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    total: int
    limit: int
    offset: int
