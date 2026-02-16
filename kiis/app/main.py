import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.core.elasticsearch import close_elasticsearch, init_elasticsearch
from app.core.exceptions import register_exception_handlers
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
    reits,
    sanctions,
    search,
)

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

    # Startup
    await init_redis()
    await init_elasticsearch()
    await init_scheduler()
    logger.info("KIIS application started")
    yield
    # Shutdown
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
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting (innermost - runs first on request)
app.add_middleware(
    RateLimitMiddleware,
    redis_url=settings.REDIS_URL,
    max_requests=settings.RATE_LIMIT_LOGIN_MAX,
    window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW,
    paths=["/api/v1/auth/login"],
)

# Exception handlers
register_exception_handlers(app)

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(dart.router, prefix="/api/v1/dart", tags=["DART"])
app.include_router(kofia.router, prefix="/api/v1/kofia", tags=["KOFIA"])
app.include_router(reits.router, prefix="/api/v1/reits", tags=["REITs"])
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


@app.get("/health")
async def health_check():
    return {"status": "ok"}
