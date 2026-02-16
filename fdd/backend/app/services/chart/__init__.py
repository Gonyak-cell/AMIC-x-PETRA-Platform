"""Chart 서비스 모듈.

Plotly 기반 차트 생성 서비스:
- Waterfall: EBITDA Bridge, Net Debt Bridge
- Line: 시계열 트렌드 차트
- Bar: 범주별 비교 차트 (단일/그룹/누적)
- Pie/Donut: 구성비 차트
"""

from app.services.chart.bar import (
    create_bar_chart,
    create_grouped_bar_chart,
    create_stacked_bar_chart,
)
from app.services.chart.line import create_single_line_chart, create_trend_chart
from app.services.chart.pie import (
    create_donut_chart,
    create_nwc_composition_chart,
    create_pie_chart,
)
from app.services.chart.renderer import (
    CHART_RENDERER_VERSION,
    ChartSpec,
    render_chart,
    render_chart_block,
    render_chart_to_base64,
    validate_chart_data,
)
from app.services.chart.waterfall import create_ebitda_bridge, create_generic_waterfall

__all__ = [
    # Waterfall
    "create_ebitda_bridge",
    "create_generic_waterfall",
    # Line
    "create_trend_chart",
    "create_single_line_chart",
    # Bar
    "create_bar_chart",
    "create_grouped_bar_chart",
    "create_stacked_bar_chart",
    # Pie
    "create_pie_chart",
    "create_donut_chart",
    "create_nwc_composition_chart",
    # Renderer facade
    "ChartSpec",
    "render_chart",
    "render_chart_to_base64",
    "render_chart_block",
    "validate_chart_data",
    "CHART_RENDERER_VERSION",
]
