"""DartAPIClient 테스트."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.data_ingestor.dart.client import DartAPIClient
from src.data_ingestor.dart.endpoints import FinancialStatementDivision, ReportCode
from src.data_ingestor.exceptions import (
    DartAuthenticationError,
    DartNotFoundError,
    DartRateLimitError,
    DartResponseError,
)


class TestDartAPIClientInit:
    """DartAPIClient 초기화 테스트."""

    def test_init_with_api_key(self) -> None:
        """API 키로 초기화 테스트."""
        client = DartAPIClient(api_key="test_api_key")
        assert client._api_key == "test_api_key"
        assert not client.is_connected

    def test_init_without_api_key_raises_error(self) -> None:
        """API 키 없이 초기화 시 예외 발생 테스트."""
        # 환경변수를 직접 제거
        original = os.environ.pop("DART_API_KEY", None)
        try:
            with pytest.raises(DartAuthenticationError):
                DartAPIClient(api_key=None)
        finally:
            if original:
                os.environ["DART_API_KEY"] = original

    def test_init_from_env_variable(self) -> None:
        """환경변수에서 API 키 로드 테스트."""
        original = os.environ.get("DART_API_KEY")
        os.environ["DART_API_KEY"] = "env_api_key"
        try:
            client = DartAPIClient()
            assert client._api_key == "env_api_key"
        finally:
            if original:
                os.environ["DART_API_KEY"] = original
            else:
                os.environ.pop("DART_API_KEY", None)

    def test_init_with_custom_timeout(self) -> None:
        """커스텀 타임아웃 설정 테스트."""
        client = DartAPIClient(api_key="test", timeout=60.0, connect_timeout=15.0)
        assert client._timeout == 60.0
        assert client._connect_timeout == 15.0


class TestDartAPIClientContextManager:
    """컨텍스트 매니저 테스트."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self) -> None:
        """컨텍스트 매니저 진입/종료 테스트."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance

            async with DartAPIClient(api_key="test") as client:
                assert client._client is not None

            mock_instance.aclose.assert_called_once()


class TestDartAPIClientRequest:
    """API 요청 테스트."""

    @pytest.fixture
    def client(self) -> DartAPIClient:
        """테스트용 클라이언트."""
        client = DartAPIClient(api_key="test_api_key")
        # Circuit breaker 메서드를 AsyncMock으로 교체
        client._circuit_breaker._on_success = AsyncMock()
        client._circuit_breaker._on_failure = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_handle_success_response(self, client: DartAPIClient) -> None:
        """성공 응답 처리 테스트."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "000",
            "message": "정상",
            "corp_code": "00126380",
            "corp_name": "삼성전자",
        }

        result = await client._handle_response(mock_response, "/company.json")
        assert result["status"] == "000"
        assert result["corp_name"] == "삼성전자"

    @pytest.mark.asyncio
    async def test_handle_no_data_response(self, client: DartAPIClient) -> None:
        """데이터 없음 응답 처리 테스트."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "013",
            "message": "조회된 데이터가 없습니다.",
        }

        with pytest.raises(DartNotFoundError):
            await client._handle_response(mock_response, "/company.json")

    @pytest.mark.asyncio
    async def test_handle_auth_error_response(self, client: DartAPIClient) -> None:
        """인증 오류 응답 처리 테스트."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "010",
            "message": "등록되지 않은 인증키입니다.",
        }

        with pytest.raises(DartAuthenticationError):
            await client._handle_response(mock_response, "/company.json")

    @pytest.mark.asyncio
    async def test_handle_rate_limit_response(self, client: DartAPIClient) -> None:
        """Rate limit 응답 처리 테스트."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "020",
            "message": "요청 제한을 초과하였습니다.",
        }

        with pytest.raises(DartRateLimitError) as exc_info:
            await client._handle_response(mock_response, "/company.json")
        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_handle_http_error(self, client: DartAPIClient) -> None:
        """HTTP 오류 응답 처리 테스트."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with pytest.raises(DartResponseError) as exc_info:
            await client._handle_response(mock_response, "/company.json")
        assert exc_info.value.status_code == 500


class TestDartAPIClientMethods:
    """API 메서드 테스트."""

    @pytest.fixture
    def client(self) -> DartAPIClient:
        """테스트용 클라이언트."""
        return DartAPIClient(api_key="test_api_key")

    @pytest.mark.asyncio
    async def test_get_company_info(self, client: DartAPIClient) -> None:
        """기업 정보 조회 테스트."""
        mock_data = {
            "status": "000",
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "corp_cls": "Y",
            "stock_code": "005930",
            "ceo_nm": "한종희",
        }

        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_data):
            result = await client.get_company_info("00126380")

            assert result.corp_code == "00126380"
            assert result.corp_name == "삼성전자"

    @pytest.mark.asyncio
    async def test_get_financial_statements(self, client: DartAPIClient) -> None:
        """재무제표 조회 테스트."""
        mock_data = {
            "status": "000",
            "list": [
                {
                    "rcept_no": "20240315000123",
                    "reprt_code": "11011",
                    "bsns_year": "2024",
                    "corp_code": "00126380",
                    "fs_div": "CFS",
                    "fs_nm": "연결재무제표",
                    "sj_div": "IS",
                    "sj_nm": "손익계산서",
                    "account_nm": "매출액",
                    "thstrm_amount": "300,000,000,000",
                    "frmtrm_amount": "280,000,000,000",
                },
            ],
        }

        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_data):
            result = await client.get_financial_statements(
                corp_code="00126380",
                bsns_year="2024",
                reprt_code=ReportCode.ANNUAL,
                fs_div=FinancialStatementDivision.CONSOLIDATED,
            )

            assert result.corp_code == "00126380"
            assert len(result.items) == 1
            assert result.items[0].account_nm == "매출액"

    @pytest.mark.asyncio
    async def test_get_major_shareholders(self, client: DartAPIClient) -> None:
        """주요주주 조회 테스트."""
        mock_data = {
            "status": "000",
            "list": [
                {
                    "rcept_no": "20240315000456",
                    "rcept_dt": "20240315",
                    "corp_code": "00126380",
                    "corp_name": "삼성전자",
                    "report_tp": "주요주주변동",
                    "repror": "이재용",
                    "stkqy": "1,000,000",
                    "stkrt": "0.54",
                },
            ],
        }

        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_data):
            result = await client.get_major_shareholders("00126380")

            assert len(result) == 1
            assert result[0].repror == "이재용"
