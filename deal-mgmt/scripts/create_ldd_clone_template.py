"""
LDD 법률실사보고서 — 원본 기반 양식 템플릿 생성 스크립트.

원본 docx 파일의 스타일/테마/번호매기기/표 서식을 100% 보존하면서
본문 텍스트만 [플레이스홀더]로 교체하여 재사용 가능한 템플릿을 생성한다.

입력: deal-mgmt/output/Project_Green_Legal_DD_final_251223.docx
출력: deal-mgmt/output/LDD_Legal_DD_Template.docx

사용법:
    python deal-mgmt/scripts/create_ldd_clone_template.py
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
INPUT_PATH = PROJECT_ROOT / "deal-mgmt" / "output" / "Project_Green_Legal_DD_final_251223.docx"
OUTPUT_PATH = PROJECT_ROOT / "deal-mgmt" / "output" / "LDD_Legal_DD_Template.docx"

# ─── 스타일 기반 분류 ──────────────────────────────────────────────────────────

# 섹션 헤더 바를 식별하기 위한 배경색
SECTION_BAR_FILLS = {"26382A", "385623"}

# Recommendation 박스 배경색
RECOMMENDATION_FILL = "E2EFD9"

# 데이터 표 헤더 배경색
DATA_TABLE_HEADER_FILL = "E2EFD9"

# 목차 체계 — 원본의 8개 대목차
TOC_SECTIONS = [
    "대상회사 일반 및 거래구조",
    "인허가 및 법률이슈",
    "계약",
    "부동산 및 자산",
    "환경",
    "인사 및 노무",
    "소송",
    "소송 및 분쟁",
]

# 보존할 스타일 (텍스트를 교체하지 않음)
PRESERVE_STYLES = {"11", "22", "31", "40"}  # TOC 스타일들


def _get_cell_fill(cell) -> str | None:
    """셀의 배경색(fill) 값을 반환."""
    tc = cell._tc
    tcPr = tc.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tcPr")
    if tcPr is None:
        return None
    shd = tcPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd")
    if shd is None:
        return None
    return shd.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fill")


def _is_section_header_bar(table) -> bool:
    """3열 섹션 헤더 바인지 판별."""
    if len(table.rows) != 1:
        return False
    cells = table.rows[0].cells
    if len(cells) != 3:
        return False
    fill0 = _get_cell_fill(cells[0])
    return fill0 in SECTION_BAR_FILLS


def _is_recommendation_box(table) -> bool:
    """Recommendation 단일 셀 박스인지 판별."""
    if len(table.rows) != 1:
        return False
    cells = table.rows[0].cells
    if len(cells) != 1:
        return False
    fill = _get_cell_fill(cells[0])
    text = cells[0].text.strip()
    return fill == RECOMMENDATION_FILL or "Recommendation" in text


def _is_data_table(table) -> bool:
    """데이터 표(2행 이상, 헤더 행 배경색)인지 판별."""
    if len(table.rows) < 2:
        return False
    first_cell = table.rows[0].cells[0]
    fill = _get_cell_fill(first_cell)
    return fill == DATA_TABLE_HEADER_FILL


def _clear_paragraph_text(paragraph, placeholder: str) -> None:
    """단락의 모든 run 텍스트를 제거하고 첫 번째 run에 placeholder 설정.
    서식(bold, font, color 등)은 첫 번째 run의 것을 유지."""
    runs = paragraph.runs
    if not runs:
        return

    # 첫 run에 placeholder 텍스트 설정
    runs[0].text = placeholder

    # 나머지 run 텍스트 비우기
    for run in runs[1:]:
        run.text = ""


def _clear_cell_content(cell, placeholder: str = "") -> None:
    """셀의 모든 단락 텍스트를 비우고 선택적으로 placeholder 삽입."""
    for i, para in enumerate(cell.paragraphs):
        if i == 0 and placeholder:
            _clear_paragraph_text(para, placeholder)
        else:
            for run in para.runs:
                run.text = ""


def _get_paragraph_style_id(paragraph) -> str:
    """단락의 스타일 ID 반환."""
    if paragraph.style and paragraph.style.style_id:
        return paragraph.style.style_id
    return ""


def _get_paragraph_num_info(paragraph) -> tuple[str, str]:
    """단락의 numId, ilvl 반환."""
    pPr = paragraph._p.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr")
    if pPr is None:
        return "", ""
    numPr = pPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr")
    if numPr is None:
        return "", ""
    numId_el = numPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numId")
    ilvl_el = numPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ilvl")
    numId = (
        numId_el.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "")
        if numId_el is not None
        else ""
    )
    ilvl = (
        ilvl_el.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "")
        if ilvl_el is not None
        else ""
    )
    return numId, ilvl


# ─── 대목차/중목차 플레이스홀더 매핑 ─────────────────────────────────────────────

SECTION_PLACEHOLDERS = {
    0: "[부문명 기재]",  # 대목차 (I, II, III...)
    1: "[소주제명 기재]",  # 중목차 (1, 2, 3...)
    2: "[세부항목명 기재]",  # 소목차 (가, 나, 다...)
}

BODY_PLACEHOLDER = "[이곳에 텍스트 입력]"
COVER_PROJECT_PLACEHOLDER = "Project [프로젝트 코드명]"
COVER_DATE_PLACEHOLDER = "[YYYY]년 [MM]월 [DD]일"
COVER_RECIPIENT = "귀     중"


def _get_style_id_from_xml(p_element) -> str:
    """XML 요소에서 직접 스타일 ID 추출."""
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    pPr = p_element.find(f"{{{ns}}}pPr")
    if pPr is None:
        return ""
    pStyle = pPr.find(f"{{{ns}}}pStyle")
    if pStyle is None:
        return ""
    return pStyle.get(f"{{{ns}}}val", "")


def _get_num_info_from_xml(p_element) -> tuple[str, str]:
    """XML 요소에서 직접 numId, ilvl 추출."""
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    pPr = p_element.find(f"{{{ns}}}pPr")
    if pPr is None:
        return "", ""
    numPr = pPr.find(f"{{{ns}}}numPr")
    if numPr is None:
        return "", ""
    numId_el = numPr.find(f"{{{ns}}}numId")
    ilvl_el = numPr.find(f"{{{ns}}}ilvl")
    numId = numId_el.get(f"{{{ns}}}val", "") if numId_el is not None else ""
    ilvl = ilvl_el.get(f"{{{ns}}}val", "") if ilvl_el is not None else ""
    return numId, ilvl


def _get_text_from_xml(element) -> str:
    """XML 요소에서 모든 텍스트 추출."""
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    texts = []
    for t in element.iter(f"{{{ns}}}t"):
        if t.text:
            texts.append(t.text)
    return "".join(texts)


def _clear_runs_in_xml(p_element, placeholder: str) -> None:
    """XML p 요소 내의 run 텍스트를 placeholder로 교체.
    첫 번째 run의 첫 번째 t에 placeholder, 나머지 t는 비움."""
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    first_t = True
    for t in p_element.iter(f"{{{ns}}}t"):
        if first_t:
            t.text = placeholder
            # preserve space
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            first_t = False
        else:
            t.text = ""


def _clear_cell_runs_xml(tc_element, placeholder: str = "") -> None:
    """XML tc 요소 내의 모든 텍스트를 비우고 선택적으로 placeholder."""
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    first_t = True
    for t in tc_element.iter(f"{{{ns}}}t"):
        if first_t and placeholder:
            t.text = placeholder
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            first_t = False
        else:
            t.text = ""


def _get_cell_fill_xml(tc_element) -> str | None:
    """XML tc 요소에서 배경색 추출."""
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    tcPr = tc_element.find(f"{{{ns}}}tcPr")
    if tcPr is None:
        return None
    shd = tcPr.find(f"{{{ns}}}shd")
    if shd is None:
        return None
    return shd.get(f"{{{ns}}}fill")


def process_document(input_path: Path, output_path: Path) -> None:
    """원본 docx를 로드하여 내용을 템플릿화한 뒤 저장."""
    doc = Document(str(input_path))
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

    # ── 본문 요소 처리 (XML 레벨) ──
    section_counter = 0

    for element in list(doc.element.body):
        tag = element.tag.split("}")[-1]

        if tag == "p":
            style_id = _get_style_id_from_xml(element)
            numId, ilvl = _get_num_info_from_xml(element)
            text = _get_text_from_xml(element).strip()

            # TOC 스타일은 보존
            if style_id in PRESERVE_STYLES:
                continue

            # 빈 단락은 유지
            if not text:
                continue

            # Title 스타일 (표지)
            if style_id == "ae":
                if "Project" in text:
                    _clear_runs_in_xml(element, COVER_PROJECT_PLACEHOLDER)
                continue

            # 날짜 패턴
            if re.match(r"\d{4}.*년.*\d{1,2}.*월.*\d{1,2}.*일", text):
                _clear_runs_in_xml(element, COVER_DATE_PLACEHOLDER)
                continue

            # "귀     중" 보존
            if "귀" in text and "중" in text and len(text) < 10:
                continue

            # EXECUTIVE SUMMARY 보존
            if text == "EXECUTIVE SUMMARY":
                continue

            # 스타일 12 = 섹션 헤더
            if style_id == "12":
                if numId:
                    ilvl_int = int(ilvl) if ilvl else 0
                    placeholder = SECTION_PLACEHOLDERS.get(ilvl_int, "[항목명 기재]")
                    _clear_runs_in_xml(element, placeholder)
                else:
                    _clear_runs_in_xml(element, BODY_PLACEHOLDER)
                continue

            # List Paragraph / Normal 본문
            if style_id in ("a5", "a", "", "a0"):
                if numId:
                    ilvl_int = int(ilvl) if ilvl else 0
                    if ilvl_int <= 2:
                        placeholder = SECTION_PLACEHOLDERS.get(ilvl_int, "[항목명 기재]")
                    else:
                        placeholder = "[세부사항 기재]"
                    _clear_runs_in_xml(element, placeholder)
                else:
                    _clear_runs_in_xml(element, BODY_PLACEHOLDER)
                continue

            # EndnoteText1, ad 등
            if style_id in ("EndnoteText1", "ad"):
                if text:
                    _clear_runs_in_xml(element, "")
                continue

            # 기타
            if text:
                _clear_runs_in_xml(element, BODY_PLACEHOLDER)

        elif tag == "tbl":
            # 테이블 처리 — XML 레벨
            rows = element.findall(f"{{{ns}}}tr")

            # 3열 섹션 헤더 바 판별
            if len(rows) == 1:
                cells = rows[0].findall(f"{{{ns}}}tc")
                if len(cells) == 3:
                    fill0 = _get_cell_fill_xml(cells[0])
                    if fill0 in SECTION_BAR_FILLS:
                        section_counter += 1
                        if section_counter == 1:
                            _clear_cell_runs_xml(cells[2], "[법무법인 명칭]")
                        else:
                            _clear_cell_runs_xml(cells[2], "[부문명 기재]")
                        continue

                # Recommendation 박스 (1열)
                if len(cells) == 1:
                    fill = _get_cell_fill_xml(cells[0])
                    text = _get_text_from_xml(cells[0])
                    if fill == RECOMMENDATION_FILL or "Recommendation" in text:
                        _clear_cell_runs_xml(cells[0], "Recommendation: [권고사항 기재]")
                        continue

            # 데이터 표 (2행 이상)
            if len(rows) >= 2:
                first_cells = rows[0].findall(f"{{{ns}}}tc")
                if first_cells:
                    fill = _get_cell_fill_xml(first_cells[0])
                    is_data = fill == DATA_TABLE_HEADER_FILL

                    for row_idx, row in enumerate(rows):
                        if row_idx == 0:
                            continue  # 헤더 행 유지
                        for tc in row.findall(f"{{{ns}}}tc"):
                            _clear_cell_runs_xml(tc, "")
                    continue

    # ── 머리글/바닥글 처리 ──
    for section in doc.sections:
        # 머리글
        if section.header and section.header.paragraphs:
            for para in section.header.paragraphs:
                if para.text.strip():
                    _clear_paragraph_text(para, "[법무법인 명칭]")

        # 바닥글은 페이지 번호 필드가 있으므로 텍스트 부분만 교체
        # (PAGE 필드 코드는 자동 보존됨)

    # ── 각주 처리 ──
    # python-docx로 직접 접근이 제한적이므로 XML 레벨에서 처리
    footnotes_part = None
    for rel in doc.part.rels.values():
        if "footnotes" in str(rel.reltype):
            footnotes_part = rel.target_part
            break

    if footnotes_part:
        from lxml import etree

        fn_root = etree.fromstring(footnotes_part.blob)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        for footnote in fn_root.findall("w:footnote", ns):
            fn_type = footnote.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type")
            if fn_type in ("separator", "continuationSeparator"):
                continue
            # 각주 텍스트를 플레이스홀더로 교체
            for t in footnote.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
                if t.text and t.text.strip():
                    t.text = "[각주 내용 기재]"
                    break  # 첫 텍스트 노드만 교체, 나머지는 비움
            # 첫 번째 이후의 t 요소 비우기
            first_found = False
            for t in footnote.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
                if not first_found:
                    first_found = True
                    continue
                t.text = ""

        footnotes_part._blob = etree.tostring(fn_root, xml_declaration=True, encoding="UTF-8", standalone=True)

    # ── 저장 ──
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    print(f"[OK] 템플릿 생성 완료: {output_path}")
    print(f"     원본: {input_path.name}")
    print(f"     출력: {output_path.name}")


if __name__ == "__main__":
    if not INPUT_PATH.exists():
        print(f"[ERROR] 원본 파일을 찾을 수 없습니다: {INPUT_PATH}")
        raise SystemExit(1)

    process_document(INPUT_PATH, OUTPUT_PATH)
