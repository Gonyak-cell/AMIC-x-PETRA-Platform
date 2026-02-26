"""빈 TM/DM PPTX 템플릿 생성 스크립트.

원본 PPTX(SPICY TM)에서 슬라이드 마스터/레이아웃을 보존한 채,
모든 콘텐츠를 공란화([플레이스홀더])하여 빈 템플릿을 생성한다.

사용법:
    python im/scripts/generate_blank_templates.py

출력:
    im/templates/AMIC_TM_Template.pptx  (25 슬라이드)
    im/templates/AMIC_DM_Template.pptx  (7 슬라이드)
"""

from __future__ import annotations

import os
import sys
from copy import deepcopy
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Cm, Emu, Pt

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
IM_ROOT = SCRIPT_DIR.parent
TEMPLATE_DIR = IM_ROOT / "templates"

# Source template (SPICY TM has the most complete structure)
SOURCE_PPTX = TEMPLATE_DIR / "SPICY - TM - 260219 vSHARE.pptx"

OUTPUT_TM = TEMPLATE_DIR / "AMIC_TM_Template.pptx"
OUTPUT_DM = TEMPLATE_DIR / "AMIC_DM_Template.pptx"

# ---------------------------------------------------------------------------
# Design constants (from TM/DM analysis)
# ---------------------------------------------------------------------------

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

# Layout indices in source PPTX
LAYOUT_BLANK = 0
LAYOUT_FOREST = 1
LAYOUT_BLANK_PGNO = 2
LAYOUT_MAIN = 3
LAYOUT_MAIN_ANDERSEN = 4

# Coordinates (cm)
CONTENT_LEFT = 1.258
CONTENT_TOP_TITLE = 1.526
TITLE_WIDTH = 25.0
TITLE_HEIGHT = 1.197
SECTION_BAR_Y = 4.723
SECTION_BAR_HEIGHT = 0.8
CONTENT_START_Y = 6.024
CONTENT_END_Y = 16.5
LEFT_PANEL_WIDTH = 12.2
RIGHT_PANEL_X = 14.058
FULL_WIDTH = 25.0
CONFIDENTIAL_X = 20.875
CONFIDENTIAL_Y = 1.805
CONFIDENTIAL_W = 5.383
CONFIDENTIAL_H = 0.442
LOGO_X = 1.258
LOGO_Y = 1.526
LOGO_W_TM = 7.568
LOGO_H_TM = 1.0
LOGO_W_DM = 6.833
LOGO_H_DM = 1.2

# TOC 테이블 좌표 (실측: FOREST 레이아웃 내 목차)
TOC_TABLE_X = 0.957
TOC_TABLE_Y = 6.024
TOC_TABLE_W = 9.8
TOC_TABLE_H = 4.4

# 재무제표 시작 Y (실측: 타이틀 바 없이 직접 시작)
FINANCIAL_START_Y = 3.325

# Colors
COLOR_TITLE_BAR = "3D3D3D"
COLOR_SECTION_BAR = "0F3A32"
COLOR_ACCENT = "26C260"
COLOR_DARK_GREEN = "1C8F57"
COLOR_LIGHT_GREEN = "E6FDD6"
COLOR_WHITE = "FFFFFF"
COLOR_BODY = "3D3D3D"

# Fonts
FONT_HEADING = "SUITE Heavy"
FONT_COVER_SUB = "SUIT Medium"
FONT_BODY = "Pretendard"


def _get_layout(prs: Presentation, index: int):
    """슬라이드 레이아웃을 인덱스로 가져오기."""
    return prs.slide_masters[0].slide_layouts[index]


