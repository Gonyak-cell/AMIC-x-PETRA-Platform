"""Document extraction routes for VDR documents."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
_pending_celery_dispatch_tasks: set[asyncio.Task[None]] = set()
_INLINE_EXTRACTION_ENV_NAMES = {"local", "dev", "development", "test"}

router = APIRouter(
    prefix="/transactions/{txn_id}/extractions",
    tags=["Document Extraction"],
)


def _run_extraction_processing_inline() -> bool:
    env = os.getenv("ENV", "").strip().lower()
    return env in _INLINE_EXTRACTION_ENV_NAMES or bool(settings.DEBUG) or not settings.AUTH_ENABLED


async def _dispatch_extraction(extraction_id: uuid.UUID, background_tasks: BackgroundTasks) -> None:
    """Use inline fallback only in local/dev flows; production relies on Celery."""
    from app.core.database import async_session_factory

    if _run_extraction_processing_inline():
        background_tasks.add_task(_run_sync_fallback, extraction_id, async_session_factory)
        return

    dispatch_task = asyncio.create_task(_dispatch_celery_best_effort(extraction_id))
    _pending_celery_dispatch_tasks.add(dispatch_task)
    dispatch_task.add_done_callback(_pending_celery_dispatch_tasks.discard)


async def _run_sync_fallback(extraction_id: uuid.UUID, session_factory: object) -> None:
    """Run the extraction pipeline in a worker thread for local fallback."""
    await asyncio.to_thread(_run_extraction_pipeline_in_thread, extraction_id, session_factory)


def _run_extraction_pipeline_in_thread(extraction_id: uuid.UUID, session_factory: object) -> None:
    from app.services.document_extraction_service import run_extraction_pipeline

    asyncio.run(run_extraction_pipeline(extraction_id, session_factory))


async def _dispatch_celery_best_effort(extraction_id: uuid.UUID) -> None:
    """Queue extraction work without blocking the request path."""
    try:
        from app.tasks.extraction_tasks import run_extraction_task

        await asyncio.to_thread(run_extraction_task.delay, str(extraction_id))
        logger.info("Celery dispatch succeeded for extraction %s", extraction_id)
    except Exception as exc:
        logger.debug("Celery dispatch failed for extraction %s: %s", extraction_id, exc)


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
    """Start AI extraction for a single VDR document."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    existing = await svc.has_active_extraction(db, body.vdr_document_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An AI extraction already exists for this document.",
        )

    extraction = await svc.create_extraction(
        db,
        txn_id,
        body.vdr_document_id,
        body.doc_category_hint,
        target_model=body.target_model,
        target_id=body.target_id,
        auto_apply_signed_at=body.auto_apply_signed_at,
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
    """Start AI extraction for multiple VDR documents."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    from sqlalchemy import select

    from app.models.document_extraction import DocumentExtraction

    active_statuses = (
        ExtractionStatus.PENDING,
        ExtractionStatus.CLASSIFYING,
        ExtractionStatus.EXTRACTING,
        ExtractionStatus.COMPLETED,
        ExtractionStatus.CONFIRMED,
    )
    existing_q = select(DocumentExtraction.vdr_document_id).where(
        DocumentExtraction.vdr_document_id.in_(body.vdr_document_ids),
        DocumentExtraction.status.in_(active_statuses),
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
        logger.info("Skipped %d duplicate extraction requests: %s", len(skipped), skipped)

    if not extractions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"All {len(skipped)} requested documents already have AI extraction records.",
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
    """List extraction jobs for a transaction."""
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
    """Get one extraction job."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    extraction = await svc.get_extraction(db, extraction_id)
    if not extraction or extraction.transaction_id != txn_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction job not found.",
        )
    return ExtractionOut.model_validate(extraction)


@router.post(
    "/{extraction_id}/retry",
    response_model=ExtractionOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_extraction(
    txn_id: uuid.UUID,
    extraction_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """Retry a failed extraction."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    extraction = await svc.get_extraction(db, extraction_id)
    if not extraction or extraction.transaction_id != txn_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction job not found.",
        )

    try:
        extraction = await svc.retry_extraction(db, extraction_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await db.commit()
    await db.refresh(extraction)

    await _dispatch_extraction(extraction.id, background_tasks)

    logger.info("Retry extraction requested: extraction=%s user=%s", extraction_id, claims.email)
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
    """Confirm extracted data and map it into the target model."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    extraction = await svc.get_extraction(db, extraction_id)
    if not extraction or extraction.transaction_id != txn_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction job not found.",
        )

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
                "Extraction reconfirmed: extraction=%s user=%s prev_target=%s/%s new_target=%s/%s data_keys=%s",
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
                "Extraction confirmed: extraction=%s user=%s target_model=%s target_id=%s data_keys=%s",
                extraction_id,
                claims.email,
                body.target_model,
                body.target_id or updated.target_id,
                list(body.confirmed_data.keys()),
            )
        return ExtractionOut.model_validate(updated)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected extraction confirm error (extraction=%s)", extraction_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An error occurred while applying the extracted data. Please review the input values.",
        ) from exc
