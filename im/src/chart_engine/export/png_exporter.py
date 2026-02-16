"""PNG 내보내기 — Plotly (Kaleido) + Graphviz.

> 마지막 수정: 2026-02-11 22:00:00

300 DPI 고해상도 PNG 이미지로 내보낸다.
"""

from __future__ import annotations

import logging
from typing import Any

import plotly.graph_objects as go

from src.chart_engine.config import ChartConfig, DEFAULT_CHART_CONFIG
from src.chart_engine.exceptions import ExportError

logger = logging.getLogger(__name__)


def plotly_to_png(
    fig: go.Figure,
    *,
    scale: int | None = None,
    config: ChartConfig | None = None,
    compress: bool = False,
) -> bytes:
    """Plotly Figure → PNG bytes (300 DPI).

    Args:
        fig: Plotly Figure.
        scale: DPI 스케일 오버라이드 (None이면 config.dpi_scale).
        config: 차트 설정.
        compress: True이면 PNG 최적화 적용. 기본 False (하위 호환).

    Returns:
        PNG 이미지 바이트.

    Raises:
        ExportError: Kaleido 변환 실패 시.
    """
    cfg = config or DEFAULT_CHART_CONFIG
    s = scale if scale is not None else cfg.dpi_scale

    try:
        png_bytes = fig.to_image(format="png", scale=s)
    except Exception as e:
        raise ExportError("png", f"Plotly→PNG 변환 실패: {e}") from e

    if compress:
        try:
            from src.design_renderer.image_optimizer import compress_png

            png_bytes = compress_png(png_bytes)
        except ImportError:
            pass

    return png_bytes


def graphviz_to_png(
    graph: Any,
    *,
    dpi: int = 300,
    compress: bool = False,
) -> bytes:
    """Graphviz Digraph → PNG bytes.

    Args:
        graph: graphviz.Digraph | graphviz.Graph 객체.
        dpi: 해상도 (DPI).
        compress: True이면 PNG 최적화 적용. 기본 False (하위 호환).

    Returns:
        PNG 이미지 바이트.

    Raises:
        ExportError: Graphviz 렌더링 실패 시.
    """
    try:
        graph.graph_attr["dpi"] = str(dpi)
        png_bytes = graph.pipe(format="png")
    except Exception as e:
        raise ExportError("png", f"Graphviz→PNG 렌더링 실패: {e}") from e

    if compress:
        try:
            from src.design_renderer.image_optimizer import compress_png

            png_bytes = compress_png(png_bytes)
        except ImportError:
            pass

    return png_bytes
