"""Aggregator 테스트."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.data_ingestor.aggregator import (
    CompanyProfile,
    DataAggregator,
    FinancialMetric,
    FinancialSummary,
    IMDocumentData,
    NewsInfo,
    ShareholderInfo,
)
from src.data_ingestor.exceptions import MissingRequiredDataError


class TestFinancialMetric:
    """FinancialMetric 테스트."""

    def test_calculate_growth_positive(self) -> None:
        """양의 성장률 계산 테스트."""
        metric = FinancialMetric(
            name="매출액",
            current_value=Decimal("1200000000"),
            previous_value=Decimal("1000000000"),
        )

        growth = metric.calculate_growth()

        assert growth is not None
        assert abs(growth - 20.0) < 0.01  # 20% 성장

    def test_calculate_growth_negative(self) -> None:
        """음의 성장률 계산 테스트."""
        metric = FinancialMetric(
            name="영업이익",
            current_value=Decimal("800000000"),
            previous_value=Decimal("1000000000"),
        )

        growth = metric.calculate_growth()

        assert growth is not None
        assert abs(growth - (-20.0)) < 0.01  # -20% 성장

    def test_calculate_growth_no_previous(self) -> None:
        """전기 값 없을 때 성장률 테스트."""
        metric = FinancialMetric(
            name="매출액",
            current_value=Decimal("1000000000"),
            previous_value=None,
        )

        assert metric.calculate_growth() is None

    def test_calculate_growth_zero_previous(self) -> None:
        """전기 값이 0일 때 테스트."""
        metric = FinancialMetric(
            name="매출액",
            current_value=Decimal("1000000000"),
            previous_value=Decimal("0"),
        )

        assert metric.calculate_growth() is None


class TestFinancialSummary:
    """FinancialSummary 테스트."""

    def test_calculate_operating_margin(self) -> None:
        """영업이익률 계산 테스트."""
        summary = FinancialSummary()
        summary.revenue.current_value = Decimal("1000000000")
        summary.operating_profit.current_value = Decimal("100000000")

        summary.calculate_ratios()

        assert summary.operating_margin is not None
        assert abs(summary.operating_margin - 10.0) < 0.01  # 10%

    def test_calculate_roe(self) -> None:
        """ROE 계산 테스트."""
        summary = FinancialSummary()
        summary.net_income.current_value = Decimal("100000000")
        summary.total_equity.current_value = Decimal("500000000")

        summary.calculate_ratios()

        assert summary.roe is not None
        assert abs(summary.roe - 20.0) < 0.01  # 20%

    def test_calculate_debt_ratio(self) -> None:
        """부채비율 계산 테스트."""
        summary = FinancialSummary()
        summary.total_liabilities.current_value = Decimal("300000000")
        summary.total_equity.current_value = Decimal("500000000")

        summary.calculate_ratios()

        assert summary.debt_ratio is not None
        assert abs(summary.debt_ratio - 60.0) < 0.01  # 60%


class TestDataAggregator:
    """DataAggregator 테스트."""

    @pytest.fixture
    def mock_dart_company(self) -> MagicMock:
        """모의 DART 기업 정보."""
        company = MagicMock()
        company.corp_code = "00126380"
        company.corp_name = "삼성전자"
        company.corp_name_eng = "Samsung Electronics"
        company.stock_code = "005930"
        company.ceo_nm = "한종희"
        company.induty_code = "제조업"
        company.hm_url = "https://www.samsung.com"
        company.ir_url = "https://www.samsung.com/ir"
        company.adres = "경기도 수원시"
        company.phn_no = "02-1234-5678"
        company.fax_no = "02-1234-5679"
        company.acc_mt = "12"
        company.est_dt = "19690113"
        return company

    @pytest.fixture
    def mock_financials(self) -> MagicMock:
        """모의 재무제표."""
        fs = MagicMock()
        fs.bsns_year = "2024"
        fs.fs_div = "CFS"

        item = MagicMock()
        item.account_nm = "매출액"
        item.current_amount = Decimal("100000000000")
        item.previous_amount = Decimal("90000000000")

        fs.get_by_account.return_value = item
        fs.items = [item]
        return fs

    def test_add_dart_company(self, mock_dart_company: MagicMock) -> None:
        """DART 기업 정보 추가 테스트."""
        aggregator = DataAggregator()
        result = aggregator.add_dart_company(mock_dart_company)

        assert result is aggregator  # 체이닝 지원
        assert aggregator._company is mock_dart_company
        assert "DART" in aggregator._data_sources

    def test_add_dart_financials(self, mock_financials: MagicMock) -> None:
        """DART 재무제표 추가 테스트."""
        aggregator = DataAggregator()
        result = aggregator.add_dart_financials(mock_financials)

        assert result is aggregator
        assert aggregator._financials is mock_financials

    def test_add_parsed_financials(self) -> None:
        """파싱된 재무 데이터 추가 테스트."""
        aggregator = DataAggregator()
        data = {"EBITDA": 50000000000, "FCF": 30000000000}

        result = aggregator.add_parsed_financials(data, source="Excel")

        assert result is aggregator
        assert aggregator._parsed_financials["EBITDA"] == 50000000000
        assert "Excel" in aggregator._data_sources

    def test_validate_missing_company(self) -> None:
        """기업 정보 누락 검증 테스트."""
        aggregator = DataAggregator()

        errors = aggregator.validate()

        assert len(errors) > 0
        assert any("기업 정보" in e for e in errors)

    def test_validate_missing_financials(self, mock_dart_company: MagicMock) -> None:
        """재무 정보 누락 검증 테스트."""
        aggregator = DataAggregator()
        aggregator.add_dart_company(mock_dart_company)

        errors = aggregator.validate()

        assert len(errors) > 0
        assert any("재무 정보" in e for e in errors)

    def test_build_without_require_all(
        self,
        mock_dart_company: MagicMock,
    ) -> None:
        """require_all=False 빌드 테스트."""
        aggregator = DataAggregator()
        aggregator.add_dart_company(mock_dart_company)

        # 예외 없이 빌드
        result = aggregator.build(require_all=False)

        assert isinstance(result, IMDocumentData)
        assert result.company.corp_name == "삼성전자"

    def test_build_with_require_all_raises(self) -> None:
        """require_all=True 빌드 시 예외 테스트."""
        aggregator = DataAggregator()

        with pytest.raises(MissingRequiredDataError):
            aggregator.build(require_all=True)

    def test_build_company_profile(
        self,
        mock_dart_company: MagicMock,
    ) -> None:
        """기업 프로필 빌드 테스트."""
        aggregator = DataAggregator()
        aggregator.add_dart_company(mock_dart_company)

        result = aggregator.build()

        assert result.company.corp_code == "00126380"
        assert result.company.corp_name == "삼성전자"
        assert result.company.stock_code == "005930"
        assert result.company.ceo_name == "한종희"

    def test_build_with_all_data(
        self,
        mock_dart_company: MagicMock,
        mock_financials: MagicMock,
    ) -> None:
        """전체 데이터 빌드 테스트."""
        aggregator = DataAggregator()
        aggregator.add_dart_company(mock_dart_company)
        aggregator.add_dart_financials(mock_financials)

        result = aggregator.build()

        assert result.company.corp_name == "삼성전자"
        assert result.financials.bsns_year == "2024"
        assert len(result.data_sources) >= 1

    def test_reset(self, mock_dart_company: MagicMock) -> None:
        """리셋 테스트."""
        aggregator = DataAggregator()
        aggregator.add_dart_company(mock_dart_company)

        aggregator.reset()

        assert aggregator._company is None
        assert aggregator._financials is None
        assert len(aggregator._data_sources) == 0


class TestIMDocumentData:
    """IMDocumentData 테스트."""

    def test_to_dict(self) -> None:
        """딕셔너리 변환 테스트."""
        data = IMDocumentData()
        data.company.corp_name = "테스트 회사"
        data.company.corp_code = "00123456"
        data.financials.bsns_year = "2024"

        result = data.to_dict()

        assert result["company"]["corp_name"] == "테스트 회사"
        assert result["financials"]["bsns_year"] == "2024"
        assert "collected_at" in result


class TestCompanyProfile:
    """CompanyProfile 테스트."""

    def test_default_values(self) -> None:
        """기본값 테스트."""
        profile = CompanyProfile()

        assert profile.corp_code == ""
        assert profile.corp_name == ""
        assert profile.fiscal_month == 12
        assert profile.brand_colors == []


class TestShareholderInfo:
    """ShareholderInfo 테스트."""

    def test_creation(self) -> None:
        """생성 테스트."""
        info = ShareholderInfo(
            name="이재용",
            share_count=1000000,
            share_ratio=0.54,
            is_major=True,
        )

        assert info.name == "이재용"
        assert info.share_ratio == 0.54
        assert info.is_major is True


class TestNewsInfo:
    """NewsInfo 테스트."""

    def test_creation(self) -> None:
        """생성 테스트."""
        info = NewsInfo(
            title="테스트 기사",
            url="https://news.example.com",
            source="테스트 뉴스",
            published_at=datetime(2024, 1, 15),
        )

        assert info.title == "테스트 기사"
        assert info.source == "테스트 뉴스"
