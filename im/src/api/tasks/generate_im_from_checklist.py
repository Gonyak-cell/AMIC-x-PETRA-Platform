"""체크리스트 기반 IM 생성 Celery 태스크.

> 마지막 수정: 2026-03-13 17:21:37

사용자가 확정한 체크리스트를 기반으로 IM 문서(PPTX)를 생성한다.

단계:
  1. 확정된 체크리스트 → IMDocumentData 변환 (ChecklistToIMDataConverter)
  2. NarrativeOrchestrator.generate() (LLM 내러티브) — 선택적 (LLM 불가 시 스킵)
  3. IMPipeline.generate() (PPTX 생성)
  4. Document 업데이트 (pptx_path, status=COMPLETED)
"""

from __future__ import annotations

import logging
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Any

from src.api.tasks.base_task import PipelineTask
from src.api.tasks.celery_app import celery_app
from src.api.tasks.progress import update_progress

logger = logging.getLogger(__name__)


def _get_sync_engine() -> Any:
    """동기 SQLAlchemy 엔진을 생성한다."""
    from sqlalchemy import create_engine

    from src.api.config import get_config

    config = get_config()
    sync_url = config.database_url.replace("+asyncpg", "")
    return create_engine(sync_url, pool_pre_ping=True)


@celery_app.task(
    bind=True,
    name="generate_im_from_checklist",
    base=PipelineTask,
    max_retries=1,
    acks_late=True,
    soft_time_limit=600,
    time_limit=660,
)
def generate_im_from_checklist_task(
    self: Any,
    document_id: str,
    checklist_id: str,
) -> dict[str, Any]:
    """확정된 체크리스트를 기반으로 IM 문서를 생성한다.

    Args:
        document_id: IM Document UUID 문자열.
        checklist_id: IMChecklist UUID 문자열.

    Returns:
        생성 결과 dict (document_id, status, pptx_path).

    Raises:
        ValueError: 체크리스트가 없거나 상태가 올바르지 않을 때.
        self.retry: 재시도 가능한 오류 시.
    """
    from sqlalchemy import select, update
    from sqlalchemy.orm import Session, selectinload

    from src.api.db.models.document import Document
    from src.api.db.models.im_checklist import ChecklistStatus, IMChecklist
    from src.api.services.checklist_to_imdata import ChecklistToIMDataConverter

    update_progress(self, document_id, "GENERATING", 5)

    engine = _get_sync_engine()

    try:
        # ------------------------------------------------------------------
        # Step 1: DB에서 체크리스트 + 아이템 로드
        # ------------------------------------------------------------------
        with Session(engine) as session:
            stmt = (
                select(IMChecklist)
                .options(selectinload(IMChecklist.items))
                .where(IMChecklist.id == uuid_mod.UUID(checklist_id))
            )
            checklist = session.execute(stmt).scalar_one_or_none()

            if checklist is None:
                raise ValueError(f"IMChecklist not found: {checklist_id}")

            if checklist.status != ChecklistStatus.CONFIRMED.value:
                logger.warning(
                    "체크리스트가 CONFIRMED 상태가 아님: status=%s (계속 진행)",
                    checklist.status,
                )

            # 체크리스트 상태 → GENERATING
            checklist.status = ChecklistStatus.GENERATING.value
            session.commit()

            # 아이템 dict 변환 (세션 밖에서도 사용하기 위해)
            checklist_items: list[dict[str, Any]] = []
            for item in checklist.items:
                checklist_items.append(
                    {
                        "category": item.category,
                        "field_key": item.field_key,
                        "field_type": item.field_type,
                        "effective_value": item.effective_value,
                        "confirmed_value": item.confirmed_value,
                        "extracted_value": item.extracted_value,
                        "fiscal_year": item.fiscal_year,
                        "unit": item.unit,
                    }
                )

            # Document에서 설정 정보 조회
            doc = session.get(Document, uuid_mod.UUID(document_id))
            if doc is None:
                raise ValueError(f"Document not found: {document_id}")

            doc_config = {
                "project_name": doc.project_name or "",
                "company_name": doc.company_name,
                "corp_code": doc.corp_code or "",
                "im_style": doc.im_style or "FULL",
                "industry": (doc.generation_config or {}).get("industry", ""),
                "company_name_en": (doc.generation_config or {}).get(
                    "company_name_en", ""
                ),
            }

        update_progress(self, document_id, "GENERATING", 15)

        # ------------------------------------------------------------------
        # Step 2: 체크리스트 → IMDocumentData 변환
        # ------------------------------------------------------------------
        converter = ChecklistToIMDataConverter()
        im_data = converter.convert(checklist_items, config=doc_config)

        update_progress(self, document_id, "GENERATING", 30)

        # ------------------------------------------------------------------
        # Step 3: 내러티브 생성 (선택적 — LLM 불가 시 스킵)
        # ------------------------------------------------------------------
        try:
            from src.narrative_generator.engine.orchestrator import (
                NarrativeOrchestrator,
            )

            orchestrator = NarrativeOrchestrator()
            narrative_result = orchestrator.generate(
                im_data,
                industry=im_data.industry,
            )
            im_data.narratives = narrative_result.narratives

            logger.info(
                "내러티브 생성 완료: %d개 섹션, %d 경고",
                len(narrative_result.narratives),
                len(narrative_result.warnings),
            )
        except Exception as exc:
            logger.warning(
                "내러티브 생성 스킵 (LLM 불가 또는 오류): %s",
                exc,
            )
            # 내러티브 없이 계속 진행 — PPTX는 데이터만으로도 생성 가능

        update_progress(self, document_id, "RENDERING", 50)

        # ------------------------------------------------------------------
        # Step 4: PPTX 생성
        # ------------------------------------------------------------------
        from src.api.tasks.output_utils import (
            compute_im_output_dir,
            compute_im_pptx_path,
        )
        from src.design_renderer.pipeline import IMPipeline

        output_dir = compute_im_output_dir(document_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        pptx_path = compute_im_pptx_path(document_id)

        pipeline = IMPipeline()
        pipeline_result = pipeline.generate(im_data, pptx_path=str(pptx_path))

        update_progress(self, document_id, "RENDERING", 85)

        if not pipeline_result.success:
            logger.warning(
                "PPTX 생성 일부 실패: %d 에러, %d 경고",
                len(pipeline_result.errors),
                len(pipeline_result.warnings),
            )

        pptx_path_str = str(pptx_path) if pptx_path.exists() else None

        # ------------------------------------------------------------------
        # Step 4.5: 품질 게이트 실행
        # ------------------------------------------------------------------
        from src.api.tasks.generate_im import _run_im_quality_gate

        quality_kwargs = _run_im_quality_gate(pptx_path_str, document_id)
        gate_metrics = quality_kwargs.pop("_gate_metrics", {})

        # ------------------------------------------------------------------
        # Step 5: DB 업데이트 (Document + Checklist)
        # ------------------------------------------------------------------
        render_ms = int(pipeline_result.elapsed_seconds * 1000)
        gate_ms = gate_metrics.get("gate_ms", 0)
        stage_details: dict[str, Any] = {
            "render_ms": render_ms,
            "generation_ms": render_ms,  # FE 하위 호환
            "pipeline_slides": pipeline_result.total_pptx_slides,
            "pipeline_errors": len(pipeline_result.errors),
            "pipeline_warnings": len(pipeline_result.warnings),
            "narrative_sections": len(im_data.narratives),
            "sections_rendered": len(pipeline_result.successful_sections),
            "sections_failed": len(pipeline_result.failed_sections),
        }
        stage_details.update(gate_metrics)
        stage_details["total_ms"] = render_ms + gate_ms

        checklist_final_status = (
            "QUALITY_FAILED"
            if quality_kwargs.get("quality_status") == "FAIL"
            else "COMPLETED"
        )
        doc_values: dict[str, Any] = {
            "pptx_path": pptx_path_str,
            "status": checklist_final_status,
            "progress_pct": 100,
            "completed_at": datetime.now(timezone.utc),
            "stage_details": stage_details,
            **quality_kwargs,
        }

        with Session(engine) as session:
            # Document 업데이트
            session.execute(
                update(Document)
                .where(Document.id == uuid_mod.UUID(document_id))
                .values(**doc_values)
            )

            # Checklist 상태 → COMPLETED
            session.execute(
                update(IMChecklist)
                .where(IMChecklist.id == uuid_mod.UUID(checklist_id))
                .values(status=ChecklistStatus.COMPLETED.value)
            )

            session.commit()

        update_progress(self, document_id, checklist_final_status, 100)

        # Ralph Loop Pass 2 (Final) — 체크리스트 기반 최종 품질 보증
        if pptx_path_str:
            try:
                from src.api.tasks.ralph_loop import run_im_ralph_loop_task

                from src.api.tasks.serializers import im_data_to_dict

                run_im_ralph_loop_task.delay(
                    document_id=document_id,
                    pass_number=2,
                    im_data_dict=im_data_to_dict(im_data),
                )
                logger.info("Ralph Loop Pass 2 시작: document=%s", document_id)
            except Exception as exc:
                logger.warning("Ralph Loop 체이닝 실패 (비필수): %s", exc)

        logger.info(
            "IM 생성 완료: document=%s, pptx=%s, slides=%d",
            document_id,
            pptx_path_str,
            pipeline_result.total_pptx_slides,
        )

        return {
            "document_id": document_id,
            "checklist_id": checklist_id,
            "status": "COMPLETED",
            "pptx_path": pptx_path_str,
            "total_slides": pipeline_result.total_pptx_slides,
            "errors": pipeline_result.errors,
            "warnings": pipeline_result.warnings[:10],  # 최대 10개만
        }

    except ValueError:
        # 체크리스트/문서 not found — 재시도 불필요
        _mark_checklist_failed(engine, checklist_id, document_id)
        raise
    except Exception as exc:
        logger.error(
            "IM 생성 실패: document=%s checklist=%s — %s",
            document_id,
            checklist_id,
            exc,
        )
        if self.request.retries >= self.max_retries:
            _mark_checklist_failed(engine, checklist_id, document_id)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        engine.dispose()


def _mark_checklist_failed(
    engine: Any,
    checklist_id: str,
    document_id: str,
) -> None:
    """체크리스트와 문서를 FAILED 상태로 전환한다.

    Args:
        engine: SQLAlchemy 엔진.
        checklist_id: 체크리스트 ID.
        document_id: 문서 ID.
    """
    try:
        from sqlalchemy import update
        from sqlalchemy.orm import Session

        from src.api.db.models.document import Document
        from src.api.db.models.im_checklist import ChecklistStatus, IMChecklist

        with Session(engine) as session:
            session.execute(
                update(IMChecklist)
                .where(IMChecklist.id == uuid_mod.UUID(checklist_id))
                .values(status=ChecklistStatus.FAILED.value)
            )
            session.execute(
                update(Document)
                .where(Document.id == uuid_mod.UUID(document_id))
                .values(
                    status="FAILED",
                    stage_details={"error": "IM generation from checklist failed"},
                )
            )
            session.commit()
    except Exception:
        logger.exception(
            "FAILED 상태 전환 실패: checklist=%s document=%s",
            checklist_id,
            document_id,
        )
