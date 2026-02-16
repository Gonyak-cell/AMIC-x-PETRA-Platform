"""워터폴 차트 생성 서비스.

Plotly go.Waterfall을 사용하여 EBITDA Bridge 등 워터폴 차트를 생성합니다.
Design System 설정을 적용하여 Big 4 스타일의 일관된 차트를 생성합니다.
"""

from decimal import Decimal
from io import BytesIO
from typing import Any

import plotly.graph_objects as go
import plotly.io as pio

from app.renderers.design_system import get_chart_style, get_colors, get_fonts


def create_ebitda_bridge(
    categories: list[str],
    values: list[Decimal | None],
    title: str = "EBITDA Bridge",
    design_override: dict[str, Any] | None = None,
) -> BytesIO:
    """EBITDA Bridge 워터폴 차트를 생성합니다.

    첫 번째 항목은 Reported EBITDA (absolute),
    마지막 항목은 Adjusted EBITDA (total),
    중간 항목들은 조정 금액 (relative)으로 처리됩니다.

    Args:
        categories: x축 레이블 리스트 (예: ["Reported", "일회성 조정", "비영업 조정", "Adjusted"])
        values: 각 항목의 금액 (Decimal). 마지막 total은 None 가능 (자동 계산됨)
        title: 차트 제목
        design_override: Design System 설정 오버라이드

    Returns:
        PNG 이미지 BytesIO 버퍼

    Example:
        >>> buffer = create_ebitda_bridge(
        ...     categories=["Reported EBITDA", "일회성 비용", "비영업 수익", "Adjusted EBITDA"],
        ...     values=[Decimal("1000"), Decimal("200"), Decimal("-50"), None],
        ...     title="FY2025 EBITDA Bridge"
        ... )
    """
    if len(categories) != len(values):
        raise ValueError("categories와 values의 길이가 일치해야 합니다")

    if len(categories) < 2:
        raise ValueError("최소 2개 이상의 항목이 필요합니다")

    # Design System에서 스타일 로드
    waterfall_style = get_chart_style("waterfall")
    colors = get_colors()
    fonts = get_fonts()

    # 오버라이드 적용
    if design_override:
        waterfall_style = {**waterfall_style, **design_override}

    # measure 타입 결정: absolute → relative... → total
    measures = ["absolute"] + ["relative"] * (len(values) - 2) + ["total"]

    # Decimal → float 변환 (Plotly는 Decimal 미지원)
    float_values: list[float | None] = []
    for v in values:
        if v is None:
            float_values.append(None)
        else:
            float_values.append(float(v))

    # 텍스트 레이블 (숫자 포맷팅)
    text_labels = []
    for v in float_values:
        if v is None:
            text_labels.append("")
        elif v >= 0:
            text_labels.append(f"{v:,.0f}")
        else:
            text_labels.append(f"({abs(v):,.0f})")

    # 워터폴 차트 생성
    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measures,
            x=categories,
            y=float_values,
            connector={
                "line": {
                    "color": waterfall_style.get("connector_color", "#666666"),
                    "dash": waterfall_style.get("connector_dash", "dot"),
                }
            },
            increasing={"marker": {"color": waterfall_style.get("increasing_color", colors.get("positive", "#2E7D32"))}},
            decreasing={"marker": {"color": waterfall_style.get("decreasing_color", colors.get("negative", "#E0301E"))}},
            totals={"marker": {"color": waterfall_style.get("total_color", colors.get("primary", "#003366"))}},
            textposition="outside",
            text=text_labels,
            textfont={"size": waterfall_style.get("label_size", 10)},
        )
    )

    # 레이아웃 설정
    fig.update_layout(
        title={
            "text": title,
            "font": {
                "family": fonts.get("heading", "맑은 고딕"),
                "size": waterfall_style.get("title_size", 14),
                "color": colors.get("primary", "#003366"),
            },
            "x": 0.5,
            "xanchor": "center",
        },
        font={"family": waterfall_style.get("font_family", "맑은 고딕")},
        plot_bgcolor=waterfall_style.get("background", "white"),
        paper_bgcolor="white",
        showlegend=False,
        width=900,
        height=500,
        margin={"t": 60, "b": 60, "l": 60, "r": 40},
        yaxis={
            "title": "금액 (백만원)",
            "gridcolor": waterfall_style.get("grid_color", "#E0E0E0"),
            "zeroline": True,
            "zerolinecolor": "#999999",
        },
    )

    # PNG로 내보내기 (300 DPI = scale 2)
    buffer = BytesIO()
    pio.write_image(fig, buffer, format="png", scale=2)
    buffer.seek(0)
    return buffer


def create_generic_waterfall(
    categories: list[str],
    values: list[Decimal | None],
    measures: list[str] | None = None,
    title: str = "Waterfall Chart",
    y_axis_title: str = "Value",
    design_override: dict[str, Any] | None = None,
) -> BytesIO:
    """범용 워터폴 차트를 생성합니다.

    Args:
        categories: x축 레이블 리스트
        values: 각 항목의 값 (Decimal). total 항목은 None 가능
        measures: 각 항목의 측정 타입 ("absolute", "relative", "total"). None이면 자동 결정
        title: 차트 제목
        y_axis_title: y축 제목
        design_override: Design System 설정 오버라이드

    Returns:
        PNG 이미지 BytesIO 버퍼
    """
    if len(categories) != len(values):
        raise ValueError("categories와 values의 길이가 일치해야 합니다")

    if measures and len(measures) != len(categories):
        raise ValueError("measures와 categories의 길이가 일치해야 합니다")

    # measures 자동 결정
    if measures is None:
        measures = ["absolute"] + ["relative"] * (len(values) - 2) + ["total"]

    # Design System에서 스타일 로드
    waterfall_style = get_chart_style("waterfall")
    colors = get_colors()
    fonts = get_fonts()

    if design_override:
        waterfall_style = {**waterfall_style, **design_override}

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

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measures,
            x=categories,
            y=float_values,
            connector={
                "line": {
                    "color": waterfall_style.get("connector_color", "#666666"),
                    "dash": waterfall_style.get("connector_dash", "dot"),
                }
            },
            increasing={"marker": {"color": waterfall_style.get("increasing_color", "#2E7D32")}},
            decreasing={"marker": {"color": waterfall_style.get("decreasing_color", "#E0301E")}},
            totals={"marker": {"color": waterfall_style.get("total_color", "#003366")}},
            textposition="outside",
            text=text_labels,
            textfont={"size": waterfall_style.get("label_size", 10)},
        )
    )

    fig.update_layout(
        title={
            "text": title,
            "font": {
                "family": fonts.get("heading", "맑은 고딕"),
                "size": waterfall_style.get("title_size", 14),
                "color": colors.get("primary", "#003366"),
            },
            "x": 0.5,
            "xanchor": "center",
        },
        font={"family": waterfall_style.get("font_family", "맑은 고딕")},
        plot_bgcolor=waterfall_style.get("background", "white"),
        paper_bgcolor="white",
        showlegend=False,
        width=900,
        height=500,
        margin={"t": 60, "b": 60, "l": 60, "r": 40},
        yaxis={
            "title": y_axis_title,
            "gridcolor": waterfall_style.get("grid_color", "#E0E0E0"),
            "zeroline": True,
            "zerolinecolor": "#999999",
        },
    )

    buffer = BytesIO()
    pio.write_image(fig, buffer, format="png", scale=2)
    buffer.seek(0)
    return buffer
