"""Tests for Analysis API endpoints.

분석 실행 생성, 동시 실행 방지, 상태 추적을 검증한다.
AnalysisOrchestrator의 엔진 호출은 모킹하여 서비스 레이어를 격리 테스트한다.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.analysis_run import AnalysisRun, AnalysisRunStatus
from app.models.deal import Deal, DealType
from app.models.fdd_checklist import (
    ChecklistCategory,
    ChecklistSeverity,
    ChecklistStatus,
    FddChecklist,
    FddChecklistItem,
)


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def deal(db: Session) -> Deal:
    """테스트용 Deal 생성."""
    deal = Deal(
        name="Analysis Test Deal",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@pytest.fixture
def completed_analysis_run(db: Session, deal: Deal) -> AnalysisRun:
    """완료된 분석 실행 레코드 생성."""
    checklist = FddChecklist(
        deal_id=deal.id,
        version=1,
        status=ChecklistStatus.PENDING_REVIEW,
        created_by="test@autofdd.dev",
    )
    db.add(checklist)
    db.flush()

    # 최소 1개 항목 추가
    db.add(
        FddChecklistItem(
            checklist_id=checklist.id,
            category=ChecklistCategory.REVENUE_RECOGNITION,
            order_index=0,
            title="Revenue",
            description="Test",
            severity=ChecklistSeverity.HIGH,
        )
    )

    run = AnalysisRun(
        deal_id=deal.id,
        trigger="manual",
        status=AnalysisRunStatus.COMPLETED,
        output_checklist_id=checklist.id,
        progress_percent=100,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@pytest.fixture
def running_analysis(db: Session, deal: Deal) -> AnalysisRun:
    """실행 중인 분석 레코드 생성."""
    run = AnalysisRun(
        deal_id=deal.id,
        trigger="manual",
        status=AnalysisRunStatus.RUNNING,
        progress_percent=50,
        started_at=datetime.now(UTC),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


# ── POST /deals/{deal_id}/analysis/run ─────────────────────────────────


class TestStartAnalysis:
    @patch("app.api.analysis.AnalysisOrchestrator")
    def test_start_analysis_success(
        self, mock_orch_cls, client: TestClient, db: Session, deal: Deal
    ):
        """분석 실행 성공 (오케스트레이터 모킹)."""
        # 모킹: run_analysis가 AnalysisRun 객체를 반환
        mock_run = AnalysisRun(
            id=uuid.uuid4(),
            deal_id=deal.id,
            trigger="manual",
            status=AnalysisRunStatus.COMPLETED,
            progress_percent=100,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db.add(mock_run)
        db.commit()
        db.refresh(mock_run)

        mock_instance = MagicMock()
        mock_instance.run_analysis.return_value = mock_run
        mock_orch_cls.return_value = mock_instance

        resp = client.post(
            f"/api/v1/deals/{deal.id}/analysis/run",
            json={},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "COMPLETED"
        assert data["deal_id"] == str(deal.id)

    def test_concurrent_execution_blocked(
        self, client: TestClient, deal: Deal, running_analysis: AnalysisRun
    ):
        """이미 실행 중인 분석이 있으면 409 반환."""
        resp = client.post(
            f"/api/v1/deals/{deal.id}/analysis/run",
            json={},
        )
        assert resp.status_code == 409
        assert "already running" in resp.json()["detail"]

    @patch("app.api.analysis.AnalysisOrchestrator")
    def test_start_analysis_with_file_ids(
        self, mock_orch_cls, client: TestClient, db: Session, deal: Deal
    ):
        """특정 파일 ID 목록으로 분석 실행."""
        mock_run = AnalysisRun(
            id=uuid.uuid4(),
            deal_id=deal.id,
            trigger="manual",
            status=AnalysisRunStatus.COMPLETED,
            progress_percent=100,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db.add(mock_run)
        db.commit()
        db.refresh(mock_run)

        mock_instance = MagicMock()
        mock_instance.run_analysis.return_value = mock_run
        mock_orch_cls.return_value = mock_instance

        file_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        resp = client.post(
            f"/api/v1/deals/{deal.id}/analysis/run",
            json={"file_ids": file_ids},
        )
        assert resp.status_code == 202

        # 오케스트레이터에 file_ids가 전달되었는지 확인
        call_kwargs = mock_instance.run_analysis.call_args
        assert call_kwargs.kwargs.get("file_ids") is not None or (
            len(call_kwargs.args) > 1 and call_kwargs.args[1] is not None
        )


# ── GET /deals/{deal_id}/analysis/runs ─────────────────────────────────


class TestListAnalysisRuns:
    def test_list_runs(
        self,
        client: TestClient,
        deal: Deal,
        completed_analysis_run: AnalysisRun,
    ):
        resp = client.get(f"/api/v1/deals/{deal.id}/analysis/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["deal_id"] == str(deal.id)

    def test_list_runs_empty(self, client: TestClient, deal: Deal):
        resp = client.get(f"/api/v1/deals/{deal.id}/analysis/runs")
        assert resp.status_code == 200
        assert resp.json() == []


# ── GET /deals/{deal_id}/analysis/runs/{run_id} ───────────────────────


class TestGetAnalysisRun:
    def test_get_run_detail(
        self,
        client: TestClient,
        deal: Deal,
        completed_analysis_run: AnalysisRun,
    ):
        resp = client.get(
            f"/api/v1/deals/{deal.id}/analysis/runs/{completed_analysis_run.id}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(completed_analysis_run.id)
        assert data["status"] == "COMPLETED"
        assert data["progress_percent"] == 100

    def test_get_run_not_found(self, client: TestClient, deal: Deal):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/deals/{deal.id}/analysis/runs/{fake_id}")
        assert resp.status_code == 404

    def test_get_running_analysis_shows_progress(
        self, client: TestClient, deal: Deal, running_analysis: AnalysisRun
    ):
        resp = client.get(
            f"/api/v1/deals/{deal.id}/analysis/runs/{running_analysis.id}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "RUNNING"
        assert data["progress_percent"] == 50


# ── Unit: AnalysisOrchestrator ──────────────────────────────────────────


class TestAnalysisOrchestratorUnit:
    def test_orchestrator_creates_checklist(self, db: Session, deal: Deal):
        """오케스트레이터가 엔진 없이도 18개 체크리스트 항목을 생성한다."""
        from app.services.analysis.orchestrator import AnalysisOrchestrator

        orch = AnalysisOrchestrator(db)

        # 엔진 호출 모킹 (데이터 없어서 None 반환되도록)
        with (
            patch.object(orch, "_run_qoe", return_value=None),
            patch.object(orch, "_run_nwc", return_value=None),
            patch.object(orch, "_run_debt", return_value=None),
            patch.object(orch, "_get_or_create_snapshot") as mock_snapshot,
        ):
            mock_snapshot.return_value = MagicMock(id=uuid.uuid4())
            run = orch.run_analysis(deal.id, actor="test@autofdd.dev")

        assert run.status == AnalysisRunStatus.COMPLETED
        assert run.progress_percent == 100
        assert run.output_checklist_id is not None

        # 체크리스트 확인
        checklist = db.get(FddChecklist, run.output_checklist_id)
        assert checklist is not None
        assert len(checklist.items) == 18
        assert checklist.status == ChecklistStatus.PENDING_REVIEW

    def test_orchestrator_handles_missing_deal(self, db: Session):
        """존재하지 않는 Deal ID로 실행 시 ValueError."""
        from app.services.analysis.orchestrator import AnalysisOrchestrator

        orch = AnalysisOrchestrator(db)
        with pytest.raises(ValueError, match="not found"):
            orch.run_analysis(uuid.uuid4())

    def test_orchestrator_increments_version(self, db: Session, deal: Deal):
        """동일 Deal에 대해 분석 재실행 시 체크리스트 버전 증가."""
        from app.services.analysis.orchestrator import AnalysisOrchestrator

        orch = AnalysisOrchestrator(db)

        with (
            patch.object(orch, "_run_qoe", return_value=None),
            patch.object(orch, "_run_nwc", return_value=None),
            patch.object(orch, "_run_debt", return_value=None),
            patch.object(orch, "_get_or_create_snapshot") as mock_snapshot,
        ):
            mock_snapshot.return_value = MagicMock(id=uuid.uuid4())
            run1 = orch.run_analysis(deal.id)

        # 두 번째 실행
        orch2 = AnalysisOrchestrator(db)
        with (
            patch.object(orch2, "_run_qoe", return_value=None),
            patch.object(orch2, "_run_nwc", return_value=None),
            patch.object(orch2, "_run_debt", return_value=None),
            patch.object(orch2, "_get_or_create_snapshot") as mock_snapshot2,
        ):
            mock_snapshot2.return_value = MagicMock(id=uuid.uuid4())
            run2 = orch2.run_analysis(deal.id)

        cl1 = db.get(FddChecklist, run1.output_checklist_id)
        cl2 = db.get(FddChecklist, run2.output_checklist_id)
        assert cl1.version == 1
        assert cl2.version == 2
