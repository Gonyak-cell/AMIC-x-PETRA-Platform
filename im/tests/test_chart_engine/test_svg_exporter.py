"""SVG 내보내기 단위 테스트.

> 마지막 수정: 2026-02-10 13:45:13
"""

from unittest.mock import MagicMock

import pytest

from src.chart_engine.exceptions import ExportError
from src.chart_engine.export.svg_exporter import graphviz_to_svg, plotly_to_svg


class TestPlotlyToSvg:
    """Plotly → SVG."""

    @pytest.mark.requires_plotly
    def test_returns_svg_string(self):
        """SVG 문자열 반환."""
        import plotly.graph_objects as go

        fig = go.Figure(go.Bar(x=["A", "B"], y=[1, 2]))
        svg = plotly_to_svg(fig)
        assert isinstance(svg, str)
        assert "<svg" in svg

    def test_export_error_on_failure(self):
        """변환 실패 시 ExportError."""
        mock_fig = MagicMock()
        mock_fig.to_image.side_effect = Exception("Kaleido 오류")
        with pytest.raises(ExportError, match="svg"):
            plotly_to_svg(mock_fig)


class TestGraphvizToSvg:
    """Graphviz → SVG."""

    def test_returns_svg_string(self):
        """SVG 문자열 반환 (XML 선언 제거)."""
        mock_graph = MagicMock()
        mock_graph.pipe.return_value = b'<?xml version="1.0" encoding="UTF-8"?>\n<svg width="100" height="100"></svg>'
        result = graphviz_to_svg(mock_graph)
        assert isinstance(result, str)
        assert "<?xml" not in result
        assert "<svg" in result

    def test_no_xml_declaration_passthrough(self):
        """XML 선언이 없는 SVG도 정상 처리."""
        mock_graph = MagicMock()
        mock_graph.pipe.return_value = b'<svg width="100"></svg>'
        result = graphviz_to_svg(mock_graph)
        assert "<svg" in result

    def test_export_error_on_failure(self):
        """렌더링 실패 시 ExportError."""
        mock_graph = MagicMock()
        mock_graph.pipe.side_effect = Exception("graphviz 없음")
        with pytest.raises(ExportError, match="svg"):
            graphviz_to_svg(mock_graph)
