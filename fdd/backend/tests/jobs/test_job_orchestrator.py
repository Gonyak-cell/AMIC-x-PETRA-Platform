"""Job Orchestrator 테스트 — FDD-1801."""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.job import JobStatus, JobType
from app.services.jobs.orchestrator import JobOrchestrator

# ── create_job ─────────────────────────────────────────


def _create_deal(db: Session):
    """Helper to create a deal for FK-dependent tests."""
    from datetime import date

    from app.models.deal import Deal

    deal = Deal(
        name="Job Test Deal",
        deal_type="COMPLETION_ACCOUNTS",
        base_currency="KRW",
        reference_date=date(2025, 12, 31),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


def test_create_job(db: Session):
    deal = _create_deal(db)
    orch = JobOrchestrator(db)
    job = orch.create_job(
        job_type=JobType.REPORT_GENERATE,
        deal_id=deal.id,
        input_params={"format": "pptx"},
    )
    assert job.id is not None
    assert job.status == JobStatus.PENDING
    assert job.progress_percent == 0
    assert job.retry_count == 0
    assert job.max_retries == 3


def test_create_job_custom_params(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(
        job_type=JobType.DATA_INGEST,
        max_retries=5,
        timeout_seconds=120,
    )
    assert job.max_retries == 5
    assert job.timeout_seconds == 120


# ── start_job ──────────────────────────────────────────


def test_start_job(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    started = orch.start_job(job.id)
    assert started.status == JobStatus.RUNNING
    assert started.started_at is not None


def test_start_job_not_pending(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    orch.start_job(job.id)
    with pytest.raises(ValueError, match="not PENDING"):
        orch.start_job(job.id)


# ── update_progress ────────────────────────────────────


def test_update_progress(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    orch.start_job(job.id)
    updated = orch.update_progress(job.id, 50, "QoE 계산 중")
    assert updated.progress_percent == 50
    assert updated.progress_message == "QoE 계산 중"


def test_update_progress_clamped(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    orch.start_job(job.id)
    assert orch.update_progress(job.id, 150).progress_percent == 100
    assert orch.update_progress(job.id, -10).progress_percent == 0


def test_update_progress_not_running(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    with pytest.raises(ValueError, match="not RUNNING"):
        orch.update_progress(job.id, 50)


# ── complete_job ───────────────────────────────────────


def test_complete_job(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    orch.start_job(job.id)
    completed = orch.complete_job(
        job.id, output_result={"file_path": "/reports/1.pptx"}
    )
    assert completed.status == JobStatus.COMPLETED
    assert completed.progress_percent == 100
    assert completed.completed_at is not None
    assert completed.output_result["file_path"] == "/reports/1.pptx"


def test_complete_not_running(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    with pytest.raises(ValueError, match="not RUNNING"):
        orch.complete_job(job.id)


# ── fail_job ───────────────────────────────────────────


def test_fail_job_with_retry(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE, max_retries=3)
    orch.start_job(job.id)
    failed = orch.fail_job(job.id, "Timeout")
    assert failed.status == JobStatus.PENDING  # retried
    assert failed.retry_count == 1
    assert failed.error_message == "Timeout"


def test_fail_job_max_retries_exhausted(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE, max_retries=1)
    orch.start_job(job.id)
    orch.fail_job(job.id, "Error 1")
    # Now retry_count=1, max_retries=1 → next start and fail should be FAILED
    orch.start_job(job.id)
    failed = orch.fail_job(job.id, "Error 2")
    assert failed.status == JobStatus.FAILED
    assert failed.completed_at is not None


def test_fail_job_no_retry(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE, max_retries=3)
    orch.start_job(job.id)
    failed = orch.fail_job(job.id, "Fatal error", retry=False)
    assert failed.status == JobStatus.FAILED


# ── cancel_job ─────────────────────────────────────────


def test_cancel_pending_job(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    cancelled = orch.cancel_job(job.id)
    assert cancelled.status == JobStatus.CANCELLED


def test_cancel_running_job(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    orch.start_job(job.id)
    cancelled = orch.cancel_job(job.id)
    assert cancelled.status == JobStatus.CANCELLED


def test_cancel_completed_job(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    orch.start_job(job.id)
    orch.complete_job(job.id)
    with pytest.raises(ValueError, match="cannot be cancelled"):
        orch.cancel_job(job.id)


# ── list_jobs ──────────────────────────────────────────


def test_list_jobs(db: Session):
    orch = JobOrchestrator(db)
    for _ in range(3):
        orch.create_job(job_type=JobType.REPORT_GENERATE)
    orch.create_job(job_type=JobType.DATA_INGEST)

    all_jobs = orch.list_jobs()
    assert len(all_jobs) == 4

    report_jobs = orch.list_jobs(job_type=JobType.REPORT_GENERATE)
    assert len(report_jobs) == 3


def test_list_jobs_filter_status(db: Session):
    orch = JobOrchestrator(db)
    job1 = orch.create_job(job_type=JobType.REPORT_GENERATE)
    orch.create_job(job_type=JobType.REPORT_GENERATE)
    orch.start_job(job1.id)

    running = orch.list_jobs(status=JobStatus.RUNNING)
    assert len(running) == 1
    assert running[0].id == job1.id


# ── check_timed_out_jobs ──────────────────────────────


def test_timeout_detection(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE, timeout_seconds=1)
    orch.start_job(job.id)
    # Manually set started_at to past
    job.started_at = datetime.utcnow() - timedelta(seconds=10)
    db.commit()

    timed_out = orch.check_timed_out_jobs()
    assert len(timed_out) == 1


def test_no_timeout_for_recent_jobs(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE, timeout_seconds=600)
    orch.start_job(job.id)
    timed_out = orch.check_timed_out_jobs()
    assert len(timed_out) == 0


# ── get_job ────────────────────────────────────────────


def test_get_job(db: Session):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    found = orch.get_job(job.id)
    assert found is not None
    assert found.id == job.id


def test_get_job_not_found(db: Session):
    orch = JobOrchestrator(db)
    assert orch.get_job(uuid.uuid4()) is None
