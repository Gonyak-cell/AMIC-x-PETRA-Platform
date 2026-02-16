"""FastAPI 인증 의존성 — get_current_user, require_permission.

AUTH_ENABLED=False (기본값)일 때 dev 사용자를 반환하여
기존 테스트와 로컬 개발 환경이 변경 없이 작동한다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.rbac import Permission, has_permission
from app.auth.token import decode_access_token
from app.config import settings
from app.core.errors import ErrorCode
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.database import get_db
from app.models.user import User, UserRole

# auto_error=False → Authorization 헤더 없어도 요청 거부하지 않음
_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """요청 컨텍스트에 전달되는 경량 사용자 정보."""

    id: uuid.UUID
    email: str
    role: UserRole
    display_name: str


# AUTH_ENABLED=False일 때 사용되는 기본 dev 사용자
_DEV_USER = CurrentUser(
    id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
    email="system@autofdd.dev",
    role=UserRole.ADMIN,
    display_name="System (Dev)",
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """JWT 토큰에서 현재 사용자를 추출하고 검증한다.

    AUTH_ENABLED=False이면 Admin 권한의 dev 사용자를 반환한다.
    """
    if not settings.auth_enabled:
        return _DEV_USER

    if credentials is None:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "Authorization header required",
        )

    payload = decode_access_token(credentials.credentials)

    # jti가 있으면 블랙리스트 확인 (레거시 토큰은 jti 없으므로 스킵)
    jti = payload.get("jti")
    if jti:
        from app.auth.token import is_token_blacklisted

        if is_token_blacklisted(db, jti):
            raise AuthenticationError(
                ErrorCode.AUTH_TOKEN_REVOKED,
                "Token has been revoked",
            )

    user_id = uuid.UUID(payload["sub"])

    user = db.get(User, user_id)
    if user is None:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "User not found",
        )
    if not user.is_active:
        raise AuthenticationError(
            ErrorCode.AUTH_USER_DISABLED,
            "User account is disabled",
        )

    return CurrentUser(
        id=user.id,
        email=user.email,
        role=user.role,
        display_name=user.display_name,
    )


def require_permission(permission: Permission):
    """특정 권한을 요구하는 FastAPI Depends 팩토리."""

    def _check(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not has_permission(current_user.role, permission):
            raise AuthorizationError(
                ErrorCode.AUTH_FORBIDDEN,
                f"Permission '{permission}' required",
                context={"user_role": current_user.role, "required": permission},
            )
        return current_user

    return Depends(_check)
