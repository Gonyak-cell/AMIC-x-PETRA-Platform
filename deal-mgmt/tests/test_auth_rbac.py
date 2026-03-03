"""역할 기반 접근 제어(RBAC) 403 테스트 (TQ-05).

SI/FI/VC 매핑 엔드포인트의 역할별 접근 제어 검증:
- _READ_ACCESS = require_role("ADMIN", "MANAGER", "ANALYST")
- _WRITE_ACCESS = require_role("ADMIN", "MANAGER")
"""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient

from app.core.security import JWTClaims, get_jwt_claims
from app.main import app

pytestmark = pytest.mark.anyio


# ── 역할 컨텍스트 매니저 ──────────────────────────────────


@contextlib.asynccontextmanager
async def _with_role(role: str) -> AsyncGenerator[None, None]:
    """테스트 범위 내에서만 JWT 역할을 일시적으로 교체한다."""
    original = app.dependency_overrides.get(get_jwt_claims)

    claims = JWTClaims(
        user_id=f"{role.lower()}-test-id",
        email=f"{role.lower()}@example.com",
        role=role,
    )

    async def _getter() -> JWTClaims:
        return claims

    app.dependency_overrides[get_jwt_claims] = _getter
    try:
        yield
    finally:
        if original is not None:
            app.dependency_overrides[get_jwt_claims] = original
        else:
            app.dependency_overrides.pop(get_jwt_claims, None)


# ── SI 매핑 — _READ_ACCESS 체크 (CLIENT → 403) ───────────


async def test_si_stats_403_client_role(client: AsyncClient) -> None:
    """GET /si-mapping/stats — CLIENT 역할은 403."""
    async with _with_role("CLIENT"):
        resp = await client.get("/api/v1/si-mapping/stats")
    assert resp.status_code == 403


async def test_si_ksic_search_403_client_role(client: AsyncClient) -> None:
    """GET /si-mapping/ksic/search — CLIENT 역할은 403."""
    async with _with_role("CLIENT"):
        resp = await client.get("/api/v1/si-mapping/ksic/search", params={"q": "식품"})
    assert resp.status_code == 403


async def test_si_map_403_client_role(client: AsyncClient) -> None:
    """POST /si-mapping/map — CLIENT 역할은 403."""
    async with _with_role("CLIENT"):
        resp = await client.post(
            "/api/v1/si-mapping/map",
            json={"ksic_codes": ["C10"], "top_n": 5},
        )
    assert resp.status_code == 403


async def test_si_deep_dive_403_client_role(client: AsyncClient) -> None:
    """GET /si-mapping/companies/{id}/deep-dive — CLIENT 역할은 403."""
    fake_id = str(uuid.uuid4())
    async with _with_role("CLIENT"):
        resp = await client.get(f"/api/v1/si-mapping/companies/{fake_id}/deep-dive")
    assert resp.status_code == 403


async def test_vc_stats_403_client_role(client: AsyncClient) -> None:
    """GET /si-mapping/vc-stats — CLIENT 역할은 403."""
    async with _with_role("CLIENT"):
        resp = await client.get("/api/v1/si-mapping/vc-stats")
    assert resp.status_code == 403


async def test_vc_map_403_client_role(client: AsyncClient) -> None:
    """GET /si-mapping/vc-map — CLIENT 역할은 403."""
    async with _with_role("CLIENT"):
        resp = await client.get("/api/v1/si-mapping/vc-map", params={"industry": "식품"})
    assert resp.status_code == 403


# ── SI 매핑 — _WRITE_ACCESS 체크 (ANALYST → 403) ────────


async def test_add_buyers_403_analyst_role(client: AsyncClient) -> None:
    """POST /transactions/{id}/si-mapping/add-buyers — ANALYST는 쓰기 금지 → 403.

    _WRITE_ACCESS 체크가 DB 조회보다 먼저 실행되므로 트랜잭션이 없어도 403 반환.
    """
    fake_txn_id = str(uuid.uuid4())
    async with _with_role("ANALYST"):
        resp = await client.post(
            f"/api/v1/transactions/{fake_txn_id}/si-mapping/add-buyers",
            json={"si_company_ids": []},
        )
    assert resp.status_code == 403


# ── PEF/FI 매핑 — _READ_ACCESS 체크 (CLIENT → 403) ──────


async def test_pef_list_403_client_role(client: AsyncClient) -> None:
    """GET /pef-registry — CLIENT 역할은 403."""
    async with _with_role("CLIENT"):
        resp = await client.get("/api/v1/pef-registry")
    assert resp.status_code == 403


async def test_fi_recommendations_403_client_role(client: AsyncClient) -> None:
    """GET /transactions/{id}/fi-recommendations — CLIENT 역할은 403.

    _READ_ACCESS 체크가 DB 조회보다 먼저 실행되므로 트랜잭션이 없어도 403 반환.
    """
    fake_txn_id = str(uuid.uuid4())
    async with _with_role("CLIENT"):
        resp = await client.get(
            f"/api/v1/transactions/{fake_txn_id}/fi-recommendations",
        )
    assert resp.status_code == 403


# ── 올바른 역할 접근 허용 확인 ───────────────────────────


async def test_si_stats_200_analyst_role(client: AsyncClient) -> None:
    """GET /si-mapping/stats — ANALYST 역할은 200 접근 허용."""
    async with _with_role("ANALYST"):
        resp = await client.get("/api/v1/si-mapping/stats")
    # 데이터 없이도 200 응답 (초기화된 DB)
    assert resp.status_code == 200


async def test_pef_list_200_manager_role(client: AsyncClient) -> None:
    """GET /pef-registry — MANAGER 역할은 200 접근 허용."""
    async with _with_role("MANAGER"):
        resp = await client.get("/api/v1/pef-registry")
    assert resp.status_code == 200
