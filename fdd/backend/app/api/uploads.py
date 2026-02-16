import hashlib
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException
from fastapi import UploadFile as FastAPIUploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.auth.rbac import Permission
from app.config import settings
from app.database import get_db
from app.models.audit import AuditAction, AuditLog
from app.models.deal import Deal
from app.models.upload import (
    IngestionStatus,
    UploadFile,
    ValidationSeverity,
)
from app.schemas.upload import (
    UploadFileConfirmType,
    UploadFileDetailRead,
    UploadFileIngestOptions,
    UploadFileRead,
)
from app.services.ingestion.type_detector import detect_upload_type

router = APIRouter()


# ── Upload Files ─────────────────────────────────────────


@router.post(
    "/deals/{deal_id}/uploads",
    response_model=UploadFileRead,
    status_code=201,
)
async def upload_file(
    deal_id: uuid.UUID,
    file: FastAPIUploadFile = File(...),
    current_user: CurrentUser = require_permission(Permission.UPLOAD_CREATE),
    db: Session = Depends(get_db),
):
    """Upload an Excel file and auto-detect its type."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Validate file extension
    filename = file.filename or "upload.xlsx"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".xlsx", ".xls"):
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx and .xls files are supported",
        )

    # Read content and compute hash
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate upload (same file hash in same deal)
    existing = db.scalar(
        select(UploadFile).where(
            UploadFile.deal_id == deal_id,
            UploadFile.file_hash == file_hash,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"This file has already been uploaded (upload_id: {existing.id})",
        )

    # Save to disk
    upload_dir = os.path.join(settings.upload_dir, str(deal_id))
    os.makedirs(upload_dir, exist_ok=True)
    file_id = uuid.uuid4()
    stored_filename = f"{file_id}{ext}"
    stored_path = os.path.join(upload_dir, stored_filename)
    with open(stored_path, "wb") as f:
        f.write(content)

    # Auto-detect type
    try:
        detection = detect_upload_type(stored_path)
    except Exception:
        detection = None

    upload_record = UploadFile(
        id=file_id,
        deal_id=deal_id,
        original_filename=filename,
        stored_path=stored_path,
        file_hash=file_hash,
        file_size_bytes=len(content),
        detected_type=detection.detected_type if detection else None,
        detection_confidence=detection.confidence if detection else None,
        status=IngestionStatus.PENDING,
    )
    db.add(upload_record)

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="upload_file",
            entity_id=file_id,
            action=AuditAction.CREATE,
            actor=current_user.email,
            new_value={
                "filename": filename,
                "file_hash": file_hash,
                "detected_type": (
                    detection.detected_type.value
                    if detection and detection.detected_type
                    else None
                ),
            },
        )
    )

    db.commit()
    db.refresh(upload_record)
    return upload_record


@router.get("/deals/{deal_id}/uploads", response_model=list[UploadFileRead])
def list_uploads(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all uploads for a deal."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    stmt = (
        select(UploadFile)
        .where(UploadFile.deal_id == deal_id)
        .order_by(UploadFile.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.get(
    "/deals/{deal_id}/uploads/{upload_id}",
    response_model=UploadFileDetailRead,
)
def get_upload(
    deal_id: uuid.UUID,
    upload_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get upload details including validation errors."""
    upload = db.get(UploadFile, upload_id)
    if upload is None or upload.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload


@router.put(
    "/deals/{deal_id}/uploads/{upload_id}/confirm-type",
    response_model=UploadFileRead,
)
def confirm_upload_type(
    deal_id: uuid.UUID,
    upload_id: uuid.UUID,
    body: UploadFileConfirmType,
    current_user: CurrentUser = require_permission(Permission.UPLOAD_CREATE),
    db: Session = Depends(get_db),
):
    """User overrides the auto-detected upload type."""
    upload = db.get(UploadFile, upload_id)
    if upload is None or upload.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Upload not found")

    old_type = upload.confirmed_type.value if upload.confirmed_type else None
    upload.confirmed_type = body.confirmed_type

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="upload_file",
            entity_id=upload_id,
            action=AuditAction.UPDATE,
            actor=current_user.email,
            old_value={"confirmed_type": old_type},
            new_value={"confirmed_type": body.confirmed_type.value},
        )
    )

    db.commit()
    db.refresh(upload)
    return upload


@router.post(
    "/deals/{deal_id}/uploads/{upload_id}/ingest",
    response_model=UploadFileRead,
)
def ingest_upload(
    deal_id: uuid.UUID,
    upload_id: uuid.UUID,
    body: UploadFileIngestOptions | None = None,
    current_user: CurrentUser = require_permission(Permission.UPLOAD_CREATE),
    db: Session = Depends(get_db),
):
    """Validate and ingest the uploaded Excel file into journal_entry table."""
    upload = db.get(UploadFile, upload_id)
    if upload is None or upload.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Upload not found")

    if upload.status not in (IngestionStatus.PENDING, IngestionStatus.FAILED):
        raise HTTPException(
            status_code=400,
            detail=f"Upload is in '{upload.status.value}' state, cannot ingest",
        )

    effective_type = upload.confirmed_type or upload.detected_type
    if effective_type is None:
        raise HTTPException(
            status_code=400,
            detail="Upload type not detected and not confirmed. Please confirm the type first.",
        )

    from app.services.ingestion.parser import ingest_file
    from app.services.ingestion.validator import validate_upload

    # Step 1: Validate
    upload.status = IngestionStatus.VALIDATING
    db.commit()

    try:
        val_errors = validate_upload(
            upload.stored_path, effective_type, upload_file_id=upload.id
        )
    except Exception as exc:
        upload.status = IngestionStatus.FAILED
        upload.error_message = f"Validation failed: {exc}"
        db.commit()
        db.refresh(upload)
        return upload

    for err in val_errors:
        db.add(err)
    db.commit()

    blocking_errors = [e for e in val_errors if e.severity == ValidationSeverity.ERROR]
    warning_count = len(val_errors) - len(blocking_errors)

    if blocking_errors:
        upload.status = IngestionStatus.FAILED
        upload.error_message = f"{len(blocking_errors)} validation error(s) found"
        upload.validation_summary = {
            "total_errors": len(blocking_errors),
            "total_warnings": warning_count,
        }
        db.commit()
        db.refresh(upload)
        return upload

    # Step 2: Ingest
    upload.status = IngestionStatus.INGESTING
    db.commit()

    deal = db.get(Deal, deal_id)
    try:
        result = ingest_file(
            db,
            upload,
            effective_type,
            user_period_date=body.period_date if body else None,
            deal_period_end=deal.reference_date if deal else None,
        )
    except Exception as exc:
        upload.status = IngestionStatus.FAILED
        upload.error_message = str(exc)
        db.commit()
        db.refresh(upload)
        return upload

    upload.total_rows = result.total_rows
    upload.rows_processed = result.rows_processed
    upload.status = IngestionStatus.COMPLETED
    upload.error_message = None
    upload.validation_summary = {
        "total_errors": 0,
        "total_warnings": warning_count,
        "rows_ingested": result.rows_processed,
        "rows_skipped": result.rows_skipped,
    }

    db.add(
        AuditLog(
            deal_id=deal_id,
            entity_type="upload_file",
            entity_id=upload_id,
            action=AuditAction.UPDATE,
            actor=current_user.email,
            old_value={"status": "INGESTING"},
            new_value={
                "status": "COMPLETED",
                "rows_ingested": result.rows_processed,
            },
        )
    )

    db.commit()
    db.refresh(upload)
    return upload
