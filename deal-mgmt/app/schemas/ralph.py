"""Ralph Loop API 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── 요청 스키마 ───────────────────────────────────────────────────────────────


class RalphSessionCreate(BaseModel):
    """Ralph Loop 세션 생성 요청."""

    doc_type: str = Field(..., description="문서 유형: ldd_full, ldd_redflag, tm, dm, im")
    max_iterations_per_section: int = Field(3, ge=1, le=10)
    max_cost_usd: float = Field(20.0, ge=1.0, le=100.0)
    pass_threshold: float = Field(4.0, ge=1.0, le=5.0)

    # LDD 전용 (실사자료 자동 분석)
    target_company: str | None = Field(None, max_length=200)
    dd_period: str | None = Field(None, max_length=100)
    law_firm: str | None = Field(None, max_length=200)
    prepared_by: str | None = Field(None, max_length=200)

    # 실사자료 경로 (LDD 자동 분석용)
    source_dir: str | None = Field(None, max_length=500, description="실사자료 폴더 경로")

    # PPTX 전용 (TM/DM/IM)
    project_code: str | None = Field(None, max_length=100)
    memo_type: str | None = Field(None, description="TM, DM, IM")


class RalphSessionUpdate(BaseModel):
    """Ralph Loop 세션 상태 업데이트 (내부용)."""

    status: str | None = None
    total_iterations: int | None = None
    total_cost_usd: float | None = None
    final_score: float | None = None
    error_message: str | None = None


# ── 응답 스키마 ───────────────────────────────────────────────────────────────


class DimensionScoreOut(BaseModel):
    """평가 차원별 점수."""

    name: str
    label: str
    score: float
    weight: float
    feedback: str = ""


class GateResultOut(BaseModel):
    """품질 게이트 평가 결과."""

    gate_name: str
    verdict: str
    weighted_score: float
    dimensions: list[DimensionScoreOut] = []
    issues: list[str] = []
    suggestions: list[str] = []
    critical_flags: list[str] = []
    cost_usd: float = 0.0
    duration_ms: int = 0


class IterationRecordOut(BaseModel):
    """단일 반복의 기록."""

    iteration: int
    section_id: str
    timestamp: str
    gate_results: list[dict] = []
    weighted_score: float = 0.0
    passed: bool = False
    cost_usd: float = 0.0


class RalphSessionOut(BaseModel):
    """Ralph Loop 세션 응답."""

    id: uuid.UUID
    transaction_id: uuid.UUID | None
    doc_type: str
    status: str
    total_iterations: int
    total_cost_usd: float
    final_score: float
    section_scores: dict | None
    output_file_name: str | None
    output_file_size: int | None
    error_message: str | None
    critical_flags: list | None
    created_by_email: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RalphProgressOut(BaseModel):
    """Ralph Loop 진행 상황 (실시간 폴링용)."""

    session_id: uuid.UUID
    status: str
    total_iterations: int
    total_cost_usd: float
    passed_sections: list[str] = []
    current_section: str | None = None
    section_scores: dict = {}
    latest_gate_results: list[GateResultOut] = []
