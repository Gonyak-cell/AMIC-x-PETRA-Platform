"""RFI V2 첨부 파일 서비스 — 업로드, 매핑, 미할당 조회."""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.blob_storage import blob_client
from app.models.enums import AuditAction
from app.models.rfi_attachment import RFIAttachment
from app.services import audit_service

logger = logging.getLogger(__name__)


async def list_attachments(
    db: AsyncSession,
    txn_id: uuid.UUID,
) -> list[RFIAttachment]:
    """전체 첨부 목록."""
    result = await db.execute(
        select(RFIAttachment).where(RFIAttachment.transaction_id == txn_id).order_by(RFIAttachment.created_at.desc())
    )
    return list(result.scalars().all())


async def list_unassigned(
    db: AsyncSession,
    txn_id: uuid.UUID,
) -> list[RFIAttachment]:
    """미할당 파일 목록 (is_mapped=False)."""
    result = await db.execute(
        select(RFIAttachment).where(
            RFIAttachment.transaction_id == txn_id,
            RFIAttachment.is_mapped.is_(False),
        )
    )
    return list(result.scalars().all())


async def create_attachment(
    db: AsyncSession,
    txn_id: uuid.UUID,
    *,
    file_name: str,
    file_url: str,
    vdr_index: str | None = None,
    created_by: str | None = None,
) -> RFIAttachment:
    """첨부 파일 메타 생성 (is_mapped=False)."""
    attachment = RFIAttachment(
        transaction_id=txn_id,
        file_name=file_name,
        file_url=file_url,
        vdr_index=vdr_index,
    )
    db.add(attachment)
    await db.flush()

    await audit_service.log(db, txn_id, AuditAction.CREATE, "rfi_attachment", str(attachment.id), created_by)
    return attachment


async def map_attachment(
    db: AsyncSession,
    txn_id: uuid.UUID,
    file_id: uuid.UUID,
    *,
    item_id: uuid.UUID | None = None,
    thread_id: uuid.UUID | None = None,
    mapped_by: str | None = None,
) -> RFIAttachment:
    """수동 매핑 — item 또는 thread에 연결."""
    result = await db.execute(
        select(RFIAttachment).where(
            RFIAttachment.id == file_id,
            RFIAttachment.transaction_id == txn_id,
        )
    )
    attachment = result.scalar_one_or_none()
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="첨부 파일을 찾을 수 없습니다")

    if item_id is None and thread_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="item_id 또는 thread_id 중 하나를 지정해야 합니다",
        )

    attachment.item_id = item_id
    attachment.thread_id = thread_id
    attachment.is_mapped = True
    await db.flush()

    await audit_service.log(db, txn_id, AuditAction.UPDATE, "rfi_attachment", str(attachment.id), mapped_by)
    return attachment


async def delete_attachment(
    db: AsyncSession,
    txn_id: uuid.UUID,
    file_id: uuid.UUID,
    *,
    deleted_by: str | None = None,
) -> None:
    """첨부 파일 삭제."""
    result = await db.execute(
        select(RFIAttachment).where(
            RFIAttachment.id == file_id,
            RFIAttachment.transaction_id == txn_id,
        )
    )
    attachment = result.scalar_one_or_none()
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="첨부 파일을 찾을 수 없습니다")

    # Blob 파일 삭제 (DB 삭제 전 실행 — DB 롤백 시 Blob만 삭제되는 것이 고아 파일만 남는 것보다 안전)
    await blob_client.delete_blob(attachment.file_url)

    await db.delete(attachment)
    await db.flush()

    await audit_service.log(db, txn_id, AuditAction.DELETE, "rfi_attachment", str(file_id), deleted_by)


async def get_attachment(
    db: AsyncSession,
    txn_id: uuid.UUID,
    file_id: uuid.UUID,
) -> RFIAttachment:
    """첨부 파일 단건 조회 (txn 소유권 검증 포함)."""
    result = await db.execute(
        select(RFIAttachment).where(
            RFIAttachment.id == file_id,
            RFIAttachment.transaction_id == txn_id,
        )
    )
    attachment = result.scalar_one_or_none()
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="첨부 파일을 찾을 수 없습니다")
    return attachment
