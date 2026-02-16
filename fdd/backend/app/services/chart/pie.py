"""파이/도넛 차트 생성 서비스.

Plotly go.Pie를 사용하여 구성비 차트를 생성합니다.
"""

from decimal import Decimal
from io import BytesIO
from typing import Any

import plotly.graph_objects as go
import plotly.io as pio

from app.renderers.design_system import get_chart_style, get_colors, get_fonts


def create_pie_chart(
    labels: list[str],
    values: list[Decimal | float | None],
    title: str = "Pie Chart",
    colors_list: list[str] | None = None,
    show_percentages: bool = True,
    design_override: dict[str, Any] | None = None,
) -> BytesIO:
    """파이 차트를 생성합니다.

    Args:
        labels: 항목 레이블 리스트
        values: 각 항목의 값 리스트
        title: 차트 제목
        colors_list: 색상 리스트 (None이면 기본 팔레트)
        show_percentages: 백분율 표시 여부
        design_override: Design System 설정 오버라이드

    Returns:
        PNG 이미지 BytesIO 버퍼

    Example:
        >>> buffer = create_pie_chart(
        ...     labels=["Revenue", "COGS", "SG&A", "Other"],
        ...     values=[Decimal("60"), Decimal("25"), Decimal("10"), Decimal("5")],
        ...     title="Cost Breakdown"
        ... )
    """
    colors = get_colors()
    fonts = get_fonts()
    pie_style = get_chart_style("pie") if get_chart_style("pie") else {}

    if design_override:
        pie_style = {**pie_style, **design_override}

    # 기본 색상 팔레트
    if colors_list is None:
        colors_list = [
            colors.get("primary", "#003366"),
            colors.get("positive", "#2E7D32"),
            colors.get("negative", "#E0301E"),
            "#FF9800",
            "#9C27B0",
            "#00BCD4",
            "#795548",
            "#607D8B",
        ]

    # Decimal → float 변환
    float_values = [float(v) if v is not None else 0 for v in values]

    # 텍스트 정보 설정
    if show_percentages:
        textinfo = "percent+label"
    else:
        textinfo = "label"

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=float_values,
            marker={"colors": colors_list[: len(labels)]},
            textinfo=textinfo,
            textposition="outside",
            hole=0,  # 파이 차트 (도넛은 hole > 0)
        )
    )

    fig.update_layout(
        title={
            "text": title,
            "font": {
                "family": fonts.get("heading", "맑은 고딕"),
                "size": pie_style.get("title_size", 14),
                "color": colors.get("primary", "#003366"),
            },
            "x": 0.5,
            "xanchor": "center",
        },
        font={"family": pie_style.get("font_family", "맑은 고딕")},
        paper_bgcolor="white",
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.1, "xanchor": "center", "x": 0.5},
        width=700,
        height=500,
        margin={"t": 60, "b": 80, "l": 40, "r": 40},
    )

    buffer = BytesIO()
    pio.write_image(fig, buffer, format="png", scale=2)
    buffer.seek(0)
    return buffer


def create_donut_chart(
    labels: list[str],
    values: list[Decimal | float | None],
    title: str = "Donut Chart",
    center_text: str | None = None,
    colors_list: list[str] | None = None,
    show_percentages: bool = True,
    hole_size: float = 0.4,
    design_override: dict[str, Any] | None = None,
) -> BytesIO:
    """도넛 차트를 생성합니다.

    Args:
        labels: 항목 레이블 리스트
        values: 각 항목의 값 리스트
        title: 차트 제목
        center_text: 도넛 중앙에 표시할 텍스트 (예: 총합)
        colors_list: 색상 리스트 (None이면 기본 팔레트)
        show_percentages: 백분율 표시 여부
        hole_size: 도넛 구멍 크기 (0~1)
        design_override: Design System 설정 오버라이드

    Returns:
        PNG 이미지 BytesIO 버퍼

    Example:
        >>> buffer = create_donut_chart(
        ...     labels=["Debt", "Cash", "Net Debt"],
        ...     values=[Decimal("100"), Decimal("30"), Decimal("70")],
        ...     title="Net Debt Composition",
        ...     center_text="Net Debt\n70M"
        ... )
    """
    colors = get_colors()
    fonts = get_fonts()
    pie_style = get_chart_style("pie") if get_chart_style("pie") else {}

    if design_override:
        pie_style = {**pie_style, **design_override}

    if colors_list is None:
        colors_list = [
            colors.get("primary", "#003366"),
            colors.get("positive", "#2E7D32"),
            colors.get("negative", "#E0301E"),
            "#FF9800",
            "#9C27B0",
            "#00BCD4",
        ]

    float_values = [float(v) if v is not None else 0 for v in values]

    if show_percentages:
        textinfo = "percent+label"
    else:
        textinfo = "label"

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=float_values,
            marker={"colors": colors_list[: len(labels)]},
            textinfo=textinfo,
            textposition="outside",
            hole=hole_size,
        )
    )

    # 중앙 텍스트 추가
    if center_text:
        fig.add_annotation(
            text=center_text,
            x=0.5,
            y=0.5,
            font={"size": 16, "color": colors.get("primary", "#003366")},
            showarrow=False,
        )

    fig.update_layout(
        title={
            "text": title,
            "font": {
                "family": fonts.get("heading", "맑은 고딕"),
                "size": pie_style.get("title_size", 14),
                "color": colors.get("primary", "#003366"),
            },
            "x": 0.5,
            "xanchor": "center",
        },
        font={"family": pie_style.get("font_family", "맑은 고딕")},
        paper_bgcolor="white",
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.1, "xanchor": "center", "x": 0.5},
        width=700,
        height=500,
        margin={"t": 60, "b": 80, "l": 40, "r": 40},
    )

    buffer = BytesIO()
    pio.write_image(fig, buffer, format="png", scale=2)
    buffer.seek(0)
    return buffer


def create_nwc_composition_chart(
    current_assets: Decimal | float,
    current_liabilities: Decimal | float,
    net_working_capital: Decimal | float,
    title: str = "NWC Composition",
    design_override: dict[str, Any] | None = None,
) -> BytesIO:
    """NWC 구성 도넛 차트를 생성합니다.

    Args:
        current_assets: 유동자산
        current_liabilities: 유동부채
        net_working_capital: 순운전자본
        title: 차트 제목
        design_override: Design System 설정 오버라이드

    Returns:
        PNG 이미지 BytesIO 버퍼
    """
    nwc_value = float(net_working_capital) if net_working_capital else 0
    center_text = f"NWC\n{nwc_value:,.0f}"

    return create_donut_chart(
        labels=["Current Assets", "Current Liabilities"],
        values=[current_assets, current_liabilities],
        title=title,
        center_text=center_text,
        hole_size=0.5,
        design_override=design_override,
    )
