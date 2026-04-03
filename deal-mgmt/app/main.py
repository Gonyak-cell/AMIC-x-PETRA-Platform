import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update
from starlette.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.log_middleware import setup_request_logging
from app.core.logging import setup_logging

# 구조화 로깅 초기화 (통일 JSON 로그 스키마)
setup_logging(level="INFO", json_output=not settings.DEBUG, service_name="deal-mgmt", log_dir=settings.LOG_DIR or None)
logger = logging.getLogger(__name__)

_STALE_THRESHOLD_MINUTES = 10


async def _bootstrap_local_sqlite_schema_for_startup(
    *,
    database_url: str | None = None,
    engine_override=None,
    metadata=None,
    allowed_roots=None,
):
    from app.core.database import engine as default_engine
    from app.core.local_dev_schema_guard import (
        LOCAL_DEV_ENTRYPOINT_HINT,
        configure_sqlite_type_compilers_for_local_dev,
        guard_local_sqlite_database_url,
    )
    from app.models import Base

    effective_database_url = database_url or settings.DATABASE_URL
    guard_result = guard_local_sqlite_database_url(
        effective_database_url,
        allowed_roots=allowed_roots,
        logger=logger,
    )
    if guard_result.database_path is None:
        return guard_result

    configure_sqlite_type_compilers_for_local_dev()

    active_engine = engine_override or default_engine
    active_metadata = metadata or Base.metadata
    async with active_engine.begin() as conn:
        await conn.run_sync(active_metadata.create_all)

    if guard_result.rebuilt:
        logger.warning(
            "Local SQLite dev database was rebuilt during app startup: %s. %s",
            guard_result.database_path,
            LOCAL_DEV_ENTRYPOINT_HINT,
        )

    return guard_result


async def _bootstrap_attachment_processing_schema_for_startup(
    *,
    database_url: str | None = None,
    engine_override=None,
):
    from app.core.local_dev_schema_guard import repair_attachment_upload_schema_if_needed

    effective_database_url = database_url or settings.DATABASE_URL
    repair_result = await repair_attachment_upload_schema_if_needed(
        database_url=effective_database_url,
        engine_override=engine_override,
        logger=logger,
    )
    if repair_result.repaired:
        logger.warning(
            "Backend uploaded marketing material schema was repaired during app startup: %s",
            ", ".join(repair_result.qualified_missing_columns),
        )
    elif repair_result.repair_attempted and repair_result.issues:
        logger.warning(
            "Uploaded marketing material schema is still missing after startup repair: %s",
            ", ".join(repair_result.qualified_missing_columns),
        )
    return repair_result


async def _cleanup_stale_extractions() -> None:
    """서버 시작 시 CLASSIFYING/EXTRACTING 상태로 방치된 extraction을 FAILED로 전환."""
    try:
        from app.core.database import async_session_factory
        from app.models.document_extraction import DocumentExtraction
        from app.models.enums import ExtractionStatus

        async with async_session_factory() as db:
            stale_cutoff = datetime.now(UTC) - timedelta(minutes=_STALE_THRESHOLD_MINUTES)
            result = await db.execute(
                update(DocumentExtraction)
                .where(
                    DocumentExtraction.status.in_([ExtractionStatus.CLASSIFYING, ExtractionStatus.EXTRACTING]),
                    DocumentExtraction.updated_at < stale_cutoff,
                )
                .values(
                    status=ExtractionStatus.FAILED,
                    error_message="서버 재시작으로 중단됨. 다시 시도해주세요.",
                )
            )
            if result.rowcount:
                await db.commit()
                logger.info("stale extraction %d건 FAILED 처리 완료", result.rowcount)
    except Exception:
        logger.exception("stale extraction 정리 실패")


