"""DataTransformer 단위 테스트.

> 마지막 수정: 2026-02-11 10:00:00
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import pytest

from src.chart_engine.data_transformer import ChartSpec, DataTransformer


# ---------------------------------------------------------------------------
# Duck-typed 테스트용 데이터 클래스 (design_renderer import 회피)
# ---------------------------------------------------------------------------


@dataclass
class _FakeFinancialStatements:
    revenue: dict[str, float] = field(default_factory=dict)
    operating_income: dict[str, float] = field(default_factory=dict)
    cost_of_goods_sold: dict[str, float] = field(default_factory=dict)
    sga_expenses: dict[str, float] = field(default_factory=dict)
    ebitda: dict[str, float] = field(default_factory=dict)
    net_income: dict[str, float] = field(default_factory=dict)

    @property
    def years(self) -> list[str]:
        all_years: set[str] = set()
        for fld in [self.revenue, self.operating_income, self.net_income]:
            all_years.update(fld.keys())
        return sorted(all_years)


@dataclass
class _FakeSegmentRevenue:
    segments: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class _FakeMarketData:
    tam: Optional[float] = None
    sam: Optional[float] = None
    som: Optional[float] = None
    competitors: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _FakeShareholder:
    name: str = ""
    stake_pct: float = 0.0


@dataclass
class _FakeDocumentData:
    financial_statements: Any = None
    segment_revenue: Any = None
    market_data: Any = None
    shareholders: list[Any] = field(default_factory=list)
    derived_metrics: Optional[dict[str, float]] = None


class TestTransformFinancial:
    """재무 데이터 변환."""

    def test_combo_chart_generated(self):
        """매출 + 영업이익률 콤보 차트 생성."""
        fs = _FakeFinancialStatements(
            revenue={"2022": 100_000, "2023": 120_000, "2024": 150_000},
            operating_income={"2022": 10_000, "2023": 15_000, "2024": 22_000},
        )
        transformer = DataTransformer()
        charts = transformer.transform_financial(fs)
        assert any(c.chart_type == "combo" for c in charts)

    def test_waterfall_chart_generated(self):
        """영업이익 워터폴 생성 (COGS/SGA 존재 시)."""
        fs = _FakeFinancialStatements(
            revenue={"2023": 120_000, "2024": 150_000},
            operating_income={"2023": 18_000, "2024": 22_000},
            cost_of_goods_sold={"2023": 75_000, "2024": 90_000},
            sga_expenses={"2023": 27_000, "2024": 38_000},
        )
        transformer = DataTransformer()
        charts = transformer.transform_financial(fs)
        assert any(c.chart_type == "waterfall" for c in charts)

    def test_ebitda_line_chart(self):
        """EBITDA 추이 라인 차트 (3년 이상)."""
        fs = _FakeFinancialStatements(
            revenue={"2022": 100_000, "2023": 120_000, "2024": 150_000},
            operating_income={"2022": 10_000, "2023": 15_000, "2024": 22_000},
            ebitda={"2022": 15_000, "2023": 20_000, "2024": 28_000},
        )
        transformer = DataTransformer()
        charts = transformer.transform_financial(fs)
        assert any(c.chart_type == "line" for c in charts)

    def test_insufficient_data_returns_empty(self):
        """데이터 부족 시 빈 리스트."""
        fs = _FakeFinancialStatements(revenue={"2024": 100_000})
        transformer = DataTransformer()
        charts = transformer.transform_financial(fs)
        assert charts == []


class TestTransformMarket:
    """시장 데이터 변환."""

    def test_tam_sam_som_donut(self):
        """TAM/SAM/SOM 도넛 차트."""
        md = _FakeMarketData(tam=10_000, sam=5_000, som=1_000)
        transformer = DataTransformer()
        charts = transformer.transform_market(md)
        assert any(c.chart_type == "donut" for c in charts)
        donut = next(c for c in charts if c.chart_type == "donut")
        assert donut.data["labels"] == ["TAM", "SAM", "SOM"]

    def test_competitors_hbar(self):
        """경쟁사 비교 수평 바 차트."""
        md = _FakeMarketData(
            competitors=[
                {"name": "경쟁사A", "revenue": 50_000},
                {"name": "경쟁사B", "revenue": 30_000},
            ],
        )
        transformer = DataTransformer()
        charts = transformer.transform_market(md)
        assert any(c.chart_type == "hbar" for c in charts)

    def test_tam_sam_som_funnel(self):
        """TAM/SAM/SOM 퍼널 차트."""
        md = _FakeMarketData(tam=10_000, sam=5_000, som=1_000)
        transformer = DataTransformer()
        charts = transformer.transform_market(md)
        assert any(c.chart_type == "funnel" for c in charts)
        funnel = next(c for c in charts if c.chart_type == "funnel")
        assert funnel.data["stages"] == ["TAM", "SAM", "SOM"]
        assert funnel.data["values"] == [10_000, 5_000, 1_000]

    def test_tam_sam_som_both_donut_and_funnel(self):
        """TAM/SAM/SOM 시 도넛과 퍼널 모두 생성."""
        md = _FakeMarketData(tam=10_000, sam=5_000, som=1_000)
        transformer = DataTransformer()
        charts = transformer.transform_market(md)
        types = [c.chart_type for c in charts]
        assert "donut" in types
        assert "funnel" in types

    def test_empty_market_returns_empty(self):
        """시장 데이터 없으면 빈 리스트."""
        md = _FakeMarketData()
        transformer = DataTransformer()
        charts = transformer.transform_market(md)
        assert charts == []


class TestTransformShareholders:
    """주주 데이터 변환."""

    def test_shareholder_donut(self):
        """주주 구성 도넛 차트."""
        shareholders = [
            _FakeShareholder(name="최대주주", stake_pct=0.51),
            _FakeShareholder(name="기관투자자", stake_pct=0.30),
            _FakeShareholder(name="소액주주", stake_pct=0.19),
        ]
        transformer = DataTransformer()
        charts = transformer.transform_shareholders(shareholders)
        assert len(charts) == 1
        assert charts[0].chart_type == "donut"

    def test_empty_shareholders_returns_empty(self):
        """빈 주주 리스트."""
        transformer = DataTransformer()
        charts = transformer.transform_shareholders([])
        assert charts == []


class TestTransformAll:
    """전체 변환."""

    def test_transform_all(self):
        """전체 변환 — 섹션별 차트 dict 반환."""
        doc = _FakeDocumentData(
            financial_statements=_FakeFinancialStatements(
                revenue={"2022": 100_000, "2023": 120_000, "2024": 150_000},
                operating_income={"2022": 10_000, "2023": 15_000, "2024": 22_000},
            ),
            market_data=_FakeMarketData(tam=10_000, sam=5_000, som=1_000),
            shareholders=[
                _FakeShareholder(name="최대주주", stake_pct=0.51),
            ],
        )
        transformer = DataTransformer()
        result = transformer.transform_all(doc)

        assert "financial_analysis" in result
        assert "market_overview" in result
        assert "shareholder_structure" in result

    def test_transform_all_empty_doc(self):
        """빈 문서 → 빈 dict."""
        doc = _FakeDocumentData()
        transformer = DataTransformer()
        result = transformer.transform_all(doc)
        assert result == {}
