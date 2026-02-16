"""인증 관련 엔드포인트.

> 마지막 수정: 2026-02-10 19:30:00

POST /api/v1/auth/login    — 로그인
POST /api/v1/auth/refresh  — 토큰 갱신
POST /api/v1/auth/logout   — 로그아웃
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_user
from src.api.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from src.api.security.auth import verify_token
from src.api.security.blacklist import blacklist_token
from src.api.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", auto_error=True
)


@router.post(
    "/login",
    summary="로그인",
    description="이메일과 비밀번호로 인증하여 JWT 토큰을 httpOnly 쿠키로 설정.",
)
async def login(
    data: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """이메일/비밀번호 로그인."""
    service = AuthService(session)
    tokens = await service.login(data.email, data.password)

    # Access Token 쿠키 설정
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=15 * 60,  # 15분
    )

    # Refresh Token 쿠키 설정
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,  # 7일
    )

    return {"message": "로그인 성공"}


@router.post(
    "/refresh",
    summary="토큰 갱신",
    description="Refresh 토큰으로 새 Access/Refresh 토큰을 httpOnly 쿠키로 설정.",
)
async def refresh(
    data: RefreshRequest,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """Refresh 토큰으로 새 토큰 발급."""
    service = AuthService(session)
    tokens = service.refresh(data.refresh_token)

    # Access Token 쿠키 설정
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=15 * 60,  # 15분
    )

    # Refresh Token 쿠키 설정
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,  # 7일
    )

    return {"message": "토큰 갱신 성공"}


@router.post(
    "/logout",
    status_code=200,
    summary="로그아웃",
    description="현재 토큰을 블랙리스트에 추가하고 쿠키를 삭제한다.",
)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    token: str = Depends(_oauth2_scheme),
) -> dict[str, str]:
    """현재 토큰 로그아웃 (블랙리스트 추가)."""
    # 쿠키 삭제
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

    payload = verify_token(token, expected_type="access")
    await blacklist_token(payload.jti, payload.exp)
    return {"message": "로그아웃 되었습니다."}
