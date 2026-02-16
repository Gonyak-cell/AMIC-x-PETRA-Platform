"""API 키 관리 스키마.

> 마지막 수정: 2026-02-10 19:30:00

API 키 생성 및 조회 Pydantic v2 스키마를 정의한다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIKeyCreateRequest(BaseModel):
    """API 키 생성 요청."""

    name: str = Field(min_length=1, max_length=100, description="키 이름/용도")
    expires_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="만료 일수 (없으면 영구)",
    )


class APIKeyCreateResponse(BaseModel):
    """API 키 생성 응답 (raw key 포함, 이 응답에서만 노출)."""

    id: UUID
    name: str
    key: str = Field(description="평문 API 키 (이 응답에서만 제공)")
    expires_at: datetime | None
    created_at: datetime


class APIKeyResponse(BaseModel):
    """API 키 조회 응답 (raw key 제외)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    is_active: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class APIKeyListResponse(BaseModel):
    """API 키 목록 응답."""

    items: list[APIKeyResponse]
    total: int
