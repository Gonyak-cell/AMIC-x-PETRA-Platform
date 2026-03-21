import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.models import Base  # noqa: F401 - 모든 모델 import 보장

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# .env의 DATABASE_URL 사용 (alembic.ini 값 오버라이드)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def _build_async_connect_args(url: str) -> dict:
    parsed = make_url(url)
    query = dict(parsed.query)
    if parsed.drivername != "postgresql+asyncpg":
        return {}

    if any(key in query for key in ("ssl", "sslmode", "sslcert", "sslkey", "sslrootcert")):
        return {}

    if parsed.host not in {None, "localhost", "127.0.0.1"}:
        return {}

    # Windows local dev environments sometimes inherit broken SSL defaults.
    return {"ssl": False}


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode (async)."""
    url = config.get_main_option("sqlalchemy.url")
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_build_async_connect_args(url),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
