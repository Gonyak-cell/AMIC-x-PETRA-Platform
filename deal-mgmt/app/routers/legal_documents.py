"""법률 문서 라우터 — CRUD + 다운로드 (SPA/SHA/BTA/SSA/MOU)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import DocumentNotReadyError
from app.core.security import JWTClaims, check_client_deal_access, get_jwt_claims, require_write_access
from app.models.enums import LegalDocStatus
from app.models.transaction import Transaction
from app.schemas.legal_document import LegalDocumentCreate, LegalDocumentOut
from app.services import legal_document_service, transaction_service

router = APIRouter(prefix="/transactions/{txn_id}/legal-documents", tags=["Legal Documents"])

# 경로 탐색(Path Traversal) 방어: 생성 파일은 반드시 이 디렉터리 내에 위치해야 한다
_SAFE_OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent.parent / "generated" / "legal"
).resolve()


async def _get_and_authorize_txn(
    db: AsyncSession,
    txn_id: uuid.UUID,
    claims: JWTClaims,
) -> Transaction:
    """거래를 조회하고 접근 권한을 확인한다.

    ADMIN 역할은 모든 거래에 접근 가능하다.
    CLIENT 역할은 deal_clients 테이블 기반 접근 제어를 거친다.
    그 외 역할은 lead_advisor 또는 deal_captain이어야 한다.
    """
    txn = await transaction_service.get_transaction(db, txn_id)
    # CLIENT 역할: deal_clients 테이블 기반 접근 제어
    if claims.role == "CLIENT":
        await check_client_deal_access(db, txn_id, claims)
        return txn
    if (
        claims.role != "ADMIN"
        and claims.email is not None
        and txn.lead_advisor_email != claims.email
        and txn.deal_captain_email != claims.email
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 거래에 접근할 권한이 없습니다",
        )
    return txn


@router.get("", response_model=list[LegalDocumentOut])
async def list_legal_documents(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await _get_and_authorize_txn(db, txn_id, claims)
    return [
        LegalDocumentOut.model_validate(d)
        for d in await legal_document_service.list_legal_documents(db, txn_id)
    ]


@router.get("/{doc_id}", response_model=LegalDocumentOut)
async def get_legal_document(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await _get_and_authorize_txn(db, txn_id, claims)
    doc = await legal_document_service.get_legal_document(db, txn_id, doc_id)
    return LegalDocumentOut.model_validate(doc)


@router.post("", response_model=LegalDocumentOut, status_code=status.HTTP_201_CREATED)
async def create_legal_document(
    txn_id: uuid.UUID,
    body: LegalDocumentCreate,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await _get_and_authorize_txn(db, txn_id, claims)
    doc = await legal_document_service.create_legal_document(
        db,
        transaction_id=txn_id,
        body=body,
        created_by_email=claims.email,
    )
    return LegalDocumentOut.model_validate(doc)


@router.post("/{doc_id}/regenerate", response_model=LegalDocumentOut)
async def regenerate_legal_document(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    body: LegalDocumentCreate | None = None,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await _get_and_authorize_txn(db, txn_id, claims)
    doc = await legal_document_service.regenerate_document(
        db,
        transaction_id=txn_id,
        doc_id=doc_id,
        new_parameters=body.parameters if body else None,
    )
    return LegalDocumentOut.model_validate(doc)


@router.get("/{doc_id}/download")
async def download_legal_document(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),
):
    await _get_and_authorize_txn(db, txn_id, claims)
    doc = await legal_document_service.get_legal_document(db, txn_id, doc_id)

    # 문서 준비 상태 확인 — 커스텀 예외를 통해 400 응답 (handlers에 등록됨)
    if doc.status != LegalDocStatus.READY:
        raise DocumentNotReadyError(doc.status.value if hasattr(doc.status, "value") else str(doc.status))

    if not doc.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="파일 경로가 없습니다. 문서를 재생성해 주세요.",
        )

    # 경로 탐색(Path Traversal) 방어: 파일이 안전 디렉터리 내에 있는지 확인
    file_path = Path(doc.file_path).resolve()
    if not str(file_path).startswith(str(_SAFE_OUTPUT_DIR)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="유효하지 않은 파일 경로입니다.",
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="파일을 찾을 수 없습니다. 문서를 재생성해 주세요.",
        )

    return FileResponse(
        path=str(file_path),
        filename=doc.file_name or f"{doc.doc_type}_{doc.id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_legal_document(
    txn_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(require_write_access()),
):
    await _get_and_authorize_txn(db, txn_id, claims)
    await legal_document_service.delete_legal_document(db, txn_id, doc_id)
