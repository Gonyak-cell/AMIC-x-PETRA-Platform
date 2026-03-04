"""인증 서비스 레이어.

> 마지막 수정: 2026-02-10 19:30:00

로그인, 토큰 갱신, 로그아웃 비즈니스 로직.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.user import User
from src.api.exceptions import AuthenticationError
from src.api.security.auth import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from src.api.security.blacklist import blacklist_token
from src.api.security.password import verify_password


class AuthService:
    """인증 관련 비즈니스 로직."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def login(
        self,
        email: str,
        password: str,
    ) -> dict[str, str]:
        """이메일/비밀번호로 로그인하고 토큰을 반환한다.

        Args:
            email: 이메일 주소.
            password: 평문 비밀번호.

        Returns:
            {"access_token": ..., "refresh_token": ...} 딕셔너리.

        Raises:
            AuthenticationError: 인증 실패.
        """
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            raise AuthenticationError(
                message="이메일 또는 비밀번호가 올바르지 않습니다.",
                details={"reason": "invalid_credentials"},
            )

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError(
                message="이메일 또는 비밀번호가 올바르지 않습니다.",
                details={"reason": "invalid_credentials"},
            )

        if not user.is_active:
            raise AuthenticationError(
                message="비활성 계정입니다.",
                details={"reason": "inactive_account"},
            )

        access_token = create_access_token(str(user.id), user.role)
        refresh_token = create_refresh_token(str(user.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    def refresh(self, refresh_token: str) -> dict[str, str]:
        """Refresh 토큰으로 새 토큰 쌍을 발급한다.

        Args:
            refresh_token: Refresh JWT 토큰.

        Returns:
            {"access_token": ..., "refresh_token": ...} 딕셔너리.

        Raises:
            AuthenticationError: 토큰이 유효하지 않은 경우.
        """
        payload = verify_token(refresh_token, expected_type="refresh")
        access_token = create_access_token(payload.sub, payload.role or "USER")
        new_refresh_token = create_refresh_token(payload.sub)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
        }

    async def logout(self, payload: TokenPayload) -> None:
        """토큰을 블랙리스트에 추가하여 로그아웃한다.

        Args:
            payload: 현재 액세스 토큰 페이로드.
        """
        await blacklist_token(payload.jti, payload.exp)
