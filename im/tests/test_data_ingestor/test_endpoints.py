"""DART API 엔드포인트 테스트.

T-D04 검증: 모든 엔드포인트 상수 정의 확인
"""

import pytest

from src.data_ingestor.dart.endpoints import (
    DART_BASE_URL,
    AccountCode,
    BusinessReportEndpoints,
    CorporateClass,
    DartDefaults,
    DartStatusCode,
    DisclosureEndpoints,
    FinancialEndpoints,
    FinancialStatementDivision,
    ReportCode,
    ShareholdingEndpoints,
    get_company_info_url,
    get_dividend_url,
    get_employees_url,
    get_executives_url,
    get_financial_statements_url,
    get_major_stock_url,
)


class TestBaseURL:
    """기본 URL 테스트."""

    def test_base_url(self) -> None:
        """DART 기본 URL 확인."""
        assert DART_BASE_URL == "https://opendart.fss.or.kr/api"
        assert DART_BASE_URL.startswith("https://")


class TestDisclosureEndpoints:
    """공시정보 엔드포인트 테스트."""

    def test_list_endpoint(self) -> None:
        """공시검색 엔드포인트."""
        assert "list.json" in DisclosureEndpoints.LIST
        assert DisclosureEndpoints.LIST.startswith(DART_BASE_URL)

    def test_company_endpoint(self) -> None:
        """기업개황 엔드포인트."""
        assert "company.json" in DisclosureEndpoints.COMPANY

    def test_corp_code_zip_endpoint(self) -> None:
        """고유번호 ZIP 엔드포인트."""
        assert "corpCode.xml" in DisclosureEndpoints.CORP_CODE_ZIP


class TestFinancialEndpoints:
    """재무정보 엔드포인트 테스트."""

    def test_single_company_account(self) -> None:
        """단일회사 주요계정 엔드포인트."""
        assert "fnlttSinglAcnt.json" in FinancialEndpoints.SINGLE_COMPANY_ACCOUNT

    def test_multi_company_account(self) -> None:
        """다중회사 주요계정 엔드포인트."""
        assert "fnlttMultiAcnt.json" in FinancialEndpoints.MULTI_COMPANY_ACCOUNT

    def test_single_company_full(self) -> None:
        """단일회사 전체 재무제표 엔드포인트."""
        assert "fnlttSinglAcntAll.json" in FinancialEndpoints.SINGLE_COMPANY_FULL


class TestBusinessReportEndpoints:
    """사업보고서 엔드포인트 테스트."""

    def test_dividend_endpoint(self) -> None:
        """배당정보 엔드포인트."""
        assert "alotMatter.json" in BusinessReportEndpoints.DIVIDEND

    def test_major_shareholder_endpoint(self) -> None:
        """최대주주현황 엔드포인트."""
        assert "hyslrSttus.json" in BusinessReportEndpoints.MAJOR_SHAREHOLDER

    def test_executives_endpoint(self) -> None:
        """임원현황 엔드포인트."""
        assert "exctvSttus.json" in BusinessReportEndpoints.EXECUTIVES

    def test_employees_endpoint(self) -> None:
        """직원현황 엔드포인트."""
        assert "empSttus.json" in BusinessReportEndpoints.EMPLOYEES


class TestShareholdingEndpoints:
    """지분공시 엔드포인트 테스트."""

    def test_major_stock_endpoint(self) -> None:
        """대량보유상황보고서 엔드포인트."""
        assert "majorstock.json" in ShareholdingEndpoints.MAJOR_STOCK

    def test_executive_stock_endpoint(self) -> None:
        """임원주요주주 특정증권 엔드포인트."""
        assert "elestock.json" in ShareholdingEndpoints.EXECUTIVE_STOCK


class TestReportCode:
    """보고서 코드 테스트."""

    def test_annual_report(self) -> None:
        """사업보고서 코드."""
        assert ReportCode.ANNUAL.value == "11011"

    def test_semi_annual_report(self) -> None:
        """반기보고서 코드."""
        assert ReportCode.SEMI_ANNUAL.value == "11012"

    def test_quarterly_reports(self) -> None:
        """분기보고서 코드."""
        assert ReportCode.Q1.value == "11013"
        assert ReportCode.Q3.value == "11014"


