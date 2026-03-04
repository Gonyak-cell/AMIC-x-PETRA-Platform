"""바 차트 생성 서비스.

Plotly go.Bar를 사용하여 범주별 비교 차트를 생성합니다.
"""

from decimal import Decimal
from io import BytesIO
from typing import Any

import plotly.graph_objects as go
import plotly.io as pio

from app.renderers.design_system import get_chart_style, get_colors, get_fonts


def create_bar_chart(
    categories: list[str],
    values: list[Decimal | float | None],
    title: str = "Bar Chart",
    y_axis_title: str = "Value",
    color: str | None = None,
    horizontal: bool = False,
    design_override: dict[str, Any] | None = None,
) -> BytesIO:
    """단일 시리즈 바 차트를 생성합니다.

    Args:
        categories: 범주 레이블 리스트
        values: 각 범주의 값 리스트
        title: 차트 제목
        y_axis_title: Y축 제목 (수직 차트) 또는 X축 제목 (수평 차트)
        color: 바 색상 (None이면 기본 primary)
        horizontal: 수평 바 차트 여부
        design_override: Design System 설정 오버라이드

    Returns:
        PNG 이미지 BytesIO 버퍼

    Example:
        >>> buffer = create_bar_chart(
        ...     categories=["Q1", "Q2", "Q3", "Q4"],
        ...     values=[Decimal("100"), Decimal("120"), Decimal("110"), Decimal("130")],
        ...     title="Quarterly Revenue"
        ... )
    """
    colors = get_colors()
    fonts = get_fonts()
    bar_style = get_chart_style("bar") if get_chart_style("bar") else {}

    if design_override:
        bar_style = {**bar_style, **design_override}

    bar_color = color or colors.get("primary", "#003366")

    # Decimal → float 변환
    float_values = [float(v) if v is not None else None for v in values]

    # 텍스트 레이블
    text_labels = []
    for v in float_values:
        if v is None:
            text_labels.append("")
        elif v >= 0:
            text_labels.append(f"{v:,.0f}")
        else:
            text_labels.append(f"({abs(v):,.0f})")

    if horizontal:
        fig = go.Figure(
            go.Bar(
                y=categories,
                x=float_values,
                orientation="h",
                marker_color=bar_color,
                text=text_labels,
                textposition="outside",
            )
        )
    else:
        fig = go.Figure(
            go.Bar(
                x=categories,
                y=float_values,
                marker_color=bar_color,
                text=text_labels,
                textposition="outside",
            )
        )

    fig.update_layout(
        title={
            "text": title,
            "font": {
                "family": fonts.get("heading", "맑은 고딕"),
                "size": bar_style.get("title_size", 14),
                "color": colors.get("primary", "#003366"),
            },
            "x": 0.5,
            "xanchor": "center",
        },
        font={"family": bar_style.get("font_family", "맑은 고딕")},
        plot_bgcolor=bar_style.get("background", "white"),
        paper_bgcolor="white",
        showlegend=False,
        width=900,
        height=500,
        margin={"t": 60, "b": 60, "l": 80, "r": 40},
    )

    if horizontal:
        fig.update_layout(
            xaxis={
                "title": y_axis_title,
                "gridcolor": bar_style.get("grid_color", "#E0E0E0"),
            },
            yaxis={"title": ""},
        )
    else:
        fig.update_layout(
            xaxis={"title": ""},
            yaxis={
                "title": y_axis_title,
                "gridcolor": bar_style.get("grid_color", "#E0E0E0"),
            },
        )

    buffer = BytesIO()
    pio.write_image(fig, buffer, format="png", scale=2)
    buffer.seek(0)
    return buffer


