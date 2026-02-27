"""금융 차트 생성 모듈 — chart_engine 위임 어댑터.

> 마지막 수정: 2026-02-27 10:28:00

IM 문서에 필수적인 금융 차트 유형을 명시적으로 지원한다.
실제 차트 생성 로직은 chart_engine 모듈에 위임하고,
이 파일은 IMDesignTokens → ChartConfig 변환 + PPTX/PDF 임베딩만 담당.

하이브리드 전략:
- stacked_bar, donut, line, hbar → 네이티브 PPTX 차트 (편집 가능)
- combo, waterfall, heatmap 등 → Plotly → PNG 래스터 (기존 방식 유지)
"""

from __future__ import annotations

import base64
import logging
from io import BytesIO
from typing import Any

import plotly.graph_objects as go

from src.chart_engine.config import (
    ChartConfig,
    DEFAULT_WIDTH,
    DEFAULT_HEIGHT,
    chart_config_from_design_tokens,
)
from src.chart_engine.export.png_exporter import plotly_to_png as _ce_plotly_to_png
from src.chart_engine.plotly import (
    create_combo_chart as _ce_combo,
    create_donut_chart as _ce_donut,
    create_hbar_chart as _ce_hbar,
    create_line_chart as _ce_line,
    create_stacked_bar_chart as _ce_stacked_bar,
    create_waterfall_chart as _ce_waterfall,
)
from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import ChartData
from src.design_renderer.image_optimizer import compress_png

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# IMDesignTokens → ChartConfig 변환
# ---------------------------------------------------------------------------


