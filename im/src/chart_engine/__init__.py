"""Chart Engine — Plotly/Graphviz/네이티브 PPTX 기반 차트·다이어그램 생성 모듈.

> 마지막 수정: 2026-02-27 10:28:00

IMDocumentData의 재무/시장/조직 데이터를 시각화하는 독립 모듈.
design_renderer에서 호출하되, design_renderer에 의존하지 않는다.

하이브리드 전략:
- stacked_bar, donut, line, hbar → 네이티브 PPTX 차트 (편집 가능)
- combo, waterfall, heatmap 등 → Plotly → PNG 래스터 (기존)
- org_chart, shareholding, flow → Graphviz → PNG

사용 예시::

    from src.chart_engine import create_chart, AMICThemeFactory, ChartConfig
    from src.chart_engine import plotly_to_png, graphviz_to_png
    from src.chart_engine.pptx_native import get_native_builder, is_native_supported

    fig = create_chart("combo", data, title="매출 추이")
    png_bytes = plotly_to_png(fig)
"""

# Config
from src.chart_engine.config import (
    AMIC_CHART_COLORS,
    CHART_DPI,
    DEFAULT_CHART_CONFIG,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    KOREAN_FONT,
    ChartColorConfig,
    ChartConfig,
)

# Exceptions
from src.chart_engine.exceptions import (
    ChartDataError,
    ChartEngineError,
    ExportError,
    GraphvizError,
    UnsupportedChartTypeError,
)

# Plotly charts
from src.chart_engine.plotly import (
    CHART_DISPATCH,
    AMICThemeFactory,
    create_chart,
    create_cohort_heatmap_chart,
    create_combo_chart,
    create_donut_chart,
    create_funnel_chart,
    create_hbar_chart,
    create_line_chart,
    create_sensitivity_heatmap_chart,
    create_stacked_bar_chart,
    create_treemap_chart,
    create_waterfall_chart,
)

# Graphviz diagrams
from src.chart_engine.graphviz import (
    create_flow_diagram,
    create_org_chart,
    create_shareholding_diagram,
)

# Export
from src.chart_engine.export import (
    graphviz_to_png,
    graphviz_to_svg,
    plotly_to_png,
    plotly_to_svg,
)

# Data transformer
from src.chart_engine.data_transformer import ChartSpec, DataTransformer

__version__ = "0.8.0"

__all__ = [
    # Config
    "ChartColorConfig",
    "ChartConfig",
    "DEFAULT_CHART_CONFIG",
    "AMIC_CHART_COLORS",
    "CHART_DPI",
    "DEFAULT_WIDTH",
    "DEFAULT_HEIGHT",
    "KOREAN_FONT",
    # Exceptions
    "ChartEngineError",
    "UnsupportedChartTypeError",
    "ChartDataError",
    "ExportError",
    "GraphvizError",
    # Plotly
    "AMICThemeFactory",
    "CHART_DISPATCH",
    "create_chart",
    "create_cohort_heatmap_chart",
    "create_combo_chart",
    "create_donut_chart",
    "create_funnel_chart",
    "create_hbar_chart",
    "create_line_chart",
    "create_sensitivity_heatmap_chart",
    "create_stacked_bar_chart",
    "create_treemap_chart",
    "create_waterfall_chart",
    # Graphviz
    "create_flow_diagram",
    "create_org_chart",
    "create_shareholding_diagram",
    # Export
    "graphviz_to_png",
    "graphviz_to_svg",
    "plotly_to_png",
    "plotly_to_svg",
    # Data transformer
    "ChartSpec",
    "DataTransformer",
]
