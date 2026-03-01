"""DART API 모델 테스트.

T-D03 검증: JSON → 모델 직렬화/역직렬화 테스트
"""

from decimal import Decimal

import pytest

from src.data_ingestor.dart.models import (
    DartAPIResponse,
    DartCompanyInfo,
    DartFinancialStatement,
    DartMajorShareholder,
    DartSearchResult,
    FinancialStatementsCollection,
)


class TestDartSearchResult:
    """DartSearchResult 모델 테스트."""

    def test_parse_listed_company(self) -> None:
        """상장 기업 JSON 파싱."""
        data = {
            "corp_code": "00123456",
            "corp_name": "삼성전자",
            "stock_code": "005930",
            "modify_date": "20240115",
        }

        result = DartSearchResult.model_validate(data)

        assert result.corp_code == "00123456"
        assert result.corp_name == "삼성전자"
        assert result.stock_code == "005930"
        assert result.is_listed is True

    def test_parse_unlisted_company(self) -> None:
        """비상장 기업 JSON 파싱 (빈 stock_code)."""
        data = {
            "corp_code": "00654321",
            "corp_name": "비상장기업",
            "stock_code": "",
            "modify_date": "20240115",
        }

        result = DartSearchResult.model_validate(data)

        assert result.stock_code is None
        assert result.is_listed is False

    def test_serialization(self) -> None:
        """모델 → JSON 직렬화."""
        result = DartSearchResult(
            corp_code="00123456",
            corp_name="테스트기업",
            stock_code="005930",
            modify_date="20240115",
        )

        data = result.model_dump()

        assert data["corp_code"] == "00123456"
        assert data["stock_code"] == "005930"


class TestDartCompanyInfo:
    """DartCompanyInfo 모델 테스트."""

    def test_parse_full_info(self) -> None:
        """전체 기업 정보 파싱."""
        data = {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "corp_name_eng": "SAMSUNG ELECTRONICS CO., LTD.",
            "stock_name": "삼성전자",
            "stock_code": "005930",
            "ceo_nm": "한종희, 경계현",
            "corp_cls": "Y",
            "jurir_no": "1301110006246",
            "bizr_no": "1248100998",
            "adres": "경기도 수원시 영통구 삼성로 129 (매탄동)",
            "hm_url": "www.samsung.com",
            "ir_url": "www.samsung.com/sec/ir",
            "phn_no": "031-200-1114",
            "fax_no": "031-200-7538",
            "induty_code": "264",
            "est_dt": "19690113",
            "acc_mt": "12",
        }

        info = DartCompanyInfo.model_validate(data)

        assert info.corp_code == "00126380"
        assert info.corp_name == "삼성전자"
        assert info.is_listed is True
        assert info.market_type == "유가증권"
        assert info.establishment_date is not None
        assert info.establishment_date.year == 1969

    def test_parse_unlisted_company(self) -> None:
        """비상장 기업 파싱."""
        data = {
            "corp_code": "00654321",
            "corp_name": "비상장기업",
            "corp_cls": "E",
            "stock_code": "",
            "hm_url": "",
        }

        info = DartCompanyInfo.model_validate(data)

        assert info.is_listed is False
        assert info.market_type == "기타"
        assert info.stock_code is None
        assert info.hm_url is None

    def test_market_types(self) -> None:
        """시장 구분 테스트."""
        test_cases = [
            ("Y", "유가증권"),
            ("K", "코스닥"),
            ("N", "코넥스"),
            ("E", "기타"),
        ]

        for corp_cls, expected in test_cases:
            info = DartCompanyInfo(
                corp_code="00000000",
                corp_name="테스트",
                corp_cls=corp_cls,
            )
            assert info.market_type == expected


class TestDartFinancialStatement:
    """DartFinancialStatement 모델 테스트."""

    def test_parse_financial_statement(self) -> None:
        """재무제표 항목 파싱."""
        data = {
            "rcept_no": "20240315000123",
            "reprt_code": "11011",
            "bsns_year": "2023",
            "corp_code": "00126380",
            "stock_code": "005930",
            "fs_div": "CFS",
            "fs_nm": "연결재무제표",
            "sj_div": "BS",
            "sj_nm": "재무상태표",
            "account_id": "ifrs-full_Assets",
            "account_nm": "자산총계",
            "thstrm_nm": "제55기",
            "thstrm_amount": "403,476,326,000,000",
            "frmtrm_nm": "제54기",
            "frmtrm_amount": "387,800,000,000,000",
            "bfefrmtrm_nm": "제53기",
            "bfefrmtrm_amount": "340,000,000,000,000",
            "ord": "1",
        }

        stmt = DartFinancialStatement.model_validate(data)

        assert stmt.bsns_year == "2023"
        assert stmt.account_nm == "자산총계"
        assert stmt.is_consolidated is True

        # 금액 파싱 (콤마 제거)
        assert stmt.current_amount == Decimal("403476326000000")
        assert stmt.previous_amount == Decimal("387800000000000")
        assert stmt.before_previous_amount == Decimal("340000000000000")

    def test_parse_empty_amounts(self) -> None:
        """빈 금액 처리."""
        data = {
            "rcept_no": "20240315000123",
            "reprt_code": "11011",
            "bsns_year": "2023",
            "corp_code": "00126380",
            "fs_div": "OFS",
            "fs_nm": "별도재무제표",
            "sj_div": "IS",
            "sj_nm": "손익계산서",
            "account_nm": "영업이익",
            "thstrm_amount": "-",
            "frmtrm_amount": "",
        }

        stmt = DartFinancialStatement.model_validate(data)

        assert stmt.current_amount is None
        assert stmt.previous_amount is None
        assert stmt.is_consolidated is False


