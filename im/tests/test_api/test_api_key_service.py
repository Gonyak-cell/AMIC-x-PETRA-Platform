"""APIKeyService 테스트 (test_api_key_service.py).

> 마지막 수정: 2026-02-10 19:30:00

API 키 서비스 레이어 비즈니스 로직 검증.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.db.models.api_key import APIKey
from src.api.exceptions import AuthorizationError, NotFoundError
from src.api.services.api_key_service import APIKeyService


def _make_api_key(
    key_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    name: str = "Test Key",
    is_active: bool = True,
) -> MagicMock:
    """테스트 APIKey mock."""
    api_key = MagicMock(spec=APIKey)
    api_key.id = key_id or uuid.uuid4()
    api_key.user_id = user_id or uuid.uuid4()
    api_key.key_hash = "test_hash"
    api_key.name = name
    api_key.is_active = is_active
    api_key.expires_at = None
    api_key.created_at = datetime.now(timezone.utc)
    return api_key


class TestAPIKeyServiceCreate:
    """APIKeyService.create 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_create_api_key_success(self) -> None:
        """API 키 생성 성공 시 (APIKey, raw_key) 반환."""
        user_id = uuid.uuid4()
        mock_session = AsyncMock()
        mock_session.refresh = AsyncMock()

        new_key = _make_api_key(user_id=user_id, name="My Key")

        with patch(
            "src.api.services.api_key_service.generate_api_key",
            return_value=("imgen_raw_key_123", "hashed_key"),
        ):
            service = APIKeyService(mock_session)

            # Mock add to set attributes
            def add_side_effect(key):
                key.id = new_key.id
                key.user_id = new_key.user_id
                key.name = new_key.name
                key.key_hash = "hashed_key"
                key.is_active = True
                key.expires_at = None
                key.created_at = new_key.created_at

            mock_session.add = MagicMock(side_effect=add_side_effect)

            api_key, raw_key = await service.create(
                user_id=user_id,
                name="My Key",
                expires_days=None,
            )

        assert raw_key == "imgen_raw_key_123"
        assert api_key.user_id == user_id
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestAPIKeyServiceListKeys:
    """APIKeyService.list_keys 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_list_keys_returns_items(self) -> None:
        """사용자의 API 키 목록 반환."""
        user_id = uuid.uuid4()
        keys = [_make_api_key(user_id=user_id) for _ in range(2)]

        mock_session = AsyncMock()

        # Count query
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=2)

        # List query
        list_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all = MagicMock(return_value=keys)
        list_result.scalars = MagicMock(return_value=scalars_mock)

        mock_session.execute = AsyncMock(side_effect=[count_result, list_result])

        service = APIKeyService(mock_session)
        items, total = await service.list_keys(user_id)

        assert len(items) == 2
        assert total == 2


class TestAPIKeyServiceRevoke:
    """APIKeyService.revoke 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_revoke_success(self) -> None:
        """API 키 비활성화 성공."""
        user_id = uuid.uuid4()
        api_key = _make_api_key(user_id=user_id, is_active=True)

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=api_key)
        mock_session.execute = AsyncMock(return_value=result_mock)

        service = APIKeyService(mock_session)
        await service.revoke(api_key.id, user_id)

        assert api_key.is_active is False
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_not_found(self) -> None:
        """존재하지 않는 키는 NotFoundError 발생."""
        user_id = uuid.uuid4()
        key_id = uuid.uuid4()

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=result_mock)

        service = APIKeyService(mock_session)
        with pytest.raises(NotFoundError):
            await service.revoke(key_id, user_id)

    @pytest.mark.asyncio
    async def test_revoke_not_owner(self) -> None:
        """본인 소유가 아니면 AuthorizationError 발생."""
        owner_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        api_key = _make_api_key(user_id=owner_id)

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=api_key)
        mock_session.execute = AsyncMock(return_value=result_mock)

        service = APIKeyService(mock_session)
        with pytest.raises(AuthorizationError):
            await service.revoke(api_key.id, other_user_id)
