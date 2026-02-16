"""Issue API — Sprint 6 (FDD-504).

이상치 탐지 실행, 이슈 CRUD, 요약 통계 엔드포인트.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.models.deal import Deal
from app.models.issue import IssueCategory, IssueSeverity, IssueStatus
from app.schemas.issue import (
    AnomalyDetectionRequest,
    AnomalyDetectionResponse,
    IssueCreate,
    IssueListResponse,
    IssueRead,
    IssueSummary,
    IssueUpdate,
)
from app.services.issues.issue_service import (
    create_issue,
    get_issue,
    get_issue_summary,
    get_issues,
    run_anomaly_detection,
    update_issue_status,
)

router = APIRouter()


# ── Anomaly Detection ────────────────────────────────────


@router.post(
    "/deals/{deal_id}/issues/detect-anomalies",
    response_model=AnomalyDetectionResponse,
    status_code=201,
)
def detect_anomalies(
    deal_id: uuid.UUID,
    body: AnomalyDetectionRequest,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """이상치 탐지를 실행하고 Issue를 생성한다."""
    deal = db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    return run_anomaly_detection(
        db=db,
        deal_id=deal_id,
        snapshot_id=body.snapshot_id,
        threshold=body.threshold,
    )


# ── Issue CRUD ────────────────────────────────────────────


@router.get(
    "/deals/{deal_id}/issues/summary",
    response_model=IssueSummary,
)
def get_issues_summary(
    deal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """이슈 요약 통계를 조회한다."""
    deal = db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    return get_issue_summary(db, deal_id)


@router.get(
    "/deals/{deal_id}/issues",
    response_model=IssueListResponse,
)
def list_issues(
    deal_id: uuid.UUID,
    severity: IssueSeverity | None = Query(default=None),
    status: IssueStatus | None = Query(default=None),
    category: IssueCategory | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """이슈 목록을 조회한다 (필터 지원)."""
    deal = db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    items, total = get_issues(
        db=db,
        deal_id=deal_id,
        severity=severity,
        status=status,
        category=category,
        limit=limit,
        offset=offset,
    )

    return IssueListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/deals/{deal_id}/issues/{issue_id}",
    response_model=IssueRead,
)
def get_issue_detail(
    deal_id: uuid.UUID,
    issue_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """이슈 상세를 조회한다."""
    deal = db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    issue = get_issue(db, issue_id)
    if issue.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Issue not found in this deal")

    return issue


@router.post(
    "/deals/{deal_id}/issues",
    response_model=IssueRead,
    status_code=201,
)
def create_new_issue(
    deal_id: uuid.UUID,
    body: IssueCreate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """수동으로 이슈를 생성한다."""
    deal = db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    return create_issue(db, deal_id, body)


@router.put(
    "/deals/{deal_id}/issues/{issue_id}",
    response_model=IssueRead,
)
def update_issue(
    deal_id: uuid.UUID,
    issue_id: uuid.UUID,
    body: IssueUpdate,
    current_user: CurrentUser = require_permission(Permission.DEAL_UPDATE),
    db: Session = Depends(get_db),
):
    """이슈 상태를 변경한다."""
    deal = db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    issue = get_issue(db, issue_id)
    if issue.deal_id != deal_id:
        raise HTTPException(status_code=404, detail="Issue not found in this deal")

    return update_issue_status(db, issue_id, body)
