import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import (
    analysis,
    audit,
    auth,
    charts,
    checklist,
    consolidation,
    deals,
    debt,
    entities,
    evidence,
    exchange_rates,
    exports,
    industries,
    issues,
    jobs,
    mapping,
    notifications,
    nwc,
    qoe,
    ralph,
    reports,
    retention,
    settings as settings_api,
    templates,
    uploads,
    vdr,
    webhooks,
    workflow,
)
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.log_middleware import setup_request_logging
from app.core.logging import get_logger, setup_logging

# 구조화 로깅 초기화 (통일 JSON 로그 스키마)
setup_logging(level=settings.log_level, json_output=True, service_name="fdd", log_dir=settings.log_dir or None)
logger = get_logger(__name__)

_ALEMBIC_DIR = Path(__file__).resolve().parent.parent
_migration_ok: bool = False


async def _run_alembic_upgrade() -> None:
    """서버 시작 시 Alembic 마이그레이션을 자동 실행한다."""
    global _migration_ok

    def _upgrade() -> None:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config(str(_ALEMBIC_DIR / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(_ALEMBIC_DIR / "alembic"))
        command.upgrade(alembic_cfg, "head")

    try:
        await asyncio.wait_for(asyncio.to_thread(_upgrade), timeout=10)
        _migration_ok = True
        logger.info("Alembic migration completed (upgrade to head)")
    except Exception as e:
        _migration_ok = False
        logger.warning("Alembic migration FAILED: %s — API may return 500 for DB operations", e)


@asynccontextmanager
async def lifespan(app_: FastAPI):
    if os.getenv("TESTING") != "true":
        await _run_alembic_upgrade()
    logger.info("FDD application started")
    yield
    logger.info("FDD application stopped")


limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="Auto FDD",
    description="Financial Due Diligence Automation API",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "type": "urn:fdd:error:system:rate_limit",
            "title": "RATE_LIMIT_EXCEEDED",
            "status": 429,
            "detail": f"Rate limit exceeded: {exc.detail}",
        },
        media_type="application/problem+json",
    )


# RFC 7807 에러 핸들러 등록 (마스터파일 §4.4 + §5.1)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    max_age=3600,
)

# 요청/응답 JSON 로깅 미들웨어
setup_request_logging(app)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(deals.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(mapping.router, prefix="/api/v1")
app.include_router(qoe.router, prefix="/api/v1")
app.include_router(nwc.router, prefix="/api/v1")
app.include_router(debt.router, prefix="/api/v1")
app.include_router(evidence.router, prefix="/api/v1")
app.include_router(charts.router, prefix="/api/v1")
app.include_router(issues.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(retention.router, prefix="/api/v1")
app.include_router(vdr.router, prefix="/api/v1")
app.include_router(workflow.router, prefix="/api/v1")
app.include_router(entities.router, prefix="/api/v1")
app.include_router(exchange_rates.router, prefix="/api/v1")
app.include_router(consolidation.router, prefix="/api/v1")
app.include_router(industries.router, prefix="/api/v1")

# Auto Analysis & Checklist
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(checklist.router, prefix="/api/v1")

# Ralph Loop (AI Quality Refinement)
app.include_router(ralph.router, prefix="/api/v1")

# Phase 5: Portal endpoints
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(settings_api.router, prefix="/api/v1")

logger.info("Auto FDD application initialized")


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0", "migration_ok": _migration_ok}


@app.get("/metrics")
def prometheus_metrics():
    """Prometheus 포맷 메트릭 엔드포인트 — FDD-1804."""
    from fastapi.responses import PlainTextResponse

    from app.services.metrics.collector import metrics

    return PlainTextResponse(
        content=metrics.to_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/metrics/json")
def json_metrics():
    """JSON 형식 메트릭 엔드포인트."""
    from app.services.metrics.collector import metrics

    return metrics.to_dict()
