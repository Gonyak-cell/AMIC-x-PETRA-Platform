"""네이티브 PPTX 차트 빌더 레지스트리.

> 마지막 수정: 2026-02-27 10:28:00

python-pptx의 ``add_chart()`` API를 사용하여 편집 가능한 네이티브 차트를 생성한다.
Plotly → PNG 래스터 방식과 달리 PowerPoint에서 직접 데이터를 수정할 수 있다.
"""

from __future__ import annotations

from src.chart_engine.pptx_native.base import NativeChartBuilder
from src.chart_engine.pptx_native.donut import DonutBuilder
from src.chart_engine.pptx_native.hbar import HBarBuilder
from src.chart_engine.pptx_native.line_chart import LineChartBuilder
from src.chart_engine.pptx_native.stacked_bar import StackedBarBuilder

# 네이티브 PPTX로 전환 가능한 차트 타입 레지스트리
_NATIVE_BUILDERS: dict[str, NativeChartBuilder] = {
    "stacked_bar": StackedBarBuilder(),
    "donut": DonutBuilder(),
    "line": LineChartBuilder(),
    "hbar": HBarBuilder(),
}

# 네이티브 전환 대상 차트 타입 집합 (빠른 조회용)
NATIVE_CHART_TYPES: frozenset[str] = frozenset(_NATIVE_BUILDERS.keys())


def get_native_builder(chart_type: str) -> NativeChartBuilder | None:
    """차트 타입에 해당하는 네이티브 빌더를 반환. 없으면 None."""
    return _NATIVE_BUILDERS.get(chart_type)


def is_native_supported(chart_type: str) -> bool:
    """해당 차트 타입이 네이티브 PPTX로 전환 가능한지 여부."""
    return chart_type in NATIVE_CHART_TYPES


__all__ = [
    "NATIVE_CHART_TYPES",
    "DonutBuilder",
    "HBarBuilder",
    "LineChartBuilder",
    "NativeChartBuilder",
    "StackedBarBuilder",
    "get_native_builder",
    "is_native_supported",
]
