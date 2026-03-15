"""
memo_generator.py — 통합 메모랜덤 생성 엔진 (TM / DM / IM / Proposal)

원본: M&A .claude/scripts/memo_generator.py
개선: deal-mgmt FastAPI 통합, 경로 추상화, GenerationResult 반환, 예외 처리 강화

마스터 템플릿(Forest 테마)을 기반으로 PPTX를 생성한다.
각 슬라이드의 디자인(로고, 색상, 폰트, 배경)은 템플릿에서 자동 상속된다.

JSON 콘텐츠 형식:
    {
        "project_name": "PROJECT ALPHA",
        "memo_type": "Teaser Memo",
        "date": "February 2026",
        "disclaimer": "본 자료(이하 ...)는 ...",
        "slides": [
            {
                "layout": "MAIN",
                "title": "Executive Summary",
                "body": [
                    {"type": "text", "content": "본문 내용..."},
                    {"type": "section_header", "content": "섹션 제목"},
                    {"type": "table", "headers": [...], "rows": [...]},
                    {"type": "bullet", "items": ["항목1", "항목2"]}
                ],
                "note": "하단 주석 (선택)"
            }
        ]
    }
"""

import os
from dataclasses import dataclass
from pathlib import Path

# ── 경로 상수 ──────────────────────────────────────────────────

_THIS_DIR = Path(__file__).parent
TEMPLATES_DIR = _THIS_DIR.parent.parent / "templates" / "memorandum"
TEMPLATE_PATH = TEMPLATES_DIR / "memorandum_master.pptx"
LOGO_PATH = TEMPLATES_DIR / "logo.png"

# ── 디자인 상수 (MA26-SPI-02 TM 분석 결과 기준) ──────────────────

SLIDE_WIDTH_INCHES = 10.8333
SLIDE_HEIGHT_INCHES = 7.5

LEFT_MARGIN = 0.4954
LOGO_TOP = 0.6007
LOGO_WIDTH = 2.9794
LOGO_HEIGHT = 0.3937
CONTENT_TOP = 1.25
CONTENT_WIDTH = 9.8425

COLOR_DARK = "3D3D3D"
COLOR_BLACK = "000000"
COLOR_WHITE = "FFFFFF"
COLOR_GRAY = "808080"
COLOR_SECTION_BG = "0F3A32"
COLOR_GREEN_PRIMARY = "0F3A32"
COLOR_GREEN_ACCENT = "1C8F57"
COLOR_GREEN_BRIGHT = "26C260"
COLOR_GRAY_MID = "6A6A6A"
COLOR_RED_ACCENT = "BC2C1A"

FONT_THEME = "+mj-lt"
FONT_SUIT = "SUIT Medium"
FONT_FALLBACK = "맑은 고딕"

PH_TITLE = 11
PH_NOTE = 12
PH_SLIDE_NUM = 13

BORDER_SOLID = "solid"
BORDER_DASH = "dash"


# ── 결과 반환 ──────────────────────────────────────────────────


@dataclass
class GenerationResult:
    """메모랜덤 생성 결과"""

    output_path: str
    file_name: str
    file_size_bytes: int
    slide_count: int
    memo_type: str
    project_code: str
    template_load_ms: int = 0
    render_ms: int = 0
    persist_ms: int = 0


# ── 헬퍼 함수 ──────────────────────────────────────────────────


LAYOUT_ALIASES: dict[str, list[str]] = {
    "COVER": ["COVER", "BLANK", "BLANK_PGNO"],
    "MAIN": ["MAIN", "MAIN_w/Andersen"],
    "FOREST": ["FOREST"],
}


def get_layout(prs, layout_name):
    """레이아웃을 별칭 순서대로 탐색한다."""
    candidates = LAYOUT_ALIASES.get(layout_name, [layout_name])
    for candidate in candidates:
        for master in prs.slide_masters:
            for layout in master.slide_layouts:
                if layout.name == candidate:
                    return layout
    raise ValueError(f"레이아웃 '{layout_name}'을 찾을 수 없습니다 (후보: {candidates}).")


def validate_template() -> list[str]:
    """템플릿 파일 존재 + 필수 레이아웃 해석 가능 여부를 검증한다."""
    from pptx import Presentation

    warnings: list[str] = []
    if not TEMPLATE_PATH.exists():
        warnings.append(f"템플릿 파일 누락: {TEMPLATE_PATH}")
        return warnings
    prs = Presentation(str(TEMPLATE_PATH))
    for alias_name in LAYOUT_ALIASES:
        try:
            get_layout(prs, alias_name)
        except ValueError as e:
            warnings.append(str(e))
    return warnings


def add_logo(slide):
    from pptx.util import Inches

    logo = str(LOGO_PATH)
    if os.path.exists(logo):
        slide.shapes.add_picture(logo, Inches(LEFT_MARGIN), Inches(LOGO_TOP), Inches(LOGO_WIDTH), Inches(LOGO_HEIGHT))


def set_theme_color(run, theme_color_name="BACKGROUND_1"):
    from pptx.enum.dml import MSO_THEME_COLOR

    theme_map = {
        "BACKGROUND_1": MSO_THEME_COLOR.BACKGROUND_1,
        "TEXT_1": MSO_THEME_COLOR.TEXT_1,
        "BACKGROUND_2": MSO_THEME_COLOR.BACKGROUND_2,
        "TEXT_2": MSO_THEME_COLOR.TEXT_2,
        "ACCENT_1": MSO_THEME_COLOR.ACCENT_1,
    }
    run.font.color.theme_color = theme_map.get(theme_color_name, MSO_THEME_COLOR.BACKGROUND_1)


def add_confidential_footer(slide, position="bottom", on_forest=False):
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    if position == "top_right":
        left, top = Inches(8.2185), Inches(0.7106)
        width, height = Inches(2.1195), Inches(0.1739)
        size = Pt(10)
        align = PP_ALIGN.RIGHT
    else:
        left, top = Inches(LEFT_MARGIN), Inches(6.7556)
        width, height = Inches(1.6935), Inches(0.1438)
        size = Pt(8)
        align = PP_ALIGN.LEFT

    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Strictly Private & Confidential"
    p.alignment = align
    run = p.runs[0]
    run.font.size = size
    if on_forest:
        set_theme_color(run, "BACKGROUND_1")
    else:
        run.font.color.rgb = RGBColor.from_string(COLOR_DARK)


