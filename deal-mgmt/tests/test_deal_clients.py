"""Deal Clients API 테스트 — 거래별 클라이언트 할당/관리."""


# ── Assign ────────────────────────────────────────────────
async def test_assign_client(client, transaction_id):
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/clients",
        json={
            "email": "client@company.com",
            "display_name": "김고객",
            "organization": "테스트기업",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "client@company.com"
    assert data["display_name"] == "김고객"
    assert data["organization"] == "테스트기업"


async def test_assign_duplicate_email_409(client, transaction_id):
    body = {
        "email": "dup@company.com",
        "display_name": "중복테스트",
        "organization": "기업",
    }
    resp1 = await client.post(f"/api/v1/transactions/{transaction_id}/clients", json=body)
    assert resp1.status_code == 201

    resp2 = await client.post(f"/api/v1/transactions/{transaction_id}/clients", json=body)
    assert resp2.status_code == 409


# ── List ──────────────────────────────────────────────────
async def test_list_clients(client, transaction_id):
    for i in range(3):
        await client.post(
            f"/api/v1/transactions/{transaction_id}/clients",
            json={
                "email": f"user{i}@company.com",
                "display_name": f"사용자{i}",
                "organization": "기업",
            },
        )
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/clients")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_list_empty(client, transaction_id):
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/clients")
    assert resp.status_code == 200
    assert resp.json() == []


# ── Remove ────────────────────────────────────────────────
async def test_remove_client(client, transaction_id):
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/clients",
        json={
            "email": "remove@company.com",
            "display_name": "삭제대상",
            "organization": "기업",
        },
    )
    client_id = resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/transactions/{transaction_id}/clients/{client_id}")
    assert del_resp.status_code == 204

    list_resp = await client.get(f"/api/v1/transactions/{transaction_id}/clients")
    assert len(list_resp.json()) == 0


async def test_remove_nonexistent_404(client, transaction_id):
    import uuid

    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/v1/transactions/{transaction_id}/clients/{fake_id}")
    assert resp.status_code == 404


# ── Cross-transaction lookup ──────────────────────────────
async def test_lookup_by_email(client, transaction_id):
    await client.post(
        f"/api/v1/transactions/{transaction_id}/clients",
        json={
            "email": "lookup@company.com",
            "display_name": "조회대상",
            "organization": "기업",
        },
    )
    resp = await client.get("/api/v1/deal-clients/by-email", params={"email": "lookup@company.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert "transaction_name" in data[0]


async def test_lookup_nonexistent_email(client):
    resp = await client.get("/api/v1/deal-clients/by-email", params={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert resp.json() == []


# ── RBAC: ANALYST/CLIENT 역할 거부 ───────────────────────
async def test_analyst_cannot_manage_clients(client, transaction_id):
    """ANALYST 역할은 deal_clients 관리 불가 (require_role ADMIN/MANAGER)."""
    from app.core.security import JWTClaims, get_jwt_claims
    from app.main import app
    from tests.conftest import _override_get_jwt_claims

    async def _analyst_claims() -> JWTClaims:
        return JWTClaims(user_id="analyst-id", email="analyst@example.com", role="ANALYST")

    app.dependency_overrides[get_jwt_claims] = _analyst_claims
    try:
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/clients",
            json={"email": "new@company.com", "display_name": "테스트", "organization": "기업"},
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides[get_jwt_claims] = _override_get_jwt_claims


async def test_client_role_cannot_manage_clients(client, transaction_id):
    """CLIENT 역할은 deal_clients 관리 불가."""
    from app.core.security import JWTClaims, get_jwt_claims
    from app.main import app
    from tests.conftest import _override_get_jwt_claims

    async def _client_claims() -> JWTClaims:
        return JWTClaims(user_id="client-id", email="client@investor.com", role="CLIENT")

    app.dependency_overrides[get_jwt_claims] = _client_claims
    try:
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/clients",
            json={"email": "new@company.com", "display_name": "테스트", "organization": "기업"},
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides[get_jwt_claims] = _override_get_jwt_claims
