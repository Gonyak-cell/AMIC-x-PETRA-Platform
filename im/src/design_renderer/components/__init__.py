"""Design Renderer 공용 컴포넌트 (PPTX/PDF 듀얼 렌더링)."""

from src.design_renderer.components.chart_embed import (
    create_chart,
    create_combo_chart,
    create_donut_chart,
    create_hbar_chart,
    create_line_chart,
    create_stacked_bar_chart,
    create_waterfall_chart,
    embed_chart_html,
    embed_chart_pptx,
)
from src.design_renderer.components.content_overflow import (
    ContentBlock,
    SlideContent,
    auto_adjust_font_size,
    estimate_content_height,
    split_content_to_slides,
)
from src.design_renderer.components.number_formatter import (
    apply_table_number_format,
    format_currency,
    format_growth_indicator,
    format_number,
    format_percentage,
)
from src.design_renderer.components.org_chart import (
    create_org_chart,
    render_org_chart_html,
    render_org_chart_pptx,
)
from src.design_renderer.components.source_citation import (
    assign_footnote_numbers,
    format_footnote,
    render_footnote_html,
    render_footnote_pptx,
)
from src.design_renderer.components.sub_header_bar import (
    render_sub_header_html,
    render_sub_header_pptx,
)
from src.design_renderer.components.financial_table import (
    render_financial_table_html,
    render_financial_table_pptx,
)
from src.design_renderer.components.kpi_card import (
    render_kpi_grid_html,
    render_kpi_grid_pptx,
)
from src.design_renderer.components.page_elements import (
    render_footer_html,
    render_footer_pptx,
    render_horizontal_line_html,
    render_horizontal_line_pptx,
    render_page_number_pptx,
    render_slide_title_html,
    render_slide_title_pptx,
)
from src.design_renderer.components.timeline import (
    create_timeline_figure,
    render_timeline_html,
    render_timeline_pptx,
)

__all__ = [
    # chart_embed
    "create_chart",
    "create_combo_chart",
    "create_donut_chart",
    "create_hbar_chart",
    "create_line_chart",
    "create_stacked_bar_chart",
    "create_waterfall_chart",
    "embed_chart_html",
    "embed_chart_pptx",
    # content_overflow
    "ContentBlock",
    "SlideContent",
    "auto_adjust_font_size",
    "estimate_content_height",
    "split_content_to_slides",
    # number_formatter
    "apply_table_number_format",
    "format_currency",
    "format_growth_indicator",
    "format_number",
    "format_percentage",
    # org_chart
    "create_org_chart",
    "render_org_chart_html",
    "render_org_chart_pptx",
    # source_citation
    "assign_footnote_numbers",
    "format_footnote",
    "render_footnote_html",
    "render_footnote_pptx",
    # sub_header_bar
    "render_sub_header_html",
    "render_sub_header_pptx",
    # timeline
    "create_timeline_figure",
    "render_timeline_html",
    "render_timeline_pptx",
    # financial_table (Sprint 3)
    "render_financial_table_html",
    "render_financial_table_pptx",
    # kpi_card (Sprint 3)
    "render_kpi_grid_html",
    "render_kpi_grid_pptx",
    # page_elements (Sprint 3)
    "render_footer_html",
    "render_footer_pptx",
    "render_horizontal_line_html",
    "render_horizontal_line_pptx",
    "render_page_number_pptx",
    "render_slide_title_html",
    "render_slide_title_pptx",
]