def _tokens_to_config(
    tokens: IMDesignTokens | None = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> ChartConfig:
    """IMDesignTokens → ChartConfig (chart_engine 공통 어댑터 위임)."""
    tokens = tokens or DEFAULT_TOKENS
    cfg = chart_config_from_design_tokens(tokens)
    if width != DEFAULT_WIDTH or height != DEFAULT_HEIGHT:
        cfg = ChartConfig(colors=cfg.colors, width=width, height=height, font=cfg.font)
    return cfg


# ---------------------------------------------------------------------------
# 6종 차트 생성 (기존 시그니처 유지)
# ---------------------------------------------------------------------------


def create_waterfall_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    tokens: IMDesignTokens | None = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> go.Figure:
    """Waterfall chart (영업이익 Bridge)."""
    return _ce_waterfall(data, title=title, config=_tokens_to_config(tokens, width, height))


def create_combo_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    tokens: IMDesignTokens | None = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> go.Figure:
    """Dual-Axis Combo chart (막대 + 꺾은선)."""
    return _ce_combo(data, title=title, config=_tokens_to_config(tokens, width, height))


def create_stacked_bar_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    tokens: IMDesignTokens | None = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> go.Figure:
    """Stacked Bar chart (사업부별 매출 구성)."""
    return _ce_stacked_bar(data, title=title, config=_tokens_to_config(tokens, width, height))


def create_donut_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    tokens: IMDesignTokens | None = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> go.Figure:
    """Donut chart (시장 점유율)."""
    return _ce_donut(data, title=title, config=_tokens_to_config(tokens, width, height))


def create_line_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    tokens: IMDesignTokens | None = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> go.Figure:
    """Multi-series Line chart (KPI 추이)."""
    return _ce_line(data, title=title, config=_tokens_to_config(tokens, width, height))


def create_hbar_chart(
    data: dict[str, Any],
    *,
    title: str = "",
    tokens: IMDesignTokens | None = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> go.Figure:
    """Horizontal Bar chart (경쟁사 비교)."""
    return _ce_hbar(data, title=title, config=_tokens_to_config(tokens, width, height))


# ---------------------------------------------------------------------------
# 범용 디스패처
# ---------------------------------------------------------------------------

_CHART_DISPATCH: dict[str, Any] = {
    "waterfall": create_waterfall_chart,
    "combo": create_combo_chart,
    "stacked_bar": create_stacked_bar_chart,
    "donut": create_donut_chart,
    "line": create_line_chart,
    "hbar": create_hbar_chart,
}


def create_chart(
    chart_data: ChartData,
    *,
    tokens: IMDesignTokens | None = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> go.Figure:
    """ChartData.chart_type에 따라 적절한 차트 생성 함수 디스패치."""
    creator = _CHART_DISPATCH.get(chart_data.chart_type)
    if creator is None:
        raise ValueError(
            f"지원하지 않는 차트 유형: '{chart_data.chart_type}'. "
            f"지원 유형: {list(_CHART_DISPATCH.keys())}"
        )

    return creator(
        chart_data.data,
        title=chart_data.title,
        tokens=tokens,
        width=width,
        height=height,
    )


# ---------------------------------------------------------------------------
# 차트 임베딩 (PPTX / HTML)
# ---------------------------------------------------------------------------


def chart_to_png_bytes(
    fig: go.Figure,
    *,
    scale: int = 3,
    optimize: bool = True,
) -> bytes:
    """Plotly Figure를 PNG 바이트로 변환.

    Args:
        fig: Plotly Figure.
        scale: DPI 스케일.
        optimize: True이면 PNG 양자화 + 압축 최적화.
    """
    png_bytes = _ce_plotly_to_png(fig, scale=scale)
    if optimize:
        png_bytes = compress_png(png_bytes)
    return png_bytes


def embed_chart_pptx(
    slide: Any,
    fig: go.Figure,
    *,
    left: float = 0.5,
    top: float = 1.5,
    width: float = 9.0,
    height: float = 4.5,
    optimize: bool = True,
) -> None:
    """Plotly Figure를 300DPI PNG로 변환하여 PPTX 슬라이드에 삽입."""
    from pptx.util import Inches

    png_bytes = chart_to_png_bytes(fig, optimize=optimize)
    buf = BytesIO(png_bytes)

    slide.shapes.add_picture(
        buf, Inches(left), Inches(top), Inches(width), Inches(height)
    )


def embed_chart_native_or_image(
    slide: Any,
    chart_data: ChartData,
    *,
    left: float = 0.5,
    top: float = 1.5,
    width: float = 9.0,
    height: float = 4.5,
    tokens: IMDesignTokens | None = None,
    optimize: bool = True,
) -> Any:
    """차트 타입에 따라 네이티브 PPTX 또는 PNG 이미지로 자동 분기.

    - stacked_bar, donut, line, hbar → 네이티브 PPTX 차트 (편집 가능)
    - combo, waterfall, heatmap 등 → Plotly → PNG 래스터 (기존)

    Args:
        slide: python-pptx Slide 객체.
        chart_data: ChartData (chart_type, title, data).
        left/top/width/height: 슬라이드 내 위치 (인치).
        tokens: IMDesignTokens (색상/폰트).
        optimize: PNG 최적화 여부 (래스터 경로만 해당).

    Returns:
        네이티브 chart shape 또는 None (이미지 삽입 시).
    """
    from src.chart_engine.pptx_native import get_native_builder

    builder = get_native_builder(chart_data.chart_type)
    if builder is not None:
        cfg = _tokens_to_config(tokens)
        return builder.build(
            slide,
            chart_data.data,
            title=chart_data.title,
            left=left,
            top=top,
            width=width,
            height=height,
            config=cfg,
        )

    # 네이티브 미지원 → 기존 Plotly → PNG 경로
    fig = create_chart(chart_data, tokens=tokens)
    embed_chart_pptx(slide, fig, left=left, top=top, width=width, height=height, optimize=optimize)
    return None


def embed_chart_html(
    fig: go.Figure,
    *,
    width: str = "100%",
    alt: str = "Chart",
    optimize: bool = True,
) -> str:
    """Plotly Figure를 base64 PNG <img> 태그로 변환."""
    png_bytes = chart_to_png_bytes(fig, optimize=optimize)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return (
        f'<div class="chart-container">'
        f'<img src="data:image/png;base64,{b64}" '
        f'alt="{alt}" style="width: {width};" />'
        f"</div>"
    )
