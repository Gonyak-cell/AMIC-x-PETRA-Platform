from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.attachment import Attachment
from app.models.enums import AuditAction
from app.models.nda import NDA
from app.models.nda_markup import NdaMarkup
from app.schemas.nda_markup import NdaMarkupListResponse, NdaMarkupOut
from app.services import audit_service, transaction_service

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "nda_markups"
ATTACHMENT_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "attachments"
MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {".docx", ".doc", ".pdf", ".xlsx", ".xls", ".pptx", ".ppt", ".hwp", ".hwpx", ".txt"}
_VERSION_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

router = APIRouter(prefix="/transactions/{txn_id}/ndas/{nda_id}/markups", tags=["NDA Markups"])


@router.get("", response_model=NdaMarkupListResponse)
async def list_nda_markups(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> NdaMarkupListResponse:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await _get_nda_or_404(db, txn_id, nda_id)

    total = (
        await db.execute(select(func.count(NdaMarkup.id)).where(NdaMarkup.nda_id == nda_id))
    ).scalar() or 0
    result = await db.execute(
        select(NdaMarkup)
        .where(NdaMarkup.nda_id == nda_id)
        .order_by(NdaMarkup.version_number.asc())
        .offset(offset)
        .limit(limit)
    )
    items = [NdaMarkupOut.model_validate(item) for item in result.scalars().all()]
    return NdaMarkupListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{markup_id}", response_model=NdaMarkupOut)
async def get_nda_markup(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    markup_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> NdaMarkupOut:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await _get_nda_or_404(db, txn_id, nda_id)
    markup = await _get_markup_or_404(db, nda_id, markup_id)
    return NdaMarkupOut.model_validate(markup)


@router.post("", response_model=NdaMarkupOut, status_code=201)
async def create_nda_markup(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    file: UploadFile | None = File(None),
    attachment_id: uuid.UUID | None = Form(None),
    version_label: str = Form(...),
    version_date: str = Form(...),
    source_party: str | None = Form(None),
    markup_type: str | None = Form(None),
    changes_summary: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> NdaMarkupOut:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    nda = await _get_nda_or_404(db, txn_id, nda_id)

    if not _VERSION_DATE_RE.match(version_date):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="version_date must use YYYY-MM-DD.")
    if (file is None) == (attachment_id is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of file or attachment_id.",
        )

    source_attachment: Attachment | None = None
    temp_path: Path | None = None

    if attachment_id is not None:
        source_attachment = await _get_attachment_source_or_404(db, txn_id, nda_id, attachment_id)
        existing_markup = (
            await db.execute(
                select(NdaMarkup).where(
                    NdaMarkup.nda_id == nda_id,
                    NdaMarkup.attachment_id == attachment_id,
                )
            )
        ).scalar_one_or_none()
        if existing_markup is not None:
            return NdaMarkupOut.model_validate(existing_markup)

        content = await run_in_threadpool(Path(source_attachment.file_path).read_bytes)
        safe_filename = Path(source_attachment.file_name or "markup").name
        file_path = source_attachment.file_path
        file_size_bytes = source_attachment.file_size_bytes
        mime_type = source_attachment.mime_type or "application/octet-stream"
    else:
        assert file is not None
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="File size exceeds the 50MB limit.")

        safe_filename = Path(file.filename or "markup").name
        ext = Path(safe_filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type.")

        nda_dir = UPLOAD_DIR / str(nda.id)
        nda_dir.mkdir(parents=True, exist_ok=True)
        temp_path = nda_dir / f"pending_{safe_filename}"
        async with aiofiles.open(temp_path, "wb") as dest:
            await dest.write(content)
        file_path = str(temp_path)
        file_size_bytes = len(content)
        mime_type = file.content_type or "application/octet-stream"

    await db.execute(select(NDA).where(NDA.id == nda_id).with_for_update())
    max_ver = (
        await db.execute(select(func.max(NdaMarkup.version_number)).where(NdaMarkup.nda_id == nda_id))
    ).scalar() or 0
    next_ver = max_ver + 1

    if temp_path is not None:
        final_path = temp_path.with_name(f"{next_ver}_{safe_filename}")
        if final_path != temp_path:
            temp_path.replace(final_path)
        file_path = str(final_path)

    markup = NdaMarkup(
        nda_id=nda_id,
        attachment_id=source_attachment.id if source_attachment else None,
        version_label=version_label,
        version_number=next_ver,
        version_date=version_date,
        source_party=source_party,
        markup_type=markup_type,
        file_path=file_path,
        file_name=safe_filename,
        file_size_bytes=file_size_bytes,
        changes_summary=changes_summary,
        created_by_email=claims.email,
    )
    db.add(markup)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="NdaMarkup",
        entity_id=markup.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value={"version": next_ver, "label": version_label, "date": version_date},
    )

    try:
        async with db.begin_nested():
            from app.models.enums import UploadSource
            from app.services import document_version_service

            doc_master = await document_version_service.find_or_create_for_nda(
                db,
                transaction_id=txn_id,
                nda_id=nda_id,
                doc_name=version_label,
                created_by_email=claims.email,
            )
            await document_version_service.upload_revision(
                db,
                document_id=doc_master.id,
                file_content=content,
                file_name=safe_filename,
                mime_type=mime_type,
                upload_source=UploadSource.NDA_MARKUP,
                changes_summary=changes_summary,
                uploaded_by_email=claims.email,
                source_entity_type="NdaMarkup",
                source_entity_id=str(markup.id),
            )
    except Exception:
        logger.error(
            "VCS sync failed for NDA markup: nda_id=%s markup_id=%s",
            nda_id,
            markup.id,
            exc_info=True,
        )

    try:
        await db.commit()
    except Exception:
        if temp_path is not None and Path(file_path).exists():
            Path(file_path).unlink(missing_ok=True)
        raise

    await db.refresh(markup)
    return NdaMarkupOut.model_validate(markup)


@router.get("/{markup_id}/download")
async def download_nda_markup(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    markup_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> FileResponse:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await _get_nda_or_404(db, txn_id, nda_id)
    markup = await _get_markup_or_404(db, nda_id, markup_id)

    if not markup.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Markup file was not found.")

    file_path = Path(markup.file_path)
    _validate_markup_file_path(file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Markup file was not found.")

    return FileResponse(
        path=str(file_path),
        filename=markup.file_name or file_path.name,
        media_type="application/octet-stream",
    )


@router.delete("/{markup_id}", status_code=204)
async def delete_nda_markup(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    markup_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> None:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await _get_nda_or_404(db, txn_id, nda_id)
    markup = await _get_markup_or_404(db, nda_id, markup_id)

    if markup.attachment_id is None:
        _try_delete_file(markup.file_path)
    _try_delete_file(markup.redline_file_path)

    await audit_service.record(
        db,
        entity_type="NdaMarkup",
        entity_id=markup.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(markup)
    await db.commit()


@router.post(
    "/{markup_id}/generate-redline",
    responses={
        200: {
            "description": "Redline DOCX file",
            "headers": {
                "X-Issues-Count": {"description": "Detected issue count", "schema": {"type": "integer"}},
                "X-Skipped-Count": {"description": "Skipped item count", "schema": {"type": "integer"}},
            },
        }
    },
)
async def generate_nda_redline(
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    markup_id: uuid.UUID,
    base_markup_id: str | None = Form(None),
    party_side: str = Form("SELL"),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> StreamingResponse:
    from app.services import nda_analysis_service, redline_engine

    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    nda = await _get_nda_or_404(db, txn_id, nda_id)
    current_markup = await _get_markup_or_404(db, nda_id, markup_id)

    if not current_markup.file_path or not Path(current_markup.file_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current markup file was not found.")

    if party_side not in ("SELL", "BUY"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="party_side must be SELL or BUY.")
    if not current_markup.file_path.lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redline generation is only supported for DOCX files.",
        )

    current_file_path = Path(current_markup.file_path)
    _validate_markup_file_path(current_file_path)
    current_bytes = await run_in_threadpool(current_file_path.read_bytes)

    reference_text: str
    base_id = _parse_optional_uuid(base_markup_id) if base_markup_id else None

    if base_id:
        base_markup = await _get_markup_or_404(db, nda_id, base_id)
        if not base_markup.file_path or not Path(base_markup.file_path).exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Base markup file was not found.")
        base_path = Path(base_markup.file_path)
        _validate_markup_file_path(base_path)
        reference_text = await run_in_threadpool(lambda: redline_engine.extract_paragraphs_text(base_path.read_bytes()))
    else:
        prev_markup = (
            await db.execute(
                select(NdaMarkup)
                .where(
                    NdaMarkup.nda_id == nda_id,
                    NdaMarkup.version_number < current_markup.version_number,
                )
                .order_by(NdaMarkup.version_number.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if prev_markup and prev_markup.file_path and Path(prev_markup.file_path).exists():
            prev_path = Path(prev_markup.file_path)
            _validate_markup_file_path(prev_path)
            reference_text = await run_in_threadpool(lambda: redline_engine.extract_paragraphs_text(prev_path.read_bytes()))
            base_id = prev_markup.id
        else:
            reference_text = "(No prior version available for comparison.)"

    try:
        (
            result_docx,
            cost,
            model_name,
            issues_count,
            skipped_count,
            _skipped_reasons,
        ) = await nda_analysis_service.generate_nda_redline(
            current_bytes,
            reference_text,
            nda_type=nda.nda_type.value if hasattr(nda.nda_type, "value") else str(nda.nda_type),
            party_side=party_side,
            owner_user_id=claims.email or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("NDA redline generation failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redline generation failed temporarily. Please try again.",
        ) from exc

    nda_dir = UPLOAD_DIR / str(nda_id)
    nda_dir.mkdir(parents=True, exist_ok=True)
    redline_path = nda_dir / f"{current_markup.version_number}_redline.docx"
    async with aiofiles.open(redline_path, "wb") as dest:
        await dest.write(result_docx.getvalue())

    current_markup.redline_file_path = str(redline_path)
    current_markup.redline_issues_count = issues_count
    current_markup.base_version_id = base_id
    await audit_service.record(
        db,
        entity_type="NdaMarkup",
        entity_id=current_markup.id,
        action=AuditAction.UPDATE,
        actor_email=claims.email,
        new_value={
            "action": "generate_redline",
            "issues_count": issues_count,
            "skipped_count": skipped_count,
            "cost_usd": cost,
            "model": model_name,
        },
    )
    await db.commit()

    result_docx.seek(0)
    safe_name = f"NDA_v{current_markup.version_number}_redline.docx"
    return StreamingResponse(
        result_docx,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "X-Issues-Count": str(issues_count),
            "X-Skipped-Count": str(skipped_count),
        },
    )


def _parse_optional_uuid(value: str | None) -> uuid.UUID | None:
    if not value or not value.strip():
        return None
    try:
        return uuid.UUID(value.strip())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid UUID: {value}") from exc


def _try_delete_file(file_path_str: str | None) -> None:
    if not file_path_str:
        return
    try:
        file_path = Path(file_path_str)
        if file_path.exists():
            file_path.unlink()
    except OSError:
        logger.warning("Markup file cleanup failed: %s", file_path_str)


def _validate_markup_file_path(file_path: Path) -> None:
    resolved = file_path.resolve()
    allowed_roots = (UPLOAD_DIR.resolve(), ATTACHMENT_UPLOAD_DIR.resolve())
    if not any(_is_relative_to(resolved, root) for root in allowed_roots):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid markup file path.")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


async def _get_nda_or_404(db: AsyncSession, txn_id: uuid.UUID, nda_id: uuid.UUID) -> NDA:
    nda = (
        await db.execute(select(NDA).where(NDA.id == nda_id, NDA.transaction_id == txn_id))
    ).scalar_one_or_none()
    if nda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NDA was not found.")
    return nda


async def _get_markup_or_404(db: AsyncSession, nda_id: uuid.UUID, markup_id: uuid.UUID) -> NdaMarkup:
    markup = (
        await db.execute(
            select(NdaMarkup).where(
                NdaMarkup.id == markup_id,
                NdaMarkup.nda_id == nda_id,
            )
        )
    ).scalar_one_or_none()
    if markup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NDA markup was not found.")
    return markup


async def _get_attachment_source_or_404(
    db: AsyncSession,
    txn_id: uuid.UUID,
    nda_id: uuid.UUID,
    attachment_id: uuid.UUID,
) -> Attachment:
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
    if attachment.entity_type != "NDA":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attachment is not an NDA attachment.")
    if attachment.entity_id not in {None, str(nda_id)}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attachment belongs to a different NDA scope.",
        )
    attachment_path = Path(attachment.file_path)
    if not attachment_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file was not found.")
    return attachment
