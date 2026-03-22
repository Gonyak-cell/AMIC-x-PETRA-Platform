"""VDR (Virtual Data Room) 서비스 — 폴더 CRUD + 문서 업로드/다운로드."""

from __future__ import annotations

import hashlib
import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from fastapi import UploadFile

from app.core.blob_storage import blob_client
from app.core.exceptions import DocumentNotFoundError
from app.models.enums import VdrDocumentStatus, VdrFolderCategory
from app.models.vdr_document import VdrDocument
from app.models.vdr_folder import VdrFolder
from app.schemas.vdr import VdrDocumentUpdate, VdrFolderCreate, VdrFolderUpdate

logger = logging.getLogger(__name__)

# 스트리밍 읽기 청크 크기: 1 MB
_CHUNK_SIZE = 1 * 1024 * 1024

# M&A 실사 VDR 기본 폴더 (12개)
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
    (VdrFolderCategory.MARKET_RESEARCH, "시장자료", False),
]


# ── VDR 권한 ─────────────────────────────────────────────────

_VDR_WRITE_ROLES = frozenset({"ADMIN"})


def check_vdr_write_permission(
    role: str,
    email: str | None,
    lead_advisor_email: str | None,
    deal_captain_email: str | None,
) -> bool:
    """VDR 쓰기 권한을 확인한다. ADMIN 또는 lead_advisor/deal_captain이면 True."""
    if role in _VDR_WRITE_ROLES:
        return True
    return bool(email and email in (lead_advisor_email, deal_captain_email))


# ── 폴더 CRUD ────────────────────────────────────────────────


