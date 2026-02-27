"""차트 렌더러 파사드.

ChartSpec을 받아 적절한 차트 유형으로 렌더링합니다.
"""

import base64
from decimal import Decimal
from io import BytesIO
from typing import Any

from app.renderers.report_builder import ChartBlock, ChartType
from app.services.chart.bar import (
    create_bar_chart,
    create_grouped_bar_chart,
    create_stacked_bar_chart,
)
from app.services.chart.line import create_single_line_chart, create_trend_chart
from app.services.chart.pie import create_donut_chart, create_pie_chart
from app.services.chart.waterfall import create_generic_waterfall

CHART_RENDERER_VERSION = "0.2.0"


class ChartSpec:
    """차트 생성 스펙."""

    def __init__(
        self,
        chart_type: ChartType | str,
        title: str = "Chart",
        categories: list[str] | None = None,
        values: list[Decimal | float | None] | None = None,
        series: list[dict[str, Any]] | None = None,
        y_axis_title: str = "Value",
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Args:
            chart_type: 차트 유형 (waterfall, bar, line, pie)
            title: 차트 제목
            categories: X축 레이블 (단일 시리즈)
            values: Y축 값 (단일 시리즈)
            series: 다중 시리즈 데이터 [{"name": "...", "values": [...], "color": "..."}]
            y_axis_title: Y축 제목
            config: 추가 설정 (horizontal, stacked, hole_size 등)
        """
        if isinstance(chart_type, str):
            chart_type = ChartType(chart_type)
        self.chart_type = chart_type
        self.title = title
        self.categories = categories or []
        self.values = values or []
        self.series = series
        self.y_axis_title = y_axis_title
        self.config = config or {}


def render_chart(spec: ChartSpec) -> BytesIO:
    """ChartSpec을 PNG 이미지로 렌더링합니다.

    Args:
        spec: ChartSpec 인스턴스

    Returns:
        PNG 이미지 BytesIO 버퍼

    Raises:
        ValueError: 지원하지 않는 차트 유형
    """
    match spec.chart_type:
        case ChartType.WATERFALL:
            return create_generic_waterfall(
                categories=spec.categories,
                values=spec.values,
                title=spec.title,
                y_axis_title=spec.y_axis_title,
            )

        case ChartType.BAR:
            if spec.series:
                if spec.config.get("stacked"):
                    return create_stacked_bar_chart(
                        categories=spec.categories,
                        series=spec.series,
                        title=spec.title,
                        y_axis_title=spec.y_axis_title,
                    )
                return create_grouped_bar_chart(
                    categories=spec.categories,
                    series=spec.series,
                    title=spec.title,
                    y_axis_title=spec.y_axis_title,
                )
            return create_bar_chart(
                categories=spec.categories,
                values=spec.values,
                title=spec.title,
                y_axis_title=spec.y_axis_title,
                horizontal=spec.config.get("horizontal", False),
            )

        case ChartType.LINE:
            if spec.series:
                return create_trend_chart(
                    categories=spec.categories,
                    series=spec.series,
                    title=spec.title,
                    y_axis_title=spec.y_axis_title,
                )
            return create_single_line_chart(
                categories=spec.categories,
                values=spec.values,
                title=spec.title,
                y_axis_title=spec.y_axis_title,
            )

        case ChartType.PIE:
            if spec.config.get("donut") or spec.config.get("hole_size"):
                return create_donut_chart(
                    labels=spec.categories,
                    values=spec.values,
                    title=spec.title,
                    hole_size=spec.config.get("hole_size", 0.4),
                    center_text=spec.config.get("center_text"),
                )
            return create_pie_chart(
                labels=spec.categories,
                values=spec.values,
                title=spec.title,
            )

        case _:
            raise ValueError(f"Unsupported chart type: {spec.chart_type}")


def render_chart_to_base64(spec: ChartSpec) -> str:
    """ChartSpec을 base64 인코딩된 PNG 문자열로 렌더링합니다.

    Args:
        spec: ChartSpec 인스턴스

    Returns:
        base64 인코딩된 PNG 문자열
    """
    buffer = render_chart(spec)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def render_chart_block(block: ChartBlock) -> ChartBlock:
    """ChartBlock의 이미지를 렌더링하여 반환합니다.

    이미 image_base64가 있으면 그대로 반환합니다.

    Args:
        block: ChartBlock 인스턴스

    Returns:
        이미지가 렌더링된 ChartBlock
    """
    if block.image_base64:
        return block

    if block.data is None:
        return block

    spec = ChartSpec(
        chart_type=block.chart_type,
        title=block.title,
        categories=block.data.categories,
        values=block.data.values,
    )

    image_base64 = render_chart_to_base64(spec)

    return ChartBlock(
        chart_type=block.chart_type,
        title=block.title,
        data=block.data,
        image_base64=image_base64,
        position=block.position,
        size=block.size,
    )


def validate_chart_data(
    spec: ChartSpec,
    source_table_rows: list[dict[str, Any]] | None = None,
) -> list[str]:
    """차트 데이터와 소스 테이블 데이터의 일치를 검증합니다.

    Args:
        spec: ChartSpec 인스턴스
        source_table_rows: 소스 테이블 행 데이터 (선택)

    Returns:
        검증 오류 메시지 리스트 (빈 리스트 = 성공)
    """
    errors: list[str] = []

    # 기본 검증
    if not spec.categories:
        errors.append("Categories list is empty")

    if not spec.values and not spec.series:
        errors.append("Neither values nor series provided")

    if spec.values and len(spec.categories) != len(spec.values):
        errors.append(
            f"Categories count ({len(spec.categories)}) != values count ({len(spec.values)})"
        )

    if spec.series:
        for idx, s in enumerate(spec.series):
            series_values = s.get("values", [])
            if len(spec.categories) != len(series_values):
                errors.append(
                    f"Series[{idx}] values count ({len(series_values)}) != categories count ({len(spec.categories)})"
                )

    # 소스 테이블 비교 검증
    if source_table_rows and spec.values:
        for i, (chart_val, row) in enumerate(zip(spec.values, source_table_rows)):
            # 첫 번째 숫자 필드 찾기 (간단한 휴리스틱)
            for key, value in row.items():
                if isinstance(value, (int, float, Decimal)) or (
                    isinstance(value, str) and value.replace(",", "").replace("-", "").replace(".", "").isdigit()
                ):
                    try:
                        table_val = Decimal(str(value).replace(",", ""))
                        if chart_val is not None:
                            chart_decimal = Decimal(str(chart_val))
                            if chart_decimal != table_val:
                                errors.append(
                                    f"Value mismatch at index {i}: chart={chart_val}, table={table_val}"
                                )
                    except Exception:
                        pass
                    break

    return errors