# 마이그레이션 상태 추적 — health check에서 참조
_migration_ok: bool = True  # deploy.yml에서 마이그레이션 관리


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _bootstrap_local_sqlite_schema_for_startup()
    await _bootstrap_attachment_processing_schema_for_startup()

    # JWT secret validation is handled at import time in core/config.py
    # (raises RuntimeError if ENV=production and using dev secret)

    # Azure Blob Storage 초기화 (VDR 파일 스토리지)
    from app.core.blob_storage import blob_client

    await blob_client.init()

    # Redis 초기화 (뉴스 피드 캐싱 등)
    from app.core.redis import init_redis

    await init_redis()

    # Stale extraction 정리 — 서버 재시작 시 CLASSIFYING/EXTRACTING 상태로 방치된 레코드 복구
    await _cleanup_stale_extractions()

    # 마케팅 자료 템플릿 사전 검증 (서버 시작 차단 안 함)
    try:
        from app.pptx.memo_generator import validate_template

        template_warnings = validate_template()
        for w in template_warnings:
            logger.warning("Template preflight: %s", w)
    except Exception:
        logger.exception("Template preflight 검증 실패 (서버 시작에 영향 없음)")

    try:
        from app.ralph.parsers.pdf_parser import get_pdf_ocr_status

        ocr_status = get_pdf_ocr_status()
        if ocr_status["enabled"] and not ocr_status["available"]:
            logger.warning("PDF OCR runtime unavailable: %s", ocr_status["reason"])
    except Exception:
        logger.exception("PDF OCR runtime 상태 점검 실패")

    # 마이그레이션은 deploy.yml에서 관리 (중복 실행 방지)
    logger.info("Deal Management application started")
    yield
    # Shutdown
    await blob_client.close()

    # Redis 종료
    from app.core.redis import close_redis

    await close_redis()

    from app.core.dependencies import close_all_clients

    await close_all_clients()
    logger.info("Deal Management application stopped")


app = FastAPI(
    title=settings.APP_NAME,
    description="M&A Deal Management Service — 9단계 거래 워크플로우 관리 시스템",
    version="0.15.3",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "서비스 상태 확인"},
        {"name": "Transactions", "description": "M&A 거래 관리"},
        {"name": "Workflow", "description": "9단계 워크플로우 상태 머신"},
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
        {"name": "Evidence", "description": "워크스트림 공통 evidence traceability 조회"},
        {"name": "Meeting Logs", "description": "마케팅/협상 미팅 로그"},
        {"name": "Negotiation Issues", "description": "협상 이견 추적 — 다자 입장 + AI 조항 제안"},
        {"name": "Contract Markups", "description": "계약 마크업 버전 관리 (파일 업로드)"},
        {"name": "VDR", "description": "VDR (Virtual Data Room) — 실사 자료실"},
        {"name": "Deal Clients", "description": "외부 고객 딜 접근 배정 관리"},
        {"name": "Permits", "description": "인허가 분석 — 업종별 인허가 자동 분석 및 기한 관리"},
        {"name": "Transcription", "description": "녹음 변환 — 오디오 업로드 + Clova STT + LLM 회의록 자동 생성"},
        {
            "name": "RFI",
            "description": "RFI V2 — 질의 원장 + 스레드 이력, 동적 Excel, 퍼지 매칭 파일 매핑, 보고서 브릿지",
        },
        {
            "name": "Document Extraction",
            "description": "문서 AI 추출 — VDR 문서 자동 분류 + 핵심 데이터 추출 (NDA/LOI/SPA/등기부등본/세무신고서)",
        },
        {
            "name": "Document Versions",
            "description": "문서 버전 관리 — SHA-256 중복 차단 + 리비전 이력 추적",
        },
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
    expose_headers=["Content-Disposition", "X-Issues-Count", "X-Skipped-Count"],
    max_age=3600,
)

# 요청/응답 JSON 로깅 미들웨어
setup_request_logging(app)

# Exception handlers
register_exception_handlers(app)

# ── Routers ─────────────────────────────────────────────
from app.routers import (
    admin_settings,
    approvals,
    attachments,
    audit,
    bids,
    buyer_marketing,
    buyers,
    client_portal,
    closing,
    compliance,
    consortium,
    contract_generation,
    contract_markups,
    contracts,
    dashboard,
    dd_checklists,
    deal_clients,
    deal_setup,
    dev_auth,
    document_extraction,
    document_versions,
    earnout,
    engagements,
    evidence,
    financial_models,
    integrations,
    ldd_reports,
    legal_documents,
    marketing_materials,
    meeting_logs,
    nda_markups,
    ndas,
    negotiation_issues,
    news_feed,
    notes,
    pef_registry,
    permits,
    pmi,
    ralph,
    rfi_v2,
    risks,
    si_mapping,
    spa_analysis,
    template_visualization,
    timeline,
    transactions,
    transcription,
    vdr,
    vdr_access,
    vdr_internal,
    vdr_overview,
    vdr_upload,
    workflow,
)

