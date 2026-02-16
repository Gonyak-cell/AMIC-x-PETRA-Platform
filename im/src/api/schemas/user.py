"""사용자 관리 스키마.

> 마지막 수정: 2026-02-10 19:30:00

사용자 생성, 프로필, 관리 Pydantic v2 스키마를 정의한다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.api.security.rbac import UserRole

_VALID_ROLES = {r.value for r in UserRole}


class UserResponse(BaseModel):
    """사용자 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserCreateRequest(BaseModel):
    """사용자 생성 요청 (ADMIN 전용)."""

    email: EmailStr = Field(description="이메일 주소")
    password: str = Field(min_length=8, description="비밀번호 (최소 8자)")
    full_name: str = Field(min_length=1, max_length=100, description="이름")
    role: str = Field(default="USER", description="역할 (USER/MANAGER/ADMIN)")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """역할이 유효한 값인지 검증한다."""
        if v not in _VALID_ROLES:
            raise ValueError(f"role은 {_VALID_ROLES} 중 하나여야 합니다")
        return v


class UserUpdateRequest(BaseModel):
    """사용자 자신의 프로필 수정 요청."""

    full_name: str | None = Field(default=None, max_length=100)
    current_password: str | None = Field(
        default=None, description="비밀번호 변경 시 현재 비밀번호"
    )
    new_password: str | None = Field(
        default=None, min_length=8, description="새 비밀번호"
    )


class AdminUserUpdateRequest(BaseModel):
    """관리자 사용자 수정 요청."""

    role: str | None = Field(default=None, description="USER/MANAGER/ADMIN")
    is_active: bool | None = Field(default=None, description="활성 상태")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        """역할이 유효한 값인지 검증한다."""
        if v is not None and v not in _VALID_ROLES:
            raise ValueError(f"role은 {_VALID_ROLES} 중 하나여야 합니다")
        return v


class UserListResponse(BaseModel):
    """사용자 목록 응답."""

    items: list[UserResponse]
    total: int
    offset: int
    limit: int
