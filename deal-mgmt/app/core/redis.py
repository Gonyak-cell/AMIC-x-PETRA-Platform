"""deal-mgmt Redis 헬퍼 — 뉴스 피드 캐싱 등에 사용."""

import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_pool: aioredis.Redis | None = None


async def init_redis() -> None:
    """Redis 연결 풀을 초기화한다."""
    global _redis_pool
    try:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        await _redis_pool.ping()
        logger.info("Redis connected: %s", settings.REDIS_URL)
    except Exception as e:
        logger.warning("Redis connection failed: %s. Running without cache.", e)
        _redis_pool = None


async def close_redis() -> None:
    """Redis 연결 풀을 종료한다."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
        logger.info("Redis disconnected")


def get_redis() -> aioredis.Redis | None:
    """Redis 클라이언트를 반환한다. 연결 실패 시 None."""
    return _redis_pool
