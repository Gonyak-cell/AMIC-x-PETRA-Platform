"""IM Ralph Loop API 스키마."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IMRalphSessionOut(BaseModel):
    """Ralph Loop 세션 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    pass_number: int
    doc_type: str
    status: str
    total_iterations: int
    total_cost_usd: float
    final_score: float
    section_scores: dict | None = None
    output_path: str | None = None
    error_message: str | None = None
    critical_flags: list | None = None
    learned_patterns: dict | None = None
    created_by_email: str | None = None
    created_at: datetime
    updated_at: datetime


class IMRalphProgressOut(BaseModel):
    """Ralph Loop 실시간 프로그레스."""

    session_id: UUID
    status: str
    current_section: str | None = None
    current_iteration: int = 0
    total_sections: int = 0
    scores: dict = {}
    gate_results: list[dict] = []


class IMRalphTriggerRequest(BaseModel):
    """수동 Ralph Loop 실행 요청."""

    document_id: UUID
    pass_number: int = 1


class IMRalphTriggerResponse(BaseModel):
    """Ralph Loop 실행 응답."""

    session_id: UUID
    celery_task_id: str
    message: str
