"""Tests for VDR API endpoints (Sprint 13)."""

from fastapi.testclient import TestClient

SAMPLE_DEAL = {
    "name": "VDR Test Deal",
    "target_company_name": "VDR Test Corp",
    "deal_type": "COMPLETION_ACCOUNTS",
    "base_currency": "KRW",
    "reference_date": "2025-12-31",
    "period_start": "2024-01-01",
    "period_end": "2025-12-31",
}


def _create_deal(client: TestClient, headers: dict) -> str:
    """Create a deal and return its id."""
    resp = client.post("/api/v1/deals", json=SAMPLE_DEAL, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


class TestVdrInit:
    def test_init_vdr_folders(self, client: TestClient, admin_headers: dict) -> None:
        """POST /vdr/init creates the 6 default folders."""
        deal_id = _create_deal(client, admin_headers)

        resp = client.post(
            f"/api/v1/deals/{deal_id}/vdr/init",
            json={"include_custom": False},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        folders = resp.json()
        assert len(folders) == 6

        # Verify expected folder types
        folder_types = {f["folder_type"] for f in folders}
        expected = {
            "FINANCIAL_STATEMENTS",
            "ACCOUNTS_RECEIVABLE",
            "ACCOUNTS_PAYABLE",
            "BANK_DEBT",
            "LEASE",
            "OTHERS",
        }
        assert folder_types == expected

        # Financial Statements should be required
        fs_folder = next(
            f for f in folders if f["folder_type"] == "FINANCIAL_STATEMENTS"
        )
        assert fs_folder["is_required"] is True

    def test_init_already_initialized(
        self, client: TestClient, admin_headers: dict
    ) -> None:
        """POST /vdr/init when folders exist returns 400."""
        deal_id = _create_deal(client, admin_headers)

        # First init
        resp1 = client.post(
            f"/api/v1/deals/{deal_id}/vdr/init",
            json={"include_custom": False},
            headers=admin_headers,
        )
        assert resp1.status_code == 201

        # Second init should fail
        resp2 = client.post(
            f"/api/v1/deals/{deal_id}/vdr/init",
            json={"include_custom": False},
            headers=admin_headers,
        )
        assert resp2.status_code == 400
        assert "already initialized" in resp2.json()["detail"]


class TestVdrFolders:
    def test_list_vdr_folders(self, client: TestClient, admin_headers: dict) -> None:
        """GET /vdr/folders returns tree structure."""
        deal_id = _create_deal(client, admin_headers)

        # Initialize folders first
        client.post(
            f"/api/v1/deals/{deal_id}/vdr/init",
            json={"include_custom": False},
            headers=admin_headers,
        )

        resp = client.get(
            f"/api/v1/deals/{deal_id}/vdr/folders",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        tree = resp.json()
        assert len(tree) == 6

        # Each folder should have children array and file_count
        for node in tree:
            assert "children" in node
            assert "file_count" in node
            assert isinstance(node["children"], list)
            assert node["file_count"] == 0

    def test_create_custom_folder(
        self, client: TestClient, admin_headers: dict
    ) -> None:
        """POST /vdr/folders creates a custom folder."""
        deal_id = _create_deal(client, admin_headers)

        resp = client.post(
            f"/api/v1/deals/{deal_id}/vdr/folders",
            json={
                "name": "Tax Returns",
                "folder_type": "CUSTOM",
                "is_required": False,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Tax Returns"
        assert data["folder_type"] == "CUSTOM"
        assert data["deal_id"] == deal_id
        assert data["is_required"] is False
