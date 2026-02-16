"""Exchange Rate API 테스트 — Sprint 16.

환율 CRUD + 벌크 + 필터링 엔드포인트 통합 테스트.
"""

from decimal import Decimal

from fastapi.testclient import TestClient

D = Decimal

SAMPLE_DEAL = {
    "name": "FX Rate Test Deal",
    "deal_type": "COMPLETION_ACCOUNTS",
    "base_currency": "KRW",
    "reference_date": "2025-12-31",
    "period_start": "2025-01-01",
    "period_end": "2025-12-31",
}


class TestExchangeRateAPI:
    """Exchange Rate CRUD API 테스트."""

    def _create_deal(self, client: TestClient, headers: dict) -> str:
        resp = client.post("/api/v1/deals", json=SAMPLE_DEAL, headers=headers)
        assert resp.status_code == 201
        return resp.json()["id"]

    def _rate_payload(
        self,
        from_currency: str = "USD",
        to_currency: str = "KRW",
        rate: str = "1300.0000",
        rate_type: str = "CLOSING",
        effective_date: str = "2025-12-31",
    ) -> dict:
        return {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": rate,
            "rate_type": rate_type,
            "effective_date": effective_date,
        }

    def test_create_rate_success(self, client: TestClient, auth_headers):
        """환율 생성 성공 → 201."""
        deal_id = self._create_deal(client, auth_headers)

        resp = client.post(
            f"/api/v1/deals/{deal_id}/exchange-rates/",
            json=self._rate_payload(),
            headers=auth_headers,
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["from_currency"] == "USD"
        assert data["to_currency"] == "KRW"
        assert D(data["rate"]) == D("1300.0000")
        assert data["rate_type"] == "CLOSING"

    def test_create_rate_deal_not_found(self, client: TestClient, auth_headers):
        """존재하지 않는 딜 → 404."""
        import uuid

        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"/api/v1/deals/{fake_id}/exchange-rates/",
            json=self._rate_payload(),
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_create_rate_duplicate_409(self, client: TestClient, auth_headers):
        """동일 조합 중복 → 409."""
        deal_id = self._create_deal(client, auth_headers)
        payload = self._rate_payload()

        resp1 = client.post(
            f"/api/v1/deals/{deal_id}/exchange-rates/",
            json=payload,
            headers=auth_headers,
        )
        assert resp1.status_code == 201

        resp2 = client.post(
            f"/api/v1/deals/{deal_id}/exchange-rates/",
            json=payload,
            headers=auth_headers,
        )
        assert resp2.status_code == 409

    def test_bulk_create_success(self, client: TestClient, auth_headers):
        """벌크 환율 등록 성공."""
        deal_id = self._create_deal(client, auth_headers)
        payload = {
            "rates": [
                self._rate_payload("USD", "KRW", "1300.0000", "CLOSING", "2025-12-31"),
                self._rate_payload("EUR", "KRW", "1400.0000", "CLOSING", "2025-12-31"),
                self._rate_payload("USD", "KRW", "1250.0000", "AVERAGE", "2025-06-30"),
            ]
        }

        resp = client.post(
            f"/api/v1/deals/{deal_id}/exchange-rates/bulk",
            json=payload,
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert len(resp.json()) == 3

    def test_list_rates_all(self, client: TestClient, auth_headers):
        """전체 목록 조회."""
        deal_id = self._create_deal(client, auth_headers)
        client.post(
            f"/api/v1/deals/{deal_id}/exchange-rates/",
            json=self._rate_payload(),
            headers=auth_headers,
        )

        resp = client.get(
            f"/api/v1/deals/{deal_id}/exchange-rates/",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_rates_filter_by_currency(self, client: TestClient, auth_headers):
        """from_currency 필터."""
        deal_id = self._create_deal(client, auth_headers)
        payload = {
            "rates": [
                self._rate_payload("USD", "KRW", "1300.0000"),
                self._rate_payload("EUR", "KRW", "1400.0000"),
            ]
        }
        client.post(
            f"/api/v1/deals/{deal_id}/exchange-rates/bulk",
            json=payload,
            headers=auth_headers,
        )

        resp = client.get(
            f"/api/v1/deals/{deal_id}/exchange-rates/?from_currency=EUR",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["from_currency"] == "EUR"

    def test_list_rates_filter_by_type(self, client: TestClient, auth_headers):
        """rate_type 필터."""
        deal_id = self._create_deal(client, auth_headers)
        payload = {
            "rates": [
                self._rate_payload("USD", "KRW", "1300.0000", "CLOSING", "2025-12-31"),
                self._rate_payload("USD", "KRW", "1250.0000", "AVERAGE", "2025-06-30"),
            ]
        }
        client.post(
            f"/api/v1/deals/{deal_id}/exchange-rates/bulk",
            json=payload,
            headers=auth_headers,
        )

        resp = client.get(
            f"/api/v1/deals/{deal_id}/exchange-rates/?rate_type=AVERAGE",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["rate_type"] == "AVERAGE"

    def test_get_rate_success(self, client: TestClient, auth_headers):
        """단건 조회."""
        deal_id = self._create_deal(client, auth_headers)
        create_resp = client.post(
            f"/api/v1/deals/{deal_id}/exchange-rates/",
            json=self._rate_payload(),
            headers=auth_headers,
        )
        rate_id = create_resp.json()["id"]

        resp = client.get(
            f"/api/v1/deals/{deal_id}/exchange-rates/{rate_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["from_currency"] == "USD"

    def test_get_rate_not_found(self, client: TestClient, auth_headers):
        """존재하지 않는 환율 → 404."""
        import uuid

        deal_id = self._create_deal(client, auth_headers)
        fake_id = str(uuid.uuid4())

        resp = client.get(
            f"/api/v1/deals/{deal_id}/exchange-rates/{fake_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_update_rate(self, client: TestClient, auth_headers):
        """환율 수정."""
        deal_id = self._create_deal(client, auth_headers)
        create_resp = client.post(
            f"/api/v1/deals/{deal_id}/exchange-rates/",
            json=self._rate_payload("USD", "KRW", "1300.0000"),
            headers=auth_headers,
        )
        rate_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/v1/deals/{deal_id}/exchange-rates/{rate_id}",
            json={"rate": "1350.0000"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert D(resp.json()["rate"]) == D("1350.0000")

    def test_delete_rate(self, client: TestClient, auth_headers):
        """환율 삭제 (hard delete) → 204."""
        deal_id = self._create_deal(client, auth_headers)
        create_resp = client.post(
            f"/api/v1/deals/{deal_id}/exchange-rates/",
            json=self._rate_payload(),
            headers=auth_headers,
        )
        rate_id = create_resp.json()["id"]

        del_resp = client.delete(
            f"/api/v1/deals/{deal_id}/exchange-rates/{rate_id}",
            headers=auth_headers,
        )
        assert del_resp.status_code == 204

        # 삭제 확인
        get_resp = client.get(
            f"/api/v1/deals/{deal_id}/exchange-rates/{rate_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404
