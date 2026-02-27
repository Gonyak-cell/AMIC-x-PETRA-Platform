"""모듈 2: 대형 동적 테이블 — 가변 행 데이터 삽입, 행 추가, 폰트 축소, 페이지 분할.

python-pptx에 Table.add_row() API가 없으므로 lxml deepcopy로 행을 추가한다.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from lxml import etree
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.util import Pt

from .constants import (
    COLOR_GREEN_LIGHT,
    COLOR_GREEN_PRIMARY,
    COLOR_NEGATIVE,
    COLOR_TEXT_DARK,
    COLOR_TEXT_WHITE,
    FONT_BODY,
    FONT_SIZE_BODY,
    MAX_ROWS_PER_SLIDE,
    MIN_FONT_SIZE,
)
from .exceptions import TableShapeError
from .font_helper import set_font_with_ea
from .number_formatter import format_cell_value
from .shape_finder import find_shape_by_name, get_shape_bounds

logger = logging.getLogger(__name__)


def replace_table_data(
    slide: Any,
    shape_name: str,
    headers: list[str] | None,
    rows: list[list[Any]],
    *,
    header_row_index: int = 0,
    auto_expand: bool = True,
    negative_color: str = COLOR_NEGATIVE,
    font_size_base: int = FONT_SIZE_BODY,
    font_size_min: int = MIN_FONT_SIZE,
    alt_row_bg: str = COLOR_GREEN_LIGHT,
) -> Any:
    """기존 테이블의 데이터를 교체하고 필요시 행을 동적 추가한다.

    Args:
        slide: Slide 인스턴스.
        shape_name: 테이블을 포함한 shape의 name.
        headers: 헤더 라벨. None이면 기존 헤더 유지.
        rows: 2D 데이터 배열.
        header_row_index: 헤더 행의 인덱스.
        auto_expand: True이면 행 부족 시 자동 추가.
        negative_color: 음수 값 텍스트 색상 (hex).
        font_size_base: 기본 폰트 크기 (pt).
        font_size_min: 최소 폰트 크기 (pt).
        alt_row_bg: 교대 행 배경색 (hex).

    Returns:
        업데이트된 table shape.
    """
    shape = find_shape_by_name(slide, shape_name)

    if not shape.has_table:
        raise TableShapeError(f"'{shape_name}'에 테이블이 없습니다.")

    table = shape.table
    tbl_xml = table._tbl

    existing_data_rows = len(table.rows) - 1  # 헤더 제외
    needed_rows = len(rows)

    # ── 행 추가 (auto_expand) ──
    if needed_rows > existing_data_rows and auto_expand:
        _add_rows_by_cloning(tbl_xml, needed_rows - existing_data_rows)
        logger.info(
            "테이블 '%s': %d행 추가 (기존 %d → 필요 %d)",
            shape_name,
            needed_rows - existing_data_rows,
            existing_data_rows,
            needed_rows,
        )

    # ── 폰트 크기 조정 (오버플로우 방지) ──
    total_rows = needed_rows + 1  # +1 for header
    _, _, _, shape_height = get_shape_bounds(shape)
    available_height_pt = shape_height / 12700  # EMU → pt
    row_height_pt = available_height_pt / total_rows if total_rows > 0 else available_height_pt

    effective_font_size = font_size_base
    if row_height_pt < font_size_base * 1.5:
        effective_font_size = max(font_size_min, int(row_height_pt / 1.5))
        logger.info(
            "테이블 '%s': 폰트 축소 %dpt → %dpt (행 %d개)",
            shape_name,
            font_size_base,
            effective_font_size,
            total_rows,
        )

    # ── 헤더 갱신 ──
    if headers:
        for col_idx, header_text in enumerate(headers):
            if col_idx < len(table.columns):
                cell = table.cell(header_row_index, col_idx)
                _set_cell_text(
                    cell,
                    header_text,
                    bold=True,
                    font_size=effective_font_size,
                    color=COLOR_TEXT_WHITE,
                )
                _set_cell_bg(cell, COLOR_GREEN_PRIMARY)

    # ── 데이터 행 갱신 ──
    for row_idx, row_data in enumerate(rows):
        actual_row = row_idx + header_row_index + 1
        if actual_row >= len(table.rows):
            break

        for col_idx, value in enumerate(row_data):
            if col_idx >= len(table.columns):
                break
            cell = table.cell(actual_row, col_idx)

            is_negative = isinstance(value, (int, float)) and value < 0
            formatted = format_cell_value(value)

            _set_cell_text(
                cell,
                formatted,
                font_size=effective_font_size,
                color=negative_color if is_negative else COLOR_TEXT_DARK,
            )

        # 교대 행 배경
        if (row_idx + 1) % 2 == 0 and alt_row_bg:
            for col_idx in range(len(table.columns)):
                if actual_row < len(table.rows):
                    _set_cell_bg(table.cell(actual_row, col_idx), alt_row_bg)

    logger.info(
        "테이블 '%s' 데이터 교체 완료: %d행 × %d열, font=%dpt",
        shape_name,
        needed_rows,
        len(table.columns),
        effective_font_size,
    )

    return shape


def split_table_across_slides(
    prs: Any,
    slide_index: int,
    shape_name: str,
    headers: list[str] | None,
    rows: list[list[Any]],
    *,
    max_rows_per_slide: int = MAX_ROWS_PER_SLIDE,
) -> int:
    """행이 한 슬라이드를 초과할 경우 슬라이드를 복제하여 분할.

    Args:
        prs: Presentation 인스턴스.
        slide_index: 원본 테이블이 있는 슬라이드 인덱스.
        shape_name: 테이블 shape name.
        headers: 헤더 라벨.
        rows: 전체 데이터 행.
        max_rows_per_slide: 슬라이드당 최대 행 수.

    Returns:
        생성된 총 슬라이드 수.
    """
    chunks = [rows[i : i + max_rows_per_slide] for i in range(0, len(rows), max_rows_per_slide)]

    if len(chunks) <= 1:
        replace_table_data(prs.slides[slide_index], shape_name, headers, rows)
        return 1

    # 첫 번째 청크: 원본 슬라이드
    replace_table_data(prs.slides[slide_index], shape_name, headers, chunks[0])

    # 나머지 청크: 슬라이드 복제
    for chunk in chunks[1:]:
        new_slide = _duplicate_slide(prs, slide_index)
        replace_table_data(new_slide, shape_name, headers, chunk)

    logger.info(
        "테이블 '%s' 페이지 분할: %d행 → %d페이지 (max %d행/페이지)",
        shape_name,
        len(rows),
        len(chunks),
        max_rows_per_slide,
    )

    return len(chunks)


# ── 내부 헬퍼 ─────────────────────────────────────────────────


def _add_rows_by_cloning(tbl_xml: Any, count: int) -> None:
    """테이블 XML에 행을 deepcopy로 추가.

    마지막 행의 XML(<a:tr>)을 복제하여 추가한다.
    python-pptx에 Table.add_row()가 없으므로 lxml 직접 조작.
    """
    tr_tag = qn("a:tr")
    existing_trs = tbl_xml.findall(tr_tag)

    if not existing_trs:
        return

    template_tr = existing_trs[-1]

    for _ in range(count):
        new_tr = deepcopy(template_tr)
        # 셀 텍스트 초기화
        for tc in new_tr.findall(qn("a:tc")):
            for txBody in tc.findall(qn("a:txBody")):
                for p in txBody.findall(qn("a:p")):
                    for r in p.findall(qn("a:r")):
                        t = r.find(qn("a:t"))
                        if t is not None:
                            t.text = ""
        tbl_xml.append(new_tr)


def _duplicate_slide(prs: Any, slide_index: int) -> Any:
    """슬라이드를 복제하여 바로 뒤에 삽입.

    python-pptx에 slide.duplicate()가 없으므로,
    동일 레이아웃의 새 슬라이드를 추가하고 shape XML을 복사한다.
    """
    source_slide = prs.slides[slide_index]
    slide_layout = source_slide.slide_layout

    new_slide = prs.slides.add_slide(slide_layout)

    for shape in source_slide.shapes:
        el = deepcopy(shape._element)
        new_slide.shapes._spTree.append(el)

    return new_slide


def _set_cell_text(
    cell: Any,
    text: str,
    *,
    bold: bool = False,
    font_size: int = FONT_SIZE_BODY,
    color: str = COLOR_TEXT_DARK,
) -> None:
    """테이블 셀의 텍스트를 설정하고 폰트를 적용한다."""
    cell.text = ""
    tf = cell.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color.lstrip("#"))
    set_font_with_ea(run, FONT_BODY)


def _set_cell_bg(cell: Any, hex_color: str) -> None:
    """셀 배경색을 lxml로 직접 설정한다.

    python-pptx의 셀 배경 API가 불안정하므로 XML 직접 조작.
    """
    tc = cell._tc
    tc_pr = tc.find(qn("a:tcPr"))
    if tc_pr is None:
        tc_pr = etree.SubElement(tc, qn("a:tcPr"))

    # 기존 solidFill 제거
    for existing in tc_pr.findall(qn("a:solidFill")):
        tc_pr.remove(existing)

    sf = etree.SubElement(tc_pr, qn("a:solidFill"))
    sc = etree.SubElement(sf, qn("a:srgbClr"))
    sc.set("val", hex_color.lstrip("#"))
