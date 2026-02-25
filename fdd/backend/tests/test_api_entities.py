"""Entity API 테스트 — Sprint 16.

Entity CRUD 엔드포인트 통합 테스트.
"""

from fastapi.testclient import TestClient

SAMPLE_DEAL = {
    "name": "Entity Test Deal",
    "target_company_name": "Entity Test Corp",
    "deal_type": "COMPLETION_ACCOUNTS",
    "base_currency": "KRW",
    "reference_date": "2025-12-31",
    "period_start": "2025-01-01",
    "period_end": "2025-12-31",
}


class TestEntityAPI:
    """Entity CRUD API 테스트."""

    def _create_deal(self, client: TestClient, headers: dict) -> str:
        resp = client.post("/api/v1/deals", json=SAMPLE_DEAL, headers=headers)
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_create_entity_success(self, client: TestClient, auth_headers):
        """엔티티 생성 성공 → 201."""
        deal_id = self._create_deal(client, auth_headers)
        payload = {
            "name": "Target Company",
            "code": "TARGET",
            "entity_type": "TARGET",
            "functional_currency": "KRW",
            "ownership_pct": "100.0000",
        }

        resp = client.post(
            f"/api/v1/deals/{deal_id}/entities/",
            json=payload,
            headers=auth_headers,
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "TARGET"
        assert data["entity_type"] == "TARGET"
        assert data["functional_currency"] == "KRW"
        assert data["is_active"] is True

    def test_create_entity_duplicate_code_409(self, client: TestClient, auth_headers):
        """중복 code → 409."""
        deal_id = self._create_deal(client, auth_headers)
        payload = {"name": "Entity A", "code": "SAME", "entity_type": "TARGET"}

        resp1 = client.post(
            f"/api/v1/deals/{deal_id}/entities/",
            json=payload,
            headers=auth_headers,
        )
        assert resp1.status_code == 201

        resp2 = client.post(
            f"/api/v1/deals/{deal_id}/entities/",
            json=payload,
            headers=auth_headers,
        )
        assert resp2.status_code == 409

    def test_create_entity_deal_not_found(self, client: TestClient, auth_headers):
        """존재하지 않는 딜 → 404."""
        import uuid

        fake_deal_id = str(uuid.uuid4())
        payload = {"name": "Entity", "code": "E1", "entity_type": "TARGET"}

        resp = client.post(
            f"/api/v1/deals/{fake_deal_id}/entities/",
            json=payload,
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_list_entities_empty(self, client: TestClient, auth_headers):
        """빈 목록 조회."""
        deal_id = self._create_deal(client, auth_headers)

        resp = client.get(
            f"/api/v1/deals/{deal_id}/entities/",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_entities_multiple(self, client: TestClient, auth_headers):
        """복수 엔티티 목록."""
        deal_id = self._create_deal(client, auth_headers)

        for code in ["TARGET", "SUB1"]:
            client.post(
                f"/api/v1/deals/{deal_id}/entities/",
                json={"name": f"Entity {code}", "code": code, "entity_type": "TARGET"},
                headers=auth_headers,
            )

        resp = client.get(
            f"/api/v1/deals/{deal_id}/entities/",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_entity_success(self, client: TestClient, auth_headers):
        """단건 조회 성공."""
        deal_id = self._create_deal(client, auth_headers)
        create_resp = client.post(
            f"/api/v1/deals/{deal_id}/entities/",
            json={"name": "Target", "code": "TARGET", "entity_type": "TARGET"},
            headers=auth_headers,
        )
        entity_id = create_resp.json()["id"]

        resp = client.get(
            f"/api/v1/deals/{deal_id}/entities/{entity_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == "TARGET"

    def test_get_entity_not_found(self, client: TestClient, auth_headers):
        """존재하지 않는 엔티티 → 404."""
        import uuid

        deal_id = self._create_deal(client, auth_headers)
        fake_id = str(uuid.uuid4())

        resp = client.get(
            f"/api/v1/deals/{deal_id}/entities/{fake_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_update_entity(self, client: TestClient, auth_headers):
        """엔티티 수정 (partial)."""
        deal_id = self._create_deal(client, auth_headers)
        create_resp = client.post(
            f"/api/v1/deals/{deal_id}/entities/",
            json={
                "name": "Original",
                "code": "E1",
                "entity_type": "TARGET",
                "ownership_pct": "100.0000",
            },
            headers=auth_headers,
        )
        entity_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/v1/deals/{deal_id}/entities/{entity_id}",
            json={"name": "Updated Name", "ownership_pct": "80.0000"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Name"
        assert data["ownership_pct"] == "80.0000"

    def test_delete_entity_soft(self, client: TestClient, auth_headers):
        """소프트 삭제 → 204, 목록에서 제외."""
        deal_id = self._create_deal(client, auth_headers)
        create_resp = client.post(
            f"/api/v1/deals/{deal_id}/entities/",
            json={"name": "ToDelete", "code": "DEL", "entity_type": "TARGET"},
            headers=auth_headers,
        )
        entity_id = create_resp.json()["id"]

        del_resp = client.delete(
            f"/api/v1/deals/{deal_id}/entities/{entity_id}",
            headers=auth_headers,
        )
        assert del_resp.status_code == 204

        # 목록에서 제외 (is_active=False)
        list_resp = client.get(
            f"/api/v1/deals/{deal_id}/entities/",
            headers=auth_headers,
        )
        assert len(list_resp.json()) == 0
