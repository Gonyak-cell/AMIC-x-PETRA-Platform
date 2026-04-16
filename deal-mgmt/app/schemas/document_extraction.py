"""문서 AI 추출 Pydantic 스키마."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import DocExtractionCategory, ExtractionStatus

# ── 요청 스키마 ──────────────────────────────────────────────


class ExtractionCreateRequest(BaseModel):
    """단일 문서 추출 요청."""

    vdr_document_id: uuid.UUID
    doc_category_hint: DocExtractionCategory | None = None
    target_model: (
        Literal[
            "nda",
            "bid",
            "contract",
            "transaction",
            "engagement",
            "marketing_material",
        ]
        | None
    ) = None
    target_id: uuid.UUID | None = None
    auto_apply_signed_at: bool = False


class BatchExtractionRequest(BaseModel):
    """다건 문서 일괄 추출 요청."""

    vdr_document_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=10)


_MAX_CONFIRMED_DATA_BYTES = 500_000  # 500 KB


class ExtractionConfirmRequest(BaseModel):
    """사용자 검토 확정 요청."""

    confirmed_data: dict  # 사용자가 수정한 추출 결과 JSON
    target_model: Literal["nda", "bid", "contract", "transaction", "engagement", "marketing_material"]
    target_id: uuid.UUID | None = None  # 기존 레코드 업데이트 시
    create_new: bool = False  # True면 신규 레코드 생성

    @field_validator("confirmed_data")
    @classmethod
    def limit_size(cls, v: dict) -> dict:
        """confirmed_data JSON 크기를 제한하여 DB 스토리지 남용을 방지한다."""
        if len(json.dumps(v, ensure_ascii=False)) > _MAX_CONFIRMED_DATA_BYTES:
            raise ValueError("confirmed_data가 500KB를 초과합니다")
        return v


# ── 응답 스키마 ──────────────────────────────────────────────


class ExtractionOut(BaseModel):
    """추출 작업 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    vdr_document_id: uuid.UUID
    doc_category: DocExtractionCategory | None = None
    classification_confidence: float | None = None
    status: ExtractionStatus
    error_message: str | None = None
    extraction_source: Literal["LLM", "RULES_FALLBACK"] = "LLM"
    processing_note: str | None = None
    extracted_data: dict | None = None
    target_model: str | None = None
    target_id: uuid.UUID | None = None
    auto_apply_signed_at: bool = False
    llm_cost_usd: float = 0.0
    reviewed_by_email: str | None = None
    reviewed_at: str | None = None
    created_at: datetime
    updated_at: datetime


class ExtractionListOut(BaseModel):
    """추출 작업 목록 응답."""

    items: list[ExtractionOut]
    total: int
