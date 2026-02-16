"""Chart API 엔드포인트 테스트."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestEBITDABridgeEndpoint:
    """POST /api/v1/charts/ebitda-bridge 테스트."""

    def test_ebitda_bridge_success(self):
        """정상적인 EBITDA Bridge 요청."""
        response = client.post(
            "/api/v1/charts/ebitda-bridge",
            json={
                "categories": ["Reported EBITDA", "일회성 조정", "Adjusted EBITDA"],
                "values": ["1000000000", "200000000", None],
                "title": "FY2025 EBITDA Bridge",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        # PNG 시그니처 확인
        assert response.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_ebitda_bridge_with_negative_values(self):
        """음수 조정 금액 포함."""
        response = client.post(
            "/api/v1/charts/ebitda-bridge",
            json={
                "categories": ["Reported", "Add-back", "Deduction", "Adjusted"],
                "values": ["1000", "200", "-50", None],
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    def test_ebitda_bridge_length_mismatch(self):
        """categories와 values 길이 불일치."""
        response = client.post(
            "/api/v1/charts/ebitda-bridge",
            json={
                "categories": ["A", "B", "C"],
                "values": ["100", "200"],
            },
        )

        assert response.status_code == 400
        assert "개수가 일치" in response.json()["detail"]

    def test_ebitda_bridge_invalid_value(self):
        """유효하지 않은 숫자 값."""
        response = client.post(
            "/api/v1/charts/ebitda-bridge",
            json={
                "categories": ["A", "B"],
                "values": ["not-a-number", "200"],
            },
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_ebitda_bridge_too_few_categories(self):
        """최소 2개 미만 항목."""
        response = client.post(
            "/api/v1/charts/ebitda-bridge",
            json={
                "categories": ["Only One"],
                "values": ["100"],
            },
        )

        assert response.status_code == 422  # Pydantic min_length validation


class TestNWCBridgeEndpoint:
    """POST /api/v1/charts/nwc-bridge 테스트."""

    def test_nwc_bridge_success(self):
        """정상적인 NWC Bridge 요청."""
        response = client.post(
            "/api/v1/charts/nwc-bridge",
            json={
                "categories": ["매출채권", "재고자산", "매입채무", "Net WC"],
                "values": ["500", "300", "-200", None],
                "title": "운전자본 구성",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"


class TestNetDebtBridgeEndpoint:
    """POST /api/v1/charts/net-debt-bridge 테스트."""

    def test_net_debt_bridge_success(self):
        """정상적인 Net Debt Bridge 요청."""
        response = client.post(
            "/api/v1/charts/net-debt-bridge",
            json={
                "categories": ["장기차입금", "단기차입금", "현금", "Net Debt"],
                "values": ["1000", "500", "-300", None],
                "title": "순차입금 구성",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"


class TestGenericWaterfallEndpoint:
    """POST /api/v1/charts/waterfall 테스트."""

    def test_generic_waterfall_success(self):
        """정상적인 범용 워터폴 요청."""
        response = client.post(
            "/api/v1/charts/waterfall",
            json={
                "categories": ["시작", "증가", "감소", "종료"],
                "values": ["1000", "300", "-100", None],
                "title": "변동 분석",
                "y_axis_title": "금액",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    def test_generic_waterfall_with_measures(self):
        """커스텀 measures 지정."""
        response = client.post(
            "/api/v1/charts/waterfall",
            json={
                "categories": ["Q1", "Q2", "Q3", "Q4", "Total"],
                "values": ["100", "120", "90", "150", None],
                "measures": ["absolute", "absolute", "absolute", "absolute", "total"],
            },
        )

        assert response.status_code == 200

    def test_generic_waterfall_measures_mismatch(self):
        """measures 길이 불일치."""
        response = client.post(
            "/api/v1/charts/waterfall",
            json={
                "categories": ["A", "B", "C"],
                "values": ["100", "50", None],
                "measures": ["absolute", "relative"],  # 2개 (3개 필요)
            },
        )

        assert response.status_code == 400
        assert "개수가 일치" in response.json()["detail"]


class TestChartContentDisposition:
    """Content-Disposition 헤더 테스트."""

    def test_ebitda_bridge_filename(self):
        """EBITDA Bridge 파일명."""
        response = client.post(
            "/api/v1/charts/ebitda-bridge",
            json={
                "categories": ["A", "B"],
                "values": ["100", None],
            },
        )

        assert "ebitda_bridge.png" in response.headers.get("content-disposition", "")

    def test_nwc_bridge_filename(self):
        """NWC Bridge 파일명."""
        response = client.post(
            "/api/v1/charts/nwc-bridge",
            json={
                "categories": ["A", "B"],
                "values": ["100", None],
            },
        )

        assert "nwc_bridge.png" in response.headers.get("content-disposition", "")

    def test_net_debt_bridge_filename(self):
        """Net Debt Bridge 파일명."""
        response = client.post(
            "/api/v1/charts/net-debt-bridge",
            json={
                "categories": ["A", "B"],
                "values": ["100", None],
            },
        )

        assert "net_debt_bridge.png" in response.headers.get("content-disposition", "")

    def test_generic_waterfall_filename(self):
        """범용 워터폴 파일명."""
        response = client.post(
            "/api/v1/charts/waterfall",
            json={
                "categories": ["A", "B"],
                "values": ["100", None],
            },
        )

        assert "waterfall.png" in response.headers.get("content-disposition", "")
