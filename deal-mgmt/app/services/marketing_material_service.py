"""마케팅 자료 서비스 — memo_generator 기반 PPTX 생성 및 CRUD."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.exceptions import DocumentNotFoundError
from app.core.local_dev_schema_guard import (
    AttachmentUploadSchemaIssue,
    build_backend_attachment_upload_schema_required_detail,
    build_local_sqlite_upload_schema_rebuild_required_detail,
    classify_attachment_upload_schema_error,
    is_file_based_sqlite_database_url,
    is_local_sqlite_attachment_upload_schema_error,
    repair_attachment_upload_schema_if_needed,
)
from app.core.log_context import get_request_id
from app.models.attachment import Attachment
from app.models.enums import MarketingDocStatus, MarketingDocType, MarketingMaterialSourceMode
from app.models.marketing_material import MarketingMaterial
from app.schemas.marketing_material import DistributionUpdate, MarketingMaterialCreate
from app.services.text_extraction_service import TextExtractionService
from app.services.vdr_routing_service import get_routing_override_map
from app.services.vdr_service import check_vdr_write_permission
from app.services.workstream_router_service import (
    COMMON_WORKSTREAM,
    FDD_WORKSTREAM,
    VALUATION_WORKSTREAM,
    build_workstream_routing_summary,
    is_source_allowed_for_any_workstream,
    route_vdr_sources,
)
from app.tasks.attachment_tasks import (
    PROCESSING_FAILED,
    PROCESSING_PENDING,
    PROCESSING_SKIPPED,
    process_attachment_task,
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "generated" / "memorandum"
ATTACHMENT_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "attachments"
MAX_ATTACHMENT_FILE_SIZE = 50 * 1024 * 1024
ATTACHMENT_CHUNK_SIZE = 65_536
ATTACHMENT_FILE_NAME_MAX_LEN = 300
LEGACY_COMPAT_ATTACHMENT_FILE_NAME_MAX_LEN = 255
ATTACHMENT_FILE_PATH_MAX_LEN = 500
ATTACHMENT_STORAGE_PATH_SAFE_MAX_LEN = 240 if os.name == "nt" else ATTACHMENT_FILE_PATH_MAX_LEN
ATTACHMENT_STORAGE_BASENAME_MAX_BYTES = 255
ATTACHMENT_MIME_TYPE_MAX_LEN = 100
ATTACHMENT_UPLOADER_EMAIL_MAX_LEN = 255
VALUE_TOO_LONG_SQLSTATES = frozenset({"22001"})
VALUE_TOO_LONG_PATTERN = re.compile(
    r"value too long for type character varying\((?P<limit>\d+)\)",
    re.IGNORECASE,
)
ALLOWED_ATTACHMENT_EXTENSIONS = {
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
_ATTACHMENT_MAGIC_SIGNATURES: list[tuple[bytes, set[str]]] = [
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
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AttachmentUploadValueIssue:
    field: str
    reason: str
    max_length: int | None = None
    actual_length: int | None = None


def _validate_uploaded_file_signature(content: bytes, ext: str) -> None:
    if not content:
        return

    if ext == ".m4a" and len(content) >= 8 and content[4:8] == b"ftyp":
        return

    for signature, valid_exts in _ATTACHMENT_MAGIC_SIGNATURES:
        if content[: len(signature)] == signature:
            if ext not in valid_exts:
                raise HTTPException(status_code=400, detail="Uploaded file content does not match its extension.")
            return

    if ext in {".txt", ".csv"}:
        if b"\x00" in content:
            raise HTTPException(status_code=400, detail="Uploaded file content does not match its extension.")
        return

    if ext != ".aac":
        raise HTTPException(status_code=400, detail="Uploaded file content does not match its extension.")


def _log_marketing_upload_integrity_error(
    exc: IntegrityError,
    *,
    stage: str,
    transaction_id: uuid.UUID,
    entity_type: str,
    entity_id: str | None,
    marketing_material_id: uuid.UUID | None,
) -> None:
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    diag = getattr(orig, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    request_id = get_request_id()
    logger.exception(
        "Uploaded marketing material integrity error: request_id=%s stage=%s txn=%s entity_type=%s entity_id=%s marketing_material_id=%s sqlstate=%s constraint=%s",
        request_id,
        stage,
        transaction_id,
        entity_type,
        entity_id,
        marketing_material_id,
        sqlstate,
        constraint_name,
    )


def _build_upload_schema_failure_detail(
    *,
    stage: str,
    issue: AttachmentUploadSchemaIssue,
    database_url: str | None,
) -> str:
    request_id = get_request_id()
    if is_file_based_sqlite_database_url(database_url):
        return build_local_sqlite_upload_schema_rebuild_required_detail(
            stage=stage,
            issue=issue,
            request_id=request_id,
        )
    return build_backend_attachment_upload_schema_required_detail(
        stage=stage,
        issue=issue,
        request_id=request_id,
    )


def _truncate_filename_preserving_extension(filename: str, max_length: int) -> str:
    normalized = filename.strip() or "marketing-material"
    if len(normalized) <= max_length:
        return normalized

    suffix = Path(normalized).suffix
    if suffix and len(suffix) < max_length:
        stem = normalized[: -len(suffix)]
        trimmed_stem = stem[: max_length - len(suffix)].rstrip(" ._")
        if not trimmed_stem:
            trimmed_stem = "file"[: max_length - len(suffix)] or "f"
        return f"{trimmed_stem}{suffix}"

    return normalized[:max_length].rstrip(" ._") or normalized[:max_length]


def _fit_uploaded_attachment_filename(
    filename: str,
    *,
    save_dir: Path,
    file_id: uuid.UUID,
) -> str:
    max_path_length = min(ATTACHMENT_FILE_PATH_MAX_LEN, ATTACHMENT_STORAGE_PATH_SAFE_MAX_LEN)
    candidate = _truncate_filename_preserving_extension(
        filename,
        LEGACY_COMPAT_ATTACHMENT_FILE_NAME_MAX_LEN,
    )

    while len(f"{file_id}_{candidate}".encode()) > ATTACHMENT_STORAGE_BASENAME_MAX_BYTES:
        next_candidate = _truncate_filename_preserving_extension(candidate, len(candidate) - 1)
        if next_candidate == candidate:
            break
        candidate = next_candidate

    while len(str(save_dir / f"{file_id}_{candidate}")) > max_path_length:
        overflow = len(str(save_dir / f"{file_id}_{candidate}")) - max_path_length
        next_length = max(1, len(candidate) - overflow)
        next_candidate = _truncate_filename_preserving_extension(candidate, next_length)
        if next_candidate == candidate:
            break
        candidate = next_candidate

    candidate = _truncate_filename_preserving_extension(candidate, ATTACHMENT_FILE_NAME_MAX_LEN)
    if (
        len(f"{file_id}_{candidate}".encode()) > ATTACHMENT_STORAGE_BASENAME_MAX_BYTES
        or len(str(save_dir / f"{file_id}_{candidate}")) > max_path_length
    ):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file name is too long for secure storage. Shorten the file name and retry.",
        )
    return candidate


def _normalize_uploaded_attachment_mime_type(mime_type: str | None) -> str:
    normalized = (mime_type or "application/octet-stream").strip() or "application/octet-stream"
    if len(normalized) <= ATTACHMENT_MIME_TYPE_MAX_LEN:
        return normalized
    return "application/octet-stream"


def _normalize_uploaded_attachment_email(email: str | None) -> str | None:
    if email is None:
        return None
    normalized = email.strip()
    if not normalized:
        return None
    return normalized[:ATTACHMENT_UPLOADER_EMAIL_MAX_LEN]


def _classify_attachment_upload_value_error(
    exc: Exception,
    *,
    file_name: str,
    file_path: str | None,
    mime_type: str,
    uploaded_by_email: str | None,
) -> AttachmentUploadValueIssue | None:
    if not isinstance(exc, DBAPIError):
        return None

    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    message = " ".join(
        part for part in (str(exc), str(orig) if orig is not None else None, getattr(exc, "statement", None)) if part
    ).lower()
    if (
        sqlstate not in VALUE_TOO_LONG_SQLSTATES
        and "value too long for type character varying" not in message
        and "string data right truncation" not in message
    ):
        return None

    limit_match = VALUE_TOO_LONG_PATTERN.search(message)
    limit = int(limit_match.group("limit")) if limit_match else None

    candidates: list[tuple[str, int | None]] = [
        ("file_name", len(file_name)),
        ("file_path", len(file_path) if file_path is not None else None),
        ("mime_type", len(mime_type)),
        ("uploaded_by_email", len(uploaded_by_email) if uploaded_by_email is not None else None),
    ]
    for field_name, actual_length in candidates:
        if actual_length is None:
            continue
        if limit is None or actual_length > limit:
            return AttachmentUploadValueIssue(
                field=field_name,
                reason="value_too_long",
                max_length=limit,
                actual_length=actual_length,
            )
    return AttachmentUploadValueIssue(field="attachment_metadata", reason="value_too_long", max_length=limit)


def _build_upload_value_failure_detail(
    *,
    stage: str,
    issue: AttachmentUploadValueIssue,
) -> str:
    request_id = get_request_id()
    subject = {
        "file_name": "Uploaded file name",
        "file_path": "Stored attachment path",
        "mime_type": "Uploaded file content type",
        "uploaded_by_email": "Uploader email",
    }.get(issue.field, "Uploaded attachment metadata")
    action = (
        "Shorten the file name and retry."
        if issue.field in {"file_name", "file_path"}
        else "Retry the upload. If it keeps failing, contact support."
    )
    limit_detail = f" Backend limit is {issue.max_length} characters." if issue.max_length is not None else ""
    actual_detail = f" Received {issue.actual_length} characters." if issue.actual_length is not None else ""
    request_detail = f" If you need support, provide request ID {request_id}." if request_id else ""
    return (
        f"Uploaded marketing material failed during {stage}. "
        f"{subject} exceeded backend length limits."
        f"{limit_detail}"
        f"{actual_detail} "
        f"{action}"
        f"{request_detail}"
    ).strip()


def _log_marketing_upload_db_error(
    exc: DBAPIError,
    *,
    stage: str,
    transaction_id: uuid.UUID,
    marketing_material_id: uuid.UUID | None,
    schema_issue: AttachmentUploadSchemaIssue | None,
    value_issue: AttachmentUploadValueIssue | None = None,
) -> None:
    request_id = get_request_id()
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    table_name = getattr(diag, "table_name", None) or (schema_issue.table if schema_issue is not None else None)
    column_name = getattr(diag, "column_name", None) or (schema_issue.column if schema_issue is not None else None)
    constraint_name = getattr(diag, "constraint_name", None)
    statement = getattr(exc, "statement", None)
    logger.exception(
        "Uploaded marketing material database error: request_id=%s stage=%s txn=%s marketing_material_id=%s exc_class=%s orig_class=%s sqlstate=%s table=%s column=%s constraint=%s schema_reason=%s value_reason=%s value_field=%s value_limit=%s value_length=%s statement=%s",
        request_id,
        stage,
        transaction_id,
        marketing_material_id,
        exc.__class__.__name__,
        orig.__class__.__name__ if orig is not None else None,
        sqlstate,
        table_name,
        column_name,
        constraint_name,
        schema_issue.reason if schema_issue is not None else None,
        value_issue.reason if value_issue is not None else None,
        value_issue.field if value_issue is not None else None,
        value_issue.max_length if value_issue is not None else None,
        value_issue.actual_length if value_issue is not None else None,
        statement,
    )


def _apply_uploaded_material_fields(
    mat: MarketingMaterial,
    attachment: Attachment,
    *,
    doc_type: MarketingDocType,
    title: str,
    project_code: str | None,
    parameters: dict | None,
    distributed_to: list[str] | None,
    distributed_at: str | None,
    created_by_email: str | None,
) -> None:
    mat.doc_type = doc_type
    mat.title = title
    mat.project_code = project_code
    mat.status = MarketingDocStatus.READY
    mat.source_mode = MarketingMaterialSourceMode.UPLOADED.value
    mat.attachment_id = attachment.id
    mat.parameters = parameters
    mat.file_path = attachment.file_path
    mat.file_name = attachment.file_name
    mat.file_size_bytes = attachment.file_size_bytes
    mat.quality_status = "SKIPPED"
    mat.created_by_email = created_by_email or attachment.uploaded_by_email

    if attachment.entity_id != str(mat.id):
        attachment.entity_id = str(mat.id)

    if distributed_to is not None:
        mat.distributed_to = distributed_to
        mat.distributed_at = distributed_at or (datetime.now(UTC).isoformat() if distributed_to else None)
    elif distributed_at is not None:
        mat.distributed_at = distributed_at


async def _enqueue_uploaded_attachment_processing(
    db: AsyncSession,
    *,
    attachment: Attachment,
    transaction_id: uuid.UUID,
    marketing_material_id: uuid.UUID,
) -> None:
    if attachment.processing_status != PROCESSING_PENDING:
        return

    try:
        process_attachment_task.delay(str(attachment.id))
    except Exception as exc:
        logger.exception(
            "Uploaded marketing material attachment enqueue failed: txn=%s marketing_material_id=%s attachment_id=%s",
            transaction_id,
            marketing_material_id,
            attachment.id,
        )
        attachment.processing_status = PROCESSING_FAILED
        attachment.processing_error = f"Automatic post-processing could not be queued: {exc}"
        await db.commit()
        await db.refresh(attachment)


async def create_uploaded_marketing_material_from_file(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    *,
    file: UploadFile,
    doc_type: MarketingDocType,
    title: str,
    project_code: str | None = None,
    distributed_to: list[str] | None = None,
    distributed_at: str | None = None,
    created_by_email: str | None = None,
    uploader_role: str | None = None,
    lead_advisor_email: str | None = None,
    deal_captain_email: str | None = None,
) -> MarketingMaterial:
    upload_stage = "material_flush"
    dest_path: Path | None = None
    attachment: Attachment | None = None
    material: MarketingMaterial | None = None
    safe_filename = Path(file.filename or "marketing-material").name
    mime_type = "application/octet-stream"
    created_by_email = _normalize_uploaded_attachment_email(created_by_email)
    attempted_attachment_schema_repair = False

    try:
        ext = Path(safe_filename).suffix.lower()
        if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Unsupported file type.")

        upload_stage = "attachment_metadata_validate"
        header = await file.read(32)
        _validate_uploaded_file_signature(header, ext)
        save_dir = ATTACHMENT_UPLOAD_DIR / str(transaction_id) / "MARKETING_MATERIAL"
        await asyncio.to_thread(save_dir.mkdir, parents=True, exist_ok=True)

        file_id = uuid.uuid4()
        normalized_filename = _fit_uploaded_attachment_filename(
            safe_filename,
            save_dir=save_dir,
            file_id=file_id,
        )
        if normalized_filename != safe_filename:
            logger.warning(
                "Normalized uploaded marketing material filename for backend compatibility: request_id=%s txn=%s original=%s normalized=%s",
                get_request_id(),
                transaction_id,
                safe_filename,
                normalized_filename,
            )
            safe_filename = normalized_filename
        mime_type = _normalize_uploaded_attachment_mime_type(file.content_type)

        upload_stage = "attachment_file_write"
        dest_path = save_dir / f"{file_id}_{safe_filename}"
        total_size = len(header)
        size_exceeded = False

        async with aiofiles.open(dest_path, "wb") as dest:
            await dest.write(header)
            while True:
                chunk = await file.read(ATTACHMENT_CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_ATTACHMENT_FILE_SIZE:
                    size_exceeded = True
                    break
                await dest.write(chunk)

        if size_exceeded:
            await asyncio.to_thread(dest_path.unlink, missing_ok=True)
            raise HTTPException(status_code=413, detail="File size exceeds the 50MB limit.")

        has_vdr_access = check_vdr_write_permission(
            uploader_role,
            created_by_email,
            lead_advisor_email,
            deal_captain_email,
        )
        processing_status = PROCESSING_PENDING if has_vdr_access else PROCESSING_SKIPPED
        processing_error = None if has_vdr_access else "VDR sync was skipped because the uploader lacks write access."

        async def _persist_uploaded_marketing_material_once() -> tuple[MarketingMaterial, Attachment]:
            nonlocal upload_stage

            next_material = MarketingMaterial(
                transaction_id=transaction_id,
                doc_type=doc_type,
                title=title,
                project_code=project_code,
                status=MarketingDocStatus.DRAFT,
                source_mode=MarketingMaterialSourceMode.UPLOADED.value,
                quality_status="SKIPPED",
                created_by_email=created_by_email,
            )
            db.add(next_material)
            await db.flush()

            upload_stage = "attachment_db_flush"
            next_attachment = Attachment(
                transaction_id=transaction_id,
                entity_type="MARKETING_MATERIAL",
                entity_id=str(next_material.id),
                file_path=str(dest_path),
                file_name=safe_filename,
                file_size_bytes=total_size,
                mime_type=mime_type,
                uploaded_by_email=created_by_email,
                processing_status=processing_status,
                processing_error=processing_error,
            )
            db.add(next_attachment)
            await db.flush()

            upload_stage = "material_finalize"
            _apply_uploaded_material_fields(
                next_material,
                next_attachment,
                doc_type=doc_type,
                title=title,
                project_code=project_code,
                parameters=None,
                distributed_to=distributed_to,
                distributed_at=distributed_at,
                created_by_email=created_by_email,
            )

            upload_stage = "commit"
            await db.commit()
            return next_material, next_attachment

        while True:
            upload_stage = "material_flush"
            try:
                material, attachment = await _persist_uploaded_marketing_material_once()
                break
            except DBAPIError as exc:
                await db.rollback()
                db.expunge_all()
                schema_issue = classify_attachment_upload_schema_error(exc)
                value_issue = _classify_attachment_upload_value_error(
                    exc,
                    file_name=safe_filename,
                    file_path=str(dest_path) if dest_path is not None else None,
                    mime_type=mime_type,
                    uploaded_by_email=created_by_email,
                )
                _log_marketing_upload_db_error(
                    exc,
                    stage=upload_stage,
                    transaction_id=transaction_id,
                    marketing_material_id=material.id if material is not None else None,
                    schema_issue=schema_issue,
                    value_issue=value_issue,
                )

                if schema_issue is not None:
                    if is_local_sqlite_attachment_upload_schema_error(
                        exc,
                        database_url=settings.DATABASE_URL,
                    ):
                        logger.warning(
                            "Detected stale local SQLite uploaded marketing material schema: request_id=%s stage=%s txn=%s marketing_material_id=%s missing=%s",
                            get_request_id(),
                            upload_stage,
                            transaction_id,
                            material.id if material is not None else None,
                            schema_issue.qualified_column,
                        )
                        raise HTTPException(
                            status_code=500,
                            detail=_build_upload_schema_failure_detail(
                                stage=upload_stage,
                                issue=schema_issue,
                                database_url=settings.DATABASE_URL,
                            ),
                        ) from exc

                    if not attempted_attachment_schema_repair and schema_issue.repairable:
                        repair_result = await repair_attachment_upload_schema_if_needed(
                            database_url=settings.DATABASE_URL,
                            logger=logger,
                        )
                        if repair_result.repaired:
                            attempted_attachment_schema_repair = True
                            logger.warning(
                                "Retried uploaded marketing material flush after repairing uploaded schema: request_id=%s txn=%s missing_columns=%s",
                                get_request_id(),
                                transaction_id,
                                ", ".join(repair_result.qualified_missing_columns),
                            )
                            continue

                    raise HTTPException(
                        status_code=500,
                        detail=_build_upload_schema_failure_detail(
                            stage=upload_stage,
                            issue=schema_issue,
                            database_url=settings.DATABASE_URL,
                        ),
                    ) from exc

                if value_issue is not None:
                    raise HTTPException(
                        status_code=500,
                        detail=_build_upload_value_failure_detail(
                            stage=upload_stage,
                            issue=value_issue,
                        ),
                    ) from exc

                raise HTTPException(
                    status_code=500,
                    detail=f"Uploaded marketing material failed during {upload_stage}.",
                ) from exc
    except HTTPException:
        await db.rollback()
        if dest_path is not None:
            await asyncio.to_thread(dest_path.unlink, missing_ok=True)
        raise
    except IntegrityError as exc:
        await db.rollback()
        if dest_path is not None:
            await asyncio.to_thread(dest_path.unlink, missing_ok=True)
        _log_marketing_upload_integrity_error(
            exc,
            stage=upload_stage,
            transaction_id=transaction_id,
            entity_type="MARKETING_MATERIAL",
            entity_id=str(material.id) if material is not None else None,
            marketing_material_id=material.id if material is not None else None,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Uploaded marketing material failed during {upload_stage}.",
        ) from exc
    except DBAPIError as exc:
        await db.rollback()
        if dest_path is not None:
            await asyncio.to_thread(dest_path.unlink, missing_ok=True)
        schema_issue = classify_attachment_upload_schema_error(exc)
        value_issue = _classify_attachment_upload_value_error(
            exc,
            file_name=safe_filename,
            file_path=str(dest_path) if dest_path is not None else None,
            mime_type=mime_type,
            uploaded_by_email=created_by_email,
        )
        _log_marketing_upload_db_error(
            exc,
            stage=upload_stage,
            transaction_id=transaction_id,
            marketing_material_id=material.id if material is not None else None,
            schema_issue=schema_issue,
            value_issue=value_issue,
        )
        if schema_issue is not None:
            raise HTTPException(
                status_code=500,
                detail=_build_upload_schema_failure_detail(
                    stage=upload_stage,
                    issue=schema_issue,
                    database_url=settings.DATABASE_URL,
                ),
            ) from exc
        if value_issue is not None:
            raise HTTPException(
                status_code=500,
                detail=_build_upload_value_failure_detail(
                    stage=upload_stage,
                    issue=value_issue,
                ),
            ) from exc
        raise HTTPException(
            status_code=500,
            detail=f"Uploaded marketing material failed during {upload_stage}.",
        ) from exc
    except Exception as exc:
        await db.rollback()
        if dest_path is not None:
            await asyncio.to_thread(dest_path.unlink, missing_ok=True)
        logger.exception(
            "Uploaded marketing material failed: request_id=%s stage=%s txn=%s marketing_material_id=%s",
            get_request_id(),
            upload_stage,
            transaction_id,
            material.id if material is not None else None,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Uploaded marketing material failed during {upload_stage}.",
        ) from exc

    assert material is not None
    assert attachment is not None

    await db.refresh(material)
    await db.refresh(attachment)
    await _enqueue_uploaded_attachment_processing(
        db,
        attachment=attachment,
        transaction_id=transaction_id,
        marketing_material_id=material.id,
    )
    await db.refresh(material)
    return material


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
        )
        db.add(mat)
        await db.flush()

    _apply_uploaded_material_fields(
        mat,
        attachment,
        doc_type=body.doc_type,
        title=body.title,
        project_code=body.project_code,
        parameters=body.parameters,
        distributed_to=body.distributed_to,
        distributed_at=body.distributed_at,
        created_by_email=created_by_email,
    )

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