def set_font(run, name=None, size_pt=None, bold=None, italic=None, color=None, theme_color=None):
    from pptx.dml.color import RGBColor
    from pptx.util import Pt

    if name:
        run.font.name = name
    if size_pt:
        run.font.size = Pt(size_pt)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if theme_color:
        set_theme_color(run, theme_color)
    elif color:
        run.font.color.rgb = RGBColor.from_string(color)


def add_textbox(
    slide,
    left,
    top,
    width,
    height,
    text,
    font_name=None,
    font_size=None,
    bold=None,
    color=None,
    alignment=None,
    word_wrap=True,
    theme_color=None,
):
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches

    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = word_wrap

    p = tf.paragraphs[0]
    p.text = text

    align_map = {
        "left": PP_ALIGN.LEFT,
        "center": PP_ALIGN.CENTER,
        "right": PP_ALIGN.RIGHT,
        "justify": PP_ALIGN.JUSTIFY,
    }
    for para in tf.paragraphs:
        if alignment:
            para.alignment = align_map.get(alignment, PP_ALIGN.LEFT)
        for run in para.runs:
            set_font(run, name=font_name, size_pt=font_size, bold=bold, color=color, theme_color=theme_color)

    return txBox


def add_rich_text_box(slide, left, top, width, height, runs, word_wrap=True, base_font_size=11, line_spacing=1.15):
    from pptx.util import Inches

    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = word_wrap

    p = tf.paragraphs[0]
    p.line_spacing = line_spacing

    for run_data in runs:
        text = run_data.get("text", "")
        r = p.add_run()
        r.text = text
        size = run_data.get("font_size", base_font_size)
        bold = run_data.get("bold", False)
        underline = run_data.get("underline", False)
        color = run_data.get("color", None)
        theme_c = run_data.get("theme_color", None)
        set_font(r, size_pt=size, bold=bold, color=color, theme_color=theme_c)
        if underline:
            r.font.underline = True

    return txBox


def add_table(slide, left, top, width, height, headers, rows):
    from pptx.dml.color import RGBColor
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Inches

    n_cols = len(headers)
    n_rows = len(rows) + 1
    tbl_shape = slide.shapes.add_table(n_rows, n_cols, Inches(left), Inches(top), Inches(width), Inches(height))
    table = tbl_shape.table

    col_w = Inches(width / n_cols)
    for i in range(n_cols):
        table.columns[i].width = col_w

    # 헤더 행
    for j, hdr in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = hdr
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor.from_string(COLOR_GREEN_PRIMARY)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        for para in cell.text_frame.paragraphs:
            para.alignment = PP_ALIGN.CENTER
            for run in para.runs:
                set_font(run, size_pt=10, bold=True, theme_color="BACKGROUND_1")

    # 데이터 행
    for i, row in enumerate(rows):
        for j, val in enumerate(row[:n_cols]):
            cell = table.cell(i + 1, j)
            cell.text = str(val)
            cell.fill.background()
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            for para in cell.text_frame.paragraphs:
                para.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
                for run in para.runs:
                    set_font(run, size_pt=10, color=COLOR_DARK)

    return tbl_shape


def add_section_header_shape(slide, left, top, width, text, bg_color=None):
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Emu, Inches

    bg = bg_color or COLOR_GREEN_PRIMARY
    height = 0.35
    rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    rect.fill.solid()
    rect.fill.fore_color.rgb = RGBColor.from_string(bg)
    rect.line.fill.background()

    tf = rect.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Emu(91440)
    tf.margin_right = Emu(91440)
    tf.margin_top = Emu(36000)
    tf.margin_bottom = Emu(36000)

    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = text
    set_font(run, size_pt=11, bold=True, theme_color="BACKGROUND_1")

    return rect


def _clear_table_style(table):
    """테이블 기본 스타일 초기화"""
    from pptx.oxml.ns import qn

    tbl_pr = table._tbl.find(qn("a:tblPr"))
    if tbl_pr is not None:
        style_elem = tbl_pr.find(qn("a:tableStyleId"))
        if style_elem is not None:
            tbl_pr.remove(style_elem)


def _set_cell_border(cell, top=None, bottom=None, left_side=None, right_side=None):
    """셀 테두리 스타일 설정"""
    from lxml import etree
    from pptx.oxml.ns import qn

    tc = cell._tc
    tc_pr = tc.find(qn("a:tcPr"))
    if tc_pr is None:
        tc_pr = etree.SubElement(tc, qn("a:tcPr"))

    border_map = {"lnT": top, "lnB": bottom, "lnL": left_side, "lnR": right_side}
    for tag, style in border_map.items():
        if style is None:
            continue
        ln = tc_pr.find(qn(f"a:{tag}"))
        if ln is None:
            ln = etree.SubElement(tc_pr, qn(f"a:{tag}"))
        # 기존 자식 제거
        for child in list(ln):
            ln.remove(child)
        ln.set("w", "9525")
        ln.set("cap", "flat")
        ln.set("cmpd", "sng")

        sf = etree.SubElement(ln, qn("a:solidFill"))
        sc = etree.SubElement(sf, qn("a:srgbClr"))
        sc.set("val", COLOR_GRAY_MID)

        prstDash = etree.SubElement(ln, qn("a:prstDash"))
        if style == "dash":
            prstDash.set("val", "sysDash")
        else:
            prstDash.set("val", "solid")


