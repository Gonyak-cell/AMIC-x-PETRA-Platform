from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NdaPartyType, NdaStatus, NdaType


class NDAOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    party_type: NdaPartyType
    buyer_candidate_id: uuid.UUID | None = None
    nda_type: NdaType
    status: NdaStatus
    sent_at: str | None = None
    signed_at: str | None = None
    expires_at: str | None = None
    document_url: str | None = None
    notes: str | None = None
    counterparty_name: str | None = None
    jurisdiction: str | None = None
    confidentiality_period_months: int | None = None
    created_at: datetime
    updated_at: datetime


class NDACreate(BaseModel):
    party_type: NdaPartyType = NdaPartyType.BUYER
    buyer_candidate_id: uuid.UUID | None = None
    counterparty_name: str | None = Field(None, max_length=200)
    nda_type: NdaType = NdaType.MUTUAL
    sent_at: str | None = Field(None, max_length=10)
    expires_at: str | None = Field(None, max_length=10)
    document_url: str | None = Field(None, max_length=500)
    notes: str | None = None


class NDAUpdate(BaseModel):
    counterparty_name: str | None = Field(None, max_length=200)
    nda_type: NdaType | None = None
    status: NdaStatus | None = None
    sent_at: str | None = Field(None, max_length=10)
    signed_at: str | None = Field(None, max_length=10)
    expires_at: str | None = Field(None, max_length=10)
    document_url: str | None = Field(None, max_length=500)
    notes: str | None = None


class NDASummary(BaseModel):
    total: int
    by_status: dict[str, int]
    signed_count: int
    pending_count: int
