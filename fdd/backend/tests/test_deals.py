"""Tests for Deal API endpoints (FDD-101, FDD-102)."""

from fastapi.testclient import TestClient

SAMPLE_DEAL = {
    "name": "Project Alpha",
    "target_company_name": "Alpha Corp",
    "deal_type": "COMPLETION_ACCOUNTS",
    "base_currency": "KRW",
    "reference_date": "2025-12-31",
    "period_start": "2024-01-01",
    "period_end": "2025-12-31",
}

SAMPLE_DEFINITION = {
    "definition_data": {
        "cash": {"include": ["1110", "1120"], "exclude": ["1130"]},
        "debt": {"include": ["2210", "2220"], "exclude": []},
        "debt_like": [],
        "cash_like": [],
        "nwc": {"include": ["1200", "2100"], "exclude": ["1110"]},
        "target_nwc": {"method": "6M_AVG", "value": None},
        "lease_ifrs16": {"include_in_debt": False},
    }
}


class TestDealCRUD:
    def test_create_deal(self, client: TestClient):
        resp = client.post("/api/v1/deals", json=SAMPLE_DEAL)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Project Alpha"
        assert data["deal_type"] == "COMPLETION_ACCOUNTS"
        assert data["status"] == "DRAFT"
        assert "id" in data

    def test_list_deals(self, client: TestClient):
        client.post("/api/v1/deals", json=SAMPLE_DEAL)
        client.post("/api/v1/deals", json={**SAMPLE_DEAL, "name": "Project Beta"})

        resp = client.get("/api/v1/deals")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2

    def test_get_deal(self, client: TestClient):
        create_resp = client.post("/api/v1/deals", json=SAMPLE_DEAL)
        deal_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/deals/{deal_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Project Alpha"

    def test_get_deal_not_found(self, client: TestClient):
        resp = client.get("/api/v1/deals/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_update_deal(self, client: TestClient):
        create_resp = client.post("/api/v1/deals", json=SAMPLE_DEAL)
        deal_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/v1/deals/{deal_id}",
            json={"name": "Project Alpha v2", "status": "ACTIVE"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Project Alpha v2"
        assert resp.json()["status"] == "ACTIVE"


class TestDealDefinition:
    def _create_deal(self, client: TestClient) -> str:
        resp = client.post("/api/v1/deals", json=SAMPLE_DEAL)
        return resp.json()["id"]

    def test_create_definition(self, client: TestClient):
        deal_id = self._create_deal(client)
        resp = client.post(
            f"/api/v1/deals/{deal_id}/definitions", json=SAMPLE_DEFINITION
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["version"] == 1
        assert data["status"] == "DRAFT"
        assert len(data["hash"]) == 64  # SHA-256

    def test_definition_versioning(self, client: TestClient):
        deal_id = self._create_deal(client)
        client.post(f"/api/v1/deals/{deal_id}/definitions", json=SAMPLE_DEFINITION)
        resp = client.post(
            f"/api/v1/deals/{deal_id}/definitions", json=SAMPLE_DEFINITION
        )
        assert resp.json()["version"] == 2

    def test_same_definition_same_hash(self, client: TestClient):
        """FDD-101 AC: 동일 정의 → 동일 해시."""
        deal_id = self._create_deal(client)
        resp1 = client.post(
            f"/api/v1/deals/{deal_id}/definitions", json=SAMPLE_DEFINITION
        )
        resp2 = client.post(
            f"/api/v1/deals/{deal_id}/definitions", json=SAMPLE_DEFINITION
        )
        assert resp1.json()["hash"] == resp2.json()["hash"]

    def test_different_definition_different_hash(self, client: TestClient):
        deal_id = self._create_deal(client)
        resp1 = client.post(
            f"/api/v1/deals/{deal_id}/definitions", json=SAMPLE_DEFINITION
        )
        modified = {
            "definition_data": {
                **SAMPLE_DEFINITION["definition_data"],
                "lease_ifrs16": {"include_in_debt": True},
            }
        }
        resp2 = client.post(f"/api/v1/deals/{deal_id}/definitions", json=modified)
        assert resp1.json()["hash"] != resp2.json()["hash"]

    def test_approve_definition(self, client: TestClient):
        deal_id = self._create_deal(client)
        client.post(f"/api/v1/deals/{deal_id}/definitions", json=SAMPLE_DEFINITION)

        resp = client.put(
            f"/api/v1/deals/{deal_id}/definitions/1/approve",
            json={"approved_by": "reviewer1"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "APPROVED"
        assert resp.json()["approved_by"] == "reviewer1"

    def test_list_definitions(self, client: TestClient):
        deal_id = self._create_deal(client)
        client.post(f"/api/v1/deals/{deal_id}/definitions", json=SAMPLE_DEFINITION)
        client.post(f"/api/v1/deals/{deal_id}/definitions", json=SAMPLE_DEFINITION)

        resp = client.get(f"/api/v1/deals/{deal_id}/definitions")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestDealSnapshot:
    def _create_deal_with_definition(self, client: TestClient) -> tuple[str, str]:
        deal_resp = client.post("/api/v1/deals", json=SAMPLE_DEAL)
        deal_id = deal_resp.json()["id"]
        def_resp = client.post(
            f"/api/v1/deals/{deal_id}/definitions", json=SAMPLE_DEFINITION
        )
        return deal_id, def_resp.json()["id"]

    def test_create_snapshot(self, client: TestClient):
        deal_id, def_id = self._create_deal_with_definition(client)
        resp = client.post(
            f"/api/v1/deals/{deal_id}/snapshots",
            json={"definition_version_id": def_id},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "RUNNING"
        assert data["engine_version"] == "0.1.0"
        assert len(data["input_hash"]) == 64

    def test_list_snapshots(self, client: TestClient):
        deal_id, def_id = self._create_deal_with_definition(client)
        client.post(
            f"/api/v1/deals/{deal_id}/snapshots",
            json={"definition_version_id": def_id},
        )

        resp = client.get(f"/api/v1/deals/{deal_id}/snapshots")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