def _add_textbox(slide, left_cm, top_cm, width_cm, height_cm, text,
                 font_name=FONT_BODY, font_size_pt=10, bold=False,
                 color_hex=COLOR_BODY, alignment=PP_ALIGN.LEFT,
                 line_spacing_pct=None):
    """텍스트 박스를 슬라이드에 추가."""
    txBox = slide.shapes.add_textbox(
        Cm(left_cm), Cm(top_cm), Cm(width_cm), Cm(height_cm)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = alignment
    if line_spacing_pct is not None:
        p.line_spacing = Pt(0)  # reset
        p.space_before = Pt(0)
        p.space_after = Pt(0)
        # Set line spacing as percentage via XML
        pPr = p._pPr
        if pPr is None:
            pPr = p._p.get_or_add_pPr()
        lnSpc = pPr.find(qn("a:lnSpc"))
        if lnSpc is None:
            from lxml import etree
            lnSpc = etree.SubElement(pPr, qn("a:lnSpc"))
        # Remove existing children
        for child in list(lnSpc):
            lnSpc.remove(child)
        from lxml import etree
        spcPct = etree.SubElement(lnSpc, qn("a:spcPct"))
        spcPct.set("val", str(int(line_spacing_pct * 1000)))
    run = p.add_run()
    run.text = text
    run.font.name = font_name
    run.font.size = Pt(font_size_pt)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color_hex)
    return txBox


def _add_rect(slide, left_cm, top_cm, width_cm, height_cm, fill_hex,
              text="", font_size_pt=12, font_color_hex=COLOR_WHITE, bold=True):
    """채우기 색상이 있는 직사각형 도형 추가."""
    from pptx.enum.shapes import MSO_SHAPE
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Cm(left_cm), Cm(top_cm), Cm(width_cm), Cm(height_cm),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(fill_hex)
    shape.line.fill.background()
    if text:
        tf = shape.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = text
        run.font.name = FONT_BODY
        run.font.size = Pt(font_size_pt)
        run.font.bold = bold
        run.font.color.rgb = RGBColor.from_string(font_color_hex)
    return shape


def _add_section_bars(slide, left_title="[섹션 제목 좌]", right_title="[섹션 제목 우]"):
    """듀얼 패널 섹션 바 추가."""
    _add_rect(slide, CONTENT_LEFT, SECTION_BAR_Y, LEFT_PANEL_WIDTH,
              SECTION_BAR_HEIGHT, COLOR_SECTION_BAR, left_title)
    _add_rect(slide, RIGHT_PANEL_X, SECTION_BAR_Y, LEFT_PANEL_WIDTH,
              SECTION_BAR_HEIGHT, COLOR_SECTION_BAR, right_title)


def _add_placeholder_area(slide, left_cm, top_cm, width_cm, height_cm,
                          text="[콘텐츠 영역]"):
    """연한 배경의 플레이스홀더 영역 추가."""
    _add_rect(slide, left_cm, top_cm, width_cm, height_cm,
              COLOR_LIGHT_GREEN, text, font_size_pt=10,
              font_color_hex=COLOR_DARK_GREEN, bold=False)


def _build_blank_prs() -> Presentation:
    """원본 PPTX에서 마스터/레이아웃만 보존한 빈 프레젠테이션 생성."""
    if not SOURCE_PPTX.exists():
        print(f"ERROR: Source template not found: {SOURCE_PPTX}")
        sys.exit(1)

    # Load source to get master/layouts, then remove all slides
    prs = Presentation(str(SOURCE_PPTX))

    # Remove all existing slides
    while len(prs.slides) > 0:
        rId = prs.slides._sldIdLst[0].get(qn("r:id"))
        prs.part.drop_rel(rId)
        del prs.slides._sldIdLst[0]

    return prs


def _add_forest_slide(prs, title_text, subtitle_text="", date_text="",
                      confidential=True):
    """FOREST 레이아웃 슬라이드 추가 (표지/간지/면책/연락처)."""
    layout = _get_layout(prs, LAYOUT_FOREST)
    slide = prs.slides.add_slide(layout)

    # Title (표지: 줄간격 90%)
    _add_textbox(slide, CONTENT_LEFT, 6.0, 20.0, 3.0, title_text,
                 font_name=FONT_HEADING, font_size_pt=40, bold=True,
                 color_hex=COLOR_WHITE, line_spacing_pct=90)

    if subtitle_text:
        _add_textbox(slide, CONTENT_LEFT, 9.5, 20.0, 1.5, subtitle_text,
                     font_name=FONT_COVER_SUB, font_size_pt=24,
                     color_hex=COLOR_WHITE, line_spacing_pct=110)

    if date_text:
        _add_textbox(slide, CONTENT_LEFT, 11.5, 10.0, 1.0, date_text,
                     font_name=FONT_COVER_SUB, font_size_pt=16,
                     color_hex=COLOR_WHITE, line_spacing_pct=90)

    if confidential:
        _add_textbox(slide, CONFIDENTIAL_X, CONFIDENTIAL_Y,
                     CONFIDENTIAL_W, CONFIDENTIAL_H,
                     "Strictly Private & Confidential",
                     font_name=FONT_HEADING, font_size_pt=10,
                     color_hex=COLOR_WHITE, alignment=PP_ALIGN.RIGHT)

    return slide


