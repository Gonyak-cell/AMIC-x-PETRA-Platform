"""JWT 블랙리스트 관리 테스트 (test_blacklist.py).

> 마지막 수정: 2026-02-10 19:30:00

blacklist_token, is_blacklisted 함수 검증 (Redis mock 사용).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBlacklistToken:
    """blacklist_token 함수 테스트."""

    @pytest.mark.asyncio
    async def test_blacklist_token_sets_key(self) -> None:
        """토큰을 블랙리스트에 추가 시 redis.setex 호출."""
        from src.api.security.blacklist import blacklist_token

        jti = "test-jti-123"
        exp = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_redis = AsyncMock()
        with patch(
            "src.api.security.blacklist._get_redis",
            return_value=mock_redis,
        ):
            await blacklist_token(jti, exp)

        # setex 호출 확인
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == f"blacklist:jti:{jti}"
        assert isinstance(call_args[1], int)  # TTL seconds
        assert call_args[1] > 0
        assert call_args[2] == "1"
        mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_blacklist_expired_token_skips(self) -> None:
        """이미 만료된 토큰은 redis에 추가하지 않는다."""
        from src.api.security.blacklist import blacklist_token

        jti = "expired-jti"
        exp = datetime.now(timezone.utc) - timedelta(hours=1)

        mock_redis = AsyncMock()
        with patch(
            "src.api.security.blacklist._get_redis",
            return_value=mock_redis,
        ):
            await blacklist_token(jti, exp)

        # setex 호출되지 않음
        mock_redis.setex.assert_not_called()


class TestIsBlacklisted:
    """is_blacklisted 함수 테스트."""

    @pytest.mark.asyncio
    async def test_is_blacklisted_returns_true(self) -> None:
        """redis.exists가 1 반환 시 True."""
        from src.api.security.blacklist import is_blacklisted

        jti = "blacklisted-jti"

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)

        with patch(
            "src.api.security.blacklist._get_redis",
            return_value=mock_redis,
        ):
            result = await is_blacklisted(jti)

        assert result is True
        mock_redis.exists.assert_called_once_with(f"blacklist:jti:{jti}")
        mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_blacklisted_returns_false(self) -> None:
        """redis.exists가 0 반환 시 False."""
        from src.api.security.blacklist import is_blacklisted

        jti = "not-blacklisted-jti"

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)

        with patch(
            "src.api.security.blacklist._get_redis",
            return_value=mock_redis,
        ):
            result = await is_blacklisted(jti)

        assert result is False
        mock_redis.exists.assert_called_once_with(f"blacklist:jti:{jti}")
        mock_redis.aclose.assert_called_once()
