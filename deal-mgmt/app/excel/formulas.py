"""Excel 수식 생성 헬퍼 — 셀 참조 + 일반 재무 수식."""

from openpyxl.utils import get_column_letter


def col(idx: int) -> str:
    """1-based 컬럼 인덱스 → 문자 (1='A', 2='B', ...)."""
    return get_column_letter(idx)


def cell_ref(col_idx: int, row: int) -> str:
    """셀 참조 문자열 생성 (예: cell_ref(5, 10) → 'E10')."""
    return f"{col(col_idx)}{row}"


def range_ref(col_idx: int, start_row: int, end_row: int) -> str:
    """범위 참조 (예: range_ref(5, 10, 14) → 'E10:E14')."""
    c = col(col_idx)
    return f"{c}{start_row}:{c}{end_row}"


def sum_range(col_idx: int, start_row: int, end_row: int) -> str:
    """=SUM(E10:E14)."""
    return f"=SUM({range_ref(col_idx, start_row, end_row)})"


def sum_cells(*refs: str) -> str:
    """=SUM(E10,F10,G10)."""
    return f"=SUM({','.join(refs)})"


def subtract(a: str, b: str) -> str:
    """=A-B."""
    return f"={a}-{b}"


def divide(numerator: str, denominator: str) -> str:
    """=A/B (0으로 나누기 방지 포함)."""
    return f"=IF({denominator}=0,0,{numerator}/{denominator})"


def multiply(a: str, b: str) -> str:
    """=A*B."""
    return f"={a}*{b}"


def growth_rate(current: str, prior: str) -> str:
    """=(현재-이전)/이전 성장률."""
    return f"=IF({prior}=0,0,({current}-{prior})/{prior})"


def margin(part: str, total: str) -> str:
    """=부분/전체 마진율."""
    return f"=IF({total}=0,0,{part}/{total})"


def npv(rate_cell: str, cashflow_range: str) -> str:
    """=NPV(할인율, 현금흐름범위)."""
    return f"=NPV({rate_cell},{cashflow_range})"


def irr(cashflow_range: str) -> str:
    """=IRR(현금흐름범위)."""
    return f"=IRR({cashflow_range})"


def wacc(ke_cell: str, kd_cell: str, equity_weight: str, debt_weight: str) -> str:
    """WACC = Ke×We + Kd×Wd."""
    return f"={ke_cell}*{equity_weight}+{kd_cell}*{debt_weight}"


def capm(rf_cell: str, beta_cell: str, mrp_cell: str, size_premium: str | None = None) -> str:
    """Ke = Rf + Beta × MRP [+ Size Premium]."""
    formula = f"={rf_cell}+{beta_cell}*{mrp_cell}"
    if size_premium:
        formula += f"+{size_premium}"
    return formula


def terminal_value_gordon(fcf_cell: str, wacc_cell: str, g_cell: str) -> str:
    """TV = FCF×(1+g) / (WACC-g)."""
    return f"=IF({wacc_cell}-{g_cell}=0,0,{fcf_cell}*(1+{g_cell})/({wacc_cell}-{g_cell}))"


def terminal_value_exit_multiple(metric_cell: str, multiple_cell: str) -> str:
    """TV = EBITDA × Exit Multiple."""
    return f"={metric_cell}*{multiple_cell}"


def discount_factor(wacc_cell: str, year: int) -> str:
    """할인계수 = 1/(1+WACC)^year."""
    return f"=1/(1+{wacc_cell})^{year}"


def pv(value_cell: str, df_cell: str) -> str:
    """현재가치 = 미래가치 × 할인계수."""
    return f"={value_cell}*{df_cell}"


def enterprise_value(ev_equity: str, debt: str, cash: str) -> str:
    """EV = Equity Value + Debt - Cash."""
    return f"={ev_equity}+{debt}-{cash}"


def equity_value(ev: str, net_debt: str) -> str:
    """Equity Value = EV - Net Debt."""
    return f"={ev}-{net_debt}"


def ev_ebitda(ev: str, ebitda: str) -> str:
    """EV/EBITDA 멀티플."""
    return f"=IF({ebitda}=0,0,{ev}/{ebitda})"


def per(price: str, eps: str) -> str:
    """P/E 멀티플."""
    return f"=IF({eps}=0,0,{price}/{eps})"


def median_formula(range_str: str) -> str:
    """=MEDIAN(범위)."""
    return f"=MEDIAN({range_str})"


def average_formula(range_str: str) -> str:
    """=AVERAGE(범위)."""
    return f"=AVERAGE({range_str})"


# ── IS/BS/CF 관련 ─────────────────────────────────────────────────────────


def gross_profit(revenue: str, cogs: str) -> str:
    """매출총이익 = 매출 - 매출원가."""
    return f"={revenue}-{cogs}"


def operating_profit(gross_profit_cell: str, sga: str) -> str:
    """영업이익 = 매출총이익 - 판관비."""
    return f"={gross_profit_cell}-{sga}"


def ebitda(op_profit: str, dep: str) -> str:
    """EBITDA = 영업이익 + 감가상각비."""
    return f"={op_profit}+{dep}"


def net_income(ebt: str, tax: str) -> str:
    """순이익 = 세전이익 - 법인세."""
    return f"={ebt}-{tax}"


def fcf(ebitda_cell: str, tax_cell: str, capex_cell: str, nwc_change_cell: str) -> str:
    """FCF = EBITDA - Tax - CAPEX - ΔNWC."""
    return f"={ebitda_cell}-{tax_cell}-{capex_cell}-{nwc_change_cell}"


def nwc(ar: str, inventory: str, ap: str) -> str:
    """순운전자본 = 매출채권 + 재고자산 - 매입채무."""
    return f"={ar}+{inventory}-{ap}"


def days_to_amount(days_cell: str, base_cell: str, calendar_days: int = 365) -> str:
    """회전일수 → 금액. 예: 매출채권 = 매출 × DSO / 365."""
    return f"={base_cell}*{days_cell}/{calendar_days}"
