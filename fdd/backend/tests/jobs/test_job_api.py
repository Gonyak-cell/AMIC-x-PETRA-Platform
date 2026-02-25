"""Job API 테스트 — FDD-1801, FDD-1802."""

import uuid

from app.models.job import JobType
from app.services.jobs.orchestrator import JobOrchestrator


def test_create_job_api(client, db):
    # Create a real deal first to satisfy FK constraint
    deal_resp = client.post(
        "/api/v1/deals",
        json={
            "name": "Job Test Deal",
            "target_company_name": "Job Test Corp",
            "deal_type": "COMPLETION_ACCOUNTS",
            "base_currency": "KRW",
            "reference_date": "2025-12-31",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
        },
    )
    deal_id = deal_resp.json()["id"]

    resp = client.post(
        "/api/v1/jobs",
        json={
            "job_type": "REPORT_GENERATE",
            "deal_id": deal_id,
            "input_params": {"format": "pptx"},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["job_type"] == "REPORT_GENERATE"


def test_list_jobs_api(client, db):
    orch = JobOrchestrator(db)
    for _ in range(3):
        orch.create_job(job_type=JobType.REPORT_GENERATE)

    resp = client.get("/api/v1/jobs")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_list_jobs_filter_status(client, db):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    orch.start_job(job.id)
    orch.create_job(job_type=JobType.REPORT_GENERATE)

    resp = client.get("/api/v1/jobs", params={"status": "RUNNING"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_job_api(client, db):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)

    resp = client.get(f"/api/v1/jobs/{job.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(job.id)


def test_get_job_not_found(client, db):
    resp = client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_get_job_progress(client, db):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    orch.start_job(job.id)
    orch.update_progress(job.id, 42, "QoE 분석 중")

    resp = client.get(f"/api/v1/jobs/{job.id}/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["progress_percent"] == 42
    assert data["progress_message"] == "QoE 분석 중"
    assert data["elapsed_seconds"] is not None


def test_cancel_job_api(client, db):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)

    resp = client.post(f"/api/v1/jobs/{job.id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


def test_cancel_completed_job_api(client, db):
    orch = JobOrchestrator(db)
    job = orch.create_job(job_type=JobType.REPORT_GENERATE)
    orch.start_job(job.id)
    orch.complete_job(job.id)

    resp = client.post(f"/api/v1/jobs/{job.id}/cancel")
    assert resp.status_code == 400
