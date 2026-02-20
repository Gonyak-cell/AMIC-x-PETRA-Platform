import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers

logger = logging.getLogger(__name__)

_ALEMBIC_DIR = Path(__file__).resolve().parent.parent


async def _run_alembic_upgrade() -> None:
    """서버 시작 시 Alembic 마이그레이션을 자동 실행한다."""

    def _upgrade() -> None:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config(str(_ALEMBIC_DIR / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(_ALEMBIC_DIR / "migrations"))
        command.upgrade(alembic_cfg, "head")

    try:
        await asyncio.to_thread(_upgrade)
        logger.info("Alembic migration completed (upgrade to head)")
    except Exception as e:
        logger.warning("Alembic migration skipped: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate secrets in production
    _effective_jwt_secret = settings.JWT_SECRET or settings.SECRET_KEY
    if not settings.DEBUG:
        if not _effective_jwt_secret:
            raise RuntimeError("JWT secret is not configured. Set JWT_SECRET or SECRET_KEY in your .env file.")
    else:
        if not _effective_jwt_secret:
            logger.warning(
                "JWT_SECRET and SECRET_KEY are both empty — "
                "JWTs will be signed with an empty string. Set at least one in .env."
            )

    # Startup — Auto-migrate DB
    await _run_alembic_upgrade()
    logger.info("Deal Management application started")
    yield
    # Shutdown
    logger.info("Deal Management application stopped")


app = FastAPI(
    title=settings.APP_NAME,
    description="M&A Deal Management Service — 7단계 거래 워크플로우 관리 시스템",
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "서비스 상태 확인"},
        {"name": "Transactions", "description": "M&A 거래 관리"},
        {"name": "Workflow", "description": "7단계 워크플로우 상태 머신"},
        {"name": "Engagements", "description": "수임계약 관리"},
        {"name": "Working Group", "description": "워킹그룹 멤버 관리"},
        {"name": "Buyers", "description": "매수자 후보 파이프라인"},
        {"name": "NDAs", "description": "NDA 관리"},
        {"name": "Bids", "description": "IOI/LOI/최종제안 관리"},
        {"name": "DD Checklist", "description": "DD 워크스트림 체크리스트"},
        {"name": "Contracts", "description": "계약/SPA 관리"},
        {"name": "Closing", "description": "클로징 체크리스트"},
        {"name": "PMI", "description": "PMI(인수 후 통합) 태스크"},
        {"name": "Earnout", "description": "어닝아웃 마일스톤"},
        {"name": "Timeline", "description": "딜 타임라인 이벤트"},
        {"name": "Integrations", "description": "FDD/IM/KIIS 서비스 연동"},
        {"name": "Dashboard", "description": "M&A 대시보드 KPI"},
    ],
)

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

# Exception handlers
register_exception_handlers(app)

# ── Routers ─────────────────────────────────────────────
from app.routers import (  # noqa: E402
    bids,
    buyers,
    closing,
    contracts,
    dashboard,
    dd_checklists,
    earnout,
    engagements,
    integrations,
    ndas,
    pmi,
    timeline,
    transactions,
    workflow,
)

app.include_router(transactions.router, prefix="/api/v1")
app.include_router(workflow.router, prefix="/api/v1")
app.include_router(engagements.router, prefix="/api/v1")
app.include_router(buyers.router, prefix="/api/v1")
app.include_router(ndas.router, prefix="/api/v1")
app.include_router(bids.router, prefix="/api/v1")
app.include_router(dd_checklists.router, prefix="/api/v1")
app.include_router(contracts.router, prefix="/api/v1")
app.include_router(closing.router, prefix="/api/v1")
app.include_router(pmi.router, prefix="/api/v1")
app.include_router(earnout.router, prefix="/api/v1")
app.include_router(integrations.router, prefix="/api/v1")
app.include_router(timeline.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "deal-mgmt"}
