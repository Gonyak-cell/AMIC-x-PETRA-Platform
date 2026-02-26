"""헬스체크 엔드포인트 (T-I06).

> 마지막 수정: 2026-02-10 16:29:08

/health (liveness probe), /ready (readiness probe) 제공.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from src.api import __version__

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Liveness probe 응답."""

    status: str
    version: str
    service: str = ""
    db: str = ""


class ReadinessResponse(BaseModel):
    """Readiness probe 응답."""

    status: str
    database: bool
    redis: bool


async def _check_db() -> bool:
    """DB 연결 상태를 확인한다."""
    try:
        from src.api.db.session import async_engine, init_engine

        if async_engine is None:
            init_engine()

        from src.api.db.session import async_engine as engine_ref

        if engine_ref is None:
            return False
        async with engine_ref.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    """Redis 연결 상태를 확인한다."""
    try:
        from redis.asyncio import from_url

        from src.api.config import get_config

        config = get_config()
        client = from_url(config.redis_url)
        try:
            await client.ping()
            return True
        finally:
            await client.aclose()
    except Exception:
        return False


@router.get(
    "/health",
    summary="Liveness probe",
    description="서버 생존 확인. 로드밸런서/쿠버네티스 liveness probe용.",
)
async def health() -> dict:
    """DB 연결 포함 상태를 반환한다."""
    db_ok = await _check_db()
    if db_ok:
        return {"status": "ok", "service": "im", "version": __version__, "db": "ok"}
    return {"status": "degraded", "service": "im", "version": __version__, "db": "error"}


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="DB + Redis 연결 확인. Readiness probe용.",
)
async def ready() -> ReadinessResponse:
    """DB와 Redis 연결을 확인한다. 하나라도 실패 시 503."""
    db_ok = await _check_db()
    redis_ok = await _check_redis()

    status = "ready" if (db_ok and redis_ok) else "not_ready"
    response = ReadinessResponse(status=status, database=db_ok, redis=redis_ok)

    if status == "not_ready":
        from fastapi.responses import JSONResponse

        return JSONResponse(  # type: ignore[return-value]
            status_code=503,
            content=response.model_dump(),
        )
    return response
