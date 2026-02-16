"""Document 관련 엔드포인트 (T-I16).

> 마지막 수정: 2026-02-10 23:30:00

POST /api/v1/documents — IM 문서 생성 시작
GET  /api/v1/documents/{id} — 상태/결과 조회
GET  /api/v1/documents/{id}/download — 파일 다운로드
GET  /api/v1/documents — 목록 조회 (pagination)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_user
from src.api.schemas.common import PaginationParams
from src.api.schemas.documents import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
)
from src.api.services.document_service import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=202,
    summary="IM 문서 생성 시작",
    description="DART 데이터 수집 → 분석 → 생성 → 렌더링 파이프라인을 비동기로 시작한다.",
)
async def create_document(
    data: DocumentCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """IM 문서 생성을 시작한다."""
    service = DocumentService(session)
    document = await service.create_document(
        owner_id=current_user.id,
        create_data=data,
    )
    return DocumentResponse.model_validate(document)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="문서 상태/결과 조회",
)
async def get_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """문서 생성 상태 및 결과를 조회한다."""
    service = DocumentService(session)
    document = await service.get_document(document_id, current_user)
    return DocumentResponse.model_validate(document)


@router.get(
    "/{document_id}/download",
    summary="문서 파일 다운로드",
    responses={
        200: {"description": "파일 다운로드 성공"},
        404: {"description": "문서 또는 파일을 찾을 수 없음"},
    },
)
async def download_document(
    document_id: UUID,
    format: str = Query(default="pptx", pattern="^(pptx|pdf)$"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """생성 완료된 PPTX 또는 PDF 파일을 다운로드한다."""
    service = DocumentService(session)
    file_path = await service.get_download_path(document_id, format, current_user)

    if format == "pptx":
        media_type = (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    else:
        media_type = "application/pdf"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=f"IM_{document_id}.{format}",
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="문서 목록 조회",
)
async def list_documents(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    """사용자의 문서 목록을 조회한다."""
    service = DocumentService(session)
    items, total = await service.list_documents(
        current_user=current_user,
        offset=offset,
        limit=limit,
        search=search,
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(doc) for doc in items],
        total=total,
        offset=offset,
        limit=limit,
    )
