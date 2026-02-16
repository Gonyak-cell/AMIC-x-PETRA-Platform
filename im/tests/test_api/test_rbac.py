"""RBAC 테스트 (T-I09).

> 마지막 수정: 2026-02-10 17:39:59
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.api.exceptions import AuthorizationError
from src.api.security.rbac import (
    UserRole,
    _get_role_level,
    require_admin,
    require_manager,
    require_role,
)


def _make_user(role: str) -> MagicMock:
    """지정 역할의 Mock User를 생성한다."""
    user = MagicMock()
    user.role = role
    return user


class TestUserRole:
    """UserRole enum 테스트."""

    def test_role_values(self) -> None:
        """역할 문자열 값이 올바르다."""
        assert UserRole.USER.value == "USER"
        assert UserRole.MANAGER.value == "MANAGER"
        assert UserRole.ADMIN.value == "ADMIN"


class TestRoleLevel:
    """역할 레벨 테스트."""

    def test_admin_highest(self) -> None:
        """ADMIN이 가장 높은 레벨이다."""
        assert _get_role_level("ADMIN") > _get_role_level("MANAGER")
        assert _get_role_level("MANAGER") > _get_role_level("USER")

    def test_unknown_role_returns_zero(self) -> None:
        """알 수 없는 역할은 레벨 0이다."""
        assert _get_role_level("UNKNOWN") == 0
        assert _get_role_level("") == 0


class TestRequireRole:
    """require_role dependency factory 테스트."""

    def test_admin_passes_all(self) -> None:
        """ADMIN은 모든 역할 요구사항을 충족한다."""
        admin = _make_user("ADMIN")
        for role in UserRole:
            checker = require_role(role)
            assert checker(admin) is admin

    def test_manager_passes_user_and_manager(self) -> None:
        """MANAGER는 USER/MANAGER 요구를 충족한다."""
        manager = _make_user("MANAGER")

        assert require_role(UserRole.USER)(manager) is manager
        assert require_role(UserRole.MANAGER)(manager) is manager

    def test_manager_fails_admin(self) -> None:
        """MANAGER는 ADMIN 요구를 충족하지 못한다."""
        manager = _make_user("MANAGER")

        with pytest.raises(AuthorizationError):
            require_role(UserRole.ADMIN)(manager)

    def test_user_passes_user_only(self) -> None:
        """USER는 USER 요구만 충족한다."""
        user = _make_user("USER")

        assert require_role(UserRole.USER)(user) is user

        with pytest.raises(AuthorizationError):
            require_role(UserRole.MANAGER)(user)
        with pytest.raises(AuthorizationError):
            require_role(UserRole.ADMIN)(user)

    def test_unknown_role_fails(self) -> None:
        """알 수 없는 역할은 모든 요구를 실패한다."""
        unknown = _make_user("UNKNOWN")

        with pytest.raises(AuthorizationError):
            require_role(UserRole.USER)(unknown)

    def test_authorization_error_includes_required_role(self) -> None:
        """AuthorizationError에 required_role이 포함된다."""
        user = _make_user("USER")

        with pytest.raises(AuthorizationError) as exc_info:
            require_role(UserRole.ADMIN)(user)

        assert exc_info.value.details.get("required_role") == "ADMIN"


class TestConvenienceFunctions:
    """편의 함수 테스트."""

    def test_require_admin(self) -> None:
        """require_admin은 ADMIN만 통과시킨다."""
        admin = _make_user("ADMIN")
        assert require_admin(admin) is admin

        user = _make_user("USER")
        with pytest.raises(AuthorizationError):
            require_admin(user)

    def test_require_manager(self) -> None:
        """require_manager는 MANAGER 이상만 통과시킨다."""
        manager = _make_user("MANAGER")
        assert require_manager(manager) is manager

        admin = _make_user("ADMIN")
        assert require_manager(admin) is admin

        user = _make_user("USER")
        with pytest.raises(AuthorizationError):
            require_manager(user)
