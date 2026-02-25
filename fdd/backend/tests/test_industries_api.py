"""Industries & Deal Summary API 엔드포인트 테스트 — Phase 6.

GET /api/v1/industries + GET /api/v1/deals/{deal_id}/summary 검증.
"""

import uuid
from datetime import date

import pytest

from app.models.deal import Deal, DealStatus, DealType, IndustryType


class TestIndustriesEndpoint:
    """GET /api/v1/industries 엔드포인트 테스트."""

    def test_returns_industry_list(self, client):
        """산업 목록을 JSON 배열로 반환해야 한다."""
        response = client.get("/api/v1/industries")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_returns_six_industries(self, client):
        """6개 산업이 반환되어야 한다."""
        response = client.get("/api/v1/industries")
        data = response.json()
        assert len(data) == 6

    def test_each_industry_has_required_fields(self, client):
        """각 산업에 id, name_kr, name_en 필드가 있어야 한다."""
        response = client.get("/api/v1/industries")
        data = response.json()
        for industry in data:
            assert "id" in industry
            assert "name_kr" in industry
            assert "name_en" in industry

    def test_general_industry_present(self, client):
        """general 산업이 목록에 존재해야 한다."""
        response = client.get("/api/v1/industries")
        data = response.json()
        ids = [ind["id"] for ind in data]
        assert "general" in ids


class TestDealSummaryEndpoint:
    """GET /api/v1/deals/{deal_id}/summary 엔드포인트 테스트."""

    def test_deal_not_found(self, client, auth_headers):
        """존재하지 않는 Deal ID는 404를 반환해야 한다."""
        fake_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/deals/{fake_id}/summary",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_summary_with_empty_analyses(self, client, auth_headers, db):
        """분석 결과가 없는 Deal은 qoe/nwc/debt가 null이어야 한다."""
        deal = Deal(
            id=uuid.uuid4(),
            name="Test Deal",
            deal_type=DealType.COMPLETION_ACCOUNTS,
            base_currency="KRW",
            reference_date=date(2025, 6, 30),
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            status=DealStatus.ACTIVE,
            industry=IndustryType.TECH_SAAS,
            created_by="test@autofdd.dev",
        )
        db.add(deal)
        db.commit()
        db.refresh(deal)

        response = client.get(
            f"/api/v1/deals/{deal.id}/summary",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["deal_id"] == str(deal.id)
        assert data["deal_name"] == "Test Deal"
        assert data["industry"] == "tech"
        assert data["qoe"] is None
        assert data["nwc"] is None
        assert data["debt"] is None
