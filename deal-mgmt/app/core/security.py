from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


@dataclass(frozen=True)
class JWTClaims:
    """크로스 백엔드 JWT 클레임 (DB 조회 없이 사용)."""

    user_id: str
    email: str | None
    role: str


def get_jwt_secret() -> str:
    """JWT 검증에 사용할 시크릿을 반환한다. JWT_SECRET 우선, 없으면 SECRET_KEY 폴백."""
    secret = settings.JWT_SECRET or settings.SECRET_KEY
    if not secret:
        raise RuntimeError("JWT secret is not configured. Set JWT_SECRET or SECRET_KEY in your .env file.")
    return secret


_DEV_CLAIMS = JWTClaims(
    user_id="00000000-0000-0000-0000-000000000000",
    email="system@autofdd.dev",
    role="ANALYST",
)


async def get_jwt_claims(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> JWTClaims:
    """JWT 토큰에서 클레임만 추출한다 (DB 조회 없음).

    FDD가 발급한 JWT를 디코딩하여 user_id, email, role을 반환한다.
    deal-mgmt는 자체 User DB가 없으므로 클레임만 사용한다.
    """
    if not settings.AUTH_ENABLED:
        _env = os.getenv("ENV", "").lower()
        if _env not in ("local", "dev", "test"):
            raise RuntimeError(
                f"CRITICAL: AUTH_ENABLED=False is only allowed in local/dev/test environments, got ENV={_env!r}"
            )
        return _DEV_CLAIMS

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Authorization 헤더 없으면 쿠키 폴백
    if token is None:
        token = request.cookies.get("access_token")
    if token is None:
        raise credentials_exception
    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": True},
        )
        sub: str | None = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except JWTError:
        logger.debug("JWT decode failed", exc_info=True)
        raise credentials_exception

    return JWTClaims(
        user_id=sub,
        email=payload.get("email"),
        role=payload.get("role", ""),
    )


def require_role(*roles: str) -> Callable[..., Coroutine[Any, Any, JWTClaims]]:
    """지정된 역할을 가진 사용자만 접근을 허용하는 의존성 팩토리."""

    async def role_checker(
        claims: JWTClaims = Depends(get_jwt_claims),
    ) -> JWTClaims:
        if claims.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 작업을 수행할 권한이 없습니다",
            )
        return claims

    return role_checker


# ── CLIENT 역할 접근 제어 ────────────────────────────────

_CLIENT_ROLE = "CLIENT"


def require_write_access() -> Callable[..., Coroutine[Any, Any, JWTClaims]]:
    """CLIENT 역할의 모든 쓰기(POST/PATCH/DELETE) 작업을 차단한다."""

    async def checker(claims: JWTClaims = Depends(get_jwt_claims)) -> JWTClaims:
        if claims.role == _CLIENT_ROLE or not claims.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="읽기 전용: 클라이언트는 데이터를 수정할 수 없습니다",
            )
        return claims

    return checker


async def check_client_deal_access(
    db: AsyncSession,
    txn_id: uuid.UUID,
    claims: JWTClaims,
) -> None:
    """CLIENT 역할일 때 해당 딜에 대한 접근 권한을 검증한다.

    비-CLIENT 역할은 바로 통과한다.
    """
    if claims.role != _CLIENT_ROLE:
        return
    if claims.email is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 거래에 접근할 권한이 없습니다",
        )
    from app.models.deal_client import DealClient

    result = await db.execute(
        select(DealClient.id).where(
            DealClient.transaction_id == txn_id,
            func.lower(DealClient.email) == func.lower(claims.email),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 거래에 접근할 권한이 없습니다",
        )
