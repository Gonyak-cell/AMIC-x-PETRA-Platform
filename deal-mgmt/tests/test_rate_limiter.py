"""Rate limiter 429 응답 + InMemoryRateLimiter 동작 테스트 (TQ-02)."""

from __future__ import annotations

import time

import pytest
from httpx import AsyncClient

from app.core.rate_limiter import InMemoryRateLimiter, si_rate_limiter

pytestmark = pytest.mark.anyio

_USER_EMAIL = "test@example.com"


def _fill_limiter(limiter: InMemoryRateLimiter, identifier: str, *, count: int = 10) -> None:
    """슬라이딩 윈도우에 타임스탬프를 직접 주입하여 한도를 소진한다."""
    now = time.monotonic()
    # 서로 다른 미세 간격을 두어 active 목록이 정확히 count개가 되도록 설정
    limiter._store[identifier] = [now - 0.001 * i for i in range(count)]


# ── InMemoryRateLimiter 단위 테스트 ──────────────────────


def test_rate_limiter_allows_within_limit() -> None:
    """한도 이내 요청은 예외 없이 통과."""

    limiter = InMemoryRateLimiter(max_calls=3, window_seconds=60.0)
    for _ in range(3):
        limiter.check("user")  # should not raise
    assert len(limiter._store["user"]) == 3


def test_rate_limiter_blocks_over_limit() -> None:
    """한도 초과 요청은 429 HTTPException 발생."""
    from fastapi import HTTPException

    limiter = InMemoryRateLimiter(max_calls=3, window_seconds=60.0)
    for _ in range(3):
        limiter.check("user")
    with pytest.raises(HTTPException) as exc_info:
        limiter.check("user")
    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


def test_rate_limiter_clear_resets_state() -> None:
    """clear() 호출 후 카운트가 초기화된다."""
    from fastapi import HTTPException

    limiter = InMemoryRateLimiter(max_calls=2, window_seconds=60.0)
    limiter.check("user")
    limiter.check("user")
    limiter.clear()
    # 초기화 후 다시 2번 허용되어야 한다
    limiter.check("user")
    limiter.check("user")
    with pytest.raises(HTTPException):
        limiter.check("user")


def test_rate_limiter_independent_identifiers() -> None:
    """서로 다른 식별자는 독립적으로 카운트된다."""
    limiter = InMemoryRateLimiter(max_calls=1, window_seconds=60.0)
    limiter.check("user-A")
    limiter.check("user-B")  # 다른 식별자이므로 통과


def test_rate_limiter_retry_after_header() -> None:
    """429 응답에 Retry-After 헤더가 양수 정수로 포함된다."""
    from fastapi import HTTPException

    limiter = InMemoryRateLimiter(max_calls=1, window_seconds=60.0)
    limiter.check("user")
    with pytest.raises(HTTPException) as exc_info:
        limiter.check("user")
    retry_after = int(exc_info.value.headers["Retry-After"])
    assert retry_after > 0
    assert retry_after <= 61  # window_seconds + 1


# ── 엔드포인트 통합 테스트 ─────────────────────────────


async def test_map_si_429_rate_limit(client: AsyncClient) -> None:
    """POST /si-mapping/map — rate limit 초과 시 429 응답 + Retry-After 헤더."""
    _fill_limiter(si_rate_limiter, _USER_EMAIL, count=10)
    resp = await client.post(
        "/api/v1/si-mapping/map",
        json={"ksic_codes": ["C10"], "top_n": 5},
    )
    assert resp.status_code == 429
    body = resp.json()
    assert "요청이 너무 많습니다" in body["detail"]
    assert "Retry-After" in resp.headers
    assert int(resp.headers["Retry-After"]) > 0


async def test_map_vc_429_rate_limit(client: AsyncClient) -> None:
    """GET /si-mapping/vc-map — rate limit 초과 시 429 응답."""
    _fill_limiter(si_rate_limiter, _USER_EMAIL, count=10)
    resp = await client.get(
        "/api/v1/si-mapping/vc-map",
        params={"industry": "식품"},
    )
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


async def test_map_si_200_after_rate_limit_reset(client: AsyncClient) -> None:
    """rate limit clear 후 재요청은 정상 처리된다 (429 아님)."""
    _fill_limiter(si_rate_limiter, _USER_EMAIL, count=10)
    # 첫 요청 → 429
    r1 = await client.post(
        "/api/v1/si-mapping/map",
        json={"ksic_codes": ["C10"], "top_n": 5},
    )
    assert r1.status_code == 429

    # 리미터 초기화 (conftest setup_database fixture가 테스트 간에 자동 초기화하지만,
    # 여기서는 동일 테스트 내 직접 초기화)
    si_rate_limiter.clear()

    r2 = await client.post(
        "/api/v1/si-mapping/map",
        json={"ksic_codes": ["C10"], "top_n": 5},
    )
    assert r2.status_code == 200
