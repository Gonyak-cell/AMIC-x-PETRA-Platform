"""Excel 보고서 렌더러.

Report IR을 Excel(.xlsx) 파일로 변환합니다.
openpyxl 기반 멀티시트 워크북을 생성합니다.
Phase 1~4: 재무제표(IS/BS/CF) + Index + 트렌드 + 전문 스타일링.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side, numbers
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.renderers.report_builder import (
    AlignType,
    CoverBlock,
    IssueBlock,
    KPIBlock,
    ReportBlock,
    ReportIR,
    ScopeBlock,
    TableBlock,
    TextBlock,
)

EXCEL_RENDERER_VERSION = "0.2.0"


# ═════════════════════════════════════════════════════════════════════════
# Styles
# ═════════════════════════════════════════════════════════════════════════

_PRIMARY = "003366"
_POSITIVE = "2E7D32"
_NEGATIVE = "E0301E"
_NEUTRAL = "666666"
_LIGHT_BG = "F5F5F5"
_WHITE = "FFFFFF"

_HEADER_FILL = PatternFill(start_color=_PRIMARY, end_color=_PRIMARY, fill_type="solid")
_HEADER_FONT = Font(name="맑은 고딕", size=9, bold=True, color=_WHITE)
_BODY_FONT = Font(name="맑은 고딕", size=9)
_BOLD_FONT = Font(name="맑은 고딕", size=9, bold=True)
_TITLE_FONT = Font(name="맑은 고딕", size=14, bold=True, color=_PRIMARY)
_BIG_FONT = Font(name="맑은 고딕", size=22, bold=True, color=_PRIMARY)
_SUBTITLE_FONT = Font(name="맑은 고딕", size=11, color=_NEUTRAL)
_KPI_VALUE_FONT = Font(name="맑은 고딕", size=16, bold=True, color=_PRIMARY)
_KPI_LABEL_FONT = Font(name="맑은 고딕", size=9, color=_NEUTRAL)

_THIN_BORDER = Border(
    left=Side(style="thin", color="D0D0D0"),
    right=Side(style="thin", color="D0D0D0"),
    top=Side(style="thin", color="D0D0D0"),
    bottom=Side(style="thin", color="D0D0D0"),
)
_BOTTOM_BORDER = Border(bottom=Side(style="medium", color=_PRIMARY))

_ZEBRA_FILL = PatternFill(start_color=_LIGHT_BG, end_color=_LIGHT_BG, fill_type="solid")

# Severity-based fills
_SEVERITY_FILLS = {
    "critical": PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid"),
    "high": PatternFill(start_color="FFE0CC", end_color="FFE0CC", fill_type="solid"),
    "medium": PatternFill(start_color="FFFFCC", end_color="FFFFCC", fill_type="solid"),
    "low": PatternFill(start_color="CCE5CC", end_color="CCE5CC", fill_type="solid"),
}

# Checklist status fills
_STATUS_FILLS = {
    "AUTO_GENERATED": PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid"),
    "CONFIRMED": PatternFill(start_color="CCE5CC", end_color="CCE5CC", fill_type="solid"),
    "CORRECTED": PatternFill(start_color="CCE0FF", end_color="CCE0FF", fill_type="solid"),
    "FLAGGED": PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid"),
    "NOT_APPLICABLE": PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid"),
}

# ── Financial Statement 전문 스타일 ──

_FS_SUBTOTAL_FONT = Font(name="맑은 고딕", size=9, bold=True)
_FS_TOTAL_FONT = Font(name="맑은 고딕", size=9, bold=True)
_FS_SUBTOTAL_BORDER = Border(
    bottom=Side(style="thin", color=_PRIMARY),
    top=Side(style="thin", color="D0D0D0"),
)
_FS_TOTAL_BORDER = Border(
    bottom=Side(style="double", color=_PRIMARY),
    top=Side(style="thin", color=_PRIMARY),
)
_FS_SECTION_FILL = PatternFill(start_color="E8EEF4", end_color="E8EEF4", fill_type="solid")
_FS_UNIT_FONT = Font(name="맑은 고딕", size=8, italic=True, color=_NEUTRAL)
_POSITIVE_FONT = Font(name="맑은 고딕", size=9, color=_POSITIVE)
_NEGATIVE_FONT = Font(name="맑은 고딕", size=9, color=_NEGATIVE)
_POSITIVE_FILL = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
_NEGATIVE_FILL = PatternFill(start_color="FFEBEE", end_color="FFEBEE", fill_type="solid")
_INDEX_LINK_FONT = Font(name="맑은 고딕", size=10, underline="single", color="0563C1")
_INDEX_CATEGORY_FONT = Font(name="맑은 고딕", size=11, bold=True, color=_PRIMARY)
_PASS_FILL = PatternFill(start_color="CCE5CC", end_color="CCE5CC", fill_type="solid")
_FAIL_FILL = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")

# 시트 탭 색상 (RRGGBB)
_TAB_COLORS = {
    "fs": "003366",       # 파랑 — 재무제표
    "qoe": "2E7D32",      # 초록 — QoE
    "nwc": "E65100",      # 주황 — NWC
    "debt": "E0301E",     # 빨강 — Net Debt
    "trend": "1565C0",    # 파랑계 — 트렌드
    "sales": "6A1B9A",    # 보라 — 매출/원가
    "recon": "37474F",    # 짙은회색 — Reconciliation
    "appendix": "9E9E9E", # 회색 — 부록
    "index": "000000",    # 검정 — Index
}


# ═════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════


def _to_decimal(value: Any) -> Decimal | None:
    """값을 Decimal로 변환. 실패 시 None."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _format_cell_value(value: Any, fmt: str | None) -> Any:
    """셀 값 포맷팅. 숫자면 Decimal, 아니면 문자열."""
    if fmt in ("currency", "percentage", "number"):
        d = _to_decimal(value)
        if d is not None:
            return float(d)  # openpyxl은 float 선호
    if value is None:
        return ""
    return str(value)


