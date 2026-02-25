"""녹음 변환 — 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TranscriptionJobOut(BaseModel):
    """변환 작업 상태/결과 응답."""

    id: uuid.UUID
    transaction_id: uuid.UUID
    title: str
    meeting_date: str
    meeting_phase: str
    buyer_id: uuid.UUID | None = None
    status: str
    transcript: str | None = None
    minutes_json: dict | None = None
    meeting_log_id: uuid.UUID | None = None
    stt_cost_krw: float = 0.0
    llm_cost_usd: float = 0.0
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TranscriptionApproval(BaseModel):
    """사용자가 결과를 검토/편집 후 확정."""

    minutes: str = Field(..., min_length=1, description="확정 회의록 텍스트")
    summary: str | None = Field(default=None, description="회의 요약")
    action_items: list[ActionItemInput] | None = None
    condition_match: str | None = None
    condition_notes: str | None = None
    buyer_reaction: str | None = None


class ActionItemInput(BaseModel):
    """액션아이템 입력."""

    title: str = Field(..., min_length=1)
    description: str | None = None
    assignee_name: str | None = None
    assignee_email: str | None = None
    due_date: str | None = None
    priority: str = "MEDIUM"


# Forward reference 해결
TranscriptionApproval.model_rebuild()
