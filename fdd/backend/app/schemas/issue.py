"""이슈 관련 Pydantic 스키마 — Sprint 6."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.issue import IssueCategory, IssueSeverity, IssueStatus

# ── Issue Create/Update ──────────────────────────────────


class IssueCreate(BaseModel):
    """수동 이슈 생성 요청."""

    category: IssueCategory
    severity: IssueSeverity
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    source_type: str | None = None
    source_id: str | None = None
    source_detail: dict[str, Any] | None = None
    detection_method: str = "manual"


class IssueUpdate(BaseModel):
    """이슈 상태 변경 요청."""

    status: IssueStatus
    resolution_note: str | None = None
    resolved_by: str | None = None


# ── Issue Read ────────────────────────────────────────────


class IssueRead(BaseModel):
    """이슈 조회 응답."""

    id: uuid.UUID
    deal_id: uuid.UUID
    snapshot_id: uuid.UUID | None
    category: IssueCategory
    severity: IssueSeverity
    status: IssueStatus
    title: str
    description: str
    risk_score: Decimal | None
    source_type: str | None
    source_id: str | None
    source_detail: dict[str, Any] | None
    detection_method: str
    detection_factors: list[dict] | None
    engine_version: str | None
    resolution_note: str | None
    resolved_by: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Issue List Response ────────────────────────────────────


class IssueListResponse(BaseModel):
    """이슈 목록 응답 (페이지네이션)."""

    items: list[IssueRead]
    total: int
    limit: int
    offset: int


# ── Issue Summary ──────────────────────────────────────────


class IssueSummary(BaseModel):
    """이슈 요약 통계."""

    total: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    by_category: dict[str, int]


# ── Anomaly Detection ──────────────────────────────────────


class AnomalyDetectionRequest(BaseModel):
    """이상치 탐지 실행 요청."""

    snapshot_id: uuid.UUID | None = None
    threshold: Decimal = Field(
        default=Decimal("50.0"),
        ge=Decimal("0"),
        le=Decimal("100"),
        description="이상치 판정 임계값 (0-100)",
    )


class AnomalyDetectionResponse(BaseModel):
    """이상치 탐지 실행 응답."""

    detected_count: int = Field(description="탐지된 이상치 수")
    issues_created: int = Field(description="생성된 이슈 수")
    engine_version: str
    threshold_used: Decimal
