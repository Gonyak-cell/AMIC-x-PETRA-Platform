"""헬스체크 엔드포인트 테스트 (T-I06).

> 마지막 수정: 2026-02-10 16:29:08

/health, /ready 엔드포인트의 응답을 검증한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import __version__, create_app


@pytest.fixture
async def client() -> AsyncClient:
    """테스트 클라이언트."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


class TestHealthEndpoint:
    """GET /health 테스트."""

    async def test_returns_200(self, client: AsyncClient) -> None:
        """200 상태 코드를 반환한다."""
        resp = await client.get("/health")
        assert resp.status_code == 200

    @patch("src.api.routes.health._check_db", new_callable=AsyncMock, return_value=True)
    async def test_returns_ok_status(
        self,
        _mock_db: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """status가 'ok'이다."""
        resp = await client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"

    async def test_includes_version(self, client: AsyncClient) -> None:
        """응답에 version 필드가 포함된다."""
        resp = await client.get("/health")
        data = resp.json()
        assert data["version"] == __version__


class TestReadyEndpoint:
    """GET /ready 테스트."""

    @patch("src.api.routes.health._check_db", new_callable=AsyncMock, return_value=True)
    @patch(
        "src.api.routes.health._check_redis", new_callable=AsyncMock, return_value=True
    )
    async def test_ready_when_all_up(
        self, mock_redis: AsyncMock, mock_db: AsyncMock, client: AsyncClient
    ) -> None:
        """DB + Redis 정상일 때 200을 반환한다."""
        resp = await client.get("/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["database"] is True
        assert data["redis"] is True

    @patch(
        "src.api.routes.health._check_db", new_callable=AsyncMock, return_value=False
    )
    @patch(
        "src.api.routes.health._check_redis", new_callable=AsyncMock, return_value=True
    )
    async def test_not_ready_when_db_down(
        self, mock_redis: AsyncMock, mock_db: AsyncMock, client: AsyncClient
    ) -> None:
        """DB 연결 실패 시 503을 반환한다."""
        resp = await client.get("/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["database"] is False

    @patch("src.api.routes.health._check_db", new_callable=AsyncMock, return_value=True)
    @patch(
        "src.api.routes.health._check_redis", new_callable=AsyncMock, return_value=False
    )
    async def test_not_ready_when_redis_down(
        self, mock_redis: AsyncMock, mock_db: AsyncMock, client: AsyncClient
    ) -> None:
        """Redis 연결 실패 시 503을 반환한다."""
        resp = await client.get("/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["redis"] is False

    @patch(
        "src.api.routes.health._check_db", new_callable=AsyncMock, return_value=False
    )
    @patch(
        "src.api.routes.health._check_redis", new_callable=AsyncMock, return_value=False
    )
    async def test_not_ready_when_all_down(
        self, mock_redis: AsyncMock, mock_db: AsyncMock, client: AsyncClient
    ) -> None:
        """DB + Redis 모두 실패 시 503을 반환한다."""
        resp = await client.get("/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["database"] is False
        assert data["redis"] is False
