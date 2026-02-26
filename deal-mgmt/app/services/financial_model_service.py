"""Financial Model Service — CRUD + VDR 추출 + 체크리스트 자동 생성 + Excel 생성."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentNotFoundError
from app.models.enums import (
    FinancialModelStatus,
    FinancialModelType,
    FMChecklistCategory,
    FMChecklistItemStatus,
    FMChecklistStatus,
)
from app.models.financial_model import FinancialModel, FMChecklist, FMChecklistItem
from app.schemas.financial_model import FinancialModelCreate

# 상태 전이 불가 상태 (진행 중인 작업이 있음)
_BUSY_STATUSES = frozenset({FinancialModelStatus.GENERATING, FinancialModelStatus.FINALIZING})

logger = logging.getLogger(__name__)

FM_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "generated" / "financial_models"
FM_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# error_message 잘림 길이 통일
MAX_ERROR_LEN = 1000

# ── 체크리스트 필드 레지스트리 (카테고리별 기본 항목) ──────────────────────


FM_FIELD_REGISTRY: list[dict] = [
    # Revenue & Growth
    {"category": FMChecklistCategory.REVENUE_FORECAST, "title": "매출액 실적 (최근 3~5년)", "field_type": "currency", "unit": "KRW", "severity": "HIGH"},
    {"category": FMChecklistCategory.REVENUE_FORECAST, "title": "세그먼트별 매출 비중", "field_type": "percentage", "unit": "%", "severity": "MEDIUM"},
    {"category": FMChecklistCategory.GROWTH_ASSUMPTIONS, "title": "매출 성장률 가정 (향후 5년)", "field_type": "percentage", "unit": "%", "severity": "HIGH"},
    {"category": FMChecklistCategory.GROWTH_ASSUMPTIONS, "title": "시장 성장률 참조치", "field_type": "percentage", "unit": "%", "severity": "MEDIUM"},
    {"category": FMChecklistCategory.VOLUME_PRICE_MIX, "title": "물량 성장 vs 단가 상승 구분", "field_type": "text", "unit": None, "severity": "MEDIUM"},
    # Cost Structure
    {"category": FMChecklistCategory.COGS_FORECAST, "title": "매출원가율 실적/가정", "field_type": "percentage", "unit": "%", "severity": "HIGH"},
    {"category": FMChecklistCategory.COGS_FORECAST, "title": "원재료비 비중 및 추세", "field_type": "percentage", "unit": "%", "severity": "MEDIUM"},
    {"category": FMChecklistCategory.SGA_FORECAST, "title": "판관비율 실적/가정", "field_type": "percentage", "unit": "%", "severity": "HIGH"},
    {"category": FMChecklistCategory.SGA_FORECAST, "title": "인건비 비중", "field_type": "percentage", "unit": "%", "severity": "MEDIUM"},
    {"category": FMChecklistCategory.DEPRECIATION_AMORT, "title": "감가상각비 추정 방법", "field_type": "text", "unit": None, "severity": "MEDIUM"},
    {"category": FMChecklistCategory.CAPEX_FORECAST, "title": "CAPEX 가정 (매출 대비 %)", "field_type": "percentage", "unit": "%", "severity": "HIGH"},
    # Working Capital & Cash Flow
    {"category": FMChecklistCategory.NWC_ASSUMPTIONS, "title": "매출채권 회전일수 (DSO)", "field_type": "number", "unit": "일", "severity": "MEDIUM"},
    {"category": FMChecklistCategory.NWC_ASSUMPTIONS, "title": "재고자산 회전일수 (DIO)", "field_type": "number", "unit": "일", "severity": "MEDIUM"},
    {"category": FMChecklistCategory.NWC_ASSUMPTIONS, "title": "매입채무 회전일수 (DPO)", "field_type": "number", "unit": "일", "severity": "MEDIUM"},
    {"category": FMChecklistCategory.FCF_DERIVATION, "title": "Free Cash Flow 도출 방식", "field_type": "text", "unit": None, "severity": "HIGH"},
    # Capital Structure & WACC
    {"category": FMChecklistCategory.FM_DEBT_SCHEDULE, "title": "차입금 구조 (이자율, 만기)", "field_type": "text", "unit": None, "severity": "HIGH"},
    {"category": FMChecklistCategory.WACC_COMPONENTS, "title": "무위험이자율 (Rf)", "field_type": "percentage", "unit": "%", "severity": "HIGH"},
    {"category": FMChecklistCategory.WACC_COMPONENTS, "title": "시장리스크프리미엄 (MRP)", "field_type": "percentage", "unit": "%", "severity": "HIGH"},
    {"category": FMChecklistCategory.WACC_COMPONENTS, "title": "Beta (Unlevered / Levered)", "field_type": "number", "unit": "x", "severity": "HIGH"},
    {"category": FMChecklistCategory.WACC_COMPONENTS, "title": "세전 타인자본비용 (Kd pre-tax)", "field_type": "percentage", "unit": "%", "severity": "HIGH"},
    {"category": FMChecklistCategory.WACC_COMPONENTS, "title": "자기자본비용 (Ke)", "field_type": "percentage", "unit": "%", "severity": "HIGH"},
    {"category": FMChecklistCategory.WACC_COMPONENTS, "title": "목표 자본구조 (D/E)", "field_type": "percentage", "unit": "%", "severity": "MEDIUM"},
    {"category": FMChecklistCategory.TAX_RATE, "title": "유효법인세율 가정", "field_type": "percentage", "unit": "%", "severity": "HIGH"},
    # Valuation
    {"category": FMChecklistCategory.DCF_PARAMETERS, "title": "Terminal Growth Rate", "field_type": "percentage", "unit": "%", "severity": "HIGH"},
    {"category": FMChecklistCategory.DCF_PARAMETERS, "title": "Exit Multiple (EV/EBITDA)", "field_type": "number", "unit": "x", "severity": "HIGH"},
    {"category": FMChecklistCategory.TRADING_MULTIPLES, "title": "비교기업 리스트 (GPCM)", "field_type": "text", "unit": None, "severity": "HIGH"},
    {"category": FMChecklistCategory.TRADING_MULTIPLES, "title": "적용 멀티플 (EV/EBITDA median)", "field_type": "number", "unit": "x", "severity": "HIGH"},
    {"category": FMChecklistCategory.TRANSACTION_MULTIPLES, "title": "선례거래 리스트 (GTM)", "field_type": "text", "unit": None, "severity": "MEDIUM"},
    {"category": FMChecklistCategory.TRANSACTION_MULTIPLES, "title": "적용 멀티플 (GTM median)", "field_type": "number", "unit": "x", "severity": "MEDIUM"},
    # Scenarios & Sensitivity
    {"category": FMChecklistCategory.BASE_SCENARIO, "title": "Base Case 핵심 파라미터 요약", "field_type": "text", "unit": None, "severity": "HIGH"},
    {"category": FMChecklistCategory.UPSIDE_SCENARIO, "title": "Upside Case 주요 차이점", "field_type": "text", "unit": None, "severity": "MEDIUM"},
    {"category": FMChecklistCategory.DOWNSIDE_SCENARIO, "title": "Downside Case 주요 차이점", "field_type": "text", "unit": None, "severity": "MEDIUM"},
    {"category": FMChecklistCategory.SENSITIVITY_MATRIX, "title": "민감도 분석 축 (WACC × Exit Multiple)", "field_type": "text", "unit": None, "severity": "MEDIUM"},
]


# ── CRUD ──────────────────────────────────────────────────────────────────


async def list_financial_models(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[FinancialModel]:
    """거래의 재무모델 목록을 조회한다."""
    stmt = (
        select(FinancialModel)
        .where(FinancialModel.transaction_id == transaction_id)
        .order_by(FinancialModel.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_financial_model(
    db: AsyncSession,
    fm_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> FinancialModel:
    """재무모델을 조회한다."""
    stmt = (
        select(FinancialModel)
        .where(FinancialModel.id == fm_id, FinancialModel.transaction_id == transaction_id)
    )
    fm = (await db.execute(stmt)).scalar_one_or_none()
    if fm is None:
        raise DocumentNotFoundError(f"FinancialModel {fm_id}")
    return fm


async def create_financial_model(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: FinancialModelCreate,
    actor_email: str,
) -> FinancialModel:
    """재무모델을 생성하고, VDR 기반 체크리스트를 자동 생성한다."""
    fm = FinancialModel(
        transaction_id=transaction_id,
        model_type=body.model_type,
        title=body.title,
        parameters=body.parameters,
        vdr_document_ids=body.vdr_document_ids,
        status=FinancialModelStatus.GENERATING,
        created_by_email=actor_email,
    )
    db.add(fm)
    await db.flush()

    # 체크리스트 자동 생성 (필드 레지스트리 기반)
    checklist = FMChecklist(
        financial_model_id=fm.id,
        status=FMChecklistStatus.PENDING_REVIEW,
    )
    db.add(checklist)
    await db.flush()

    for idx, field_def in enumerate(FM_FIELD_REGISTRY):
        item = FMChecklistItem(
            checklist_id=checklist.id,
            category=field_def["category"],
            order_index=idx,
            title=field_def["title"],
            description=f'{field_def["title"]} — 자동 추출 또는 사용자 입력 필요',
            field_type=field_def["field_type"],
            unit=field_def["unit"],
            severity=field_def["severity"],
            status=FMChecklistItemStatus.AUTO_GENERATED,
        )
        db.add(item)

    # 상태를 PENDING_REVIEW로 전환 (VDR 추출은 백그라운드)
    fm.status = FinancialModelStatus.PENDING_REVIEW
    await db.commit()
    await db.refresh(fm)

    # VDR 추출 + Ralph Loop Pass 1은 Celery 태스크로 실행
    if body.vdr_document_ids and body.enable_ralph_loop:
        from app.tasks.fm_tasks import run_vdr_extraction_and_ralph_task

        run_vdr_extraction_and_ralph_task.delay(
            fm_id=str(fm.id),
            transaction_id=str(transaction_id),
            vdr_document_ids=body.vdr_document_ids,
            model_type=body.model_type,
            ralph_max_iterations=body.ralph_max_iterations,
            ralph_max_cost_usd=body.ralph_max_cost_usd,
        )

    return fm


async def delete_financial_model(
    db: AsyncSession,
    fm_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> None:
    """재무모델을 삭제한다."""
    fm = await get_financial_model(db, fm_id, transaction_id)
    await db.delete(fm)
    await db.commit()


async def regenerate_financial_model(
    db: AsyncSession,
    fm_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> FinancialModel:
    """재무모델을 재생성한다.

    GENERATING/FINALIZING 상태에서는 재생성 불가 (진행 중인 태스크와 충돌 방지).
    """
    fm = await get_financial_model(db, fm_id, transaction_id)

    if fm.status in _BUSY_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot regenerate: model is currently {fm.status.value}",
        )

    fm.status = FinancialModelStatus.GENERATING
    fm.version += 1
    fm.error_message = None
    fm.file_path = None
    fm.file_name = None
    fm.file_size_bytes = None
    fm.ralph_score = None
    await db.commit()
    await db.refresh(fm)

    # VDR 기반 Ralph Loop 재실행 트리거
    if fm.vdr_document_ids:
        from app.tasks.fm_tasks import run_vdr_extraction_and_ralph_task

        run_vdr_extraction_and_ralph_task.delay(
            fm_id=str(fm.id),
            transaction_id=str(transaction_id),
            vdr_document_ids=fm.vdr_document_ids,
            model_type=fm.model_type,
        )
    else:
        # VDR 없으면 즉시 PENDING_REVIEW
        fm.status = FinancialModelStatus.PENDING_REVIEW
        await db.commit()
        await db.refresh(fm)

    return fm


# ── Background Tasks ─────────────────────────────────────────────────────


async def _run_vdr_extraction_and_ralph(
    fm_id: uuid.UUID,
    transaction_id: uuid.UUID,
    vdr_document_ids: list[str],
    model_type: FinancialModelType,
    ralph_max_iterations: int = 2,
    ralph_max_cost_usd: float = 15.0,
) -> None:
    """VDR 문서에서 재무 데이터를 추출하고 Ralph Loop Pass 1로 초안 Excel을 생성한다."""
    from app.core.database import async_session_factory
    from app.ralph.convergence import ConvergenceConfig
    from app.ralph.gates.excel_gate import ExcelProgrammaticGate
    from app.ralph.gates.llm_judge_gate import LLMJudgeGate
    from app.ralph.generators.excel_generator import RalphExcelGenerator
    from app.ralph.orchestrator import LoopConfig, RalphLoopOrchestrator
    from app.ralph.prd_manager import load_prd
    from app.services.fm_checklist_service import FMChecklistService

    logger.info(
        "Background: VDR extraction + Ralph Pass 1 for FM %s (txn=%s, vdr_docs=%d, type=%s)",
        fm_id, transaction_id, len(vdr_document_ids), model_type,
    )

    try:
        async with async_session_factory() as db:
            fm = await get_financial_model(db, fm_id, transaction_id)

            # 멱등성 가드: 이미 완료/실패 또는 다른 단계 진행 중이면 스킵
            if fm.status not in (
                FinancialModelStatus.GENERATING,
                FinancialModelStatus.PENDING_REVIEW,
            ):
                logger.warning(
                    "FM %s skipping Pass 1: unexpected status %s",
                    fm_id, fm.status,
                )
                return

            # 1. 체크리스트에서 auto_value 추출
            svc = FMChecklistService(db)
            checklist = await svc.get_checklist(fm_id)
            checklist_values: dict[str, str] = {}
            for item in checklist.items:
                if item.auto_value:
                    checklist_values[item.title] = item.auto_value

            # 2. Ralph Loop 구성
            generator: RalphExcelGenerator | None = None
            generator = RalphExcelGenerator(
                model_type=fm.model_type,
                title=fm.title,
                checklist_values=checklist_values,
                parameters=fm.parameters,
            )
            gates = [
                ExcelProgrammaticGate(),
                LLMJudgeGate(doc_type="excel"),  # LLM 미연결 시 fallback 사용
            ]
            prd = load_prd("financial_model")
            config = LoopConfig(
                convergence=ConvergenceConfig(
                    max_iterations_per_section=ralph_max_iterations,
                    max_cost_usd=ralph_max_cost_usd,
                ),
                output_dir=str(FM_OUTPUT_DIR / str(transaction_id)),
            )

            # 3. Ralph Loop Pass 1 실행
            orchestrator = RalphLoopOrchestrator(generator, gates, prd, config)
            result = await orchestrator.run({"checklist_values": checklist_values})

            # 4. FM 상태 업데이트
            fm.ralph_session_id = result.session_id
            fm.ralph_score = result.final_score
            fm.status = FinancialModelStatus.PENDING_REVIEW
            if result.output_path:
                fm.file_path = result.output_path
                fm.file_name = Path(result.output_path).name
            await db.commit()

            logger.info(
                "FM %s Ralph Pass 1 완료: score=%.2f, iterations=%d",
                fm_id, result.final_score, result.total_iterations,
            )

    except Exception as e:
        logger.error("FM %s Ralph Pass 1 FAILED: %s", fm_id, e, exc_info=True)
        # 에러 시에도 PENDING_REVIEW로 전환 (체크리스트 리뷰는 가능)
        try:
            async with async_session_factory() as db:
                fm = await get_financial_model(db, fm_id, transaction_id)
                fm.status = FinancialModelStatus.PENDING_REVIEW
                fm.error_message = f"Ralph Pass 1 실패 (체크리스트 리뷰 가능): {str(e)[:MAX_ERROR_LEN]}"
                await db.commit()
        except Exception:
            logger.error("Failed to update FM status after Ralph Pass 1 failure", exc_info=True)
    finally:
        if generator is not None:
            generator.cleanup()


async def run_finalize_and_generate(
    fm_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> None:
    """Finalize → Ralph Loop Pass 2 → 최종 Excel 생성.

    체크리스트 confirmed_value(user_value 우선) 기반으로
    Ralph Loop Pass 2를 실행하고, FinancialModel 상태를 READY로 전환한다.
    Ralph Loop 실패 시 직접 FinancialModelBuilder로 fallback 생성.
    """
    from app.core.database import async_session_factory
    from app.ralph.convergence import ConvergenceConfig
    from app.ralph.gates.excel_gate import ExcelProgrammaticGate
    from app.ralph.gates.llm_judge_gate import LLMJudgeGate
    from app.ralph.generators.excel_generator import RalphExcelGenerator
    from app.ralph.orchestrator import LoopConfig, RalphLoopOrchestrator
    from app.ralph.prd_manager import load_prd
    from app.services.fm_checklist_service import FMChecklistService

    logger.info(
        "Background: Finalize + Ralph Pass 2 for FM %s (txn=%s)",
        fm_id,
        transaction_id,
    )

    try:
        async with async_session_factory() as db:
            fm = await get_financial_model(db, fm_id, transaction_id)

            # 멱등성 가드: FINALIZING 상태가 아니면 스킵
            if fm.status != FinancialModelStatus.FINALIZING:
                logger.warning(
                    "FM %s skipping Pass 2: expected FINALIZING, got %s",
                    fm_id, fm.status,
                )
                return

            svc = FMChecklistService(db)
            checklist = await svc.get_checklist(fm_id)

            # 체크리스트 항목에서 confirmed 값 추출 (user_value 우선)
            checklist_values: dict[str, str] = {}
            for item in checklist.items:
                val = item.user_value or item.auto_value or ""
                if val:
                    checklist_values[item.title] = val

            file_name = f"{fm.title.replace(' ', '_')}_v{fm.version}.xlsx"
            output_dir = str(FM_OUTPUT_DIR / str(transaction_id))

            # Ralph Loop Pass 2 (최종)
            generator: RalphExcelGenerator | None = None
            generator = RalphExcelGenerator(
                model_type=fm.model_type,
                title=fm.title,
                checklist_values=checklist_values,
                parameters=fm.parameters,
            )
            gates = [
                ExcelProgrammaticGate(),
                LLMJudgeGate(doc_type="excel"),
            ]
            prd = load_prd("financial_model")
            config = LoopConfig(
                convergence=ConvergenceConfig(
                    max_iterations_per_section=3,
                    max_cost_usd=20.0,
                ),
                output_dir=output_dir,
            )

            orchestrator = RalphLoopOrchestrator(generator, gates, prd, config)
            result = await orchestrator.run({"checklist_values": checklist_values})

            # 최종 파일 경로 결정
            output_path = result.output_path
            if not output_path:
                # Ralph Loop 실패 시 직접 빌드 (fallback)
                from app.excel.model_builder import FinancialModelBuilder

                logger.warning("FM %s Ralph Pass 2 output 없음 — fallback 빌드", fm_id)
                path = Path(output_dir) / file_name
                path.parent.mkdir(parents=True, exist_ok=True)
                builder = FinancialModelBuilder(
                    model_type=fm.model_type,
                    title=fm.title,
                    checklist_values=checklist_values,
                    parameters=fm.parameters,
                )
                output_path = str(builder.save(path))

            # FM 상태 업데이트
            fm.status = FinancialModelStatus.READY
            fm.file_path = output_path
            fm.file_name = file_name
            fm.file_size_bytes = Path(output_path).stat().st_size
            fm.ralph_score = result.final_score
            fm.error_message = None
            await db.commit()

            logger.info(
                "FM %s finalized: %s (%.1f KB, score=%.2f)",
                fm_id, file_name,
                fm.file_size_bytes / 1024,
                result.final_score,
            )

    except Exception as e:
        logger.error("FM %s finalize FAILED: %s", fm_id, e, exc_info=True)
        try:
            async with async_session_factory() as db:
                fm = await get_financial_model(db, fm_id, transaction_id)
                fm.status = FinancialModelStatus.FAILED
                fm.error_message = str(e)[:MAX_ERROR_LEN]
                await db.commit()
        except Exception:
            logger.error("Failed to update FM status to FAILED", exc_info=True)
    finally:
        if generator is not None:
            generator.cleanup()
