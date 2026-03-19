"""DM (Discussion Memorandum) 기본 템플릿 TemplateSpec.

> 마지막 수정: 2026-03-13 21:16:29

memo_generator.py 디자인 상수 + dm.json PRD 기반.
레이아웃: Forest 테마 (10.8333" x 7.5").
"""

from __future__ import annotations

from app.pptx.template_spec import (
    OverflowPolicy,
    ShrinkPolicy,
    SlideSpec,
    SlotContentType,
    SlotSpec,
    TemplateSpec,
    register_spec,
)

# ── memo_generator.py 상수 참조 ──
_LEFT = 0.4954
_TOP = 1.25
_WIDTH = 9.8425
_BODY_HEIGHT = 5.5

DM_DEFAULT = TemplateSpec(
    template_id="dm-default-v1",
    doc_type="DM",
    variant="default",
    template_path="templates/memorandum/memorandum_master.pptx",
    brand_tokens={
        "color_primary": "#0F3A32",
        "color_accent": "#1C8F57",
        "color_bright": "#26C260",
        "color_body_text": "#3D3D3D",
        "color_red_accent": "#BC2C1A",
        "font_heading": "SUIT Medium",
        "font_body": "SUIT Medium",
        "font_fallback": "맑은 고딕",
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
                    min_font_pt=28.0,
                    alignment="CENTER",
                ),
                SlotSpec(
                    name="memo_type",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 3.6, _WIDTH, 0.5),
                    max_lines=1,
                    max_chars=40,
                    min_font_pt=18.0,
                    alignment="CENTER",
                ),
                SlotSpec(
                    name="date",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 4.2, _WIDTH, 0.4),
                    max_lines=1,
                    max_chars=30,
                    min_font_pt=14.0,
                    alignment="CENTER",
                ),
            ),
        ),
        # ── 2. Disclaimer ──
        SlideSpec(
            purpose="disclaimer",
            layout_name="MAIN",
            required_shapes=("disclaimer_text",),
            slots=(
                SlotSpec(
                    name="disclaimer_text",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, _TOP, _WIDTH, _BODY_HEIGHT),
                    max_lines=40,
                    min_font_pt=9.0,
                    shrink_policy=ShrinkPolicy.TRUNCATE,
                ),
            ),
        ),
        # ── 3. Discussion Overview ──
        SlideSpec(
            purpose="discussion_overview",
            layout_name="MAIN",
            required_shapes=("title", "body"),
            slots=(
                SlotSpec(
                    name="title",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 0.6, _WIDTH, 0.5),
                    max_lines=1,
                    max_chars=50,
                    min_font_pt=16.0,
                ),
                SlotSpec(
                    name="body",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, _TOP, _WIDTH, _BODY_HEIGHT),
                    min_font_pt=10.0,
                    overflow_policy=OverflowPolicy.TRUNCATE,
                ),
            ),
        ),
        # ── 4. Key Discussion Topics ──
        SlideSpec(
            purpose="key_topics",
            layout_name="MAIN",
            required_shapes=("title", "body"),
            slots=(
                SlotSpec(
                    name="title",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 0.6, _WIDTH, 0.5),
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
        # ── 5. Financial Analysis ──
        SlideSpec(
            purpose="financial_analysis",
            layout_name="MAIN",
            required_shapes=("title", "table"),
            optional_shapes=("chart",),
            slots=(
                SlotSpec(
                    name="title",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 0.6, _WIDTH, 0.5),
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
                    bbox=(_LEFT, 5.5, _WIDTH, 1.5),
                ),
            ),
        ),
        # ── 6. Next Steps ──
        SlideSpec(
            purpose="next_steps",
            layout_name="MAIN",
            required_shapes=("title", "body"),
            slots=(
                SlotSpec(
                    name="title",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 0.6, _WIDTH, 0.5),
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
    ),
)

register_spec(DM_DEFAULT)
