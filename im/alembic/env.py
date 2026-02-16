"""Alembic 비동기 마이그레이션 환경 설정 (T-I05).

> 마지막 수정: 2026-02-10 16:29:08

SQLAlchemy 2.0 async 엔진을 사용하여 마이그레이션을 실행한다.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from src.api.config import get_config
from src.api.db.base import Base

# 모든 모델 import (autogenerate용)
from src.api.db.models import *  # noqa: F401, F403

# Alembic Config 객체
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData 대상
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """오프라인 모드에서 마이그레이션 실행 (DB 연결 없이 SQL 생성)."""
    api_config = get_config()
    url = api_config.database_url

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    """마이그레이션 실행 (동기 콜백)."""
    context.configure(
        connection=connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """비동기 엔진으로 마이그레이션 실행."""
    api_config = get_config()

    connectable = create_async_engine(
        api_config.database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """온라인 모드에서 비동기 마이그레이션 실행."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