def create_default_folders(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[VdrFolder]:
    """기본 VDR 폴더를 db.add만 수행한다 (commit 없음).

    호출자가 트랜잭션을 직접 관리할 때 사용 (예: create_transaction).
    독립 호출 시에는 init_vdr_folders()를 사용.
    """
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


async def list_all_documents(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[VdrDocument]:
    """거래의 전체 활성 문서 목록을 조회한다 (폴더 무관)."""
    q = (
        select(VdrDocument)
        .where(
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
    *,
    _folder_verified: bool = False,
    auto_commit: bool = True,
) -> VdrDocument:
    """파일을 Azure Blob(또는 로컬 폴백)에 저장하고 메타데이터를 DB에 기록한다.

    Args:
        _folder_verified: True이면 폴더 존재 확인을 건너뛴다.
            auto_upload_document()처럼 이미 폴더를 검증한 호출자 전용.
        auto_commit: False이면 db.commit()을 건너뛴다.
            호출자가 추가 변경 후 직접 커밋할 때 사용 (이중 커밋 방지).
    """
    if not _folder_verified:
        await get_folder(db, transaction_id, folder_id)

    import asyncio

    sha256 = await asyncio.to_thread(hashlib.sha256, file_content)
    sha256_hex = sha256.hexdigest()

    ext = Path(original_name).suffix.lower()
    stored_name = f"{uuid.uuid4()}{ext}"

    # blob_name = 상대 경로 (Azure Blob key 또는 로컬 상대 경로)
    blob_name = f"{transaction_id}/{folder_id}/{stored_name}"
    await blob_client.ensure_initialized()
    await blob_client.upload_blob(blob_name, file_content, mime_type)

    doc = VdrDocument(
        transaction_id=transaction_id,
        folder_id=folder_id,
        original_name=original_name,
        stored_name=stored_name,
        file_path=blob_name,
        file_size_bytes=len(file_content),
        mime_type=mime_type,
        sha256_hash=sha256_hex,
        uploaded_by_email=uploaded_by_email,
        description=description,
    )
    db.add(doc)
    if auto_commit:
        try:
            await db.commit()
            await db.refresh(doc)
        except Exception:
            await db.rollback()
            try:
                await blob_client.delete_blob(blob_name)
            except Exception as cleanup_err:
                logger.warning("고아 blob 삭제 실패: %s (error=%s)", blob_name, cleanup_err)
            raise
    else:
        await db.flush()
    return doc


async def upload_document_stream(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    folder_id: uuid.UUID,
    original_name: str,
    file_obj: UploadFile,
    file_size: int,
    sha256_hex: str,
    mime_type: str,
    uploaded_by_email: str | None = None,
    description: str | None = None,
    *,
    _folder_verified: bool = False,
    auto_commit: bool = True,
) -> VdrDocument:
    """UploadFile을 스트리밍으로 Azure Blob에 저장하고 메타데이터를 DB에 기록한다.

    upload_document()의 스트리밍 변형. SHA256과 file_size는 사전 계산된 값을 사용하여
    중복 해시 계산과 메모리 전체 로드를 제거한다. 메모리: O(1MB).

    Args:
        file_obj: Starlette UploadFile (seek(0) 상태여야 함).
        file_size: stream_hash_and_size()로 사전 계산된 파일 크기.
        sha256_hex: stream_hash_and_size()로 사전 계산된 SHA256 해시.
        _folder_verified: True이면 폴더 존재 확인을 건너뛴다.
        auto_commit: False이면 db.commit()을 건너뛴다.
    """
    if not _folder_verified:
        await get_folder(db, transaction_id, folder_id)

    ext = Path(original_name).suffix.lower()
    stored_name = f"{uuid.uuid4()}{ext}"

    blob_name = f"{transaction_id}/{folder_id}/{stored_name}"
    await blob_client.ensure_initialized()
    await blob_client.upload_blob_stream(blob_name, file_obj, mime_type, file_size)

    doc = VdrDocument(
        transaction_id=transaction_id,
        folder_id=folder_id,
        original_name=original_name,
        stored_name=stored_name,
        file_path=blob_name,
        file_size_bytes=file_size,
        mime_type=mime_type,
        sha256_hash=sha256_hex,
        uploaded_by_email=uploaded_by_email,
        description=description,
    )
    db.add(doc)
    if auto_commit:
        try:
            await db.commit()
            await db.refresh(doc)
        except Exception:
            await db.rollback()
            try:
                await blob_client.delete_blob(blob_name)
            except Exception as cleanup_err:
                logger.warning("고아 blob 삭제 실패: %s (error=%s)", blob_name, cleanup_err)
            raise
    else:
        await db.flush()
    return doc


async def stream_hash_and_size(
    file: UploadFile,
    max_file_size: int,
) -> tuple[str, int]:
    """청크 단위로 SHA256 해시와 파일 크기를 계산한다.

    메모리 사용량: O(_CHUNK_SIZE) ≈ 1MB.
    완료 후 file.seek(0)으로 포인터를 리셋하여 후속 blob 업로드에 재사용 가능하다.

    Args:
        file: Starlette UploadFile (내부적으로 SpooledTemporaryFile 사용).
        max_file_size: 최대 허용 파일 크기 (바이트). 초과 시 HTTPException 413.

    Returns:
        (sha256_hex, total_bytes)
    """
    from fastapi import HTTPException, status

    hasher = hashlib.sha256()
    total = 0
    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"파일 크기가 최대 허용량({max_file_size // 1024 // 1024}MB)을 초과합니다.",
            )
        hasher.update(chunk)
    await file.seek(0)
    return hasher.hexdigest(), total


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
    """문서를 소프트 삭제하고, 관련 추출 데이터를 정리한다."""
    doc = await get_document(db, transaction_id, doc_id)
    doc.status = VdrDocumentStatus.DELETED

    # 관련 extraction 정리 + corporate_info 리셋
    await _cleanup_extractions_for_document(db, transaction_id, doc_id)

    await db.commit()


async def _cleanup_extractions_for_document(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    doc_id: uuid.UUID,
) -> None:
    """삭제된 문서에 연결된 추출 데이터를 정리한다."""
    from app.models.document_extraction import DocumentExtraction
    from app.models.transaction import Transaction

    result = await db.execute(
        select(DocumentExtraction).where(
            DocumentExtraction.vdr_document_id == doc_id,
            DocumentExtraction.transaction_id == transaction_id,
        )
    )
    extractions = result.scalars().all()
    if not extractions:
        return

    txn = await db.get(Transaction, transaction_id)
    if not txn:
        return

    registry_keys = {
        "company_name",
        "representative_name",
        "establishment_date",
        "corporate_registration_number",
        "head_office_address",
        "capital_amount",
        "total_shares_issued",
        "par_value_per_share",
        "common_shares",
        "preferred_shares",
        "directors",
        "corporate_purpose",
    }
    biz_keys = {"business_registration_number", "business_type", "business_item"}

    for ext in extractions:
        # CONFIRMED + transaction 매핑인 경우 corporate_info 정리
        if ext.target_model == "transaction" and txn.corporate_info:
            cat = ext.doc_category
            if cat in ("CORPORATE_DOCS", "REGISTRY_DOCS"):
                txn.corporate_info = {k: v for k, v in txn.corporate_info.items() if k not in registry_keys}
            elif cat == "BIZ_REG_DOCS":
                txn.corporate_info = {k: v for k, v in txn.corporate_info.items() if k not in biz_keys}

            # 빈 dict → None으로 정리
            if not txn.corporate_info:
                txn.corporate_info = None

        # extraction 레코드 무효화
        ext.status = "FAILED"
        ext.error_message = "원본 문서 삭제됨"


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


# ── 자동 라우팅 업로드 ────────────────────────────────────────


async def resolve_folder_by_category(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    category: VdrFolderCategory,
) -> VdrFolder | None:
    """카테고리로 최상위 폴더를 조회한다. 없으면 None."""
    q = select(VdrFolder).where(
        VdrFolder.transaction_id == transaction_id,
        VdrFolder.category == category,
        VdrFolder.parent_id.is_(None),
    )
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def resolve_fallback_folder(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> VdrFolder | None:
    """폴백 폴더를 반환한다. 1차: CORPORATE, 2차: order_index 첫 번째 폴더."""
    corporate = await resolve_folder_by_category(db, transaction_id, VdrFolderCategory.CORPORATE)
    if corporate:
        return corporate

    q = (
        select(VdrFolder)
        .where(VdrFolder.transaction_id == transaction_id)
        .order_by(VdrFolder.order_index, VdrFolder.name)
        .limit(1)
    )
    result = await db.execute(q)
    return result.scalar_one_or_none()


def resolve_unique_filename(original_name: str, has_duplicate: bool) -> str:
    """중복 시 uuid4 접미사를 추가한 파일명을 반환한다.

    uuid4 12자리를 사용하여 TOCTOU 경쟁 조건에서도 충돌을 방지한다.
    """
    if not has_duplicate:
        return original_name
    p = Path(original_name)
    suffix_id = uuid.uuid4().hex[:12]
    return f"{p.stem}_{suffix_id}{p.suffix}"


async def check_duplicate_filename(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    folder_id: uuid.UUID,
    original_name: str,
) -> bool:
    """동일 폴더 내 동일 파일명의 활성 문서가 존재하면 True."""
    count = await db.scalar(
        select(func.count())
        .select_from(VdrDocument)
        .where(
            VdrDocument.transaction_id == transaction_id,
            VdrDocument.folder_id == folder_id,
            VdrDocument.original_name == original_name,
            VdrDocument.status == VdrDocumentStatus.ACTIVE,
        )
    )
    return (count or 0) > 0


async def resolve_folders_by_categories(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    categories: set[VdrFolderCategory],
) -> dict[VdrFolderCategory, VdrFolder]:
    """여러 카테고리의 최상위 폴더를 단일 IN 쿼리로 조회한다."""
    if not categories:
        return {}
    q = select(VdrFolder).where(
        VdrFolder.transaction_id == transaction_id,
        VdrFolder.category.in_(categories),
        VdrFolder.parent_id.is_(None),
    )
    result = await db.execute(q)
    return {folder.category: folder for folder in result.scalars().all()}


async def check_duplicate_filenames_batch(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    checks: list[tuple[uuid.UUID, str]],
) -> set[tuple[uuid.UUID, str]]:
    """여러 (folder_id, filename) 쌍의 중복 여부를 단일 쿼리로 확인한다.

    Returns:
        중복이 존재하는 (folder_id, original_name) 쌍의 set.
    """
    if not checks:
        return set()

    from sqlalchemy import and_, or_

    conditions = [
        and_(
            VdrDocument.folder_id == fid,
            VdrDocument.original_name == name,
        )
        for fid, name in checks
    ]
    q = select(VdrDocument.folder_id, VdrDocument.original_name).where(
        VdrDocument.transaction_id == transaction_id,
        VdrDocument.status == VdrDocumentStatus.ACTIVE,
        or_(*conditions),
    )
    result = await db.execute(q)
    return {(row.folder_id, row.original_name) for row in result.all()}


async def auto_upload_document(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    original_name: str,
    file_content: bytes,
    mime_type: str,
    uploaded_by_email: str | None = None,
    description: str | None = None,
) -> tuple[VdrDocument, VdrFolder, VdrFolderCategory | None]:
    """파일을 분석하여 자동으로 폴더를 선택해 업로드한다.

    Returns:
        (업로드된 문서, 라우팅된 폴더, 라우팅 카테고리 또는 폴백 시 None)
    """
    from app.services.vdr_categorization_service import auto_route

    ext = Path(original_name).suffix.lower()
    routed_category = auto_route(original_name, ext, mime_type, len(file_content))

    folder: VdrFolder | None = None

    if routed_category is not None:
        folder = await resolve_folder_by_category(db, transaction_id, routed_category)

    if folder is None:
        folder = await resolve_fallback_folder(db, transaction_id)
        routed_category = None  # 폴백 사용 시 None으로 표시

    if folder is None:
        raise ValueError("VDR이 초기화되지 않았습니다. 먼저 폴더 구조를 초기화해 주세요.")

    has_dup = await check_duplicate_filename(db, transaction_id, folder.id, original_name)
    final_name = resolve_unique_filename(original_name, has_dup)

    doc = await upload_document(
        db,
        transaction_id=transaction_id,
        folder_id=folder.id,
        original_name=final_name,
        file_content=file_content,
        mime_type=mime_type,
        uploaded_by_email=uploaded_by_email,
        description=description,
        _folder_verified=True,
    )

    # routed_category=None 이면 폴백 사용, 라우터에서 VdrAutoUploadResult 조립 시 참조
    return doc, folder, routed_category


async def auto_upload_document_stream(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    original_name: str,
    file_obj: UploadFile,
    file_size: int,
    sha256_hex: str,
    mime_type: str,
    uploaded_by_email: str | None = None,
    description: str | None = None,
) -> tuple[VdrDocument, VdrFolder, VdrFolderCategory | None]:
    """파일을 스트리밍으로 분석하여 자동으로 폴더를 선택해 업로드한다.

    auto_upload_document()의 스트리밍 변형. 메모리: O(1MB).

    Returns:
        (업로드된 문서, 라우팅된 폴더, 라우팅 카테고리 또는 폴백 시 None)
    """
    from app.services.vdr_categorization_service import auto_route

    ext = Path(original_name).suffix.lower()
    routed_category = auto_route(original_name, ext, mime_type, file_size)

    folder: VdrFolder | None = None

    if routed_category is not None:
        folder = await resolve_folder_by_category(db, transaction_id, routed_category)

    if folder is None:
        folder = await resolve_fallback_folder(db, transaction_id)
        routed_category = None

    if folder is None:
        raise ValueError("VDR이 초기화되지 않았습니다. 먼저 폴더 구조를 초기화해 주세요.")

    has_dup = await check_duplicate_filename(db, transaction_id, folder.id, original_name)
    final_name = resolve_unique_filename(original_name, has_dup)

    doc = await upload_document_stream(
        db,
        transaction_id=transaction_id,
        folder_id=folder.id,
        original_name=final_name,
        file_obj=file_obj,
        file_size=file_size,
        sha256_hex=sha256_hex,
        mime_type=mime_type,
        uploaded_by_email=uploaded_by_email,
        description=description,
        _folder_verified=True,
    )

    return doc, folder, routed_category


async def _count_default_root_categories(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> int:
    default_categories = [category for category, _, _ in _DEFAULT_FOLDERS]
    return (
        await db.scalar(
            select(func.count(func.distinct(VdrFolder.category))).where(
                VdrFolder.transaction_id == transaction_id,
                VdrFolder.parent_id.is_(None),
                VdrFolder.category.in_(default_categories),
            )
        )
        or 0
    )


async def init_vdr_folders(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> list[VdrFolder]:
    """Create or repair the default VDR root folders for a transaction."""
    from app.models.transaction import Transaction

    await db.scalar(select(Transaction.id).where(Transaction.id == transaction_id).with_for_update())

    default_categories = [category for category, _, _ in _DEFAULT_FOLDERS]
    existing_result = await db.execute(
        select(VdrFolder.category).where(
            VdrFolder.transaction_id == transaction_id,
            VdrFolder.parent_id.is_(None),
            VdrFolder.category.in_(default_categories),
        )
    )
    existing_categories = set(existing_result.scalars().all())

    for idx, (category, name, is_required) in enumerate(_DEFAULT_FOLDERS):
        if category in existing_categories:
            continue
        db.add(
            VdrFolder(
                transaction_id=transaction_id,
                name=name,
                category=category,
                order_index=idx,
                is_required=is_required,
            )
        )

    await db.commit()
    return await list_folders(db, transaction_id)


async def get_vdr_summary(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> dict:
    """VDR summary that treats partial default folder sets as uninitialized."""
    folder_count = (
        await db.scalar(select(func.count()).select_from(VdrFolder).where(VdrFolder.transaction_id == transaction_id))
        or 0
    )
    default_root_count = await _count_default_root_categories(db, transaction_id)

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
        "initialized": default_root_count == len(_DEFAULT_FOLDERS),
    }


async def get_all_vdr_overviews(db: AsyncSession) -> list[dict]:
    """Return per-transaction VDR overview with repaired initialization status."""
    from app.models.transaction import Transaction

    default_categories = [category for category, _, _ in _DEFAULT_FOLDERS]
    folder_sub = (
        select(
            VdrFolder.transaction_id,
            func.count().label("cnt"),
        )
        .group_by(VdrFolder.transaction_id)
        .subquery()
    )

    default_root_sub = (
        select(
            VdrFolder.transaction_id,
            func.count(func.distinct(VdrFolder.category)).label("default_cnt"),
        )
        .where(
            VdrFolder.parent_id.is_(None),
            VdrFolder.category.in_(default_categories),
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
            func.coalesce(default_root_sub.c.default_cnt, 0).label("default_root_folders"),
            func.coalesce(doc_sub.c.cnt, 0).label("total_documents"),
            func.coalesce(doc_sub.c.total_size, 0).label("total_size_bytes"),
            doc_sub.c.last_upload.label("last_upload_at"),
        )
        .outerjoin(folder_sub, folder_sub.c.transaction_id == Transaction.id)
        .outerjoin(default_root_sub, default_root_sub.c.transaction_id == Transaction.id)
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
            "vdr_initialized": row.default_root_folders == len(_DEFAULT_FOLDERS),
            "total_folders": row.total_folders,
            "total_documents": row.total_documents,
            "total_size_bytes": row.total_size_bytes,
            "last_upload_at": row.last_upload_at,
        }
        for row in result.all()
    ]
