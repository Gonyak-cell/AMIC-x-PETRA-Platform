"""JWT 토큰 블랙리스트 관리.

> 마지막 수정: 2026-02-10 19:30:00

Redis 기반 JTI 블랙리스트로 로그아웃된 토큰을 추적한다.
"""

from __future__ import annotations

from datetime import datetime, timezone

from redis.asyncio import Redis

from src.api.config import get_config


async def _get_redis() -> Redis:
    """Redis 클라이언트를 생성한다."""
    config = get_config()
    return Redis.from_url(config.redis_url, decode_responses=True)


async def blacklist_token(jti: str, exp: datetime) -> None:
    """토큰을 블랙리스트에 추가한다.

    Args:
        jti: 토큰 고유 ID.
        exp: 토큰 만료 시각 (UTC).
    """
    now = datetime.now(timezone.utc)
    ttl_seconds = int((exp - now).total_seconds())
    if ttl_seconds <= 0:
        return

    redis = await _get_redis()
    try:
        await redis.setex(f"blacklist:jti:{jti}", ttl_seconds, "1")
    finally:
        await redis.close()


async def is_blacklisted(jti: str) -> bool:
    """토큰이 블랙리스트에 있는지 확인한다.

    Args:
        jti: 토큰 고유 ID.

    Returns:
        블랙리스트에 있으면 True.
    """
    redis = await _get_redis()
    try:
        result = await redis.exists(f"blacklist:jti:{jti}")
        return bool(result)
    finally:
        await redis.close()
