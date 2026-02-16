from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import (
    audit,
    auth,
    charts,
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
from app.core.logging import get_logger, setup_logging

# 구조화 로깅 초기화 (마스터파일 §4.5)
setup_logging(level=settings.log_level, json_output=True)
logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="Auto FDD",
    description="Financial Due Diligence Automation API",
    version="0.1.0",
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

# Phase 5: Portal endpoints
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(settings_api.router, prefix="/api/v1")

logger.info("Auto FDD application initialized")


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}


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
