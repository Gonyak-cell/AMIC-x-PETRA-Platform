"""마케팅 자료 서비스 — memo_generator 기반 PPTX 생성 및 CRUD."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import DocumentNotFoundError
from app.models.enums import MarketingDocStatus, MarketingDocType, MarketingMaterialSourceMode
from app.models.marketing_material import MarketingMaterial
from app.schemas.marketing_material import DistributionUpdate, MarketingMaterialCreate
from app.services.text_extraction_service import TextExtractionService
from app.services.vdr_routing_service import get_routing_override_map
from app.services.workstream_router_service import (
    COMMON_WORKSTREAM,
    FDD_WORKSTREAM,
    VALUATION_WORKSTREAM,
    build_workstream_routing_summary,
    is_source_allowed_for_any_workstream,
    route_vdr_sources,
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "generated" / "memorandum"
logger = logging.getLogger(__name__)


async def _run_quality_gate(
    mat: MarketingMaterial,
    output_path: Path,
    memo_type: str,
    generation_ms: int | None = None,
    *,
    template_load_ms: int = 0,
    render_ms: int = 0,
    persist_ms: int = 0,
) -> None:
    """품질 게이트를 실행하고 mat 필드를 갱신한다.

    게이트 예외 시 fail-closed(FAILED + FAIL) 처리한다.
    """
    import time as _time

    _gate_t0 = _time.monotonic()
    _gate_ms: int = 0

    try:
        from app.ralph.gates.pptx_gate import PPTXProgrammaticGate

        gate = PPTXProgrammaticGate()
        gate_result = await gate.evaluate(
            str(output_path),
            prd_section={"memo_type": memo_type.upper()},
        )
        _gate_ms = int((_time.monotonic() - _gate_t0) * 1000)

        mat.quality_score = gate_result.weighted_score
        mat.quality_issues = [str(i) for i in gate_result.issues]

        # slide_count: PPTX 직접 파싱
        try:
            from pptx import Presentation as _Prs

            _prs = _Prs(str(output_path))
            mat.slide_count = len(_prs.slides)
        except Exception:
            mat.slide_count = None

        if gate_result.critical_flags:
            mat.status = MarketingDocStatus.FAILED
            mat.quality_status = "FAIL"
            mat.error_message = f"품질 게이트 미통과: {gate_result.critical_flags}"
        else:
            if gate_result.weighted_score >= 3.5:
                mat.status = MarketingDocStatus.READY
                mat.quality_status = "PASS"
            else:
                mat.status = MarketingDocStatus.CONDITIONAL_READY
                mat.quality_status = "CONDITIONAL"
    except Exception as gate_exc:
        import logging as _logging

        _gate_ms = int((_time.monotonic() - _gate_t0) * 1000)
        _logging.getLogger(__name__).warning("품질 게이트 실행 실패 (mat=%s): %s", mat.id, gate_exc)
        mat.status = MarketingDocStatus.FAILED
        mat.quality_status = "FAIL"
        mat.error_message = "품질 게이트 실행 중 내부 오류가 발생했습니다"

    # 성능 메트릭을 parameters에 병합
    metrics: dict[str, int] = {
        "template_load_ms": template_load_ms,
        "render_ms": render_ms,
        "gate_ms": _gate_ms,
        "persist_ms": persist_ms,
    }
    if generation_ms is not None:
        metrics["generation_ms"] = generation_ms
        metrics["total_ms"] = generation_ms + _gate_ms
    if mat.slide_count is not None:
        metrics["slide_count"] = mat.slide_count
    if mat.parameters:
        mat.parameters = {**mat.parameters, "_metrics": metrics}
    else:
        mat.parameters = {"_metrics": metrics}


# ── doc_type → memo_generator 유형 매핑 ─────────────────────────
_TYPE_MAP: dict[MarketingDocType, str] = {
    MarketingDocType.TM: "tm",
    MarketingDocType.DM: "dm",
    MarketingDocType.IM: "im",
}

_MARKETING_DOC_TARGET_WORKSTREAMS: dict[MarketingDocType, tuple[str, ...]] = {
    MarketingDocType.TM: (COMMON_WORKSTREAM, VALUATION_WORKSTREAM),
    MarketingDocType.DM: (COMMON_WORKSTREAM, VALUATION_WORKSTREAM),
    MarketingDocType.IM: (COMMON_WORKSTREAM, VALUATION_WORKSTREAM, FDD_WORKSTREAM),
}


def _validate_prerequisites(body: MarketingMaterialCreate) -> list[str]:
    """Celery 태스크 진입 전 필수 요소를 검증하여 누락 사유를 반환한다."""
    errors: list[str] = []
    if not body.title or not body.title.strip():
        errors.append("title이 비어 있습니다")
    if body.doc_type not in _TYPE_MAP:
        errors.append(f"지원하지 않는 doc_type입니다: {body.doc_type.value}")
    return errors


def _get_marketing_material_target_workstreams(doc_type: MarketingDocType) -> tuple[str, ...]:
    return _MARKETING_DOC_TARGET_WORKSTREAMS.get(
        doc_type,
        (COMMON_WORKSTREAM, VALUATION_WORKSTREAM),
    )


def _build_marketing_material_source_routing(
    routed_sources: list,
    target_workstreams: tuple[str, ...],
) -> dict:
    summary = build_workstream_routing_summary(routed_sources)
    included_ids = {
        str(routed.source.vdr_document_id)
        for routed in routed_sources
        if is_source_allowed_for_any_workstream(routed, target_workstreams)
    }
    summary["summary"]["target_workstreams"] = list(target_workstreams)
    summary["summary"]["included_for_marketing_material"] = len(included_ids)
    summary["summary"]["excluded_from_marketing_material"] = len(routed_sources) - len(included_ids)
    for document in summary["documents"]:
        document["include_for_marketing_material"] = document["document_id"] in included_ids
    return summary


async def preview_marketing_material_source_routing(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    doc_type: MarketingDocType,
) -> dict:
    target_workstreams = _get_marketing_material_target_workstreams(doc_type)
    source_files = await TextExtractionService().extract_from_vdr_documents(
        db,
        transaction_id,
        use_cache_only=True,
    )
    if not source_files:
        return _build_marketing_material_source_routing([], target_workstreams)

    document_ids = [source.vdr_document_id for source in source_files]
    routing_overrides = await get_routing_override_map(
        db,
        transaction_id,
        document_ids=document_ids,
    )
    routed_sources = route_vdr_sources(source_files, overrides=routing_overrides)
    return _build_marketing_material_source_routing(routed_sources, target_workstreams)


# ── CRUD ─────────────────────────────────────────────────────────


async def list_marketing_materials(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[MarketingMaterial]:
    q = (
        select(MarketingMaterial)
        .where(MarketingMaterial.transaction_id == transaction_id)
        .order_by(MarketingMaterial.created_at.desc())
    )
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_marketing_material(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    mat_id: uuid.UUID,
) -> MarketingMaterial:
    q = select(MarketingMaterial).where(
        MarketingMaterial.id == mat_id,
        MarketingMaterial.transaction_id == transaction_id,
    )
    result = await db.execute(q)
    mat = result.scalar_one_or_none()
    if not mat:
        raise DocumentNotFoundError("마케팅 자료를 찾을 수 없습니다.")
    return mat


async def create_marketing_material(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: MarketingMaterialCreate,
    created_by_email: str | None = None,
) -> MarketingMaterial:
    """마케팅 자료 레코드를 생성하고 PPTX 생성을 비동기로 트리거한다."""
    from fastapi import HTTPException
    from fastapi import status as http_status

    errors = _validate_prerequisites(body)
    if errors:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": errors},
        )

    if body.attachment_id:
        return await _create_uploaded_marketing_material(
            db,
            transaction_id,
            body,
            created_by_email=created_by_email,
        )

    mat = MarketingMaterial(
        transaction_id=transaction_id,
        doc_type=body.doc_type,
        title=body.title,
        project_code=body.project_code,
        status=MarketingDocStatus.GENERATING,
        source_mode=MarketingMaterialSourceMode.GENERATED.value,
        parameters=body.parameters,
        created_by_email=created_by_email,
    )
    db.add(mat)
    await db.commit()
    await db.refresh(mat)

    # PPTX 생성 — Celery 태스크로 실행
    from app.tasks.marketing_tasks import generate_pptx_task

    try:
        generate_pptx_task.delay(
            mat_id=str(mat.id),
            transaction_id=str(transaction_id),
            body_dict=body.model_dump(mode="json"),
        )
    except Exception:
        logger.exception(
            "Failed to enqueue marketing material generation task",
            extra={
                "transaction_id": str(transaction_id),
                "marketing_material_id": str(mat.id),
                "doc_type": body.doc_type.value,
            },
        )
        mat.status = MarketingDocStatus.FAILED
        mat.error_message = "작업 큐에 연결할 수 없어 생성 요청을 시작하지 못했습니다."
        await db.commit()
        await db.refresh(mat)

    return mat


async def _create_uploaded_marketing_material(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: MarketingMaterialCreate,
    *,
    created_by_email: str | None = None,
) -> MarketingMaterial:
    from app.models.attachment import Attachment

    attachment = await db.get(Attachment, body.attachment_id)
    if not attachment or attachment.transaction_id != transaction_id:
        raise DocumentNotFoundError("업로드한 마케팅 자료 첨부파일을 찾을 수 없습니다.")
    if attachment.entity_type != "MARKETING_MATERIAL":
        raise DocumentNotFoundError("마케팅 자료 첨부파일만 연결할 수 있습니다.")

    result = await db.execute(
        select(MarketingMaterial).where(
            MarketingMaterial.transaction_id == transaction_id,
            MarketingMaterial.attachment_id == attachment.id,
        )
    )
    mat = result.scalar_one_or_none()

    if mat is None:
        mat = MarketingMaterial(
            transaction_id=transaction_id,
            doc_type=body.doc_type,
            title=body.title,
            project_code=body.project_code,
            status=MarketingDocStatus.READY,
            source_mode=MarketingMaterialSourceMode.UPLOADED.value,
            attachment_id=attachment.id,
            parameters=body.parameters,
            file_path=attachment.file_path,
            file_name=attachment.file_name,
            file_size_bytes=attachment.file_size_bytes,
            quality_status="SKIPPED",
            created_by_email=created_by_email or attachment.uploaded_by_email,
        )
        db.add(mat)
    else:
        mat.doc_type = body.doc_type
        mat.title = body.title
        mat.project_code = body.project_code
        mat.status = MarketingDocStatus.READY
        mat.source_mode = MarketingMaterialSourceMode.UPLOADED.value
        mat.attachment_id = attachment.id
        mat.parameters = body.parameters
        mat.file_path = attachment.file_path
        mat.file_name = attachment.file_name
        mat.file_size_bytes = attachment.file_size_bytes
        mat.quality_status = "SKIPPED"
        mat.created_by_email = created_by_email or attachment.uploaded_by_email

    if body.distributed_to is not None:
        mat.distributed_to = body.distributed_to
        mat.distributed_at = body.distributed_at or (
            datetime.now(UTC).isoformat() if body.distributed_to else None
        )
    elif body.distributed_at is not None:
        mat.distributed_at = body.distributed_at

    await db.commit()
    await db.refresh(mat)
    return mat


async def _generate_pptx(
    mat_id: uuid.UUID,
    transaction_id: uuid.UUID,
    body: MarketingMaterialCreate,
    session_factory: async_sessionmaker,
) -> None:
    """백그라운드에서 PPTX를 생성하고 DB를 업데이트한다.

    요청 컨텍스트와 독립된 새 DB 세션을 사용한다.
    """
    import time as _time

    from app.pptx.memo_generator import generate_memo

    try:
        memo_type = _TYPE_MAP[body.doc_type]
        project_code = body.project_code or str(mat_id)[:8].upper()

        out_dir = OUTPUT_DIR / str(transaction_id)
        out_dir.mkdir(parents=True, exist_ok=True)

        output_path = out_dir / f"{memo_type}_{mat_id}.pptx"

        # Gate A: Template Preflight — 렌더링 전 템플릿 무결성 검증
        from app.pptx.memo_generator import TEMPLATE_PATH
        from app.pptx.template_spec import get_spec

        spec = get_spec(memo_type.upper())
        if spec:
            from app.ralph.gates.template_preflight import TemplatePreflight

            preflight = TemplatePreflight()
            preflight_result = await preflight.evaluate(
                str(TEMPLATE_PATH),
                prd_section={"memo_type": memo_type.upper()},
                source_data={"template_spec": spec},
            )
            if not preflight_result.passed:
                async with session_factory() as db:
                    q = select(MarketingMaterial).where(
                        MarketingMaterial.id == mat_id,
                    )
                    r = await db.execute(q)
                    mat = r.scalar_one_or_none()
                    if mat:
                        mat.status = MarketingDocStatus.FAILED
                        mat.quality_status = "FAIL"
                        mat.quality_issues = preflight_result.issues
                        mat.error_message = f"템플릿 프리플라이트 실패: {preflight_result.issues}"
                        await db.commit()
                return

        # 동기 함수를 스레드풀에서 실행 (python-pptx는 동기 IO)
        _t0 = _time.monotonic()
        result = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: generate_memo(
                memo_type=memo_type,
                project_code=project_code,
                output_path=str(output_path),
                content=body.parameters,
            ),
        )
        _generation_ms = int((_time.monotonic() - _t0) * 1000)

        # 독립적인 새 세션으로 DB 업데이트
        async with session_factory() as db:
            q = select(MarketingMaterial).where(MarketingMaterial.id == mat_id)
            r = await db.execute(q)
            mat = r.scalar_one_or_none()
            if mat:
                mat.file_path = result.output_path
                mat.file_name = result.file_name
                mat.file_size_bytes = result.file_size_bytes

                await _run_quality_gate(
                    mat,
                    output_path,
                    memo_type,
                    _generation_ms,
                    template_load_ms=result.template_load_ms,
                    render_ms=result.render_ms,
                    persist_ms=result.persist_ms,
                )

                await db.commit()

    except Exception as exc:
        async with session_factory() as db:
            q = select(MarketingMaterial).where(MarketingMaterial.id == mat_id)
            r = await db.execute(q)
            mat = r.scalar_one_or_none()
            if mat:
                import logging as _log

                _log.getLogger(__name__).error("PPTX 생성 실패 (mat=%s): %s", mat_id, exc)
                mat.status = MarketingDocStatus.FAILED
                mat.error_message = "PPTX 생성 중 내부 오류가 발생했습니다"
                await db.commit()


async def create_marketing_material_with_ralph(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: MarketingMaterialCreate,
    created_by_email: str | None = None,
) -> MarketingMaterial:
    """Ralph Loop 품질 강화 모드로 마케팅 자료를 생성한다."""
    from fastapi import HTTPException
    from fastapi import status as http_status

    errors = _validate_prerequisites(body)
    if errors:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": errors},
        )

    from app.ralph.convergence import ConvergenceConfig
    from app.ralph.gates.pptx_gate import PPTXProgrammaticGate
    from app.ralph.generators.pptx_generator import RalphMemoGenerator
    from app.ralph.orchestrator import RalphLoopOrchestrator
    from app.ralph.prd_manager import load_prd

    mat = MarketingMaterial(
        transaction_id=transaction_id,
        doc_type=body.doc_type,
        title=body.title,
        project_code=body.project_code,
        status=MarketingDocStatus.GENERATING,
        source_mode=MarketingMaterialSourceMode.GENERATED.value,
        parameters=body.parameters,
        created_by_email=created_by_email,
    )
    db.add(mat)
    await db.commit()
    await db.refresh(mat)

    try:
        memo_type = _TYPE_MAP[body.doc_type]
        project_code = body.project_code or str(mat.id)[:8].upper()

        generator = RalphMemoGenerator(
            memo_type=memo_type.upper(),
            project_code=project_code,
        )
        gates = [PPTXProgrammaticGate()]
        prd = load_prd(memo_type.upper())
        config = ConvergenceConfig(
            max_iterations_per_section=body.ralph_max_iterations,
            max_cost_usd=body.ralph_max_cost_usd,
        )

        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=gates,
            prd=prd,
            config=config,
        )
        loop_result = await orchestrator.run(source_data=body.parameters)

        if loop_result.final_artifact and Path(loop_result.final_artifact).exists():
            p = Path(loop_result.final_artifact)
            mat.file_path = str(p)
            mat.file_name = p.name
            mat.file_size_bytes = p.stat().st_size
            await _run_quality_gate(mat, p, memo_type)
        else:
            mat.status = MarketingDocStatus.FAILED
            mat.error_message = "Ralph Loop 완료 — 최종 산출물 파일이 생성되지 않았습니다"

    except Exception as exc:
        mat.status = MarketingDocStatus.FAILED
        mat.error_message = f"Ralph Loop 실패: {exc}"

    await db.commit()
    await db.refresh(mat)
    return mat


async def generate_marketing_material(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    mat_id: uuid.UUID,
) -> MarketingMaterial:
    """이미 생성된 자료를 재생성 (FAILED → GENERATING → READY)."""
    mat = await get_marketing_material(db, transaction_id, mat_id)
    if mat.source_mode == MarketingMaterialSourceMode.UPLOADED.value:
        raise DocumentNotFoundError("외부 업로드 자료는 재생성할 수 없습니다.")

    from app.pptx.memo_generator import generate_memo

    memo_type = _TYPE_MAP[mat.doc_type]
    project_code = mat.project_code or str(mat_id)[:8].upper()

    out_dir = OUTPUT_DIR / str(transaction_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{memo_type}_{mat_id}.pptx"

    mat.status = MarketingDocStatus.GENERATING
    mat.error_message = None
    mat.quality_score = None
    mat.quality_status = None
    mat.quality_issues = None
    mat.slide_count = None
    await db.commit()

    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: generate_memo(
                memo_type=memo_type,
                project_code=project_code,
                output_path=str(output_path),
                content=mat.parameters,
            ),
        )
        mat.file_path = result.output_path
        mat.file_name = result.file_name
        mat.file_size_bytes = result.file_size_bytes
        await _run_quality_gate(
            mat,
            output_path,
            memo_type,
            template_load_ms=result.template_load_ms,
            render_ms=result.render_ms,
            persist_ms=result.persist_ms,
        )
    except Exception as exc:
        import logging as _log

        _log.getLogger(__name__).error("재생성 실패 (mat=%s): %s", mat.id, exc)
        mat.status = MarketingDocStatus.FAILED
        mat.error_message = "PPTX 재생성 중 내부 오류가 발생했습니다"

    await db.commit()
    await db.refresh(mat)
    return mat


async def update_distribution(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    mat_id: uuid.UUID,
    body: DistributionUpdate,
) -> MarketingMaterial:
    """배포 대상 목록 갱신."""
    mat = await get_marketing_material(db, transaction_id, mat_id)

    if mat.status != MarketingDocStatus.READY or not mat.file_path:
        raise DocumentNotFoundError("배포하려면 READY 상태이고 파일이 존재해야 합니다")

    if mat.source_mode != MarketingMaterialSourceMode.UPLOADED.value and mat.quality_status != "PASS":
        _msg_map = {
            "FAIL": "품질 게이트 미통과 자료는 배포할 수 없습니다. 자료를 재생성해 주세요.",
            "CONDITIONAL": "조건부 통과 자료는 배포할 수 없습니다. 재검토 후 재생성해 주세요.",
            "SKIPPED": "품질 검증이 실행되지 않은 자료입니다. 자료를 재생성해 주세요.",
        }
        raise DocumentNotFoundError(
            _msg_map.get(mat.quality_status or "", "품질 검증을 통과한 자료만 배포할 수 있습니다.")
        )

    if not Path(mat.file_path).exists():
        raise DocumentNotFoundError("파일이 서버에 존재하지 않습니다. 자료를 다시 생성해 주세요.")

    mat.distributed_to = body.distributed_to
    mat.distributed_at = body.distributed_at or datetime.now(UTC).isoformat()

    await db.commit()
    await db.refresh(mat)
    return mat


async def delete_marketing_material(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    mat_id: uuid.UUID,
) -> None:
    """마케팅 자료 삭제 (파일 포함)."""
    mat = await get_marketing_material(db, transaction_id, mat_id)

    # 생성된 PPTX 파일 삭제
    if mat.file_path and mat.source_mode != MarketingMaterialSourceMode.UPLOADED.value:
        p = Path(mat.file_path)
        if p.exists():
            p.unlink(missing_ok=True)

    await db.delete(mat)
    await db.commit()
