"""역할별 접근 제어 테스트.

require_write_access()는 CLIENT 역할만 차단한다.
ANALYST, MANAGER, ADMIN은 모두 쓰기 가능.
CLIENT는 deal_clients 등록된 딜만 읽기 가능, 쓰기 전면 차단.
"""

from __future__ import annotations

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


def _set_role(claims: JWTClaims) -> None:
    async def _override() -> JWTClaims:
        return claims

    app.dependency_overrides[get_jwt_claims] = _override


def _restore_role() -> None:
    from tests.conftest import _override_get_jwt_claims

    app.dependency_overrides[get_jwt_claims] = _override_get_jwt_claims


# ── CLIENT: 쓰기 차단 ─────────────────────────────────────
async def test_client_cannot_create_transaction(client):
    _set_role(CLIENT_CLAIMS)
    try:
        resp = await client.post(
            "/api/v1/transactions",
            json={
                "name": "클라이언트 생성 시도",
                "deal_type": "MA",
                "side": "SELL",
                "target_company_name": "기업",
                "client_name": "고객",
                "lead_advisor_email": "client@investor.com",
            },
        )
        assert resp.status_code == 403
    finally:
        _restore_role()


async def test_client_cannot_create_buyer(client, transaction_id):
    _set_role(CLIENT_CLAIMS)
    try:
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/buyers",
            json={"company_name": "클라이언트추가기업", "buyer_type": "STRATEGIC"},
        )
        assert resp.status_code == 403
    finally:
        _restore_role()


async def test_client_cannot_create_approval(client, transaction_id):
    _set_role(CLIENT_CLAIMS)
    try:
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/approvals",
            json={
                "approval_type": "PHASE_ADVANCE",
                "title": "클라이언트 승인 시도",
                "approvers": [{"email": "boss@example.com", "role": "대표"}],
            },
        )
        assert resp.status_code == 403
    finally:
        _restore_role()


# ── ANALYST: 읽기/쓰기 모두 허용 ─────────────────────────
async def test_analyst_can_read_transactions(client, transaction_id):
    _set_role(ANALYST_CLAIMS)
    try:
        resp = await client.get(f"/api/v1/transactions/{transaction_id}")
        assert resp.status_code == 200
    finally:
        _restore_role()


async def test_analyst_can_read_dashboard(client):
    _set_role(ANALYST_CLAIMS)
    try:
        resp = await client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200
    finally:
        _restore_role()


async def test_analyst_can_create_transaction(client):
    _set_role(ANALYST_CLAIMS)
    try:
        resp = await client.post(
            "/api/v1/transactions",
            json={
                "name": "분석가 생성 거래",
                "deal_type": "MA",
                "side": "SELL",
                "target_company_name": "기업",
                "client_name": "고객",
                "lead_advisor_email": "analyst@example.com",
            },
        )
        assert resp.status_code == 201
    finally:
        _restore_role()


# ── MANAGER: 읽기/쓰기 모두 허용 ─────────────────────────
async def test_manager_can_read_transactions(client, transaction_id):
    _set_role(MANAGER_CLAIMS)
    try:
        resp = await client.get(f"/api/v1/transactions/{transaction_id}")
        assert resp.status_code == 200
    finally:
        _restore_role()


async def test_manager_can_create_transaction(client):
    _set_role(MANAGER_CLAIMS)
    try:
        resp = await client.post(
            "/api/v1/transactions",
            json={
                "name": "매니저 생성 거래",
                "deal_type": "MA",
                "side": "BUY",
                "target_company_name": "대상기업",
                "client_name": "고객기업",
                "lead_advisor_email": "manager@example.com",
            },
        )
        assert resp.status_code == 201
    finally:
        _restore_role()