def _add_main_slide(prs, title_text, use_andersen=False):
    """MAIN 레이아웃 슬라이드 추가."""
    layout_idx = LAYOUT_MAIN_ANDERSEN if use_andersen else LAYOUT_MAIN
    layout = _get_layout(prs, layout_idx)
    slide = prs.slides.add_slide(layout)

    # Title bar
    _add_rect(slide, CONTENT_LEFT, CONTENT_TOP_TITLE,
              TITLE_WIDTH, TITLE_HEIGHT, COLOR_TITLE_BAR,
              title_text, font_size_pt=16, font_color_hex=COLOR_WHITE)

    return slide


def _add_toc_table(slide, sections: list[tuple[str, str]]):
    """TOC 테이블을 실측 좌표에 추가."""
    from pptx.util import Cm, Pt

    rows = len(sections)
    cols = 2  # 번호 | 제목
    table_shape = slide.shapes.add_table(
        rows, cols,
        Cm(TOC_TABLE_X), Cm(TOC_TABLE_Y),
        Cm(TOC_TABLE_W), Cm(TOC_TABLE_H),
    )
    table = table_shape.table

    # 테이블 스타일 투명화 (FOREST 배경 위)
    tbl = table._tbl
    tblPr = tbl.tblPr
    if tblPr is None:
        from lxml import etree
        tblPr = etree.SubElement(tbl, qn("a:tblPr"))
    tblPr.set("bandRow", "0")
    tblPr.set("firstRow", "0")

    # 열 너비 설정 (실측: 번호 1.50cm / 섹션명 8.30cm)
    num_col_w = Cm(1.50)
    name_col_w = Cm(8.30)
    table.columns[0].width = num_col_w
    table.columns[1].width = name_col_w

    for i, (num, name) in enumerate(sections):
        for j, (text, bold) in enumerate([(num, True), (name, False)]):
            cell = table.cell(i, j)
            cell.text = ""
            # 셀 배경 투명
            tcPr = cell._tc.get_or_add_tcPr()
            # 테두리 제거
            for border_name in ["lnL", "lnR", "lnT", "lnB"]:
                ln = tcPr.find(qn(f"a:{border_name}"))
                if ln is not None:
                    tcPr.remove(ln)
                from lxml import etree
                ln = etree.SubElement(tcPr, qn(f"a:{border_name}"))
                noFill = etree.SubElement(ln, qn("a:noFill"))
            # 셀 배경 투명
            solidFill = tcPr.find(qn("a:solidFill"))
            if solidFill is not None:
                tcPr.remove(solidFill)
            from lxml import etree
            noFill = etree.SubElement(tcPr, qn("a:noFill"))

            p = cell.text_frame.paragraphs[0]
            run = p.add_run()
            run.text = text
            run.font.name = FONT_HEADING
            run.font.size = Pt(14)
            run.font.bold = bold
            run.font.color.rgb = RGBColor.from_string(COLOR_WHITE)


