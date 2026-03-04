"""Ralph Loop Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RalphConfigRequest(BaseModel):
    """Ralph Loop 설정 요청."""

    max_iterations_per_section: int = Field(default=3, ge=1, le=5)
    max_cost_usd: float = Field(default=20.0, ge=1.0, le=50.0)
    pass_threshold: float = Field(default=4.0, ge=3.0, le=5.0)


class RalphSessionCreate(BaseModel):
    """Ralph 세션 생성 요청."""

    pass_type: str = Field(description="draft | final")
    checklist_id: str | None = Field(
        default=None, description="Final pass 시 체크리스트 ID"
    )
    config: RalphConfigRequest = Field(default_factory=RalphConfigRequest)


class RalphSessionRead(BaseModel):
    """Ralph 세션 응답."""

    id: str
    deal_id: str
    pass_type: str
    status: str
    checklist_id: str | None = None
    report_version_id: str | None = None
    total_iterations: int = 0
    total_cost_usd: float = 0.0
    final_score: float = 0.0
    section_scores: dict[str, float] | None = None
    critical_flags: list[str] | None = None
    error_message: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class RalphProgressRead(BaseModel):
    """Ralph 진행 상태 응답."""

    session_id: str
    status: str
    total_iterations: int = 0
    total_cost_usd: float = 0.0
    final_score: float = 0.0
    section_scores: dict[str, float] | None = None
    progress: dict[str, Any] | None = None
    critical_flags: list[str] | None = None