def create_grouped_bar_chart(
    categories: list[str],
    series: list[dict[str, Any]],
    title: str = "Grouped Bar Chart",
    y_axis_title: str = "Value",
    design_override: dict[str, Any] | None = None,
) -> BytesIO:
    """그룹 바 차트 (다중 시리즈)를 생성합니다.

    Args:
        categories: 범주 레이블 리스트
        series: 시리즈 데이터 리스트
            [{"name": "2024", "values": [100, 110], "color": "#003366"}, ...]
        title: 차트 제목
        y_axis_title: Y축 제목
        design_override: Design System 설정 오버라이드

    Returns:
        PNG 이미지 BytesIO 버퍼
    """
    colors = get_colors()
    fonts = get_fonts()
    bar_style = get_chart_style("bar") if get_chart_style("bar") else {}

    if design_override:
        bar_style = {**bar_style, **design_override}

    # 기본 색상 팔레트
    color_palette = [
        colors.get("primary", "#003366"),
        colors.get("positive", "#2E7D32"),
        colors.get("negative", "#E0301E"),
        "#FF9800",
        "#9C27B0",
    ]

    fig = go.Figure()

    for idx, s in enumerate(series):
        name = s.get("name", f"Series {idx + 1}")
        values = s.get("values", [])
        color = s.get("color", color_palette[idx % len(color_palette)])

        float_values = [float(v) if v is not None else None for v in values]

        fig.add_trace(
            go.Bar(
                x=categories,
                y=float_values,
                name=name,
                marker_color=color,
            )
        )

    fig.update_layout(
        title={
            "text": title,
            "font": {
                "family": fonts.get("heading", "맑은 고딕"),
                "size": bar_style.get("title_size", 14),
                "color": colors.get("primary", "#003366"),
            },
            "x": 0.5,
            "xanchor": "center",
        },
        font={"family": bar_style.get("font_family", "맑은 고딕")},
        plot_bgcolor=bar_style.get("background", "white"),
        paper_bgcolor="white",
        barmode="group",
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.2,
            "xanchor": "center",
            "x": 0.5,
        },
        width=900,
        height=500,
        margin={"t": 60, "b": 80, "l": 60, "r": 40},
        yaxis={
            "title": y_axis_title,
            "gridcolor": bar_style.get("grid_color", "#E0E0E0"),
        },
    )

    buffer = BytesIO()
    pio.write_image(fig, buffer, format="png", scale=2)
    buffer.seek(0)
    return buffer


def create_stacked_bar_chart(
    categories: list[str],
    series: list[dict[str, Any]],
    title: str = "Stacked Bar Chart",
    y_axis_title: str = "Value",
    design_override: dict[str, Any] | None = None,
) -> BytesIO:
    """누적 바 차트를 생성합니다.

    Args:
        categories: 범주 레이블 리스트
        series: 시리즈 데이터 리스트
        title: 차트 제목
        y_axis_title: Y축 제목
        design_override: Design System 설정 오버라이드

    Returns:
        PNG 이미지 BytesIO 버퍼
    """
    colors = get_colors()
    fonts = get_fonts()
    bar_style = get_chart_style("bar") if get_chart_style("bar") else {}

    if design_override:
        bar_style = {**bar_style, **design_override}

    color_palette = [
        colors.get("primary", "#003366"),
        colors.get("positive", "#2E7D32"),
        "#FF9800",
        "#9C27B0",
        "#00BCD4",
    ]

    fig = go.Figure()

    for idx, s in enumerate(series):
        name = s.get("name", f"Series {idx + 1}")
        values = s.get("values", [])
        color = s.get("color", color_palette[idx % len(color_palette)])

        float_values = [float(v) if v is not None else None for v in values]

        fig.add_trace(
            go.Bar(
                x=categories,
                y=float_values,
                name=name,
                marker_color=color,
            )
        )

    fig.update_layout(
        title={
            "text": title,
            "font": {
                "family": fonts.get("heading", "맑은 고딕"),
                "size": bar_style.get("title_size", 14),
                "color": colors.get("primary", "#003366"),
            },
            "x": 0.5,
            "xanchor": "center",
        },
        font={"family": bar_style.get("font_family", "맑은 고딕")},
        plot_bgcolor=bar_style.get("background", "white"),
        paper_bgcolor="white",
        barmode="stack",
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.2,
            "xanchor": "center",
            "x": 0.5,
        },
        width=900,
        height=500,
        margin={"t": 60, "b": 80, "l": 60, "r": 40},
        yaxis={
            "title": y_axis_title,
            "gridcolor": bar_style.get("grid_color", "#E0E0E0"),
        },
    )

    buffer = BytesIO()
    pio.write_image(fig, buffer, format="png", scale=2)
    buffer.seek(0)
    return buffer
