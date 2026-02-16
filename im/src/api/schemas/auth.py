"""인증 관련 스키마.

> 마지막 수정: 2026-02-10 19:30:00

로그인, 토큰 관리 Pydantic v2 스키마를 정의한다.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """로그인 요청."""

    email: EmailStr = Field(description="이메일 주소")
    password: str = Field(description="비밀번호")


class TokenResponse(BaseModel):
    """토큰 응답."""

    access_token: str = Field(description="Access JWT 토큰")
    refresh_token: str = Field(description="Refresh JWT 토큰")
    token_type: str = Field(default="bearer", description="토큰 타입")


class RefreshRequest(BaseModel):
    """토큰 갱신 요청."""

    refresh_token: str = Field(description="Refresh JWT 토큰")
