"""Job Orchestrator — FDD-1801.

비동기 Job 생성, 상태 관리, 재시도, 타임아웃 처리.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditAction, AuditLog
from app.models.job import Job, JobStatus, JobType


class JobOrchestrator:
    """Job 생명주기 관리."""

    def __init__(self, db: Session):
        self.db = db

    def create_job(
        self,
        *,
        job_type: JobType,
        deal_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        input_params: dict | None = None,
        max_retries: int = 3,
        timeout_seconds: int = 600,
    ) -> Job:
        """새 Job을 PENDING 상태로 생성한다."""
        job = Job(
            job_type=job_type,
            status=JobStatus.PENDING,
            deal_id=deal_id,
            user_id=user_id,
            input_params=input_params,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )
        self.db.add(job)
        self.db.flush()

        self.db.add(
            AuditLog(
                deal_id=deal_id,
                entity_type="job",
                entity_id=job.id,
                action=AuditAction.CREATE,
                actor="system",
                user_id=user_id,
                new_value={"job_type": job_type.value, "status": JobStatus.PENDING.value},
            )
        )
        self.db.commit()
        return job

    def start_job(self, job_id: uuid.UUID) -> Job:
        """Job을 RUNNING 상태로 전환한다."""
        job = self._get_job(job_id)
        if job.status != JobStatus.PENDING:
            raise ValueError(f"Job {job_id} is not PENDING (current: {job.status})")

        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        job.progress_percent = 0
        job.progress_message = "시작됨"
        self.db.commit()
        return job

    def update_progress(
        self, job_id: uuid.UUID, percent: int, message: str | None = None
    ) -> Job:
        """Job 진행률을 업데이트한다."""
        job = self._get_job(job_id)
        if job.status != JobStatus.RUNNING:
            raise ValueError(f"Job {job_id} is not RUNNING (current: {job.status})")

        job.progress_percent = min(max(percent, 0), 100)
        if message:
            job.progress_message = message
        self.db.commit()
        return job

    def complete_job(
        self, job_id: uuid.UUID, output_result: dict | None = None
    ) -> Job:
        """Job을 COMPLETED 상태로 전환한다."""
        job = self._get_job(job_id)
        if job.status != JobStatus.RUNNING:
            raise ValueError(f"Job {job_id} is not RUNNING (current: {job.status})")

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.progress_percent = 100
        job.progress_message = "완료"
        job.output_result = output_result
        self.db.commit()
        return job

    def fail_job(
        self, job_id: uuid.UUID, error_message: str, *, retry: bool = True
    ) -> Job:
        """Job 실패 처리. retry=True이면 재시도 가능 시 PENDING으로 되돌린다."""
        job = self._get_job(job_id)

        if retry and job.retry_count < job.max_retries:
            job.retry_count += 1
            job.status = JobStatus.PENDING
            job.error_message = error_message
            job.progress_message = f"재시도 {job.retry_count}/{job.max_retries}"
            job.started_at = None
        else:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_message = error_message
            job.progress_message = "실패"

        self.db.commit()
        return job

    def cancel_job(self, job_id: uuid.UUID) -> Job:
        """Job을 취소한다."""
        job = self._get_job(job_id)
        if job.status in (JobStatus.COMPLETED, JobStatus.CANCELLED):
            raise ValueError(f"Job {job_id} cannot be cancelled (current: {job.status})")

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        job.progress_message = "취소됨"
        self.db.commit()
        return job

    def get_job(self, job_id: uuid.UUID) -> Job | None:
        """Job을 조회한다."""
        return self.db.get(Job, job_id)

    def list_jobs(
        self,
        *,
        deal_id: uuid.UUID | None = None,
        status: JobStatus | None = None,
        job_type: JobType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Job]:
        """Job 목록을 조회한다."""
        stmt = select(Job)
        if deal_id is not None:
            stmt = stmt.where(Job.deal_id == deal_id)
        if status is not None:
            stmt = stmt.where(Job.status == status)
        if job_type is not None:
            stmt = stmt.where(Job.job_type == job_type)
        stmt = stmt.order_by(Job.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def check_timed_out_jobs(self) -> list[Job]:
        """타임아웃된 RUNNING Job을 찾아 FAILED로 전환한다."""
        now = datetime.utcnow()
        stmt = select(Job).where(
            Job.status == JobStatus.RUNNING,
            Job.started_at.isnot(None),
        )
        running_jobs = list(self.db.scalars(stmt).all())
        timed_out: list[Job] = []

        for job in running_jobs:
            if job.started_at and (now - job.started_at).total_seconds() > job.timeout_seconds:
                self.fail_job(job.id, "Job timed out", retry=True)
                timed_out.append(job)

        return timed_out

    def _get_job(self, job_id: uuid.UUID) -> Job:
        """Job을 조회하고 없으면 예외를 발생시킨다."""
        job = self.db.get(Job, job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        return job
