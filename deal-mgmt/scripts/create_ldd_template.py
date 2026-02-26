"""
LDD(법률실사) 보고서 docxtpl 템플릿 생성 스크립트.

법률실사보고서 기재례(Kor/Eng 통합) + DDRL 10개 섹션 구조를 기반으로
python-docx를 사용하여 docxtpl 호환 템플릿 2종을 생성한다.

템플릿 종류:
  - ldd_full_template.docx    : 정식 전체 LDD 보고서 (10개 섹션 + Executive Summary)
  - ldd_redflag_template.docx : Redflag DD (Executive Summary + Red/Amber 이슈만)

서식 기준 (법률실사보고서 기재례 분석):
  - 폰트: 바탕체 (한글), Times New Roman (영문)
  - 페이지: A4 (21.0 × 29.7 cm)
  - 여백: 좌 2.54 / 우 2.54 / 상 3.00 / 하 2.54 cm
  - 제목: 16pt Bold 중앙정렬
  - 본문: 12pt
  - 색상: 흑백

사용법:
    cd deal-mgmt
    uv run python scripts/create_ldd_template.py

생성 위치: deal-mgmt/templates/ldd/
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "ldd"
TEMPLATE_VERSION = "1.0"

FONT_KO = "바탕체"
FONT_EN = "Times New Roman"


# ─── 공통 유틸 ────────────────────────────────────────────────────────────────

def _apply_font(run, size_pt: float | None = None, bold: bool | None = None,
                color: RGBColor | None = None) -> None:
    """Run에 바탕체(한글) + Times New Roman(영문) 폰트 적용."""
    run.font.name = FONT_EN
    run.font.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_KO)
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def _set_margins(doc: Document, left: float = 2.54, right: float = 2.54,
                  top: float = 3.00, bottom: float = 2.54) -> None:
    """A4 페이지 여백 설정 (cm 단위)."""
    for section in doc.sections:
        section.page_width  = Cm(21.0)
        section.page_height = Cm(29.7)
        section.left_margin   = Cm(left)
        section.right_margin  = Cm(right)
        section.top_margin    = Cm(top)
        section.bottom_margin = Cm(bottom)


def _add_title(doc: Document, text: str, size_pt: float = 16.0,
               space_before_pt: float = 40.0) -> None:
    """문서 제목 단락 — 중앙정렬, 바탕체 Bold."""
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(space_before_pt)
    para.paragraph_format.space_after  = Pt(12)
    run = para.add_run(text)
    _apply_font(run, size_pt=size_pt, bold=True)


def _add_subtitle(doc: Document, text: str, size_pt: float = 11.0) -> None:
    """부제 — 중앙정렬."""
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_after = Pt(6)
    run = para.add_run(text)
    _apply_font(run, size_pt=size_pt)


def _add_section_heading(doc: Document, text: str) -> None:
    """섹션 제목 (H1 수준) — 14pt Bold."""
    para = doc.add_paragraph(style="Heading 1")
    para.paragraph_format.space_before = Pt(16)
    para.paragraph_format.space_after  = Pt(8)
    run = para.add_run(text)
    _apply_font(run, size_pt=14.0, bold=True)


def _add_subsection_heading(doc: Document, text: str) -> None:
    """소항 제목 (H2 수준) — 12pt Bold."""
    para = doc.add_paragraph(style="Heading 2")
    para.paragraph_format.space_before = Pt(10)
    para.paragraph_format.space_after  = Pt(6)
    run = para.add_run(text)
    _apply_font(run, size_pt=12.0, bold=True)


def _add_body(doc: Document, text: str, indent_cm: float = 0.0) -> None:
    """본문 단락 — 12pt."""
    para = doc.add_paragraph()
    if indent_cm:
        para.paragraph_format.left_indent = Cm(indent_cm)
    para.paragraph_format.space_after = Pt(4)
    run = para.add_run(text)
    _apply_font(run, size_pt=12.0)


def _add_jinja_block(doc: Document, tag: str) -> None:
    """Jinja2 단락 수준 태그 ({%p for %} 등) 전용 단락."""
    para = doc.add_paragraph()
    run = para.add_run(tag)
    _apply_font(run, size_pt=12.0)


def _set_cell_background(cell, hex_color: str) -> None:
    """테이블 셀 배경색 설정 (hex: 'E2EFDA', 'FCE4D6' 등)."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _set_cell_text(cell, text: str, size_pt: float = 10.0,
                   bold: bool = False, center: bool = False) -> None:
    """테이블 셀 텍스트 설정."""
    cell.text = ""
    para = cell.paragraphs[0]
    if center:
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run(text)
    _apply_font(run, size_pt=size_pt, bold=bold)