def add_info_table_block(
    slide,
    left,
    top,
    width,
    label,
    fields,
    financial=None,
    bullet_values=None,
    label_w=1.5,
    field_col_w=1.5,
    row_h=0.35,
    fin_row_h=0.65,
):
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Emu, Inches

    table_w = width - label_w
    value_col_w = table_w - field_col_w

    if bullet_values is not None:
        block_h = max(len(bullet_values) * 0.28, row_h)
        lbl_w = label_w

        lbl_shape = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(lbl_w), Inches(block_h))
        tf = lbl_shape.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = Emu(54000)

        lines = label.split("\n")
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            run.text = line
            set_font(run, size_pt=10 if i == 0 else 8, bold=(i == 0), color=COLOR_GREEN_ACCENT)

        val_left = left + lbl_w
        val_w = width - lbl_w
        txBox = slide.shapes.add_textbox(Inches(val_left), Inches(top), Inches(val_w), Inches(block_h))
        tf2 = txBox.text_frame
        tf2.word_wrap = True
        tf2.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf2.margin_left = Emu(54000)
        for i, val in enumerate(bullet_values):
            p2 = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
            run = p2.add_run()
            run.text = val
            set_font(run, size_pt=10, color=COLOR_DARK)
            p2.space_after = Emu(18000)

        return top + block_h + 0.10

    n_fields = len(fields)
    has_fin = financial is not None
    total_h = n_fields * row_h + (fin_row_h if has_fin else 0)
    n_rows = n_fields + (1 if has_fin else 0)

    lbl_shape = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(label_w), Inches(total_h))
    tf = lbl_shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Emu(18000)
    tf.margin_right = Emu(18000)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = label
    set_font(run, size_pt=10, bold=True, color=COLOR_GREEN_ACCENT)

    if fields:
        tbl_shape = slide.shapes.add_table(
            n_rows, 2, Inches(left + label_w), Inches(top), Inches(table_w), Inches(total_h)
        )
        table = tbl_shape.table
        _clear_table_style(table)

        table.columns[0].width = Inches(field_col_w)
        table.columns[1].width = Inches(value_col_w)

        for i in range(n_rows):
            if has_fin and i == n_rows - 1:
                table.rows[i].height = Inches(fin_row_h)
            else:
                table.rows[i].height = Inches(row_h)

        for i, (fname, fval) in enumerate(fields):
            is_first = i == 0
            is_last_row = i == n_fields - 1 and not has_fin
            top_bdr = BORDER_SOLID if is_first else BORDER_DASH
            bot_bdr = BORDER_SOLID if is_last_row else BORDER_DASH

            c0 = table.cell(i, 0)
            c0.text = fname
            c0.fill.background()
            c0.vertical_anchor = MSO_ANCHOR.MIDDLE
            c0.text_frame.margin_left = Emu(54000)
            c0.text_frame.margin_right = Emu(18000)
            c0.text_frame.margin_top = Emu(18000)
            c0.text_frame.margin_bottom = Emu(18000)
            for para in c0.text_frame.paragraphs:
                para.alignment = PP_ALIGN.LEFT
                for run in para.runs:
                    set_font(run, size_pt=10, bold=True, color=COLOR_GREEN_ACCENT)
            _set_cell_border(c0, top=top_bdr, bottom=bot_bdr)

            c1 = table.cell(i, 1)
            c1.text = fval
            c1.fill.background()
            c1.vertical_anchor = MSO_ANCHOR.MIDDLE
            c1.text_frame.margin_left = Emu(54000)
            c1.text_frame.margin_right = Emu(36000)
            c1.text_frame.margin_top = Emu(18000)
            c1.text_frame.margin_bottom = Emu(18000)
            for para in c1.text_frame.paragraphs:
                para.alignment = PP_ALIGN.LEFT
                for run in para.runs:
                    set_font(run, size_pt=10, color=COLOR_DARK)
            _set_cell_border(c1, top=top_bdr, bottom=bot_bdr)

    return top + total_h + 0.10


# ── 슬라이드 생성 함수 ──────────────────────────────────────────


def create_cover_slide(prs, project_name, memo_type_label, date_str):

    layout = get_layout(prs, "COVER")
    slide = prs.slides.add_slide(layout)

    add_logo(slide)

    add_textbox(slide, LEFT_MARGIN, 2.8, 8.0, 0.8, project_name, font_size=36, bold=True, theme_color="BACKGROUND_1")

    add_textbox(
        slide, LEFT_MARGIN, 3.7, 8.0, 0.5, memo_type_label, font_size=20, bold=False, theme_color="BACKGROUND_1"
    )

    if date_str:
        add_textbox(slide, LEFT_MARGIN, 4.3, 4.0, 0.4, date_str, font_size=14, theme_color="BACKGROUND_1")

    add_confidential_footer(slide, position="top_right", on_forest=True)

    return slide


def create_disclaimer_slide(prs, disclaimer_text, date_label="", company_name=""):
    from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN
    from pptx.util import Emu, Inches

    layout = get_layout(prs, "FOREST")
    slide = prs.slides.add_slide(layout)

    title_box = slide.shapes.add_textbox(Inches(LEFT_MARGIN), Inches(LOGO_TOP), Inches(1.548), Inches(0.3124))
    title_tf = title_box.text_frame
    title_tf.word_wrap = False
    title_tf.auto_size = MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT
    title_tf.margin_left = title_tf.margin_right = 0
    title_tf.margin_top = title_tf.margin_bottom = 0
    p = title_tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = "DISCLAIMER"
    run.font.name = FONT_THEME
    set_theme_color(run, "BACKGROUND_1")

    body_box = slide.shapes.add_textbox(Inches(LEFT_MARGIN), Inches(1.191), Inches(4.7251), Inches(3.5758))
    body_tf = body_box.text_frame
    body_tf.word_wrap = True
    body_tf.auto_size = MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT
    body_tf.margin_left = body_tf.margin_right = 0
    body_tf.margin_top = body_tf.margin_bottom = 0

    SPACE_AFTER = Emu(76200)
    SPACE_AFTER_CO = Emu(38100)

    paras = disclaimer_text.split("\n\n") if "\n\n" in disclaimer_text else [disclaimer_text]
    for i, para_text in enumerate(paras):
        p = body_tf.paragraphs[0] if i == 0 else body_tf.add_paragraph()
        p.alignment = PP_ALIGN.JUSTIFY
        p.space_after = SPACE_AFTER
        p.line_spacing = 1.1
        run = p.add_run()
        run.text = para_text.strip()
        set_font(run, size_pt=8, theme_color="BACKGROUND_1")

    ep1 = body_tf.add_paragraph()
    ep1.space_after = SPACE_AFTER
    ep1.line_spacing = 1.1

    if date_label:
        dp = body_tf.add_paragraph()
        dp.alignment = PP_ALIGN.JUSTIFY
        dp.space_after = SPACE_AFTER
        dp.line_spacing = 1.1
        run = dp.add_run()
        run.text = date_label
        set_font(run, size_pt=8, theme_color="BACKGROUND_1")

    ep2 = body_tf.add_paragraph()
    ep2.space_after = SPACE_AFTER
    ep2.line_spacing = 1.1

    if company_name:
        cp = body_tf.add_paragraph()
        cp.alignment = PP_ALIGN.JUSTIFY
        cp.space_after = SPACE_AFTER_CO
        cp.line_spacing = 1.1
        run = cp.add_run()
        run.text = company_name
        set_font(run, size_pt=10, bold=True, theme_color="BACKGROUND_1")

    return slide


