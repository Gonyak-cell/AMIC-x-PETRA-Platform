"""다이어그램 API 엔드포인트.

Excalidraw 다이어그램 CRUD 및 PNG 내보내기를 제공한다.

GET    /api/v1/documents/{id}/diagrams              — 목록 조회
POST   /api/v1/documents/{id}/diagrams              — 생성
GET    /api/v1/documents/{id}/diagrams/{diagram_id}  — 상세 조회
PUT    /api/v1/documents/{id}/diagrams/{diagram_id}  — 수정 (Excalidraw JSON)
DELETE /api/v1/documents/{id}/diagrams/{diagram_id}  — 삭제
POST   /api/v1/documents/{id}/diagrams/{diagram_id}/export-png — PNG 내보내기
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from src.api.config import get_config
from src.api.db.models.diagram import Diagram
from src.api.db.models.document import Document
from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_user
from src.api.schemas.diagrams import (
    DiagramCreate,
    DiagramListResponse,
    DiagramResponse,
    DiagramUpdate,
    PngExportResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["diagrams"])

# PNG 업로드 제한
_MAX_PNG_SIZE = 10 * 1024 * 1024  # 10 MB
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_document_for_user(
    document_id: uuid.UUID,
    session: AsyncSession,
    current_user: User,
) -> Document:
    """문서를 조회하고 접근 권한을 확인한다."""
    stmt = select(Document).where(Document.id == document_id)
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    if doc.owner_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")
    return doc


async def _get_diagram(
    document_id: uuid.UUID,
    diagram_id: uuid.UUID,
    session: AsyncSession,
    current_user: User,
) -> Diagram:
    """다이어그램을 조회하고 접근 권한을 확인한다."""
    await _get_document_for_user(document_id, session, current_user)
    stmt = select(Diagram).where(
        Diagram.id == diagram_id,
        Diagram.document_id == document_id,
    )
    result = await session.execute(stmt)
    diagram = result.scalar_one_or_none()
    if diagram is None:
        raise HTTPException(status_code=404, detail="다이어그램을 찾을 수 없습니다.")
    return diagram


def _validate_png_upload(content: bytes) -> None:
    """PNG 파일 크기 및 매직 바이트를 검증한다."""
    if len(content) > _MAX_PNG_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"PNG 파일 크기가 {_MAX_PNG_SIZE // (1024 * 1024)}MB를 초과합니다.",
        )
    if not content.startswith(_PNG_MAGIC):
        raise HTTPException(
            status_code=422,
            detail="유효한 PNG 파일이 아닙니다.",
        )


# ---------------------------------------------------------------------------
# 목록 조회
# ---------------------------------------------------------------------------


@router.get(
    "/documents/{document_id}/diagrams",
    response_model=list[DiagramListResponse],
    summary="다이어그램 목록 조회",
)
async def list_diagrams(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[DiagramListResponse]:
    """문서의 다이어그램 목록을 반환한다 (excalidraw_data 생략)."""
    await _get_document_for_user(document_id, session, current_user)
    stmt = (
        select(Diagram)
        .options(defer(Diagram.excalidraw_data))
        .where(Diagram.document_id == document_id)
        .order_by(Diagram.created_at)
    )
    result = await session.execute(stmt)
    diagrams = result.scalars().all()
    return [DiagramListResponse.model_validate(d) for d in diagrams]


# ---------------------------------------------------------------------------
# 생성
# ---------------------------------------------------------------------------


@router.post(
    "/documents/{document_id}/diagrams",
    response_model=DiagramResponse,
    status_code=201,
    summary="다이어그램 생성",
)
async def create_diagram(
    document_id: uuid.UUID,
    data: DiagramCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> DiagramResponse:
    """Excalidraw 다이어그램을 생성한다."""
    await _get_document_for_user(document_id, session, current_user)

    diagram = Diagram(
        id=uuid.uuid4(),
        document_id=document_id,
        diagram_type=data.diagram_type,
        title=data.title,
        excalidraw_data=data.excalidraw_data,
    )
    session.add(diagram)
    await session.commit()
    await session.refresh(diagram)

    logger.info(
        "Diagram created: doc=%s type=%s id=%s user=%s",
        document_id,
        data.diagram_type,
        diagram.id,
        current_user.id,
    )

    return DiagramResponse.model_validate(diagram)


# ---------------------------------------------------------------------------
# 상세 조회
# ---------------------------------------------------------------------------


@router.get(
    "/documents/{document_id}/diagrams/{diagram_id}",
    response_model=DiagramResponse,
    summary="다이어그램 상세 조회",
)
async def get_diagram(
    document_id: uuid.UUID,
    diagram_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> DiagramResponse:
    """다이어그램의 전체 Excalidraw 데이터를 반환한다."""
    diagram = await _get_diagram(document_id, diagram_id, session, current_user)
    return DiagramResponse.model_validate(diagram)


# ---------------------------------------------------------------------------
# 수정
# ---------------------------------------------------------------------------


@router.put(
    "/documents/{document_id}/diagrams/{diagram_id}",
    response_model=DiagramResponse,
    summary="다이어그램 수정",
)
async def update_diagram(
    document_id: uuid.UUID,
    diagram_id: uuid.UUID,
    data: DiagramUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> DiagramResponse:
    """다이어그램의 Excalidraw JSON 데이터를 수정한다."""
    diagram = await _get_diagram(document_id, diagram_id, session, current_user)
    diagram.excalidraw_data = data.excalidraw_data
    await session.commit()
    await session.refresh(diagram)

    logger.info(
        "Diagram updated: doc=%s id=%s user=%s",
        document_id,
        diagram_id,
        current_user.id,
    )

    return DiagramResponse.model_validate(diagram)


# ---------------------------------------------------------------------------
# 삭제
# ---------------------------------------------------------------------------


@router.delete(
    "/documents/{document_id}/diagrams/{diagram_id}",
    status_code=204,
    summary="다이어그램 삭제",
)
async def delete_diagram(
    document_id: uuid.UUID,
    diagram_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """다이어그램을 삭제한다."""
    diagram = await _get_diagram(document_id, diagram_id, session, current_user)
    await session.delete(diagram)
    await session.commit()

    logger.info(
        "Diagram deleted: doc=%s id=%s user=%s",
        document_id,
        diagram_id,
        current_user.id,
    )


# ---------------------------------------------------------------------------
# PNG 내보내기
# ---------------------------------------------------------------------------


@router.post(
    "/documents/{document_id}/diagrams/{diagram_id}/export-png",
    response_model=PngExportResponse,
    summary="다이어그램 PNG 내보내기",
)
async def export_diagram_png(
    document_id: uuid.UUID,
    diagram_id: uuid.UUID,
    file: UploadFile = ...,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> PngExportResponse:
    """프론트엔드에서 생성한 PNG Blob을 서버에 저장한다."""
    diagram = await _get_diagram(document_id, diagram_id, session, current_user)

    content = await file.read()
    _validate_png_upload(content)

    cfg = get_config()
    output_dir = Path(cfg.output_dir) / "diagrams" / str(document_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    png_filename = f"{diagram.diagram_type}_{diagram_id}.png"
    png_path = output_dir / png_filename

    try:
        png_path.write_bytes(content)
    except OSError as exc:
        logger.error("PNG 파일 저장 실패: %s — %s", png_path, exc)
        raise HTTPException(
            status_code=500,
            detail="PNG 파일 저장에 실패했습니다.",
        ) from exc

    diagram.png_path = str(png_path)
    await session.commit()
    await session.refresh(diagram)

    logger.info(
        "Diagram PNG exported: %s (%d bytes)",
        png_path,
        len(content),
    )

    return PngExportResponse(png_path=str(png_path))
