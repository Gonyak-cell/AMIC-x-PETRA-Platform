"""Chaos / Failure Injection 테스트 — FDD-1805.

장애 주입 10종: Job 상태 전이, 타임아웃, 동시성, 엣지 케이스.
"""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.job import Job, JobStatus, JobType
from app.services.jobs.orchestrator import JobOrchestrator
from app.services.masking.engine import DistributionMode, MaskingEngine
from app.services.metrics.collector import MetricsCollector
from app.services.retention.policy import DataType, RetentionPolicy

# ── 1. Job 다중 재시도 후 최종 실패 ─────────────────────


def test_chaos_job_retry_exhaustion(db: Session):
    """Job이 max_retries까지 재시도한 후 최종 FAILED가 된다."""
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE, max_retries=2)

    for i in range(2):
        orch.start_job(job.id)
        orch.fail_job(job.id, f"Error {i + 1}")

    # 마지막 재시도
    orch.start_job(job.id)
    final = orch.fail_job(job.id, "Final error")
    assert final.status == JobStatus.FAILED
    assert final.retry_count == 2


# ── 2. 동시 타임아웃 + 재시도 ────────────────────────────


def test_chaos_multiple_timeout_jobs(db: Session):
    """여러 Job이 동시에 타임아웃되는 경우."""
    orch = JobOrchestrator(db)
    jobs = []
    for _ in range(5):
        j = orch.create_job(job_type=JobType.DATA_INGEST, timeout_seconds=1)
        orch.start_job(j.id)
        j.started_at = datetime.utcnow() - timedelta(seconds=10)
        jobs.append(j)
    db.commit()

    timed_out = orch.check_timed_out_jobs()
    assert len(timed_out) == 5


# ── 3. Job 상태 전이 무효 ────────────────────────────────


def test_chaos_invalid_state_transitions(db: Session):
    """유효하지 않은 상태 전이가 거부된다."""
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)

    # PENDING → complete (invalid)
    with pytest.raises(ValueError):
        orch.complete_job(job.id)

    # PENDING → progress (invalid)
    with pytest.raises(ValueError):
        orch.update_progress(job.id, 50)

    # start → cancel → start (invalid)
    orch.start_job(job.id)
    orch.cancel_job(job.id)
    with pytest.raises(ValueError):
        orch.start_job(job.id)


# ── 4. 마스킹 엔진 — 빈 데이터 ──────────────────────────


def test_chaos_masking_empty_report():
    """빈 Report IR 마스킹이 에러 없이 동작한다."""
    engine = MaskingEngine.for_mode(DistributionMode.REDACTED)
    result = engine.mask_report_ir({})
    assert result["distribution_mode"] == "REDACTED"


def test_chaos_masking_nested_empty():
    """깊이 중첩된 빈 섹션 마스킹."""
    engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
    ir = {"sections": [{"id": "s1", "blocks": [{"type": "table", "rows": []}]}]}
    result = engine.mask_report_ir(ir)
    assert result["sections"][0]["blocks"][0]["rows"] == []


# ── 5. 마스킹 — 극단적 금액 ─────────────────────────────


def test_chaos_masking_extreme_amounts():
    """매우 크거나 0인 금액 마스킹."""
    from decimal import Decimal

    engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
    assert "X" in engine.mask_amount(Decimal("999999999999"))
    assert "X" in engine.mask_amount(Decimal("0"))
    assert "X" in engine.mask_amount(Decimal("-1"))


# ── 6. 메트릭 수집 — 대량 데이터 ────────────────────────


def test_chaos_metrics_high_volume():
    """대량 메트릭 기록이 문제없이 동작한다."""
    m = MetricsCollector()
    for i in range(10000):
        m.api_requests_total.inc("GET")
        m.api_request_duration.observe(0.001 * i)

    assert m.api_requests_total.get("GET") == 10000
    assert m.api_request_duration.count() == 10000
    # prometheus 출력도 정상
    output = m.to_prometheus()
    assert "10000" in output


# ── 7. Retention — 없는 데이터 파기 ──────────────────────


def test_chaos_purge_no_expired(db: Session):
    """만료 항목이 없을 때 파기 시도."""
    policy = RetentionPolicy(db)
    result = policy.purge_expired_audit_logs(dry_run=False)
    assert result.purged_count == 0


# ── 8. Job 없는 ID 조회 ─────────────────────────────────


def test_chaos_job_operations_on_nonexistent(db: Session):
    """존재하지 않는 Job에 대한 작업이 적절히 실패한다."""
    orch = JobOrchestrator(db)
    fake_id = uuid.uuid4()

    with pytest.raises(ValueError, match="not found"):
        orch.start_job(fake_id)

    with pytest.raises(ValueError, match="not found"):
        orch.cancel_job(fake_id)


# ── 9. 마스킹 — 유니코드 / 특수문자 ──────────────────────


def test_chaos_masking_unicode():
    """유니코드 텍스트 마스킹이 정상 동작한다."""
    engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
    assert "[회사" in engine.mask_text("주식회사 가나다™", "company")
    assert "[인물" in engine.mask_text("김영수 대표이사", "person")


# ── 10. Job 0 retries ───────────────────────────────────


def test_chaos_job_zero_retries(db: Session):
    """max_retries=0이면 첫 실패에서 바로 FAILED."""
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.ANOMALY_DETECT, max_retries=0)
    orch.start_job(job.id)
    failed = orch.fail_job(job.id, "Immediate failure")
    assert failed.status == JobStatus.FAILED
    assert failed.retry_count == 0