class TestFinancialStatementDivision:
    """재무제표 구분 테스트."""

    def test_consolidated(self) -> None:
        """연결재무제표 코드."""
        assert FinancialStatementDivision.CONSOLIDATED.value == "CFS"

    def test_separate(self) -> None:
        """별도재무제표 코드."""
        assert FinancialStatementDivision.SEPARATE.value == "OFS"


class TestCorporateClass:
    """법인구분 테스트."""

    def test_all_markets(self) -> None:
        """모든 시장 코드 확인."""
        assert CorporateClass.KOSPI.value == "Y"
        assert CorporateClass.KOSDAQ.value == "K"
        assert CorporateClass.KONEX.value == "N"
        assert CorporateClass.ETC.value == "E"


class TestDartStatusCode:
    """API 상태 코드 테스트."""

    def test_success_code(self) -> None:
        """성공 코드."""
        assert DartStatusCode.SUCCESS == "000"
        assert DartStatusCode.is_success("000") is True
        assert DartStatusCode.is_success("013") is False

    def test_error_codes(self) -> None:
        """에러 코드 존재 확인."""
        assert DartStatusCode.INVALID_KEY == "010"
        assert DartStatusCode.RATE_LIMIT_EXCEEDED == "020"
        assert DartStatusCode.NO_DATA == "013"

    def test_retryable_errors(self) -> None:
        """재시도 가능한 에러 확인."""
        assert DartStatusCode.is_retryable("020") is True  # Rate limit
        assert DartStatusCode.is_retryable("800") is True  # System maintenance
        assert DartStatusCode.is_retryable("010") is False  # Invalid key

    def test_get_message(self) -> None:
        """상태 코드 메시지 조회."""
        msg = DartStatusCode.get_message("000")
        assert msg == "정상"

        msg = DartStatusCode.get_message("020")
        assert "제한" in msg


class TestAccountCode:
    """계정과목 코드 테스트."""

    def test_balance_sheet_codes(self) -> None:
        """재무상태표 계정과목 코드."""
        assert "Assets" in AccountCode.TOTAL_ASSETS
        assert "Liabilities" in AccountCode.TOTAL_LIABILITIES
        assert "Equity" in AccountCode.TOTAL_EQUITY

    def test_income_statement_codes(self) -> None:
        """손익계산서 계정과목 코드."""
        assert "Revenue" in AccountCode.REVENUE
        assert "CostOfSales" in AccountCode.COST_OF_SALES
        assert "OperatingIncome" in AccountCode.OPERATING_INCOME


class TestDartDefaults:
    """기본값 테스트."""

    def test_rate_limit(self) -> None:
        """Rate limit 기본값."""
        assert DartDefaults.RATE_LIMIT_CALLS == 100
        assert DartDefaults.RATE_LIMIT_PERIOD == 60.0

    def test_timeouts(self) -> None:
        """타임아웃 기본값."""
        assert DartDefaults.REQUEST_TIMEOUT == 30.0
        assert DartDefaults.CONNECT_TIMEOUT == 10.0

    def test_retry_config(self) -> None:
        """재시도 설정 기본값."""
        assert DartDefaults.MAX_RETRIES == 3
        assert DartDefaults.RETRY_BASE_DELAY == 1.0


class TestConvenienceFunctions:
    """편의 함수 테스트."""

    def test_get_financial_statements_url(self) -> None:
        """재무제표 URL 반환."""
        url = get_financial_statements_url()
        assert "fnlttSinglAcnt.json" in url

    def test_get_company_info_url(self) -> None:
        """기업개황 URL 반환."""
        url = get_company_info_url()
        assert "company.json" in url

    def test_get_major_stock_url(self) -> None:
        """대량보유상황보고서 URL 반환."""
        url = get_major_stock_url()
        assert "majorstock.json" in url

    def test_get_dividend_url(self) -> None:
        """배당정보 URL 반환."""
        url = get_dividend_url()
        assert "alotMatter.json" in url

    def test_get_executives_url(self) -> None:
        """임원현황 URL 반환."""
        url = get_executives_url()
        assert "exctvSttus.json" in url

    def test_get_employees_url(self) -> None:
        """직원현황 URL 반환."""
        url = get_employees_url()
        assert "empSttus.json" in url
