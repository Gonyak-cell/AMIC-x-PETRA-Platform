"""DM (Discussion Memorandum) 기본 템플릿 TemplateSpec (IM 모듈).

> 마지막 수정: 2026-03-13 21:16:29

design_tokens.py 디자인 상수 + DM_SECTIONS 기반.
레이아웃: SL Template (10.83" x 7.5").
"""

from __future__ import annotations

from src.template_engine.template_spec import (
    OverflowPolicy,
    ShrinkPolicy,
    SlideSpec,
    SlotContentType,
    SlotSpec,
    TemplateSpec,
    register_spec,
)

# ── design_tokens.py IMPageLayout 참조 ──
_LEFT = 0.5
_TOP = 1.07
_WIDTH = 9.83
_BODY_HEIGHT = 5.43  # 6.5 - 1.07

DM_DEFAULT = TemplateSpec(
    template_id="im-dm-default-v1",
    doc_type="DM",
    variant="default",
    template_path="templates/sl_template.pptx",
    brand_tokens={
        "color_primary": "#0F3A32",
        "color_secondary": "#1C8F57",
        "color_accent": "#26C260",
        "color_body_text": "#3D3D3D",
        "color_negative": "#BC2C1A",
        "font_heading": "SUITE",
        "font_body": "Pretendard",
        "font_fallback": "Noto Sans KR",
    },
    slides=(
        # ── 1. Cover ──
        SlideSpec(
            purpose="cover",
            layout_name="COVER",
            required_shapes=("project_name", "memo_type", "date"),
            slots=(
                SlotSpec(
                    name="project_name",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 2.5, _WIDTH, 1.0),
                    max_lines=2,
                    max_chars=60,
                    min_font_pt=40.0,
                    alignment="CENTER",
                ),
                SlotSpec(
                    name="memo_type",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 3.6, _WIDTH, 0.5),
                    max_lines=1,
                    max_chars=40,
                    min_font_pt=24.0,
                    alignment="CENTER",
                ),
                SlotSpec(
                    name="date",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 4.2, _WIDTH, 0.4),
                    max_lines=1,
                    max_chars=30,
                    min_font_pt=16.0,
                    alignment="CENTER",
                ),
            ),
        ),
        # ── 2. DM Market Trends ──
        SlideSpec(
            purpose="dm_market_trends",
            layout_name="MAIN",
            required_shapes=("title", "body"),
            optional_shapes=("chart",),
            slots=(
                SlotSpec(
                    name="title",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 0.6, _WIDTH, 0.4),
                    max_lines=1,
                    min_font_pt=16.0,
                ),
                SlotSpec(
                    name="body",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, _TOP, _WIDTH, _BODY_HEIGHT),
                    min_font_pt=10.0,
                    overflow_policy=OverflowPolicy.TRUNCATE,
                ),
                SlotSpec(
                    name="chart",
                    content_type=SlotContentType.CHART,
                    bbox=(_LEFT, _TOP, _WIDTH, _BODY_HEIGHT),
                ),
            ),
        ),
        # ── 3. DM Deal Structure ──
        SlideSpec(
            purpose="dm_deal_structure",
            layout_name="MAIN",
            required_shapes=("title", "body"),
            slots=(
                SlotSpec(
                    name="title",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 0.6, _WIDTH, 0.4),
                    max_lines=1,
                    min_font_pt=16.0,
                ),
                SlotSpec(
                    name="body",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, _TOP, _WIDTH, _BODY_HEIGHT),
                    min_font_pt=10.0,
                ),
            ),
        ),
        # ── 4. DM Investment Thesis ──
        SlideSpec(
            purpose="dm_investment_thesis",
            layout_name="MAIN",
            required_shapes=("title", "body"),
            slots=(
                SlotSpec(
                    name="title",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 0.6, _WIDTH, 0.4),
                    max_lines=1,
                    min_font_pt=16.0,
                ),
                SlotSpec(
                    name="body",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, _TOP, _WIDTH, _BODY_HEIGHT),
                    min_font_pt=10.0,
                ),
            ),
        ),
        # ── 5. DM Valuation ──
        SlideSpec(
            purpose="dm_valuation",
            layout_name="MAIN",
            required_shapes=("title", "table"),
            optional_shapes=("chart",),
            slots=(
                SlotSpec(
                    name="title",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 0.6, _WIDTH, 0.4),
                    max_lines=1,
                    min_font_pt=16.0,
                ),
                SlotSpec(
                    name="table",
                    content_type=SlotContentType.TABLE,
                    bbox=(_LEFT, _TOP, _WIDTH, 4.0),
                    min_font_pt=9.0,
                ),
                SlotSpec(
                    name="chart",
                    content_type=SlotContentType.CHART,
                    bbox=(_LEFT, 5.3, _WIDTH, 1.2),
                ),
            ),
        ),
        # ── 6. DM Risk Assessment ──
        SlideSpec(
            purpose="dm_risk_assessment",
            layout_name="MAIN",
            required_shapes=("title", "body"),
            slots=(
                SlotSpec(
                    name="title",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 0.6, _WIDTH, 0.4),
                    max_lines=1,
                    min_font_pt=16.0,
                ),
                SlotSpec(
                    name="body",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, _TOP, _WIDTH, _BODY_HEIGHT),
                    min_font_pt=10.0,
                    shrink_policy=ShrinkPolicy.TRUNCATE,
                ),
            ),
        ),
        # ── 7. DM Summary ──
        SlideSpec(
            purpose="dm_summary",
            layout_name="MAIN",
            required_shapes=("title", "body"),
            slots=(
                SlotSpec(
                    name="title",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 0.6, _WIDTH, 0.4),
                    max_lines=1,
                    min_font_pt=16.0,
                ),
                SlotSpec(
                    name="body",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, _TOP, _WIDTH, _BODY_HEIGHT),
                    min_font_pt=10.0,
                ),
            ),
        ),
        # ── 8. Contact ──
        SlideSpec(
            purpose="contact",
            layout_name="FOREST",
            required_shapes=("contact_info",),
            slots=(
                SlotSpec(
                    name="contact_info",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 2.0, _WIDTH, 4.0),
                    min_font_pt=12.0,
                    alignment="CENTER",
                ),
            ),
        ),
    ),
)

register_spec(DM_DEFAULT)
