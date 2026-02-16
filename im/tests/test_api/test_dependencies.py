"""FastAPI 의존성 테스트 (T-I10).

> 마지막 수정: 2026-02-10 17:39:59
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.config import APIConfig
from src.api.exceptions import AuthenticationError
from src.api.security.auth import TokenPayload, create_access_token


@pytest.fixture
def hs256_config() -> APIConfig:
    """HS256 폴백용 테스트 설정."""
    return APIConfig(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost:5434/imgen_test",
        redis_url="redis://localhost:6380/15",
        redis_result_backend="redis://localhost:6380/14",
        jwt_secret_key="test-secret-key-for-jwt-tests-min32",
        jwt_algorithm="HS256",
    )


@pytest.fixture
def mock_user() -> MagicMock:
    """Mock User 객체."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.role = "USER"
    user.is_active = True
    return user


@pytest.fixture
def mock_session(mock_user: MagicMock) -> AsyncMock:
    """Mock 비동기 DB 세션."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_user
    session.execute.return_value = result
    return session


class TestGetCurrentUser:
    """get_current_user 테스트."""

    @pytest.mark.asyncio
    async def test_jwt_auth_success(
        self, hs256_config: APIConfig, mock_user: MagicMock, mock_session: AsyncMock
    ) -> None:
        """JWT 인증 정상 흐름."""
        from src.api.dependencies import get_current_user

        token = create_access_token(
            str(mock_user.id), "USER", config=hs256_config
        )

        with patch("src.api.dependencies.verify_token") as mock_verify, \
             patch("src.api.dependencies.is_blacklisted", new_callable=AsyncMock, return_value=False):
            mock_verify.return_value = TokenPayload(
                sub=str(mock_user.id),
                role="USER",
                exp=MagicMock(),
                iat=MagicMock(),
                jti="test-jti",
                token_type="access",
            )
            user = await get_current_user(
                token=token, api_key=None, session=mock_session
            )

        assert user is mock_user

    @pytest.mark.asyncio
    async def test_api_key_auth_success(
        self, mock_user: MagicMock, mock_session: AsyncMock
    ) -> None:
        """API Key 인증 정상 흐름."""
        from src.api.dependencies import get_current_user

        with patch("src.api.dependencies.verify_api_key") as mock_verify_key:
            mock_verify_key.return_value = mock_user
            user = await get_current_user(
                token=None, api_key="imgen_test_key", session=mock_session
            )

        assert user is mock_user
        mock_verify_key.assert_called_once_with("imgen_test_key", mock_session)

    @pytest.mark.asyncio
    async def test_jwt_takes_priority(
        self, hs256_config: APIConfig, mock_user: MagicMock, mock_session: AsyncMock
    ) -> None:
        """JWT와 API Key 둘 다 있으면 JWT를 우선한다."""
        from src.api.dependencies import get_current_user

        with patch("src.api.dependencies.verify_token") as mock_verify_jwt, \
             patch("src.api.dependencies.verify_api_key") as mock_verify_key, \
             patch("src.api.dependencies.is_blacklisted", new_callable=AsyncMock, return_value=False):
            mock_verify_jwt.return_value = TokenPayload(
                sub=str(mock_user.id),
                role="USER",
                exp=MagicMock(),
                iat=MagicMock(),
                jti="test-jti",
                token_type="access",
            )
            await get_current_user(
                token="some-jwt", api_key="imgen_key", session=mock_session
            )

        mock_verify_jwt.assert_called_once()
        mock_verify_key.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_credentials_raises_401(self) -> None:
        """인증 정보가 없으면 401."""
        from src.api.dependencies import get_current_user

        session = AsyncMock()

        with pytest.raises(AuthenticationError, match="인증 정보가 제공되지"):
            await get_current_user(token=None, api_key=None, session=session)

    @pytest.mark.asyncio
    async def test_invalid_jwt_raises_401(self, mock_session: AsyncMock) -> None:
        """잘못된 JWT → 401."""
        from src.api.dependencies import get_current_user

        with patch("src.api.dependencies.verify_token") as mock_verify:
            mock_verify.side_effect = AuthenticationError("유효하지 않은 토큰")
            with pytest.raises(AuthenticationError):
                await get_current_user(
                    token="invalid-jwt", api_key=None, session=mock_session
                )

    @pytest.mark.asyncio
    async def test_invalid_api_key_raises_401(self, mock_session: AsyncMock) -> None:
        """잘못된 API Key → 401."""
        from src.api.dependencies import get_current_user

        with patch("src.api.dependencies.verify_api_key") as mock_verify:
            mock_verify.side_effect = AuthenticationError("유효하지 않은 API 키")
            with pytest.raises(AuthenticationError):
                await get_current_user(
                    token=None, api_key="invalid-key", session=mock_session
                )

    @pytest.mark.asyncio
    async def test_user_not_found_raises_401(self, mock_session: AsyncMock) -> None:
        """DB에 없는 사용자 → 401."""
        from src.api.dependencies import get_current_user

        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result

        with patch("src.api.dependencies.verify_token") as mock_verify, \
             patch("src.api.dependencies.is_blacklisted", new_callable=AsyncMock, return_value=False):
            mock_verify.return_value = TokenPayload(
                sub=str(uuid.uuid4()),
                role="USER",
                exp=MagicMock(),
                iat=MagicMock(),
                jti="test-jti",
                token_type="access",
            )
            with pytest.raises(AuthenticationError, match="찾을 수 없습니다"):
                await get_current_user(
                    token="valid-jwt", api_key=None, session=mock_session
                )


class TestGetCurrentActiveUser:
    """get_current_active_user 테스트."""

    @pytest.mark.asyncio
    async def test_active_user_passes(self, mock_user: MagicMock) -> None:
        """활성 사용자는 통과한다."""
        from src.api.dependencies import get_current_active_user

        mock_user.is_active = True
        result = await get_current_active_user(user=mock_user)
        assert result is mock_user

    @pytest.mark.asyncio
    async def test_inactive_user_rejected(self, mock_user: MagicMock) -> None:
        """비활성 사용자는 거부한다."""
        from src.api.dependencies import get_current_active_user

        mock_user.is_active = False
        with pytest.raises(AuthenticationError, match="비활성 계정"):
            await get_current_active_user(user=mock_user)
