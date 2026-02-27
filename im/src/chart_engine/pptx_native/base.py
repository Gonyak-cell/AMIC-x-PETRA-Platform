"""네이티브 PPTX 차트 빌더 기본 클래스.

> 마지막 수정: 2026-02-27 10:28:00
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.chart_engine.config import ChartConfig, DEFAULT_CHART_CONFIG


class NativeChartBuilder(ABC):
    """네이티브 PPTX 차트를 생성하는 빌더의 기본 클래스.

    Plotly → PNG 래스터 대신 python-pptx의 ``add_chart()`` API를 사용하여
    편집 가능한 네이티브 차트를 슬라이드에 직접 삽입한다.
    """

    @abstractmethod
    def build(
        self,
        slide: Any,
        data: dict[str, Any],
        *,
        title: str = "",
        left: float = 0.5,
        top: float = 1.5,
        width: float = 9.0,
        height: float = 4.5,
        config: ChartConfig | None = None,
    ) -> Any:
        """슬라이드에 네이티브 차트를 추가하고 chart shape를 반환.

        Args:
            slide: python-pptx Slide 객체.
            data: 차트 입력 데이터 (Plotly 차트와 동일한 dict 스키마).
            title: 차트 제목.
            left/top/width/height: 슬라이드 내 위치 및 크기 (인치).
            config: AMIC 차트 설정.

        Returns:
            python-pptx chart shape.
        """
        ...

    def _get_config(self, config: ChartConfig | None) -> ChartConfig:
        return config or DEFAULT_CHART_CONFIG
