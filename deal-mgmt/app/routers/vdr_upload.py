"""VDR 업로드 전용 라우터 — auto-upload, direct-upload, classification."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import DocumentNotFoundError
from app.core.security import JWTClaims, get_jwt_claims, require_write_access
from app.models.enums import VdrClassificationStatus
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.routers.vdr import (
    _get_and_authorize_txn,
    _upload_limiter,
    _validate_upload,
)
from app.schemas.vdr import (
    ClassificationStatusOut,
    DirectUploadBatchResult,
    DirectUploadFileResult,
    FailedFileInfo,
    SuggestCategoryRequest,
    SuggestCategoryResponse,
    VdrAutoUploadResult,
    VdrDocumentOut,
    VdrFolderOut,
)
from app.services import vdr_service
from app.services.vdr_classification_service import run_secondary_classification as _run_secondary_classification

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/transactions/{txn_id}/vdr",
    tags=["VDR Upload"],
)

_MAX_DIRECT_UPLOAD_FILES = 20
_MAX_CLASSIFICATION_POLL_DOCS = 50


@router.post("/suggest-category", response_model=SuggestCategoryResponse)
async def suggest_folder_category(
    txn_id: uuid.UUID,
    body: SuggestCategoryRequest,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> SuggestCategoryResponse:
    """파일명을 분석하여 적합한 VDR 폴더 카테고리를 추천한다."""
    await _get_and_authorize_txn(db, txn_id, claims)

    from app.services.vdr_categorization_service import suggest_category

    category = suggest_category(body.filename)
    if category is None:
        return SuggestCategoryResponse(category=None, folder_name=None)

    folder = await vdr_service.resolve_folder_by_category(db, txn_id, category)

    return SuggestCategoryResponse(
        category=category.value,
        folder_name=folder.name if folder else None,
    )


@router.post(
    "/documents/auto-upload",
    response_model=VdrAutoUploadResult,
    status_code=status.HTTP_201_CREATED,
)
async def auto_upload_document(
    txn_id: uuid.UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """파일을 분석하여 적합한 VDR 폴더에 자동으로 업로드한다."""
    await _get_and_authorize_txn(db, txn_id, claims)
    _upload_limiter.check(f"vdr_upload:{claims.email or claims.user_id}")
    filename, _ext, content_type, content = await _validate_upload(file)

    try:
        doc, folder, routed_category = await vdr_service.auto_upload_document(
            db=db,
            transaction_id=txn_id,
            original_name=filename,
            file_content=content,
            mime_type=content_type,
            uploaded_by_email=claims.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    was_fallback = routed_category is None
    original_name_renamed = doc.original_name != filename

    return VdrAutoUploadResult(
        document=VdrDocumentOut.model_validate(doc),
        routed_folder=VdrFolderOut.model_validate(folder),
        routed_category=routed_category,
        was_fallback=was_fallback,
        original_name_renamed=original_name_renamed,
        final_name=doc.original_name,
    )


@router.post(
    "/documents/direct-upload",
    response_model=DirectUploadBatchResult,
    status_code=status.HTTP_201_CREATED,
)
async def direct_upload(
    txn_id: uuid.UUID,
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """다중 파일을 폴더 지정 없이 업로드 — 1차 심사 + 2차 심사 자동 디스패치."""
    if len(files) > _MAX_DIRECT_UPLOAD_FILES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"한 번에 최대 {_MAX_DIRECT_UPLOAD_FILES}개 파일까지 업로드할 수 있습니다.",
        )
    await _get_and_authorize_txn(db, txn_id, claims)
    _upload_limiter.check(f"vdr_upload:{claims.email or claims.user_id}")

    from app.services.vdr_categorization_service import auto_route, score_document

    results: list[DirectUploadFileResult] = []
    pending_doc_ids: list[uuid.UUID] = []
    failed_files: list[FailedFileInfo] = []

    for file in files:
        filename, ext, content_type, content = await _validate_upload(file)

        scores = score_document(filename, ext, content_type, len(content))
        top_score = scores[0][1] if scores else 0
        routed_category = auto_route(filename, ext, content_type, len(content))

        if routed_category is not None:
            try:
                doc, folder, _ = await vdr_service.auto_upload_document(
                    db=db,
                    transaction_id=txn_id,
                    original_name=filename,
                    file_content=content,
                    mime_type=content_type,
                    uploaded_by_email=claims.email,
                )
            except (ValueError, DocumentNotFoundError) as exc:
                logger.warning(
                    "Direct upload 1차 통과 파일 업로드 실패: txn=%s, file=%s — %s",
                    txn_id,
                    filename,
                    exc,
                )
                failed_files.append(FailedFileInfo(filename=filename, reason=str(exc)))
                continue

            doc.classification_status = VdrClassificationStatus.DIRECT
            doc.classification_score = top_score

            results.append(
                DirectUploadFileResult(
                    document=VdrDocumentOut.model_validate(doc),
                    routed_folder=VdrFolderOut.model_validate(folder),
                    routed_category=routed_category,
                    classification_status=VdrClassificationStatus.DIRECT,
                    score=top_score,
                    was_fallback=False,
                )
            )
        else:
            fallback = await vdr_service.resolve_fallback_folder(db, txn_id)
            if fallback is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="VDR이 초기화되지 않았습니다. 먼저 폴더 구조를 초기화해 주세요.",
                )

            try:
                doc = await vdr_service.upload_document(
                    db=db,
                    transaction_id=txn_id,
                    folder_id=fallback.id,
                    original_name=filename,
                    file_content=content,
                    mime_type=content_type,
                    uploaded_by_email=claims.email,
                    _folder_verified=True,
                )
            except DocumentNotFoundError as exc:
                logger.warning(
                    "Direct upload 폴백 업로드 실패: txn=%s, file=%s — %s",
                    txn_id,
                    filename,
                    exc,
                )
                failed_files.append(FailedFileInfo(filename=filename, reason=str(exc)))
                continue

            doc.classification_status = VdrClassificationStatus.PENDING_REVIEW
            doc.classification_score = top_score
            pending_doc_ids.append(doc.id)

            results.append(
                DirectUploadFileResult(
                    document=VdrDocumentOut.model_validate(doc),
                    routed_folder=VdrFolderOut.model_validate(fallback),
                    routed_category=None,
                    classification_status=VdrClassificationStatus.PENDING_REVIEW,
                    score=top_score,
                    was_fallback=True,
                )
            )

    await db.commit()

    for doc_id in pending_doc_ids:
        background_tasks.add_task(_run_secondary_classification, doc_id, txn_id)

    logger.info(
        "Direct upload 완료: txn=%s, user=%s, total=%d, pending=%d, failed=%d",
        txn_id,
        claims.email,
        len(results),
        len(pending_doc_ids),
        len(failed_files),
    )

    return DirectUploadBatchResult(
        results=results,
        pending_review_count=len(pending_doc_ids),
        total_uploaded=len(results),
        failed_files=failed_files,
    )


@router.get(
    "/documents/classification-status",
    response_model=list[ClassificationStatusOut],
)
async def get_classification_status(
    txn_id: uuid.UUID,
    doc_ids: list[uuid.UUID] = Query(...),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> list[ClassificationStatusOut]:
    """2차 심사 대기 중인 문서들의 분류 상태를 조회한다 (FE 폴링용)."""
    if len(doc_ids) > _MAX_CLASSIFICATION_POLL_DOCS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"한 번에 최대 {_MAX_CLASSIFICATION_POLL_DOCS}개 문서까지 조회할 수 있습니다.",
        )
    await _get_and_authorize_txn(db, txn_id, claims)

    stmt = select(VdrDocument).where(
        VdrDocument.transaction_id == txn_id,
        VdrDocument.id.in_(doc_ids),
    )
    result = await db.execute(stmt)
    docs = list(result.scalars().all())

    # 재분류된 문서의 폴더 정보를 한 번에 조회 (N+1 방지)
    classified_folder_ids = {
        doc.folder_id
        for doc in docs
        if doc.classification_status == VdrClassificationStatus.CLASSIFIED and doc.folder_id
    }
    folder_map: dict[uuid.UUID, VdrFolder] = {}
    if classified_folder_ids:
        folder_stmt = select(VdrFolder).where(VdrFolder.id.in_(classified_folder_ids))
        folder_result = await db.execute(folder_stmt)
        for folder in folder_result.scalars().all():
            folder_map[folder.id] = folder

    items: list[ClassificationStatusOut] = []
    for doc in docs:
        folder_out: VdrFolderOut | None = None
        folder_category = None
        if doc.classification_status == VdrClassificationStatus.CLASSIFIED and doc.folder_id:
            folder = folder_map.get(doc.folder_id)
            if folder:
                folder_out = VdrFolderOut.model_validate(folder)
                folder_category = folder.category

        items.append(
            ClassificationStatusOut(
                document_id=doc.id,
                classification_status=doc.classification_status or VdrClassificationStatus.MANUAL,
                routed_folder=folder_out,
                routed_category=folder_category,
                manual_review_needed=doc.manual_review_needed,
            )
        )

    return items
