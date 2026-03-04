"""IM Ralph Loop Celery 태스크.

IM PPTX 디자인/시각화 품질을 반복 개선한다.
Pass 1 (Draft): 초기 생성 직후 → 디자인 평가 → 개선
Pass 2 (Final): 체크리스트 확인 후 재생성 → 최종 품질 보증
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import uuid as uuid_mod
from typing import Any

from src.api.tasks.base_task import PipelineTask
from src.api.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """Celery 워커에서 코루틴을 안전하게 실행한다."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()


def _get_sync_engine() -> Any:
    """동기 SQLAlchemy 엔진을 생성한다."""
    from sqlalchemy import create_engine

    from src.api.config import get_config

    config = get_config()
    sync_url = config.database_url.replace("+asyncpg", "")
    return create_engine(sync_url, pool_pre_ping=True)


@celery_app.task(
    bind=True,
    name="run_im_ralph_loop",
    base=PipelineTask,
    max_retries=0,
    acks_late=True,
    soft_time_limit=600,
    time_limit=660,
)
def run_im_ralph_loop_task(
    self: Any,
    document_id: str,
    pass_number: int = 1,
    config_override: dict | None = None,
    im_data_dict: dict | None = None,
) -> dict[str, Any]:
    """IM PPTX에 Ralph Loop 품질 개선을 적용한다.

    Args:
        document_id: IM Document UUID 문자열.
        pass_number: 1=Draft, 2=Final.
        config_override: LoopConfig 오버라이드.
        im_data_dict: IMDocumentData 직렬화 dict (Celery 체인에서 전달).

    Returns:
        세션 결과 dict.
    """
    from sqlalchemy import update
    from sqlalchemy.orm import Session

    from src.api.config import get_config
    from src.api.db.models.document import Document
    from src.api.db.models.im_ralph_session import IMRalphSession

    api_config = get_config()
    engine = _get_sync_engine()
    session_id = None

    try:
        # 1. Document 조회 + im_style → doc_type 매핑
        with Session(engine) as session:
            doc = session.get(Document, uuid_mod.UUID(document_id))
            if doc is None:
                raise ValueError(f"Document not found: {document_id}")

            pptx_path = doc.pptx_path
            from src.ralph.doc_type_resolver import resolve_doc_type

            im_style = doc.im_style or "FULL"
            doc_type = resolve_doc_type(im_style)
            company_name = doc.company_name
            generation_config = doc.generation_config or {}

        # im_data_dict가 없으면 최소 데이터 구성 (수동 트리거 시)
        if not im_data_dict:
            im_data_dict = {
                "company_name_kr": company_name,
                "project_name": getattr(doc, "project_name", "") or "",
                "corp_code": getattr(doc, "corp_code", "") or "",
                "im_style": im_style,
                "industry": generation_config.get("industry", ""),
            }

        if not pptx_path:
            logger.warning(
                "Ralph Loop 스킵: PPTX 파일이 없음 (document=%s)", document_id
            )
            return {
                "document_id": document_id,
                "status": "SKIPPED",
                "reason": "no_pptx_path",
            }

        # 2. IMRalphSession 생성
        session_id = uuid_mod.uuid4()

        with Session(engine) as session:
            ralph_session = IMRalphSession(
                id=session_id,
                document_id=uuid_mod.UUID(document_id),
                pass_number=pass_number,
                doc_type=doc_type,
                status="GENERATING",
            )
            session.add(ralph_session)
            session.commit()

        # 3. Ralph Loop 실행
        result = _run_async(
            _execute_ralph_loop(
                document_id=document_id,
                session_id=str(session_id),
                pptx_path=pptx_path,
                doc_type=doc_type,
                pass_number=pass_number,
                api_config=api_config,
                config_override=config_override,
                im_data_dict=im_data_dict,
            )
        )

        # 4. 세션 업데이트
        with Session(engine) as session:
            session.execute(
                update(IMRalphSession)
                .where(IMRalphSession.id == session_id)
                .values(
                    status="COMPLETED" if result["success"] else "FAILED",
                    total_iterations=result.get("total_iterations", 0),
                    total_cost_usd=result.get("total_cost_usd", 0.0),
                    final_score=result.get("final_score", 0.0),
                    section_scores=result.get("section_scores"),
                    progress=result.get("progress"),
                    output_path=result.get("output_path"),
                    error_message=result.get("error")
                    if not result["success"]
                    else None,
                    critical_flags=result.get("critical_flags"),
                    learned_patterns=result.get("learned_patterns"),
                )
            )
            session.commit()

        # 5. 개선된 PPTX 경로가 있으면 Document 업데이트
        if result["success"] and result.get("output_path"):
            with Session(engine) as session:
                session.execute(
                    update(Document)
                    .where(Document.id == uuid_mod.UUID(document_id))
                    .values(pptx_path=result["output_path"])
                )
                session.commit()

        logger.info(
            "IM Ralph Loop 완료: document=%s pass=%d score=%.2f iterations=%d cost=$%.4f",
            document_id,
            pass_number,
            result.get("final_score", 0.0),
            result.get("total_iterations", 0),
            result.get("total_cost_usd", 0.0),
        )

        return {
            "document_id": document_id,
            "session_id": str(session_id),
            "status": "COMPLETED" if result["success"] else "FAILED",
            "final_score": result.get("final_score", 0.0),
            "total_iterations": result.get("total_iterations", 0),
            "total_cost_usd": result.get("total_cost_usd", 0.0),
        }

    except Exception as exc:
        logger.error("IM Ralph Loop 실패: document=%s — %s", document_id, exc)

        # 세션을 FAILED로 업데이트
        if session_id is not None:
            try:
                with Session(engine) as session:
                    session.execute(
                        update(IMRalphSession)
                        .where(IMRalphSession.id == session_id)
                        .values(
                            status="FAILED",
                            error_message=str(exc),
                        )
                    )
                    session.commit()
            except Exception:
                logger.exception("Ralph 세션 FAILED 업데이트 실패")

        return {
            "document_id": document_id,
            "status": "FAILED",
            "error": str(exc),
        }
    finally:
        engine.dispose()


