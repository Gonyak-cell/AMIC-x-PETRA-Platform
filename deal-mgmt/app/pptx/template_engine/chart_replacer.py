"""모듈 1: 차트 플레이스홀더 제어 — 기존 차트의 데이터 교체.

shape.has_chart로 차트를 식별하고 chart.replace_data()로 데이터를 갱신한다.
차트의 서식(색상, 폰트, 레이아웃)은 replace_data 호출 시 보존된다.
"""

from __future__ import annotations

import logging
from typing import Any

from pptx.chart.data import CategoryChartData

from .constants import NUMBER_FORMAT_NEGATIVE_PARENS
from .exceptions import ChartShapeError, DataValidationError
from .shape_finder import find_shape_by_name

logger = logging.getLogger(__name__)


def replace_chart_data(
    slide: Any,
    shape_name: str,
    categories: list[str],
    series: list[dict[str, Any]],
    *,
    scale_factor: float = 1.0,
    number_format: str = NUMBER_FORMAT_NEGATIVE_PARENS,
) -> Any:
    """기존 차트의 데이터를 교체한다.

    Args:
        slide: Slide 인스턴스.
        shape_name: 차트를 포함한 shape의 name.
        categories: 카테고리 라벨 (예: ["2022", "2023", "2024"]).
        series: 시리즈 데이터 리스트.
            [{"name": "매출", "values": [100000, 120000, 150000]}, ...]
        scale_factor: 값 스케일링 (예: 0.001 = 원 → 천원).
        number_format: 차트 데이터 레이블 포맷.

    Returns:
        업데이트된 chart 객체.

    Raises:
        ChartShapeError: shape에 차트가 없을 때.
        DataValidationError: 카테고리/시리즈 길이 불일치.
    """
    shape = find_shape_by_name(slide, shape_name)

    if not shape.has_chart:
        raise ChartShapeError(
            f"'{shape_name}'에 차트가 없습니다. "
            f"shape_type: {shape.shape_type}"
        )

    chart = shape.chart

    # 데이터 검증
    n_cats = len(categories)
    for s in series:
        values = s.get("values", [])
        if len(values) != n_cats:
            raise DataValidationError(
                f"시리즈 '{s.get('name', '')}' 값 수({len(values)})가 "
                f"카테고리 수({n_cats})와 불일치"
            )

    # CategoryChartData 구성
    chart_data = CategoryChartData()
    chart_data.categories = categories

    for s in series:
        scaled_values = tuple(
            v * scale_factor if v is not None else None for v in s["values"]
        )
        chart_data.add_series(s.get("name", ""), scaled_values)

    # 데이터 교체 (서식 보존)
    chart.replace_data(chart_data)

    # 숫자 서식 적용
    _apply_number_format(chart, number_format)

    logger.info(
        "차트 '%s' 데이터 교체 완료: %d 카테고리, %d 시리즈, scale=%.4f",
        shape_name,
        n_cats,
        len(series),
        scale_factor,
    )

    return chart


def replace_chart_data_batch(
    slide: Any,
    replacements: list[dict[str, Any]],
) -> list[Any]:
    """한 슬라이드의 여러 차트를 일괄 교체.

    Args:
        slide: Slide 인스턴스.
        replacements: [{"shape_name": str, "categories": list,
                        "series": list, "scale_factor": float}, ...]

    Returns:
        업데이트된 chart 객체 리스트.
    """
    results = []
    for r in replacements:
        chart = replace_chart_data(
            slide,
            r["shape_name"],
            r["categories"],
            r["series"],
            scale_factor=r.get("scale_factor", 1.0),
            number_format=r.get("number_format", NUMBER_FORMAT_NEGATIVE_PARENS),
        )
        results.append(chart)
    return results


def _apply_number_format(chart: Any, number_format: str) -> None:
    """차트의 모든 시리즈에 숫자 서식을 적용한다."""
    for plot in chart.plots:
        for series in plot.series:
            series.format.number_format = number_format
            series.format.number_format_is_linked = False
