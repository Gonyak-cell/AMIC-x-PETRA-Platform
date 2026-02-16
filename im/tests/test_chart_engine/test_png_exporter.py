"""PNG 내보내기 단위 테스트.

> 마지막 수정: 2026-02-10 13:45:13
"""

from unittest.mock import MagicMock, patch

import pytest

from src.chart_engine.exceptions import ExportError
from src.chart_engine.export.png_exporter import graphviz_to_png, plotly_to_png


class TestPlotlyToPng:
    """Plotly → PNG."""

    @pytest.mark.requires_plotly
    def test_returns_png_bytes(self):
        """PNG 바이트 반환 (PNG 매직 바이트 확인)."""
        import plotly.graph_objects as go

        fig = go.Figure(go.Bar(x=["A", "B"], y=[1, 2]))
        png = plotly_to_png(fig)
        assert isinstance(png, bytes)
        assert len(png) > 0
        # PNG 매직 바이트: \x89PNG
        assert png[:4] == b"\x89PNG"

    @pytest.mark.requires_plotly
    def test_custom_scale(self):
        """커스텀 스케일 적용."""
        import plotly.graph_objects as go

        fig = go.Figure(go.Bar(x=["A"], y=[1]))
        png = plotly_to_png(fig, scale=1)
        assert isinstance(png, bytes)
        assert len(png) > 0

    def test_export_error_on_failure(self):
        """변환 실패 시 ExportError."""
        mock_fig = MagicMock()
        mock_fig.to_image.side_effect = Exception("Kaleido 오류")
        with pytest.raises(ExportError, match="png"):
            plotly_to_png(mock_fig)


class TestGraphvizToPng:
    """Graphviz → PNG."""

    def test_returns_bytes(self):
        """Graphviz PNG 바이트 반환."""
        mock_graph = MagicMock()
        mock_graph.graph_attr = {}
        mock_graph.pipe.return_value = b"\x89PNG\r\n\x1a\nfakedata"
        result = graphviz_to_png(mock_graph, dpi=300)
        assert result.startswith(b"\x89PNG")
        mock_graph.pipe.assert_called_once_with(format="png")

    def test_dpi_applied(self):
        """DPI 설정 확인."""
        mock_graph = MagicMock()
        mock_graph.graph_attr = {}
        mock_graph.pipe.return_value = b"fake"
        graphviz_to_png(mock_graph, dpi=150)
        assert mock_graph.graph_attr["dpi"] == "150"

    def test_export_error_on_failure(self):
        """렌더링 실패 시 ExportError."""
        mock_graph = MagicMock()
        mock_graph.graph_attr = {}
        mock_graph.pipe.side_effect = Exception("graphviz 없음")
        with pytest.raises(ExportError, match="png"):
            graphviz_to_png(mock_graph)
