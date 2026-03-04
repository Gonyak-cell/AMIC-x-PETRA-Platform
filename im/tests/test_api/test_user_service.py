"""UserService 테스트 (test_user_service.py).

> 마지막 수정: 2026-02-10 19:30:00

사용자 서비스 레이어 비즈니스 로직 검증.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.db.models.user import User
from src.api.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
)
from src.api.schemas.user import (
    AdminUserUpdateRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from src.api.services.user_service import UserService


def _make_user(
    user_id: uuid.UUID | None = None,
    email: str = "test@example.com",
    full_name: str = "Test User",
    role: str = "USER",
    is_active: bool = True,
) -> MagicMock:
    """테스트 User mock."""
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.email = email
    user.hashed_password = "hashed_password"
    user.full_name = full_name
    user.role = role
    user.is_active = is_active
    return user


class TestUserServiceCreateUser:
    """UserService.create_user 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_create_user_success(self) -> None:
        """사용자 생성 성공."""
        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=result_mock)

        new_user = _make_user(email="new@example.com")
        mock_session.refresh = AsyncMock()

        with patch(
            "src.api.services.user_service.hash_password",
            return_value="hashed_new_password",
        ):
            service = UserService(mock_session)
            data = UserCreateRequest(
                email="new@example.com",
                password="password123",
                full_name="New User",
                role="USER",
            )

            # Mock add to return the user
            def add_side_effect(user):
                user.id = new_user.id
                user.email = new_user.email
                user.full_name = new_user.full_name
                user.role = new_user.role

            mock_session.add = MagicMock(side_effect=add_side_effect)

            # Refresh should populate the user
            async def refresh_side_effect(user):
                pass

            mock_session.refresh = AsyncMock(side_effect=refresh_side_effect)

            user = await service.create_user(data)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        assert user.email == "new@example.com"

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self) -> None:
        """이메일 중복 시 ConflictError 발생."""
        existing_user = _make_user()

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=existing_user)
        mock_session.execute = AsyncMock(return_value=result_mock)

        service = UserService(mock_session)
        data = UserCreateRequest(
            email="test@example.com",
            password="password123",
            full_name="Test User",
            role="USER",
        )

        with pytest.raises(ConflictError):
            await service.create_user(data)


class TestUserServiceGetById:
    """UserService.get_by_id 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self) -> None:
        """ID로 사용자 조회 성공."""
        user = _make_user()

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=user)
        mock_session.execute = AsyncMock(return_value=result_mock)

        service = UserService(mock_session)
        found = await service.get_by_id(user.id)

        assert found.id == user.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self) -> None:
        """존재하지 않는 ID로 NotFoundError 발생."""
        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=result_mock)

        service = UserService(mock_session)
        with pytest.raises(NotFoundError):
            await service.get_by_id(uuid.uuid4())


class TestUserServiceUpdateMe:
    """UserService.update_me 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_update_me_full_name(self) -> None:
        """이름 수정 성공."""
        user = _make_user(full_name="Old Name")

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=user)
        mock_session.execute = AsyncMock(return_value=result_mock)
        mock_session.refresh = AsyncMock()

        service = UserService(mock_session)
        data = UserUpdateRequest(full_name="New Name")
        updated = await service.update_me(user.id, data)

        assert updated.full_name == "New Name"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_me_password_success(self) -> None:
        """비밀번호 변경 성공."""
        user = _make_user()

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=user)
        mock_session.execute = AsyncMock(return_value=result_mock)
        mock_session.refresh = AsyncMock()

        with (
            patch(
                "src.api.services.user_service.verify_password",
                return_value=True,
            ),
            patch(
                "src.api.services.user_service.hash_password",
                return_value="new_hashed_password",
            ),
        ):
            service = UserService(mock_session)
            data = UserUpdateRequest(
                current_password="old_password",
                new_password="new_password",
            )
            updated = await service.update_me(user.id, data)

        assert updated.hashed_password == "new_hashed_password"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_me_password_wrong_current(self) -> None:
        """현재 비밀번호 불일치 시 AuthenticationError 발생."""
        user = _make_user()

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=user)
        mock_session.execute = AsyncMock(return_value=result_mock)

        with patch(
            "src.api.services.user_service.verify_password",
            return_value=False,
        ):
            service = UserService(mock_session)
            data = UserUpdateRequest(
                current_password="wrong_password",
                new_password="new_password",
            )

            with pytest.raises(AuthenticationError):
                await service.update_me(user.id, data)


class TestUserServiceListUsers:
    """UserService.list_users 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_list_users_returns_items_and_total(self) -> None:
        """사용자 목록 조회 시 items와 total 반환."""
        users = [_make_user() for _ in range(3)]

        mock_session = AsyncMock()

        # Count query
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=3)

        # List query
        list_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all = MagicMock(return_value=users)
        list_result.scalars = MagicMock(return_value=scalars_mock)

        mock_session.execute = AsyncMock(side_effect=[count_result, list_result])

        service = UserService(mock_session)
        items, total = await service.list_users(offset=0, limit=10)

        assert len(items) == 3
        assert total == 3


class TestUserServiceAdminUpdate:
    """UserService.admin_update 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_admin_update_role(self) -> None:
        """관리자가 사용자 역할 수정."""
        user = _make_user(role="USER")

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=user)
        mock_session.execute = AsyncMock(return_value=result_mock)
        mock_session.refresh = AsyncMock()

        service = UserService(mock_session)
        data = AdminUserUpdateRequest(role="ADMIN")
        updated = await service.admin_update(user.id, data)

        assert updated.role == "ADMIN"
        mock_session.commit.assert_called_once()


class TestUserServiceDeactivate:
    """UserService.deactivate 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_deactivate_success(self) -> None:
        """사용자 비활성화 성공."""
        user = _make_user(is_active=True)

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=user)
        mock_session.execute = AsyncMock(return_value=result_mock)

        service = UserService(mock_session)
        await service.deactivate(user.id)

        assert user.is_active is False
        mock_session.commit.assert_called_once()
