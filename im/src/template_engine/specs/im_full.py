"""IM FULL 스타일 TemplateSpec (IM 모듈).

> 마지막 수정: 2026-03-13 21:16:29

im_document.py SECTION_IDS + design_tokens.py 기반.
19개 섹션: cover, disclaimer, toc_divider, deal_overview, executive_summary,
investment_highlights, company_overview, business_model, market_overview,
business_overview, value_creation, growth_strategy, financial_analysis,
valuation, management_team, shareholder_structure, transaction_structure,
appendix, contact.
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


def _content_slide(
    purpose: str,
    *,
    has_table: bool = False,
    has_chart: bool = False,
    has_image: bool = False,
) -> SlideSpec:
    """MAIN 레이아웃 콘텐츠 슬라이드 팩토리."""
    slots: list[SlotSpec] = [
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
            bbox=(_LEFT, _TOP, _WIDTH, _BODY_HEIGHT if not has_table else 2.5),
            min_font_pt=10.0,
            overflow_policy=OverflowPolicy.TRUNCATE,
        ),
    ]
    if has_table:
        slots.append(
            SlotSpec(
                name="table",
                content_type=SlotContentType.TABLE,
                bbox=(_LEFT, 3.8, _WIDTH, 2.7),
                min_font_pt=9.0,
            )
        )
    if has_chart:
        slots.append(
            SlotSpec(
                name="chart",
                content_type=SlotContentType.CHART,
                bbox=(_LEFT, _TOP, _WIDTH, _BODY_HEIGHT),
            )
        )
    if has_image:
        slots.append(
            SlotSpec(
                name="image",
                content_type=SlotContentType.IMAGE,
                bbox=(_LEFT, _TOP, _WIDTH, _BODY_HEIGHT),
                aspect_ratio_policy="CONTAIN",
            )
        )

    optional = tuple(s.name for s in slots if s.name not in ("title", "body"))

    return SlideSpec(
        purpose=purpose,
        layout_name="MAIN",
        required_shapes=("title", "body"),
        optional_shapes=optional,
        slots=tuple(slots),
    )


IM_FULL = TemplateSpec(
    template_id="im-full-v1",
    doc_type="IM",
    variant="full",
    template_path="templates/sl_template.pptx",
    brand_tokens={
        "color_primary": "#0F3A32",
        "color_secondary": "#1C8F57",
        "color_accent": "#26C260",
        "color_fresh": "#A3E96B",
        "color_light": "#E6FDD6",
        "color_body_text": "#3D3D3D",
        "color_negative": "#BC2C1A",
        "color_caution": "#EF6C00",
        "font_heading": "SUITE",
        "font_body": "Pretendard",
        "font_cover_subtitle": "SUIT Medium",
        "font_fallback": "Noto Sans KR",
    },
    slides=(
        # ── 1. Cover ──
        SlideSpec(
            purpose="cover",
            layout_name="COVER",
            required_shapes=("project_name", "company_name", "date"),
            optional_shapes=("logo", "confidential"),
            slots=(
                SlotSpec(
                    name="project_name",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 2.0, _WIDTH, 1.0),
                    max_lines=2,
                    max_chars=60,
                    min_font_pt=40.0,
                    alignment="CENTER",
                ),
                SlotSpec(
                    name="company_name",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 3.2, _WIDTH, 0.6),
                    max_lines=1,
                    max_chars=50,
                    min_font_pt=24.0,
                    alignment="CENTER",
                ),
                SlotSpec(
                    name="date",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 4.0, _WIDTH, 0.4),
                    max_lines=1,
                    max_chars=30,
                    min_font_pt=16.0,
                    alignment="CENTER",
                ),
                SlotSpec(
                    name="logo",
                    content_type=SlotContentType.IMAGE,
                    bbox=(_LEFT, 0.6, 3.0, 0.5),
                    aspect_ratio_policy="CONTAIN",
                ),
                SlotSpec(
                    name="confidential",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 6.8, _WIDTH, 0.3),
                    max_lines=1,
                    min_font_pt=10.0,
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
                    max_lines=50,
                    min_font_pt=9.0,
                    shrink_policy=ShrinkPolicy.TRUNCATE,
                ),
            ),
        ),
        # ── 3. TOC Divider ──
        SlideSpec(
            purpose="toc_divider",
            layout_name="FOREST",
            required_shapes=("toc_title",),
            optional_shapes=("toc_items",),
            slots=(
                SlotSpec(
                    name="toc_title",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, _TOP, _WIDTH, 0.6),
                    max_lines=1,
                    min_font_pt=24.0,
                ),
                SlotSpec(
                    name="toc_items",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 1.8, _WIDTH, 4.5),
                    max_lines=20,
                    min_font_pt=14.0,
                ),
            ),
        ),
        # ── 4. Deal Overview ──
        _content_slide("deal_overview"),
        # ── 5. Executive Summary ──
        _content_slide("executive_summary"),
        # ── 6. Investment Highlights ──
        _content_slide("investment_highlights"),
        # ── 7. Company Overview ──
        SlideSpec(
            purpose="company_overview",
            layout_name="MAIN",
            required_shapes=("title", "body"),
            optional_shapes=("logo", "table"),
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
                    bbox=(_LEFT, _TOP, _WIDTH, 2.5),
                    min_font_pt=10.0,
                ),
                SlotSpec(
                    name="logo",
                    content_type=SlotContentType.IMAGE,
                    bbox=(7.5, 0.6, 2.5, 0.4),
                    aspect_ratio_policy="CONTAIN",
                ),
                SlotSpec(
                    name="table",
                    content_type=SlotContentType.TABLE,
                    bbox=(_LEFT, 3.8, _WIDTH, 2.7),
                    min_font_pt=9.0,
                ),
            ),
        ),
        # ── 8. Business Model ──
        _content_slide("business_model", has_image=True),
        # ── 9. Market Overview ──
        _content_slide("market_overview", has_chart=True),
        # ── 10. Business Overview ──
        _content_slide("business_overview", has_chart=True),
        # ── 11. Value Creation ──
        _content_slide("value_creation"),
        # ── 12. Growth Strategy ──
        _content_slide("growth_strategy"),
        # ── 13. Financial Analysis ──
        _content_slide("financial_analysis", has_table=True, has_chart=True),
        # ── 14. Valuation ──
        _content_slide("valuation", has_table=True, has_chart=True),
        # ── 15. Management Team ──
        SlideSpec(
            purpose="management_team",
            layout_name="MAIN",
            required_shapes=("title", "body"),
            optional_shapes=("photo",),
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
                SlotSpec(
                    name="photo",
                    content_type=SlotContentType.IMAGE,
                    bbox=(7.5, _TOP, 2.5, 2.0),
                    aspect_ratio_policy="CONTAIN",
                ),
            ),
        ),
        # ── 16. Shareholder Structure ──
        _content_slide("shareholder_structure", has_table=True, has_chart=True),
        # ── 17. Transaction Structure ──
        _content_slide("transaction_structure", has_table=True),
        # ── 18. Appendix ──
        SlideSpec(
            purpose="appendix",
            layout_name="MAIN",
            required_shapes=("title",),
            optional_shapes=("body", "table"),
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
                    min_font_pt=9.0,
                    overflow_policy=OverflowPolicy.TRUNCATE,
                ),
                SlotSpec(
                    name="table",
                    content_type=SlotContentType.TABLE,
                    bbox=(_LEFT, _TOP, _WIDTH, _BODY_HEIGHT),
                    min_font_pt=8.0,
                ),
            ),
        ),
        # ── 19. Contact ──
        SlideSpec(
            purpose="contact",
            layout_name="FOREST",
            required_shapes=("contact_info",),
            optional_shapes=("logo",),
            slots=(
                SlotSpec(
                    name="contact_info",
                    content_type=SlotContentType.TEXT,
                    bbox=(_LEFT, 2.0, _WIDTH, 4.0),
                    min_font_pt=12.0,
                    alignment="CENTER",
                ),
                SlotSpec(
                    name="logo",
                    content_type=SlotContentType.IMAGE,
                    bbox=(4.0, 1.0, 3.0, 0.5),
                    aspect_ratio_policy="CONTAIN",
                ),
            ),
        ),
    ),
)

register_spec(IM_FULL)
