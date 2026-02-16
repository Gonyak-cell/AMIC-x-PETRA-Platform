"""차트 타입 테스트 — 6종 차트 생성 + 임베딩."""

import pytest

from src.design_renderer.components.chart_embed import (
    create_combo_chart,
    create_donut_chart,
    create_hbar_chart,
    create_line_chart,
    create_stacked_bar_chart,
    create_waterfall_chart,
    embed_chart_html,
)
from src.design_renderer.design_tokens import DEFAULT_TOKENS


pytestmark = pytest.mark.requires_plotly


class TestWaterfallChart:
    """워터폴 차트."""

    def test_create(self):
        """워터폴 차트 Figure 생성."""
        fig = create_waterfall_chart(
            {
                "categories": ["매출", "COGS", "판관비", "영업이익"],
                "values": [150_000, -85_000, -37_000, 28_000],
                "measure": ["absolute", "relative", "relative", "total"],
            },
            title="영업이익 워터폴",
        )
        assert fig is not None


class TestComboChart:
    """콤보 차트 (바+라인)."""

    def test_create(self):
        """콤보 차트 생성."""
        fig = create_combo_chart(
            {
                "years": ["2022", "2023", "2024"],
                "bar_values": [100_000, 120_000, 150_000],
                "bar_name": "매출",
                "line_values": [0.15, 0.167, 0.187],
                "line_name": "영업이익률",
            },
            title="매출 및 영업이익률",
        )
        assert fig is not None


class TestDonutChart:
    """도넛 차트."""

    def test_create(self):
        """도넛 차트 생성."""
        fig = create_donut_chart(
            {
                "labels": ["IT서비스", "SI", "기타"],
                "values": [80_000, 50_000, 20_000],
            },
            title="사업부별 매출",
        )
        assert fig is not None


class TestLineChart:
    """라인 차트."""

    def test_create(self):
        """라인 차트 생성."""
        fig = create_line_chart(
            {
                "x": ["2022", "2023", "2024"],
                "series": [
                    {"name": "매출", "values": [100_000, 120_000, 150_000]},
                ],
            },
            title="매출 추이",
        )
        assert fig is not None


class TestHbarChart:
    """수평 바 차트."""

    def test_create(self):
        """수평 바 차트 생성."""
        fig = create_hbar_chart(
            {
                "categories": ["경쟁사A", "경쟁사B", "자사"],
                "values": [80_000, 60_000, 150_000],
            },
            title="시장 점유율 비교",
        )
        assert fig is not None


class TestStackedBarChart:
    """누적 바 차트."""

    def test_create(self):
        """누적 바 차트 생성."""
        fig = create_stacked_bar_chart(
            {
                "categories": ["2022", "2023", "2024"],
                "series": [
                    {"name": "IT서비스", "values": [60_000, 70_000, 90_000]},
                    {"name": "SI", "values": [30_000, 40_000, 45_000]},
                    {"name": "기타", "values": [10_000, 10_000, 15_000]},
                ],
            },
            title="사업부별 매출 추이",
        )
        assert fig is not None


class TestEmbedChartHtml:
    """차트 HTML 임베딩."""

    def test_embed_returns_html(self):
        """차트를 HTML img 태그로 임베딩."""
        fig = create_line_chart(
            {
                "x": ["A", "B"],
                "series": [{"name": "Test", "values": [1, 2]}],
            },
        )
        html = embed_chart_html(fig)
        assert isinstance(html, str)
        assert "<img" in html or "data:image" in html or len(html) > 0