def create_toc_slide(prs, sections, current_section=0):

    layout = get_layout(prs, "FOREST")
    slide = prs.slides.add_slide(layout)

    add_logo(slide)

    add_textbox(
        slide,
        LEFT_MARGIN,
        1.497,
        3.5517,
        0.4166,
        "TABLE OF CONTENTS",
        font_size=24,
        bold=True,
        theme_color="BACKGROUND_1",
    )

    add_confidential_footer(slide, position="bottom", on_forest=True)

    _build_toc_table_xml(slide, sections, current_section)

    return slide


def _build_toc_table_xml(slide, sections, current_section=0):
    from lxml import etree
    from pptx.oxml.ns import qn
    from pptx.util import Inches

    n_rows = len(sections)
    col0_w = 540000
    col1_w = 2988000
    row_h = 396000

    left = Inches(0.3767)
    top = Inches(2.3715)

    sp_tree = slide.shapes._spTree

    graphic_frame = etree.SubElement(sp_tree, qn("p:graphicFrame"))
    nv = etree.SubElement(graphic_frame, qn("p:nvGraphicFramePr"))
    cnv = etree.SubElement(nv, qn("p:cNvPr"))
    cnv.set("id", "100")
    cnv.set("name", "TOC Table")
    cnv_gf = etree.SubElement(nv, qn("p:cNvGraphicFramePr"))
    gf_locks = etree.SubElement(cnv_gf, qn("a:graphicFrameLocks"))
    gf_locks.set("noGrp", "1")
    etree.SubElement(nv, qn("p:nvPr"))

    xfrm = etree.SubElement(graphic_frame, qn("p:xfrm"))
    off = etree.SubElement(xfrm, qn("a:off"))
    off.set("x", str(int(left)))
    off.set("y", str(int(top)))
    ext = etree.SubElement(xfrm, qn("a:ext"))
    ext.set("cx", str(col0_w + col1_w))
    ext.set("cy", str(row_h * n_rows))

    graphic = etree.SubElement(graphic_frame, qn("a:graphic"))
    graphic_data = etree.SubElement(graphic, qn("a:graphicData"))
    graphic_data.set("uri", "http://schemas.openxmlformats.org/drawingml/2006/table")

    tbl = etree.SubElement(graphic_data, qn("a:tbl"))
    tbl_pr = etree.SubElement(tbl, qn("a:tblPr"))
    tbl_pr.set("firstRow", "1")
    tbl_pr.set("bandRow", "1")
    style_id = etree.SubElement(tbl_pr, qn("a:tableStyleId"))
    style_id.text = "{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"

    tbl_grid = etree.SubElement(tbl, qn("a:tblGrid"))
    gc0 = etree.SubElement(tbl_grid, qn("a:gridCol"))
    gc0.set("w", str(col0_w))
    gc1 = etree.SubElement(tbl_grid, qn("a:gridCol"))
    gc1.set("w", str(col1_w))

    for i, section_title in enumerate(sections):
        is_current = i == current_section
        number_str = str(i + 1).zfill(2)

        tr = etree.SubElement(tbl, qn("a:tr"))
        tr.set("h", str(row_h))

        for col_idx, cell_text in enumerate([number_str, section_title]):
            is_col0 = col_idx == 0
            tc = etree.SubElement(tr, qn("a:tc"))

            txBody = etree.SubElement(tc, qn("a:txBody"))
            etree.SubElement(txBody, qn("a:bodyPr"))
            etree.SubElement(txBody, qn("a:lstStyle"))
            par = etree.SubElement(txBody, qn("a:p"))
            pPr = etree.SubElement(par, qn("a:pPr"))
            pPr.set("marL", "0")
            pPr.set("indent", "0")

            r = etree.SubElement(par, qn("a:r"))
            rPr = etree.SubElement(r, qn("a:rPr"))
            rPr.set("lang", "ko-KR")
            rPr.set("altLang", "en-US")
            rPr.set("sz", "1400")
            rPr.set("b", "0")
            rPr.set("spc", "0")
            rPr.set("baseline", "0")
            rPr.set("dirty", "0")

            t = etree.SubElement(r, qn("a:t"))
            t.text = cell_text

            if is_current:
                rPr.set("kern", "1200")
                rPr.set("cap", "all")
                ef = etree.SubElement(rPr, qn("a:solidFill"))
                ec = etree.SubElement(ef, qn("a:srgbClr"))
                ec.set("val", COLOR_GREEN_PRIMARY)
            else:
                rPr.set("cap", "none")
                ef = etree.SubElement(rPr, qn("a:solidFill"))
                ec = etree.SubElement(ef, qn("a:schemeClr"))
                ec.set("val", "bg1")

            el = etree.SubElement(rPr, qn("a:latin"))
            el.set("typeface", FONT_THEME)

            end_pr = etree.SubElement(par, qn("a:endParaRPr"))
            end_pr.set("lang", "ko-KR")
            end_pr.set("dirty", "0")

            tc_pr = etree.SubElement(tc, qn("a:tcPr"))
            tc_pr.set("marR", "0")
            tc_pr.set("marT", "0")
            tc_pr.set("marB", "0")
            tc_pr.set("anchor", "ctr")
            tc_pr.set("marL", "108000" if is_col0 else "0")

            if is_current:
                sf = etree.SubElement(tc_pr, qn("a:solidFill"))
                sc = etree.SubElement(sf, qn("a:schemeClr"))
                sc.set("val", "bg1")
            else:
                etree.SubElement(tc_pr, qn("a:noFill"))


