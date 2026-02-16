"""JWT 토큰 생성 및 검증 — FDD-1704."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import ErrorCode
from app.core.exceptions import AuthenticationError


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    role: str,
) -> str:
    """JWT Access Token을 생성한다."""
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
        "type": "access",
        "iat": datetime.now(UTC),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: uuid.UUID) -> str:
    """JWT Refresh Token을 생성한다."""
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
        "iat": datetime.now(UTC),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """JWT Access Token을 검증하고 payload를 반환한다."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as e:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_EXPIRED,
            "Access token has expired",
        ) from e
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "Invalid access token",
        ) from e

    if payload.get("type") != "access":
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "Not an access token",
        )
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """JWT Refresh Token을 검증하고 payload를 반환한다."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as e:
        raise AuthenticationError(
            ErrorCode.AUTH_REFRESH_TOKEN_EXPIRED,
            "Refresh token has expired",
        ) from e
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "Invalid refresh token",
        ) from e

    if payload.get("type") != "refresh":
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "Not a refresh token",
        )
    return payload


def is_token_blacklisted(db: Session, jti: str) -> bool:
    """jti가 블랙리스트에 등록되었는지 확인한다."""
    from app.models.token_blacklist import TokenBlacklist

    stmt = select(TokenBlacklist.id).where(TokenBlacklist.jti == jti)
    return db.scalars(stmt).first() is not None
