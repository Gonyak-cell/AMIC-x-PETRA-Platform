"""데이터 일관성 테스트 — 섹션 프리셋/파생지표/교차검증."""

import pytest

from src.design_renderer.im_document import (
    COVENANT_SECTIONS,
    SECTION_IDS,
    TITAN_SECTIONS,
    FinancialStatements,
    IMDocumentData,
    IMStyle,
)


class TestSectionPresets:
    """IM 스타일별 섹션 구성."""

    def test_titan_sections(self):
        """TITAN → 9개 특정 섹션."""
        data = IMDocumentData(im_style=IMStyle.TITAN)
        assert data.sections == TITAN_SECTIONS
        assert len(data.sections) == 9
        assert "cover" in data.sections
        assert "contact" in data.sections

    def test_covenant_sections(self):
        """COVENANT → 10개 특정 섹션."""
        data = IMDocumentData(im_style=IMStyle.COVENANT)
        assert data.sections == COVENANT_SECTIONS
        assert len(data.sections) == 10
        assert "value_creation" in data.sections

    def test_full_sections(self):
        """FULL → 19개 전체 섹션."""
        data = IMDocumentData(im_style=IMStyle.FULL)
        assert data.sections == SECTION_IDS
        assert len(data.sections) == 19

    def test_custom_sections(self):
        """CUSTOM → 사용자 지정 유지."""
        custom = ["cover", "executive_summary", "contact"]
        data = IMDocumentData(im_style=IMStyle.CUSTOM, sections=custom)
        assert data.sections == custom

    def test_get_active_sections_filters_invalid(self):
        """유효하지 않은 section_id 필터링."""
        data = IMDocumentData(
            im_style=IMStyle.CUSTOM,
            sections=["cover", "invalid_section", "contact"],
        )
        active = data.get_active_sections()
        assert "invalid_section" not in active
        assert "cover" in active
        assert "contact" in active


class TestDerivedMetrics:
    """파생 지표 계산."""

    @pytest.fixture
    def data_with_financials(self) -> IMDocumentData:
        data = IMDocumentData(
            financial_statements=FinancialStatements(
                revenue={"2022": 100_000, "2023": 120_000, "2024": 150_000},
                operating_income={"2022": 15_000, "2023": 20_000, "2024": 28_000},
                net_income={"2022": 10_000, "2023": 14_000, "2024": 20_000},
                ebitda={"2022": 20_000, "2023": 26_000, "2024": 35_000},
                gross_profit={"2022": 40_000, "2023": 50_000, "2024": 65_000},
                total_liabilities={"2024": 100_000},
                total_equity={"2024": 200_000},
            )
        )
        data.compute_derived_metrics()
        return data

    def test_revenue_cagr_3y(self, data_with_financials: IMDocumentData):
        """3년 매출 CAGR 계산."""
        metrics = data_with_financials.derived_metrics
        assert metrics is not None
        assert "revenue_cagr_3y" in metrics
        # (150000/100000)^(1/2) - 1 ≈ 0.2247
        assert 0.20 < metrics["revenue_cagr_3y"] < 0.25

    def test_margin_ratios(self, data_with_financials: IMDocumentData):
        """마진율 계산 (최신 연도)."""
        metrics = data_with_financials.derived_metrics
        assert "operating_margin_latest" in metrics
        # 28000 / 150000 ≈ 0.1867
        assert 0.18 < metrics["operating_margin_latest"] < 0.20

    def test_yoy_growth(self, data_with_financials: IMDocumentData):
        """YoY 성장률."""
        metrics = data_with_financials.derived_metrics
        assert "revenue_yoy" in metrics
        # (150000 - 120000) / 120000 = 0.25
        assert abs(metrics["revenue_yoy"] - 0.25) < 0.01

    def test_debt_to_equity(self, data_with_financials: IMDocumentData):
        """부채비율."""
        metrics = data_with_financials.derived_metrics
        assert "debt_to_equity_latest" in metrics
        # 100000 / 200000 = 0.5
        assert abs(metrics["debt_to_equity_latest"] - 0.5) < 0.01


class TestValidateConsistency:
    """교차 검증."""

    def test_matching_values_no_warnings(self):
        """일치하는 값 → 경고 없음."""
        data = IMDocumentData()
        rendered = {
            "revenue_2024": [
                ("exec_summary", 150_000),
                ("financial", 150_000),
            ]
        }
        warnings = data.validate_consistency(rendered)
        assert len(warnings) == 0

    def test_mismatched_values_warning(self):
        """불일치 → 경고 생성."""
        data = IMDocumentData()
        rendered = {
            "revenue_2024": [
                ("exec_summary", 150_000),
                ("financial", 155_000),
            ]
        }
        warnings = data.validate_consistency(rendered)
        assert len(warnings) > 0
        assert "불일치" in warnings[0]


class TestFinancialStatements:
    """FinancialStatements 속성."""

    def test_years_sorted(self):
        """years 속성이 정렬된 연도 리스트."""
        fs = FinancialStatements(
            revenue={"2024": 150_000, "2022": 100_000, "2023": 120_000}
        )
        assert fs.years == ["2022", "2023", "2024"]

    def test_years_empty(self):
        """빈 재무제표 → 빈 연도."""
        fs = FinancialStatements()
        assert fs.years == []
