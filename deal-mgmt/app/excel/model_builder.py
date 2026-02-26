"""Financial Model Excel Builder — 체크리스트 가정값 기반 수식 워크북 생성.

모델 유형별 워크시트를 생성하며, 모든 셀에는 수식을 삽입한다 (값이 아님).
IB 표준 포매팅 적용: 입력=노랑, 수식=흰, 헤더=forest-dark.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from app.excel import formulas as F
from app.excel.styles import (
    NUM_FMT_KRW,
    NUM_FMT_MULTIPLE,
    NUM_FMT_PCT,
    NUM_FMT_PCT_2,
    apply_formula,
    apply_header,
    apply_input,
    apply_label,
    apply_section_title,
    apply_subheader,
    apply_title,
    apply_total,
    create_named_styles,
    set_column_widths,
)
from app.models.enums import FinancialModelType, FMChecklistCategory
from app.services.financial_model_service import FM_FIELD_REGISTRY

# title → category 매핑 (Input 시트 카테고리별 필터링용)
_TITLE_TO_CATEGORY: dict[str, FMChecklistCategory] = {field["title"]: field["category"] for field in FM_FIELD_REGISTRY}
_TITLE_TO_UNIT: dict[str, str | None] = {field["title"]: field.get("unit") for field in FM_FIELD_REGISTRY}

logger = logging.getLogger(__name__)

# 프로젝션 기간 (기본 5년)
PROJECTION_YEARS = 5
BASE_YEAR = datetime.now().year - 1  # 직전 실적 연도 (자동 계산)
FORECAST_START = BASE_YEAR + 1

# ── 카테고리 → 체크리스트 값 추출 ─────────────────────────────────────────


def _get_val(checklist_values: dict[str, str], title: str, default: str = "") -> str:
    """체크리스트에서 confirmed/user 값을 가져온다."""
    return checklist_values.get(title, default)


def _get_num(checklist_values: dict[str, str], title: str, default: float = 0.0) -> float:
    """체크리스트 값을 float으로 변환."""
    val = _get_val(checklist_values, title, str(default))
    try:
        return float(val.replace(",", "").replace("%", "").replace("x", ""))
    except (ValueError, AttributeError):
        return default


# ── 시트 구성 정의 ────────────────────────────────────────────────────────

SHEET_CONFIG: dict[FinancialModelType, list[str]] = {
    FinancialModelType.DCF: [
        "Legend",
        "Input",
        "IS",
        "BS",
        "CF",
        "WACC",
        "DCF",
        "Sensitivity",
        "Summary",
    ],
    FinancialModelType.LBO: [
        "Legend",
        "Input",
        "Sources & Uses",
        "IS",
        "BS",
        "CF",
        "Debt Schedule",
        "Returns",
        "Sensitivity",
        "Summary",
    ],
    FinancialModelType.COMPS: [
        "Legend",
        "GPCM",
        "GTM",
        "Football Field",
        "Summary",
    ],
    FinancialModelType.TRANSACTION_COMPS: [
        "Legend",
        "GTM",
        "Summary",
    ],
    FinancialModelType.PROJECTION: [
        "Legend",
        "Input",
        "IS",
        "BS",
        "CF",
        "Revenue Build-Up",
        "Cost Structure",
        "Summary",
    ],
    FinancialModelType.FULL: [
        "Legend",
        "Input",
        "IS",
        "BS",
        "CF",
        "WACC",
        "DCF",
        "GPCM",
        "GTM",
        "Sensitivity",
        "Football Field",
        "Summary",
    ],
}


# ── 메인 빌더 클래스 ─────────────────────────────────────────────────────


class FinancialModelBuilder:
    """체크리스트 가정값을 반영하여 Excel 워크북을 생성한다."""

    def __init__(
        self,
        model_type: FinancialModelType,
        title: str,
        checklist_values: dict[str, str] | None = None,
        parameters: dict | None = None,
    ):
        self.model_type = model_type
        self.title = title
        self.values = checklist_values or {}
        self.params = parameters or {}
        self.wb = Workbook()
        # 기본 시트 제거
        self.wb.remove(self.wb.active)
        create_named_styles(self.wb)

    def build(self) -> Workbook:
        """모델 유형에 맞는 워크시트를 생성하여 워크북을 반환한다."""
        sheets = SHEET_CONFIG.get(self.model_type, SHEET_CONFIG[FinancialModelType.DCF])

        for sheet_name in sheets:
            builder_fn = _SHEET_BUILDERS.get(sheet_name)
            if builder_fn:
                ws = self.wb.create_sheet(title=sheet_name)
                builder_fn(self, ws)
            else:
                logger.warning("No builder for sheet '%s'", sheet_name)
                ws = self.wb.create_sheet(title=sheet_name)
                apply_title(ws["B2"], sheet_name)

        return self.wb

    def save(self, file_path: str | Path) -> Path:
        """워크북을 빌드하고 파일로 저장한다."""
        self.build()
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.wb.save(str(path))
        logger.info("Financial model saved: %s (%d sheets)", path.name, len(self.wb.sheetnames))
        return path

    # ── Legend 시트 ────────────────────────────────────────────

    def _build_legend(self, ws):
        """프로젝트 메타 정보 + 범례."""
        set_column_widths(ws, {"A": 5, "B": 25, "C": 40, "D": 25})
        ws.sheet_properties.tabColor = "1B4332"

        apply_title(ws["B2"], self.title)
        ws["B4"] = "Model Type"
        ws["C4"] = self.model_type.value
        ws["B5"] = "Version"
        ws["C5"] = 1
        ws["B6"] = "Currency"
        ws["C6"] = self.params.get("currency", "KRW")

        apply_section_title(ws["B8"], "범례 (Legend)")
        apply_input(ws["C10"], "입력값 (사용자 가정)")
        apply_formula(ws["C11"], "수식 (자동 계산)")
        apply_subheader(ws["C12"], "섹션 헤더")

        ws["B10"] = "노랑 배경"
        ws["B11"] = "흰 배경"
        ws["B12"] = "초록 배경"

    # ── Input 시트 ────────────────────────────────────────────

    def _build_input(self, ws):
        """체크리스트 가정값 입력 시트."""
        set_column_widths(ws, {"A": 3, "B": 35, "C": 18, "D": 12, "E": 15})
        ws.sheet_properties.tabColor = "FFD966"

        apply_title(ws["B2"], "Assumptions & Input")

        row = 4
        # 카테고리별 입력값 배치
        categories = [
            (
                "Revenue & Growth",
                [
                    FMChecklistCategory.REVENUE_FORECAST,
                    FMChecklistCategory.GROWTH_ASSUMPTIONS,
                    FMChecklistCategory.VOLUME_PRICE_MIX,
                ],
            ),
            (
                "Cost Structure",
                [
                    FMChecklistCategory.COGS_FORECAST,
                    FMChecklistCategory.SGA_FORECAST,
                    FMChecklistCategory.DEPRECIATION_AMORT,
                    FMChecklistCategory.CAPEX_FORECAST,
                ],
            ),
            (
                "Working Capital",
                [
                    FMChecklistCategory.NWC_ASSUMPTIONS,
                    FMChecklistCategory.FCF_DERIVATION,
                ],
            ),
            (
                "Capital Structure & WACC",
                [
                    FMChecklistCategory.FM_DEBT_SCHEDULE,
                    FMChecklistCategory.WACC_COMPONENTS,
                    FMChecklistCategory.TAX_RATE,
                ],
            ),
            (
                "Valuation",
                [
                    FMChecklistCategory.DCF_PARAMETERS,
                    FMChecklistCategory.TRADING_MULTIPLES,
                    FMChecklistCategory.TRANSACTION_MULTIPLES,
                ],
            ),
            (
                "Scenarios",
                [
                    FMChecklistCategory.BASE_SCENARIO,
                    FMChecklistCategory.UPSIDE_SCENARIO,
                    FMChecklistCategory.DOWNSIDE_SCENARIO,
                    FMChecklistCategory.SENSITIVITY_MATRIX,
                ],
            ),
        ]

        for group_name, cats in categories:
            apply_section_title(ws.cell(row=row, column=2), group_name)
            row += 1
            apply_header(ws.cell(row=row, column=2), "항목")
            apply_header(ws.cell(row=row, column=3), "값")
            apply_header(ws.cell(row=row, column=4), "단위")
            row += 1

            for cat in cats:
                cat_items = [(title, val) for title, val in self.values.items() if _TITLE_TO_CATEGORY.get(title) == cat]
                if not cat_items:
                    # 값이 없어도 레지스트리에서 빈 행 생성 (입력 슬롯)
                    cat_items = [(f["title"], "") for f in FM_FIELD_REGISTRY if f["category"] == cat]
                # 카테고리 이름 표시
                apply_subheader(ws.cell(row=row, column=2), cat.value.replace("_", " ").title())
                row += 1
                for title, val in cat_items:
                    apply_label(ws.cell(row=row, column=2), title)
                    cell = ws.cell(row=row, column=3)
                    apply_input(cell, val or "", None)
                    unit = _TITLE_TO_UNIT.get(title)
                    if unit:
                        ws.cell(row=row, column=4).value = unit
                    row += 1

            row += 1  # 그룹 간 간격

    # ── IS (Income Statement) 시트 ─────────────────────────────

    def _build_is(self, ws):
        """손익계산서 — 5년 프로젝션 수식 기반."""
        years = list(range(FORECAST_START, FORECAST_START + PROJECTION_YEARS))
        set_column_widths(ws, {"A": 3, "B": 30, **{get_column_letter(i + 3): 16 for i in range(len(years))}})
        ws.sheet_properties.tabColor = "2D6A4F"

        apply_title(ws["B2"], "Income Statement (Projected)")

        # 헤더 행
        row = 4
        apply_header(ws.cell(row=row, column=2), "(KRW mn)")
        for i, yr in enumerate(years):
            apply_header(ws.cell(row=row, column=i + 3), f"FY{yr}")

        # IS 항목 (행 번호 기반 수식)
        items = [
            ("Revenue", "input", NUM_FMT_KRW),
            ("  Growth Rate", "formula", NUM_FMT_PCT),
            ("COGS", "input", NUM_FMT_KRW),
            ("Gross Profit", "formula", NUM_FMT_KRW),
            ("  Gross Margin", "formula", NUM_FMT_PCT),
            ("SG&A", "input", NUM_FMT_KRW),
            ("Operating Profit (EBIT)", "formula", NUM_FMT_KRW),
            ("  Operating Margin", "formula", NUM_FMT_PCT),
            ("D&A", "input", NUM_FMT_KRW),
            ("EBITDA", "formula", NUM_FMT_KRW),
            ("  EBITDA Margin", "formula", NUM_FMT_PCT),
            ("Interest Expense", "input", NUM_FMT_KRW),
            ("Other Income/(Expense)", "input", NUM_FMT_KRW),
            ("EBT (Earnings Before Tax)", "formula", NUM_FMT_KRW),
            ("Income Tax", "formula", NUM_FMT_KRW),
            ("Net Income", "formula", NUM_FMT_KRW),
            ("  Net Margin", "formula", NUM_FMT_PCT),
        ]

        start_row = row + 1
        for idx, (label, cell_type, fmt) in enumerate(items):
            r = start_row + idx
            indent = 1 if label.startswith("  ") else 0
            apply_label(ws.cell(row=r, column=2), label.strip(), indent=indent)

            for ci in range(len(years)):
                c = ci + 3
                cell = ws.cell(row=r, column=c)

                if cell_type == "input":
                    apply_input(cell, 0, fmt)
                elif cell_type == "formula":
                    # 수식 연결
                    rev_row = start_row  # Revenue
                    cogs_row = start_row + 2
                    gp_row = start_row + 3
                    sga_row = start_row + 5
                    ebit_row = start_row + 6
                    da_row = start_row + 8
                    ebitda_row = start_row + 9
                    interest_row = start_row + 11
                    other_row = start_row + 12
                    ebt_row = start_row + 13
                    tax_row = start_row + 14
                    ni_row = start_row + 15

                    cl = get_column_letter(c)

                    if label == "  Growth Rate":
                        if ci == 0:
                            apply_input(cell, 0, fmt)
                        else:
                            prev_c = get_column_letter(c - 1)
                            apply_formula(cell, F.growth_rate(f"{cl}{rev_row}", f"{prev_c}{rev_row}"), fmt)
                    elif label == "Gross Profit":
                        apply_formula(cell, F.gross_profit(f"{cl}{rev_row}", f"{cl}{cogs_row}"), fmt)
                    elif label == "  Gross Margin":
                        apply_formula(cell, F.margin(f"{cl}{gp_row}", f"{cl}{rev_row}"), fmt)
                    elif label == "Operating Profit (EBIT)":
                        apply_formula(cell, F.operating_profit(f"{cl}{gp_row}", f"{cl}{sga_row}"), fmt)
                    elif label == "  Operating Margin":
                        apply_formula(cell, F.margin(f"{cl}{ebit_row}", f"{cl}{rev_row}"), fmt)
                    elif label == "EBITDA":
                        apply_formula(cell, F.ebitda(f"{cl}{ebit_row}", f"{cl}{da_row}"), fmt)
                    elif label == "  EBITDA Margin":
                        apply_formula(cell, F.margin(f"{cl}{ebitda_row}", f"{cl}{rev_row}"), fmt)
                    elif label == "EBT (Earnings Before Tax)":
                        apply_formula(cell, f"={cl}{ebit_row}-{cl}{interest_row}+{cl}{other_row}", fmt)
                    elif label == "Income Tax":
                        tax_rate = _get_num(self.values, "유효법인세율 가정", 0.22)
                        apply_formula(cell, f"=MAX({cl}{ebt_row},0)*{tax_rate}", fmt)
                    elif label == "Net Income":
                        apply_formula(cell, F.net_income(f"{cl}{ebt_row}", f"{cl}{tax_row}"), fmt)
                    elif label == "  Net Margin":
                        apply_formula(cell, F.margin(f"{cl}{ni_row}", f"{cl}{rev_row}"), fmt)

        # 합계 행 (EBITDA, Net Income에 bold 적용)
        for total_row in [start_row + 9, start_row + 15]:  # EBITDA, Net Income
            for ci in range(len(years)):
                cell = ws.cell(row=total_row, column=ci + 3)
                apply_total(cell, cell.value, NUM_FMT_KRW)

    # ── BS (Balance Sheet) 시트 ────────────────────────────────

    def _build_bs(self, ws):
        """재무상태표 — 자산 = 부채 + 자본 균형 확인."""
        years = list(range(FORECAST_START, FORECAST_START + PROJECTION_YEARS))
        set_column_widths(ws, {"A": 3, "B": 30, **{get_column_letter(i + 3): 16 for i in range(len(years))}})
        ws.sheet_properties.tabColor = "2D6A4F"

        apply_title(ws["B2"], "Balance Sheet (Projected)")

        row = 4
        apply_header(ws.cell(row=row, column=2), "(KRW mn)")
        for i, yr in enumerate(years):
            apply_header(ws.cell(row=row, column=i + 3), f"FY{yr}")

        # 자산
        items_assets = [
            "Cash & Equivalents",
            "Accounts Receivable",
            "Inventory",
            "Other Current Assets",
            "Total Current Assets",
            "PP&E (net)",
            "Intangible Assets",
            "Other Non-Current Assets",
            "Total Non-Current Assets",
            "Total Assets",
        ]
        items_liab_eq = [
            "Accounts Payable",
            "Short-term Debt",
            "Other Current Liabilities",
            "Total Current Liabilities",
            "Long-term Debt",
            "Other Non-Current Liabilities",
            "Total Non-Current Liabilities",
            "Total Liabilities",
            "Common Equity",
            "Retained Earnings",
            "Total Equity",
            "Total Liabilities & Equity",
        ]

        r = row + 1
        apply_section_title(ws.cell(row=r, column=2), "Assets")
        r += 1
        asset_start = r
        for label in items_assets:
            is_total = label.startswith("Total")
            indent = 0 if is_total else 1
            apply_label(ws.cell(row=r, column=2), label, indent=indent)
            for ci in range(len(years)):
                cell = ws.cell(row=r, column=ci + 3)
                c = get_column_letter(ci + 3)
                if label == "Total Current Assets":
                    apply_formula(cell, F.sum_range(ci + 3, asset_start, r - 1), NUM_FMT_KRW)
                elif label == "Total Non-Current Assets":
                    apply_formula(cell, F.sum_range(ci + 3, asset_start + 5, r - 1), NUM_FMT_KRW)
                elif label == "Total Assets":
                    tca_row = asset_start + 4
                    tnca_row = r - 1
                    apply_total(cell, f"={c}{tca_row}+{c}{tnca_row}", NUM_FMT_KRW)
                else:
                    apply_input(cell, 0, NUM_FMT_KRW)
            r += 1

        r += 1
        apply_section_title(ws.cell(row=r, column=2), "Liabilities & Equity")
        r += 1
        liab_start = r
        for label in items_liab_eq:
            is_total = label.startswith("Total")
            indent = 0 if is_total else 1
            apply_label(ws.cell(row=r, column=2), label, indent=indent)
            for ci in range(len(years)):
                cell = ws.cell(row=r, column=ci + 3)
                c = get_column_letter(ci + 3)
                if label == "Total Current Liabilities":
                    apply_formula(cell, F.sum_range(ci + 3, liab_start, r - 1), NUM_FMT_KRW)
                elif label == "Total Non-Current Liabilities":
                    apply_formula(cell, F.sum_range(ci + 3, liab_start + 4, r - 1), NUM_FMT_KRW)
                elif label == "Total Liabilities":
                    tcl_row = liab_start + 3
                    tncl_row = r - 1
                    apply_total(cell, f"={c}{tcl_row}+{c}{tncl_row}", NUM_FMT_KRW)
                elif label == "Total Equity":
                    apply_formula(cell, F.sum_range(ci + 3, r - 2, r - 1), NUM_FMT_KRW)
                elif label == "Total Liabilities & Equity":
                    tl_row = liab_start + 7
                    te_row = r - 1
                    apply_total(cell, f"={c}{tl_row}+{c}{te_row}", NUM_FMT_KRW)
                else:
                    apply_input(cell, 0, NUM_FMT_KRW)
            r += 1

        # Balance Check 행
        r += 1
        apply_label(ws.cell(row=r, column=2), "Balance Check (Assets - L&E)")
        ta_row = asset_start + len(items_assets) - 1
        tle_row = liab_start + len(items_liab_eq) - 1
        for ci in range(len(years)):
            c = get_column_letter(ci + 3)
            cell = ws.cell(row=r, column=ci + 3)
            apply_formula(cell, f"={c}{ta_row}-{c}{tle_row}", NUM_FMT_KRW)

    # ── CF (Cash Flow) 시트 ───────────────────────────────────

    def _build_cf(self, ws):
        """현금흐름표 — IS/BS 연결."""
        years = list(range(FORECAST_START, FORECAST_START + PROJECTION_YEARS))
        set_column_widths(ws, {"A": 3, "B": 35, **{get_column_letter(i + 3): 16 for i in range(len(years))}})
        ws.sheet_properties.tabColor = "2D6A4F"

        apply_title(ws["B2"], "Cash Flow Statement (Projected)")

        row = 4
        apply_header(ws.cell(row=row, column=2), "(KRW mn)")
        for i, yr in enumerate(years):
            apply_header(ws.cell(row=row, column=i + 3), f"FY{yr}")

        items = [
            ("Operating Activities", "section"),
            ("Net Income", "input"),
            ("D&A", "input"),
            ("Changes in Working Capital", "input"),
            ("Cash from Operations", "formula"),
            ("", "blank"),
            ("Investing Activities", "section"),
            ("CAPEX", "input"),
            ("Other Investing", "input"),
            ("Cash from Investing", "formula"),
            ("", "blank"),
            ("Financing Activities", "section"),
            ("Debt Issuance/(Repayment)", "input"),
            ("Equity Issuance/(Repurchase)", "input"),
            ("Dividends", "input"),
            ("Cash from Financing", "formula"),
            ("", "blank"),
            ("Net Change in Cash", "formula"),
            ("Beginning Cash", "input"),
            ("Ending Cash", "formula"),
            ("", "blank"),
            ("Free Cash Flow (FCFF)", "formula"),
        ]

        r = row + 1
        cfo_items_start = r + 1  # Net Income row
        for label, cell_type in items:
            if cell_type == "blank":
                r += 1
                continue
            if cell_type == "section":
                apply_section_title(ws.cell(row=r, column=2), label)
                r += 1
                continue

            apply_label(ws.cell(row=r, column=2), label)
            for ci in range(len(years)):
                c = get_column_letter(ci + 3)
                cell = ws.cell(row=r, column=ci + 3)
                if cell_type == "input":
                    apply_input(cell, 0, NUM_FMT_KRW)
                elif cell_type == "formula":
                    if label == "Cash from Operations":
                        apply_formula(cell, F.sum_range(ci + 3, cfo_items_start, r - 1), NUM_FMT_KRW)
                    elif label == "Cash from Investing":
                        # 이전 2개 항목 합
                        apply_formula(cell, F.sum_range(ci + 3, r - 2, r - 1), NUM_FMT_KRW)
                    elif label == "Cash from Financing":
                        apply_formula(cell, F.sum_range(ci + 3, r - 3, r - 1), NUM_FMT_KRW)
                    elif label == "Net Change in Cash":
                        # CFO + CFI + CFF
                        apply_total(cell, f"={c}{cfo_items_start + 3}+{c}{r - 7}+{c}{r - 2}", NUM_FMT_KRW)
                    elif label == "Ending Cash":
                        apply_formula(cell, f"={c}{r - 2}+{c}{r - 1}", NUM_FMT_KRW)
                    elif label == "Free Cash Flow (FCFF)":
                        # EBITDA(IS) - Tax - CAPEX - ΔNWC (간이)
                        cfo_row = cfo_items_start + 3
                        capex_row = cfo_items_start + 5  # CAPEX
                        apply_total(cell, f"={c}{cfo_row}-{c}{capex_row}", NUM_FMT_KRW)
            r += 1

    # ── WACC 시트 ─────────────────────────────────────────────

    def _build_wacc(self, ws):
        """WACC 계산 시트."""
        set_column_widths(ws, {"A": 3, "B": 35, "C": 18, "D": 15})
        ws.sheet_properties.tabColor = "40916C"

        apply_title(ws["B2"], "Weighted Average Cost of Capital (WACC)")

        row = 4
        apply_section_title(ws.cell(row=row, column=2), "Cost of Equity (Ke)")
        row += 1

        ke_items = [
            ("Risk-Free Rate (Rf)", "input", NUM_FMT_PCT_2, "무위험이자율 (Rf)", 0.035),
            ("Equity Risk Premium (MRP)", "input", NUM_FMT_PCT_2, "시장리스크프리미엄 (MRP)", 0.06),
            ("Levered Beta (βL)", "input", NUM_FMT_MULTIPLE, "Beta (Unlevered / Levered)", 1.0),
            ("Size Premium", "input", NUM_FMT_PCT_2, None, 0.0),
            ("Cost of Equity (Ke)", "formula", NUM_FMT_PCT_2, None, None),
        ]

        rf_row = row
        for label, cell_type, fmt, cl_title, default in ke_items:
            apply_label(ws.cell(row=row, column=2), label)
            cell = ws.cell(row=row, column=3)
            if cell_type == "input":
                val = _get_num(self.values, cl_title, default) if cl_title else default
                apply_input(cell, val, fmt)
            elif label == "Cost of Equity (Ke)":
                apply_formula(cell, F.capm(f"C{rf_row}", f"C{rf_row + 2}", f"C{rf_row + 1}", f"C{rf_row + 3}"), fmt)
            row += 1

        ke_row = row - 1
        row += 1

        apply_section_title(ws.cell(row=row, column=2), "Cost of Debt (Kd)")
        row += 1
        kd_items = [
            ("Pre-tax Cost of Debt", "input", NUM_FMT_PCT_2, "세전 타인자본비용 (Kd pre-tax)", 0.04),
            ("Effective Tax Rate", "input", NUM_FMT_PCT_2, "유효법인세율 가정", 0.22),
            ("After-tax Cost of Debt (Kd)", "formula", NUM_FMT_PCT_2, None, None),
        ]

        kd_start = row
        for label, cell_type, fmt, cl_title, default in kd_items:
            apply_label(ws.cell(row=row, column=2), label)
            cell = ws.cell(row=row, column=3)
            if cell_type == "input":
                val = _get_num(self.values, cl_title, default) if cl_title else default
                apply_input(cell, val, fmt)
            elif label == "After-tax Cost of Debt (Kd)":
                apply_formula(cell, f"=C{kd_start}*(1-C{kd_start + 1})", fmt)
            row += 1

        kd_row = row - 1
        row += 1

        apply_section_title(ws.cell(row=row, column=2), "Capital Structure")
        row += 1
        cap_items = [
            ("Equity Weight (We)", "input", NUM_FMT_PCT, "목표 자본구조 (D/E)", 0.7),
            ("Debt Weight (Wd)", "formula", NUM_FMT_PCT, None, None),
        ]

        we_row = row
        for label, cell_type, fmt, cl_title, default in cap_items:
            apply_label(ws.cell(row=row, column=2), label)
            cell = ws.cell(row=row, column=3)
            if cell_type == "input":
                apply_input(cell, default, fmt)
            elif label == "Debt Weight (Wd)":
                apply_formula(cell, f"=1-C{we_row}", fmt)
            row += 1

        wd_row = row - 1
        row += 1

        apply_section_title(ws.cell(row=row, column=2), "WACC")
        row += 1
        apply_label(ws.cell(row=row, column=2), "WACC")
        apply_total(
            ws.cell(row=row, column=3), F.wacc(f"C{ke_row}", f"C{kd_row}", f"C{we_row}", f"C{wd_row}"), NUM_FMT_PCT_2
        )

    # ── DCF 시트 ──────────────────────────────────────────────

    def _build_dcf(self, ws):
        """DCF 밸류에이션 시트."""
        years = list(range(FORECAST_START, FORECAST_START + PROJECTION_YEARS))
        set_column_widths(ws, {"A": 3, "B": 30, **{get_column_letter(i + 3): 16 for i in range(len(years) + 1)}})
        ws.sheet_properties.tabColor = "40916C"

        apply_title(ws["B2"], "Discounted Cash Flow Analysis")

        row = 4
        apply_header(ws.cell(row=row, column=2), "")
        for i, yr in enumerate(years):
            apply_header(ws.cell(row=row, column=i + 3), f"FY{yr}")
        apply_header(ws.cell(row=row, column=len(years) + 3), "Terminal")

        items = [
            "FCFF",
            "Terminal Value",
            "Discount Factor",
            "PV of FCFF",
            "PV of Terminal Value",
        ]

        r = row + 1
        for label in items:
            apply_label(ws.cell(row=r, column=2), label)
            for ci in range(len(years)):
                c = ci + 3
                cl = get_column_letter(c)
                cell = ws.cell(row=r, column=c)
                if label == "FCFF":
                    apply_input(cell, 0, NUM_FMT_KRW)
                elif label == "Terminal Value":
                    if ci == len(years) - 1:
                        # Terminal Value on last year
                        apply_formula(cell, 0, NUM_FMT_KRW)  # placeholder, linked to WACC sheet
                elif label == "Discount Factor":
                    apply_formula(cell, F.discount_factor("WACC!C$" + str(row + 10), ci + 1), "0.0000")
                elif label == "PV of FCFF":
                    apply_formula(cell, F.pv(f"{cl}{r - 2}", f"{cl}{r - 1}"), NUM_FMT_KRW)
                elif label == "PV of Terminal Value":
                    if ci == len(years) - 1:
                        tv_row = r - 3
                        df_row = r - 1
                        apply_formula(cell, F.pv(f"{cl}{tv_row}", f"{cl}{df_row}"), NUM_FMT_KRW)
            r += 1

        # Summary section
        r += 1
        apply_section_title(ws.cell(row=r, column=2), "Valuation Summary")
        r += 1
        summary_items = [
            ("Sum of PV of FCFF", "formula"),
            ("PV of Terminal Value", "formula"),
            ("Enterprise Value (DCF)", "formula"),
            ("(-) Net Debt", "input"),
            ("Equity Value", "formula"),
        ]
        summary_start = r
        for label, cell_type in summary_items:
            apply_label(ws.cell(row=r, column=2), label)
            cell = ws.cell(row=r, column=3)
            if cell_type == "input":
                apply_input(cell, 0, NUM_FMT_KRW)
            elif label == "Sum of PV of FCFF":
                # Sum PV of FCFF row across years
                pv_row = row + 4 + 3  # PV of FCFF row
                apply_formula(cell, F.sum_range(3, pv_row, pv_row), NUM_FMT_KRW)
            elif label == "PV of Terminal Value":
                apply_formula(cell, f"=C{summary_start - 1}", NUM_FMT_KRW)  # reference from above
            elif label == "Enterprise Value (DCF)":
                apply_total(cell, f"=C{summary_start}+C{summary_start + 1}", NUM_FMT_KRW)
            elif label == "Equity Value":
                apply_total(cell, F.equity_value(f"C{summary_start + 2}", f"C{summary_start + 3}"), NUM_FMT_KRW)
            r += 1

    # ── GPCM 시트 ─────────────────────────────────────────────

    def _build_gpcm(self, ws):
        """Guideline Public Company Method (비교기업 분석)."""
        set_column_widths(
            ws,
            {
                "A": 3,
                "B": 25,
                "C": 15,
                "D": 15,
                "E": 15,
                "F": 15,
                "G": 15,
                "H": 15,
            },
        )
        ws.sheet_properties.tabColor = "95D5B2"

        apply_title(ws["B2"], "Guideline Public Company Method (GPCM)")

        row = 4
        headers = ["Company", "Market Cap", "EV", "Revenue", "EBITDA", "EV/Revenue", "EV/EBITDA"]
        for i, h in enumerate(headers):
            apply_header(ws.cell(row=row, column=i + 2), h)

        # 5개 비교기업 입력 슬롯
        for comp_idx in range(1, 6):
            r = row + comp_idx
            apply_input(ws.cell(row=r, column=2), f"비교기업 {comp_idx}")
            for ci in range(3, 7):
                apply_input(ws.cell(row=r, column=ci), 0, NUM_FMT_KRW)
            # EV/Revenue
            cl_ev = get_column_letter(4)
            cl_rev = get_column_letter(5)
            apply_formula(ws.cell(row=r, column=7), F.ev_ebitda(f"{cl_ev}{r}", f"{cl_rev}{r}"), NUM_FMT_MULTIPLE)
            # EV/EBITDA
            cl_ebitda = get_column_letter(6)
            apply_formula(ws.cell(row=r, column=8), F.ev_ebitda(f"{cl_ev}{r}", f"{cl_ebitda}{r}"), NUM_FMT_MULTIPLE)

        # 통계
        stat_row = row + 6
        for label, func in [("Median", "MEDIAN"), ("Average", "AVERAGE"), ("High", "MAX"), ("Low", "MIN")]:
            apply_subheader(ws.cell(row=stat_row, column=2), label)
            for ci in [7, 8]:  # EV/Revenue, EV/EBITDA
                cl = get_column_letter(ci)
                apply_formula(
                    ws.cell(row=stat_row, column=ci),
                    f"={func}({cl}{row + 1}:{cl}{row + 5})",
                    NUM_FMT_MULTIPLE,
                )
            stat_row += 1

        # Implied EV 섹션
        stat_row += 1
        apply_section_title(ws.cell(row=stat_row, column=2), "Implied Enterprise Value")
        stat_row += 1
        apply_label(ws.cell(row=stat_row, column=2), "Target EBITDA")
        apply_input(ws.cell(row=stat_row, column=3), 0, NUM_FMT_KRW)

        stat_row += 1
        apply_label(ws.cell(row=stat_row, column=2), "Median Multiple")
        apply_formula(ws.cell(row=stat_row, column=3), f"=H{row + 6}", NUM_FMT_MULTIPLE)

        stat_row += 1
        apply_label(ws.cell(row=stat_row, column=2), "Implied EV (GPCM)")
        apply_total(ws.cell(row=stat_row, column=3), f"=C{stat_row - 2}*C{stat_row - 1}", NUM_FMT_KRW)

    # ── GTM 시트 ──────────────────────────────────────────────

    def _build_gtm(self, ws):
        """Guideline Transaction Method (선례거래 분석)."""
        set_column_widths(
            ws,
            {
                "A": 3,
                "B": 25,
                "C": 12,
                "D": 15,
                "E": 15,
                "F": 15,
                "G": 15,
                "H": 15,
            },
        )
        ws.sheet_properties.tabColor = "95D5B2"

        apply_title(ws["B2"], "Guideline Transaction Method (GTM)")

        row = 4
        headers = ["Transaction", "Year", "Deal Value", "Revenue", "EBITDA", "DV/Revenue", "DV/EBITDA"]
        for i, h in enumerate(headers):
            apply_header(ws.cell(row=row, column=i + 2), h)

        for txn_idx in range(1, 6):
            r = row + txn_idx
            apply_input(ws.cell(row=r, column=2), f"선례거래 {txn_idx}")
            apply_input(ws.cell(row=r, column=3), 2024, "0")
            for ci in range(4, 7):
                apply_input(ws.cell(row=r, column=ci), 0, NUM_FMT_KRW)
            cl_dv = get_column_letter(4)
            cl_rev = get_column_letter(5)
            cl_ebitda = get_column_letter(6)
            apply_formula(ws.cell(row=r, column=7), F.ev_ebitda(f"{cl_dv}{r}", f"{cl_rev}{r}"), NUM_FMT_MULTIPLE)
            apply_formula(ws.cell(row=r, column=8), F.ev_ebitda(f"{cl_dv}{r}", f"{cl_ebitda}{r}"), NUM_FMT_MULTIPLE)

        stat_row = row + 6
        for label, func in [("Median", "MEDIAN"), ("Average", "AVERAGE")]:
            apply_subheader(ws.cell(row=stat_row, column=2), label)
            for ci in [7, 8]:
                cl = get_column_letter(ci)
                apply_formula(
                    ws.cell(row=stat_row, column=ci),
                    f"={func}({cl}{row + 1}:{cl}{row + 5})",
                    NUM_FMT_MULTIPLE,
                )
            stat_row += 1

    # ── Sensitivity 시트 ──────────────────────────────────────

    def _build_sensitivity(self, ws):
        """2-way 민감도 분석 (WACC × Exit Multiple)."""
        set_column_widths(ws, {"A": 3, "B": 18, **{get_column_letter(i + 3): 16 for i in range(7)}})
        ws.sheet_properties.tabColor = "D8F3DC"

        apply_title(ws["B2"], "Sensitivity Analysis")

        # WACC × Terminal Growth Rate
        row = 4
        apply_section_title(ws.cell(row=row, column=2), "WACC vs Terminal Growth Rate")
        row += 1

        wacc_values = [0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.14]
        growth_values = [0.01, 0.015, 0.02, 0.025, 0.03]

        apply_label(ws.cell(row=row, column=2), "WACC \\ TGR")
        for i, g in enumerate(growth_values):
            apply_header(ws.cell(row=row, column=i + 3), f"{g:.1%}")

        for j, w in enumerate(wacc_values):
            r = row + 1 + j
            apply_subheader(ws.cell(row=r, column=2), f"{w:.1%}")
            for i, g in enumerate(growth_values):
                cell = ws.cell(row=r, column=i + 3)
                # 간이 공식: EV = FCFF / (WACC - g)
                apply_formula(cell, f"=IF({w}-{g}<=0,0,1/({w}-{g}))", "0.0x")

        # WACC × Exit Multiple
        row = row + len(wacc_values) + 3
        apply_section_title(ws.cell(row=row, column=2), "WACC vs Exit Multiple (EV/EBITDA)")
        row += 1

        multiples = [6.0, 7.0, 8.0, 9.0, 10.0]
        apply_label(ws.cell(row=row, column=2), "WACC \\ Multiple")
        for i, m in enumerate(multiples):
            apply_header(ws.cell(row=row, column=i + 3), f"{m:.1f}x")

        for j, w in enumerate(wacc_values):
            r = row + 1 + j
            apply_subheader(ws.cell(row=r, column=2), f"{w:.1%}")
            for i, m in enumerate(multiples):
                apply_input(ws.cell(row=r, column=i + 3), 0, NUM_FMT_KRW)

    # ── Summary 시트 ──────────────────────────────────────────

    def _build_summary(self, ws):
        """밸류에이션 요약 시트."""
        set_column_widths(ws, {"A": 3, "B": 30, "C": 20, "D": 20, "E": 20})
        ws.sheet_properties.tabColor = "1B4332"

        apply_title(ws["B2"], "Valuation Summary")

        row = 4
        apply_header(ws.cell(row=row, column=2), "Methodology")
        apply_header(ws.cell(row=row, column=3), "Implied EV")
        apply_header(ws.cell(row=row, column=4), "Implied Equity")
        apply_header(ws.cell(row=row, column=5), "Weight")

        methods = [
            "DCF (Gordon Growth)",
            "DCF (Exit Multiple)",
            "GPCM (EV/EBITDA)",
            "GTM (EV/EBITDA)",
        ]

        for i, method in enumerate(methods):
            r = row + 1 + i
            apply_label(ws.cell(row=r, column=2), method)
            apply_input(ws.cell(row=r, column=3), 0, NUM_FMT_KRW)
            apply_input(ws.cell(row=r, column=4), 0, NUM_FMT_KRW)
            apply_input(ws.cell(row=r, column=5), 0.25, NUM_FMT_PCT)

        total_row = row + 1 + len(methods) + 1
        apply_label(ws.cell(row=total_row, column=2), "Weighted Average EV")
        apply_total(
            ws.cell(row=total_row, column=3),
            f"=SUMPRODUCT(C{row + 1}:C{row + len(methods)},E{row + 1}:E{row + len(methods)})",
            NUM_FMT_KRW,
        )
        apply_label(ws.cell(row=total_row + 1, column=2), "Weighted Average Equity")
        apply_total(
            ws.cell(row=total_row + 1, column=3),
            f"=SUMPRODUCT(D{row + 1}:D{row + len(methods)},E{row + 1}:E{row + len(methods)})",
            NUM_FMT_KRW,
        )

    # ── Football Field 시트 ──────────────────────────────────

    def _build_football_field(self, ws):
        """밸류에이션 범위 요약 (Football Field 차트 데이터)."""
        set_column_widths(ws, {"A": 3, "B": 25, "C": 16, "D": 16, "E": 16})
        ws.sheet_properties.tabColor = "D8F3DC"

        apply_title(ws["B2"], "Football Field — Valuation Range")

        row = 4
        apply_header(ws.cell(row=row, column=2), "Method")
        apply_header(ws.cell(row=row, column=3), "Low")
        apply_header(ws.cell(row=row, column=4), "Mid")
        apply_header(ws.cell(row=row, column=5), "High")

        methods = ["DCF", "GPCM (EV/EBITDA)", "GTM (DV/EBITDA)", "52-week High/Low"]
        for i, m in enumerate(methods):
            r = row + 1 + i
            apply_label(ws.cell(row=r, column=2), m)
            for ci in [3, 4, 5]:
                apply_input(ws.cell(row=r, column=ci), 0, NUM_FMT_KRW)

    # ── Stub 시트 빌더 (Sprint 2 확장용) ─────────────────────

    def _build_sources_uses(self, ws):
        """Sources & Uses (LBO)."""
        set_column_widths(ws, {"A": 3, "B": 25, "C": 18})
        ws.sheet_properties.tabColor = "FFD966"
        apply_title(ws["B2"], "Sources & Uses")
        apply_section_title(ws["B4"], "Sources")
        apply_section_title(ws["B10"], "Uses")

    def _build_debt_schedule(self, ws):
        """Debt Schedule (LBO)."""
        set_column_widths(ws, {"A": 3, "B": 25, "C": 18})
        ws.sheet_properties.tabColor = "FFD966"
        apply_title(ws["B2"], "Debt Schedule")

    def _build_returns(self, ws):
        """Returns Analysis (LBO — IRR/MOIC)."""
        set_column_widths(ws, {"A": 3, "B": 25, "C": 18})
        ws.sheet_properties.tabColor = "40916C"
        apply_title(ws["B2"], "Returns Analysis (IRR / MOIC)")

    def _build_revenue_buildup(self, ws):
        """Revenue Build-Up (Projection)."""
        set_column_widths(ws, {"A": 3, "B": 30, "C": 18})
        ws.sheet_properties.tabColor = "FFD966"
        apply_title(ws["B2"], "Revenue Build-Up")

    def _build_cost_structure(self, ws):
        """Cost Structure (Projection)."""
        set_column_widths(ws, {"A": 3, "B": 30, "C": 18})
        ws.sheet_properties.tabColor = "FFD966"
        apply_title(ws["B2"], "Cost Structure")


# ── 시트 이름 → 빌더 함수 매핑 ────────────────────────────────────────────

_SHEET_BUILDERS: dict[str, callable] = {
    "Legend": FinancialModelBuilder._build_legend,
    "Input": FinancialModelBuilder._build_input,
    "IS": FinancialModelBuilder._build_is,
    "BS": FinancialModelBuilder._build_bs,
    "CF": FinancialModelBuilder._build_cf,
    "WACC": FinancialModelBuilder._build_wacc,
    "DCF": FinancialModelBuilder._build_dcf,
    "GPCM": FinancialModelBuilder._build_gpcm,
    "GTM": FinancialModelBuilder._build_gtm,
    "Sensitivity": FinancialModelBuilder._build_sensitivity,
    "Summary": FinancialModelBuilder._build_summary,
    "Football Field": FinancialModelBuilder._build_football_field,
    "Sources & Uses": FinancialModelBuilder._build_sources_uses,
    "Debt Schedule": FinancialModelBuilder._build_debt_schedule,
    "Returns": FinancialModelBuilder._build_returns,
    "Revenue Build-Up": FinancialModelBuilder._build_revenue_buildup,
    "Cost Structure": FinancialModelBuilder._build_cost_structure,
}
