"""범용 첨부파일 라우터 — 외부 자료 업로드/다운로드/삭제."""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from pathlib import Path

import aiofiles
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limiter import InMemoryRateLimiter
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.attachment import Attachment
from app.models.enums import AttachmentEntityType, AuditAction
from app.schemas.attachment import AttachmentListResponse, AttachmentOut, VdrSyncInfo
from app.services import audit_service, transaction_service
from app.services.attachment_vdr_bridge import sync_attachment_to_vdr
from app.services.vdr_service import check_vdr_write_permission

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "attachments"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# M1 fix: 업로드 Rate Limiter (VDR과 동일 수준: 분당 20건/사용자)
_upload_limiter = InMemoryRateLimiter(max_calls=20, window_seconds=60.0)
CHUNK_SIZE = 65_536  # 64 KB — 스트리밍 쓰기 단위
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

# entity_id 허용 패턴: 영문 대문자, 숫자, _, - (1~50자) 또는 UUID 형식
_ENTITY_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{1,50}$")

# 매직 바이트 → 실제 MIME 매핑 (확장자 위조 방지)
_MAGIC_SIGNATURES: list[tuple[bytes, set[str]]] = [
    (b"%PDF", {".pdf"}),
    (b"PK\x03\x04", {".docx", ".xlsx", ".pptx", ".zip", ".hwpx"}),
    (b"\x89PNG", {".png"}),
    (b"\xff\xd8\xff", {".jpg", ".jpeg"}),
    (b"HWP Document File", {".hwp"}),
    # OLE2 Compound Document (레거시 Office: .doc, .xls, .ppt)
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", {".doc", ".xls", ".ppt"}),
    # Audio
    (b"ID3", {".mp3"}),
    (b"\xff\xfb", {".mp3"}),  # MP3 프레임 헤더
    (b"fLaC", {".flac"}),
    (b"RIFF", {".wav"}),
    (b"OggS", {".ogg"}),
    # ASF/WMA
    (b"\x30\x26\xb2\x75", {".wma"}),
]

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
) -> AttachmentListResponse:
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    # entity_type 검증
    if entity_type and entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 entity_type입니다",
        )

    # entity_id 검증 (SEC-03)
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
    q = q.order_by(Attachment.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    items = [AttachmentOut.model_validate(a) for a in result.scalars().all()]
    return AttachmentListResponse(items=items, total=total)


@router.post("", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    txn_id: uuid.UUID,
    background_tasks: BackgroundTasks,
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

    # entity_type 검증
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 entity_type입니다",
        )

    # entity_id 검증 (SEC-03)
    if entity_id is not None:
        _validate_entity_id(entity_id)

    # 조기 크기 검사 — Starlette UploadFile.size 활용 (P-01)
    if file.size and file.size > MAX_FILE_SIZE:
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

    # 다중 확장자 차단 (예: file.jpg.exe)
    suffixes = Path(safe_filename).suffixes
    if len(suffixes) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="다중 확장자 파일은 허용되지 않습니다",
        )

    # 매직 바이트 검증 — 첫 32바이트만 읽어 확인 (P-01)
    header = await file.read(32)
    _validate_magic_bytes(header, ext)

    # 파일 저장 — 청크 스트리밍 (P-01: 전체 메모리 적재 방지)
    save_dir = UPLOAD_DIR / str(txn_id) / entity_type
    await asyncio.to_thread(save_dir.mkdir, parents=True, exist_ok=True)

    file_id = uuid.uuid4()
    dest_path = save_dir / f"{file_id}_{safe_filename}"

    total_size = len(header)
    size_exceeded = False
    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(header)
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                size_exceeded = True
                break
            await f.write(chunk)
    if size_exceeded:
        await asyncio.to_thread(dest_path.unlink, missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="파일 크기가 50MB를 초과합니다",
        )

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

    # M-1 fix: rollback 시 attachment 객체가 expire 되므로 미리 직렬화
    result = AttachmentOut.model_validate(attachment)

    # ── VDR 자동 연동 (best-effort) ──────────────────────
    # H1 fix: VDR 쓰기 권한이 있는 사용자만 연동 (ADMIN / lead_advisor / deal_captain)
    vdr_sync = None
    has_vdr_access = check_vdr_write_permission(
        claims.role,
        claims.email,
        txn.lead_advisor_email,
        txn.deal_captain_email,
    )
    if has_vdr_access:
        try:
            vdr_result = await sync_attachment_to_vdr(
                db,
                txn_id,
                attachment,
                dest_path,
                background_tasks,
            )
            if vdr_result:
                vdr_sync = VdrSyncInfo(
                    vdr_document_id=vdr_result.document.id,
                    folder_name=vdr_result.folder.name,
                    category=vdr_result.category,
                    classification_status=vdr_result.classification_status.value,
                )
        except Exception:
            await db.rollback()
            logger.warning("VDR 연동 실패: txn=%s, attachment=%s", txn_id, attachment.id, exc_info=True)

    result.vdr_sync = vdr_sync
    return result


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
) -> None:
    await check_client_deal_access(db, txn_id, claims)
    attachment = await _get_attachment_or_404(db, txn_id, attachment_id)

    file_path_str = attachment.file_path  # 삭제 전 경로 보존

    # DB 커밋 먼저 → 파일 삭제 best-effort (P-04: 원자성 역전 방지)
    await audit_service.record(
        db,
        entity_type="Attachment",
        entity_id=attachment.id,
        action=AuditAction.DELETE,
        actor_email=claims.email,
    )
    await db.delete(attachment)
    await db.commit()

    # 파일 삭제 — best-effort (DB 커밋 성공 후)
    try:
        file_path = Path(file_path_str)
        if file_path.exists():
            file_path.unlink()
    except OSError:
        logger.warning("파일 삭제 실패, 고아 파일 남음: %s", file_path_str)


# ── 헬퍼 ────────────────────────────────────────────────


def _validate_entity_id(entity_id: str) -> None:
    """entity_id 길이(50자)·허용 문자 검증 (SEC-03)."""
    if not _ENTITY_ID_PATTERN.match(entity_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="entity_id는 영문, 숫자, _, - 만 허용되며 50자 이내여야 합니다",
        )


def _validate_magic_bytes(content: bytes, ext: str) -> None:
    """파일 매직 바이트와 확장자 일치 여부를 검증한다."""
    if not content:
        return

    # M4A/MP4 ISO BMFF: offset 4에서 'ftyp' 확인
    if ext in {".m4a"} and len(content) >= 8 and content[4:8] == b"ftyp":
        return

    for signature, valid_exts in _MAGIC_SIGNATURES:
        if content[: len(signature)] == signature:
            if ext not in valid_exts:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"파일 내용이 확장자({ext})와 일치하지 않습니다",
                )
            return

    # 텍스트 계열 확장자: 널바이트 체크만 적용
    text_extensions = {".txt", ".csv"}
    if ext in text_extensions:
        if b"\x00" in content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"파일 내용이 텍스트 형식({ext})과 일치하지 않습니다",
            )
        return

    # deny-by-default: 매직 시그니처 미등록 확장자 차단 (.aac 등 시그니처 없는 오디오 제외)
    no_magic_allowed = {".aac"}
    if ext not in no_magic_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"파일 내용이 확장자({ext})와 일치하지 않습니다",
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
