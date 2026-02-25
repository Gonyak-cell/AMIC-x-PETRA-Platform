"""협상 이견 스키마 — AI 조항 수정 제안 포함."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NegotiationIssuePriority, NegotiationIssueStatus


class NegotiationIssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    meeting_id: uuid.UUID | None = None
    title: str
    clause_reference: str | None = None
    category: str | None = None
    our_position: str | None = None
    counterpart_position: str | None = None
    legal_review: str | None = None
    ai_suggestion: str | None = None
    ai_suggestion_rationale: str | None = None
    status: NegotiationIssueStatus
    priority: NegotiationIssuePriority
    resolution: str | None = None
    resolved_at: str | None = None
    created_by_email: str | None = None
    created_at: datetime
    updated_at: datetime


class NegotiationIssueCreate(BaseModel):
    meeting_id: uuid.UUID | None = None
    title: str = Field(..., min_length=1, max_length=300)
    clause_reference: str | None = None
    category: str | None = None
    our_position: str | None = None
    counterpart_position: str | None = None
    legal_review: str | None = None
    status: NegotiationIssueStatus = NegotiationIssueStatus.OPEN
    priority: NegotiationIssuePriority = NegotiationIssuePriority.MEDIUM


class NegotiationIssueUpdate(BaseModel):
    meeting_id: uuid.UUID | None = None
    title: str | None = Field(None, min_length=1, max_length=300)
    clause_reference: str | None = None
    category: str | None = None
    our_position: str | None = None
    counterpart_position: str | None = None
    legal_review: str | None = None
    status: NegotiationIssueStatus | None = None
    priority: NegotiationIssuePriority | None = None
    resolution: str | None = None
    resolved_at: str | None = None


class NegotiationIssueListResponse(BaseModel):
    items: list[NegotiationIssueOut]
    total: int


class AIClauseSuggestionResponse(BaseModel):
    suggested_text: str
    rationale: str
    confidence: float