app.include_router(dev_auth.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(workflow.router, prefix="/api/v1")
app.include_router(engagements.router, prefix="/api/v1")
# buyer_marketing을 buyers보다 먼저 등록 — /buyers/dart-search, /buyers/export-excel
# 경로가 buyers의 /buyers/{buyer_id} UUID 파라미터와 충돌하기 때문
app.include_router(buyer_marketing.router, prefix="/api/v1")
app.include_router(buyers.router, prefix="/api/v1")
app.include_router(consortium.router, prefix="/api/v1")
app.include_router(ndas.router, prefix="/api/v1")
app.include_router(nda_markups.router, prefix="/api/v1")
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
app.include_router(contract_generation.router, prefix="/api/v1")
app.include_router(marketing_materials.router, prefix="/api/v1")
app.include_router(financial_models.router, prefix="/api/v1")
app.include_router(ldd_reports.router, prefix="/api/v1")
app.include_router(ldd_reports._default_sections_router, prefix="/api/v1")
app.include_router(evidence.router, prefix="/api/v1")
app.include_router(ralph.router, prefix="/api/v1")
# vdr_upload, vdr_access를 vdr보다 먼저 등록 — /documents/classification-status,
# /access-logs 등 고정 경로가 vdr의 /documents/{doc_id} 와일드카드보다 먼저 매칭되어야 함
app.include_router(vdr_upload.router, prefix="/api/v1")
app.include_router(vdr_access.router, prefix="/api/v1")
app.include_router(vdr.router, prefix="/api/v1")
app.include_router(vdr_overview.router, prefix="/api/v1")
app.include_router(deal_clients.router, prefix="/api/v1")
app.include_router(deal_clients.admin_router, prefix="/api/v1")
app.include_router(meeting_logs.router, prefix="/api/v1")
app.include_router(negotiation_issues.router, prefix="/api/v1")
app.include_router(contract_markups.router, prefix="/api/v1")
app.include_router(document_versions.router, prefix="/api/v1")
app.include_router(permits.router, prefix="/api/v1")
app.include_router(permits.kb_router, prefix="/api/v1")
app.include_router(client_portal.router, prefix="/api/v1")
app.include_router(transcription.router, prefix="/api/v1")
app.include_router(rfi_v2.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(vdr_internal.router, prefix="/api/v1")
app.include_router(document_extraction.router, prefix="/api/v1")
app.include_router(attachments.router, prefix="/api/v1")
app.include_router(template_visualization.router, prefix="/api/v1")
app.include_router(si_mapping.router, prefix="/api/v1")
app.include_router(admin_settings.router, prefix="/api/v1")
app.include_router(pef_registry.router, prefix="/api/v1")
app.include_router(spa_analysis.router, prefix="/api/v1")
app.include_router(deal_setup.router, prefix="/api/v1")
app.include_router(news_feed.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    result = {"status": "ok", "service": "deal-mgmt", "migration_ok": _migration_ok}
    try:
        from app.ralph.parsers.pdf_parser import get_pdf_ocr_status

        result["ocr"] = get_pdf_ocr_status()
        if result["ocr"]["required"] and not result["ocr"]["available"]:
            result["status"] = "degraded"
    except Exception as exc:
        logger.error("Health check OCR status failed: %s", exc)
        result["ocr"] = {"enabled": False, "available": False, "required": False, "reason": str(exc)}

    try:
        from sqlalchemy import text

        from app.core.database import async_session_factory

        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        result["db"] = "ok"
    except Exception as exc:
        logger.error("Health check DB 연결 실패: %s", exc)
        result["status"] = "degraded"
        result["db"] = "error"

    try:
        from app.core.database import async_session_factory
        from app.core.local_dev_schema_guard import probe_attachment_upload_schema

        schema_engine = getattr(async_session_factory, "kw", {}).get("bind")
        schema_result = await probe_attachment_upload_schema(
            engine_override=schema_engine,
            logger=logger,
        )
        result["attachment_upload_schema_ok"] = schema_result.ok
        result["attachment_upload_schema"] = {
            "ok": schema_result.ok,
            "issues": [
                {
                    "table": issue.table,
                    "column": issue.column,
                    "reason": issue.reason,
                    "repairable": issue.repairable,
                }
                for issue in schema_result.issues
            ],
        }
        if not schema_result.ok:
            result["status"] = "degraded"
    except Exception as exc:
        logger.error("Health check attachment upload schema probe failed: %s", exc)
        result["status"] = "degraded"
        result["attachment_upload_schema_ok"] = False
        result["attachment_upload_schema"] = {
            "ok": False,
            "error": str(exc),
            "issues": [],
        }
    return result