def _get_alignment(align: AlignType) -> Alignment:
    """AlignType → openpyxl Alignment."""
    h = {"LEFT": "left", "CENTER": "center", "RIGHT": "right"}.get(
        align.value.upper(), "left"
    )
    return Alignment(horizontal=h, vertical="center", wrap_text=True)


def _auto_width(ws: Worksheet, min_width: float = 8.0, max_width: float = 50.0) -> None:
    """컬럼 너비 자동 조정."""
    for col_cells in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col_cells[0].column)
        for cell in col_cells:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        adjusted = min(max(max_len + 2, min_width), max_width)
        ws.column_dimensions[col_letter].width = adjusted


def _display_width(text: str) -> int:
    """텍스트의 표시 너비를 반환 (한글/전각 문자는 2, 그 외 1)."""
    width = 0
    for ch in text:
        cp = ord(ch)
        # CJK Unified Ideographs, Hangul Syllables, Fullwidth Forms
        if (
            0xAC00 <= cp <= 0xD7AF  # Hangul Syllables
            or 0x3000 <= cp <= 0x303F  # CJK Symbols
            or 0x4E00 <= cp <= 0x9FFF  # CJK Unified Ideographs
            or 0xFF01 <= cp <= 0xFF60  # Fullwidth Forms
        ):
            width += 2
        else:
            width += 1
    return width


