from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _create_engine():
    database_url = settings.DATABASE_URL
    engine_kwargs: dict[str, object] = {
        "echo": settings.DEBUG,
    }

    if database_url.startswith("sqlite"):
        engine_kwargs["pool_pre_ping"] = True
    else:
        engine_kwargs.update(
            {
                "pool_pre_ping": True,
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_POOL_MAX_OVERFLOW,
                "pool_recycle": settings.DB_POOL_RECYCLE,
                "pool_timeout": settings.DB_POOL_TIMEOUT,
                "connect_args": {"ssl": False},
            }
        )

    return create_async_engine(database_url, **engine_kwargs)


engine = _create_engine()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
