"""Integrations 라우터 테스트 — 외부 서비스 미가동 시 error 반환 확인."""

from httpx import AsyncClient


async def test_fdd_link_returns_error_when_unavailable(client: AsyncClient, transaction_id: str):
    """FDD 서비스 미가동 시 error status 반환."""
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/integrations/fdd/link",
        json={"target_name": "테스트 기업"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "FDD"
    assert data["status"] == "error"
    assert data["error"] is not None


async def test_im_link_returns_error_when_unavailable(client: AsyncClient, transaction_id: str):
    """IM 서비스 미가동 시 error status 반환."""
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/integrations/im/link",
        json={"company_name": "테스트 기업", "project_name": "프로젝트 A"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "IM"
    assert data["status"] == "error"


async def test_kiis_company_search_returns_error_when_unavailable(client: AsyncClient, transaction_id: str):
    """KIIS 서비스 미가동 시 error status 반환."""
    resp = await client.get(
        f"/api/v1/transactions/{transaction_id}/integrations/kiis/company",
        params={"q": "삼성"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "KIIS"
    assert data["status"] == "error"
