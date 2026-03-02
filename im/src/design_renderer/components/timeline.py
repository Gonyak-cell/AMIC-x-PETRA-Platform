"""기업 연혁 타임라인 시각화 — Matplotlib/SVG 기반.

CompanyOverview.history 데이터를 수평/수직 타임라인으로 변환하여
PPTX (PNG 삽입) 및 PDF (SVG 인라인) 듀얼 출력을 지원한다.
"""

from __future__ import annotations

import logging
from io import BytesIO
from typing import TYPE_CHECKING, Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Matplotlib 비인터랙티브 백엔드 — use() 후 pyplot import 필수
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as _plt  # noqa: E402


def _get_plt():
    """Matplotlib pyplot 반환."""
    return _plt


def _setup_font(tokens: IMDesignTokens) -> None:
    """Matplotlib 한글 폰트 설정."""
    import matplotlib.font_manager as fm

    # 시스템 폰트에서 NanumGothic 또는 Pretendard 검색
    for font_name in [tokens.typography.font_chart, tokens.typography.font_body]:
        fonts = fm.findSystemFonts()
        for f in fonts:
            try:
                prop = fm.FontProperties(fname=f)
                if font_name.lower() in prop.get_name().lower():
                    matplotlib.rcParams["font.family"] = prop.get_name()
                    matplotlib.rcParams["axes.unicode_minus"] = False
                    return
            except Exception:
                continue

    # 폴백: 기본 sans-serif
    matplotlib.rcParams["axes.unicode_minus"] = False