def create_section_divider_slide(prs, section_number, section_title):
    layout = get_layout(prs, "FOREST")
    slide = prs.slides.add_slide(layout)

    add_logo(slide)

    add_textbox(
        slide,
        LEFT_MARGIN,
        3.0,
        1.0,
        0.5,
        str(section_number).zfill(2),
        font_size=48,
        bold=True,
        theme_color="BACKGROUND_1",
    )

    add_textbox(slide, LEFT_MARGIN, 3.6, 5.0, 0.5, section_title, font_size=28, bold=True, theme_color="BACKGROUND_1")

    add_confidential_footer(slide, position="bottom", on_forest=True)

    return slide


def create_main_slide(prs, title, body_elements=None, note=None):

    layout = get_layout(prs, "MAIN")
    slide = prs.slides.add_slide(layout)

    for ph in slide.placeholders:
        if ph.placeholder_format.idx == PH_TITLE:
            ph.text = title
            for para in ph.text_frame.paragraphs:
                for run in para.runs:
                    set_font(run, size_pt=18, bold=True, color=COLOR_DARK)
            break

    if note:
        for ph in slide.placeholders:
            if ph.placeholder_format.idx == PH_NOTE:
                ph.text = note
                for para in ph.text_frame.paragraphs:
                    for run in para.runs:
                        set_font(run, size_pt=8, color=COLOR_GRAY)
                break

    if body_elements:
        current_top = CONTENT_TOP
        for elem in body_elements:
            current_top = _place_body_element(slide, elem, current_top)

    return slide


