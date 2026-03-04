"""Tests for Ralph API endpoints.

Ralph 세션 생성, 목록 조회, 상세 조회, 진행 상태 조회 API를 검증한다.
"""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.deal import Deal, DealType
from app.models.ralph_session import FddRalphSession, FddRalphSessionStatus


@pytest.fixture
def deal(db: Session) -> Deal:
    deal = Deal(
        name="Ralph API Test Deal",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@pytest.fixture
def ralph_session(db: Session, deal: Deal) -> FddRalphSession:
    session = FddRalphSession(
        deal_id=deal.id,
        pass_type="draft",
        status=FddRalphSessionStatus.COMPLETED,
        total_iterations=6,
        total_cost_usd=3.50,
        final_score=4.2,
        section_scores={"exec_summary": 4.5, "qoe_commentary": 4.0},
        critical_flags=[],
        progress={"sections": {}},
        created_by="test@autofdd.dev",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


class TestRalphSessionList:
    def test_list_sessions(self, client, deal, ralph_session, auth_headers, test_user):
        resp = client.get(
            f"/api/v1/deals/{deal.id}/ralph/sessions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["pass_type"] == "draft"
        assert data[0]["status"] == FddRalphSessionStatus.COMPLETED

    def test_list_sessions_empty(self, client, deal, auth_headers, test_user):
        resp = client.get(
            f"/api/v1/deals/{deal.id}/ralph/sessions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestRalphSessionDetail:
    def test_get_session(self, client, deal, ralph_session, auth_headers, test_user):
        resp = client.get(
            f"/api/v1/deals/{deal.id}/ralph/sessions/{ralph_session.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(ralph_session.id)
        assert data["final_score"] == 4.2
        assert data["total_iterations"] == 6

    def test_get_session_not_found(self, client, deal, auth_headers, test_user):
        fake_id = uuid.uuid4()
        resp = client.get(
            f"/api/v1/deals/{deal.id}/ralph/sessions/{fake_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get_session_wrong_deal(
        self, client, db, deal, ralph_session, auth_headers, test_user
    ):
        """Deal ID가 다른 세션은 404를 반환해야 한다."""
        other_deal = Deal(
            name="Other Deal",
            deal_type=DealType.COMPLETION_ACCOUNTS,
            base_currency="KRW",
        )
        db.add(other_deal)
        db.commit()
        db.refresh(other_deal)

        resp = client.get(
            f"/api/v1/deals/{other_deal.id}/ralph/sessions/{ralph_session.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestRalphProgress:
    def test_get_progress(self, client, deal, ralph_session, auth_headers, test_user):
        resp = client.get(
            f"/api/v1/deals/{deal.id}/ralph/sessions/{ralph_session.id}/progress",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == str(ralph_session.id)
        assert data["status"] == FddRalphSessionStatus.COMPLETED
        assert data["final_score"] == 4.2
        assert data["total_iterations"] == 6

    def test_get_progress_not_found(self, client, deal, auth_headers, test_user):
        fake_id = uuid.uuid4()
        resp = client.get(
            f"/api/v1/deals/{deal.id}/ralph/sessions/{fake_id}/progress",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestRalphSchemaValidation:
    def test_report_generate_request_ralph_fields(self):
        """ReportGenerateRequest에 ralph_enabled 필드가 있어야 한다."""
        from app.schemas.report import ReportGenerateRequest

        req = ReportGenerateRequest()
        assert req.ralph_enabled is False
        assert req.ralph_config is None

    def test_report_generate_request_with_ralph_config(self):
        from app.schemas.report import RalphConfigRequest, ReportGenerateRequest

        req = ReportGenerateRequest(
            ralph_enabled=True,
            ralph_config=RalphConfigRequest(
                max_iterations_per_section=2,
                max_cost_usd=10.0,
                pass_threshold=3.5,
            ),
        )
        assert req.ralph_enabled is True
        assert req.ralph_config is not None
        assert req.ralph_config.max_iterations_per_section == 2

    def test_ralph_config_validation(self):
        from pydantic import ValidationError

        from app.schemas.report import RalphConfigRequest

        with pytest.raises(ValidationError):
            RalphConfigRequest(max_iterations_per_section=0)  # ge=1

        with pytest.raises(ValidationError):
            RalphConfigRequest(max_cost_usd=0.5)  # ge=1.0

        with pytest.raises(ValidationError):
            RalphConfigRequest(pass_threshold=2.0)  # ge=3.0
