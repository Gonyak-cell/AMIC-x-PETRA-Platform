"""IM Ralph Loop API 라우터."""

from __future__ import annotations

import uuid as uuid_mod
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.im_ralph_session import IMRalphSession
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_active_user
from src.api.exceptions import ConflictError, NotFoundError, ValidationError
from src.api.schemas.ralph import (
    IMRalphProgressOut,
    IMRalphSessionOut,
    IMRalphTriggerRequest,
    IMRalphTriggerResponse,
)

router = APIRouter(
    prefix="/api/v1/ralph",
    tags=["Ralph Loop"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("/sessions", response_model=list[IMRalphSessionOut])
async def list_sessions(
    document_id: uuid_mod.UUID | None = None,
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    """Ralph Loop 세션 목록을 반환한다.

    Args:
        document_id: 특정 문서의 세션만 필터링.
        session: DB 세션.
    """
    stmt = select(IMRalphSession).order_by(IMRalphSession.created_at.desc())

    if document_id is not None:
        stmt = stmt.where(IMRalphSession.document_id == document_id)

    result = await session.execute(stmt.limit(50))
    return result.scalars().all()


@router.get("/sessions/{session_id}", response_model=IMRalphSessionOut)
async def get_session(
    session_id: uuid_mod.UUID,
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    """Ralph Loop 세션 상세를 반환한다."""
    stmt = select(IMRalphSession).where(IMRalphSession.id == session_id)
    result = await session.execute(stmt)
    ralph_session = result.scalar_one_or_none()

    if ralph_session is None:
        raise NotFoundError(resource_type="IMRalphSession", identifier=str(session_id))
    return ralph_session


@router.get("/sessions/{session_id}/progress", response_model=IMRalphProgressOut)
async def get_session_progress(
    session_id: uuid_mod.UUID,
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    """Ralph Loop 실시간 프로그레스를 반환한다."""
    stmt = select(IMRalphSession).where(IMRalphSession.id == session_id)
    result = await session.execute(stmt)
    ralph_session = result.scalar_one_or_none()

    if ralph_session is None:
        raise NotFoundError(resource_type="IMRalphSession", identifier=str(session_id))

    progress = ralph_session.progress or {}
    records = progress.get("records", {})

    # 현재 섹션 추출
    current_section = None
    current_iteration = 0
    scores: dict[str, float] = {}
    gate_results: list[dict] = []

    for section_id, section_records in records.items():
        if section_records:
            last_record = section_records[-1]
            current_section = section_id
            current_iteration = len(section_records)
            scores[section_id] = last_record.get("weighted_score", 0.0)
            gate_results.extend(last_record.get("gate_results", []))

    return IMRalphProgressOut(
        session_id=ralph_session.id,
        status=ralph_session.status,
        current_section=current_section,
        current_iteration=current_iteration,
        total_sections=len(records),
        scores=scores,
        gate_results=gate_results[-10:],  # 최근 10개만
    )


@router.post("/sessions", response_model=IMRalphTriggerResponse, status_code=202)
async def trigger_ralph_loop(
    body: IMRalphTriggerRequest,
    user: Any = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    """수동으로 Ralph Loop를 실행한다."""
    from src.api.db.models.document import Document

    # 문서 존재 확인
    stmt = select(Document).where(Document.id == body.document_id)
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()

    if doc is None:
        raise NotFoundError(resource_type="Document", identifier=str(body.document_id))
    if not doc.pptx_path:
        raise ValidationError(
            field="pptx_path", reason="PPTX 파일이 생성되지 않은 문서입니다."
        )

    # 진행 중인 세션이 있는지 확인
    active_stmt = select(IMRalphSession).where(
        IMRalphSession.document_id == body.document_id,
        IMRalphSession.status.in_(["PLANNING", "GENERATING", "VALIDATING"]),
    )
    active_result = await session.execute(active_stmt)
    if active_result.scalar_one_or_none() is not None:
        raise ConflictError(
            resource_type="IMRalphSession", identifier=str(body.document_id)
        )

    # 세션 미리 생성
    session_id = uuid_mod.uuid4()
    ralph_session = IMRalphSession(
        id=session_id,
        document_id=body.document_id,
        pass_number=body.pass_number,
        doc_type="im_full",
        status="PLANNING",
        created_by_email=user.email,
    )
    session.add(ralph_session)
    await session.commit()

    # Celery 태스크 실행
    from src.api.tasks.ralph_loop import run_im_ralph_loop_task

    task = run_im_ralph_loop_task.delay(
        document_id=str(body.document_id),
        pass_number=body.pass_number,
    )

    return IMRalphTriggerResponse(
        session_id=session_id,
        celery_task_id=task.id,
        message=f"Ralph Loop Pass {body.pass_number} 실행이 시작되었습니다.",
    )
