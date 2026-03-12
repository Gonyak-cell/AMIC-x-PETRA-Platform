"""문서 버전 관리 라우터 — Document_Master + Revision CRUD + 파일 업로드/다운로드."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.enums import DocumentType, UploadSource
from app.schemas.document_version import (
    DocumentMasterCreate,
    DocumentMasterListResponse,
    DocumentMasterOut,
    DocumentRevisionOut,
    RevisionListResponse,
)
from app.services import document_version_service, transaction_service

UPLOAD_DIR = Path("uploads/document_versions")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".docx", ".doc", ".pdf", ".xlsx", ".xls", ".pptx", ".ppt", ".hwp", ".hwpx", ".txt", ".csv"}

router = APIRouter(
    prefix="/transactions/{txn_id}/documents",
    tags=["Document Versions"],
)


# ── DocumentMaster CRUD ─────────────────────────────────


@router.post("", response_model=DocumentMasterOut, status_code=201)
async def create_document(
    txn_id: uuid.UUID,
    body: DocumentMasterCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> DocumentMasterOut:
    """문서 원장을 생성한다."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    # doc_type 유효성 검증
    try:
        doc_type = DocumentType(body.doc_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 문서 유형입니다: {body.doc_type}",
        )

    doc = await document_version_service.create_document(
        db,
        transaction_id=txn_id,
        doc_type=doc_type,
        doc_name=body.doc_name,
        description=body.description,
        contract_id=body.contract_id,
        nda_id=body.nda_id,
        created_by_email=claims.email,
    )
    await db.commit()
    await db.refresh(doc)
    return DocumentMasterOut.model_validate(doc)


@router.get("", response_model=DocumentMasterListResponse)
async def list_documents(
    txn_id: uuid.UUID,
    doc_type: str | None = Query(None, description="문서 유형 필터"),
    include_archived: bool = Query(False, description="보관 문서 포함 여부"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> DocumentMasterListResponse:
    """트랜잭션 하위 문서 목록을 조회한다."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    items, total = await document_version_service.list_documents(
        db,
        transaction_id=txn_id,
        doc_type=doc_type,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    return DocumentMasterListResponse(
        items=[DocumentMasterOut.model_validate(d) for d in items],
        total=total,
    )


@router.get("/{doc_id}", response_model=DocumentMasterOut)
async def get_document(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> DocumentMasterOut:
    """문서 원장 1건을 조회한다."""
    await check_client_deal_access(db, txn_id, claims)
    doc = await document_version_service.get_document(db, document_id=doc_id)
    return DocumentMasterOut.model_validate(doc)


# ── DocumentRevision CRUD ───────────────────────────────


@router.post("/{doc_id}/revisions", response_model=DocumentRevisionOut, status_code=201)
async def upload_revision(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    file: UploadFile = File(...),
    changes_summary: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> DocumentRevisionOut:
    """리비전을 업로드한다. SHA-256 중복 차단."""
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)

    # 파일 크기 검증
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="파일 크기가 50MB를 초과합니다",
        )

    # 확장자 검증
    safe_filename = file.filename or "document"
    safe_filename = Path(safe_filename).name
    ext = Path(safe_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"허용되지 않는 파일 형식입니다. 허용: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    revision = await document_version_service.upload_revision(
        db,
        document_id=doc_id,
        file_content=content,
        file_name=safe_filename,
        mime_type=file.content_type,
        upload_source=UploadSource.MANUAL,
        changes_summary=changes_summary,
        uploaded_by_email=claims.email,
    )
    await db.commit()
    await db.refresh(revision)
    return DocumentRevisionOut.model_validate(revision)


@router.get("/{doc_id}/revisions", response_model=RevisionListResponse)
async def list_revisions(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    include_deleted: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> RevisionListResponse:
    """리비전 이력을 조회한다."""
    await check_client_deal_access(db, txn_id, claims)

    items, total = await document_version_service.get_revision_history(
        db,
        document_id=doc_id,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
    )
    return RevisionListResponse(
        items=[DocumentRevisionOut.model_validate(r) for r in items],
        total=total,
    )


@router.get("/{doc_id}/revisions/{rev_id}", response_model=DocumentRevisionOut)
async def get_revision(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    rev_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> DocumentRevisionOut:
    """특정 리비전을 조회한다."""
    await check_client_deal_access(db, txn_id, claims)
    rev = await document_version_service.get_revision(db, revision_id=rev_id)
    return DocumentRevisionOut.model_validate(rev)


@router.get("/{doc_id}/revisions/{rev_id}/download")
async def download_revision(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    rev_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
) -> FileResponse:
    """리비전 파일을 다운로드한다."""
    await check_client_deal_access(db, txn_id, claims)
    rev = await document_version_service.get_revision(db, revision_id=rev_id)

    if not rev.file_path:
        raise HTTPException(status_code=404, detail="파일이 없습니다")

    file_path = Path(rev.file_path)
    # 경로 탐색 방어: UPLOAD_DIR 내부인지 확인
    try:
        file_path.resolve().relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="잘못된 파일 경로입니다")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    return FileResponse(
        path=str(file_path),
        filename=rev.file_name or file_path.name,
        media_type=rev.mime_type or "application/octet-stream",
    )


@router.delete("/{doc_id}/revisions/{rev_id}", status_code=204)
async def delete_revision(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    rev_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
) -> None:
    """리비전을 소프트 삭제한다."""
    await check_client_deal_access(db, txn_id, claims)
    await document_version_service.soft_delete_revision(
        db,
        revision_id=rev_id,
        actor_email=claims.email,
    )
    await db.commit()
