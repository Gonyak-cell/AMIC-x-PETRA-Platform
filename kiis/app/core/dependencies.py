from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.redis import get_redis


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """DB 세션 의존성 (FastAPI Depends용)"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_redis_dep() -> AsyncGenerator[aioredis.Redis | None, None]:
    """Redis 의존성 (FastAPI Depends용). 연결 실패 시 None."""
    yield get_redis()