def _add_toc_slide(prs, sections: list[tuple[str, str]]):
    """TOC (Table of Contents) 슬라이드 추가.

    원본 실측: 제목 Y=3.80cm/24pt, TOC 테이블 Y=6.02cm.
    _add_forest_slide(Y=6.0/40pt)를 쓰면 제목과 테이블이 겹치므로 직접 생성.
    """
    layout = _get_layout(prs, LAYOUT_FOREST)
    slide = prs.slides.add_slide(layout)

    # 제목 (실측: X=1.26, Y=3.80, W=9.02, H=1.06, 24pt)
    _add_textbox(slide, 1.26, 3.80, 9.02, 1.06, "TABLE OF CONTENTS",
                 font_name=FONT_HEADING, font_size_pt=24, bold=True,
                 color_hex=COLOR_WHITE)

    # 실측 좌표 기반 TOC 테이블
    _add_toc_table(slide, sections)

    # Confidential at bottom
    _add_textbox(slide, CONTENT_LEFT, 17.159, 4.301, 0.365,
                 "Strictly Private & Confidential",
                 font_name=FONT_BODY, font_size_pt=8,
                 color_hex=COLOR_WHITE)

    return slide


def _add_divider_slide(prs, section_title: str):
    """간지(Divider) 슬라이드 추가."""
    slide = _add_forest_slide(prs, section_title, confidential=False)
    _add_textbox(slide, CONTENT_LEFT, 17.159, 4.301, 0.365,
                 "Strictly Private & Confidential",
                 font_name=FONT_BODY, font_size_pt=8,
                 color_hex=COLOR_WHITE)
    return slide


# ---------------------------------------------------------------------------
# TM Template Builder
# ---------------------------------------------------------------------------


def build_tm_template() -> None:
    """25슬라이드 TM 빈 템플릿 생성."""
    prs = _build_blank_prs()

    # 1. Cover
    _add_forest_slide(prs, "[PROJECT OO]", "[Teaser Memo]", "[Month Year]")

    # 2. Disclaimer
    slide = _add_forest_slide(prs, "DISCLAIMER", confidential=False)
    _add_textbox(slide, CONTENT_LEFT, 8.0, FULL_WIDTH, 8.0,
                 "[면책 조항 본문을 이곳에 입력하십시오.\n"
                 "본 자료는 기밀 정보를 포함하고 있으며, "
                 "수신인 이외의 자에 대한 공개, 배포 또는 복사를 금합니다.]",
                 font_name=FONT_BODY, font_size_pt=10, color_hex=COLOR_WHITE)

    # 3. TOC
    _add_toc_slide(prs, [
        ("01", "[Executive Summary]"),
        ("02", "[Market Opportunity]"),
        ("03", "[Target Highlights]"),
        ("04", "[Financial Summary]"),
    ])

    # 4. Executive Summary
    slide = _add_main_slide(prs, "Executive Summary")
    _add_section_bars(slide, "[기업 개요]", "[투자 하이라이트]")
    _add_placeholder_area(slide, CONTENT_LEFT, CONTENT_START_Y,
                          LEFT_PANEL_WIDTH, 10.5, "[기업 정보 표]")
    _add_placeholder_area(slide, RIGHT_PANEL_X, CONTENT_START_Y,
                          LEFT_PANEL_WIDTH, 10.5, "[투자 하이라이트 도형]")

    # 5. Target Positioning
    slide = _add_main_slide(prs, "Target Positioning")
    _add_placeholder_area(slide, CONTENT_LEFT, CONTENT_START_Y,
                          FULL_WIDTH, 10.5, "[포지셔닝 맵 영역]")

    # 6. Investment Highlights
    slide = _add_main_slide(prs, "Investment Highlights")
    _add_placeholder_area(slide, CONTENT_LEFT, CONTENT_START_Y,
                          FULL_WIDTH, 10.5, "[투자 하이라이트 상세]")

    # 7. Divider - Market Opportunity
    _add_divider_slide(prs, "[II. Market Opportunity]")

    # 8-12. Market Analysis (5 slides)
    for i, title in enumerate([
        "Market Overview",
        "Demand Analysis",
        "Supply Analysis",
        "Competitive Landscape",
        "Market Outlook",
    ]):
        slide = _add_main_slide(prs, f"[{title}]")
        _add_section_bars(slide, f"[{title}]", "[분석 요약]")
        _add_placeholder_area(slide, CONTENT_LEFT, CONTENT_START_Y,
                              LEFT_PANEL_WIDTH, 10.8, "[차트 플레이스홀더]")
        _add_placeholder_area(slide, RIGHT_PANEL_X, CONTENT_START_Y,
                              LEFT_PANEL_WIDTH, 10.8, "[텍스트 해설]")

    # 13. Divider - Target Highlights
    _add_divider_slide(prs, "[III. Target Highlights]")

    # 14-19. Target Details (6 slides)
    for title in [
        "Business Overview",
        "Product / Service",
        "Competitive Advantage",
        "Customer Base",
        "Growth Strategy",
        "Roadmap",
    ]:
        slide = _add_main_slide(prs, f"[{title}]")
        _add_section_bars(slide, f"[{title}]", "[상세 분석]")
        _add_placeholder_area(slide, CONTENT_LEFT, CONTENT_START_Y,
                              LEFT_PANEL_WIDTH, 10.5, "[표/차트 플레이스홀더]")
        _add_placeholder_area(slide, RIGHT_PANEL_X, CONTENT_START_Y,
                              LEFT_PANEL_WIDTH, 10.5, "[텍스트/도형 플레이스홀더]")

    # 20. Divider - Financial Summary
    _add_divider_slide(prs, "[IV. Financial Summary]")

    # 21-24. Financial Statements (4 slides)
    # 재무제표: 섹션바 없이 FINANCIAL_START_Y(3.325cm)부터 직접 시작
    financial_content_h = CONTENT_END_Y - FINANCIAL_START_Y
    for title in [
        "Income Statement (Historical)",
        "Income Statement (Projected)",
        "Balance Sheet",
        "Key Financial Metrics",
    ]:
        slide = _add_main_slide(prs, f"[{title}]")
        # 재무제표는 섹션바 없이 전체 너비 표로 직접 시작
        _add_placeholder_area(slide, CONTENT_LEFT, FINANCIAL_START_Y,
                              FULL_WIDTH, financial_content_h,
                              f"[{title} 표 플레이스홀더]")

    # 25. Contact
    slide = _add_forest_slide(prs, "", confidential=False)
    _add_textbox(slide, CONTENT_LEFT, 4.0, 10.0, 2.0,
                 "[회사명]\n[담당자명]  [직책]  [이메일]",
                 font_name=FONT_BODY, font_size_pt=10, color_hex=COLOR_WHITE)

    prs.save(str(OUTPUT_TM))
    print(f"TM template saved: {OUTPUT_TM} ({len(prs.slides)} slides)")


