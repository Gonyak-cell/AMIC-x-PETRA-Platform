"""라인 차트 생성 서비스.

Plotly go.Scatter를 사용하여 시계열 트렌드 차트를 생성합니다.
"""

from decimal import Decimal
from io import BytesIO
from typing import Any

import plotly.graph_objects as go
import plotly.io as pio

from app.renderers.design_system import get_chart_style, get_colors, get_fonts


def create_trend_chart(
    categories: list[str],
    series: list[dict[str, Any]],
    title: str = "Trend Chart",
    y_axis_title: str = "Value",
    design_override: dict[str, Any] | None = None,
) -> BytesIO:
    """시계열 트렌드 라인 차트를 생성합니다.

    Args:
        categories: X축 레이블 리스트 (예: ["2024-01", "2024-02", ...])
        series: 시리즈 데이터 리스트
            [{"name": "Revenue", "values": [100, 110, 120], "color": "#003366"}, ...]
        title: 차트 제목
        y_axis_title: Y축 제목
        design_override: Design System 설정 오버라이드

    Returns:
        PNG 이미지 BytesIO 버퍼

    Example:
        >>> buffer = create_trend_chart(
        ...     categories=["Jan", "Feb", "Mar", "Apr"],
        ...     series=[
        ...         {"name": "Revenue", "values": [100, 110, 105, 120]},
        ...         {"name": "EBITDA", "values": [20, 22, 21, 25]},
        ...     ],
        ...     title="Monthly Performance"
        ... )
    """
    colors = get_colors()
    fonts = get_fonts()
    line_style = get_chart_style("line") if get_chart_style("line") else {}

    if design_override:
        line_style = {**line_style, **design_override}

    # 기본 색상 팔레트
    color_palette = [
        colors.get("primary", "#003366"),
        colors.get("positive", "#2E7D32"),
        colors.get("negative", "#E0301E"),
        "#FF9800",  # Orange
        "#9C27B0",  # Purple
        "#00BCD4",  # Cyan
    ]

    fig = go.Figure()

    for idx, s in enumerate(series):
        name = s.get("name", f"Series {idx + 1}")
        values = s.get("values", [])
        color = s.get("color", color_palette[idx % len(color_palette)])

        # Decimal → float 변환
        float_values = [float(v) if v is not None else None for v in values]

        fig.add_trace(
            go.Scatter(
                x=categories,
                y=float_values,
                mode="lines+markers",
                name=name,
                line={"color": color, "width": 2},
                marker={"size": 6, "color": color},
            )
        )

    fig.update_layout(
        title={
            "text": title,
            "font": {
                "family": fonts.get("heading", "맑은 고딕"),
                "size": line_style.get("title_size", 14),
                "color": colors.get("primary", "#003366"),
            },
            "x": 0.5,
            "xanchor": "center",
        },
        font={"family": line_style.get("font_family", "맑은 고딕")},
        plot_bgcolor=line_style.get("background", "white"),
        paper_bgcolor="white",
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.2, "xanchor": "center", "x": 0.5},
        width=900,
        height=500,
        margin={"t": 60, "b": 80, "l": 60, "r": 40},
        xaxis={"title": "", "gridcolor": line_style.get("grid_color", "#E0E0E0")},
        yaxis={
            "title": y_axis_title,
            "gridcolor": line_style.get("grid_color", "#E0E0E0"),
            "zeroline": True,
            "zerolinecolor": "#999999",
        },
    )

    buffer = BytesIO()
    pio.write_image(fig, buffer, format="png", scale=2)
    buffer.seek(0)
    return buffer


def create_single_line_chart(
    categories: list[str],
    values: list[Decimal | float | None],
    title: str = "Line Chart",
    series_name: str = "Value",
    y_axis_title: str = "Value",
    color: str | None = None,
    design_override: dict[str, Any] | None = None,
) -> BytesIO:
    """단일 시리즈 라인 차트를 생성합니다.

    Args:
        categories: X축 레이블 리스트
        values: Y축 값 리스트
        title: 차트 제목
        series_name: 시리즈 이름
        y_axis_title: Y축 제목
        color: 라인 색상 (None이면 기본 primary)
        design_override: Design System 설정 오버라이드

    Returns:
        PNG 이미지 BytesIO 버퍼
    """
    colors = get_colors()
    line_color = color or colors.get("primary", "#003366")

    return create_trend_chart(
        categories=categories,
        series=[{"name": series_name, "values": values, "color": line_color}],
        title=title,
        y_axis_title=y_axis_title,
        design_override=design_override,
    )
