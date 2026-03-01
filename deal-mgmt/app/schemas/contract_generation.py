"""계약서 자동 생성 시스템 — Pydantic 스키마."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ── Template ────────────────────────────────────────────────────────────────


class ContractTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doc_type: str
    name: str
    description: str | None = None
    version: str
    status: str
    created_at: datetime
    updated_at: datetime


class ContractClauseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clause_order: int
    title: str
    content: str
    is_boilerplate: bool
    condition_expression: str | None = None


class TemplateVariableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    variable_key: str
    input_type: str
    question_label: str
    description: str | None = None
    default_value: str | None = None
    is_required: bool
    select_options: dict[str, str] | None = None
    display_order: int
    group_name: str | None = None
    visible_condition: str | None = None


class ContractTemplateDetailOut(BaseModel):
    template: ContractTemplateOut
    clauses: list[ContractClauseOut]
    variables: list[TemplateVariableOut]


# ── Generate ────────────────────────────────────────────────────────────────


class ContractGenerateRequest(BaseModel):
    template_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=300)
    variables: dict[str, Any] = Field(default_factory=dict)
    use_llm_smoothing: bool = Field(default=True)

    @field_validator("variables")
    @classmethod
    def validate_variables_size(cls, v: dict[str, Any]) -> dict[str, Any]:
        """변수 개수와 키/값 크기를 제한한다."""
        if len(v) > 50:
            msg = f"변수는 최대 50개까지 허용됩니다 (현재: {len(v)})"
            raise ValueError(msg)
        for key, val in v.items():
            if len(key) > 100:
                msg = f"변수 키 길이는 100자 이하여야 합니다: {key[:20]}..."
                raise ValueError(msg)
            if isinstance(val, str) and len(val) > 10_000:
                msg = f"변수 값 길이는 10,000자 이하여야 합니다: {key}"
                raise ValueError(msg)
        return v


class GenerationTimingOut(BaseModel):
    """생성 파이프라인 각 단계 소요 시간 (초)."""

    template_lookup: float
    validation: float
    assembly: float
    html_build: float
    llm_smoothing: float
    total: float


class ContractGenerationOut(BaseModel):
    legal_document_id: uuid.UUID
    html: str
    clauses_used: int
    clauses_skipped: int
    llm_smoothed: bool
    llm_cost_usd: float | None = None
    updated_at: datetime
    timing: GenerationTimingOut | None = None


# ── Export ───────────────────────────────────────────────────────────────────


class ContractExportRequest(BaseModel):
    html: str = Field(..., min_length=1, max_length=5_000_000)
    title: str = Field(..., min_length=1, max_length=300)
    legal_document_id: uuid.UUID | None = None


# ── Save HTML ───────────────────────────────────────────────────────────────


class ContractSaveHtmlRequest(BaseModel):
    html: str = Field(..., min_length=1, max_length=5_000_000)
    last_modified_at: str | None = Field(default=None, description="OCC용 — 마지막 수정 시각")


class ContractSaveHtmlOut(BaseModel):
    status: str
    updated_at: datetime
    html: str | None = Field(default=None, description="살균 후 HTML (원본과 다를 경우 동기화용)")
