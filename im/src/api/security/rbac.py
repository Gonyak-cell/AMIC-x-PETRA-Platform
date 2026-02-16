"""RBAC(역할 기반 접근 제어) 모듈 (T-I09).

> 마지막 수정: 2026-02-10 17:39:59

UserRole enum 및 FastAPI dependency factory를 제공한다.
"""

from __future__ import annotations

import enum
from typing import Any, Callable

from src.api.exceptions import AuthorizationError


class UserRole(str, enum.Enum):
    """사용자 역할."""

    USER = "USER"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


_ROLE_LEVEL: dict[UserRole, int] = {
    UserRole.USER: 1,
    UserRole.MANAGER: 2,
    UserRole.ADMIN: 3,
}


def _get_role_level(role: str) -> int:
    """역할 문자열의 레벨을 반환한다.

    Args:
        role: 역할 문자열.

    Returns:
        역할 레벨 (1-3). 알 수 없는 역할은 0.
    """
    try:
        return _ROLE_LEVEL[UserRole(role)]
    except (ValueError, KeyError):
        return 0


def require_role(minimum_role: UserRole) -> Callable[..., Any]:
    """최소 역할을 요구하는 FastAPI dependency factory.

    Args:
        minimum_role: 최소 요구 역할.

    Returns:
        FastAPI dependency 함수.
    """
    min_level = _ROLE_LEVEL[minimum_role]

    def _checker(current_user: Any) -> Any:
        """현재 사용자의 역할을 검증한다.

        Args:
            current_user: User 모델 인스턴스 (role 속성 필요).

        Returns:
            검증 통과 시 current_user.

        Raises:
            AuthorizationError: 역할 레벨이 부족한 경우.
        """
        user_level = _get_role_level(current_user.role)
        if user_level < min_level:
            raise AuthorizationError(required_role=minimum_role.value)
        return current_user

    return _checker


# 편의 함수
require_admin: Callable[..., Any] = require_role(UserRole.ADMIN)
require_manager: Callable[..., Any] = require_role(UserRole.MANAGER)
