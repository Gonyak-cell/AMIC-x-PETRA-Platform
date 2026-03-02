"""범용 첨부파일 라우터 — 외부 자료 업로드/다운로드/삭제."""

from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.attachment import Attachment
from app.models.enums import AttachmentEntityType, AuditAction
from app.schemas.attachment import AttachmentListResponse, AttachmentOut
from app.services import audit_service, transaction_service

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "attachments"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
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
    # Audio (마케팅 로그 녹음 첨부)
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".aac",
    ".wma",
}
VALID_ENTITY_TYPES = {e.value for e in AttachmentEntityType}

router = APIRouter(
    prefix="/transactions/{txn_id}/attachments",
    tags=["Attachments"],
)


@router.get("", response_model=AttachmentListResponse)
async def list_attachments(
    txn_id: uuid.UUID,
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    q = select(Attachment).where(Attachment.transaction_id == txn_id)
    count_q = select(func.count(Attachment.id)).where(Attachment.transaction_id == txn_id)

    if entity_type:
        q = q.where(Attachment.entity_type == entity_type)
        count_q = count_q.where(Attachment.entity_type == entity_type)
    if entity_id:
        parsed_eid = _parse_uuid(entity_id, "entity_id")
        q = q.where(Attachment.entity_id == parsed_eid)
        count_q = count_q.where(Attachment.entity_id == parsed_eid)

    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(Attachment.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    items = [AttachmentOut.model_validate(a) for a in result.scalars().all()]
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
):
    await transaction_service.get_transaction(db, txn_id)

    # entity_type 검증
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 entity_type입니다. 허용: {', '.join(sorted(VALID_ENTITY_TYPES))}",
        )

    # 파일 크기 검증
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="파일 크기가 50MB를 초과합니다",
        )

    # 확장자 검증
    safe_filename = file.filename or "attachment"
    safe_filename = Path(safe_filename).name
    ext = Path(safe_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"허용되지 않는 파일 형식입니다. 허용: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # 파일 저장
    save_dir = UPLOAD_DIR / str(txn_id) / entity_type
    save_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4()
    dest_path = save_dir / f"{file_id}_{safe_filename}"

    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(content)

    parsed_entity_id = _parse_uuid(entity_id, "entity_id") if entity_id else None

    attachment = Attachment(
        transaction_id=txn_id,
        entity_type=entity_type,
        entity_id=parsed_entity_id,
        file_path=str(dest_path),
        file_name=safe_filename,
        file_size_bytes=len(content),
        mime_type=file.content_type or "application/octet-stream",
        description=description,
        uploaded_by_email=claims.email,
    )
    db.add(attachment)
    await db.flush()
    await audit_service.record(
        db,
        entity_type="Attachment",
        entity_id=attachment.id,
        action=AuditAction.CREATE,
        actor_email=claims.email,
        new_value={"entity_type": entity_type, "file_name": safe_filename},
    )
    await db.commit()
    await db.refresh(attachment)
    return AttachmentOut.model_validate(attachment)


@router.get("/{attachment_id}/download")
async def download_attachment(
    txn_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await check_client_deal_access(db, txn_id, claims)
    attachment = await _get_attachment_or_404(db, txn_id, attachment_id)

    file_path = Path(attachment.file_path)
    # 경로 탐색 방어
    try:
        file_path.resolve().relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="잘못된 파일 경로입니다")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

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
):
    await check_client_deal_access(db, txn_id, claims)
    attachment = await _get_attachment_or_404(db, txn_id, attachment_id)

    # 파일 삭제
    file_path = Path(attachment.file_path)
    if file_path.exists():
        file_path.unlink()

    await audit_service.record(
        db,
        entity_type="Attachment",
        entity_id=attachment.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(attachment)
    await db.commit()


# ── 헬퍼 ────────────────────────────────────────────────


def _parse_uuid(value: str | None, field_name: str = "id") -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"잘못된 UUID 형식입니다: {field_name}",
        )


async def _get_attachment_or_404(db: AsyncSession, txn_id: uuid.UUID, attachment_id: uuid.UUID) -> Attachment:
    q = select(Attachment).where(
        Attachment.id == attachment_id,
        Attachment.transaction_id == txn_id,
    )
    attachment = (await db.execute(q)).scalar_one_or_none()
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="첨부파일을 찾을 수 없습니다")
    return attachment
