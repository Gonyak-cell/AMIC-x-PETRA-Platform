"""Renderers 패키지.

Report IR을 PPT/Word/PDF로 변환하는 렌더러들을 포함합니다.

현재 구현:
- design_system: 디자인 시스템 설정 로더
- report_builder: Report IR 구성 (dataclasses)

향후 구현 (Sprint 9+):
- pptx_renderer: PPT 렌더러 (pptx-service 연동)
- docx_renderer: Word 렌더러 (python-docx)
"""

from app.renderers.design_system import (
    clear_cache,
    get_adjustment_color,
    get_chart_style,
    get_colors,
    get_design_system,
    get_fdd_config,
    get_fonts,
    get_layout,
    get_number_formats,
    get_risk_color,
    get_sizes,
    load_design_system,
)
from app.renderers.report_builder import (
    AlignType,
    BlockType,
    ChartBlock,
    ChartData,
    ChartType,
    CoverBlock,
    KPIBlock,
    Position,
    ReportBlock,
    ReportIR,
    ReportMetadata,
    RiskLevel,
    Size,
    TableBlock,
    TableColumn,
    TextBlock,
    build_kpi_block,
    build_qoe_table_block,
    build_text_block,
    build_waterfall_chart_block,
    report_ir_to_dict,
)

__all__ = [
    # Design System
    "load_design_system",
    "get_design_system",
    "get_colors",
    "get_fonts",
    "get_sizes",
    "get_number_formats",
    "get_layout",
    "get_chart_style",
    "get_fdd_config",
    "get_adjustment_color",
    "get_risk_color",
    "clear_cache",
    # Report Builder - Enums
    "BlockType",
    "ChartType",
    "AlignType",
    "RiskLevel",
    # Report Builder - Blocks
    "Position",
    "Size",
    "CoverBlock",
    "KPIBlock",
    "TableBlock",
    "TableColumn",
    "ChartBlock",
    "ChartData",
    "TextBlock",
    # Report Builder - IR
    "ReportMetadata",
    "ReportBlock",
    "ReportIR",
    # Report Builder - Functions
    "build_qoe_table_block",
    "build_waterfall_chart_block",
    "build_kpi_block",
    "build_text_block",
    "report_ir_to_dict",
]
