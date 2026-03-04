"""AuthService 테스트 (test_auth_service.py).

> 마지막 수정: 2026-02-10 19:30:00

인증 서비스 레이어 비즈니스 로직 검증.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.db.models.user import User
from src.api.exceptions import AuthenticationError
from src.api.services.auth_service import AuthService


def _make_user(
    email: str = "test@example.com",
    password_hash: str = "hashed_password",
    is_active: bool = True,
) -> MagicMock:
    """테스트 User mock."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = email
    user.hashed_password = password_hash
    user.role = "USER"
    user.is_active = is_active
    return user


class TestAuthServiceLogin:
    """AuthService.login 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_login_success(self) -> None:
        """올바른 이메일/비밀번호로 로그인 성공."""
        user = _make_user()

        # Mock DB session
        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=user)
        mock_session.execute = AsyncMock(return_value=result_mock)

        with (
            patch(
                "src.api.services.auth_service.verify_password",
                return_value=True,
            ) as mock_verify,
            patch(
                "src.api.services.auth_service.create_access_token",
                return_value="access_token_123",
            ),
            patch(
                "src.api.services.auth_service.create_refresh_token",
                return_value="refresh_token_123",
            ),
        ):
            service = AuthService(mock_session)
            tokens = await service.login("test@example.com", "plain_password")

        assert tokens["access_token"] == "access_token_123"
        assert tokens["refresh_token"] == "refresh_token_123"
        mock_verify.assert_called_once_with("plain_password", user.hashed_password)

    @pytest.mark.asyncio
    async def test_login_wrong_password(self) -> None:
        """잘못된 비밀번호로 AuthenticationError 발생."""
        user = _make_user()

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=user)
        mock_session.execute = AsyncMock(return_value=result_mock)

        with patch(
            "src.api.services.auth_service.verify_password",
            return_value=False,
        ):
            service = AuthService(mock_session)
            with pytest.raises(AuthenticationError) as exc_info:
                await service.login("test@example.com", "wrong_password")

        assert "비밀번호" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_login_user_not_found(self) -> None:
        """존재하지 않는 이메일로 AuthenticationError 발생."""
        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=result_mock)

        service = AuthService(mock_session)
        with pytest.raises(AuthenticationError) as exc_info:
            await service.login("nonexistent@example.com", "password")

        assert (
            "이메일" in exc_info.value.message or "비밀번호" in exc_info.value.message
        )

    @pytest.mark.asyncio
    async def test_login_inactive_user(self) -> None:
        """비활성 사용자는 AuthenticationError 발생."""
        user = _make_user(is_active=False)

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=user)
        mock_session.execute = AsyncMock(return_value=result_mock)

        with patch(
            "src.api.services.auth_service.verify_password",
            return_value=True,
        ):
            service = AuthService(mock_session)
            with pytest.raises(AuthenticationError) as exc_info:
                await service.login("test@example.com", "password")

        assert "비활성" in exc_info.value.message


class TestAuthServiceRefresh:
    """AuthService.refresh 메서드 테스트."""

    def test_refresh_success(self) -> None:
        """유효한 refresh 토큰으로 새 토큰 발급."""
        from src.api.security.auth import TokenPayload

        mock_payload = TokenPayload(
            sub=str(uuid.uuid4()),
            role="USER",
            exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc),
            jti="jti-123",
            token_type="refresh",
        )

        mock_session = AsyncMock()

        with (
            patch(
                "src.api.services.auth_service.verify_token",
                return_value=mock_payload,
            ),
            patch(
                "src.api.services.auth_service.create_access_token",
                return_value="new_access_token",
            ),
            patch(
                "src.api.services.auth_service.create_refresh_token",
                return_value="new_refresh_token",
            ),
        ):
            service = AuthService(mock_session)
            tokens = service.refresh("old_refresh_token")

        assert tokens["access_token"] == "new_access_token"
        assert tokens["refresh_token"] == "new_refresh_token"


class TestAuthServiceLogout:
    """AuthService.logout 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_logout_calls_blacklist(self) -> None:
        """로그아웃 시 blacklist_token 호출."""
        from src.api.security.auth import TokenPayload

        mock_payload = TokenPayload(
            sub=str(uuid.uuid4()),
            role="USER",
            exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc),
            jti="jti-to-blacklist",
            token_type="access",
        )

        mock_session = AsyncMock()

        with patch(
            "src.api.services.auth_service.blacklist_token",
            new_callable=AsyncMock,
        ) as mock_blacklist:
            service = AuthService(mock_session)
            await service.logout(mock_payload)

        mock_blacklist.assert_called_once_with(
            mock_payload.jti,
            mock_payload.exp,
        )
