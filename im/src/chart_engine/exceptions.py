"""Chart Engine 모듈 커스텀 예외 계층.

> 마지막 수정: 2026-02-10 13:45:13

차트 생성, 내보내기, 다이어그램에서 발생하는 예외를 정의합니다.
"""

from __future__ import annotations

from typing import Any


class ChartEngineError(Exception):
    """Chart Engine 모듈 최상위 예외."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ============================================================================
# 차트 유형 예외
# ============================================================================


class UnsupportedChartTypeError(ChartEngineError):
    """지원하지 않는 차트 유형."""

    def __init__(self, chart_type: str, supported: list[str] | None = None) -> None:
        super().__init__(
            message=f"지원하지 않는 차트 유형: '{chart_type}'",
            details={"chart_type": chart_type, "supported_types": supported or []},
        )


class ChartDataError(ChartEngineError):
    """차트 데이터 유효성 검증 실패."""

    def __init__(self, chart_type: str, reason: str = "") -> None:
        super().__init__(
            message=f"차트 데이터 오류 ({chart_type}): {reason}",
            details={"chart_type": chart_type, "reason": reason},
        )


# ============================================================================
# 내보내기 예외
# ============================================================================


class ExportError(ChartEngineError):
    """차트 내보내기 실패."""

    def __init__(self, format: str, reason: str = "") -> None:
        super().__init__(
            message=f"차트 내보내기 실패 ({format}): {reason}",
            details={"format": format, "reason": reason},
        )


# ============================================================================
# Graphviz 예외
# ============================================================================


class GraphvizError(ChartEngineError):
    """Graphviz 다이어그램 생성 실패."""

    def __init__(self, diagram_type: str, reason: str = "") -> None:
        super().__init__(
            message=f"다이어그램 생성 실패 ({diagram_type}): {reason}",
            details={"diagram_type": diagram_type, "reason": reason},
        )
