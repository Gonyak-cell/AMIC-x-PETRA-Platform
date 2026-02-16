"""API 키 관리 모듈 (T-I08).

> 마지막 수정: 2026-02-10 17:39:59

API 키 생성(imgen_ prefix + 32 hex) 및 SHA-256 해시 기반 검증을 제공한다.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.api.db.models.api_key import APIKey
from src.api.db.models.user import User
from src.api.exceptions import AuthenticationError

_KEY_PREFIX = "imgen_"
_KEY_HEX_LENGTH = 32


def generate_api_key() -> tuple[str, str]:
    """새 API 키를 생성한다.

    Returns:
        (raw_key, sha256_hash) 튜플.
        raw_key 형식: "imgen_" + 32자 hex (총 70자).
    """
    raw = _KEY_PREFIX + secrets.token_hex(_KEY_HEX_LENGTH)
    key_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, key_hash


async def verify_api_key(
    raw_key: str,
    session: AsyncSession,
) -> User:
    """API 키를 검증하고 소유자 User를 반환한다.

    Args:
        raw_key: 평문 API 키.
        session: 비동기 DB 세션.

    Returns:
        해당 API 키의 소유자 User.

    Raises:
        AuthenticationError: 키가 잘못되었거나 비활성/만료인 경우.
    """
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    stmt = (
        select(APIKey)
        .where(APIKey.key_hash == key_hash)
        .options(joinedload(APIKey.user))
    )
    result = await session.execute(stmt)
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise AuthenticationError(
            message="유효하지 않은 API 키입니다.",
            details={"reason": "not_found"},
        )

    if not api_key.is_active:
        raise AuthenticationError(
            message="비활성화된 API 키입니다.",
            details={"reason": "inactive"},
        )

    if api_key.expires_at is not None:
        now = datetime.now(timezone.utc)
        expires = api_key.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now >= expires:
            raise AuthenticationError(
                message="만료된 API 키입니다.",
                details={"reason": "expired"},
            )

    # last_used_at 갱신
    api_key.last_used_at = datetime.now(timezone.utc)

    return api_key.user