def _auto_row_height(
    ws: Worksheet,
    *,
    default_height: float = 15.0,
    header_height: float = 20.0,
    max_height: float = 60.0,
    col_width_chars: int = 40,
) -> None:
    """행 높이를 셀 내용 길이 기반으로 근사 조정.

    openpyxl은 auto-fit을 지원하지 않으므로
    셀 내용의 표시 너비를 기준으로 래핑 행 수를 추정합니다.
    한글(전각) 문자는 영문의 약 2배 너비로 계산합니다.

    Args:
        ws: 대상 워크시트
        default_height: 기본 행 높이 (pt)
        header_height: 헤더 행 높이 (pt)
        max_height: 최대 행 높이 (pt)
        col_width_chars: 줄바꿈 기준 컬럼 글자 수 (영문 기준)
    """
    for row_cells in ws.iter_rows(min_row=1, max_row=ws.max_row):
        row_num = row_cells[0].row
        max_lines = 1

        for cell in row_cells:
            if cell.value is None:
                continue
            text = str(cell.value)
            # 명시적 줄바꿈 + 표시 너비 기반 래핑 추정
            for line in text.split("\n"):
                display_width = _display_width(line)
                line_wraps = max(1, -(-display_width // col_width_chars))  # ceil division
                max_lines = max(max_lines, line_wraps)

        # 첫 행(또는 bold 폰트)이면 헤더 높이 사용
        first_cell = row_cells[0]
        base = header_height if (row_num == 1 or (first_cell.font and first_cell.font.bold)) else default_height
        ws.row_dimensions[row_num].height = min(base * max_lines, max_height)


def _write_section_title(ws: Worksheet, row: int, title: str) -> int:
    """섹션 제목 작성. 다음 행 반환."""
    cell = ws.cell(row=row, column=1, value=title)
    cell.font = _TITLE_FONT
    return row + 2


def _set_tab_color(ws: Worksheet, color_key: str) -> None:
    """시트 탭 색상 설정."""
    color = _TAB_COLORS.get(color_key)
    if color:
        ws.sheet_properties.tabColor = color


def _setup_print(ws: Worksheet, landscape: bool = True) -> None:
    """인쇄 설정: 가로 방향 + 맞춤 인쇄."""
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.oddHeader.center.text = "&A"  # 시트명
    ws.oddFooter.right.text = "Page &P of &N"


def _apply_variance_formatting(
    ws: Worksheet, col_letter: str, start_row: int, end_row: int
) -> None:
    """증감 컬럼 조건부 서식: 양수=초록, 음수=빨강."""
    rng = f"{col_letter}{start_row}:{col_letter}{end_row}"
    ws.conditional_formatting.add(
        rng,
        CellIsRule(
            operator="greaterThan",
            formula=["0"],
            font=_POSITIVE_FONT,
        ),
    )
    ws.conditional_formatting.add(
        rng,
        CellIsRule(
            operator="lessThan",
            formula=["0"],
            font=_NEGATIVE_FONT,
        ),
    )


# ═════════════════════════════════════════════════════════════════════════
# Sheet Renderers
# ═════════════════════════════════════════════════════════════════════════


def _render_cover_sheet(wb: Workbook, report_ir: ReportIR) -> None:
    """Cover & Summary 시트 렌더링."""
    ws = wb.active
    if ws is None:
        ws = wb.create_sheet()
    ws.title = "Cover & Summary"

    row = 2

    # 딜 이름
    cover_blocks = [b for b in report_ir.sections if isinstance(b, CoverBlock)]
    if cover_blocks:
        cover = cover_blocks[0]
        cell = ws.cell(row=row, column=2, value=cover.deal_name or "FDD Report")
        cell.font = _BIG_FONT
        cell.alignment = Alignment(horizontal="center")
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
        row += 1

        if cover.target_name:
            cell = ws.cell(row=row, column=2, value=cover.target_name)
            cell.font = _SUBTITLE_FONT
            cell.alignment = Alignment(horizontal="center")
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
            row += 1

        if cover.deal_type:
            cell = ws.cell(row=row, column=2, value=cover.deal_type)
            cell.font = _SUBTITLE_FONT
            cell.alignment = Alignment(horizontal="center")
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
            row += 1

        if cover.date:
            cell = ws.cell(
                row=row, column=2, value=cover.date.strftime("%Y년 %m월 %d일")
            )
            cell.font = _SUBTITLE_FONT
            cell.alignment = Alignment(horizontal="center")
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
            row += 1

        if cover.confidentiality:
            row += 1
            cell = ws.cell(row=row, column=2, value=cover.confidentiality)
            cell.font = Font(name="맑은 고딕", size=10, bold=True, color=_NEGATIVE)
            cell.alignment = Alignment(horizontal="center")
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
            row += 1

    # KPI 블록
    kpi_blocks = [b for b in report_ir.sections if isinstance(b, KPIBlock)]
    if kpi_blocks:
        row += 2
        for kpi_block in kpi_blocks:
            if kpi_block.title:
                row = _write_section_title(ws, row, kpi_block.title)

            col = 2
            for kpi in kpi_block.kpis:
                label = kpi.get("label", "")
                value = kpi.get("value", "")
                unit = kpi.get("unit", "")

                label_cell = ws.cell(row=row, column=col, value=label)
                label_cell.font = _KPI_LABEL_FONT
                label_cell.alignment = Alignment(horizontal="center")

                value_cell = ws.cell(
                    row=row + 1, column=col, value=f"{value} {unit}".strip()
                )
                value_cell.font = _KPI_VALUE_FONT
                value_cell.alignment = Alignment(horizontal="center")

                col += 1

            row += 3

    # Scope 블록
    scope_blocks = [b for b in report_ir.sections if isinstance(b, ScopeBlock)]
    if scope_blocks:
        for scope_block in scope_blocks:
            if scope_block.title:
                row = _write_section_title(ws, row, scope_block.title)

            for item in scope_block.scope_items:
                label_cell = ws.cell(row=row, column=2, value=item.label)
                label_cell.font = _BOLD_FONT
                ws.cell(row=row, column=3, value=item.value).font = _BODY_FONT
                row += 1

            row += 1

    _auto_width(ws)


def _render_table_sheet(
    wb: Workbook, block: TableBlock, sheet_name: str
) -> None:
    """TableBlock을 별도 시트로 렌더링."""
    ws = wb.create_sheet(title=sheet_name[:31])  # Excel 시트명 최대 31자
    row = 1

    # 제목
    if block.title:
        row = _write_section_title(ws, row, block.title)

    if not block.columns:
        return

    # 헤더 행
    if block.show_header:
        for col_idx, col_def in enumerate(block.columns, start=1):
            cell = ws.cell(row=row, column=col_idx, value=col_def.header)
            cell.font = _HEADER_FONT
            cell.fill = _HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = _THIN_BORDER
        row += 1

    # 데이터 행
    for row_idx, row_data in enumerate(block.rows):
        for col_idx, col_def in enumerate(block.columns, start=1):
            raw_value = row_data.get(col_def.key, "")
            value = _format_cell_value(raw_value, col_def.format)

            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.font = _BODY_FONT
            cell.alignment = _get_alignment(col_def.align)
            cell.border = _THIN_BORDER

            # 숫자 포맷
            if col_def.format == "currency" and isinstance(value, float):
                cell.number_format = "#,##0"
            elif col_def.format == "percentage" and isinstance(value, float):
                cell.number_format = "0.0%"

            # Zebra stripe
            if block.zebra_stripe and row_idx % 2 == 1:
                cell.fill = _ZEBRA_FILL

        row += 1

    # 푸터 행 (합계 등)
    for footer_data in block.footer_rows:
        for col_idx, col_def in enumerate(block.columns, start=1):
            raw_value = footer_data.get(col_def.key, "")
            value = _format_cell_value(raw_value, col_def.format)

            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.font = _BOLD_FONT
            cell.alignment = _get_alignment(col_def.align)
            cell.border = _BOTTOM_BORDER

            if col_def.format == "currency" and isinstance(value, float):
                cell.number_format = "#,##0"

        row += 1

    # 필터 추가 (헤더 행에)
    if block.show_header and block.rows:
        header_row = 2 if block.title else 1
        last_col = get_column_letter(len(block.columns))
        last_row = header_row + len(block.rows)
        ws.auto_filter.ref = f"A{header_row}:{last_col}{last_row}"

    _auto_width(ws)
    _auto_row_height(ws)


def _render_issue_sheet(wb: Workbook, block: IssueBlock) -> None:
    """IssueBlock을 Issues 시트로 렌더링."""
    ws = wb.create_sheet(title="Issues")
    row = 1

    if block.title:
        row = _write_section_title(ws, row, block.title)

    if not block.issues:
        ws.cell(row=row, column=1, value="No issues found.").font = _BODY_FONT
        return

    # 헤더
    headers = ["ID", "Category", "Severity", "Issue", "Description", "Status"]
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col_idx, value=header)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _THIN_BORDER
    row += 1

    # 데이터
    for issue in block.issues:
        if not block.show_resolved and issue.status == "resolved":
            continue

        values = [
            issue.issue_id,
            issue.category,
            issue.severity,
            issue.title,
            issue.description,
            issue.status,
        ]
        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.font = _BODY_FONT
            cell.border = _THIN_BORDER

        # 심각도별 색상
        severity_fill = _SEVERITY_FILLS.get(issue.severity.lower())
        if severity_fill:
            ws.cell(row=row, column=3).fill = severity_fill

        row += 1

    _auto_width(ws)


def _render_checklist_sheet(
    wb: Workbook, checklist_data: list[dict[str, Any]] | None
) -> None:
    """FDD 체크리스트 결과를 시트로 렌더링 (선택적).

    Args:
        wb: 워크북
        checklist_data: 체크리스트 항목 리스트.
            [{"category": "...", "title": "...", "auto_finding": "...",
              "auto_amount": "...", "user_correction": "...", "user_amount": "...",
              "status": "...", "severity": "...", "vdr_sources": "..."}]
    """
    if not checklist_data:
        return

    ws = wb.create_sheet(title="FDD Checklist")
    row = 1
    row = _write_section_title(ws, row, "FDD Checklist Review")

    # 헤더
    headers = [
        "Category",
        "Title",
        "Auto Finding",
        "Auto Amount",
        "User Correction",
        "User Amount",
        "Status",
        "Severity",
        "VDR Sources",
    ]
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col_idx, value=header)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _THIN_BORDER
    row += 1

    # 데이터
    for item in checklist_data:
        values = [
            item.get("category", ""),
            item.get("title", ""),
            item.get("auto_finding", ""),
            item.get("auto_amount", ""),
            item.get("user_correction", ""),
            item.get("user_amount", ""),
            item.get("status", ""),
            item.get("severity", ""),
            item.get("vdr_sources", ""),
        ]
        for col_idx, value in enumerate(values, start=1):
            formatted = _format_cell_value(value, "currency" if col_idx in (4, 6) else None)
            cell = ws.cell(row=row, column=col_idx, value=formatted)
            cell.font = _BODY_FONT
            cell.border = _THIN_BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=True)

            if col_idx in (4, 6) and isinstance(formatted, float):
                cell.number_format = "#,##0"

        # 상태별 색상
        status = item.get("status", "")
        status_fill = _STATUS_FILLS.get(status)
        if status_fill:
            ws.cell(row=row, column=7).fill = status_fill

        row += 1

    _auto_width(ws)


