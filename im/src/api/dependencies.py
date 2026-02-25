"""FastAPI 공통 의존성 (T-I10).

> 마지막 수정: 2026-02-10 17:39:59

JWT 및 API Key 기반 인증 의존성을 제공한다.
OAuth2PasswordBearer + APIKeyHeader 듀얼 인증을 지원한다.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.exceptions import AuthenticationError
from src.api.security.api_keys import verify_api_key
from src.api.config import get_config
from src.api.security.auth import verify_token
from src.api.security.blacklist import is_blacklisted

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _dev_user() -> User:
    """AUTH_ENABLED=False일 때 반환할 dev 사용자."""
    return User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        email="system@autofdd.dev",
        hashed_password="federated:no-local-password",
        full_name="System (Dev)",
        role="ADMIN",
        is_active=True,
    )


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    api_key: str | None = Depends(api_key_header),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """현재 인증된 사용자를 반환한다.

    JWT 우선 검증 → 쿠키 폴백 → API Key 폴백 → 모두 없으면 401.

    Args:
        request: FastAPI Request (쿠키 접근용).
        token: Bearer JWT 토큰 (Authorization 헤더).
        api_key: API 키 (X-API-Key 헤더).
        session: 비동기 DB 세션.

    Returns:
        인증된 User 인스턴스.

    Raises:
        AuthenticationError: 인증 정보가 없거나 유효하지 않은 경우.
    """
    # Dev 모드: 인증 우회
    if not get_config().auth_enabled:
        return _dev_user()

    # Authorization 헤더 없으면 쿠키 폴백
    if token is None:
        token = request.cookies.get("access_token")

    # JWT 우선
    if token is not None:
        payload = verify_token(token, expected_type="access")

        # 블랙리스트 체크 (로그아웃된 토큰 거부, jti 없는 FDD 토큰은 생략)
        if payload.jti and await is_blacklisted(payload.jti):
            raise AuthenticationError(
                message="토큰이 무효화되었습니다.",
                details={"reason": "blacklisted"},
            )

        try:
            user_id = uuid.UUID(payload.sub)
        except (ValueError, AttributeError):
            raise AuthenticationError(
                message="유효하지 않은 사용자 ID입니다.",
                details={"reason": "invalid_sub"},
            )
        # CLIENT 역할 차단: 외부 고객은 IM 서비스에 접근할 수 없다
        if payload.role and payload.role.upper() == "CLIENT":
            raise AuthenticationError(
                message="외부 클라이언트는 IM 서비스에 접근할 수 없습니다.",
                details={"reason": "client_role_forbidden"},
            )

        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            # Cross-backend federation: auto-create user from FDD JWT claims
            import jwt as _jwt

            cfg = get_config()
            decoded = _jwt.decode(
                token,
                cfg.jwt_secret_key,
                algorithms=[cfg.jwt_algorithm],
                options={"verify_exp": False},
            )
            email = decoded.get("email", f"{payload.sub}@federated")

            # 이메일로 기존 사용자 조회 (ID가 달라도 동일 이메일이면 재사용)
            email_stmt = select(User).where(User.email == email)
            email_result = await session.execute(email_stmt)
            user = email_result.scalar_one_or_none()

            if user is None:
                user = User(
                    id=user_id,
                    email=email,
                    hashed_password="federated:no-local-password",
                    full_name=email.split("@")[0],
                    role=payload.role or "USER",
                    is_active=True,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
        return user

    # API Key 폴백
    if api_key is not None:
        return await verify_api_key(api_key, session)

    # 인증 정보 없음
    raise AuthenticationError(
        message="인증 정보가 제공되지 않았습니다.",
        details={"reason": "no_credentials"},
    )


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """활성 상태의 현재 사용자를 반환한다.

    Args:
        user: get_current_user에서 반환된 User.

    Returns:
        활성 상태의 User.

    Raises:
        AuthenticationError: 사용자가 비활성 상태인 경우.
    """
    if not user.is_active:
        raise AuthenticationError(
            message="비활성 계정입니다.",
            details={"reason": "inactive_account"},
        )
    return user
