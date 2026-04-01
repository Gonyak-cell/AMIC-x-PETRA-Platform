from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limiter import InMemoryRateLimiter
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.attachment import Attachment
from app.models.enums import AttachmentEntityType, AuditAction
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.schemas.attachment import AttachmentListResponse, AttachmentOut, VdrSyncInfo
from app.services import audit_service, transaction_service
from app.services.vdr_service import check_vdr_write_permission
from app.tasks.attachment_tasks import (
    PROCESSING_FAILED,
    PROCESSING_PENDING,
    PROCESSING_SKIPPED,
    process_attachment_task,
)

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "attachments"
MAX_FILE_SIZE = 50 * 1024 * 1024
CHUNK_SIZE = 65_536
ALLOWED_EXTENSIONS = {
    ".docx",
    ".doc",
    ".pdf",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ppt",
    ".hwp",
    ".hwpx",
    ".txt",
    ".csv",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".aac",
    ".wma",
}
VALID_ENTITY_TYPES = {e.value for e in AttachmentEntityType}
_ENTITY_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,50}$")
_upload_limiter = InMemoryRateLimiter(max_calls=20, window_seconds=60.0)
_MAGIC_SIGNATURES: list[tuple[bytes, set[str]]] = [
    (b"%PDF", {".pdf"}),
    (b"PK\x03\x04", {".docx", ".xlsx", ".pptx", ".zip", ".hwpx"}),
    (b"\x89PNG", {".png"}),
    (b"\xff\xd8\xff", {".jpg", ".jpeg"}),
    (b"HWP Document File", {".hwp"}),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", {".doc", ".xls", ".ppt"}),
    (b"ID3", {".mp3"}),
    (b"\xff\xfb", {".mp3"}),
    (b"fLaC", {".flac"}),
    (b"RIFF", {".wav"}),
    (b"OggS", {".ogg"}),
    (b"\x30\x26\xb2\x75", {".wma"}),
]

router = APIRouter(prefix="/transactions/{txn_id}/attachments", tags=["Attachments"])


