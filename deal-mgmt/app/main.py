import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.log_middleware import setup_request_logging
from app.core.logging import setup_logging

# 구조화 로깅 초기화 (통일 JSON 로그 스키마)
setup_logging(level="INFO", json_output=not settings.DEBUG, service_name="deal-mgmt", log_dir=settings.LOG_DIR or None)
logger = logging.getLogger(__name__)

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
    # JWT secret validation is handled at import time in core/config.py
    # (raises RuntimeError if ENV=production and using dev secret)

    # 마이그레이션은 deploy.yml에서 관리 (중복 실행 방지)
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
        {"name": "Closing", "description": "Closing 체크리스트"},
        {"name": "PMI", "description": "PMI(인수 후 통합) 태스크"},
        {"name": "Earnout", "description": "어닝아웃 마일스톤"},
        {"name": "Timeline", "description": "딜 타임라인 이벤트"},
        {"name": "Notes", "description": "딜 내부 노트/코멘트"},
        {"name": "Approvals", "description": "승인 워크플로우"},
        {"name": "Risks", "description": "리스크 레지스터 (5×4 매트릭스)"},
        {"name": "Compliance", "description": "규제/컴플라이언스 체크리스트"},
        {"name": "Integrations", "description": "FDD/IM/KIIS 서비스 연동"},
        {"name": "Dashboard", "description": "M&A 대시보드 KPI"},
        {"name": "Legal Documents", "description": "법률 문서 생성 (SPA/SHA/BTA/SSA/MOU)"},
        {"name": "Marketing Materials", "description": "마케팅 자료 생성 (TM/DM/IM PPTX)"},
        {"name": "Financial Models", "description": "재무모델 생성 (DCF/LBO/COMPS/PROJECTION/FULL Excel)"},
        {"name": "LDD Reports", "description": "법률실사(LDD) 보고서 생성 (DDRL 체크리스트 → .docx)"},
        {"name": "Meeting Logs", "description": "마케팅/협상 미팅 로그"},
        {"name": "Negotiation Issues", "description": "협상 이견 추적 — 다자 입장 + AI 조항 제안"},
        {"name": "Contract Markups", "description": "계약 마크업 버전 관리 (파일 업로드)"},
        {"name": "VDR", "description": "VDR (Virtual Data Room) — 실사 자료실"},
        {"name": "Deal Clients", "description": "외부 고객 딜 접근 배정 관리"},
        {"name": "Permits", "description": "인허가 분석 — 업종별 인허가 자동 분석 및 기한 관리"},
    {"name": "Transcription", "description": "녹음 변환 — 오디오 업로드 + Clova STT + LLM 회의록 자동 생성"},
        {"name": "RFI", "description": "RFI (Request for Information) — 정보 요청 관리, Excel 가져오기/내보내기, 체크리스트 연동"},
    ],
)

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

# 요청/응답 JSON 로깅 미들웨어
setup_request_logging(app)

# Exception handlers
register_exception_handlers(app)

# ── Routers ─────────────────────────────────────────────
from app.routers import (  # noqa: E402
    approvals,
    audit,
    bids,
    buyers,
    client_portal,
    closing,
    compliance,
    contract_markups,
    contracts,
    dashboard,
    dd_checklists,
    deal_clients,
    earnout,
    engagements,
    financial_models,
    integrations,
    ldd_reports,
    legal_documents,
    marketing_materials,
    meeting_logs,
    ndas,
    negotiation_issues,
    notes,
    permits,
    pmi,
    ralph,
    rfi,
    risks,
    timeline,
    transactions,
    transcription,
    vdr,
    vdr_internal,
    vdr_overview,
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
app.include_router(notes.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")
app.include_router(risks.router, prefix="/api/v1")
app.include_router(compliance.router, prefix="/api/v1")
app.include_router(integrations.router, prefix="/api/v1")
app.include_router(timeline.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(legal_documents.router, prefix="/api/v1")
app.include_router(marketing_materials.router, prefix="/api/v1")
app.include_router(financial_models.router, prefix="/api/v1")
app.include_router(ldd_reports.router, prefix="/api/v1")
app.include_router(ldd_reports._default_sections_router, prefix="/api/v1")
app.include_router(ralph.router, prefix="/api/v1")
app.include_router(vdr.router, prefix="/api/v1")
app.include_router(vdr_overview.router, prefix="/api/v1")
app.include_router(deal_clients.router, prefix="/api/v1")
app.include_router(deal_clients.admin_router, prefix="/api/v1")
app.include_router(meeting_logs.router, prefix="/api/v1")
app.include_router(negotiation_issues.router, prefix="/api/v1")
app.include_router(contract_markups.router, prefix="/api/v1")
app.include_router(permits.router, prefix="/api/v1")
app.include_router(permits.kb_router, prefix="/api/v1")
app.include_router(client_portal.router, prefix="/api/v1")
app.include_router(transcription.router, prefix="/api/v1")
app.include_router(rfi.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(vdr_internal.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    result = {"status": "ok", "service": "deal-mgmt", "migration_ok": _migration_ok}
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
