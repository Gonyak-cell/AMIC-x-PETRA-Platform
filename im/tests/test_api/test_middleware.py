"""미들웨어 테스트 (T-I20).

> 마지막 수정: 2026-02-10 23:30:00

Rate limit, CORS, Request logging 미들웨어를 검증한다.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import create_app


@pytest.fixture
def middleware_app():
    """미들웨어가 등록된 FastAPI 앱."""
    with patch("src.api.config.get_config") as mock_config:
        cfg = mock_config.return_value
        cfg.rate_limit_per_minute = 5
        cfg.redis_url = "memory://"
        cfg.allowed_origins = ["http://localhost:3000"]
        cfg.redis_result_backend = "memory://"
        cfg.database_url = "postgresql+asyncpg://test:test@localhost:5434/imgen_test"
        cfg.db_pool_size = 5
        cfg.db_max_overflow = 10
        cfg.db_echo = False
        cfg.jwt_secret_key = "test-secret"
        cfg.jwt_algorithm = "HS256"
        cfg.jwt_private_key_path = ""
        cfg.jwt_public_key_path = ""
        cfg.jwt_access_token_expire_minutes = 30
        cfg.jwt_refresh_token_expire_days = 7
        cfg.celery_task_soft_time_limit = 300
        cfg.celery_task_hard_time_limit = 600
        cfg.debug = True
        cfg.log_level = "DEBUG"
        cfg.output_dir = "output/"
        yield create_app()


@pytest.fixture
async def middleware_client(middleware_app) -> AsyncClient:
    """미들웨어 테스트용 AsyncClient."""
    async with AsyncClient(
        transport=ASGITransport(app=middleware_app),
        base_url="http://test",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


class TestCORSMiddleware:
    """CORS 미들웨어 테스트."""

    @pytest.mark.asyncio
    async def test_cors_allowed_origin(self, middleware_client: AsyncClient) -> None:
        """허용된 오리진의 CORS 헤더 반환."""
        response = await middleware_client.get(
            "/health",
            headers={"origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )

    @pytest.mark.asyncio
    async def test_cors_disallowed_origin(self, middleware_client: AsyncClient) -> None:
        """허용되지 않은 오리진은 CORS 헤더 미반환."""
        response = await middleware_client.get(
            "/health",
            headers={"origin": "http://evil.com"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers


# ---------------------------------------------------------------------------
# Request Logging
# ---------------------------------------------------------------------------


class TestRequestLoggingMiddleware:
    """Request logging 미들웨어 테스트."""

    @pytest.mark.asyncio
    async def test_logging_records_request(
        self, middleware_client: AsyncClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """요청 로그에 method/path/status/duration 기록."""
        with caplog.at_level(logging.INFO, logger="src.api.core.log_middleware"):
            await middleware_client.get("/health")
        messages = [r.getMessage() for r in caplog.records]
        assert any("GET" in m and "/health" in m for m in messages)

    @pytest.mark.asyncio
    async def test_logging_masks_authorization(
        self, middleware_client: AsyncClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Authorization 헤더가 로그에 노출되지 않음."""
        with caplog.at_level(logging.INFO, logger="src.api.core.log_middleware"):
            await middleware_client.get(
                "/health",
                headers={"authorization": "Bearer secret-token-123"},
            )
        log_messages = " ".join(r.getMessage() for r in caplog.records)
        assert "secret-token-123" not in log_messages

    @pytest.mark.asyncio
    async def test_logging_records_duration(
        self, middleware_client: AsyncClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """duration(ms)이 로그에 포함."""
        with caplog.at_level(logging.INFO, logger="src.api.core.log_middleware"):
            await middleware_client.get("/health")
        assert any("ms" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# Rate Limit (기본 동작만 검증 — Redis 불필요)
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    """Rate limit 미들웨어 테스트."""

    @pytest.mark.asyncio
    async def test_rate_limit_within_limit(
        self, middleware_client: AsyncClient
    ) -> None:
        """제한 내 요청은 200 반환."""
        response = await middleware_client.get("/health")
        assert response.status_code == 200
