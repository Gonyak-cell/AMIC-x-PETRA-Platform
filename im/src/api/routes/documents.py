"""Document 관련 엔드포인트 (T-I16).

> 마지막 수정: 2026-03-13 22:38:00

POST /api/v1/documents — IM 문서 생성 시작
POST /api/v1/documents/{id}/upload-financials — 재무데이터 Excel 업로드
GET  /api/v1/documents/{id} — 상태/결과 조회
GET  /api/v1/documents/{id}/download — 파일 다운로드
GET  /api/v1/documents — 목록 조회 (pagination)
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_user
from src.api.exceptions import ValidationError
from src.api.schemas.documents import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
)
from src.api.services.document_service import DocumentService

_ALLOWED_EXTENSIONS = {".xlsx", ".xlsm", ".csv"}
_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=202,
    summary="IM 문서 생성 시작",
    description="데이터 소스(DART/MANUAL/EXCEL)에 따라 파이프라인을 비동기로 시작한다.",
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


@router.post(
    "/{document_id}/upload-financials",
    summary="재무데이터 Excel/CSV 업로드",
    description="생성 전 문서에 재무데이터 파일을 첨부한다. data_source=EXCEL인 문서 전용.",
)
async def upload_financial_data(
    document_id: UUID,
    file: UploadFile,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Excel/CSV 재무데이터를 업로드한다."""
    service = DocumentService(session)
    document = await service.get_document(document_id, current_user)

    if document.data_source != "EXCEL":
        raise ValidationError(
            field="data_source",
            reason="data_source가 EXCEL인 문서만 파일 업로드가 가능합니다",
        )

    # 파일 확장자 검증
    if not file.filename:
        raise ValidationError(field="file", reason="파일명이 없습니다")
    ext = Path(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValidationError(
            field="file",
            reason=f"허용 확장자: {', '.join(_ALLOWED_EXTENSIONS)}",
        )

    # 파일 크기 검증
    content = await file.read()
    if len(content) > _MAX_UPLOAD_SIZE:
        raise ValidationError(field="file", reason="파일 크기는 10MB 이하여야 합니다")

    # 파일 저장
    upload_dir = Path("uploads") / "financials" / str(document_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"financials{ext}"
    dest.write_bytes(content)

    # generation_config에 경로 기록
    config = document.generation_config or {}
    config["excel_file_path"] = str(dest)
    document.generation_config = config
    await session.commit()

    # AWAITING_UPLOAD 상태이면 Celery 태스크 디스패치
    from src.api.db.models.document import DocumentStatus
    from src.api.exceptions import ConflictError

    if document.status == DocumentStatus.AWAITING_UPLOAD.value:
        from src.api.tasks.generate_im import generate_im_task

        task = generate_im_task.delay(
            str(document.id),
            document.corp_code,
            document.generation_config,
            document.data_source,
        )
        document.status = DocumentStatus.PENDING.value
        document.celery_task_id = task.id
        await session.commit()
    elif document.status in (
        DocumentStatus.PENDING.value,
        DocumentStatus.COLLECTING.value,
        DocumentStatus.ANALYZING.value,
        DocumentStatus.GENERATING.value,
        DocumentStatus.RENDERING.value,
    ):
        raise ConflictError(
            "Document",
            f"이미 진행 중인 문서입니다 (status={document.status})",
        )

    return {"status": "uploaded", "filename": file.filename, "size": len(content)}


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
) -> Response:
    """생성 완료된 PPTX 또는 PDF 파일을 다운로드한다."""
    service = DocumentService(session)
    document = await service.get_document(document_id, current_user)

    # 품질 게이트 차단: QUALITY_FAILED 상태 다운로드 불가
    if document.status == "QUALITY_FAILED":
        raise ValidationError(
            field="quality_status",
            reason="품질 게이트 미통과(FAIL) 문서는 다운로드할 수 없습니다. 재생성이 필요합니다.",
        )

    # PDF 형식 요청 시 supported_formats 확인
    if format == "pdf":
        supported = document.supported_formats or []
        if "pdf" not in supported:
            raise ValidationError(
                field="format",
                reason="PDF 형식은 현재 미지원입니다",
            )

    file_path = await service.get_download_path(document_id, format, current_user)

    if format == "pptx":
        media_type = (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    else:
        media_type = "application/pdf"

    response = FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=f"IM_{document_id}.{format}",
    )

    # 조건부 통과: 경고 헤더 추가 (TM/DM과 동일 정책)
    if document.quality_status == "CONDITIONAL":
        response.headers["X-Quality-Warning"] = "CONDITIONAL"

    return response


@router.delete(
    "/{document_id}",
    status_code=204,
    response_class=Response,
    summary="문서 삭제",
    description="소유자 또는 ADMIN이 문서를 삭제한다. 진행 중인 문서는 삭제 불가.",
)
async def delete_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    """문서를 삭제한다."""
    service = DocumentService(session)
    await service.delete_document(document_id, current_user)
    return Response(status_code=204)


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
