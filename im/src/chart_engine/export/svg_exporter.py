"""SVG 내보내기 — Plotly (Kaleido) + Graphviz.

> 마지막 수정: 2026-02-10 13:45:13

PDF 인라인 삽입용 SVG 문자열을 생성한다.
"""

from __future__ import annotations

import logging
from typing import Any

import plotly.graph_objects as go

from src.chart_engine.exceptions import ExportError

logger = logging.getLogger(__name__)


def plotly_to_svg(fig: go.Figure) -> str:
    """Plotly Figure → SVG 문자열.

    Args:
        fig: Plotly Figure.

    Returns:
        SVG 문자열.

    Raises:
        ExportError: Kaleido 변환 실패 시.
    """
    try:
        svg_bytes = fig.to_image(format="svg")
        return svg_bytes.decode("utf-8")
    except Exception as e:
        raise ExportError("svg", f"Plotly→SVG 변환 실패: {e}") from e


def graphviz_to_svg(graph: Any) -> str:
    """Graphviz Digraph → SVG 문자열 (XML 선언 제거, 인라인 삽입용).

    Args:
        graph: graphviz.Digraph | graphviz.Graph 객체.

    Returns:
        SVG 문자열 (<?xml ...?> 선언 제거됨).

    Raises:
        ExportError: Graphviz 렌더링 실패 시.
    """
    try:
        svg_bytes = graph.pipe(format="svg")
        svg_str = svg_bytes.decode("utf-8")

        # XML 선언 제거 (인라인 삽입용)
        if svg_str.startswith("<?xml"):
            svg_str = svg_str[svg_str.index("?>") + 2 :].strip()

        return svg_str
    except Exception as e:
        raise ExportError("svg", f"Graphviz→SVG 렌더링 실패: {e}") from e
