"""API 키 관리 테스트 (T-I08).

> 마지막 수정: 2026-02-10 17:39:59
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.exceptions import AuthenticationError
from src.api.security.api_keys import (
    _KEY_PREFIX,
    generate_api_key,
    verify_api_key,
)


class TestGenerateApiKey:
    """API 키 생성 테스트."""

    def test_key_has_prefix(self) -> None:
        """생성된 키가 'imgen_' prefix를 포함한다."""
        raw_key, _ = generate_api_key()
        assert raw_key.startswith(_KEY_PREFIX)

    def test_key_length(self) -> None:
        """생성된 키의 길이가 올바르다 (6 + 64 = 70자)."""
        raw_key, _ = generate_api_key()
        assert len(raw_key) == len(_KEY_PREFIX) + 64  # 32 bytes = 64 hex chars

    def test_hash_consistency(self) -> None:
        """같은 키에 대해 해시가 일관적이다."""
        raw_key, key_hash = generate_api_key()
        expected_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        assert key_hash == expected_hash

    def test_unique_keys(self) -> None:
        """매번 고유한 키를 생성한다."""
        keys = {generate_api_key()[0] for _ in range(10)}
        assert len(keys) == 10


class TestVerifyApiKey:
    """API 키 검증 테스트."""

    @pytest.fixture
    def mock_user(self) -> MagicMock:
        """Mock User 객체."""
        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.is_active = True
        return user

    @pytest.fixture
    def mock_api_key(self, mock_user: MagicMock) -> MagicMock:
        """Mock APIKey 객체."""
        api_key = MagicMock()
        api_key.is_active = True
        api_key.expires_at = None
        api_key.last_used_at = None
        api_key.user = mock_user
        return api_key

    @pytest.mark.asyncio
    async def test_valid_key_returns_user(
        self, mock_api_key: MagicMock, mock_user: MagicMock
    ) -> None:
        """유효한 키로 User를 반환한다."""
        raw_key, key_hash = generate_api_key()
        mock_api_key.key_hash = key_hash

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_api_key
        session.execute.return_value = result

        user = await verify_api_key(raw_key, session)

        assert user is mock_user
        assert mock_api_key.last_used_at is not None

    @pytest.mark.asyncio
    async def test_nonexistent_key_rejected(self) -> None:
        """존재하지 않는 키를 거부한다."""
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute.return_value = result

        with pytest.raises(AuthenticationError, match="유효하지 않은"):
            await verify_api_key("imgen_fake_key_1234", session)

    @pytest.mark.asyncio
    async def test_inactive_key_rejected(self, mock_api_key: MagicMock) -> None:
        """비활성 키를 거부한다."""
        raw_key, key_hash = generate_api_key()
        mock_api_key.key_hash = key_hash
        mock_api_key.is_active = False

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_api_key
        session.execute.return_value = result

        with pytest.raises(AuthenticationError, match="비활성"):
            await verify_api_key(raw_key, session)

    @pytest.mark.asyncio
    async def test_expired_key_rejected(self, mock_api_key: MagicMock) -> None:
        """만료된 키를 거부한다."""
        raw_key, key_hash = generate_api_key()
        mock_api_key.key_hash = key_hash
        mock_api_key.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_api_key
        session.execute.return_value = result

        with pytest.raises(AuthenticationError, match="만료"):
            await verify_api_key(raw_key, session)

    @pytest.mark.asyncio
    async def test_last_used_at_updated(
        self, mock_api_key: MagicMock, mock_user: MagicMock
    ) -> None:
        """검증 성공 시 last_used_at이 갱신된다."""
        raw_key, key_hash = generate_api_key()
        mock_api_key.key_hash = key_hash
        mock_api_key.last_used_at = None

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_api_key
        session.execute.return_value = result

        await verify_api_key(raw_key, session)

        assert mock_api_key.last_used_at is not None
