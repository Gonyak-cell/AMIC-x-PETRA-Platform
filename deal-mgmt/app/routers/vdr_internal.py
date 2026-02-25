"""VDR 내부 API — IM 백엔드 전용.

deal-mgmt 서비스의 VDR 데이터를 IM 백엔드에서 조회할 수 있는
내부 전용 엔드포인트를 제공한다.

인증: 환경변수 INTERNAL_SERVICE_KEY 기반 (Bearer 토큰이 아닌 헤더 검증).
"""

from __future__ import annotations

import logging
import os
import uuid

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.enums import VdrDocumentStatus
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.schemas.vdr import VdrDocumentOut, VdrFolderOut
from app.services import vdr_service

router = APIRouter(
    prefix="/internal/vdr",
    tags=["VDR Internal"],
)

_INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "")
if not _INTERNAL_SERVICE_KEY:
    logger.warning(
        "INTERNAL_SERVICE_KEY 환경변수 미설정 — 내부 API 접근이 거부됩니다. "
        "프로덕션 배포 시 반드시 설정하세요."
    )

# IM 백엔드에서 파싱 가능한 MIME 타입
_PARSEABLE_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
}


async def _verify_internal_key(
    x_internal_key: str | None = Header(None, alias="X-Internal-Key"),
) -> None:
    """내부 서비스 키를 검증한다."""
    if x_internal_key != _INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=403, detail="Invalid internal service key")


@router.get(
    "/transactions/{txn_id}/documents",
    response_model=list[VdrDocumentOut],
    summary="파서 가능한 VDR 문서 메타 목록 조회",
    dependencies=[Depends(_verify_internal_key)],
)
async def list_parseable_documents(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[VdrDocumentOut]:
    """거래의 VDR에서 파서가 처리 가능한 문서 메타 목록을 반환한다.

    Excel, PDF, CSV 파일만 필터링한다.
    """
    stmt = (
        select(VdrDocument)
        .where(
            VdrDocument.transaction_id == txn_id,
            VdrDocument.status == VdrDocumentStatus.UPLOADED,
            VdrDocument.mime_type.in_(_PARSEABLE_MIME_TYPES),
        )
        .order_by(VdrDocument.created_at.desc())
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [VdrDocumentOut.model_validate(d) for d in docs]


@router.get(
    "/transactions/{txn_id}/documents/{doc_id}/metadata",
    response_model=VdrDocumentOut,
    summary="단일 VDR 문서 메타데이터 조회",
    dependencies=[Depends(_verify_internal_key)],
)
async def get_document_metadata(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> VdrDocumentOut:
    """단일 VDR 문서의 메타데이터를 반환한다."""
    stmt = select(VdrDocument).where(
        VdrDocument.id == doc_id,
        VdrDocument.transaction_id == txn_id,
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="VDR 문서를 찾을 수 없습니다.")
    return VdrDocumentOut.model_validate(doc)


@router.get(
    "/transactions/{txn_id}/documents/{doc_id}/file-path",
    summary="VDR 문서 파일 경로 조회 (내부 전용)",
    dependencies=[Depends(_verify_internal_key)],
)
async def get_document_file_path(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """VDR 문서의 실제 파일 경로를 반환한다.

    Docker 공유 볼륨 내 경로를 반환하므로 IM 백엔드에서
    직접 파일을 읽을 수 있다.
    """
    stmt = select(VdrDocument).where(
        VdrDocument.id == doc_id,
        VdrDocument.transaction_id == txn_id,
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="VDR 문서를 찾을 수 없습니다.")

    storage_path = vdr_service.VDR_STORAGE_DIR / str(txn_id) / str(doc_id)
    if not storage_path.exists():
        raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다.")

    # 공유 볼륨 경로로 변환
    shared_path = f"/vdr-shared/{txn_id}/{doc_id}"

    return {
        "file_path": shared_path,
        "original_name": doc.original_name,
        "mime_type": doc.mime_type,
        "file_size_bytes": str(doc.file_size_bytes),
    }


@router.get(
    "/transactions/{txn_id}/folders",
    response_model=list[VdrFolderOut],
    summary="VDR 폴더 목록 조회",
    dependencies=[Depends(_verify_internal_key)],
)
async def list_folders(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[VdrFolderOut]:
    """거래의 VDR 폴더 목록을 반환한다."""
    stmt = (
        select(VdrFolder)
        .where(VdrFolder.transaction_id == txn_id)
        .order_by(VdrFolder.order_index)
    )
    result = await db.execute(stmt)
    folders = result.scalars().all()
    return [VdrFolderOut.model_validate(f) for f in folders]
