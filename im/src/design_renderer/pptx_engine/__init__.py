"""PPTX 생성 엔진 (python-pptx 기반)."""

from src.design_renderer.pptx_engine.create_template import (
    create_im_template,
    get_layout_by_purpose,
)
from src.design_renderer.pptx_engine.shape_builder import (
    add_body_textbox,
    add_bullet_list,
    add_chart_image,
    add_financial_table,
    add_kpi_grid,
    add_sub_header_bar,
    add_summary_textbox,
)
from src.design_renderer.pptx_engine.slide_factory import SlideFactory
from src.design_renderer.pptx_engine.style_applier import (
    add_watermark,
    apply_presentation_style,
    apply_run_style,
    apply_slide_style,
    set_edit_restriction,
)
from src.design_renderer.pptx_engine.template_manager import TemplateManager
from src.design_renderer.pptx_engine.toc_builder import (
    build_toc_slide,
    build_toc_slide_html,
)

__all__ = [
    # create_template (Sprint 2)
    "create_im_template",
    "get_layout_by_purpose",
    # template_manager (Sprint 3)
    "TemplateManager",
    # slide_factory (Sprint 3)
    "SlideFactory",
    # shape_builder (Sprint 3)
    "add_body_textbox",
    "add_bullet_list",
    "add_chart_image",
    "add_financial_table",
    "add_kpi_grid",
    "add_sub_header_bar",
    "add_summary_textbox",
    # style_applier (Sprint 3 + Sprint 5 보안)
    "add_watermark",
    "apply_presentation_style",
    "apply_run_style",
    "apply_slide_style",
    "set_edit_restriction",
    # toc_builder (Sprint 3)
    "build_toc_slide",
    "build_toc_slide_html",
]
