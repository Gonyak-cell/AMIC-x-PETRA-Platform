"""Analysis API — VDR 기반 자동 분석 실행 및 상태 조회."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.models.analysis_run import AnalysisRun, AnalysisRunStatus
from app.schemas.fdd_checklist import AnalysisRunCreate, AnalysisRunRead
from app.services.analysis.orchestrator import AnalysisOrchestrator

router = APIRouter(prefix="/deals/{deal_id}/analysis", tags=["analysis"])


@router.post("/run", response_model=AnalysisRunRead, status_code=202)
def start_analysis(
    deal_id: UUID,
    body: AnalysisRunCreate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """VDR 기반 자동 분석 실행.

    VDR에 업로드된 COMPLETED 파일을 기반으로 QoE/NWC/Debt 엔진 실행 후
    FDD 체크리스트를 자동 생성한다.

    Args:
        deal_id: Deal UUID
        body: file_ids 목록 (None이면 VDR 전체)

    Returns:
        202 Accepted — AnalysisRun 레코드
    """
    # 동시 실행 방지
    running = db.scalar(
        select(AnalysisRun).where(
            AnalysisRun.deal_id == deal_id,
            AnalysisRun.status == AnalysisRunStatus.RUNNING,
        )
    )
    if running:
        raise HTTPException(
            status_code=409,
            detail="Analysis is already running for this deal",
        )

    orchestrator = AnalysisOrchestrator(
        db,
        cross_verify_enabled=body.cross_verify_enabled,
    )
    run = orchestrator.run_analysis(
        deal_id=deal_id,
        file_ids=body.file_ids,
        actor=current_user.email,
    )
    return run


@router.get("/runs", response_model=list[AnalysisRunRead])
def list_analysis_runs(
    deal_id: UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_READ),
    db: Session = Depends(get_db),
):
    """분석 실행 내역 조회.

    Args:
        deal_id: Deal UUID

    Returns:
        AnalysisRun 목록 (최신순)
    """
    stmt = (
        select(AnalysisRun)
        .where(AnalysisRun.deal_id == deal_id)
        .order_by(AnalysisRun.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.get("/runs/{run_id}", response_model=AnalysisRunRead)
def get_analysis_run(
    deal_id: UUID,
    run_id: UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_READ),
    db: Session = Depends(get_db),
):
    """분석 실행 상세 조회 (진행률 포함).

    Args:
        deal_id: Deal UUID
        run_id: AnalysisRun UUID

    Returns:
        AnalysisRun 상세
    """
    run = db.scalar(
        select(AnalysisRun).where(
            AnalysisRun.id == run_id,
            AnalysisRun.deal_id == deal_id,
        )
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return run


@router.get("/cross-verification")
def get_cross_verification_result(
    deal_id: UUID,
    current_user: CurrentUser = require_permission(Permission.DEAL_READ),
    db: Session = Depends(get_db),
):
    """최근 분석의 교차검증 결과를 조회한다.

    Args:
        deal_id: Deal UUID

    Returns:
        교차검증 결과 JSON (없으면 404)
    """
    run = db.scalar(
        select(AnalysisRun)
        .where(
            AnalysisRun.deal_id == deal_id,
            AnalysisRun.cross_verify_summary.isnot(None),
        )
        .order_by(AnalysisRun.created_at.desc())
        .limit(1)
    )
    if run is None:
        raise HTTPException(
            status_code=404,
            detail="No cross-verification results found for this deal",
        )
    return run.cross_verify_summary