class TestDartMajorShareholder:
    """DartMajorShareholder 모델 테스트."""

    def test_parse_shareholder(self) -> None:
        """주요주주 정보 파싱."""
        data = {
            "rcept_no": "20240315000456",
            "rcept_dt": "2024-03-15",
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "report_tp": "지분변동",
            "repror": "국민연금공단",
            "stkqy": "421,387,600",
            "stkrt": "7.15",
            "stkqy_irds": "1,234,567",
            "stkrt_irds": "0.02",
        }

        shareholder = DartMajorShareholder.model_validate(data)

        assert shareholder.share_count == 421387600
        assert shareholder.share_ratio == Decimal("7.15")
        assert shareholder.repror == "국민연금공단"


class TestFinancialStatementsCollection:
    """FinancialStatementsCollection 테스트."""

    @pytest.fixture
    def sample_collection(self) -> FinancialStatementsCollection:
        """샘플 컬렉션 생성."""
        items = [
            DartFinancialStatement(
                rcept_no="20240315000123",
                reprt_code="11011",
                bsns_year="2023",
                corp_code="00126380",
                fs_div="CFS",
                fs_nm="연결재무제표",
                sj_div="IS",
                sj_nm="손익계산서",
                account_nm="매출액",
                thstrm_amount="300000000000000",
            ),
            DartFinancialStatement(
                rcept_no="20240315000124",
                reprt_code="11011",
                bsns_year="2022",
                corp_code="00126380",
                fs_div="CFS",
                fs_nm="연결재무제표",
                sj_div="IS",
                sj_nm="손익계산서",
                account_nm="매출액",
                thstrm_amount="280000000000000",
            ),
            DartFinancialStatement(
                rcept_no="20240315000125",
                reprt_code="11011",
                bsns_year="2023",
                corp_code="00126380",
                fs_div="OFS",
                fs_nm="별도재무제표",
                sj_div="IS",
                sj_nm="손익계산서",
                account_nm="매출액",
                thstrm_amount="150000000000000",
            ),
        ]
        return FinancialStatementsCollection(corp_code="00126380", items=items)

    def test_filter_by_year(self, sample_collection: FinancialStatementsCollection) -> None:
        """연도별 필터링."""
        items_2023 = sample_collection.filter_by_year("2023")
        assert len(items_2023) == 2

        items_2022 = sample_collection.filter_by_year("2022")
        assert len(items_2022) == 1

    def test_filter_consolidated(self, sample_collection: FinancialStatementsCollection) -> None:
        """연결재무제표 필터링."""
        consolidated = sample_collection.filter_consolidated()
        assert len(consolidated) == 2
        assert all(item.is_consolidated for item in consolidated)

    def test_filter_separate(self, sample_collection: FinancialStatementsCollection) -> None:
        """별도재무제표 필터링."""
        separate = sample_collection.filter_separate()
        assert len(separate) == 1
        assert not separate[0].is_consolidated

    def test_get_account_values(self, sample_collection: FinancialStatementsCollection) -> None:
        """계정별 연도 값 조회."""
        values = sample_collection.get_account_values("매출액", consolidated=True)

        assert "2023" in values
        assert "2022" in values
        assert values["2023"] == Decimal("300000000000000")

    def test_years_property(self, sample_collection: FinancialStatementsCollection) -> None:
        """연도 목록 조회."""
        years = sample_collection.years
        assert years == ["2022", "2023"]

    def test_account_names_property(self, sample_collection: FinancialStatementsCollection) -> None:
        """계정명 목록 조회."""
        names = sample_collection.account_names
        assert "매출액" in names


class TestDartAPIResponse:
    """DartAPIResponse 테스트."""

    def test_success_response(self) -> None:
        """성공 응답 판별."""
        response = DartAPIResponse(status="000", message="정상")
        assert response.is_success is True
        assert response.is_no_data is False

    def test_no_data_response(self) -> None:
        """데이터 없음 응답 판별."""
        response = DartAPIResponse(status="013", message="조회된 데이터가 없습니다.")
        assert response.is_success is False
        assert response.is_no_data is True

    def test_error_response(self) -> None:
        """에러 응답 판별."""
        response = DartAPIResponse(status="020", message="요청 제한 초과")
        assert response.is_success is False
        assert response.is_no_data is False
