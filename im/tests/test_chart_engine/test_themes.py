"""AMICThemeFactory 단위 테스트.

> 마지막 수정: 2026-02-10 13:45:13
"""

import pytest

from src.chart_engine.config import ChartColorConfig, ChartConfig
from src.chart_engine.plotly.themes import AMICThemeFactory

pytestmark = pytest.mark.requires_plotly


class TestAMICThemeFactory:
    """AMIC 테마 팩토리."""

    def test_apply_layout_sets_font(self):
        """apply_layout 적용 후 폰트 확인."""
        import plotly.graph_objects as go

        theme = AMICThemeFactory()
        fig = go.Figure(go.Bar(x=["A"], y=[1]))
        theme.apply_layout(fig, title="테스트")

        assert fig.layout.font.family == "Noto Sans KR"
        assert fig.layout.title.text == "테스트"

    def test_apply_layout_custom_size(self):
        """커스텀 너비/높이 적용."""
        import plotly.graph_objects as go

        theme = AMICThemeFactory()
        fig = go.Figure(go.Bar(x=["A"], y=[1]))
        theme.apply_layout(fig, width=1200, height=600)

        assert fig.layout.width == 1200
        assert fig.layout.height == 600

    def test_color_sequence_length(self):
        """컬러 시퀀스 6개 이상 반환."""
        theme = AMICThemeFactory()
        colors = theme.get_color_sequence()
        assert len(colors) >= 6
        assert colors[0] == "#0F3A32"  # primary

    def test_semantic_colors(self):
        """시맨틱 색상 맵 반환."""
        theme = AMICThemeFactory()
        sc = theme.get_semantic_colors()
        assert "positive" in sc
        assert "negative" in sc
        assert "caution" in sc

    def test_custom_config_applied(self):
        """커스텀 config의 색상이 테마에 반영."""
        custom = ChartConfig(
            colors=ChartColorConfig(primary="#FF0000"),
        )
        theme = AMICThemeFactory(custom)
        colors = theme.get_color_sequence()
        assert colors[0] == "#FF0000"
