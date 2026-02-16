"""공통 스키마 — 페이지네이션, 에러 응답.

> 마지막 수정: 2026-02-10 23:30:00

모든 라우트에서 공유하는 범용 스키마를 정의한다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """페이지네이션 파라미터."""

    offset: int = Field(default=0, ge=0, description="시작 오프셋")
    limit: int = Field(default=20, ge=1, le=100, description="페이지 크기")


class ErrorResponse(BaseModel):
    """에러 응답 스키마."""

    error: str = Field(description="에러 메시지")
    details: dict[str, Any] = Field(default_factory=dict, description="상세 정보")
