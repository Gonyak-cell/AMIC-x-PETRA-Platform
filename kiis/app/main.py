import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.core.elasticsearch import close_elasticsearch, init_elasticsearch
from app.core.exceptions import register_exception_handlers
from app.core.log_middleware import setup_request_logging
from app.core.logging import setup_logging
from app.core.redis import close_redis, init_redis
from app.tasks.scheduler import close_scheduler, init_scheduler
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import (
    alerts,
    analysis,
    auth,
    company,
    dart,
    dashboard,
    deals,
    disclosures,
    entity,
    kofia,
    managers,
    news,
    portfolio,
    public_data,
    reits,
    sanctions,
    search,
)

# 구조화 로깅 초기화 (통일 JSON 로그 스키마)
setup_logging(level="INFO", json_output=not settings.DEBUG, service_name="kiis", log_dir=settings.LOG_DIR or None)
logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """보안 헤더를 모든 응답에 추가하는 미들웨어."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


_INSECURE_DEFAULT_KEY = "change-this-to-a-random-secret-key"

# Alembic 프로젝트 루트 (kiis/)
_ALEMBIC_DIR = Path(__file__).resolve().parent.parent

# 마이그레이션 상태 추적 — health check에서 참조
_migration_ok: bool = True  # deploy.yml에서 마이그레이션 관리


async def _run_alembic_upgrade() -> None:
    """서버 시작 시 Alembic 마이그레이션을 자동 실행한다."""
    global _migration_ok

    def _upgrade() -> None:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config(str(_ALEMBIC_DIR / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(_ALEMBIC_DIR / "migrations"))
        command.upgrade(alembic_cfg, "head")

    try:
        await asyncio.wait_for(asyncio.to_thread(_upgrade), timeout=10)
        _migration_ok = True
        logger.info("Alembic migration completed (upgrade to head)")
    except Exception as e:
        _migration_ok = False
        logger.warning("Alembic migration FAILED: %s — API may return 500 for DB operations", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate secrets in production
    _effective_jwt_secret = settings.JWT_SECRET or settings.SECRET_KEY
    if not settings.DEBUG:
        if not settings.SECRET_KEY or settings.SECRET_KEY == _INSECURE_DEFAULT_KEY:
            raise RuntimeError(
                "SECRET_KEY must be set to a secure random value in production. "
                "Set SECRET_KEY in your .env file."
            )
        if not _effective_jwt_secret:
            raise RuntimeError(
                "JWT secret is not configured. "
                "Set JWT_SECRET or SECRET_KEY in your .env file."
            )
        if not settings.DART_API_KEY:
            raise RuntimeError(
                "DART_API_KEY is required in production. "
                "Register at https://opendart.fss.or.kr and set DART_API_KEY."
            )
    else:
        if not _effective_jwt_secret:
            logger.warning(
                "JWT_SECRET and SECRET_KEY are both empty — "
                "JWTs will be signed with an empty string. Set at least one in .env."
            )
        if not settings.DART_API_KEY:
            logger.warning("DART_API_KEY is empty — DART API calls will fail")

    # 마이그레이션은 deploy.yml에서 관리 (중복 실행 방지)
    await init_redis()
    await init_elasticsearch()
    await init_scheduler()
    logger.info("KIIS application started")
    yield
    # Shutdown
    from app.routers.kofia import close_kofia_service

    await close_kofia_service()
    await close_scheduler()
    await close_elasticsearch()
    await close_redis()
    logger.info("KIIS application stopped")


app = FastAPI(
    title=settings.APP_NAME,
    description="Korea Investment Intelligence System - 차세대 지능형 투자정보 통합 시스템",
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Auth", "description": "사용자 인증 및 토큰 관리"},
        {"name": "DART", "description": "금융감독원 전자공시 데이터 조회"},
        {"name": "KOFIA", "description": "금융투자협회 펀드 정보 조회"},
        {"name": "REITs", "description": "리츠 정보 조회 및 분석"},
        {"name": "Companies", "description": "기업 정보 통합 조회"},
        {"name": "News", "description": "금융 뉴스 수집 및 NLP 분석"},
        {"name": "Entity Resolution", "description": "기업명 동일성 판별 (Entity Resolution)"},
        {"name": "PublicData", "description": "공공데이터포털 사모펀드 GP 정보"},
        {"name": "Analysis", "description": "평판 분석 및 스코어링"},
        {"name": "Deals", "description": "딜 소싱 및 투자 DNA 분석"},
        {"name": "Disclosures", "description": "전자공시 딥링크 관리"},
        {"name": "Portfolio", "description": "포트폴리오 생존분석"},
        {"name": "Managers", "description": "심사역(Key Man) 이동 추적"},
        {"name": "Sanctions", "description": "금융 제재 경중 분류"},
        {"name": "Search", "description": "ElasticSearch 통합검색"},
        {"name": "Dashboard", "description": "시스템 대시보드 요약"},
        {"name": "Watchlist", "description": "관심 기업 모니터링"},
        {"name": "Alerts", "description": "알림 이력 관리"},
    ],
)

# Security Headers (outermost - runs last on response)
app.add_middleware(SecurityHeadersMiddleware)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    max_age=3600,
)

# Rate Limiting (innermost - runs first on request)
app.add_middleware(
    RateLimitMiddleware,
    redis_url=settings.REDIS_URL,
    max_requests=settings.RATE_LIMIT_LOGIN_MAX,
    window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW,
    paths=["/api/v1/auth/login"],
)

# 요청/응답 JSON 로깅 미들웨어
setup_request_logging(app)

# Exception handlers
register_exception_handlers(app)

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(dart.router, prefix="/api/v1/dart", tags=["DART"])
app.include_router(kofia.router, prefix="/api/v1/kofia", tags=["KOFIA"])
app.include_router(reits.router, prefix="/api/v1/reits", tags=["REITs"])
app.include_router(public_data.router, prefix="/api/v1/public-data", tags=["PublicData"])
app.include_router(company.router, prefix="/api/v1/companies", tags=["Companies"])
app.include_router(news.router, prefix="/api/v1/news", tags=["News"])
app.include_router(entity.router, prefix="/api/v1/entities", tags=["Entity Resolution"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(deals.router, prefix="/api/v1/deals", tags=["Deals"])
app.include_router(disclosures.router, prefix="/api/v1/disclosures", tags=["Disclosures"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
app.include_router(managers.router, prefix="/api/v1/managers", tags=["Managers"])
app.include_router(sanctions.router, prefix="/api/v1/sanctions", tags=["Sanctions"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(alerts.watchlist_router, prefix="/api/v1/watchlist", tags=["Watchlist"])
app.include_router(alerts.alerts_router, prefix="/api/v1/alerts", tags=["Alerts"])

from app.routers import audit as audit_router  # noqa: E402
app.include_router(audit_router.router, prefix="/api/v1/audit", tags=["Audit"])


@app.get("/health")
async def health_check():
    result = {"status": "ok", "service": "kiis", "migration_ok": _migration_ok}
    try:
        from sqlalchemy import text

        from app.core.database import async_session_factory

        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        result["db"] = "ok"
    except Exception:
        result["status"] = "degraded"
        result["db"] = "error"
    return result