@router.get("", response_model=AttachmentListResponse)
async def list_attachments(
    txn_id: uuid.UUID,
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> AttachmentListResponse:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    if entity_type and entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity_type.")
    if entity_id is not None:
        _validate_entity_id(entity_id)

    q = select(Attachment).where(Attachment.transaction_id == txn_id)
    count_q = select(func.count(Attachment.id)).where(Attachment.transaction_id == txn_id)

    if entity_type:
        q = q.where(Attachment.entity_type == entity_type)
        count_q = count_q.where(Attachment.entity_type == entity_type)
    if entity_id:
        q = q.where(Attachment.entity_id == entity_id)
        count_q = count_q.where(Attachment.entity_id == entity_id)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(q.order_by(Attachment.created_at.desc()).offset(offset).limit(limit))
    attachments = list(result.scalars().all())
    vdr_sync_map = await _load_vdr_sync_map(db, attachments)
    items = [
        _serialize_attachment_out(attachment, vdr_sync=vdr_sync_map.get(attachment.id)) for attachment in attachments
    ]
    return AttachmentListResponse(items=items, total=total)


@router.post("", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    txn_id: uuid.UUID,
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    entity_id: str | None = Form(None),
    description: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> AttachmentOut:
    txn = await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    _upload_limiter.check(f"attachment_upload:{claims.email or claims.user_id}")

    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity_type.")
    if entity_id is not None:
        _validate_entity_id(entity_id)
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size exceeds the 50MB limit.",
        )

    upload_stage = "validate"
    dest_path: Path | None = None
    attachment: Attachment | None = None
    safe_filename = Path(file.filename or "attachment").name

    try:
        ext = Path(safe_filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type.")
        if len(Path(safe_filename).suffixes) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Multiple file extensions are not allowed."
            )

        header = await file.read(32)
        _validate_magic_bytes(header, ext)

        upload_stage = "file_write"
        save_dir = UPLOAD_DIR / str(txn_id) / entity_type
        await asyncio.to_thread(save_dir.mkdir, parents=True, exist_ok=True)

        file_id = uuid.uuid4()
        dest_path = save_dir / f"{file_id}_{safe_filename}"
        total_size = len(header)
        size_exceeded = False

        async with aiofiles.open(dest_path, "wb") as dest:
            await dest.write(header)
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    size_exceeded = True
                    break
                await dest.write(chunk)

        if size_exceeded:
            await asyncio.to_thread(dest_path.unlink, missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="File size exceeds the 50MB limit.",
            )

        has_vdr_access = check_vdr_write_permission(
            claims.role,
            claims.email,
            txn.lead_advisor_email,
            txn.deal_captain_email,
        )
        processing_status = PROCESSING_PENDING if has_vdr_access else PROCESSING_SKIPPED
        processing_error = None if has_vdr_access else "VDR sync was skipped because the uploader lacks write access."

        upload_stage = "db_flush"
        attachment = Attachment(
            transaction_id=txn_id,
            entity_type=entity_type,
            entity_id=entity_id,
            file_path=str(dest_path),
            file_name=safe_filename,
            file_size_bytes=total_size,
            mime_type=file.content_type or "application/octet-stream",
            description=description,
            uploaded_by_email=claims.email,
            processing_status=processing_status,
            processing_error=processing_error,
        )
        db.add(attachment)
        await db.flush()

        upload_stage = "audit"
        await audit_service.record(
            db,
            entity_type="Attachment",
            entity_id=attachment.id,
            action=AuditAction.CREATE,
            actor_email=claims.email,
            new_value={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "file_name": safe_filename,
                "processing_status": processing_status,
            },
        )

        upload_stage = "commit"
        await db.commit()
    except HTTPException:
        await _rollback_upload(db)
        if dest_path is not None:
            await asyncio.to_thread(dest_path.unlink, missing_ok=True)
        raise
    except Exception as exc:
        await _rollback_upload(db)
        if dest_path is not None:
            await asyncio.to_thread(dest_path.unlink, missing_ok=True)
        attachment_id = getattr(attachment, "id", None)
        logger.exception(
            "Attachment upload failed: stage=%s txn=%s entity_type=%s entity_id=%s attachment_id=%s",
            upload_stage,
            txn_id,
            entity_type,
            entity_id,
            attachment_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Attachment upload failed during {upload_stage}.",
        ) from exc

    assert attachment is not None

    try:
        await db.refresh(attachment)
    except Exception:
        logger.warning(
            "Attachment refresh failed after commit: txn=%s attachment=%s",
            txn_id,
            attachment.id,
            exc_info=True,
        )

    if attachment.processing_status == PROCESSING_PENDING:
        try:
            process_attachment_task.delay(str(attachment.id))
        except Exception as exc:
            logger.exception(
                "Attachment processing enqueue failed: txn=%s attachment=%s",
                txn_id,
                attachment.id,
            )
            attachment.processing_status = PROCESSING_FAILED
            attachment.processing_error = f"Automatic post-processing could not be queued: {exc}"
            await db.commit()
            try:
                await db.refresh(attachment)
            except Exception:
                logger.warning(
                    "Attachment refresh failed after enqueue error: attachment=%s", attachment.id, exc_info=True
                )

    vdr_sync_map = await _load_vdr_sync_map(db, [attachment])
    return _serialize_attachment_out(attachment, vdr_sync=vdr_sync_map.get(attachment.id))


@router.post("/{attachment_id}/retry-processing", response_model=AttachmentOut)
async def retry_attachment_processing(
    txn_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> AttachmentOut:
    await check_client_deal_access(db, txn_id, claims)
    attachment = await _get_attachment_or_404(db, txn_id, attachment_id)

    if attachment.processing_status == PROCESSING_SKIPPED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attachment processing was skipped and cannot be retried automatically.",
        )
    if attachment.processing_status == "RUNNING":
        return _serialize_attachment_out(
            attachment, vdr_sync=(await _load_vdr_sync_map(db, [attachment])).get(attachment.id)
        )
    if attachment.processing_status == "SYNCED" and attachment.vdr_document_id is not None:
        return _serialize_attachment_out(
            attachment, vdr_sync=(await _load_vdr_sync_map(db, [attachment])).get(attachment.id)
        )

    attachment.processing_status = PROCESSING_PENDING
    attachment.processing_error = None
    await db.commit()
    await db.refresh(attachment)

    try:
        process_attachment_task.delay(str(attachment.id))
    except Exception as exc:
        logger.exception("Attachment retry enqueue failed: txn=%s attachment=%s", txn_id, attachment.id)
        attachment.processing_status = PROCESSING_FAILED
        attachment.processing_error = f"Automatic post-processing could not be queued: {exc}"
        await db.commit()
        await db.refresh(attachment)

    vdr_sync_map = await _load_vdr_sync_map(db, [attachment])
    return _serialize_attachment_out(attachment, vdr_sync=vdr_sync_map.get(attachment.id))


@router.get("/{attachment_id}/download")
async def download_attachment(
    txn_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> FileResponse:
    await check_client_deal_access(db, txn_id, claims)
    attachment = await _get_attachment_or_404(db, txn_id, attachment_id)

    file_path = Path(attachment.file_path)
    try:
        file_path.resolve().relative_to(UPLOAD_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid attachment path.") from exc
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file was not found.")

    return FileResponse(
        path=str(file_path),
        filename=attachment.file_name or file_path.name,
        media_type="application/octet-stream",
    )


@router.delete("/{attachment_id}", status_code=204)
async def delete_attachment(
    txn_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> None:
    await check_client_deal_access(db, txn_id, claims)
    attachment = await _get_attachment_or_404(db, txn_id, attachment_id)
    file_path_str = attachment.file_path

    await audit_service.record(
        db,
        entity_type="Attachment",
        entity_id=attachment.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(attachment)
    await db.commit()

    try:
        file_path = Path(file_path_str)
        if file_path.exists():
            file_path.unlink()
    except OSError:
        logger.warning("Attachment file cleanup failed: %s", file_path_str)


def _validate_entity_id(entity_id: str) -> None:
    if not _ENTITY_ID_PATTERN.match(entity_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="entity_id may only contain letters, numbers, _ and -, up to 50 characters.",
        )


async def _rollback_upload(db: AsyncSession) -> None:
    try:
        await db.rollback()
    except Exception:
        logger.warning("Attachment upload rollback failed", exc_info=True)


def _serialize_attachment_out(
    attachment: Attachment,
    *,
    vdr_sync: VdrSyncInfo | None = None,
) -> AttachmentOut:
    state = attachment.__dict__
    created_at = state.get("created_at") or datetime.now(UTC)
    updated_at = state.get("updated_at") or created_at
    return AttachmentOut(
        id=state["id"],
        transaction_id=state["transaction_id"],
        entity_type=state["entity_type"],
        entity_id=state.get("entity_id"),
        file_name=state["file_name"],
        file_size_bytes=state["file_size_bytes"],
        mime_type=state["mime_type"],
        processing_status=state.get("processing_status", PROCESSING_PENDING),
        processing_error=state.get("processing_error"),
        description=state.get("description"),
        uploaded_by_email=state.get("uploaded_by_email"),
        created_at=created_at,
        updated_at=updated_at,
        vdr_sync=vdr_sync,
    )


async def _load_vdr_sync_map(
    db: AsyncSession,
    attachments: list[Attachment],
) -> dict[uuid.UUID, VdrSyncInfo]:
    document_ids = [attachment.vdr_document_id for attachment in attachments if attachment.vdr_document_id is not None]
    if not document_ids:
        return {}

    result = await db.execute(
        select(
            VdrDocument.id,
            VdrFolder.name,
            VdrFolder.category,
            VdrDocument.classification_status,
        )
        .join(VdrFolder, VdrFolder.id == VdrDocument.folder_id)
        .where(VdrDocument.id.in_(document_ids))
    )
    doc_map: dict[uuid.UUID, VdrSyncInfo] = {}
    for doc_id, folder_name, category, classification_status in result.all():
        doc_map[doc_id] = VdrSyncInfo(
            vdr_document_id=doc_id,
            folder_name=folder_name,
            category=category.value if hasattr(category, "value") else category,
            classification_status=classification_status.value
            if hasattr(classification_status, "value")
            else str(classification_status),
        )

    attachment_map: dict[uuid.UUID, VdrSyncInfo] = {}
    for attachment in attachments:
        if attachment.vdr_document_id is not None and attachment.vdr_document_id in doc_map:
            attachment_map[attachment.id] = doc_map[attachment.vdr_document_id]
    return attachment_map


def _validate_magic_bytes(content: bytes, ext: str) -> None:
    if not content:
        return

    if ext in {".m4a"} and len(content) >= 8 and content[4:8] == b"ftyp":
        return

    for signature, valid_exts in _MAGIC_SIGNATURES:
        if content[: len(signature)] == signature:
            if ext not in valid_exts:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"파일 내용과 확장자({ext})가 일치하지 않습니다.",
                )
            return

    if ext in {".txt", ".csv"}:
        if b"\x00" in content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"파일 내용과 확장자({ext})가 일치하지 않습니다.",
            )
        return

    if ext not in {".aac"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"파일 내용과 확장자({ext})가 일치하지 않습니다.",
        )


async def _get_attachment_or_404(db: AsyncSession, txn_id: uuid.UUID, attachment_id: uuid.UUID) -> Attachment:
    attachment = (
        await db.execute(
            select(Attachment).where(
                Attachment.id == attachment_id,
                Attachment.transaction_id == txn_id,
            )
        )
    ).scalar_one_or_none()
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment was not found.")
    return attachment
