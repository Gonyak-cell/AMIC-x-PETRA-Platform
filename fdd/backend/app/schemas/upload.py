import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.upload import IngestionStatus, UploadType, ValidationSeverity

# ── Upload File ──────────────────────────────────────────


class UploadFileRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    original_filename: str
    file_hash: str
    file_size_bytes: int
    detected_type: UploadType | None
    confirmed_type: UploadType | None
    detection_confidence: Decimal | None
    status: IngestionStatus
    total_rows: int | None
    rows_processed: int | None
    sheet_name: str | None
    error_message: str | None
    validation_summary: dict[str, Any] | None
    uploaded_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadFileConfirmType(BaseModel):
    confirmed_type: UploadType


class UploadFileIngestOptions(BaseModel):
    """TB 파일 인제스트 시 선택적 파라미터."""

    period_date: date | None = Field(
        default=None,
        description="TB 파일의 기간 날짜 (사용자 지정). 미지정 시 자동 탐지.",
    )


# ── Validation Error ─────────────────────────────────────


class ValidationErrorRead(BaseModel):
    id: uuid.UUID
    severity: ValidationSeverity
    error_code: str
    field_name: str | None
    row_number: int | None
    message: str
    suggestion: str | None

    model_config = {"from_attributes": True}


# ── Upload Detail (includes validation errors) ──────────


class UploadFileDetailRead(UploadFileRead):
    validation_errors: list[ValidationErrorRead] = Field(default_factory=list)
