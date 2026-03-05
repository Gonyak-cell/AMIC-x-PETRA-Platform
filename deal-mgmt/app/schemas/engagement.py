from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EngagementType, WorkingGroupRole


# ── Engagement ──────────────────────────────────────────
class EngagementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    type: EngagementType
    fee_structure: dict | None = None
    signed_at: str | None = None
    expires_at: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class EngagementCreate(BaseModel):
    type: EngagementType
    fee_structure: dict | None = None
    signed_at: str | None = Field(None, max_length=10)
    expires_at: str | None = Field(None, max_length=10)
    notes: str | None = None


class EngagementUpdate(BaseModel):
    type: EngagementType | None = None
    fee_structure: dict | None = None
    signed_at: str | None = Field(None, max_length=10)
    expires_at: str | None = Field(None, max_length=10)
    notes: str | None = None


# ── Working Group Member ────────────────────────────────
class WorkingGroupMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    name: str
    email: str
    organization: str | None = None
    role: WorkingGroupRole
    phone: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WorkingGroupMemberCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    organization: str | None = Field(None, max_length=200)
    role: WorkingGroupRole
    phone: str | None = Field(None, max_length=20)


class WorkingGroupMemberUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    organization: str | None = Field(None, max_length=200)
    role: WorkingGroupRole | None = None
    phone: str | None = Field(None, max_length=20)
    is_active: bool | None = None
