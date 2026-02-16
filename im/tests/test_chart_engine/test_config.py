"""config.py / exceptions.py 단위 테스트.

> 마지막 수정: 2026-02-10 13:45:13
"""

from src.chart_engine.config import (
    AMIC_CHART_COLORS,
    DEFAULT_CHART_CONFIG,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    KOREAN_FONT,
    ChartColorConfig,
    ChartConfig,
)
from src.chart_engine.exceptions import (
    ChartDataError,
    ChartEngineError,
    ExportError,
    GraphvizError,
    UnsupportedChartTypeError,
)


class TestChartConfig:
    """ChartConfig / ChartColorConfig 기본값."""

    def test_default_chart_config(self):
        """기본 설정값 검증."""
        cfg = ChartConfig()
        assert cfg.width == DEFAULT_WIDTH
        assert cfg.height == DEFAULT_HEIGHT
        assert cfg.font == KOREAN_FONT
        assert cfg.dpi_scale == 3
        assert cfg.colors.primary == "#0F3A32"
        assert cfg.colors.accent == "#26C260"

    def test_custom_colors(self):
        """커스텀 컬러 설정."""
        colors = ChartColorConfig(primary="#FF0000", accent="#00FF00")
        cfg = ChartConfig(colors=colors, width=800)
        assert cfg.colors.primary == "#FF0000"
        assert cfg.width == 800
        assert cfg.height == DEFAULT_HEIGHT  # 기본값 유지

    def test_default_chart_config_singleton(self):
        """DEFAULT_CHART_CONFIG는 frozen 인스턴스."""
        assert DEFAULT_CHART_CONFIG.width == DEFAULT_WIDTH
        assert DEFAULT_CHART_CONFIG.colors.primary == "#0F3A32"

    def test_amic_chart_colors_length(self):
        """AMIC 차트 컬러 시퀀스 10개."""
        assert len(AMIC_CHART_COLORS) == 10


class TestExceptions:
    """예외 계층 구조."""

    def test_chart_engine_error_base(self):
        """최상위 예외에 message + details 포함."""
        err = ChartEngineError("테스트 오류", {"key": "value"})
        assert err.message == "테스트 오류"
        assert err.details == {"key": "value"}
        assert str(err) == "테스트 오류"

    def test_exception_hierarchy(self):
        """모든 예외가 ChartEngineError 상속."""
        assert issubclass(UnsupportedChartTypeError, ChartEngineError)
        assert issubclass(ChartDataError, ChartEngineError)
        assert issubclass(ExportError, ChartEngineError)
        assert issubclass(GraphvizError, ChartEngineError)

    def test_unsupported_chart_type_error(self):
        """UnsupportedChartTypeError 세부 정보."""
        err = UnsupportedChartTypeError("pie", ["combo", "donut"])
        assert "pie" in err.message
        assert err.details["chart_type"] == "pie"
        assert "combo" in err.details["supported_types"]