async def _execute_ralph_loop(
    document_id: str,
    session_id: str,
    pptx_path: str,
    doc_type: str,
    pass_number: int,
    api_config: Any,
    config_override: dict | None = None,
    im_data_dict: dict | None = None,
) -> dict[str, Any]:
    """Ralph Loop 오케스트레이터를 실행한다."""
    from src.ralph.convergence import ConvergenceConfig
    from src.ralph.gates.im_design_judge import IMLLMDesignJudge
    from src.ralph.gates.im_pptx_gate import IMPPTXProgrammaticGate
    from src.ralph.gates.im_vision_gate import IMVisionGate
    from src.ralph.im_generator import IMDocumentGenerator
    from src.ralph.llm_client import RalphLLMClient
    from src.ralph.orchestrator import LoopConfig, RalphLoopOrchestrator
    from src.ralph.prd import get_prd

    # PRD 로드
    prd = get_prd(doc_type)

    # LLM 클라이언트
    llm_client = RalphLLMClient.from_config(api_config)

    # 게이트 구성
    gates = [IMPPTXProgrammaticGate()]

    openai_key = getattr(api_config, "openai_api_key", "")
    if openai_key and getattr(api_config, "ralph_vision_enabled", True):
        gates.append(IMVisionGate(openai_api_key=openai_key, max_slides=6))

    if llm_client.is_available:
        gates.append(IMLLMDesignJudge(llm_call=llm_client.call))

    # LoopConfig (Bug 2: ConvergenceConfig 분리)
    convergence = ConvergenceConfig(
        max_iterations_per_section=getattr(api_config, "ralph_max_iterations", 3),
        pass_threshold=getattr(api_config, "ralph_pass_threshold", 4.0),
        max_cost_usd=getattr(api_config, "ralph_budget_per_pass", 5.0),
    )
    loop_config = LoopConfig(convergence=convergence)

    if config_override:
        for key, value in config_override.items():
            if hasattr(convergence, key):
                setattr(convergence, key, value)
            elif hasattr(loop_config, key):
                setattr(loop_config, key, value)

    # Generator (Bug 1: im_data_dict 전달)
    generator = IMDocumentGenerator(
        im_data_dict=im_data_dict or {},
        output_dir=getattr(api_config, "output_dir", ""),
    )

    # Orchestrator (Bug 3: prd 파라미터 추가)
    orchestrator = RalphLoopOrchestrator(
        generator=generator,
        gates=gates,
        prd=prd,
        config=loop_config,
    )

    # 소스 데이터 구성
    source_data = {
        "document_id": document_id,
        "pptx_path": pptx_path,
    }

    # 실행 (Bug 4: run() 시그니처 수정)
    result = await orchestrator.run(source_data)

    return {
        "success": result.final_score >= loop_config.convergence.pass_threshold,
        "final_score": result.final_score,
        "total_iterations": result.total_iterations,
        "total_cost_usd": llm_client.total_cost_usd,
        "section_scores": result.section_scores,
        "progress": result.progress if result.progress else None,
        "output_path": result.output_path,
        "critical_flags": result.critical_flags,
        "learned_patterns": None,
    }
