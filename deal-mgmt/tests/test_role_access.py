"""역할별 접근 제어 테스트.

require_write_access()는 CLIENT 역할만 차단한다.
ANALYST, MANAGER, ADMIN은 모두 쓰기 가능.
CLIENT는 deal_clients 등록된 딜만 읽기 가능, 쓰기 전면 차단.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from app.core.security import JWTClaims, get_jwt_claims
from app.main import app

CLIENT_CLAIMS = JWTClaims(
    user_id="client-user-id",
    email="client@investor.com",
    role="CLIENT",
)

ANALYST_CLAIMS = JWTClaims(
    user_id="analyst-user-id",
    email="analyst@example.com",
    role="ANALYST",
)

MANAGER_CLAIMS = JWTClaims(
    user_id="manager-user-id",
    email="manager@example.com",
    role="MANAGER",
)


@pytest.fixture()
async def _as_client() -> AsyncGenerator[None, None]:
    """테스트 동안 JWT claims를 CLIENT로 오버라이드하고, 종료 시 원래 상태로 복원."""
    prev = app.dependency_overrides.get(get_jwt_claims)

    async def _override() -> JWTClaims:
        return CLIENT_CLAIMS

    app.dependency_overrides[get_jwt_claims] = _override
    yield
    if prev is not None:
        app.dependency_overrides[get_jwt_claims] = prev
    else:
        app.dependency_overrides.pop(get_jwt_claims, None)


@pytest.fixture()
async def _as_analyst() -> AsyncGenerator[None, None]:
    """테스트 동안 JWT claims를 ANALYST로 오버라이드하고, 종료 시 원래 상태로 복원."""
    prev = app.dependency_overrides.get(get_jwt_claims)

    async def _override() -> JWTClaims:
        return ANALYST_CLAIMS

    app.dependency_overrides[get_jwt_claims] = _override
    yield
    if prev is not None:
        app.dependency_overrides[get_jwt_claims] = prev
    else:
        app.dependency_overrides.pop(get_jwt_claims, None)


@pytest.fixture()
async def _as_manager() -> AsyncGenerator[None, None]:
    """테스트 동안 JWT claims를 MANAGER로 오버라이드하고, 종료 시 원래 상태로 복원."""
    prev = app.dependency_overrides.get(get_jwt_claims)

    async def _override() -> JWTClaims:
        return MANAGER_CLAIMS

    app.dependency_overrides[get_jwt_claims] = _override
    yield
    if prev is not None:
        app.dependency_overrides[get_jwt_claims] = prev
    else:
        app.dependency_overrides.pop(get_jwt_claims, None)


# ── CLIENT: 쓰기 차단 ─────────────────────────────────────
@pytest.mark.usefixtures("_as_client")
async def test_client_cannot_create_transaction(client):
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "name": "클라이언트 생성 시도",
            "deal_type": "SE",
            "side": "SELL",
            "target_company_name": "기업",
            "client_name": "고객",
            "lead_advisor_email": "client@investor.com",
        },
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_as_client")
async def test_client_cannot_create_buyer(client, transaction_id):
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/buyers",
        json={"company_name": "클라이언트추가기업", "buyer_type": "STRATEGIC"},
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_as_client")
async def test_client_cannot_create_approval(client, transaction_id):
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/approvals",
        json={
            "approval_type": "PHASE_ADVANCE",
            "title": "클라이언트 승인 시도",
            "approvers": [{"email": "boss@example.com", "role": "대표"}],
        },
    )
    assert resp.status_code == 403


# ── ANALYST: 읽기/쓰기 모두 허용 ─────────────────────────
@pytest.mark.usefixtures("_as_analyst")
async def test_analyst_can_read_transactions(client, transaction_id):
    resp = await client.get(f"/api/v1/transactions/{transaction_id}")
    assert resp.status_code == 200


@pytest.mark.usefixtures("_as_analyst")
async def test_analyst_can_read_dashboard(client):
    resp = await client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 200


@pytest.mark.usefixtures("_as_analyst")
async def test_analyst_can_create_transaction(client):
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "name": "분석가 생성 거래",
            "deal_type": "SE",
            "side": "SELL",
            "target_company_name": "기업",
            "client_name": "고객",
            "lead_advisor_email": "analyst@example.com",
        },
    )
    assert resp.status_code == 201


# ── MANAGER: 읽기/쓰기 모두 허용 ─────────────────────────
@pytest.mark.usefixtures("_as_manager")
async def test_manager_can_read_transactions(client, transaction_id):
    resp = await client.get(f"/api/v1/transactions/{transaction_id}")
    assert resp.status_code == 200


@pytest.mark.usefixtures("_as_manager")
async def test_manager_can_create_transaction(client):
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "name": "매니저 생성 거래",
            "deal_type": "SE",
            "side": "BUY",
            "target_company_name": "대상기업",
            "client_name": "고객기업",
            "lead_advisor_email": "manager@example.com",
        },
    )
    assert resp.status_code == 201
