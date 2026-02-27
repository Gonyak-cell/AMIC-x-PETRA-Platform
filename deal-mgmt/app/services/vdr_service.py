"""VDR (Virtual Data Room) 서비스 — 폴더 CRUD + 문서 업로드/다운로드."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.blob_storage import blob_client
from app.core.exceptions import DocumentNotFoundError
from app.models.enums import VdrDocumentStatus, VdrFolderCategory
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.schemas.vdr import VdrDocumentUpdate, VdrFolderCreate, VdrFolderUpdate

# M&A 실사 VDR 기본 폴더 (11개)
_DEFAULT_FOLDERS: list[tuple[VdrFolderCategory, str, bool]] = [
    (VdrFolderCategory.CORPORATE, "기업 일반", True),
    (VdrFolderCategory.FINANCIAL, "재무 자료", True),
    (VdrFolderCategory.LEGAL, "법률 자료", True),
    (VdrFolderCategory.TAX, "세무 자료", True),
    (VdrFolderCategory.HR, "인사/노무", False),
    (VdrFolderCategory.TECHNICAL, "기술/IT", False),
    (VdrFolderCategory.COMMERCIAL, "영업/마케팅", False),
    (VdrFolderCategory.REAL_ESTATE, "부동산/자산", False),
    (VdrFolderCategory.ENVIRONMENT, "환경", False),
    (VdrFolderCategory.IP, "지식재산권", False),
    (VdrFolderCategory.INSURANCE, "보험", False),
]


# ── 폴더 CRUD ────────────────────────────────────────────────


async def init_vdr_folders(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[VdrFolder]:
    """기본 VDR 폴더 구조를 생성한다. 이미 존재하면 예외 발생."""
    existing = await db.scalar(
        select(func.count()).select_from(VdrFolder).where(VdrFolder.transaction_id == transaction_id)
    )
    if existing and existing > 0:
        raise ValueError("이 거래의 VDR 폴더가 이미 초기화되어 있습니다.")

    created: list[VdrFolder] = []
    for idx, (category, name, is_required) in enumerate(_DEFAULT_FOLDERS):
        folder = VdrFolder(
            transaction_id=transaction_id,
            name=name,
            category=category,
            order_index=idx,
            is_required=is_required,
        )
        db.add(folder)
        created.append(folder)

    await db.commit()
    for f in created:
        await db.refresh(f)
    return created


async def list_folders(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[VdrFolder]:
    """거래의 모든 VDR 폴더를 order_index 순으로 조회."""
    q = (
        select(VdrFolder)
        .where(VdrFolder.transaction_id == transaction_id)
        .order_by(VdrFolder.order_index, VdrFolder.name)
    )
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_folder(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    folder_id: uuid.UUID,
) -> VdrFolder:
    """단일 폴더 조회. 없으면 DocumentNotFoundError."""
    q = select(VdrFolder).where(
        VdrFolder.id == folder_id,
        VdrFolder.transaction_id == transaction_id,
    )
    result = await db.execute(q)
    folder = result.scalar_one_or_none()
    if not folder:
        raise DocumentNotFoundError("VDR 폴더를 찾을 수 없습니다.")
    return folder


async def create_folder(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    body: VdrFolderCreate,
) -> VdrFolder:
    """새 커스텀 폴더를 생성한다."""
    if body.parent_id:
        await get_folder(db, transaction_id, body.parent_id)

    max_order = await db.scalar(
        select(func.max(VdrFolder.order_index)).where(
            VdrFolder.transaction_id == transaction_id,
            VdrFolder.parent_id == body.parent_id,
        )
    )
    next_order = (max_order or 0) + 1

    folder = VdrFolder(
        transaction_id=transaction_id,
        name=body.name,
        category=body.category,
        parent_id=body.parent_id,
        order_index=next_order,
        description=body.description,
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


async def update_folder(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    folder_id: uuid.UUID,
    body: VdrFolderUpdate,
) -> VdrFolder:
    """폴더 이름, 순서, 설명을 업데이트한다."""
    folder = await get_folder(db, transaction_id, folder_id)
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(folder, key, value)
    await db.commit()
    await db.refresh(folder)
    return folder


async def delete_folder(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    folder_id: uuid.UUID,
) -> None:
    """폴더를 삭제한다. is_required=True이면 거부."""
    folder = await get_folder(db, transaction_id, folder_id)
    if folder.is_required:
        raise ValueError("필수 폴더는 삭제할 수 없습니다.")
    await db.delete(folder)
    await db.commit()


# ── 문서 CRUD ────────────────────────────────────────────────


async def list_documents(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    folder_id: uuid.UUID,
) -> list[VdrDocument]:
    """폴더 내 활성 문서 목록 조회."""
    q = (
        select(VdrDocument)
        .where(
            VdrDocument.folder_id == folder_id,
            VdrDocument.transaction_id == transaction_id,
            VdrDocument.status == VdrDocumentStatus.ACTIVE,
        )
        .order_by(VdrDocument.created_at.desc())
    )
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_document(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    doc_id: uuid.UUID,
) -> VdrDocument:
    """단일 문서 조회."""
    q = select(VdrDocument).where(
        VdrDocument.id == doc_id,
        VdrDocument.transaction_id == transaction_id,
    )
    result = await db.execute(q)
    doc = result.scalar_one_or_none()
    if not doc:
        raise DocumentNotFoundError("VDR 문서를 찾을 수 없습니다.")
    return doc


async def upload_document(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    folder_id: uuid.UUID,
    original_name: str,
    file_content: bytes,
    mime_type: str,
    uploaded_by_email: str | None = None,
    description: str | None = None,
) -> VdrDocument:
    """파일을 Azure Blob(또는 로컬 폴백)에 저장하고 메타데이터를 DB에 기록한다."""
    await get_folder(db, transaction_id, folder_id)

    sha256 = hashlib.sha256(file_content).hexdigest()

    ext = Path(original_name).suffix.lower()
    stored_name = f"{uuid.uuid4()}{ext}"

    # blob_name = 상대 경로 (Azure Blob key 또는 로컬 상대 경로)
    blob_name = f"{transaction_id}/{folder_id}/{stored_name}"
    await blob_client.upload_blob(blob_name, file_content, mime_type)

    doc = VdrDocument(
        transaction_id=transaction_id,
        folder_id=folder_id,
        original_name=original_name,
        stored_name=stored_name,
        file_path=blob_name,
        file_size_bytes=len(file_content),
        mime_type=mime_type,
        sha256_hash=sha256,
        uploaded_by_email=uploaded_by_email,
        description=description,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def update_document(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    doc_id: uuid.UUID,
    body: VdrDocumentUpdate,
) -> VdrDocument:
    """문서 설명 수정 또는 폴더 이동."""
    doc = await get_document(db, transaction_id, doc_id)
    update_data = body.model_dump(exclude_unset=True)

    if update_data.get("folder_id"):
        await get_folder(db, transaction_id, update_data["folder_id"])

    for key, value in update_data.items():
        setattr(doc, key, value)
    await db.commit()
    await db.refresh(doc)
    return doc


async def delete_document(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    doc_id: uuid.UUID,
) -> None:
    """문서를 소프트 삭제한다 (상태를 DELETED로 변경)."""
    doc = await get_document(db, transaction_id, doc_id)
    doc.status = VdrDocumentStatus.DELETED
    await db.commit()


async def get_vdr_summary(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> dict:
    """VDR 요약 통계."""
    folder_count = (
        await db.scalar(select(func.count()).select_from(VdrFolder).where(VdrFolder.transaction_id == transaction_id))
        or 0
    )

    doc_stats = await db.execute(
        select(
            func.count().label("count"),
            func.coalesce(func.sum(VdrDocument.file_size_bytes), 0).label("total_size"),
        ).where(
            VdrDocument.transaction_id == transaction_id,
            VdrDocument.status == VdrDocumentStatus.ACTIVE,
        )
    )
    row = doc_stats.one()

    return {
        "total_folders": folder_count,
        "total_documents": row.count,
        "total_size_bytes": row.total_size,
        "initialized": folder_count > 0,
    }


async def get_all_vdr_overviews(db: AsyncSession) -> list[dict]:
    """모든 거래의 VDR 현황을 단일 쿼리로 조회한다."""
    from app.models.transaction import Transaction

    folder_sub = (
        select(
            VdrFolder.transaction_id,
            func.count().label("cnt"),
        )
        .group_by(VdrFolder.transaction_id)
        .subquery()
    )

    doc_sub = (
        select(
            VdrDocument.transaction_id,
            func.count().label("cnt"),
            func.coalesce(func.sum(VdrDocument.file_size_bytes), 0).label("total_size"),
            func.max(VdrDocument.created_at).label("last_upload"),
        )
        .where(VdrDocument.status == VdrDocumentStatus.ACTIVE)
        .group_by(VdrDocument.transaction_id)
        .subquery()
    )

    q = (
        select(
            Transaction.id,
            Transaction.name,
            Transaction.code_name,
            Transaction.phase,
            Transaction.status,
            func.coalesce(folder_sub.c.cnt, 0).label("total_folders"),
            func.coalesce(doc_sub.c.cnt, 0).label("total_documents"),
            func.coalesce(doc_sub.c.total_size, 0).label("total_size_bytes"),
            doc_sub.c.last_upload.label("last_upload_at"),
        )
        .outerjoin(folder_sub, folder_sub.c.transaction_id == Transaction.id)
        .outerjoin(doc_sub, doc_sub.c.transaction_id == Transaction.id)
        .where(Transaction.is_deleted.is_(False))
        .order_by(Transaction.updated_at.desc())
    )

    result = await db.execute(q)
    return [
        {
            "transaction_id": row.id,
            "transaction_name": row.name,
            "code_name": row.code_name,
            "phase": row.phase.value if hasattr(row.phase, "value") else str(row.phase),
            "status": row.status.value if hasattr(row.status, "value") else str(row.status),
            "vdr_initialized": row.total_folders > 0,
            "total_folders": row.total_folders,
            "total_documents": row.total_documents,
            "total_size_bytes": row.total_size_bytes,
            "last_upload_at": row.last_upload_at,
        }
        for row in result.all()
    ]


async def get_folder_document_counts(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> dict[uuid.UUID, int]:
    """각 폴더별 활성 문서 수를 반환한다."""
    q = (
        select(
            VdrDocument.folder_id,
            func.count().label("cnt"),
        )
        .where(
            VdrDocument.transaction_id == transaction_id,
            VdrDocument.status == VdrDocumentStatus.ACTIVE,
        )
        .group_by(VdrDocument.folder_id)
    )
    result = await db.execute(q)
    return {row.folder_id: row.cnt for row in result.all()}