def create_timeline_figure(
    events: list[dict[str, str]],
    *,
    orientation: str = "horizontal",
    tokens: IMDesignTokens | None = None,
    width: float = 9.0,
    height: float = 2.5,
) -> Any:
    """연혁 타임라인 Matplotlib Figure 생성.

    Args:
        events: [{"year": "2005", "event": "설립"}, ...]
            year 기준으로 자동 정렬.
        orientation: "horizontal" (기본) 또는 "vertical".
        tokens: 디자인 토큰.
        width, height: Figure 크기 (inches).

    Returns:
        matplotlib.figure.Figure 객체.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    _setup_font(tokens)
    plt = _get_plt()

    if not events:
        fig, ax = plt.subplots(figsize=(width, height))
        ax.text(0.5, 0.5, "No timeline data", ha="center", va="center")
        ax.set_axis_off()
        return fig

    # 연도 기준 정렬
    sorted_events = sorted(events, key=lambda e: e.get("year", "0"))

    fig, ax = plt.subplots(figsize=(width, height))

    if orientation == "vertical":
        _render_vertical_timeline(ax, sorted_events, tokens)
    else:
        _render_horizontal_timeline(ax, sorted_events, tokens)

    fig.tight_layout(pad=0.5)
    return fig


def _render_horizontal_timeline(
    ax: Any,
    events: list[dict[str, str]],
    tokens: IMDesignTokens,
) -> None:
    """수평 타임라인: x축=연도, 이벤트는 위/아래 교대 배치."""
    c = tokens.colors
    n = len(events)
    x_positions = list(range(n))

    # 타임라인 선
    ax.plot(
        x_positions,
        [0] * n,
        color=c.primary,
        linewidth=2,
        zorder=1,
    )

    # 이벤트 마커 + 라벨
    for i, evt in enumerate(events):
        year = evt.get("year", "")
        event_text = evt.get("event", "")

        # 마커
        ax.scatter(i, 0, s=80, color=c.accent, zorder=2, edgecolors=c.primary)

        # 연도 라벨 (아래)
        ax.text(
            i,
            -0.15,
            year,
            ha="center",
            va="top",
            fontsize=8,
            fontweight="bold",
            color=c.primary,
        )

        # 이벤트 텍스트 (위/아래 교대)
        y_offset = 0.2 if i % 2 == 0 else -0.35
        va = "bottom" if i % 2 == 0 else "top"
        ax.text(
            i,
            y_offset,
            event_text,
            ha="center",
            va=va,
            fontsize=7,
            color=c.text_body,
            wrap=True,
        )

    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(-0.6, 0.6)
    ax.set_axis_off()


def _render_vertical_timeline(
    ax: Any,
    events: list[dict[str, str]],
    tokens: IMDesignTokens,
) -> None:
    """수직 타임라인: y축=연도(역순), 이벤트는 오른쪽."""
    c = tokens.colors
    n = len(events)
    y_positions = list(range(n - 1, -1, -1))

    # 타임라인 선
    ax.plot(
        [0] * n,
        y_positions,
        color=c.primary,
        linewidth=2,
        zorder=1,
    )

    for i, evt in enumerate(events):
        year = evt.get("year", "")
        event_text = evt.get("event", "")
        y = y_positions[i]

        # 마커
        ax.scatter(0, y, s=80, color=c.accent, zorder=2, edgecolors=c.primary)

        # 연도 (왼쪽)
        ax.text(
            -0.3,
            y,
            year,
            ha="right",
            va="center",
            fontsize=9,
            fontweight="bold",
            color=c.primary,
        )

        # 이벤트 (오른쪽)
        ax.text(
            0.3,
            y,
            event_text,
            ha="left",
            va="center",
            fontsize=8,
            color=c.text_body,
        )

    ax.set_xlim(-1.5, 5)
    ax.set_ylim(-0.5, n - 0.5)
    ax.set_axis_off()


# ---------------------------------------------------------------------------
# PPTX 삽입
# ---------------------------------------------------------------------------


def render_timeline_pptx(
    slide: Any,
    events: list[dict[str, str]],
    *,
    left: float = 0.5,
    top: float = 2.0,
    width: float = 9.0,
    height: float = 2.5,
    orientation: str = "horizontal",
    tokens: IMDesignTokens | None = None,
) -> None:
    """타임라인을 PNG로 변환하여 PPTX 슬라이드에 삽입.

    Args:
        slide: pptx.slide.Slide 인스턴스.
        events: 연혁 이벤트 리스트.
        left, top, width, height: 위치/크기 (inches).
        orientation: "horizontal" | "vertical".
        tokens: 디자인 토큰.
    """
    from pptx.util import Inches

    fig = create_timeline_figure(
        events,
        orientation=orientation,
        tokens=tokens,
        width=width,
        height=height,
    )

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches="tight", transparent=True)
    _get_plt().close(fig)
    buf.seek(0)

    slide.shapes.add_picture(
        buf, Inches(left), Inches(top), Inches(width), Inches(height)
    )


# ---------------------------------------------------------------------------
# HTML/SVG 인라인
# ---------------------------------------------------------------------------


def render_timeline_html(
    events: list[dict[str, str]],
    *,
    orientation: str = "horizontal",
    tokens: IMDesignTokens | None = None,
    width: float = 9.0,
    height: float = 2.5,
) -> str:
    """타임라인을 SVG 인라인으로 변환하여 HTML 반환.

    PDF 출력에서는 SVG가 벡터로 렌더링되어 최적.

    Args:
        events: 연혁 이벤트 리스트.
        orientation: "horizontal" | "vertical".
        tokens: 디자인 토큰.

    Returns:
        인라인 SVG HTML 문자열.
    """
    fig = create_timeline_figure(
        events,
        orientation=orientation,
        tokens=tokens,
        width=width,
        height=height,
    )

    buf = BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", transparent=True)
    _get_plt().close(fig)
    buf.seek(0)

    svg_str = buf.getvalue().decode("utf-8")

    # XML 선언 제거 (인라인 삽입용)
    if svg_str.startswith("<?xml"):
        svg_str = svg_str[svg_str.index("?>") + 2 :].strip()

    return f'<div class="timeline-container">{svg_str}</div>'
