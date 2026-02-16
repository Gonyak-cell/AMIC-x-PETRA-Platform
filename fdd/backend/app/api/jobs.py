"""Job API — FDD-1801, FDD-1802.

Job 생성, 상태 조회, 진행률, 취소.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.auth.rbac import Permission
from app.database import get_db
from app.models.job import JobStatus, JobType
from app.schemas.job import JobCreate, JobListResponse, JobProgress, JobRead
from app.services.jobs.orchestrator import JobOrchestrator

router = APIRouter(tags=["jobs"])


@router.post("/jobs", response_model=JobRead, status_code=201)
def create_job(
    body: JobCreate,
    current_user: CurrentUser = require_permission(Permission.REPORT_GENERATE),
    db: Session = Depends(get_db),
) -> JobRead:
    """새 Job을 생성한다."""
    orch = JobOrchestrator(db)
    job = orch.create_job(
        job_type=body.job_type,
        deal_id=body.deal_id,
        user_id=current_user.id,
        input_params=body.input_params,
        max_retries=body.max_retries,
        timeout_seconds=body.timeout_seconds,
    )
    return JobRead.model_validate(job)


@router.get("/jobs", response_model=list[JobRead])
def list_jobs(
    deal_id: uuid.UUID | None = Query(default=None),
    status: JobStatus | None = Query(default=None),
    job_type: JobType | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JobRead]:
    """Job 목록을 조회한다."""
    orch = JobOrchestrator(db)
    jobs = orch.list_jobs(
        deal_id=deal_id, status=status, job_type=job_type, limit=limit, offset=offset
    )
    return [JobRead.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobRead:
    """Job 상태를 조회한다."""
    orch = JobOrchestrator(db)
    job = orch.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobRead.model_validate(job)


@router.get("/jobs/{job_id}/progress", response_model=JobProgress)
def get_job_progress(
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobProgress:
    """Job 진행률을 조회한다."""
    orch = JobOrchestrator(db)
    job = orch.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    elapsed = None
    if job.started_at:
        elapsed = (datetime.utcnow() - job.started_at).total_seconds()

    return JobProgress(
        id=job.id,
        status=job.status,
        progress_percent=job.progress_percent,
        progress_message=job.progress_message,
        retry_count=job.retry_count,
        started_at=job.started_at,
        elapsed_seconds=elapsed,
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobRead)
def cancel_job(
    job_id: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.REPORT_GENERATE),
    db: Session = Depends(get_db),
) -> JobRead:
    """Job을 취소한다."""
    orch = JobOrchestrator(db)
    try:
        job = orch.cancel_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JobRead.model_validate(job)
