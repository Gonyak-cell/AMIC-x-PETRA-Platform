"""Client Portal API 테스트 — CLIENT 전용 대시보드."""

from app.core.security import JWTClaims, get_jwt_claims
from app.main import app

CLIENT_CLAIMS = JWTClaims(
    user_id="client-user-id",
    email="portal@company.com",
    role="CLIENT",
)


def _override_client_claims() -> JWTClaims:
    return CLIENT_CLAIMS


async def test_client_dashboard_requires_client_assignment(client, transaction_id):
    """deal_clients에 등록되지 않은 CLIENT는 접근 불가."""
    original = app.dependency_overrides.get(get_jwt_claims)
    app.dependency_overrides[get_jwt_claims] = _override_client_claims
    try:
        resp = await client.get(f"/api/v1/transactions/{transaction_id}/client-portal/dashboard")
        # CLIENT가 deal_clients에 없으면 403
        assert resp.status_code == 403
    finally:
        if original:
            app.dependency_overrides[get_jwt_claims] = original
        else:
            app.dependency_overrides.pop(get_jwt_claims, None)


async def test_client_dashboard_with_assignment(client, transaction_id):
    """deal_clients에 등록된 CLIENT는 대시보드 접근 가능."""
    # 먼저 ADMIN으로 클라이언트 할당
    await client.post(
        f"/api/v1/transactions/{transaction_id}/clients",
        json={
            "email": "portal@company.com",
            "display_name": "포탈고객",
            "organization": "기업",
        },
    )

    original = app.dependency_overrides.get(get_jwt_claims)
    app.dependency_overrides[get_jwt_claims] = _override_client_claims
    try:
        resp = await client.get(f"/api/v1/transactions/{transaction_id}/client-portal/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "transaction_name" in data
        assert "current_phase" in data
        assert "team_contacts" in data
        assert "materials" in data
        assert "buyer_summaries" in data
    finally:
        if original:
            app.dependency_overrides[get_jwt_claims] = original
        else:
            app.dependency_overrides.pop(get_jwt_claims, None)


async def test_client_dashboard_nonexistent_txn(client):
    """존재하지 않는 거래 ID → 404."""
    import uuid

    original = app.dependency_overrides.get(get_jwt_claims)
    app.dependency_overrides[get_jwt_claims] = _override_client_claims
    try:
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/transactions/{fake_id}/client-portal/dashboard")
        assert resp.status_code in (403, 404)
    finally:
        if original:
            app.dependency_overrides[get_jwt_claims] = original
        else:
            app.dependency_overrides.pop(get_jwt_claims, None)
