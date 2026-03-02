"""M&A 계약서 표준 DOCX 서식 설정 — CONTRACT_STYLE_CONFIG + 문서 생성 유틸.

52개 실제 로펌 체결본(SPA/SHA/BTA/SSA/MOU) python-docx 분석 결과 기반.
대형 로펌(WY/율촌, BKL/배김이재성, LK/법무법인 린) 공통 서식을 표준으로 채택.
"""

from __future__ import annotations

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

# ── 표준 스타일 설정 ─────────────────────────────────────────────────────────

CONTRACT_STYLE_CONFIG: dict = {
    # ── 페이지 설정 ──
    "page": {
        "width_cm": 21.0,
        "height_cm": 29.7,
        "margin_top_cm": 3.0,
        "margin_bottom_cm": 3.0,
        "margin_left_cm": 2.5,
        "margin_right_cm": 2.5,
        "gutter_cm": 0.0,
        "header_distance_cm": 1.25,
        "footer_distance_cm": 1.25,
    },
    # ── 폰트 설정 ──
    "font": {
        "ascii": "Times New Roman",
        "east_asia": "바탕",
        "body_size_pt": 11.5,  # Tempus 체결본 실측: 23 핲프포인트 = 11.5pt
        "title_size_pt": 16.0,
        "subtitle_size_pt": 14.0,
        "article_heading_size_pt": 11.5,  # 조 제목도 본문과 동일 크기 (Bold 구분)
        "signature_size_pt": 11.5,
    },
    # ── 단락 설정 ──
    "paragraph": {
        "line_spacing": 1.3,  # 비율 (Tempus Heading1/계약본문1 실측)
        "line_spacing_rule": "MULTIPLE",  # WD_LINE_SPACING.MULTIPLE
        "space_before_pt": 0.0,
        "space_after_pt": 0.0,
        "alignment": "JUSTIFY",
        "first_line_indent_cm": 0.0,
    },
    # ── 조항 번호 들여쓰기 (Tempus SPA 실측) ──
    "indent": {
        "body_left_cm": 0.0,
        "level1_left_cm": 0.0,
        "level2_left_cm": 1.3,  # Tempus 실측: 계약bullet1/Body Text = 1.30cm
        "level2_hanging_cm": 1.3,  # 내어쓰기 1.30cm (번호 정렬)
        "level3_left_cm": 2.1,  # 호 ((1), (2)) — 합리적 추정
        "level3_hanging_cm": 0.7,
        "level4_left_cm": 2.8,  # 목 ((가), (나)) — level3 + 0.7
        "level4_hanging_cm": 0.7,
        "definition_left_cm": 1.3,  # 정의 조항 본문: 1.30cm (hanging 없음)
    },
    # ── 제목/소제목 간격 (Tempus 실측) ──
    "heading": {
        "title_space_before_pt": 60.0,
        "title_space_after_pt": 12.0,
        "article_space_before_pt": 18.0,  # Tempus Heading1 sb=18pt
        "article_space_after_pt": 12.0,  # Tempus Heading1 sa=12pt
        "section_label_space_before_pt": 10.0,
        "section_label_space_after_pt": 6.0,
    },
    # ── 서명란 ──
    "signature": {
        "table_style": "Table Grid",
        "min_row_height_cm": 3.0,
        "role_font_size_pt": 11.0,
        "role_bold": True,
    },
    # ── 바닥글 ──
    "footer": {
        "page_number_format": "- {page} -",
        "alignment": "CENTER",
        "font_size_pt": 9.0,
    },
}

_CFG = CONTRACT_STYLE_CONFIG


# ── 기본 문서 생성 ───────────────────────────────────────────────────────────


