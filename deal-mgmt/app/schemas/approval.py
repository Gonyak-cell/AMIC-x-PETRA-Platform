from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApprovalStatus, ApprovalType


class ApproverEntry(BaseModel):
    email: str
    role: str
    status: str = "PENDING"
    comment: str | None = None
    decided_at: str | None = None


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    requester_email: str
    approval_type: ApprovalType
    title: str
    description: str | None = None
    status: ApprovalStatus
    approvers: list[dict]
    deadline: str | None = None
    related_entity_type: str | None = None
    related_entity_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class ApprovalCreate(BaseModel):
    approval_type: ApprovalType
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    approvers: list[ApproverEntry] = Field(..., min_length=1)
    deadline: str | None = Field(None, max_length=10)
    related_entity_type: str | None = Field(None, max_length=50)
    related_entity_id: uuid.UUID | None = None


class ApprovalDecision(BaseModel):
    email: str
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    comment: str | None = None


class ApprovalListResponse(BaseModel):
    items: list[ApprovalOut]
    total: int


class ApprovalSummary(BaseModel):
    total: int
    pending: int
    approved: int
    rejected: int
