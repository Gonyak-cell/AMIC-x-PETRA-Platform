"""JWT RS256 인증 모듈 (T-I07).

> 마지막 수정: 2026-02-10 17:39:59

RS256(비대칭키) 기반 JWT 토큰 생성 및 검증을 제공한다.
PEM 파일이 없으면 HS256(대칭키)로 폴백한다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt

from src.api.config import APIConfig, get_config
from src.api.exceptions import AuthenticationError


@dataclass(frozen=True)
class TokenPayload:
    """JWT 토큰 페이로드."""

    sub: str
    role: str
    exp: datetime
    iat: datetime
    jti: str | None
    token_type: str


def _load_private_key(path: str) -> str | None:
    """RS256 개인키 PEM 파일을 로드한다.

    Args:
        path: PEM 파일 경로.

    Returns:
        PEM 문자열 또는 None (파일 없음).
    """
    p = Path(path)
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return None


def _load_public_key(path: str) -> str | None:
    """RS256 공개키 PEM 파일을 로드한다.

    Args:
        path: PEM 파일 경로.

    Returns:
        PEM 문자열 또는 None (파일 없음).
    """
    p = Path(path)
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return None


def _get_signing_key_and_algorithm(
    config: APIConfig,
) -> tuple[str, str]:
    """서명에 사용할 키와 알고리즘을 결정한다.

    RS256 개인키가 있으면 RS256, 없으면 HS256 폴백.

    Returns:
        (signing_key, algorithm) 튜플.
    """
    if config.jwt_algorithm == "RS256":
        private_key = _load_private_key(config.jwt_private_key_path)
        if private_key is not None:
            return private_key, "RS256"
    return config.jwt_secret_key, "HS256"


def _get_verification_key_and_algorithm(
    config: APIConfig,
) -> tuple[str, str]:
    """검증에 사용할 키와 알고리즘을 결정한다.

    RS256 공개키가 있으면 RS256, 없으면 HS256 폴백.

    Returns:
        (verification_key, algorithm) 튜플.
    """
    if config.jwt_algorithm == "RS256":
        public_key = _load_public_key(config.jwt_public_key_path)
        if public_key is not None:
            return public_key, "RS256"
    return config.jwt_secret_key, "HS256"


def create_access_token(
    user_id: str,
    role: str,
    config: APIConfig | None = None,
) -> str:
    """Access JWT 토큰을 생성한다.

    Args:
        user_id: 사용자 UUID 문자열.
        role: 사용자 역할 (USER, MANAGER, ADMIN).
        config: API 설정. None이면 기본 설정 사용.

    Returns:
        인코딩된 JWT 문자열.
    """
    cfg = config or get_config()
    now = datetime.now(timezone.utc)
    key, algorithm = _get_signing_key_and_algorithm(cfg)

    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "exp": now + timedelta(minutes=cfg.jwt_access_token_expire_minutes),
        "iat": now,
        "jti": str(uuid.uuid4()),
        "token_type": "access",
    }
    return jwt.encode(payload, key, algorithm=algorithm)


def create_refresh_token(
    user_id: str,
    config: APIConfig | None = None,
) -> str:
    """Refresh JWT 토큰을 생성한다.

    Args:
        user_id: 사용자 UUID 문자열.
        config: API 설정. None이면 기본 설정 사용.

    Returns:
        인코딩된 JWT 문자열.
    """
    cfg = config or get_config()
    now = datetime.now(timezone.utc)
    key, algorithm = _get_signing_key_and_algorithm(cfg)

    payload: dict[str, Any] = {
        "sub": user_id,
        "role": "",
        "exp": now + timedelta(days=cfg.jwt_refresh_token_expire_days),
        "iat": now,
        "jti": str(uuid.uuid4()),
        "token_type": "refresh",
    }
    return jwt.encode(payload, key, algorithm=algorithm)


def verify_token(
    token: str,
    config: APIConfig | None = None,
    *,
    expected_type: str | None = None,
) -> TokenPayload:
    """JWT 토큰을 검증하고 페이로드를 반환한다.

    Args:
        token: 인코딩된 JWT 문자열.
        config: API 설정. None이면 기본 설정 사용.
        expected_type: 기대하는 토큰 타입 ("access" 또는 "refresh").

    Returns:
        TokenPayload 인스턴스.

    Raises:
        AuthenticationError: 토큰이 만료/변조/잘못된 경우.
    """
    cfg = config or get_config()
    key, algorithm = _get_verification_key_and_algorithm(cfg)

    try:
        decoded = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            options={"require": ["sub", "role", "exp", "iat"]},
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationError(
            message="토큰이 만료되었습니다.",
            details={"reason": "expired"},
        )
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(
            message="유효하지 않은 토큰입니다.",
            details={"reason": str(e)},
        )

    # type ↔ token_type 호환 처리 (FDD: "type", IM: "token_type")
    token_type = decoded.get("token_type") or decoded.get("type", "")
    if expected_type is not None and token_type != expected_type:
        raise AuthenticationError(
            message=f"잘못된 토큰 타입입니다. 기대: {expected_type}, 실제: {token_type}",
            details={"expected": expected_type, "actual": token_type},
        )

    return TokenPayload(
        sub=decoded["sub"],
        role=decoded["role"],
        exp=datetime.fromtimestamp(decoded["exp"], tz=timezone.utc),
        iat=datetime.fromtimestamp(decoded["iat"], tz=timezone.utc),
        jti=decoded.get("jti"),
        token_type=token_type,
    )
