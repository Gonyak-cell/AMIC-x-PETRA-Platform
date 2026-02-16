"""비동기 DB 엔진 및 세션 팩토리 (T-I03).

> 마지막 수정: 2026-02-10 16:29:08

SQLAlchemy 2.0 async 엔진과 세션 생성기를 제공한다.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.config import APIConfig, get_config

# 모듈 레벨 엔진 (lifespan에서 초기화)
async_engine: AsyncEngine | None = None
AsyncSessionFactory: async_sessionmaker[AsyncSession] | None = None


def init_engine(config: APIConfig | None = None) -> AsyncEngine:
    """비동기 DB 엔진을 생성하고 모듈 변수에 저장한다.

    Args:
        config: API 설정. None이면 get_config() 사용.

    Returns:
        생성된 AsyncEngine.
    """
    global async_engine, AsyncSessionFactory

    if config is None:
        config = get_config()

    async_engine = create_async_engine(
        config.database_url,
        pool_size=config.db_pool_size,
        max_overflow=config.db_max_overflow,
        echo=config.db_echo,
    )
    AsyncSessionFactory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return async_engine


async def dispose_engine() -> None:
    """엔진을 종료하고 커넥션 풀을 정리한다."""
    global async_engine, AsyncSessionFactory

    if async_engine is not None:
        await async_engine.dispose()
        async_engine = None
        AsyncSessionFactory = None


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """비동기 DB 세션을 생성하는 제너레이터.

    성공 시 commit, 실패 시 rollback 후 예외를 재발생시킨다.

    Yields:
        AsyncSession 인스턴스.
    """
    if AsyncSessionFactory is None:
        init_engine()

    assert AsyncSessionFactory is not None
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
