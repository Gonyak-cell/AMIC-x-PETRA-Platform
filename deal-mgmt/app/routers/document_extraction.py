"""문서 AI 추출 라우터 — VDR 문서 분류/추출/확정 엔드포인트."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.enums import ExtractionStatus
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
    """BackgroundTasks로 확실히 실행하고, Celery도 시도한다.

    Celery 워커가 태스크를 인식 못하면 메시지가 버려지므로,
    BackgroundTasks를 항상 등록하여 실행을 보장한다.
    파이프라인의 멱등성 가드가 중복 실행을 방지한다.
    """
    from app.core.database import async_session_factory

    # 항상 BackgroundTasks 등록 (실행 보장)
    background_tasks.add_task(_run_sync_fallback, extraction_id, async_session_factory)

    # Celery도 시도 (워커가 정상이면 더 빠르게 처리)
    try:
        from app.tasks.extraction_tasks import run_extraction_task

        run_extraction_task.delay(str(extraction_id))
        logger.info("Celery 디스패치 성공 (BackgroundTasks도 등록됨): %s", extraction_id)
    except Exception as exc:
        logger.debug("Celery 디스패치 실패 (BackgroundTasks로 처리): %s", exc)


async def _run_sync_fallback(extraction_id: uuid.UUID, session_factory: object) -> None:
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
    await check_client_deal_access(db, txn_id, claims)

    existing = await svc.has_active_extraction(db, body.vdr_document_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이 문서에 대한 AI 분석이 이미 존재합니다",
        )

    extraction = await svc.create_extraction(
        db,
        txn_id,
        body.vdr_document_id,
        body.doc_category_hint,
    )
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
    await check_client_deal_access(db, txn_id, claims)

    # 이미 활성 추출이 있는 문서를 IN 쿼리 1회로 일괄 확인
    from sqlalchemy import select

    from app.models.document_extraction import DocumentExtraction

    _active_statuses = (
        ExtractionStatus.PENDING,
        ExtractionStatus.CLASSIFYING,
        ExtractionStatus.EXTRACTING,
        ExtractionStatus.COMPLETED,
        ExtractionStatus.CONFIRMED,
    )
    existing_q = select(DocumentExtraction.vdr_document_id).where(
        DocumentExtraction.vdr_document_id.in_(body.vdr_document_ids),
        DocumentExtraction.status.in_(_active_statuses),
    )
    existing_ids = set((await db.execute(existing_q)).scalars().all())

    skipped = [vid for vid in body.vdr_document_ids if vid in existing_ids]
    extractions = []
    for vdr_doc_id in body.vdr_document_ids:
        if vdr_doc_id in existing_ids:
            continue
        ext = await svc.create_extraction(db, txn_id, vdr_doc_id)
        extractions.append(ext)

    if skipped:
        logger.info("배치 추출 중복 스킵: %d건 (%s)", len(skipped), skipped)

    if not extractions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"요청한 {len(skipped)}건 모두 이미 AI 분석이 존재합니다",
        )
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
    await check_client_deal_access(db, txn_id, claims)

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
    await check_client_deal_access(db, txn_id, claims)

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
    await check_client_deal_access(db, txn_id, claims)

    # 추출 레코드 존재 확인
    extraction = await svc.get_extraction(db, extraction_id)
    if not extraction or extraction.transaction_id != txn_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="추출 작업을 찾을 수 없습니다",
        )

    # 재확정 감사: 이전 상태 스냅샷
    prev_target_model = extraction.target_model
    prev_target_id = extraction.target_id
    is_reconfirm = extraction.status == ExtractionStatus.CONFIRMED

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
        if is_reconfirm:
            logger.info(
                "추출 재확정: extraction=%s, user=%s, prev_target=%s/%s → new_target=%s/%s, data_keys=%s",
                extraction_id,
                claims.email,
                prev_target_model,
                prev_target_id,
                body.target_model,
                body.target_id or updated.target_id,
                list(body.confirmed_data.keys()),
            )
        else:
            logger.info(
                "추출 확정: extraction=%s, user=%s, target_model=%s, target_id=%s, data_keys=%s",
                extraction_id,
                claims.email,
                body.target_model,
                body.target_id or updated.target_id,
                list(body.confirmed_data.keys()),
            )
        return ExtractionOut.model_validate(updated)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        logger.exception("추출 확정 중 예기치 않은 오류 (extraction=%s)", extraction_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="데이터 적용 중 오류가 발생했습니다. 입력 값을 확인해주세요.",
        )
