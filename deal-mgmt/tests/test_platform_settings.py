"""플랫폼 전역 설정 API 통합 테스트."""

import pytest
from httpx import AsyncClient


class TestGetSettings:
    """GET /api/v1/settings — 설정 조회."""

    async def test_returns_default_settings(self, client: AsyncClient) -> None:
        """최초 조회 시 싱글턴 자동 생성 + 기본값 반환."""
        resp = await client.get("/api/v1/settings")
        assert resp.status_code == 200
        body = resp.json()
        assert body["site_name"] == "AMIC Platform"
        assert body["table_style"] == "DEFAULT"

    async def test_idempotent_creation(self, client: AsyncClient) -> None:
        """연속 조회 시 동일 레코드 반환."""
        resp1 = await client.get("/api/v1/settings")
        resp2 = await client.get("/api/v1/settings")
        assert resp1.json() == resp2.json()


class TestUpdateSettings:
    """PUT /api/v1/admin/settings — 설정 업데이트."""

    async def test_update_table_style(self, client: AsyncClient) -> None:
        """table_style 정상 변경."""
        resp = await client.put(
            "/api/v1/admin/settings",
            json={"table_style": "MODERN_GREEN"},
        )
        assert resp.status_code == 200
        assert resp.json()["table_style"] == "MODERN_GREEN"

        # 변경 후 GET으로 확인
        get_resp = await client.get("/api/v1/settings")
        assert get_resp.json()["table_style"] == "MODERN_GREEN"

    async def test_update_site_name(self, client: AsyncClient) -> None:
        """site_name 변경."""
        resp = await client.put(
            "/api/v1/admin/settings",
            json={"site_name": "My Platform"},
        )
        assert resp.status_code == 200
        assert resp.json()["site_name"] == "My Platform"

    async def test_partial_update_preserves_other_fields(self, client: AsyncClient) -> None:
        """부분 업데이트 시 다른 필드 보존."""
        await client.put(
            "/api/v1/admin/settings",
            json={"site_name": "Changed"},
        )
        resp = await client.put(
            "/api/v1/admin/settings",
            json={"table_style": "MODERN_GREEN"},
        )
        body = resp.json()
        assert body["site_name"] == "Changed"
        assert body["table_style"] == "MODERN_GREEN"

    async def test_invalid_table_style_rejected(self, client: AsyncClient) -> None:
        """유효하지 않은 table_style → 422."""
        resp = await client.put(
            "/api/v1/admin/settings",
            json={"table_style": "INVALID_THEME"},
        )
        assert resp.status_code == 422

    async def test_null_table_style_ignored(self, client: AsyncClient) -> None:
        """table_style=null 전송 시 기존 값 유지 (null 필터링)."""
        # 먼저 MODERN_GREEN으로 변경
        await client.put(
            "/api/v1/admin/settings",
            json={"table_style": "MODERN_GREEN"},
        )
        # null 전송 → 무시되어야 함
        resp = await client.put(
            "/api/v1/admin/settings",
            json={"table_style": None},
        )
        assert resp.status_code == 200
        assert resp.json()["table_style"] == "MODERN_GREEN"

    async def test_unknown_fields_ignored(self, client: AsyncClient) -> None:
        """화이트리스트 외 필드는 무시."""
        resp = await client.put(
            "/api/v1/admin/settings",
            json={"table_style": "MODERN_GREEN", "unknown_field": "hack"},
        )
        assert resp.status_code == 200
        assert resp.json()["table_style"] == "MODERN_GREEN"


class TestAuditLog:
    """설정 변경 시 감사 로그 생성 확인."""

    async def test_update_creates_audit_record(self, client: AsyncClient) -> None:
        """설정 변경 후 감사 로그 존재 확인."""
        await client.put(
            "/api/v1/admin/settings",
            json={"table_style": "MODERN_GREEN"},
        )
        resp = await client.get(
            "/api/v1/audit-logs",
            params={"entity_type": "PlatformSettings"},
        )
        assert resp.status_code == 200
        body = resp.json()
        items = body.get("items", body) if isinstance(body, dict) else body
        assert len(items) >= 1
        latest = items[0]
        assert latest["entity_type"] == "PlatformSettings"
        assert latest["action"] == "UPDATE"


class TestSettingsRbac:
    """권한 분리 테스트 (conftest ADMIN mock 기반)."""

    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/v1/settings"),
        ],
    )
    async def test_authenticated_read_allowed(self, client: AsyncClient, method: str, path: str) -> None:
        """인증된 사용자는 설정 조회 가능."""
        resp = await client.request(method, path)
        assert resp.status_code == 200