# ---------------------------------------------------------------------------
# DM Template Builder
# ---------------------------------------------------------------------------


def build_dm_template() -> None:
    """7슬라이드 DM 빈 템플릿 생성."""
    prs = _build_blank_prs()

    # 1. Cover
    _add_forest_slide(prs, "[PROJECT OO]", "[Discussion Memo]", "[Month Year]")

    # 2-6. Analysis slides
    for title in [
        "Market & Transaction Trends",
        "Deal Structure Considerations",
        "Investment Thesis",
        "Valuation Analysis",
        "Risk Assessment",
    ]:
        slide = _add_main_slide(prs, f"[{title}]")
        _add_section_bars(slide, f"[{title}]", "[분석 요약]")
        _add_placeholder_area(slide, CONTENT_LEFT, CONTENT_START_Y,
                              LEFT_PANEL_WIDTH, 10.5, "[표/차트 플레이스홀더]")
        _add_placeholder_area(slide, RIGHT_PANEL_X, CONTENT_START_Y,
                              LEFT_PANEL_WIDTH, 10.5, "[텍스트/도형 플레이스홀더]")

    # 7. Summary
    slide = _add_main_slide(prs, "[Summary & Recommendations]")
    _add_placeholder_area(slide, CONTENT_LEFT, CONTENT_START_Y,
                          FULL_WIDTH, 10.5, "[요약 및 결론]")

    prs.save(str(OUTPUT_DM))
    print(f"DM template saved: {OUTPUT_DM} ({len(prs.slides)} slides)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print(f"Source: {SOURCE_PPTX}")
    print(f"Output dir: {TEMPLATE_DIR}")
    build_tm_template()
    build_dm_template()
    print("Done.")
