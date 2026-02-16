"""Company 관련 스키마 (T-I15).

> 마지막 수정: 2026-02-10 23:30:00

기업 데이터 요청/응답 Pydantic v2 스키마를 정의한다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompanyRequest(BaseModel):
    """기업 데이터 요청."""

    corp_code: str = Field(
        min_length=8, max_length=8, description="법인 코드 (8자리 숫자)"
    )

    @field_validator("corp_code")
    @classmethod
    def validate_corp_code(cls, v: str) -> str:
        """corp_code가 8자리 숫자인지 검증한다."""
        if not v.isdigit():
            raise ValueError("corp_code는 8자리 숫자여야 합니다")
        return v


class CompanyResponse(BaseModel):
    """기업 데이터 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    corp_code: str
    corp_name: str
    corp_name_en: str | None
    stock_code: str | None
    industry: str | None
    homepage_url: str | None
    fetch_status: str
    last_fetched_at: datetime | None
    cache_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
