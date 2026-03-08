"""문서 버전 관리 서비스 — Document_Master + Revision CRUD + SHA-256 중복 차단."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_master import DocumentMaster
from app.models.document_revision import DocumentRevision
from app.models.enums import AuditAction, DocumentType, UploadSource
from app.services import audit_service

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads/document_versions")


# ── DocumentMaster CRUD ─────────────────────────────────


async def create_document(
    db: AsyncSession,
    *,
    transaction_id: uuid.UUID,
    doc_type: DocumentType,
    doc_name: str,
    description: str | None = None,
    contract_id: uuid.UUID | None = None,
    nda_id: uuid.UUID | None = None,
    created_by_email: str | None = None,
) -> DocumentMaster:
    """문서 원장을 생성한다."""
    doc = DocumentMaster(
        transaction_id=transaction_id,
        doc_type=doc_type,
        doc_name=doc_name,
        description=description,
        contract_id=contract_id,
        nda_id=nda_id,
        created_by_email=created_by_email,
    )
    db.add(doc)
    await db.flush()

    await audit_service.record(
        db,
        entity_type="document_master",
        entity_id=doc.id,
        action=AuditAction.CREATE,
        actor_email=created_by_email,
        new_value={"doc_type": doc_type.value, "doc_name": doc_name},
    )
    return doc


async def list_documents(
    db: AsyncSession,
    *,
    transaction_id: uuid.UUID,
    doc_type: str | None = None,
    include_archived: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[DocumentMaster], int]:
    """트랜잭션 하위 문서 목록을 반환한다."""
    base = select(DocumentMaster).where(DocumentMaster.transaction_id == transaction_id)
    if not include_archived:
        base = base.where(DocumentMaster.is_archived.is_(False))
    if doc_type:
        base = base.where(DocumentMaster.doc_type == doc_type)

    count_q = select(func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    items_q = base.order_by(DocumentMaster.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(items_q)
    return list(result.scalars().all()), total


async def get_document(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
) -> DocumentMaster:
    """문서 원장 1건을 조회한다."""
    doc = await db.get(DocumentMaster, document_id)
    if not doc:
        raise HTTPException(404, "문서를 찾을 수 없습니다")
    return doc


# ── DocumentRevision CRUD ───────────────────────────────


async def upload_revision(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    file_content: bytes,
    file_name: str,
    mime_type: str | None = None,
    upload_source: UploadSource = UploadSource.MANUAL,
    changes_summary: str | None = None,
    uploaded_by_email: str | None = None,
    source_entity_type: str | None = None,
    source_entity_id: str | None = None,
) -> DocumentRevision:
    """리비전을 업로드한다. SHA-256 중복 차단 + FOR UPDATE 락."""
    # 1. SHA-256 해시 계산
    sha256_hex: str = await asyncio.to_thread(lambda: hashlib.sha256(file_content).hexdigest())

    # 2. 동일 문서 내 중복 체크
    dup_q = select(DocumentRevision).where(
        DocumentRevision.document_id == document_id,
        DocumentRevision.sha256_hash == sha256_hex,
        DocumentRevision.is_deleted.is_(False),
    )
    existing = (await db.execute(dup_q)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            409,
            f"동일한 파일이 이미 v{existing.revision_number}으로 등록되어 있습니다",
        )

    # 3. DocumentMaster FOR UPDATE 락 → revision_number 증가
    lock_q = select(DocumentMaster).where(DocumentMaster.id == document_id).with_for_update()
    doc = (await db.execute(lock_q)).scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "문서를 찾을 수 없습니다")

    next_rev = doc.current_revision_number + 1

    # 4. 이전 리비전 is_current=False
    prev_rev_q = select(DocumentRevision).where(
        DocumentRevision.document_id == document_id,
        DocumentRevision.is_current.is_(True),
        DocumentRevision.is_deleted.is_(False),
    )
    prev_rev = (await db.execute(prev_rev_q)).scalar_one_or_none()
    if prev_rev:
        prev_rev.is_current = False

    # 5. 파일 저장
    safe_name = file_name.replace("/", "_").replace("\\", "_")
    dir_path = UPLOAD_DIR / str(document_id)
    dir_path.mkdir(parents=True, exist_ok=True)
    dest = dir_path / f"{next_rev}_{safe_name}"
    await asyncio.to_thread(dest.write_bytes, file_content)
    relative_path = str(dest)

    # 6. DocumentRevision INSERT
    revision = DocumentRevision(
        document_id=document_id,
        revision_number=next_rev,
        sha256_hash=sha256_hex,
        file_path=relative_path,
        file_name=file_name,
        file_size_bytes=len(file_content),
        mime_type=mime_type,
        uploaded_by_email=uploaded_by_email,
        upload_source=upload_source,
        changes_summary=changes_summary,
        prev_revision_id=prev_rev.id if prev_rev else None,
        is_current=True,
        source_entity_type=source_entity_type,
        source_entity_id=source_entity_id,
    )
    db.add(revision)

    # 7. DocumentMaster 갱신
    doc.current_revision_number = next_rev
    await db.flush()

    # 8. 감사 로그
    await audit_service.record(
        db,
        entity_type="document_revision",
        entity_id=revision.id,
        action=AuditAction.CREATE,
        actor_email=uploaded_by_email,
        new_value={
            "revision_number": next_rev,
            "file_name": file_name,
            "sha256_hash": sha256_hex,
            "upload_source": upload_source.value,
        },
    )

    logger.info(
        "문서 리비전 생성: doc=%s rev=%d hash=%s",
        document_id,
        next_rev,
        sha256_hex[:12],
    )
    return revision


async def get_revision_history(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    include_deleted: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[DocumentRevision], int]:
    """리비전 이력을 조회한다."""
    base = select(DocumentRevision).where(DocumentRevision.document_id == document_id)
    if not include_deleted:
        base = base.where(DocumentRevision.is_deleted.is_(False))

    count_q = select(func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    items_q = base.order_by(DocumentRevision.revision_number.desc()).offset(offset).limit(limit)
    result = await db.execute(items_q)
    return list(result.scalars().all()), total


async def get_revision(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
) -> DocumentRevision:
    """특정 리비전을 조회한다."""
    rev = await db.get(DocumentRevision, revision_id)
    if not rev or rev.is_deleted:
        raise HTTPException(404, "리비전을 찾을 수 없습니다")
    return rev


async def soft_delete_revision(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    actor_email: str | None = None,
) -> None:
    """리비전을 소프트 삭제한다. Hard Delete 엄격 금지."""
    rev = await db.get(DocumentRevision, revision_id)
    if not rev:
        raise HTTPException(404, "리비전을 찾을 수 없습니다")
    if rev.is_deleted:
        raise HTTPException(409, "이미 삭제된 리비전입니다")

    rev.is_deleted = True
    rev.is_current = False

    # 직전 리비전이 있으면 is_current=True로 복원
    if rev.prev_revision_id:
        prev = await db.get(DocumentRevision, rev.prev_revision_id)
        if prev and not prev.is_deleted:
            prev.is_current = True

    await db.flush()

    await audit_service.record(
        db,
        entity_type="document_revision",
        entity_id=revision_id,
        action=AuditAction.DELETE,
        actor_email=actor_email,
        old_value={
            "revision_number": rev.revision_number,
            "file_name": rev.file_name,
        },
    )


# ── 기존 모델 연동 헬퍼 ─────────────────────────────────


async def find_or_create_for_contract(
    db: AsyncSession,
    *,
    transaction_id: uuid.UUID,
    contract_id: uuid.UUID,
    contract_type: str,
    doc_name: str,
    created_by_email: str | None = None,
) -> DocumentMaster:
    """Contract에 대응하는 DocumentMaster를 찾거나 생성한다."""
    q = select(DocumentMaster).where(
        DocumentMaster.contract_id == contract_id,
    )
    doc = (await db.execute(q)).scalar_one_or_none()
    if doc:
        return doc

    # ContractType → DocumentType 매핑
    type_map: dict[str, DocumentType] = {
        "SPA": DocumentType.CONTRACT_SPA,
        "AMENDMENT": DocumentType.CONTRACT_AMENDMENT,
        "SIDE_LETTER": DocumentType.CONTRACT_SIDE_LETTER,
        "SHAREHOLDERS_AGREEMENT": DocumentType.CONTRACT_SHA,
        "ESCROW_AGREEMENT": DocumentType.CONTRACT_ESCROW,
        "BTA": DocumentType.CONTRACT_BTA,
        "SSA": DocumentType.CONTRACT_SSA,
    }
    doc_type = type_map.get(contract_type, DocumentType.CONTRACT_OTHER)

    return await create_document(
        db,
        transaction_id=transaction_id,
        doc_type=doc_type,
        doc_name=doc_name,
        contract_id=contract_id,
        created_by_email=created_by_email,
    )


async def find_or_create_for_nda(
    db: AsyncSession,
    *,
    transaction_id: uuid.UUID,
    nda_id: uuid.UUID,
    doc_name: str,
    created_by_email: str | None = None,
) -> DocumentMaster:
    """NDA에 대응하는 DocumentMaster를 찾거나 생성한다."""
    q = select(DocumentMaster).where(
        DocumentMaster.nda_id == nda_id,
    )
    doc = (await db.execute(q)).scalar_one_or_none()
    if doc:
        return doc

    return await create_document(
        db,
        transaction_id=transaction_id,
        doc_type=DocumentType.NDA,
        doc_name=doc_name,
        nda_id=nda_id,
        created_by_email=created_by_email,
    )
