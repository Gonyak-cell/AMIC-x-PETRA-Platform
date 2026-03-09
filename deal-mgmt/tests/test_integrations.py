"""Integrations 라우터 테스트 — DI Mock 클라이언트 기반.

conftest.py에서 get_fdd_client / get_im_client / get_kiis_client가
MockFDDClient / MockIMClient / MockKIISClient로 오버라이드되므로
외부 서비스 없이도 정상 응답을 검증할 수 있다.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.dependencies import get_fdd_client, get_im_client, get_kiis_client
from app.main import app

# ── 실패용 Mock 클라이언트 ────────────────────────────────


class FailingFDDClient:
    """외부 서비스 장애를 시뮬레이션하는 FDD 클라이언트."""

    async def create_deal(self, target_name: str, industry: str | None = None) -> dict:
        raise ConnectionError("FDD 서비스 연결 불가")

    async def get_deal_status(self, deal_id: uuid.UUID) -> dict:
        raise ConnectionError("FDD 서비스 연결 불가")

    async def trigger_analysis(self, deal_id: uuid.UUID, analysis_type: str) -> dict:
        raise ConnectionError("FDD 서비스 연결 불가")


class FailingIMClient:
    """외부 서비스 장애를 시뮬레이션하는 IM 클라이언트."""

    async def create_document(
        self,
        company_name: str,
        project_name: str,
        corp_code: str | None = None,
    ) -> dict:
        raise ConnectionError("IM 서비스 연결 불가")

    async def get_document_status(self, document_id: uuid.UUID) -> dict:
        raise ConnectionError("IM 서비스 연결 불가")

    async def trigger_generation(self, document_id: uuid.UUID) -> dict:
        raise ConnectionError("IM 서비스 연결 불가")


class FailingKIISClient:
    """외부 서비스 장애를 시뮬레이션하는 KIIS 클라이언트."""

    async def search_company(self, name: str) -> list[dict]:
        raise ConnectionError("KIIS 서비스 연결 불가")

    async def get_company_detail(self, corp_code: str) -> dict:
        raise ConnectionError("KIIS 서비스 연결 불가")

    async def get_financial_summary(self, corp_code: str) -> dict:
        raise ConnectionError("KIIS 서비스 연결 불가")

    async def search_gps(self, query: str) -> list[dict]:
        raise ConnectionError("KIIS 서비스 연결 불가")

    async def close(self) -> None:
        pass


# ── 정상 경로 테스트 ──────────────────────────────────────


async def test_fdd_link_returns_linked(client: AsyncClient, transaction_id: str):
    """FDD Mock 클라이언트 → linked 응답 확인."""
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/integrations/fdd/link",
        json={"target_name": "테스트 기업"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "FDD"
    assert data["status"] == "linked"
    assert data["data"] is not None
    assert data["data"]["target_name"] == "테스트 기업"


async def test_im_link_returns_linked(client: AsyncClient, transaction_id: str):
    """IM Mock 클라이언트 → linked 응답 확인."""
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/integrations/im/link",
        json={"company_name": "테스트 기업", "project_name": "프로젝트 A"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "IM"
    assert data["status"] == "linked"
    assert data["data"] is not None
    assert data["data"]["company_name"] == "테스트 기업"


async def test_kiis_company_search_returns_results(client: AsyncClient, transaction_id: str):
    """KIIS Mock 클라이언트 → 검색 결과 확인."""
    resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/integrations/kiis/company",
        params={"q": "삼성"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "KIIS"
    assert data["status"] == "ok"
    assert data["data"] is not None
    items = data["data"]["items"]
    assert len(items) >= 1
    assert "삼성" in items[0]["corp_name"]


# ── 에러 경로 테스트 (외부 서비스 장애 시뮬레이션) ────────


@pytest.fixture()
def _override_failing_fdd():
    """FDD 클라이언트를 장애 Mock으로 교체."""
    app.dependency_overrides[get_fdd_client] = FailingFDDClient
    yield
    from app.services.mock_clients import MockFDDClient

    app.dependency_overrides[get_fdd_client] = MockFDDClient


@pytest.fixture()
def _override_failing_im():
    """IM 클라이언트를 장애 Mock으로 교체."""
    app.dependency_overrides[get_im_client] = FailingIMClient
    yield
    from app.services.mock_clients import MockIMClient

    app.dependency_overrides[get_im_client] = MockIMClient


@pytest.fixture()
def _override_failing_kiis():
    """KIIS 클라이언트를 장애 Mock으로 교체."""
    app.dependency_overrides[get_kiis_client] = FailingKIISClient
    yield
    from app.services.mock_clients import MockKIISClient

    app.dependency_overrides[get_kiis_client] = MockKIISClient


@pytest.mark.usefixtures("_override_failing_fdd")
async def test_fdd_link_error_on_service_failure(client: AsyncClient, transaction_id: str):
    """FDD 서비스 장애 → status=error 응답."""
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/integrations/fdd/link",
        json={"target_name": "테스트 기업"},
    )
    assert resp.status_code == 502
    data = resp.json()
    assert "FDD" in data["detail"]


@pytest.mark.usefixtures("_override_failing_im")
async def test_im_link_error_on_service_failure(client: AsyncClient, transaction_id: str):
    """IM 서비스 장애 → 502 응답."""
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/integrations/im/link",
        json={"company_name": "테스트 기업", "project_name": "프로젝트 A"},
    )
    assert resp.status_code == 502
    data = resp.json()
    assert "IM" in data["detail"]


@pytest.mark.usefixtures("_override_failing_kiis")
async def test_kiis_search_error_on_service_failure(client: AsyncClient, transaction_id: str):
    """KIIS 서비스 장애 → 502 응답."""
    resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/integrations/kiis/company",
        params={"q": "삼성"},
    )
    assert resp.status_code == 502
    data = resp.json()
    assert "KIIS" in data["detail"]
