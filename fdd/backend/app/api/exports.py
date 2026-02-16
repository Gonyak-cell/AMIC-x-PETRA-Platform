"""Exports API — Phase 5 Portal endpoints."""

import io
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.models.export_record import ExportFormat, ExportModule, ExportStatus
from app.schemas.export_record import (
    BatchDownloadRequest,
    ExportRecordRead,
    PaginatedExports,
)
from app.services.export.export_service import (
    delete_export,
    get_export_by_id,
    get_exports_by_ids,
    list_exports,
)

router = APIRouter(tags=["exports"])

FORMAT_MEDIA_TYPES: dict[ExportFormat, str] = {
    ExportFormat.PDF: "application/pdf",
    ExportFormat.PPTX: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ExportFormat.CSV: "text/csv",
    ExportFormat.ZIP: "application/zip",
}


@router.get("/exports", response_model=PaginatedExports)
def list_export_records(
    module: ExportModule | None = Query(default=None),
    status: ExportStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = require_permission(Permission.EXPORT_READ),
    db: Session = Depends(get_db),
):
    """내보내기 기록을 페이징 조회한다."""
    items, total = list_exports(
        db, module=module, status=status, page=page, size=size
    )
    return PaginatedExports(
        items=[ExportRecordRead.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


# NOTE: /batch-download must be defined BEFORE /{export_id}/download
@router.post("/exports/batch-download")
def batch_download_exports(
    body: BatchDownloadRequest,
    current_user: CurrentUser = require_permission(Permission.EXPORT_READ),
    db: Session = Depends(get_db),
):
    """여러 내보내기 파일을 ZIP으로 일괄 다운로드한다."""
    records = get_exports_by_ids(db, body.export_ids)
    if not records:
        raise HTTPException(status_code=404, detail="No export records found")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for record in records:
            if (
                record.status != ExportStatus.COMPLETED
                or not record.file_path
                or not Path(record.file_path).exists()
            ):
                continue
            filename = f"{record.name}.{record.format.value}"
            zf.write(record.file_path, arcname=filename)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="exports-batch.zip"'},
    )


@router.get("/exports/{export_id}/download")
def download_export(
    export_id: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.EXPORT_READ),
    db: Session = Depends(get_db),
):
    """단일 내보내기 파일을 다운로드한다."""
    record = get_export_by_id(db, export_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Export record not found")
    if record.status != ExportStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Export is not completed")
    if not record.file_path or not Path(record.file_path).exists():
        raise HTTPException(status_code=404, detail="Export file not found on disk")

    file_path = Path(record.file_path)
    media_type = FORMAT_MEDIA_TYPES.get(record.format, "application/octet-stream")
    filename = f"{record.name}.{record.format.value}"

    return StreamingResponse(
        open(file_path, "rb"),  # noqa: SIM115
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/exports/{export_id}", status_code=204)
def delete_export_record(
    export_id: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.EXPORT_DELETE),
    db: Session = Depends(get_db),
):
    """내보내기 기록을 삭제한다."""
    deleted = delete_export(db, export_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Export record not found")
    return None