def create_base_contract_document() -> Document:
    """표준 M&A 계약서 서식이 적용된 빈 DOCX 문서를 생성한다."""
    doc = Document()
    pg = _CFG["page"]
    fn = _CFG["font"]
    pr = _CFG["paragraph"]

    # 페이지 설정
    for section in doc.sections:
        section.page_width = Cm(pg["width_cm"])
        section.page_height = Cm(pg["height_cm"])
        section.top_margin = Cm(pg["margin_top_cm"])
        section.bottom_margin = Cm(pg["margin_bottom_cm"])
        section.left_margin = Cm(pg["margin_left_cm"])
        section.right_margin = Cm(pg["margin_right_cm"])
        section.header_distance = Cm(pg["header_distance_cm"])
        section.footer_distance = Cm(pg["footer_distance_cm"])

    # Normal 스타일 강제 적용
    normal = doc.styles["Normal"]
    normal.font.name = fn["ascii"]
    normal.font.size = Pt(fn["body_size_pt"])

    # oxml 레벨 eastAsia 폰트 설정
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:eastAsia"), fn["east_asia"])
    rfonts.set(qn("w:ascii"), fn["ascii"])
    rfonts.set(qn("w:hAnsi"), fn["ascii"])

    # Normal 단락 서식 — CONFIG에서 참조
    ls_rule_map = {
        "AT_LEAST": WD_LINE_SPACING.AT_LEAST,
        "SINGLE": WD_LINE_SPACING.SINGLE,
        "MULTIPLE": WD_LINE_SPACING.MULTIPLE,
    }
    align_map = {"JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY, "LEFT": WD_ALIGN_PARAGRAPH.LEFT}
    pf = normal.paragraph_format
    ls_rule = ls_rule_map.get(pr["line_spacing_rule"], WD_LINE_SPACING.MULTIPLE)
    if ls_rule == WD_LINE_SPACING.MULTIPLE:
        pf.line_spacing = pr["line_spacing"]  # 비율 (1.3 등)
    else:
        pf.line_spacing = Pt(pr.get("line_spacing_pt", pr.get("line_spacing", 18)))
    pf.line_spacing_rule = ls_rule
    pf.space_before = Pt(pr["space_before_pt"])
    pf.space_after = Pt(pr["space_after_pt"])
    pf.alignment = align_map.get(pr["alignment"], WD_ALIGN_PARAGRAPH.JUSTIFY)

    # 커스텀 뎁스별 단락 스타일 등록
    _register_contract_styles(doc)

    # 바닥글 페이지 번호
    _add_page_number_footer(doc)

    return doc


# ── 폰트 적용 ────────────────────────────────────────────────────────────────


def apply_font(
    run: object,
    size_pt: float | None = None,
    bold: bool | None = None,
) -> None:
    """Run에 표준 폰트를 적용한다 (바탕 + Times New Roman)."""
    fn = _CFG["font"]
    run.font.name = fn["ascii"]  # type: ignore[union-attr]

    # oxml 레벨 eastAsia 폰트
    rpr = run.font.element.rPr  # type: ignore[union-attr]
    if rpr is not None:
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.insert(0, rfonts)
        rfonts.set(qn("w:eastAsia"), fn["east_asia"])

    if size_pt is not None:
        run.font.size = Pt(size_pt)  # type: ignore[union-attr]
    if bold is not None:
        run.bold = bold  # type: ignore[union-attr]


# ── 제목/소제목 ──────────────────────────────────────────────────────────────


def add_title(
    doc: Document,
    text: str,
    size_pt: float | None = None,
    space_before_pt: float | None = None,
) -> None:
    """문서 제목 — 중앙정렬, Bold."""
    hd = _CFG["heading"]
    fn = _CFG["font"]
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(space_before_pt or hd["title_space_before_pt"])
    para.paragraph_format.space_after = Pt(hd["title_space_after_pt"])
    run = para.add_run(text)
    apply_font(run, size_pt=size_pt or fn["title_size_pt"], bold=True)


def add_subtitle(doc: Document, text: str) -> None:
    """영문 부제 — 중앙정렬."""
    fn = _CFG["font"]
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_after = Pt(6)
    run = para.add_run(text)
    apply_font(run, size_pt=fn["subtitle_size_pt"], bold=False)


def add_section_label(doc: Document, text: str, bold: bool = True) -> None:
    """'전  문', '아  래' 등 중앙 소제목."""
    hd = _CFG["heading"]
    fn = _CFG["font"]
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(hd["section_label_space_before_pt"])
    para.paragraph_format.space_after = Pt(hd["section_label_space_after_pt"])
    run = para.add_run(text)
    apply_font(run, size_pt=fn["body_size_pt"], bold=bold)


# ── 조항 ──────────────────────────────────────────────────────────────────


def add_article_heading(doc: Document, num: int, title: str) -> None:
    """제N조 (제목) — Heading 1 스타일, Bold."""
    hd = _CFG["heading"]
    fn = _CFG["font"]
    para = doc.add_paragraph(style="Heading 1")
    para.paragraph_format.space_before = Pt(hd["article_space_before_pt"])
    para.paragraph_format.space_after = Pt(hd["article_space_after_pt"])
    run = para.add_run(f"제{num}조 ({title})")
    apply_font(run, size_pt=fn["article_heading_size_pt"], bold=True)


def add_subheading(doc: Document, text: str) -> None:
    """소항 제목 — Heading 2 스타일."""
    fn = _CFG["font"]
    para = doc.add_paragraph(style="Heading 2")
    para.paragraph_format.space_before = Pt(8)
    para.paragraph_format.space_after = Pt(4)
    run = para.add_run(text)
    apply_font(run, size_pt=fn["body_size_pt"], bold=True)


# ── 본문 ──────────────────────────────────────────────────────────────────


def add_body(
    doc: Document,
    text: str,
    indent_level: int = 0,
) -> None:
    """조항 본문 단락. indent_level: 0=기본, 1=항(1.4cm), 2=호(2.1cm)."""
    fn = _CFG["font"]
    ind = _CFG["indent"]
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(0)

    if indent_level == 1:
        para.paragraph_format.left_indent = Cm(ind["level2_left_cm"])
    elif indent_level == 2:
        para.paragraph_format.left_indent = Cm(ind["level3_left_cm"])
    elif indent_level >= 3:
        para.paragraph_format.left_indent = Cm(ind["level3_left_cm"] + 0.7)

    run = para.add_run(text)
    apply_font(run, size_pt=fn["body_size_pt"])


def add_preamble_body(doc: Document, text: str, indent_cm: float | None = None) -> None:
    """전문 본문 — 들여쓰기. indent_cm 미지정 시 CONFIG definition_left_cm 사용."""
    fn = _CFG["font"]
    ind = _CFG["indent"]
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Cm(indent_cm if indent_cm is not None else ind["definition_left_cm"])
    para.paragraph_format.space_after = Pt(4)
    run = para.add_run(text)
    apply_font(run, size_pt=fn["body_size_pt"])


def add_preamble_text(doc: Document, text: str) -> None:
    """전문 설명 본문 — 들여쓰기 없음."""
    fn = _CFG["font"]
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(4)
    run = para.add_run(text)
    apply_font(run, size_pt=fn["body_size_pt"])


# ── Jinja2 태그 ──────────────────────────────────────────────────────────


def add_jinja_block(doc: Document, tag: str) -> None:
    """Jinja2 블록 태그 전용 단락 ({%p for %} 등)."""
    fn = _CFG["font"]
    para = doc.add_paragraph()
    run = para.add_run(tag)
    apply_font(run, size_pt=fn["body_size_pt"])


def add_jinja_line(
    doc: Document,
    text: str,
    indent_level: int = 1,
) -> None:
    """반복 루프 내 항목 단락."""
    fn = _CFG["font"]
    ind = _CFG["indent"]
    para = doc.add_paragraph()
    if indent_level >= 1:
        para.paragraph_format.left_indent = Cm(ind["level2_left_cm"])
    para.paragraph_format.space_after = Pt(2)
    run = para.add_run(text)
    apply_font(run, size_pt=fn["body_size_pt"])


# ── 서명란 ────────────────────────────────────────────────────────────────


def add_date_line(doc: Document) -> None:
    """서명 날짜 줄 — 중앙정렬."""
    fn = _CFG["font"]
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(20)
    para.paragraph_format.space_after = Pt(10)
    run = para.add_run("{{ signing_date }}")
    apply_font(run, size_pt=fn["body_size_pt"])


def add_signature_table(
    doc: Document,
    parties: list[tuple[str, str, str]],
) -> None:
    """서명란 테이블. parties: [(역할, 회사변수, 대표이사변수), ...]."""
    fn = _CFG["font"]
    sig = _CFG["signature"]

    doc.add_paragraph()
    note = doc.add_paragraph("본 계약의 성립을 증명하기 위하여 아래에 서명 또는 기명날인한다.")
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in note.runs:
        apply_font(run, size_pt=fn["body_size_pt"])
    doc.add_paragraph()

    table = doc.add_table(rows=len(parties), cols=2)
    table.style = sig["table_style"]

    for i, (role, company_var, rep_var) in enumerate(parties):
        row = table.rows[i]
        cell_l = row.cells[0]
        cell_l.text = role
        for run in cell_l.paragraphs[0].runs:
            apply_font(run, size_pt=sig["role_font_size_pt"], bold=sig["role_bold"])

        cell_r = row.cells[1]
        p = cell_r.paragraphs[0]
        r1 = p.add_run(company_var + "\n")
        apply_font(r1, size_pt=sig["role_font_size_pt"])
        r2 = p.add_run(f"대표이사 {rep_var}")
        apply_font(r2, size_pt=sig["role_font_size_pt"])

        for cell in (cell_l, cell_r):
            tc = cell._element
            tcp = tc.get_or_add_tcPr()
            # 기존 w:tcW 제거 후 재설정 (중복 방지)
            existing = tcp.find(qn("w:tcW"))
            if existing is not None:
                tcp.remove(existing)
            val_el = OxmlElement("w:tcW")
            val_el.set(qn("w:w"), "0")
            val_el.set(qn("w:type"), "auto")
            tcp.append(val_el)


# ── 커스텀 뎁스별 단락 스타일 ──────────────────────────────────────────────────


def _register_contract_styles(doc: Document) -> None:
    """계약서 뎁스별 커스텀 단락 스타일(Contract_L1~L4, Body, Definition)을 등록한다."""
    fn = _CFG["font"]
    ind = _CFG["indent"]
    hd = _CFG["heading"]
    pr = _CFG["paragraph"]
    base_sz = fn["body_size_pt"]
    line_sp = pr["line_spacing"]

    styles_spec = [
        # (name, bold, left_cm, hang_cm, sb_pt, sa_pt, alignment)
        (
            "Contract_L1",
            True,
            ind["level1_left_cm"],
            0.0,
            hd["article_space_before_pt"],
            hd["article_space_after_pt"],
            "JUSTIFY",
        ),
        ("Contract_L2", False, ind["level2_left_cm"], -ind["level2_hanging_cm"], 0.0, 0.0, "JUSTIFY"),
        ("Contract_L3", False, ind["level3_left_cm"], -ind["level3_hanging_cm"], 0.0, 0.0, "JUSTIFY"),
        ("Contract_L4", False, ind["level4_left_cm"], -ind["level4_hanging_cm"], 0.0, 0.0, "JUSTIFY"),
        ("Contract_Body", False, ind["body_left_cm"], 0.0, 0.0, 0.0, "JUSTIFY"),
        ("Contract_Definition", False, ind["definition_left_cm"], 0.0, 0.0, 0.0, "JUSTIFY"),
    ]

    align_map = {"JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY, "CENTER": WD_ALIGN_PARAGRAPH.CENTER}

    for name, bold, left_cm, hang_cm, sb_pt, sa_pt, align in styles_spec:
        # 기존 스타일이 있으면 건너뜀
        if name in [s.name for s in doc.styles]:
            continue

        style = doc.styles.add_style(name, 1)  # 1 = WD_STYLE_TYPE.PARAGRAPH
        style.base_style = doc.styles["Normal"]

        # 폰트
        style.font.name = fn["ascii"]
        style.font.size = Pt(base_sz)
        style.font.bold = bold

        # oxml eastAsia
        rpr = style.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.insert(0, rfonts)
        rfonts.set(qn("w:eastAsia"), fn["east_asia"])

        # 단락 서식
        pf = style.paragraph_format
        pf.line_spacing = line_sp
        pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        pf.alignment = align_map.get(align, WD_ALIGN_PARAGRAPH.JUSTIFY)
        pf.space_before = Pt(sb_pt)
        pf.space_after = Pt(sa_pt)

        if left_cm:
            pf.left_indent = Cm(left_cm)
        if hang_cm:
            pf.first_line_indent = Cm(hang_cm)


# ── 바닥글 페이지 번호 ───────────────────────────────────────────────────────


def _add_page_number_footer(doc: Document) -> None:
    """바닥글에 '- 1 -' 형식 페이지 번호를 추가한다."""
    fn = _CFG["font"]
    ft = _CFG["footer"]

    section = doc.sections[0]
    footer = section.footer
    footer.is_linked_to_previous = False

    para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # "- " 접두사
    r_prefix = para.add_run("- ")
    r_prefix.font.size = Pt(ft["font_size_pt"])
    r_prefix.font.name = fn["ascii"]

    # PAGE 필드 코드
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")

    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "

    fld_char_separate = OxmlElement("w:fldChar")
    fld_char_separate.set(qn("w:fldCharType"), "separate")

    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")

    r_page = para.add_run()
    r_page.font.size = Pt(ft["font_size_pt"])
    r_page.font.name = fn["ascii"]
    r_page._element.append(fld_char_begin)
    r_page._element.append(instr_text)
    r_page._element.append(fld_char_separate)
    r_page._element.append(fld_char_end)

    # " -" 접미사
    r_suffix = para.add_run(" -")
    r_suffix.font.size = Pt(ft["font_size_pt"])
    r_suffix.font.name = fn["ascii"]
