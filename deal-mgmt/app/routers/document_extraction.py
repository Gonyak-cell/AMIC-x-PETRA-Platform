"""문서 AI 추출 라우터 — VDR 문서 분류/추출/확정 엔드포인트."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims, require_write_access
from app.schemas.document_extraction import (
    BatchExtractionRequest,
    ExtractionConfirmRequest,
    ExtractionCreateRequest,
    ExtractionListOut,
    ExtractionOut,
)
from app.services import document_extraction_service as svc
from app.services import transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/transactions/{txn_id}/extractions",
    tags=["Document Extraction"],
)


# ── 헬퍼 ─────────────────────────────────────────────────────


async def _dispatch_extraction(extraction_id: uuid.UUID, background_tasks: BackgroundTasks) -> None:
    """Celery 우선, 연결 실패 시 FastAPI BackgroundTasks 폴백."""
    try:
        from app.tasks.extraction_tasks import run_extraction_task

        run_extraction_task.delay(str(extraction_id))
        logger.info("Celery 디스패치 성공: %s", extraction_id)
    except Exception as exc:
        logger.warning("Celery 디스패치 실패, 동기 폴백: %s", exc)
        from app.core.database import async_session_factory

        background_tasks.add_task(
            _run_sync_fallback, extraction_id, async_session_factory
        )


async def _run_sync_fallback(extraction_id: uuid.UUID, session_factory) -> None:
    """FastAPI BackgroundTasks용 동기 폴백."""
    from app.services.document_extraction_service import run_extraction_pipeline

    await run_extraction_pipeline(extraction_id, session_factory)


# ── 엔드포인트 ───────────────────────────────────────────────


@router.post(
    "",
    response_model=ExtractionOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_extraction(
    txn_id: uuid.UUID,
    body: ExtractionCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """단일 VDR 문서 AI 추출을 시작한다."""
    await transaction_service.get_transaction(db, txn_id)

    extraction = await svc.create_extraction(db, txn_id, body.vdr_document_id)
    await db.commit()
    await db.refresh(extraction)

    await _dispatch_extraction(extraction.id, background_tasks)

    return ExtractionOut.model_validate(extraction)


@router.post(
    "/batch",
    response_model=list[ExtractionOut],
    status_code=status.HTTP_202_ACCEPTED,
)
async def batch_extract(
    txn_id: uuid.UUID,
    body: BatchExtractionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """여러 VDR 문서를 일괄 AI 추출한다 (최대 10건)."""
    await transaction_service.get_transaction(db, txn_id)

    extractions = []
    for vdr_doc_id in body.vdr_document_ids:
        ext = await svc.create_extraction(db, txn_id, vdr_doc_id)
        extractions.append(ext)
    await db.commit()

    for ext in extractions:
        await db.refresh(ext)
        await _dispatch_extraction(ext.id, background_tasks)

    return [ExtractionOut.model_validate(e) for e in extractions]


@router.get(
    "",
    response_model=ExtractionListOut,
)
async def list_extractions(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """거래의 모든 추출 작업 목록을 조회한다 (폴링용)."""
    await transaction_service.get_transaction(db, txn_id)

    items = await svc.list_extractions(db, txn_id)
    return ExtractionListOut(
        items=[ExtractionOut.model_validate(i) for i in items],
        total=len(items),
    )


@router.get(
    "/{extraction_id}",
    response_model=ExtractionOut,
)
async def get_extraction(
    txn_id: uuid.UUID,
    extraction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """단일 추출 작업 상세를 조회한다."""
    await transaction_service.get_transaction(db, txn_id)

    extraction = await svc.get_extraction(db, extraction_id)
    if not extraction or extraction.transaction_id != txn_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="추출 작업을 찾을 수 없습니다",
        )
    return ExtractionOut.model_validate(extraction)


@router.put(
    "/{extraction_id}/confirm",
    response_model=ExtractionOut,
)
async def confirm_extraction(
    txn_id: uuid.UUID,
    extraction_id: uuid.UUID,
    body: ExtractionConfirmRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """추출 결과를 검토/수정 후 확정하여 DB에 매핑한다."""
    await transaction_service.get_transaction(db, txn_id)

    # 추출 레코드 존재 확인
    extraction = await svc.get_extraction(db, extraction_id)
    if not extraction or extraction.transaction_id != txn_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="추출 작업을 찾을 수 없습니다",
        )

    try:
        updated = await svc.confirm_extraction(
            db=db,
            extraction_id=extraction_id,
            confirmed_data=body.confirmed_data,
            target_model=body.target_model,
            target_id=body.target_id,
            create_new=body.create_new,
            user_email=claims.email or "",
        )
        return ExtractionOut.model_validate(updated)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