# ─── FULL 템플릿 생성 ─────────────────────────────────────────────────────────

def create_full_template(output_path: Path) -> None:
    """정식 전체 LDD 보고서 템플릿 (10개 섹션)."""
    doc = Document()
    _set_margins(doc)

    # ── 표지 ──
    _add_title(doc, "{{ title }}", size_pt=16.0, space_before_pt=60.0)
    _add_subtitle(doc, "Legal Due Diligence Report", size_pt=11.0)
    doc.add_paragraph()
    _add_body(doc, "대상회사:  {{ target_company }}", indent_cm=2.0)
    _add_body(doc, "실사기간:  {{ dd_period }}", indent_cm=2.0)
    _add_body(doc, "보고서유형: 정식 법률실사보고서 (Full LDD)", indent_cm=2.0)
    _add_body(doc, "법무법인:  {{ law_firm }}", indent_cm=2.0)
    _add_body(doc, "담당변호사: {{ prepared_by }}", indent_cm=2.0)
    _add_body(doc, "작성일:    {{ report_date }}", indent_cm=2.0)
    doc.add_page_break()

    # ── Executive Summary ──
    _add_section_heading(doc, "I. 실사 결과 요약 (Executive Summary)")

    _add_subsection_heading(doc, "1. 이슈 현황 개요")
    _add_body(doc, "본 법률실사 결과 도출된 이슈 현황은 아래와 같습니다.")

    # 요약 테이블: 이슈레벨별 카운트
    summary_tbl = doc.add_table(rows=2, cols=5)
    summary_tbl.style = "Table Grid"
    headers = ["구분", "Critical (Red)", "High/Medium (Amber)", "Low (Green)", "합계"]
    values  = ["건수", "{{ red_count }}", "{{ amber_count }}", "{{ green_count }}", "{{ issue_count }}"]
    header_colors = ["D9D9D9", "FF0000", "FF9900", "70AD47", "D9D9D9"]
    value_colors  = ["D9D9D9", "FCE4D6", "FFF2CC", "E2EFDA", "D9D9D9"]

    for i, (hdr, color) in enumerate(zip(headers, header_colors)):
        cell = summary_tbl.rows[0].cells[i]
        _set_cell_background(cell, color)
        _set_cell_text(cell, hdr, bold=True, center=True)
    for i, (val, color) in enumerate(zip(values, value_colors)):
        cell = summary_tbl.rows[1].cells[i]
        _set_cell_background(cell, color)
        _set_cell_text(cell, val, center=True)

    doc.add_paragraph()

    # 전체 검토 현황 테이블
    _add_body(doc, "전체 검토 항목 현황")
    status_tbl = doc.add_table(rows=2, cols=6)
    status_tbl.style = "Table Grid"
    s_headers = ["전체", "이슈(ISSUE)", "이상없음(OK)", "해당없음(N/A)", "미검토(Pending)", "RFI 요청"]
    s_values  = ["{{ total_items }}", "{{ issue_count }}", "{{ ok_count }}",
                 "{{ na_count }}", "{{ pending_count }}", "{{ rfi_count }}"]
    for i, hdr in enumerate(s_headers):
        _set_cell_text(status_tbl.rows[0].cells[i], hdr, bold=True, center=True)
        _set_cell_background(status_tbl.rows[0].cells[i], "D9D9D9")
    for i, val in enumerate(s_values):
        _set_cell_text(status_tbl.rows[1].cells[i], val, center=True)

    doc.add_paragraph()
    _add_subsection_heading(doc, "2. 주요 발견사항 요약")
    _add_body(doc, "※ 아래는 주요 이슈 항목 요약입니다. 상세 내용은 섹션별 체크리스트를 참조하십시오.")
    doc.add_page_break()

    # ── 섹션별 체크리스트 ──
    _add_section_heading(doc, "II. 섹션별 체크리스트")
    _add_body(doc, "결과 기호: OK=이상없음  ISSUE=이슈발견  N/A=해당없음  Pending=미검토")
    _add_body(doc, "이슈등급: CRITICAL(Red)  HIGH(Amber)  MEDIUM(Amber)  LOW(Green)")
    doc.add_paragraph()

    # docxtpl 루프: 섹션 반복
    _add_jinja_block(doc, "{%p for section in sections %}")

    _add_subsection_heading(doc, "{{ section.title }}")

    # 항목 테이블 헤더 행 (정적)
    item_tbl = doc.add_table(rows=2, cols=7)
    item_tbl.style = "Table Grid"
    col_headers = ["No.", "항목명", "결과", "이슈등급", "발견사항", "거래영향", "권고사항"]
    col_widths   = [1.0, 3.5, 1.5, 1.8, 4.5, 3.5, 4.0]

    # 헤더 행
    for j, (hdr, w) in enumerate(zip(col_headers, col_widths)):
        cell = item_tbl.rows[0].cells[j]
        _set_cell_background(cell, "D9D9D9")
        _set_cell_text(cell, hdr, size_pt=9.0, bold=True, center=True)
        cell.width = Cm(w)

    # docxtpl 테이블 행 루프
    tr_loop_start = item_tbl.rows[1]
    vals = [
        "{{ loop.index }}",
        "{{ item.name }}",
        "{{ item.status }}",
        "{{ item.issue_level or '' }}",
        "{{ item.description }}",
        "{{ item.deal_impact }}",
        "{{ item.recommendation }}",
    ]
    # 첫 번째 데이터 행 — 루프 시작 태그를 첫 셀에 삽입
    cell0 = tr_loop_start.cells[0]
    cell0.text = ""
    p0 = cell0.paragraphs[0]
    p0.add_run("{%tr for item in section.items %}")

    for j in range(1, 7):
        cell = tr_loop_start.cells[j]
        cell.text = ""

    # 값 행 추가 (루프 내용 행)
    data_row = item_tbl.add_row()
    for j, val in enumerate(vals):
        _set_cell_text(data_row.cells[j], val, size_pt=9.0)

    # 루프 종료 태그
    end_row = item_tbl.add_row()
    end_row.cells[0].text = ""
    end_row.cells[0].paragraphs[0].add_run("{%tr endfor %}")
    for j in range(1, 7):
        end_row.cells[j].text = ""

    doc.add_paragraph()

    # RFI 목록 (해당 섹션에 RFI 있을 경우)
    _add_jinja_block(doc, "{%p endfor %}")
    doc.add_page_break()

    # ── 이슈 목록 요약 ──
    _add_section_heading(doc, "III. 이슈 목록 요약")
    _add_body(doc, "※ 아래는 ISSUE로 분류된 항목만 모은 종합 목록입니다.")
    doc.add_paragraph()

    # 이슈 요약 테이블 헤더
    issue_tbl = doc.add_table(rows=1, cols=6)
    issue_tbl.style = "Table Grid"
    issue_hdrs = ["섹션", "항목명", "이슈등급", "발견사항", "거래영향", "RFI 번호"]
    for j, hdr in enumerate(issue_hdrs):
        _set_cell_background(issue_tbl.rows[0].cells[j], "D9D9D9")
        _set_cell_text(issue_tbl.rows[0].cells[j], hdr, size_pt=9.0, bold=True, center=True)

    # docxtpl 이슈 루프
    issue_row = issue_tbl.add_row()
    issue_row.cells[0].text = ""
    issue_row.cells[0].paragraphs[0].add_run(
        "{%tr for issue in all_issues %}"
    )
    for j in range(1, 6):
        issue_row.cells[j].text = ""

    issue_data_row = issue_tbl.add_row()
    issue_vals = [
        "{{ issue.section_title }}",
        "{{ issue.name }}",
        "{{ issue.issue_level }}",
        "{{ issue.description }}",
        "{{ issue.deal_impact }}",
        "{{ issue.rfi_number if issue.rfi_required else '' }}",
    ]
    for j, val in enumerate(issue_vals):
        _set_cell_text(issue_data_row.cells[j], val, size_pt=9.0)

    issue_end_row = issue_tbl.add_row()
    issue_end_row.cells[0].text = ""
    issue_end_row.cells[0].paragraphs[0].add_run("{%tr endfor %}")
    for j in range(1, 6):
        issue_end_row.cells[j].text = ""

    doc.add_paragraph()
    _add_body(doc, "— 이 상 —", indent_cm=0.0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    print(f"[OK] FULL 템플릿 생성: {output_path}")


# ─── REDFLAG 템플릿 생성 ──────────────────────────────────────────────────────

def create_redflag_template(output_path: Path) -> None:
    """Redflag DD 보고서 템플릿 (Executive Summary + Red/Amber 이슈만)."""
    doc = Document()
    _set_margins(doc)

    # ── 표지 ──
    _add_title(doc, "{{ title }}", size_pt=16.0, space_before_pt=60.0)
    _add_subtitle(doc, "Redflag Due Diligence Report", size_pt=11.0)
    doc.add_paragraph()
    _add_body(doc, "대상회사:  {{ target_company }}", indent_cm=2.0)
    _add_body(doc, "실사기간:  {{ dd_period }}", indent_cm=2.0)
    _add_body(doc, "보고서유형: Redflag DD (Red/Amber 이슈 중심)", indent_cm=2.0)
    _add_body(doc, "법무법인:  {{ law_firm }}", indent_cm=2.0)
    _add_body(doc, "담당변호사: {{ prepared_by }}", indent_cm=2.0)
    _add_body(doc, "작성일:    {{ report_date }}", indent_cm=2.0)
    doc.add_page_break()

    # ── Executive Summary ──
    _add_section_heading(doc, "I. Executive Summary")

    _add_subsection_heading(doc, "Overall Assessment")
    _add_body(doc, "본 Redflag DD는 대상회사 {{ target_company }}에 대한 "
              "법률실사에서 Red(Critical) 및 Amber(High/Medium) 등급 이슈를 중심으로 "
              "거래에 미치는 영향과 주요 권고사항을 기술한다.")
    doc.add_paragraph()

    # 이슈 현황 요약 테이블
    _add_body(doc, "이슈 현황 요약")
    rf_tbl = doc.add_table(rows=2, cols=4)
    rf_tbl.style = "Table Grid"
    rf_headers = ["Critical (Red)", "High/Medium (Amber)", "Low (Green)", "합계"]
    rf_values  = ["{{ red_count }}", "{{ amber_count }}", "{{ green_count }}", "{{ issue_count }}"]
    rf_h_colors = ["FF0000", "FF9900", "70AD47", "D9D9D9"]
    rf_v_colors = ["FCE4D6", "FFF2CC", "E2EFDA", "D9D9D9"]

    for i, (hdr, color) in enumerate(zip(rf_headers, rf_h_colors)):
        cell = rf_tbl.rows[0].cells[i]
        _set_cell_background(cell, color)
        _set_cell_text(cell, hdr, bold=True, center=True)
    for i, (val, color) in enumerate(zip(rf_values, rf_v_colors)):
        cell = rf_tbl.rows[1].cells[i]
        _set_cell_background(cell, color)
        _set_cell_text(cell, val, center=True)

    doc.add_paragraph()

    _add_subsection_heading(doc, "Key Recommendations")
    _add_body(doc, "1. Critical(Red) 이슈에 대해 거래 진행 전 해소 방안 확인 필요")
    _add_body(doc, "2. Amber 이슈는 진술보장 조항 또는 거래가격 조정에 반영 권고")
    _add_body(doc, "3. RFI 요청 항목({{ rfi_count }}건)에 대한 추가 자료 수령 필요")
    doc.add_paragraph()

    # Red Flags 요약 테이블
    _add_subsection_heading(doc, "Red Flags 요약")
    flag_tbl = doc.add_table(rows=1, cols=5)
    flag_tbl.style = "Table Grid"
    flag_hdrs = ["섹션", "항목명", "위험도", "발견사항", "거래영향"]
    for j, hdr in enumerate(flag_hdrs):
        _set_cell_background(flag_tbl.rows[0].cells[j], "D9D9D9")
        _set_cell_text(flag_tbl.rows[0].cells[j], hdr, size_pt=9.0, bold=True, center=True)

    # Red 이슈 루프
    red_row = flag_tbl.add_row()
    red_row.cells[0].text = ""
    red_row.cells[0].paragraphs[0].add_run("{%tr for issue in red_issues %}")
    for j in range(1, 5):
        red_row.cells[j].text = ""

    red_data = flag_tbl.add_row()
    red_vals = [
        "{{ issue.section_title }}",
        "{{ issue.name }}",
        "{{ issue.issue_level }} ({{ issue.risk_color }})",
        "{{ issue.description }}",
        "{{ issue.deal_impact }}",
    ]
    for j, val in enumerate(red_vals):
        _set_cell_text(red_data.cells[j], val, size_pt=9.0)

    red_end = flag_tbl.add_row()
    red_end.cells[0].text = ""
    red_end.cells[0].paragraphs[0].add_run("{%tr endfor %}")
    for j in range(1, 5):
        red_end.cells[j].text = ""

    doc.add_page_break()

    # ── 상세 Findings ──
    _add_section_heading(doc, "II. 상세 Findings (Red/Amber 이슈)")
    _add_body(doc, "※ Green(Low) 이슈 및 OK/N/A 항목은 본 보고서에서 제외합니다.")
    doc.add_paragraph()

    # 섹션별 이슈 루프
    _add_jinja_block(doc, "{%p for section in sections_with_issues %}")
    _add_subsection_heading(doc, "{{ section.title }}")

    sec_tbl = doc.add_table(rows=1, cols=6)
    sec_tbl.style = "Table Grid"
    sec_hdrs = ["항목명", "이슈등급", "발견사항", "거래영향", "권고사항", "RFI"]
    for j, hdr in enumerate(sec_hdrs):
        _set_cell_background(sec_tbl.rows[0].cells[j], "D9D9D9")
        _set_cell_text(sec_tbl.rows[0].cells[j], hdr, size_pt=9.0, bold=True, center=True)

    sec_data_start = sec_tbl.add_row()
    sec_data_start.cells[0].text = ""
    sec_data_start.cells[0].paragraphs[0].add_run("{%tr for item in section.issues %}")
    for j in range(1, 6):
        sec_data_start.cells[j].text = ""

    sec_data = sec_tbl.add_row()
    sec_vals = [
        "{{ item.name }}",
        "{{ item.issue_level }}",
        "{{ item.description }}",
        "{{ item.deal_impact }}",
        "{{ item.recommendation }}",
        "{{ item.rfi_number if item.rfi_required else '' }}",
    ]
    for j, val in enumerate(sec_vals):
        _set_cell_text(sec_data.cells[j], val, size_pt=9.0)

    sec_end = sec_tbl.add_row()
    sec_end.cells[0].text = ""
    sec_end.cells[0].paragraphs[0].add_run("{%tr endfor %}")
    for j in range(1, 6):
        sec_end.cells[j].text = ""

    doc.add_paragraph()
    _add_jinja_block(doc, "{%p endfor %}")

    _add_body(doc, "— 이 상 —")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    print(f"[OK] REDFLAG 템플릿 생성: {output_path}")


# ─── NARRATIVE FULL 템플릿 ──────────────────────────────────────────────────

def create_narrative_full_template(output_path: Path) -> None:
    """서술형 정식 LDD 보고서 템플릿.

    체크리스트 테이블 대신 항목별 6블록 서술 문단을 사용한다.
    표지 → 목차 → Executive Summary → 섹션별 서술 분석 → 이슈 요약 → 별첨 → "이 상"
    """
    doc = Document()
    _set_margins(doc)

    # ── 표지 ──
    _add_title(doc, "{{ title }}", size_pt=16.0, space_before_pt=60.0)
    _add_subtitle(doc, "Legal Due Diligence Report", size_pt=11.0)
    doc.add_paragraph()
    _add_body(doc, "대상회사:  {{ target_company }}", indent_cm=2.0)
    _add_body(doc, "실사기간:  {{ dd_period }}", indent_cm=2.0)
    _add_body(doc, "보고서유형: 정식 법률실사보고서 (서술형)", indent_cm=2.0)
    _add_body(doc, "법무법인:  {{ law_firm }}", indent_cm=2.0)
    _add_body(doc, "담당변호사: {{ prepared_by }}", indent_cm=2.0)
    _add_body(doc, "작성일:    {{ report_date }}", indent_cm=2.0)
    doc.add_page_break()

    # ── Executive Summary ──
    _add_section_heading(doc, "I. 실사 결과 요약 (Executive Summary)")

    _add_subsection_heading(doc, "1. 이슈 현황 개요")
    _add_body(doc, "본 법률실사 결과 도출된 이슈 현황은 아래와 같습니다.")

    # 요약 테이블
    summary_tbl = doc.add_table(rows=2, cols=5)
    summary_tbl.style = "Table Grid"
    headers = ["구분", "Critical (Red)", "High/Medium (Amber)", "Low (Green)", "합계"]
    values  = ["건수", "{{ red_count }}", "{{ amber_count }}", "{{ green_count }}", "{{ issue_count }}"]
    header_colors = ["D9D9D9", "FF0000", "FF9900", "70AD47", "D9D9D9"]
    value_colors  = ["D9D9D9", "FCE4D6", "FFF2CC", "E2EFDA", "D9D9D9"]
    for i, (hdr, color) in enumerate(zip(headers, header_colors)):
        cell = summary_tbl.rows[0].cells[i]
        _set_cell_background(cell, color)
        _set_cell_text(cell, hdr, bold=True, center=True)
    for i, (val, color) in enumerate(zip(values, value_colors)):
        cell = summary_tbl.rows[1].cells[i]
        _set_cell_background(cell, color)
        _set_cell_text(cell, val, center=True)

    doc.add_paragraph()

    _add_subsection_heading(doc, "2. 주요 발견사항 요약")
    _add_body(doc, "※ 아래는 주요 이슈 항목 요약입니다. 상세 서술 분석은 섹션별 보고를 참조하십시오.")
    doc.add_page_break()

    # ── 섹션별 서술 분석 ──
    _add_section_heading(doc, "II. 섹션별 분석")

    # 섹션 루프
    _add_jinja_block(doc, "{%p for section in narrative_items %}")
    _add_subsection_heading(doc, "{{ section.section_title }}")

    # 항목 루프
    _add_jinja_block(doc, "{%p for item in section.items %}")

    # 항목 제목
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(10)
    para.paragraph_format.space_after = Pt(4)
    run = para.add_run("{{ item.item_id }}. {{ item.item_name }}")
    _apply_font(run, size_pt=12.0, bold=True)

    # 항목 상태 표시
    _add_body(doc, "[상태: {{ item.status }}{% if item.issue_level %} / {{ item.issue_level }}{% endif %}]")

    # 블록 루프 — 각 블록은 소제목 + 본문
    _add_jinja_block(doc, "{%p for block in item.blocks %}")

    para_block_title = doc.add_paragraph()
    para_block_title.paragraph_format.space_before = Pt(6)
    run_bt = para_block_title.add_run("{{ block.title }}")
    _apply_font(run_bt, size_pt=11.0, bold=True)

    _add_body(doc, "{{ block.content }}")

    _add_jinja_block(doc, "{%p endfor %}")  # end block loop

    doc.add_paragraph()  # 항목 사이 간격
    _add_jinja_block(doc, "{%p endfor %}")  # end item loop
    _add_jinja_block(doc, "{%p endfor %}")  # end section loop
    doc.add_page_break()

    # ── 이슈 요약 테이블 ──
    _add_section_heading(doc, "III. 이슈 목록 요약")
    _add_body(doc, "※ ISSUE로 분류된 항목의 종합 목록입니다.")
    doc.add_paragraph()

    issue_tbl = doc.add_table(rows=1, cols=6)
    issue_tbl.style = "Table Grid"
    issue_hdrs = ["섹션", "항목명", "이슈등급", "발견사항", "거래영향", "RFI 번호"]
    for j, hdr in enumerate(issue_hdrs):
        _set_cell_background(issue_tbl.rows[0].cells[j], "D9D9D9")
        _set_cell_text(issue_tbl.rows[0].cells[j], hdr, size_pt=9.0, bold=True, center=True)

    issue_row = issue_tbl.add_row()
    issue_row.cells[0].text = ""
    issue_row.cells[0].paragraphs[0].add_run("{%tr for issue in all_issues %}")
    for j in range(1, 6):
        issue_row.cells[j].text = ""

    issue_data_row = issue_tbl.add_row()
    issue_vals = [
        "{{ issue.section_title }}",
        "{{ issue.name }}",
        "{{ issue.issue_level }}",
        "{{ issue.description }}",
        "{{ issue.deal_impact }}",
        "{{ issue.rfi_number if issue.rfi_required else '' }}",
    ]
    for j, val in enumerate(issue_vals):
        _set_cell_text(issue_data_row.cells[j], val, size_pt=9.0)

    issue_end_row = issue_tbl.add_row()
    issue_end_row.cells[0].text = ""
    issue_end_row.cells[0].paragraphs[0].add_run("{%tr endfor %}")
    for j in range(1, 6):
        issue_end_row.cells[j].text = ""

    doc.add_paragraph()
    _add_body(doc, "— 이 상 —")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    print(f"[OK] NARRATIVE FULL 템플릿 생성: {output_path}")


# ─── NARRATIVE REDFLAG 템플릿 ────────────────────────────────────────────────

def create_narrative_redflag_template(output_path: Path) -> None:
    """서술형 Redflag DD 템플릿.

    Critical/High/Medium 이슈 항목만 서술 분석 포함.
    """
    doc = Document()
    _set_margins(doc)

    # ── 표지 ──
    _add_title(doc, "{{ title }}", size_pt=16.0, space_before_pt=60.0)
    _add_subtitle(doc, "Redflag Due Diligence Report (서술형)", size_pt=11.0)
    doc.add_paragraph()
    _add_body(doc, "대상회사:  {{ target_company }}", indent_cm=2.0)
    _add_body(doc, "실사기간:  {{ dd_period }}", indent_cm=2.0)
    _add_body(doc, "보고서유형: Redflag DD (Red/Amber 이슈 서술 분석)", indent_cm=2.0)
    _add_body(doc, "법무법인:  {{ law_firm }}", indent_cm=2.0)
    _add_body(doc, "담당변호사: {{ prepared_by }}", indent_cm=2.0)
    _add_body(doc, "작성일:    {{ report_date }}", indent_cm=2.0)
    doc.add_page_break()

    # ── Executive Summary ──
    _add_section_heading(doc, "I. Executive Summary")
    _add_body(doc, "본 Redflag DD는 대상회사 {{ target_company }}에 대한 "
              "법률실사에서 Red(Critical) 및 Amber(High/Medium) 등급 이슈를 중심으로 "
              "심층 서술 분석을 제공한다.")
    doc.add_paragraph()

    rf_tbl = doc.add_table(rows=2, cols=4)
    rf_tbl.style = "Table Grid"
    rf_headers = ["Critical (Red)", "High/Medium (Amber)", "Low (Green)", "합계"]
    rf_values  = ["{{ red_count }}", "{{ amber_count }}", "{{ green_count }}", "{{ issue_count }}"]
    rf_h_colors = ["FF0000", "FF9900", "70AD47", "D9D9D9"]
    rf_v_colors = ["FCE4D6", "FFF2CC", "E2EFDA", "D9D9D9"]
    for i, (hdr, color) in enumerate(zip(rf_headers, rf_h_colors)):
        cell = rf_tbl.rows[0].cells[i]
        _set_cell_background(cell, color)
        _set_cell_text(cell, hdr, bold=True, center=True)
    for i, (val, color) in enumerate(zip(rf_values, rf_v_colors)):
        cell = rf_tbl.rows[1].cells[i]
        _set_cell_background(cell, color)
        _set_cell_text(cell, val, center=True)
    doc.add_page_break()

    # ── 서술형 Findings ──
    _add_section_heading(doc, "II. 상세 Findings (서술 분석)")
    _add_body(doc, "※ Green(Low) 이슈, OK, N/A 항목은 본 보고서에서 제외합니다.")
    doc.add_paragraph()

    _add_jinja_block(doc, "{%p for section in narrative_items %}")
    _add_subsection_heading(doc, "{{ section.section_title }}")

    _add_jinja_block(doc, "{%p for item in section.items %}")

    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(10)
    run = para.add_run("{{ item.item_id }}. {{ item.item_name }}")
    _apply_font(run, size_pt=12.0, bold=True)

    _add_body(doc, "[{{ item.status }} / {{ item.issue_level }}]")

    _add_jinja_block(doc, "{%p for block in item.blocks %}")
    para_bt = doc.add_paragraph()
    para_bt.paragraph_format.space_before = Pt(6)
    run_bt = para_bt.add_run("{{ block.title }}")
    _apply_font(run_bt, size_pt=11.0, bold=True)
    _add_body(doc, "{{ block.content }}")
    _add_jinja_block(doc, "{%p endfor %}")

    doc.add_paragraph()
    _add_jinja_block(doc, "{%p endfor %}")
    _add_jinja_block(doc, "{%p endfor %}")

    _add_body(doc, "— 이 상 —")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    print(f"[OK] NARRATIVE REDFLAG 템플릿 생성: {output_path}")


# ─── 진입점 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    create_full_template(TEMPLATE_DIR / "ldd_full_template.docx")
    create_redflag_template(TEMPLATE_DIR / "ldd_redflag_template.docx")
    create_narrative_full_template(TEMPLATE_DIR / "ldd_narrative_full_template.docx")
    create_narrative_redflag_template(TEMPLATE_DIR / "ldd_narrative_redflag_template.docx")

    print(f"\n[DIR] 템플릿 저장 위치: {TEMPLATE_DIR.resolve()}")
    print("[OK] LDD 템플릿 생성 완료 (버전:", TEMPLATE_VERSION, ")")
