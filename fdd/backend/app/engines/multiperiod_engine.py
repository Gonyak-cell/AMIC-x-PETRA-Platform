"""다기간 재무제표 엔진 — 4년+반기 IS/BS/CF 시계열 분석.

순수 함수만 포함. DB 접근 절대 금지.
모든 금액: Decimal. float 절대 금지.

Big 4 WP 수준의 다기간 비교를 지원:
- 기간별 금액 (FY2022, FY2023, FY2024, H1 2024, H1 2025 등)
- YoY 변동률 (전년 대비 %)
- CAGR (3년+ 시 연평균 성장률)
- 소계/합계 행 자동 산출
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

ENGINE_VERSION = "0.1.0"

# Quantize constant — 4 decimal places (NUMERIC(18,4) 호환)
Q4 = Decimal("0.0001")
# Percentage precision — 2 decimal places
Q2 = Decimal("0.01")

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


def _q(amount: Decimal) -> Decimal:
    """NUMERIC(18,4) 정밀도로 반올림."""
    return amount.quantize(Q4, rounding=ROUND_HALF_UP)


def _pct(value: Decimal) -> Decimal:
    """퍼센트 정밀도 (소수점 2자리)."""
    return value.quantize(Q2, rounding=ROUND_HALF_UP)


# ── Data Types ───────────────────────────────────────────


@dataclass(frozen=True)
class LineItemDef:
    """라인아이템 정의 (엔진 입력용).

    StandardLineItem의 순수 데이터 버전 — DB 모델 의존 없이
    엔진이 행 구조를 알 수 있도록 한다.
    """

    code: str
    name_ko: str
    name_en: str
    category: str           # LineItemCategory value
    statement_type: str     # "IS" | "BS"
    display_order: int
    parent_code: str | None = None
    is_subtotal: bool = False


@dataclass(frozen=True)
class EvidenceLinkData:
    """Evidence link data (엔진 → 서비스 출력용, DB 저장 전)."""

    target_type: str
    source_type: str        # "TB" or "MAPPING"
    source_id: str
    source_detail: dict[str, Any] | None = None


@dataclass(frozen=True)
class MultiPeriodRow:
    """다기간 재무제표 행.

    각 행은 라인아이템 하나를 나타내며,
    모든 기간의 금액 + YoY + CAGR을 포함한다.
    """

    line_item_code: str
    label_ko: str
    label_en: str
    category: str
    display_order: int
    indent: int
    is_subtotal: bool
    is_total: bool
    periods: dict[str, Decimal]         # {"FY2022": Decimal("1234.5678"), ...}
    yoy_changes: dict[str, Decimal]     # {"FY2023": Decimal("5.32"), ...} (%)
    cagr: Decimal | None                # 3년+ 시 CAGR (%), None if insufficient


@dataclass
class MultiPeriodResult:
    """다기간 재무제표 결과."""

    statement_type: str                 # "IS" | "BS" | "CF"
    period_labels: list[str]            # ["FY2022", "FY2023", "FY2024", "H1 2025"]
    rows: list[MultiPeriodRow]
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Sign Convention (QoE 엔진과 동일) ──────────────────────
# TB 잔액 부호 규칙:
#   Revenue → 대변(음수) → P&L에서 양수로 부호 반전
#   COGS/SGA/D&A → 차변(양수) → 그대로
#   Other Operating Income → 대변(음수) → 양수로 반전

_SIGN_NEGATE_CATEGORIES = frozenset(
    {
        "REVENUE",
        "OTHER_OPERATING_INCOME",
        "INTEREST_INCOME",
    }
)


# ── Helper: YoY / CAGR ──────────────────────────────────


def _compute_yoy(
    periods: dict[str, Decimal],
    ordered_labels: list[str],
) -> dict[str, Decimal]:
    """YoY 변동률을 계산한다.

    Returns:
        {"FY2023": Decimal("5.32"), ...}  — 퍼센트 단위
        기준기간이 0이면 해당 키를 생략한다.
    """
    yoy: dict[str, Decimal] = {}
    for i in range(1, len(ordered_labels)):
        prev_label = ordered_labels[i - 1]
        curr_label = ordered_labels[i]
        prev_val = periods.get(prev_label, ZERO)
        curr_val = periods.get(curr_label, ZERO)

        if prev_val == ZERO:
            continue

        change_pct = _pct((curr_val - prev_val) / prev_val * HUNDRED)
        yoy[curr_label] = change_pct

    return yoy


def _compute_cagr(
    periods: dict[str, Decimal],
    ordered_fy_labels: list[str],
) -> Decimal | None:
    """CAGR (연평균 복합 성장률)을 계산한다.

    FY(연간) 레이블만 사용. 반기(H1/H2) 레이블은 제외.
    3개 이상 연간 기간이 있어야 산출 가능.

    Returns:
        CAGR (%), None if insufficient data or zero base
    """
    # FY 레이블만 필터 (H1/H2/Q 등 제외)
    fy_labels = [l for l in ordered_fy_labels if l.startswith("FY")]

    if len(fy_labels) < 2:
        return None

    first_label = fy_labels[0]
    last_label = fy_labels[-1]
    first_val = periods.get(first_label, ZERO)
    last_val = periods.get(last_label, ZERO)

    if first_val == ZERO or first_val < ZERO:
        return None

    n = len(fy_labels) - 1  # 기간 수
    if n < 1:
        return None

    # CAGR = ((end/start)^(1/n) - 1) * 100
    # Decimal에서 power(1/n)을 사용하기 위해 float 변환 후 다시 Decimal
    ratio = last_val / first_val
    if ratio <= ZERO:
        return None

    # float 변환은 CAGR 근사치에만 사용 (금액 계산에는 절대 사용 안 함)
    ratio_f = float(ratio)
    cagr_f = (ratio_f ** (1.0 / n) - 1.0) * 100.0
    return _pct(Decimal(str(cagr_f)))


# ── Core: Multi-period FS Computation ─────────────────────


def _normalize_amount(amount: Decimal, category: str) -> Decimal:
    """TB 잔액 부호를 P&L/BS 표시 부호로 변환."""
    if category in _SIGN_NEGATE_CATEGORIES:
        return _q(-amount)
    return _q(amount)


def compute_multiperiod_fs(
    amounts_by_period: dict[str, dict[str, Decimal]],
    line_item_defs: list[LineItemDef],
    *,
    statement_type: str,
    negate_signs: bool = True,
) -> tuple[MultiPeriodResult, list[EvidenceLinkData]]:
    """다기간 재무제표를 계산한다.

    Args:
        amounts_by_period: {period_label: {line_item_code: amount}}
            예: {"FY2022": {"IS-REV-001": Decimal("100000")}, ...}
            금액은 TB 원장 부호 기준.
        line_item_defs: 라인아이템 정의 리스트 (display_order 순서)
        statement_type: "IS" | "BS" | "CF"
        negate_signs: True면 TB 부호 → P&L 표시 부호 변환 (IS에만 적용)

    Returns:
        (MultiPeriodResult, evidence_links)
    """
    # 기간 레이블 정렬 (FY 연도순 → H/Q 순)
    period_labels = _sort_period_labels(list(amounts_by_period.keys()))

    # 해당 statement_type의 라인아이템만 필터 + display_order 정렬
    filtered_defs = sorted(
        [d for d in line_item_defs if d.statement_type == statement_type],
        key=lambda d: d.display_order,
    )

    warnings: list[str] = []
    evidence: list[EvidenceLinkData] = []
    rows: list[MultiPeriodRow] = []

    # 소계/합계 행의 하위 항목 집계를 위한 parent→children 맵
    code_to_def = {d.code: d for d in filtered_defs}
    children_map: dict[str, list[str]] = {}
    for d in filtered_defs:
        if d.parent_code:
            children_map.setdefault(d.parent_code, []).append(d.code)

    for item_def in filtered_defs:
        # 기간별 금액 산출
        period_amounts: dict[str, Decimal] = {}

        for period_label in period_labels:
            period_data = amounts_by_period.get(period_label, {})

            if item_def.is_subtotal and item_def.code in children_map:
                # 소계 행: 하위 항목 합산
                total = ZERO
                for child_code in children_map[item_def.code]:
                    raw = period_data.get(child_code, ZERO)
                    if negate_signs and statement_type == "IS":
                        child_def = code_to_def.get(child_code)
                        cat = child_def.category if child_def else ""
                        total += _normalize_amount(raw, cat)
                    else:
                        total += _q(raw)
                period_amounts[period_label] = total
            else:
                # 일반 행: 직접 값
                raw = period_data.get(item_def.code, ZERO)
                if negate_signs and statement_type == "IS":
                    period_amounts[period_label] = _normalize_amount(
                        raw, item_def.category
                    )
                else:
                    period_amounts[period_label] = _q(raw)

        # YoY 계산
        yoy = _compute_yoy(period_amounts, period_labels)

        # CAGR 계산
        cagr = _compute_cagr(period_amounts, period_labels)

        # 들여쓰기 수준
        indent = 1 if item_def.parent_code else 0

        rows.append(
            MultiPeriodRow(
                line_item_code=item_def.code,
                label_ko=item_def.name_ko,
                label_en=item_def.name_en,
                category=item_def.category,
                display_order=item_def.display_order,
                indent=indent,
                is_subtotal=item_def.is_subtotal,
                is_total=False,
                periods=period_amounts,
                yoy_changes=yoy,
                cagr=cagr,
            )
        )

        # Evidence 생성
        for period_label, amount in period_amounts.items():
            if amount != ZERO:
                evidence.append(
                    EvidenceLinkData(
                        target_type=f"multiperiod_{statement_type.lower()}",
                        source_type="MAPPING",
                        source_id=f"{period_label}:{item_def.code}",
                        source_detail={
                            "period": period_label,
                            "line_item_code": item_def.code,
                            "amount": str(amount),
                        },
                    )
                )

    # 경고 생성
    if not rows:
        warnings.append(f"MULTIPERIOD_EMPTY: No line items found for {statement_type}")

    if len(period_labels) < 2:
        warnings.append(
            f"MULTIPERIOD_SINGLE_PERIOD: Only {len(period_labels)} period(s) — "
            "YoY analysis requires at least 2 periods"
        )

    result = MultiPeriodResult(
        statement_type=statement_type,
        period_labels=period_labels,
        rows=rows,
        warnings=warnings,
        metadata={
            "engine_version": ENGINE_VERSION,
            "period_count": len(period_labels),
            "row_count": len(rows),
            "has_cagr": any(r.cagr is not None for r in rows),
        },
    )

    return result, evidence


# ── Convenience Functions ─────────────────────────────────


def compute_multiperiod_is(
    amounts_by_period: dict[str, dict[str, Decimal]],
    line_item_defs: list[LineItemDef],
) -> tuple[MultiPeriodResult, list[EvidenceLinkData]]:
    """다기간 손익계산서 (Income Statement)."""
    return compute_multiperiod_fs(
        amounts_by_period,
        line_item_defs,
        statement_type="IS",
        negate_signs=True,
    )


def compute_multiperiod_bs(
    amounts_by_period: dict[str, dict[str, Decimal]],
    line_item_defs: list[LineItemDef],
) -> tuple[MultiPeriodResult, list[EvidenceLinkData]]:
    """다기간 재무상태표 (Balance Sheet)."""
    return compute_multiperiod_fs(
        amounts_by_period,
        line_item_defs,
        statement_type="BS",
        negate_signs=False,
    )


def compute_multiperiod_cf(
    amounts_by_period: dict[str, dict[str, Decimal]],
    line_item_defs: list[LineItemDef],
) -> tuple[MultiPeriodResult, list[EvidenceLinkData]]:
    """다기간 현금흐름표 (Cash Flow Statement).

    CF는 별도 statement_type이 없으므로,
    서비스 레이어에서 IS/BS 변동 기반으로 CF 라인아이템을 미리 생성한 후
    이 함수에 전달한다.
    """
    return compute_multiperiod_fs(
        amounts_by_period,
        line_item_defs,
        statement_type="CF",
        negate_signs=False,
    )


# ── Derived Metrics (EBITDA / Margins / Ratios) ──────────


@dataclass(frozen=True)
class DerivedMetricsRow:
    """유도 지표 행 (매출총이익률, EBITDA 마진 등)."""

    metric_name_ko: str
    metric_name_en: str
    periods: dict[str, Decimal]     # 기간별 값 (%, 배수, 금액)
    unit: str                       # "%" | "x" | "원"


def compute_derived_metrics(
    is_result: MultiPeriodResult,
) -> list[DerivedMetricsRow]:
    """IS 결과에서 주요 재무 비율을 산출한다.

    산출 지표:
    - 매출총이익률 (Gross Margin %)
    - 영업이익률 (Operating Margin %)
    - EBITDA 마진율 (EBITDA Margin %)
    """
    metrics: list[DerivedMetricsRow] = []
    period_labels = is_result.period_labels

    # 카테고리별 행 매핑 (code → row)
    category_rows: dict[str, MultiPeriodRow] = {}
    for row in is_result.rows:
        category_rows[row.category] = row

    # Revenue, Gross Profit, Operating Income 행 찾기
    revenue_row = category_rows.get("REVENUE")
    if not revenue_row:
        return metrics

    # 소계 행에서 찾기 (매출총이익, 영업이익 등)
    subtotal_rows: dict[str, MultiPeriodRow] = {}
    for row in is_result.rows:
        if row.is_subtotal:
            # 한국어 라벨로 매칭
            key = row.label_ko.strip()
            subtotal_rows[key] = row

    # EBITDA 행도 찾기
    ebitda_row: MultiPeriodRow | None = None
    for row in is_result.rows:
        if "EBITDA" in row.label_en or "EBITDA" in row.label_ko:
            ebitda_row = row
            break

    # Gross Margin
    gp_row = subtotal_rows.get("매출총이익") or subtotal_rows.get("Gross Profit")
    if gp_row:
        gm_periods: dict[str, Decimal] = {}
        for pl in period_labels:
            rev = revenue_row.periods.get(pl, ZERO)
            gp = gp_row.periods.get(pl, ZERO)
            if rev != ZERO:
                gm_periods[pl] = _pct(gp / rev * HUNDRED)
        if gm_periods:
            metrics.append(
                DerivedMetricsRow(
                    metric_name_ko="매출총이익률",
                    metric_name_en="Gross Margin",
                    periods=gm_periods,
                    unit="%",
                )
            )

    # Operating Margin
    oi_row = subtotal_rows.get("영업이익") or subtotal_rows.get("Operating Income")
    if oi_row:
        om_periods: dict[str, Decimal] = {}
        for pl in period_labels:
            rev = revenue_row.periods.get(pl, ZERO)
            oi = oi_row.periods.get(pl, ZERO)
            if rev != ZERO:
                om_periods[pl] = _pct(oi / rev * HUNDRED)
        if om_periods:
            metrics.append(
                DerivedMetricsRow(
                    metric_name_ko="영업이익률",
                    metric_name_en="Operating Margin",
                    periods=om_periods,
                    unit="%",
                )
            )

    # EBITDA Margin
    if ebitda_row:
        em_periods: dict[str, Decimal] = {}
        for pl in period_labels:
            rev = revenue_row.periods.get(pl, ZERO)
            ebitda = ebitda_row.periods.get(pl, ZERO)
            if rev != ZERO:
                em_periods[pl] = _pct(ebitda / rev * HUNDRED)
        if em_periods:
            metrics.append(
                DerivedMetricsRow(
                    metric_name_ko="EBITDA 마진",
                    metric_name_en="EBITDA Margin",
                    periods=em_periods,
                    unit="%",
                )
            )

    return metrics


# ── Period Label Sorting ──────────────────────────────────


def _sort_period_labels(labels: list[str]) -> list[str]:
    """기간 레이블을 시간순으로 정렬한다.

    지원 형식:
    - "FY2022", "FY2023" — 연간 (fiscal year)
    - "H1 2024", "H2 2024" — 반기
    - "Q1 2024", "Q2 2024" — 분기
    - "2024-01", "2024-02" — 월별

    정렬 규칙: 연도 ASC → 기간 종류 (FY < H1 < H2 < Q1..Q4 < 월)
    """

    def _sort_key(label: str) -> tuple[int, int]:
        label = label.strip()

        # FY2022 형식
        if label.startswith("FY"):
            try:
                year = int(label[2:])
                return (year, 0)
            except ValueError:
                pass

        # H1 2024, H2 2024 형식
        if label.startswith(("H1", "H2")):
            half = 1 if label.startswith("H1") else 2
            parts = label.split()
            if len(parts) == 2:
                try:
                    year = int(parts[1])
                    return (year, half)
                except ValueError:
                    pass

        # Q1 2024 ~ Q4 2024 형식
        if label.startswith(("Q1", "Q2", "Q3", "Q4")):
            quarter = int(label[1])
            parts = label.split()
            if len(parts) == 2:
                try:
                    year = int(parts[1])
                    return (year, 2 + quarter)
                except ValueError:
                    pass

        # 2024-01 형식
        if "-" in label and len(label) == 7:
            parts = label.split("-")
            if len(parts) == 2:
                try:
                    year = int(parts[0])
                    month = int(parts[1])
                    return (year, 6 + month)
                except ValueError:
                    pass

        # 기타: 문자열 순서
        return (9999, 0)

    return sorted(labels, key=_sort_key)
