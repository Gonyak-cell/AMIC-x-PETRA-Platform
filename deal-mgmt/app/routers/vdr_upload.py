"""VDR 업로드 전용 라우터 — auto-upload, direct-upload, classification."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.blob_storage import blob_client
from app.core.database import get_db
from app.core.exceptions import DocumentNotFoundError
from app.core.security import JWTClaims, get_jwt_claims, require_write_access
from app.models.enums import VdrClassificationStatus, VdrFolderCategory
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.routers.vdr import (
    _MAX_FILE_SIZE,
    _get_and_authorize_txn,
    _upload_limiter,
    _validate_upload_metadata,
    _validate_upload_streaming,
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

# direct_upload 병렬 업로드 동시성 제한 (Azure VM 2 vCPU 기준)
_UPLOAD_CONCURRENCY = 5


@dataclass
class _PreparedFile:
    """Phase A에서 검증/분류 완료된 파일 정보."""

    file: UploadFile
    filename: str
    ext: str
    content_type: str
    sha256_hex: str
    file_size: int
    top_score: int
    routed_category: VdrFolderCategory | None


async def _prepare_vdr_upload_context(
    db: AsyncSession,
    txn_id: uuid.UUID,
    claims: JWTClaims,
) -> None:
    await _get_and_authorize_txn(db, txn_id, claims)
    await vdr_service.init_vdr_folders(db, txn_id)
    _upload_limiter.check(f"vdr_upload:{claims.email or claims.user_id}")


async def _manual_folder_upload(
    txn_id: uuid.UUID,
    folder_id: uuid.UUID,
    files: list[UploadFile],
    db: AsyncSession,
    claims: JWTClaims,
) -> DirectUploadBatchResult:
    if len(files) > _MAX_DIRECT_UPLOAD_FILES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"한 번에 최대 {_MAX_DIRECT_UPLOAD_FILES}개 파일까지 업로드할 수 있습니다.",
        )

    await _prepare_vdr_upload_context(db, txn_id, claims)
    folder = await vdr_service.get_folder(db, txn_id, folder_id)

    results: list[DirectUploadFileResult] = []
    failed_files: list[FailedFileInfo] = []

    for file in files:
        raw_name = Path(file.filename or "untitled").name
        try:
            filename, _ext, content_type, sha256_hex, file_size = await _validate_upload_streaming(file)
            has_dup = await vdr_service.check_duplicate_filename(
                db,
                txn_id,
                folder.id,
                filename,
            )
            final_name = vdr_service.resolve_unique_filename(filename, has_dup)
            doc = await vdr_service.upload_document_stream(
                db=db,
                transaction_id=txn_id,
                folder_id=folder.id,
                original_name=final_name,
                file_obj=file,
                file_size=file_size,
                sha256_hex=sha256_hex,
                mime_type=content_type,
                uploaded_by_email=claims.email,
            )
        except HTTPException as exc:
            failed_files.append(FailedFileInfo(filename=raw_name, reason=str(exc.detail)))
            continue
        except DocumentNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        except Exception as exc:
            logger.warning(
                "Manual VDR upload 실패: txn=%s, folder=%s, file=%s — %s",
                txn_id,
                folder_id,
                raw_name,
                exc,
            )
            failed_files.append(
                FailedFileInfo(
                    filename=raw_name,
                    reason=f"파일 저장 실패: {exc}",
                )
            )
            continue

        results.append(
            DirectUploadFileResult(
                document=VdrDocumentOut.model_validate(doc),
                routed_folder=VdrFolderOut.model_validate(folder),
                routed_category=folder.category,
                classification_status=VdrClassificationStatus.DIRECT,
                score=100,
                was_fallback=False,
            )
        )

    logger.info(
        "Manual VDR upload 완료: txn=%s, folder=%s, user=%s, total=%d, failed=%d",
        txn_id,
        folder_id,
        claims.email,
        len(results),
        len(failed_files),
    )

    return DirectUploadBatchResult(
        results=results,
        pending_review_count=0,
        total_uploaded=len(results),
        failed_files=failed_files,
    )


async def _auto_route_upload_batch(
    txn_id: uuid.UUID,
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    claims: JWTClaims,
) -> DirectUploadBatchResult:
    if len(files) > _MAX_DIRECT_UPLOAD_FILES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"한 번에 최대 {_MAX_DIRECT_UPLOAD_FILES}개 파일까지 업로드할 수 있습니다.",
        )
    await _prepare_vdr_upload_context(db, txn_id, claims)

    from app.services.vdr_categorization_service import auto_route, score_document

    # ── Phase A: 메타데이터 검증 + 스트리밍 해시/크기 + 분류 (병렬) ──
    _hash_sem = asyncio.Semaphore(_UPLOAD_CONCURRENCY)
    failed_files: list[FailedFileInfo] = []

    async def _prepare_one(file: UploadFile) -> _PreparedFile | None:
        async with _hash_sem:
            try:
                filename, ext, content_type = _validate_upload_metadata(file)
                sha256_hex, file_size = await vdr_service.stream_hash_and_size(
                    file,
                    _MAX_FILE_SIZE,
                )
            except HTTPException as exc:
                raw_name = file.filename or "untitled"
                failed_files.append(FailedFileInfo(filename=Path(raw_name).name, reason=exc.detail))
                return None

            scores = score_document(filename, ext, content_type, file_size)
            top_score = scores[0][1] if scores else 0
            routed_category = auto_route(filename, ext, content_type, file_size)

            return _PreparedFile(
                file=file,
                filename=filename,
                ext=ext,
                content_type=content_type,
                sha256_hex=sha256_hex,
                file_size=file_size,
                top_score=top_score,
                routed_category=routed_category,
            )

    prepared_results = await asyncio.gather(*[_prepare_one(f) for f in files])
    prepared = [p for p in prepared_results if p is not None]

    # ── Phase B: 2-pass — 배치 쿼리 → DB 레코드 생성 → blob 업로드 ──
    results: list[DirectUploadFileResult] = []
    pending_doc_ids: list[uuid.UUID] = []

    @dataclass
    class _BlobTask:
        file: UploadFile
        blob_name: str
        content_type: str
        file_size: int
        doc: VdrDocument

    blob_tasks: list[_BlobTask] = []

    # ── Pass 1: 폴더 배치 조회 + 폴백 1회 조회 ──
    needed_categories = {p.routed_category for p in prepared if p.routed_category is not None}
    folder_cache = await vdr_service.resolve_folders_by_categories(db, txn_id, needed_categories)
    fallback_folder = await vdr_service.resolve_fallback_folder(db, txn_id)

    # 폴더 결정 + 중복 체크 데이터 수집
    dup_checks: list[tuple[uuid.UUID, str]] = []
    folder_assignments: list[tuple[VdrFolder, bool]] = []  # (folder, is_fallback)

    for p in prepared:
        if p.routed_category is not None:
            folder = folder_cache.get(p.routed_category) or fallback_folder
            if folder is None:
                failed_files.append(FailedFileInfo(filename=p.filename, reason="VDR이 초기화되지 않았습니다."))
                folder_assignments.append((None, False))  # type: ignore[arg-type]
                continue
            folder_assignments.append((folder, False))
            dup_checks.append((folder.id, p.filename))
        else:
            if fallback_folder is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="VDR이 초기화되지 않았습니다. 먼저 폴더 구조를 초기화해 주세요.",
                )
            folder_assignments.append((fallback_folder, True))
            dup_checks.append((fallback_folder.id, p.filename))

    # 배치 중복 체크 (단일 쿼리)
    dup_set = await vdr_service.check_duplicate_filenames_batch(db, txn_id, dup_checks)

    # ── Pass 2: DB 레코드 생성 + blob 태스크 수집 ──
    for p, (folder, is_fallback) in zip(prepared, folder_assignments, strict=True):
        if folder is None:
            continue  # Pass 1에서 실패 처리됨

        has_dup = (folder.id, p.filename) in dup_set
        final_name = vdr_service.resolve_unique_filename(p.filename, has_dup)

        stored_name = f"{uuid.uuid4()}{p.ext}"
        blob_name = f"{txn_id}/{folder.id}/{stored_name}"

        doc = VdrDocument(
            transaction_id=txn_id,
            folder_id=folder.id,
            original_name=final_name,
            stored_name=stored_name,
            file_path=blob_name,
            file_size_bytes=p.file_size,
            mime_type=p.content_type,
            sha256_hash=p.sha256_hex,
            uploaded_by_email=claims.email,
        )
        if is_fallback:
            doc.classification_status = VdrClassificationStatus.PENDING_REVIEW
        else:
            doc.classification_status = VdrClassificationStatus.DIRECT
        doc.classification_score = p.top_score
        db.add(doc)
        await db.flush()

        blob_tasks.append(
            _BlobTask(
                file=p.file,
                blob_name=blob_name,
                content_type=p.content_type,
                file_size=p.file_size,
                doc=doc,
            )
        )

        if is_fallback:
            pending_doc_ids.append(doc.id)

        results.append(
            DirectUploadFileResult(
                document=VdrDocumentOut.model_validate(doc),
                routed_folder=VdrFolderOut.model_validate(folder),
                routed_category=None if is_fallback else p.routed_category,
                classification_status=doc.classification_status,
                score=p.top_score,
                was_fallback=is_fallback,
            )
        )

    await blob_client.ensure_initialized()

    # blob 병렬 업로드 (별도 Semaphore로 동시성 제한)
    _blob_sem = asyncio.Semaphore(_UPLOAD_CONCURRENCY)

    async def _upload_blob(task: _BlobTask) -> tuple[_BlobTask, Exception | None]:
        async with _blob_sem:
            try:
                await blob_client.upload_blob_stream(
                    task.blob_name,
                    task.file,
                    task.content_type,
                    task.file_size,
                )
                return task, None
            except Exception as exc:
                logger.warning(
                    "Direct upload blob 업로드 실패: blob=%s — %s",
                    task.blob_name,
                    exc,
                )
                return task, exc

    blob_results = await asyncio.gather(*[_upload_blob(t) for t in blob_tasks])

    # blob 실패 처리: DB 레코드 롤백 + 결과에서 제거
    for task, exc in blob_results:
        if exc is not None:
            await db.delete(task.doc)
            results = [r for r in results if r.document.id != task.doc.id]
            pending_doc_ids = [d for d in pending_doc_ids if d != task.doc.id]
            failed_files.append(
                FailedFileInfo(
                    filename=task.doc.original_name,
                    reason=f"파일 저장 실패: {exc}",
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
    await _prepare_vdr_upload_context(db, txn_id, claims)
    filename, _ext, content_type, sha256_hex, file_size = await _validate_upload_streaming(file)

    try:
        doc, folder, routed_category = await vdr_service.auto_upload_document_stream(
            db=db,
            transaction_id=txn_id,
            original_name=filename,
            file_obj=file,
            file_size=file_size,
            sha256_hex=sha256_hex,
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
    "/uploads",
    response_model=DirectUploadBatchResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_documents(
    txn_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
    folder_id: uuid.UUID | None = Form(None),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    """VDR 통합 업로드 진입점.

    - folder_id 지정 시: 해당 폴더로 수동 업로드
    - folder_id 미지정 시: 자동 라우팅 배치 업로드
    """
    if folder_id is not None:
        return await _manual_folder_upload(
            txn_id=txn_id,
            folder_id=folder_id,
            files=files,
            db=db,
            claims=claims,
        )
    return await _auto_route_upload_batch(
        txn_id=txn_id,
        files=files,
        background_tasks=background_tasks,
        db=db,
        claims=claims,
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
    """다중 파일을 폴더 지정 없이 업로드 — 2-Phase 병렬 파이프라인.

    Phase A (병렬): 메타데이터 검증 → 스트리밍 해시/크기 → 분류
    Phase B (순차 DB + 병렬 blob): DB 레코드 생성 → blob 스트리밍 업로드 → 일괄 커밋
    """
    return await _auto_route_upload_batch(
        txn_id=txn_id,
        files=files,
        background_tasks=background_tasks,
        db=db,
        claims=claims,
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
