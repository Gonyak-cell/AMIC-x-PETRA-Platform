"""Ralph Loop API 라우터 — 세션 관리, 진행 상황, 결과 조회."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims, require_write_access
from app.models.enums import AuditAction
from app.models.ralph_session import RalphSession, RalphSessionStatus
from app.schemas.ralph import RalphProgressOut, RalphSessionCreate, RalphSessionOut
from app.services import audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ralph", tags=["ralph-loop"])


# ── 백그라운드 루프 실행 ─────────────────────────────────────────────────────


async def _run_ralph_loop(
    session_id: uuid.UUID,
    body: RalphSessionCreate,
) -> None:
    """백그라운드에서 Ralph Loop를 실행하고 세션 상태를 업데이트한다.

    독립적인 DB 세션을 생성하여 요청 생명주기와 분리한다.
    """
    from app.core.database import async_session_factory
    from app.ralph.convergence import ConvergenceConfig
    from app.ralph.llm_client import RalphLLMClient
    from app.ralph.orchestrator import LoopConfig, RalphLoopOrchestrator
    from app.ralph.prd_manager import load_prd

    async with async_session_factory() as db:
        session = await db.get(RalphSession, session_id)
        if not session:
            return

        try:
            session.status = RalphSessionStatus.GENERATING
            await db.commit()

            # 1. LLM 클라이언트 생성
            llm_client = RalphLLMClient.from_settings(settings)
            llm_call = llm_client.call if llm_client.is_available else None

            # 1.5. 학습 패턴 조회 (과거 세션에서 축적된 이슈/베스트 프랙티스)
            learned_patterns: list[str] = []
            try:
                from app.ralph.learning.pattern_aggregator import PatternAggregator

                agg = PatternAggregator(db)
                learned_patterns = await agg.get_learned_patterns(body.doc_type)
                if learned_patterns:
                    logger.info("Ralph Loop: %d개 학습 패턴 로드됨", len(learned_patterns))
            except Exception as exc:
                logger.warning("학습 패턴 조회 실패 (무시): %s", exc)

            # 2. Generator + Gates 조립
            generator, gates = _build_pipeline(
                body.doc_type,
                llm_call,
                body.source_dir,
                learned_patterns=learned_patterns,
            )

            # 3. PRD 로드
            prd = load_prd(body.doc_type)

            # 4. Orchestrator 설정 + 실행
            config = LoopConfig(
                convergence=ConvergenceConfig(
                    max_iterations_per_section=body.max_iterations_per_section,
                    max_cost_usd=body.max_cost_usd,
                    pass_threshold=body.pass_threshold,
                ),
            )
            orchestrator = RalphLoopOrchestrator(
                generator=generator,
                gates=gates,
                prd=prd,
                config=config,
            )

            result = await orchestrator.run(
                source_data={"source_dir": body.source_dir or ""},
            )

            # 5. 결과 저장
            session.status = result.status.value
            session.final_score = result.final_score
            session.total_iterations = result.total_iterations
            session.total_cost_usd = result.total_cost_usd + (llm_client.total_cost_usd if llm_call else 0)
            session.section_scores = result.section_scores
            session.progress = result.progress
            session.output_path = result.output_path
            session.critical_flags = result.critical_flags or None

            if result.errors:
                session.error_message = "; ".join(result.errors)

            await db.commit()
            logger.info("Ralph Loop 완료: session=%s, score=%.2f", session_id, result.final_score)

        except Exception as exc:
            logger.exception("Ralph Loop 실패: session=%s", session_id)
            session.status = RalphSessionStatus.FAILED
            session.error_message = str(exc)
            await db.commit()


def _build_pipeline(
    doc_type: str,
    llm_call,
    source_dir: str | None = None,
    learned_patterns: list[str] | None = None,
):
    """문서 유형에 따라 Generator + Gates를 조립한다."""
    from app.ralph.gates.llm_judge_gate import LLMJudgeGate

    gates = []

    if doc_type.lower().startswith("ldd"):
        from app.ralph.gates.docx_gate import DOCXProgrammaticGate
        from app.ralph.generators.ldd.section_analyzer import LDDDocumentGenerator, LDDSectionAnalyzer
        from app.ralph.parsers.base import ParsedFile
        from app.ralph.parsers.file_classifier import parse_and_classify, scan_directory
        from app.schemas.ldd_report import DEFAULT_LDD_SECTIONS

        # 파서 + 분류 (경로 검증: 프로젝트 루트 내부만 허용)
        source_map: dict[str, list[ParsedFile]] = {}
        if source_dir:
            _ralph_project_root = Path(__file__).resolve().parent.parent.parent
            try:
                resolved = Path(source_dir).resolve()
                resolved.relative_to(_ralph_project_root)
            except (ValueError, OSError) as exc:
                raise ValueError(f"source_dir은 프로젝트 디렉토리 내부여야 합니다: {source_dir}") from exc
            for file_info in scan_directory(source_dir):
                parsed = parse_and_classify(file_info["path"])
                for section in parsed.ddrl_sections:
                    source_map.setdefault(section, []).append(parsed)

        analyzer = LDDSectionAnalyzer(llm_call=llm_call, learned_patterns=learned_patterns)
        generator = LDDDocumentGenerator(analyzer, DEFAULT_LDD_SECTIONS)
        generator.set_source_map(source_map)

        gates.append(DOCXProgrammaticGate())
        if llm_call:
            gates.append(LLMJudgeGate(llm_provider=llm_call, doc_type="ldd"))

    else:
        # PPTX (TM/DM/IM)
        from app.ralph.gates.pptx_gate import PPTXProgrammaticGate
        from app.ralph.generators.pptx_generator import RalphMemoGenerator

        generator = RalphMemoGenerator(memo_type=doc_type.upper(), llm_call=llm_call)
        gates.append(PPTXProgrammaticGate())
        if llm_call:
            gates.append(LLMJudgeGate(llm_provider=llm_call, doc_type="pptx"))

    return generator, gates


# ── 세션 목록 조회 ────────────────────────────────────────────────────────────


@router.get(
    "/transactions/{transaction_id}/sessions",
    response_model=list[RalphSessionOut],
)
async def list_ralph_sessions(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[RalphSessionOut]:
    """거래에 속한 Ralph Loop 세션 목록을 조회한다."""
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")
    q = (
        select(RalphSession)
        .where(RalphSession.transaction_id == transaction_id)
        .order_by(RalphSession.created_at.desc())
    )
    result = await db.execute(q)
    return [RalphSessionOut.model_validate(s) for s in result.scalars().all()]


# ── 세션 상세 조회 ────────────────────────────────────────────────────────────


@router.get(
    "/sessions/{session_id}",
    response_model=RalphSessionOut,
)
async def get_ralph_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> RalphSessionOut:
    """Ralph Loop 세션 상세 정보를 조회한다."""
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")
    q = select(RalphSession).where(RalphSession.id == session_id)
    result = await db.execute(q)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Ralph Loop 세션을 찾을 수 없습니다.")
    # 거래 소유권 검증 — session이 속한 거래에 대한 접근 권한 확인
    from app.services import transaction_service

    txn = await transaction_service.get_transaction(db, session.transaction_id)
    if claims.role != "ADMIN" and claims.email not in (txn.lead_advisor_email, txn.deal_captain_email):
        raise HTTPException(status_code=403, detail="이 세션에 접근할 권한이 없습니다")
    return RalphSessionOut.model_validate(session)


# ── 진행 상황 조회 (폴링용) ───────────────────────────────────────────────────


@router.get(
    "/sessions/{session_id}/progress",
    response_model=RalphProgressOut,
)
async def get_ralph_progress(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> RalphProgressOut:
    """Ralph Loop 실시간 진행 상황을 조회한다."""
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")
    q = select(RalphSession).where(RalphSession.id == session_id)
    result = await db.execute(q)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Ralph Loop 세션을 찾을 수 없습니다.")
    # 거래 소유권 검증
    from app.services import transaction_service

    txn = await transaction_service.get_transaction(db, session.transaction_id)
    if claims.role != "ADMIN" and claims.email not in (txn.lead_advisor_email, txn.deal_captain_email):
        raise HTTPException(status_code=403, detail="이 세션에 접근할 권한이 없습니다")

    progress_data = session.progress or {}

    return RalphProgressOut(
        session_id=session.id,
        status=session.status,
        total_iterations=session.total_iterations,
        total_cost_usd=session.total_cost_usd,
        passed_sections=progress_data.get("passed_sections", []),
        section_scores=session.section_scores or {},
    )


# ── 세션 생성 (Ralph Loop 시작) ───────────────────────────────────────────────


@router.post(
    "/transactions/{transaction_id}/sessions",
    response_model=RalphSessionOut,
    status_code=202,
)
async def create_ralph_session(
    transaction_id: uuid.UUID,
    body: RalphSessionCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> RalphSessionOut:
    """Ralph Loop 세션을 생성하고 비동기 실행을 시작한다."""
    if claims.role == "CLIENT":
        raise HTTPException(status_code=403, detail="클라이언트는 이 기능에 접근할 수 없습니다")
    # 동일 거래+문서유형에 활성 세션이 있으면 409
    existing_q = (
        select(RalphSession)
        .where(
            RalphSession.transaction_id == transaction_id,
            RalphSession.doc_type == body.doc_type,
            RalphSession.status.in_(
                [
                    RalphSessionStatus.PLANNING,
                    RalphSessionStatus.GENERATING,
                ]
            ),
        )
        .limit(1)
    )
    existing = (await db.execute(existing_q)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"이 거래에 이미 진행 중인 Ralph Loop 세션이 있습니다 (id={existing.id})",
        )

    session = RalphSession(
        transaction_id=transaction_id,
        doc_type=body.doc_type,
        status=RalphSessionStatus.PLANNING,
        config={
            "max_iterations_per_section": body.max_iterations_per_section,
            "max_cost_usd": body.max_cost_usd,
            "pass_threshold": body.pass_threshold,
        },
    )
    db.add(session)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="RalphSession",
        entity_id=session.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value={"doc_type": body.doc_type, "transaction_id": transaction_id},
    )
    await db.commit()
    await db.refresh(session)

    # Celery 태스크로 Ralph Loop 실행
    from app.tasks.ralph_tasks import run_ralph_loop_task

    run_ralph_loop_task.delay(
        session_id=str(session.id),
        body_dict=body.model_dump(mode="json"),
    )

    return RalphSessionOut.model_validate(session)