def _place_body_element(slide, elem, current_top):
    from pptx.util import Inches

    elem_type = elem.get("type", "text")

    if elem_type == "text":
        content = elem.get("content", "")
        font_size = elem.get("font_size", 14)
        bold = elem.get("bold", False)
        lines = max(1, len(content) // 80 + 1)
        height = lines * 0.25
        add_textbox(
            slide,
            LEFT_MARGIN,
            current_top,
            CONTENT_WIDTH,
            height,
            content,
            font_size=font_size,
            bold=bold,
            color=COLOR_DARK,
            alignment="left",
        )
        return current_top + height + 0.15

    elif elem_type == "section_header":
        content = elem.get("content", "")
        width = elem.get("width", CONTENT_WIDTH / 2)
        bg_color = elem.get("bg_color", None)
        add_section_header_shape(slide, LEFT_MARGIN, current_top, width, content, bg_color=bg_color)
        return current_top + 0.45

    elif elem_type == "bullet":
        items = elem.get("items", [])
        underline = elem.get("underline", False)
        font_size = elem.get("font_size", 11)
        height = len(items) * 0.3
        txBox = add_textbox(
            slide,
            LEFT_MARGIN + 0.2,
            current_top,
            CONTENT_WIDTH - 0.2,
            height,
            "",
            font_size=font_size,
            color=COLOR_DARK,
        )
        tf = txBox.text_frame
        tf.clear()
        for i, item in enumerate(items):
            p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
            pfx = elem.get("prefix", "•")
            p.text = f"{pfx}  {item}"
            if p.runs:
                set_font(p.runs[0], size_pt=font_size, color=COLOR_DARK)
                if underline:
                    p.runs[0].font.underline = True
            p.space_after = Inches(0.05)
        return current_top + height + 0.15

    elif elem_type == "table":
        headers = elem.get("headers", [])
        rows = elem.get("rows", [])
        if headers and rows:
            height = min((len(rows) + 1) * 0.35, 4.0)
            add_table(slide, LEFT_MARGIN, current_top, CONTENT_WIDTH, height, headers, rows)
            return current_top + height + 0.2

    elif elem_type == "rich_text":
        runs = elem.get("runs", [])
        font_size = elem.get("font_size", 11)
        lines = max(1, sum(len(r.get("text", "")) for r in runs) // 80 + 1)
        height = lines * 0.25
        add_rich_text_box(slide, LEFT_MARGIN, current_top, CONTENT_WIDTH, height, runs, base_font_size=font_size)
        return current_top + height + 0.15

    elif elem_type == "info_block":
        label = elem.get("label", "")
        fields = elem.get("fields", [])
        financial = elem.get("financial", None)
        bullet_values = elem.get("bullet_values", None)
        return add_info_table_block(
            slide,
            LEFT_MARGIN,
            current_top,
            CONTENT_WIDTH,
            label,
            fields,
            financial=financial,
            bullet_values=bullet_values,
        )

    elif elem_type == "two_column":
        left_items = elem.get("left", [])
        right_items = elem.get("right", [])
        col_width = CONTENT_WIDTH / 2 - 0.1
        max_top = current_top
        col_top = current_top
        for item in left_items:
            col_top = _place_body_element_at(slide, item, LEFT_MARGIN, col_top, col_width)
        max_top = max(max_top, col_top)
        col_top = current_top
        right_left = LEFT_MARGIN + col_width + 0.2
        for item in right_items:
            col_top = _place_body_element_at(slide, item, right_left, col_top, col_width)
        max_top = max(max_top, col_top)
        return max_top + 0.15

    return current_top + 0.3


def _place_body_element_at(slide, elem, left, top, width):

    elem_type = elem.get("type", "text")

    if elem_type == "text":
        content = elem.get("content", "")
        font_size = elem.get("font_size", 11)
        bold = elem.get("bold", False)
        lines = max(1, len(content) // 40 + 1)
        height = lines * 0.22
        add_textbox(slide, left, top, width, height, content, font_size=font_size, bold=bold, color=COLOR_DARK)
        return top + height + 0.1

    elif elem_type == "section_header":
        content = elem.get("content", "")
        add_section_header_shape(slide, left, top, width, content)
        return top + 0.42

    elif elem_type == "bullet":
        items = elem.get("items", [])
        font_size = elem.get("font_size", 10)
        height = len(items) * 0.25
        txBox = add_textbox(slide, left + 0.1, top, width - 0.1, height, "", font_size=font_size, color=COLOR_DARK)
        tf = txBox.text_frame
        tf.clear()
        for i, item in enumerate(items):
            p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
            p.text = f"•  {item}"
            if p.runs:
                set_font(p.runs[0], size_pt=font_size, color=COLOR_DARK)
        return top + height + 0.1

    elif elem_type == "table":
        headers = elem.get("headers", [])
        rows = elem.get("rows", [])
        if headers and rows:
            height = min((len(rows) + 1) * 0.32, 3.5)
            add_table(slide, left, top, width, height, headers, rows)
            return top + height + 0.1

    elif elem_type == "rich_text":
        runs = elem.get("runs", [])
        font_size = elem.get("font_size", 10)
        lines = max(1, sum(len(r.get("text", "")) for r in runs) // 40 + 1)
        height = lines * 0.22
        add_rich_text_box(slide, left, top, width, height, runs, base_font_size=font_size)
        return top + height + 0.1

    elif elem_type == "info_block":
        label = elem.get("label", "")
        fields = elem.get("fields", [])
        financial = elem.get("financial", None)
        bullet_values = elem.get("bullet_values", None)
        return add_info_table_block(
            slide, left, top, width, label, fields, financial=financial, bullet_values=bullet_values
        )

    return top + 0.3


def create_closing_slide(prs, contact_info=None):
    layout = get_layout(prs, "FOREST")
    slide = prs.slides.add_slide(layout)

    add_logo(slide)

    add_textbox(slide, LEFT_MARGIN, 3.0, 5.0, 0.5, "Thank You", font_size=36, bold=True, theme_color="BACKGROUND_1")

    if contact_info:
        add_textbox(slide, LEFT_MARGIN, 4.0, 5.0, 1.5, contact_info, font_size=12, theme_color="BACKGROUND_1")

    add_confidential_footer(slide, position="bottom", on_forest=True)

    return slide


# ── 통합 생성 함수 ──────────────────────────────────────────────


def generate_from_json(prs, content):
    """JSON 콘텐츠 기반 프레젠테이션 생성"""
    project_name = content.get("project_name", "PROJECT")
    memo_type = content.get("memo_type", "Memorandum")
    date_str = content.get("date", "")
    disclaimer = content.get("disclaimer", "")
    contact = content.get("contact", "")

    create_cover_slide(prs, project_name, memo_type, date_str)

    if disclaimer:
        create_disclaimer_slide(
            prs,
            disclaimer,
            date_label=date_str,
            company_name=content.get("company_name", "주식회사 페트라브릿지파트너스"),
        )

    slides_data = content.get("slides", [])
    section_titles = []
    for s in slides_data:
        title = s.get("title", "")
        if title and title not in section_titles:
            section_titles.append(title)
    if section_titles:
        create_toc_slide(prs, section_titles)

    for slide_data in slides_data:
        layout_name = slide_data.get("layout", "MAIN")

        if layout_name == "SECTION_DIVIDER":
            create_section_divider_slide(prs, slide_data.get("section_number", 1), slide_data.get("title", ""))
        elif layout_name == "MAIN":
            create_main_slide(
                prs,
                title=slide_data.get("title", ""),
                body_elements=slide_data.get("body", []),
                note=slide_data.get("note"),
            )
        elif layout_name == "FOREST":
            layout = get_layout(prs, "FOREST")
            slide = prs.slides.add_slide(layout)
            add_logo(slide)
            if slide_data.get("title"):
                add_textbox(
                    slide,
                    LEFT_MARGIN,
                    3.0,
                    5.0,
                    0.5,
                    slide_data["title"],
                    font_size=28,
                    bold=True,
                    theme_color="BACKGROUND_1",
                )
            add_confidential_footer(slide, position="bottom", on_forest=True)

    create_closing_slide(prs, contact)


def generate_memo(
    memo_type: str,
    project_code: str,
    output_path: str,
    content: dict | None = None,
) -> GenerationResult:
    """메모랜덤 생성 메인 함수.

    Args:
        memo_type: 'tm' | 'dm' | 'im' | 'proposal'
        project_code: 프로젝트 코드명 (예: ALPHA)
        output_path: 출력 PPTX 파일 경로 (절대 경로 권장)
        content: 슬라이드 콘텐츠 dict. None이면 기본 플레이스홀더 사용.

    Returns:
        GenerationResult — 파일 경로, 크기, 슬라이드 수 등

    Raises:
        FileNotFoundError: 마스터 템플릿이 없을 때
        ValueError: 잘못된 memo_type
        Exception: python-pptx 생성 오류
    """
    import time as _time

    from pptx import Presentation

    template = str(TEMPLATE_PATH)
    if not os.path.exists(template):
        raise FileNotFoundError(f"마스터 템플릿 없음: {template}")

    valid_types = ("tm", "dm", "im", "proposal")
    if memo_type not in valid_types:
        raise ValueError(f"잘못된 memo_type: {memo_type}. 허용값: {valid_types}")

    # 템플릿 로딩 시간 측정
    _t0 = _time.monotonic()
    prs = Presentation(template)
    _template_load_ms = int((_time.monotonic() - _t0) * 1000)

    if content is None:
        content = _default_content(memo_type, project_code)

    # 콘텐츠 렌더링 시간 측정
    _t1 = _time.monotonic()
    generate_from_json(prs, content)
    _render_ms = int((_time.monotonic() - _t1) * 1000)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # 파일 저장 시간 측정
    _t2 = _time.monotonic()
    prs.save(str(out))
    _persist_ms = int((_time.monotonic() - _t2) * 1000)

    file_size = out.stat().st_size
    slide_count = len(prs.slides)

    return GenerationResult(
        output_path=str(out),
        file_name=out.name,
        file_size_bytes=file_size,
        slide_count=slide_count,
        memo_type=memo_type,
        project_code=project_code,
        template_load_ms=_template_load_ms,
        render_ms=_render_ms,
        persist_ms=_persist_ms,
    )


# ── 기본 콘텐츠 템플릿 ────────────────────────────────────────


def _default_content(memo_type: str, project_code: str) -> dict:
    """메모 유형별 기본 플레이스홀더 콘텐츠"""
    project_name = f"PROJECT {project_code.upper()}"

    base = {
        "project_name": project_name,
        "date": "February 2026",
        "company_name": "주식회사 페트라브릿지파트너스",
        "disclaimer": (
            "본 자료는 잠재적인 투자 또는 관련 거래에 관한 예비적 검토를 위하여 "
            "제한된 수의 잠재적 투자자에게만 제공되는 자료입니다.\n\n"
            "본 자료에 포함된 정보는 공개자료 및 대상회사의 협조 하에 제공된 자료 등을 "
            "바탕으로 작성되었으나, 그 정확성, 완전성 또는 최신성에 대하여 작성자, "
            "대상회사 또는 그 주주, 임직원, 자문사 등이 어떠한 보증도 하지 아니합니다.\n\n"
            "본 자료의 수령인은 작성자의 사전 서면동의 없이 본 자료의 전부 또는 일부를 "
            "제3자에게 제공, 복제, 배포 또는 유출하여서는 아니 됩니다."
        ),
        "contact": "AMIC × PETRA Bridge Partners",
    }

    STRUCTURES: dict[str, dict] = {
        "tm": {
            "memo_type": "Teaser Memo",
            "slides": [
                {
                    "title": "Investment Highlights",
                    "body": [
                        {
                            "type": "bullet",
                            "items": [
                                "[투자 포인트 1]",
                                "[투자 포인트 2]",
                                "[투자 포인트 3]",
                                "[투자 포인트 4]",
                                "[투자 포인트 5]",
                            ],
                        }
                    ],
                },
                {
                    "title": "Company Overview",
                    "body": [
                        {
                            "type": "two_column",
                            "left": [
                                {"type": "section_header", "content": "회사 개요"},
                                {
                                    "type": "table",
                                    "headers": ["항목", "내용"],
                                    "rows": [
                                        ["회사명", "[회사명]"],
                                        ["설립일", "[설립일]"],
                                        ["대표이사", "[대표이사]"],
                                        ["주요사업", "[주요사업]"],
                                        ["소재지", "[소재지]"],
                                    ],
                                },
                            ],
                            "right": [
                                {"type": "section_header", "content": "주주 현황"},
                                {
                                    "type": "table",
                                    "headers": ["주주", "지분율"],
                                    "rows": [
                                        ["[주주1]", "[지분율]"],
                                        ["[주주2]", "[지분율]"],
                                        ["합계", "100%"],
                                    ],
                                },
                            ],
                        }
                    ],
                },
                {
                    "title": "Business Overview",
                    "body": [
                        {"type": "text", "content": "[사업 현황 요약]", "bold": True, "font_size": 14},
                        {"type": "bullet", "items": ["[사업 영역 1]", "[사업 영역 2]", "[사업 영역 3]"]},
                    ],
                },
                {
                    "title": "Financial Summary",
                    "body": [
                        {
                            "type": "table",
                            "headers": ["항목", "2023", "2024", "2025E"],
                            "rows": [
                                ["매출액", "[금액]", "[금액]", "[금액]"],
                                ["영업이익", "[금액]", "[금액]", "[금액]"],
                                ["EBITDA", "[금액]", "[금액]", "[금액]"],
                                ["순이익", "[금액]", "[금액]", "[금액]"],
                            ],
                        }
                    ],
                },
                {
                    "title": "Transaction Overview",
                    "body": [
                        {
                            "type": "two_column",
                            "left": [
                                {"type": "section_header", "content": "거래 개요"},
                                {
                                    "type": "table",
                                    "headers": ["항목", "내용"],
                                    "rows": [
                                        ["거래 형태", "[거래 형태]"],
                                        ["대상 지분", "[대상 지분]"],
                                        ["예상 거래규모", "[거래규모]"],
                                        ["희망 일정", "[일정]"],
                                    ],
                                },
                            ],
                            "right": [
                                {"type": "section_header", "content": "거래 구조"},
                                {"type": "text", "content": "[거래 구조 설명]"},
                            ],
                        }
                    ],
                },
            ],
        },
        "dm": {
            "memo_type": "Discussion Memo",
            "slides": [
                {
                    "title": "Executive Summary",
                    "body": [
                        {"type": "text", "content": "[논의 배경 및 목적]", "bold": True, "font_size": 14},
                        {
                            "type": "two_column",
                            "left": [
                                {"type": "section_header", "content": "대상회사 개요"},
                                {
                                    "type": "table",
                                    "headers": ["항목", "내용"],
                                    "rows": [
                                        ["회사명", "[회사명]"],
                                        ["주요사업", "[주요사업]"],
                                        ["매출액(2024)", "[금액]"],
                                    ],
                                },
                            ],
                            "right": [
                                {"type": "section_header", "content": "논의 사항"},
                                {
                                    "type": "table",
                                    "headers": ["항목", "내용"],
                                    "rows": [
                                        ["주제", "[주제]"],
                                        ["관련 당사자", "[당사자]"],
                                        ["제안 내용", "[제안]"],
                                    ],
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "Discussion Background",
                    "body": [
                        {"type": "text", "content": "[논의 배경 상세 설명]"},
                        {"type": "bullet", "items": ["[배경 1]", "[배경 2]", "[배경 3]"]},
                    ],
                },
                {
                    "title": "Key Discussion Points",
                    "body": [
                        {
                            "type": "bullet",
                            "items": [
                                "[논의 포인트 1]",
                                "[논의 포인트 2]",
                                "[논의 포인트 3]",
                                "[논의 포인트 4]",
                            ],
                        }
                    ],
                },
                {
                    "title": "Next Steps",
                    "body": [
                        {
                            "type": "table",
                            "headers": ["단계", "내용", "담당", "일정"],
                            "rows": [
                                ["1", "[액션 1]", "[담당자]", "[일정]"],
                                ["2", "[액션 2]", "[담당자]", "[일정]"],
                                ["3", "[액션 3]", "[담당자]", "[일정]"],
                            ],
                        }
                    ],
                },
            ],
        },
        "im": {
            "memo_type": "Information Memorandum",
            "slides": [
                {
                    "title": "Transaction Overview",
                    "body": [
                        {
                            "type": "two_column",
                            "left": [
                                {"type": "section_header", "content": "거래 개요"},
                                {
                                    "type": "table",
                                    "headers": ["항목", "내용"],
                                    "rows": [
                                        ["거래 형태", "[거래 형태]"],
                                        ["대상 지분", "[대상 지분]"],
                                        ["예상 거래규모", "[거래규모]"],
                                        ["희망 일정", "[일정]"],
                                    ],
                                },
                            ],
                            "right": [
                                {"type": "section_header", "content": "거래 구조"},
                                {"type": "text", "content": "[거래 구조 설명]"},
                            ],
                        }
                    ],
                },
                {
                    "title": "Investment Highlights",
                    "body": [
                        {
                            "type": "bullet",
                            "items": [
                                "[투자 포인트 1]",
                                "[투자 포인트 2]",
                                "[투자 포인트 3]",
                                "[투자 포인트 4]",
                                "[투자 포인트 5]",
                            ],
                        }
                    ],
                },
                {"title": "Investment Highlights (cont.)", "body": [{"type": "text", "content": "[투자 포인트 상세]"}]},
                {
                    "title": "Company Overview",
                    "body": [
                        {
                            "type": "table",
                            "headers": ["항목", "내용"],
                            "rows": [
                                ["회사명", "[회사명]"],
                                ["설립일", "[설립일]"],
                                ["대표이사", "[대표이사]"],
                                ["임직원 수", "[인원]"],
                                ["주요사업", "[주요사업]"],
                                ["소재지", "[소재지]"],
                            ],
                        }
                    ],
                },
                {"title": "Business Overview", "body": [{"type": "text", "content": "[사업 모델 및 현황]"}]},
                {"title": "Market Analysis", "body": [{"type": "text", "content": "[시장 규모 및 성장성]"}]},
                {"title": "Competitive Landscape", "body": [{"type": "text", "content": "[경쟁 구도 분석]"}]},
                {
                    "title": "Financial Summary (P&L)",
                    "body": [
                        {
                            "type": "table",
                            "headers": ["항목", "2022", "2023", "2024", "2025E", "2026E"],
                            "rows": [
                                ["매출액", "[금액]", "[금액]", "[금액]", "[금액]", "[금액]"],
                                ["매출총이익", "[금액]", "[금액]", "[금액]", "[금액]", "[금액]"],
                                ["영업이익", "[금액]", "[금액]", "[금액]", "[금액]", "[금액]"],
                                ["EBITDA", "[금액]", "[금액]", "[금액]", "[금액]", "[금액]"],
                                ["순이익", "[금액]", "[금액]", "[금액]", "[금액]", "[금액]"],
                            ],
                        }
                    ],
                },
                {
                    "title": "Financial Summary (B/S)",
                    "body": [
                        {
                            "type": "table",
                            "headers": ["항목", "2022", "2023", "2024"],
                            "rows": [
                                ["총자산", "[금액]", "[금액]", "[금액]"],
                                ["총부채", "[금액]", "[금액]", "[금액]"],
                                ["자기자본", "[금액]", "[금액]", "[금액]"],
                            ],
                        }
                    ],
                },
                {
                    "title": "Valuation Analysis",
                    "body": [{"type": "text", "content": "[밸류에이션 분석 — EV/EBITDA, DCF 등]"}],
                },
                {
                    "title": "Exit Strategy",
                    "body": [
                        {"type": "bullet", "items": ["[엑싯 시나리오 1]", "[엑싯 시나리오 2]", "[엑싯 시나리오 3]"]}
                    ],
                },
                {
                    "title": "Risk Factors",
                    "body": [
                        {
                            "type": "table",
                            "headers": ["구분", "내용", "대응방안"],
                            "rows": [
                                ["시장", "[리스크]", "[대응]"],
                                ["운영", "[리스크]", "[대응]"],
                                ["재무", "[리스크]", "[대응]"],
                            ],
                        }
                    ],
                },
                {
                    "title": "Investment Summary",
                    "body": [
                        {
                            "type": "bullet",
                            "items": [
                                "[핵심 투자 포인트 1]",
                                "[핵심 투자 포인트 2]",
                                "[핵심 투자 포인트 3]",
                                "[핵심 투자 포인트 4]",
                            ],
                        }
                    ],
                },
            ],
        },
        "proposal": {
            "memo_type": "Proposal",
            "slides": [
                {"title": "About AMIC × PETRA Bridge Partners", "body": [{"type": "text", "content": "[회사 소개]"}]},
                {
                    "title": "Track Record",
                    "body": [
                        {
                            "type": "table",
                            "headers": ["연도", "프로젝트", "역할", "거래규모"],
                            "rows": [
                                ["[연도]", "[프로젝트]", "[역할]", "[규모]"],
                                ["[연도]", "[프로젝트]", "[역할]", "[규모]"],
                            ],
                        }
                    ],
                },
                {
                    "title": "Scope of Services",
                    "body": [{"type": "bullet", "items": ["[서비스 범위 1]", "[서비스 범위 2]", "[서비스 범위 3]"]}],
                },
                {
                    "title": "Fee Structure",
                    "body": [
                        {
                            "type": "table",
                            "headers": ["구분", "금액", "비고"],
                            "rows": [
                                ["기본 보수", "[금액]", "[비고]"],
                                ["성공 보수", "[금액]", "[비고]"],
                            ],
                        }
                    ],
                },
            ],
        },
    }

    structure = STRUCTURES.get(memo_type, STRUCTURES["tm"])
    return {**base, **structure}
