"""마케팅 자료 서비스 — memo_generator 기반 PPTX 생성 및 CRUD."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import DocumentNotFoundError
from app.models.enums import MarketingDocStatus, MarketingDocType
from app.models.marketing_material import MarketingMaterial
from app.schemas.marketing_material import DistributionUpdate, MarketingMaterialCreate

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "generated" / "memorandum"

# ── doc_type → memo_generator 유형 매핑 ─────────────────────────
_TYPE_MAP: dict[MarketingDocType, str] = {
    MarketingDocType.TM: "tm",
    MarketingDocType.DM: "dm",
    MarketingDocType.IM: "im",
}


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
    mat = MarketingMaterial(
        transaction_id=transaction_id,
        doc_type=body.doc_type,
        title=body.title,
        project_code=body.project_code,
        status=MarketingDocStatus.GENERATING,
        parameters=body.parameters,
        created_by_email=created_by_email,
    )
    db.add(mat)
    await db.commit()
    await db.refresh(mat)

    # PPTX 생성 — Celery 태스크로 실행
    from app.tasks.marketing_tasks import generate_pptx_task

    generate_pptx_task.delay(
        mat_id=str(mat.id),
        transaction_id=str(transaction_id),
        body_dict=body.model_dump(mode="json"),
    )

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
    from app.pptx.memo_generator import generate_memo

    try:
        memo_type = _TYPE_MAP[body.doc_type]
        project_code = body.project_code or str(mat_id)[:8].upper()

        out_dir = OUTPUT_DIR / str(transaction_id)
        out_dir.mkdir(parents=True, exist_ok=True)

        output_path = out_dir / f"{memo_type}_{mat_id}.pptx"

        # 동기 함수를 스레드풀에서 실행 (python-pptx는 동기 IO)
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: generate_memo(
                memo_type=memo_type,
                project_code=project_code,
                output_path=str(output_path),
                content=body.parameters,
            )
        )

        # 독립적인 새 세션으로 DB 업데이트
        async with session_factory() as db:
            q = select(MarketingMaterial).where(MarketingMaterial.id == mat_id)
            r = await db.execute(q)
            mat = r.scalar_one_or_none()
            if mat:
                mat.status = MarketingDocStatus.READY
                mat.file_path = result.output_path
                mat.file_name = result.file_name
                mat.file_size_bytes = result.file_size_bytes
                await db.commit()

    except Exception as exc:
        async with session_factory() as db:
            q = select(MarketingMaterial).where(MarketingMaterial.id == mat_id)
            r = await db.execute(q)
            mat = r.scalar_one_or_none()
            if mat:
                mat.status = MarketingDocStatus.FAILED
                mat.error_message = str(exc)
                await db.commit()


async def create_marketing_material_with_ralph(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: MarketingMaterialCreate,
    created_by_email: str | None = None,
) -> MarketingMaterial:
    """Ralph Loop 품질 강화 모드로 마케팅 자료를 생성한다."""
    import logging

    from app.ralph.convergence import ConvergenceConfig
    from app.ralph.gates.pptx_gate import PPTXProgrammaticGate
    from app.ralph.generators.pptx_generator import RalphMemoGenerator
    from app.ralph.orchestrator import RalphLoopOrchestrator
    from app.ralph.prd_manager import load_prd

    logger = logging.getLogger(__name__)

    mat = MarketingMaterial(
        transaction_id=transaction_id,
        doc_type=body.doc_type,
        title=body.title,
        project_code=body.project_code,
        status=MarketingDocStatus.GENERATING,
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
            generator=generator, gates=gates, prd=prd, config=config,
        )
        loop_result = await orchestrator.run(source_data=body.parameters)

        if loop_result.final_artifact and Path(loop_result.final_artifact).exists():
            p = Path(loop_result.final_artifact)
            mat.status = MarketingDocStatus.READY
            mat.file_path = str(p)
            mat.file_name = p.name
            mat.file_size_bytes = p.stat().st_size
        else:
            mat.status = MarketingDocStatus.READY
            mat.error_message = "Ralph Loop 완료 — LLM 미연결 시 기본 템플릿"

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

    from app.pptx.memo_generator import generate_memo

    memo_type = _TYPE_MAP[mat.doc_type]
    project_code = mat.project_code or str(mat_id)[:8].upper()

    out_dir = OUTPUT_DIR / str(transaction_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{memo_type}_{mat_id}.pptx"

    mat.status = MarketingDocStatus.GENERATING
    mat.error_message = None
    await db.commit()

    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: generate_memo(
                memo_type=memo_type,
                project_code=project_code,
                output_path=str(output_path),
                content=mat.parameters,
            )
        )
        mat.status = MarketingDocStatus.READY
        mat.file_path = result.output_path
        mat.file_name = result.file_name
        mat.file_size_bytes = result.file_size_bytes
    except Exception as exc:
        mat.status = MarketingDocStatus.FAILED
        mat.error_message = str(exc)

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
    if mat.file_path:
        p = Path(mat.file_path)
        if p.exists():
            p.unlink(missing_ok=True)

    await db.delete(mat)
    await db.commit()