# ═════════════════════════════════════════════════════════════════════════
# Financial Statement Sheet Renderer
# ═════════════════════════════════════════════════════════════════════════


def _render_financial_statement_sheet(
    wb: Workbook, block: TableBlock, sheet_name: str
) -> None:
    """재무제표(IS/BS/CF) 전문 시트 렌더링.

    metadata 기반 소계/합계/들여쓰기 처리.
    metadata keys:
      - style: "financial_statement"
      - subtotal_rows: list[int] — 소계 행 인덱스
      - total_rows: list[int] — 합계 행 인덱스
      - indent_map: dict[str, int] — {row_index_str: indent_level}
      - tab_color: str — 탭 색상 키
    """
    ws = wb.create_sheet(title=sheet_name[:31])
    meta = block.metadata or {}

    _set_tab_color(ws, meta.get("tab_color", "fs"))
    _setup_print(ws)

    row = 1

    # 제목
    if block.title:
        cell = ws.cell(row=row, column=1, value=block.title)
        cell.font = _TITLE_FONT
        row += 1
        # 단위 표시
        unit_cell = ws.cell(row=row, column=1, value="(단위: 백만원)")
        unit_cell.font = _FS_UNIT_FONT
        row += 2

    if not block.columns:
        return

    subtotal_rows = set(meta.get("subtotal_rows", []))
    total_rows = set(meta.get("total_rows", []))
    indent_map: dict[str, int] = meta.get("indent_map", {})

    # 헤더 행
    header_row = row
    if block.show_header:
        for col_idx, col_def in enumerate(block.columns, start=1):
            cell = ws.cell(row=row, column=col_idx, value=col_def.header)
            cell.font = _HEADER_FONT
            cell.fill = _HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = _THIN_BORDER
        row += 1

    # 데이터 행
    data_start_row = row
    for row_idx, row_data in enumerate(block.rows):
        is_subtotal = row_idx in subtotal_rows
        is_total = row_idx in total_rows
        indent_level = indent_map.get(str(row_idx), 0)

        for col_idx, col_def in enumerate(block.columns, start=1):
            raw_value = row_data.get(col_def.key, "")
            value = _format_cell_value(raw_value, col_def.format)

            # 첫 번째 컬럼(계정명)에 들여쓰기 적용
            if col_idx == 1 and isinstance(value, str) and indent_level > 0:
                value = "  " * indent_level + value

            cell = ws.cell(row=row, column=col_idx, value=value)

            # 폰트 결정
            if is_total:
                cell.font = _FS_TOTAL_FONT
                cell.border = _FS_TOTAL_BORDER
            elif is_subtotal:
                cell.font = _FS_SUBTOTAL_FONT
                cell.border = _FS_SUBTOTAL_BORDER
            else:
                cell.font = _BODY_FONT
                cell.border = _THIN_BORDER

            # 숫자 포맷
            if col_def.format == "currency" and isinstance(value, float):
                cell.number_format = "#,##0"
            elif col_def.format == "percentage" and isinstance(value, float):
                cell.number_format = "0.0%"

            # 정렬
            if col_idx == 1:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="right", vertical="center")

        row += 1

    # 푸터 행
    for footer_data in block.footer_rows:
        for col_idx, col_def in enumerate(block.columns, start=1):
            raw_value = footer_data.get(col_def.key, "")
            value = _format_cell_value(raw_value, col_def.format)
            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.font = _FS_TOTAL_FONT
            cell.border = _FS_TOTAL_BORDER
            if col_def.format == "currency" and isinstance(value, float):
                cell.number_format = "#,##0"
            if col_idx == 1:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="right", vertical="center")
        row += 1

    # Freeze pane: 헤더 행 + 첫 컬럼 고정
    if block.show_header:
        ws.freeze_panes = ws.cell(row=header_row + 1, column=2)

    # 증감 컬럼 조건부 서식 (variance 컬럼 감지)
    for col_idx, col_def in enumerate(block.columns, start=1):
        key_lower = col_def.key.lower()
        if any(k in key_lower for k in ("change", "variance", "delta", "diff", "증감")):
            col_letter = get_column_letter(col_idx)
            _apply_variance_formatting(ws, col_letter, data_start_row, row - 1)

    # 컬럼 너비 설정
    if block.columns:
        # 첫 컬럼(계정명) 넓게
        ws.column_dimensions["A"].width = 35
        for col_idx in range(2, len(block.columns) + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 18

    _auto_row_height(ws, col_width_chars=35)


def _render_trend_sheet(
    wb: Workbook, block: TableBlock, sheet_name: str
) -> None:
    """트렌드/월별 분석 시트 렌더링.

    metadata.style == "trend" 또는 "seasonality"
    증감 양수=초록, 음수=빨강 조건부 서식 포함.
    """
    ws = wb.create_sheet(title=sheet_name[:31])
    meta = block.metadata or {}

    _set_tab_color(ws, meta.get("tab_color", "trend"))
    _setup_print(ws)

    row = 1

    if block.title:
        cell = ws.cell(row=row, column=1, value=block.title)
        cell.font = _TITLE_FONT
        row += 1
        unit_cell = ws.cell(row=row, column=1, value="(단위: 백만원)")
        unit_cell.font = _FS_UNIT_FONT
        row += 2

    if not block.columns:
        return

    # 헤더
    header_row = row
    if block.show_header:
        for col_idx, col_def in enumerate(block.columns, start=1):
            cell = ws.cell(row=row, column=col_idx, value=col_def.header)
            cell.font = _HEADER_FONT
            cell.fill = _HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = _THIN_BORDER
        row += 1

    # 데이터
    subtotal_rows = set(meta.get("subtotal_rows", []))
    total_rows = set(meta.get("total_rows", []))
    data_start_row = row
    for row_idx, row_data in enumerate(block.rows):
        is_subtotal = row_idx in subtotal_rows
        is_total = row_idx in total_rows

        for col_idx, col_def in enumerate(block.columns, start=1):
            raw_value = row_data.get(col_def.key, "")
            value = _format_cell_value(raw_value, col_def.format)

            cell = ws.cell(row=row, column=col_idx, value=value)

            if is_total:
                cell.font = _FS_TOTAL_FONT
                cell.border = _FS_TOTAL_BORDER
            elif is_subtotal:
                cell.font = _FS_SUBTOTAL_FONT
                cell.border = _FS_SUBTOTAL_BORDER
            else:
                cell.font = _BODY_FONT
                cell.border = _THIN_BORDER

            if col_def.format == "currency" and isinstance(value, float):
                cell.number_format = "#,##0"
            elif col_def.format == "percentage" and isinstance(value, float):
                cell.number_format = "0.0%"

            if col_idx == 1:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="right", vertical="center")

            # 비율 컬럼이 아닌 증감 컬럼의 셀별 색상
            if col_idx > 1 and col_def.format == "currency" and isinstance(value, float):
                if any(
                    k in col_def.key.lower()
                    for k in ("change", "variance", "delta", "diff", "증감")
                ):
                    if value > 0:
                        cell.font = _POSITIVE_FONT
                    elif value < 0:
                        cell.font = _NEGATIVE_FONT

        row += 1

    # Freeze pane
    if block.show_header:
        ws.freeze_panes = ws.cell(row=header_row + 1, column=2)

    # 컬럼 너비
    if block.columns:
        ws.column_dimensions["A"].width = 30
        for col_idx in range(2, len(block.columns) + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 15

    _auto_row_height(ws, col_width_chars=30)

    # 트렌드 라인 차트 삽입 (데이터 컬럼 2개 이상)
    if len(block.columns) >= 3 and block.rows:
        from app.renderers.excel_charts import render_trend_line_chart

        data_cols = list(range(2, len(block.columns) + 1))
        chart_anchor = f"{get_column_letter(len(block.columns) + 2)}2"
        render_trend_line_chart(
            ws,
            data_cols=data_cols,
            label_col=1,
            start_row=data_start_row,
            end_row=data_start_row + len(block.rows) - 1,
            anchor=chart_anchor,
            title=block.title or "Trend",
        )


def _render_reconciliation_sheet(
    wb: Workbook, block: TableBlock, sheet_name: str
) -> None:
    """Reconciliation/검증 시트 렌더링.

    Pass/Fail 색상으로 검증 결과 표시.
    metadata.style == "reconciliation"
    """
    ws = wb.create_sheet(title=sheet_name[:31])
    meta = block.metadata or {}

    _set_tab_color(ws, meta.get("tab_color", "recon"))
    _setup_print(ws)

    row = 1
    if block.title:
        row = _write_section_title(ws, row, block.title)

    if not block.columns:
        return

    # 헤더
    if block.show_header:
        for col_idx, col_def in enumerate(block.columns, start=1):
            cell = ws.cell(row=row, column=col_idx, value=col_def.header)
            cell.font = _HEADER_FONT
            cell.fill = _HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = _THIN_BORDER
        row += 1

    # 데이터 — result 컬럼에 Pass/Fail 색상 적용
    result_col_idx: int | None = None
    for idx, col_def in enumerate(block.columns, start=1):
        if col_def.key.lower() in ("result", "status", "check"):
            result_col_idx = idx
            break

    for row_data in block.rows:
        for col_idx, col_def in enumerate(block.columns, start=1):
            raw_value = row_data.get(col_def.key, "")
            value = _format_cell_value(raw_value, col_def.format)

            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.font = _BODY_FONT
            cell.border = _THIN_BORDER
            cell.alignment = Alignment(horizontal="center" if col_idx == result_col_idx else "left", vertical="center")

            if col_def.format == "currency" and isinstance(value, float):
                cell.number_format = "#,##0"

            # Pass/Fail 색상
            if col_idx == result_col_idx and isinstance(raw_value, str):
                val_lower = raw_value.lower().strip()
                if val_lower in ("pass", "ok", "✓", "일치"):
                    cell.fill = _PASS_FILL
                elif val_lower in ("fail", "error", "✗", "불일치"):
                    cell.fill = _FAIL_FILL

        row += 1

    _auto_width(ws)
    _auto_row_height(ws)


def _render_index_sheet(wb: Workbook) -> None:
    """Index/ToC 시트 렌더링.

    워크북의 모든 시트를 카테고리별로 그룹핑하고 하이퍼링크를 삽입합니다.
    반드시 모든 시트 생성 이후에 호출해야 합니다.
    """
    ws = wb.create_sheet(title="Index", index=0)
    _set_tab_color(ws, "index")

    row = 2
    cell = ws.cell(row=row, column=2, value="FDD Report — Table of Contents")
    cell.font = _BIG_FONT
    row += 2

    # 시트 이름으로 카테고리 분류
    categories: dict[str, list[str]] = {
        "재무제표 (Financial Statements)": [],
        "QoE 분석 (Quality of Earnings)": [],
        "NWC 분석 (Net Working Capital)": [],
        "Net Debt": [],
        "트렌드 분석 (Trends)": [],
        "매출/원가 분석 (Revenue & Cost)": [],
        "검증 (Reconciliation)": [],
        "이슈 및 체크리스트": [],
        "기타": [],
    }

    for sheet in wb.sheetnames:
        if sheet == "Index":
            continue
        name_lower = sheet.lower()
        if any(k in name_lower for k in ("income statement", "balance sheet", "cash flow", "손익", "재무상태", "현금흐름")):
            categories["재무제표 (Financial Statements)"].append(sheet)
        elif "qoe" in name_lower or "ebitda" in name_lower:
            categories["QoE 분석 (Quality of Earnings)"].append(sheet)
        elif "nwc" in name_lower or "working capital" in name_lower:
            categories["NWC 분석 (Net Working Capital)"].append(sheet)
        elif "debt" in name_lower:
            categories["Net Debt"].append(sheet)
        elif any(k in name_lower for k in ("trend", "monthly", "seasonality", "yoy", "트렌드")):
            categories["트렌드 분석 (Trends)"].append(sheet)
        elif any(k in name_lower for k in ("revenue", "cost", "margin", "매출", "원가")):
            categories["매출/원가 분석 (Revenue & Cost)"].append(sheet)
        elif any(k in name_lower for k in ("reconciliation", "검증", "recon")):
            categories["검증 (Reconciliation)"].append(sheet)
        elif any(k in name_lower for k in ("issue", "checklist", "체크")):
            categories["이슈 및 체크리스트"].append(sheet)
        else:
            categories["기타"].append(sheet)

    seq = 1
    for category, sheets in categories.items():
        if not sheets:
            continue

        cell = ws.cell(row=row, column=2, value=category)
        cell.font = _INDEX_CATEGORY_FONT
        row += 1

        for sheet_name in sheets:
            # 시퀀스 번호
            ws.cell(row=row, column=2, value=seq).font = _BODY_FONT
            # 하이퍼링크
            safe_name = sheet_name.replace("'", "''")
            link_cell = ws.cell(row=row, column=3, value=sheet_name)
            link_cell.hyperlink = f"#'{safe_name}'!A1"
            link_cell.font = _INDEX_LINK_FONT
            seq += 1
            row += 1

        row += 1  # 카테고리 간 빈 행

    ws.column_dimensions["B"].width = 6
    ws.column_dimensions["C"].width = 45


# ═════════════════════════════════════════════════════════════════════════
# Main Renderer
# ═════════════════════════════════════════════════════════════════════════


def _classify_table_block(block: TableBlock) -> tuple[str, str]:
    """TableBlock → (sheet_name, renderer_type) 분류.

    Returns:
        (sheet_name, renderer_type):
          renderer_type = "financial_statement" | "trend" | "reconciliation" | "table"
    """
    meta = block.metadata or {}
    style = meta.get("style", "")
    title = block.title or "Data"

    # metadata.style 기반 분류 (최우선)
    if style == "financial_statement":
        return (title[:31], "financial_statement")
    if style in ("trend", "seasonality", "monthly"):
        return (title[:31], "trend")
    if style == "reconciliation":
        return (title[:31], "reconciliation")

    # 기존 제목 기반 분류 (하위 호환)
    t = title.lower()
    if "qoe" in t and "adjust" in t:
        return ("QoE Adjustments", "table")
    if "qoe" in t or "ebitda" in t:
        return ("QoE Bridge", "table")
    if "nwc" in t and "peg" in t:
        return ("NWC Peg", "table")
    if "nwc" in t or "working capital" in t:
        return ("NWC", "table")
    if "debt" in t:
        return ("Net Debt", "table")
    return (title[:31], "table")


def render_excel_report(
    report_ir: ReportIR,
    output_path: Path | None = None,
    checklist_data: list[dict[str, Any]] | None = None,
) -> BytesIO:
    """Report IR을 Excel 문서로 렌더링합니다.

    Args:
        report_ir: ReportIR 인스턴스
        output_path: 저장할 파일 경로 (None이면 BytesIO 반환만)
        checklist_data: FDD 체크리스트 데이터 (선택적)

    Returns:
        Excel 문서 BytesIO 버퍼
    """
    wb = Workbook()

    # Sheet 1: Cover & Summary
    _render_cover_sheet(wb, report_ir)

    # 블록 분류 및 렌더링
    issue_blocks: list[IssueBlock] = []
    used_names: set[str] = {"Cover & Summary"}

    def _unique_name(name: str) -> str:
        """시트명 중복 방지."""
        base = name[:31]
        if base not in used_names:
            used_names.add(base)
            return base
        for i in range(2, 100):
            candidate = f"{base[:28]}({i})"
            if candidate not in used_names:
                used_names.add(candidate)
                return candidate
        return base

    for block in report_ir.sections:
        if isinstance(block, TableBlock):
            sheet_name, renderer_type = _classify_table_block(block)
            sheet_name = _unique_name(sheet_name)

            if renderer_type == "financial_statement":
                _render_financial_statement_sheet(wb, block, sheet_name)
            elif renderer_type == "trend":
                _render_trend_sheet(wb, block, sheet_name)
            elif renderer_type == "reconciliation":
                _render_reconciliation_sheet(wb, block, sheet_name)
            else:
                _render_table_sheet(wb, block, sheet_name)
                # QoE Bridge → 워터폴 차트
                title_lower = (block.title or "").lower()
                if "qoe" in title_lower and "bridge" in title_lower and block.rows:
                    from app.renderers.excel_charts import render_waterfall_chart

                    ws = wb[sheet_name]
                    render_waterfall_chart(
                        ws,
                        data_col=2,
                        label_col=1,
                        start_row=4,
                        end_row=3 + len(block.rows),
                        anchor=f"{get_column_letter(len(block.columns) + 2)}2",
                        title="QoE EBITDA Bridge",
                    )
                # Revenue Breakdown → 바 차트
                elif "revenue" in title_lower and "breakdown" in title_lower and block.rows:
                    from app.renderers.excel_charts import render_bar_chart

                    ws = wb[sheet_name]
                    render_bar_chart(
                        ws,
                        data_col=2,
                        label_col=1,
                        start_row=4,
                        end_row=3 + len(block.rows),
                        anchor=f"{get_column_letter(len(block.columns) + 2)}2",
                        title="Revenue Breakdown",
                        horizontal=True,
                    )
        elif isinstance(block, IssueBlock):
            issue_blocks.append(block)

    # Issues 시트
    for issue_block in issue_blocks:
        _render_issue_sheet(wb, issue_block)

    # Checklist 시트 (선택적)
    _render_checklist_sheet(wb, checklist_data)

    # Index 시트 — 모든 시트 생성 후 맨 앞에 삽입
    _render_index_sheet(wb)

    # 저장
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    if output_path:
        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())
        buffer.seek(0)

    return buffer
