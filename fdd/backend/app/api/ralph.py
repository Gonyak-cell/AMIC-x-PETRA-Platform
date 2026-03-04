"""Ralph Loop API 엔드포인트."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.models.ralph_session import FddRalphSession
from app.schemas.ralph import (
    RalphProgressRead,
    RalphSessionCreate,
    RalphSessionRead,
)
from app.services.report.report_service import build_report_ir

router = APIRouter(prefix="/deals/{deal_id}/ralph", tags=["ralph"])


@router.post("/sessions", response_model=RalphSessionRead, status_code=201)
async def create_ralph_session(
    deal_id: UUID,
    body: RalphSessionCreate,
    current_user: CurrentUser = require_permission(Permission.REPORT_GENERATE),
    db: Session = Depends(get_db),
):
    """Ralph Loop 세션을 생성하고 실행한다.

    - pass_type="draft": 초안 보고서 품질 개선 (Pass 1)
    - pass_type="final": 체크리스트 반영 최종 보고서 (Pass 2)
    """
    from app.services.ralph_service import FDDRalphService

    if body.pass_type not in ("draft", "final"):
        raise HTTPException(
            status_code=400, detail="pass_type must be 'draft' or 'final'"
        )

    if body.pass_type == "final" and not body.checklist_id:
        raise HTTPException(
            status_code=400, detail="checklist_id required for final pass"
        )

    # Report IR 생성
    report_ir = build_report_ir(db=db, deal_id=deal_id)

    service = FDDRalphService(db)

    if body.pass_type == "draft":
        refined_ir, session = await service.run_draft_pass(
            deal_id=deal_id,
            report_ir=report_ir,
            config=body.config.model_dump() if body.config else None,
            actor=current_user.email,
        )
    else:
        refined_ir, session = await service.run_final_pass(
            deal_id=deal_id,
            report_ir=report_ir,
            checklist_id=UUID(body.checklist_id),
            actor=current_user.email,
        )

    return _session_to_read(session)


@router.get("/sessions", response_model=list[RalphSessionRead])
def list_ralph_sessions(
    deal_id: UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_READ),
    db: Session = Depends(get_db),
):
    """Deal의 Ralph 세션 목록을 조회한다."""
    stmt = (
        select(FddRalphSession)
        .where(FddRalphSession.deal_id == deal_id)
        .order_by(FddRalphSession.created_at.desc())
    )
    sessions = list(db.scalars(stmt).all())
    return [_session_to_read(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=RalphSessionRead)
def get_ralph_session(
    deal_id: UUID,
    session_id: UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_READ),
    db: Session = Depends(get_db),
):
    """Ralph 세션 상세를 조회한다."""
    session = db.get(FddRalphSession, session_id)
    if session is None or session.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Ralph session not found")
    return _session_to_read(session)


@router.get("/sessions/{session_id}/progress", response_model=RalphProgressRead)
def get_ralph_progress(
    deal_id: UUID,
    session_id: UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_READ),
    db: Session = Depends(get_db),
):
    """Ralph 세션의 실시간 진행 상태를 조회한다."""
    session = db.get(FddRalphSession, session_id)
    if session is None or session.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Ralph session not found")

    return RalphProgressRead(
        session_id=str(session.id),
        status=session.status,
        total_iterations=session.total_iterations or 0,
        total_cost_usd=session.total_cost_usd or 0.0,
        final_score=session.final_score or 0.0,
        section_scores=session.section_scores,
        progress=session.progress,
        critical_flags=session.critical_flags,
    )


def _session_to_read(session: FddRalphSession) -> RalphSessionRead:
    return RalphSessionRead(
        id=str(session.id),
        deal_id=str(session.deal_id),
        pass_type=session.pass_type,
        status=session.status,
        checklist_id=str(session.checklist_id) if session.checklist_id else None,
        report_version_id=str(session.report_version_id)
        if session.report_version_id
        else None,
        total_iterations=session.total_iterations or 0,
        total_cost_usd=session.total_cost_usd or 0.0,
        final_score=session.final_score or 0.0,
        section_scores=session.section_scores,
        critical_flags=session.critical_flags,
        error_message=session.error_message,
        created_by=session.created_by,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )
