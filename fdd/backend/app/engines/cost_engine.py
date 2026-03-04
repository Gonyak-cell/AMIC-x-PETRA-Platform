"""비용 구조 분석 엔진 — 제조원가 3요소, 판관비, 인건비.

순수 함수만 포함. DB 접근 절대 금지.
모든 금액: Decimal. float 절대 금지.

Big 4 WP 수준의 비용 구조 분석:
- 제조원가 3요소 (직접재료비/직접인건비/제조경비)
- 판관비 항목별 breakdown
- 인건비 분석 (총인건비, 1인당, 부서별)
- 원가율/비율 추이
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

ENGINE_VERSION = "0.1.0"

Q4 = Decimal("0.0001")
Q2 = Decimal("0.01")
ZERO = Decimal("0")
HUNDRED = Decimal("100")


def _q(amount: Decimal) -> Decimal:
    return amount.quantize(Q4, rounding=ROUND_HALF_UP)


def _pct(value: Decimal) -> Decimal:
    return value.quantize(Q2, rounding=ROUND_HALF_UP)


# ── Data Types ───────────────────────────────────────────


@dataclass(frozen=True)
class EvidenceLinkData:
    target_type: str
    source_type: str
    source_id: str
    source_detail: dict[str, Any] | None = None


@dataclass(frozen=True)
class CostItem:
    """비용 항목."""

    code: str
    name_ko: str
    name_en: str
    amounts_by_period: dict[str, Decimal]
    share_pct: Decimal  # 매출 대비 비중 (%)
    yoy_pct: Decimal | None  # YoY 변동률 (%)


@dataclass
class ManufacturingCostResult:
    """제조원가 분석 결과."""

    period_labels: list[str]
    direct_materials: dict[str, Decimal]  # 기간별 직접재료비
    direct_labor: dict[str, Decimal]  # 기간별 직접인건비
    manufacturing_overhead: dict[str, Decimal]  # 기간별 제조경비
    total_cogs: dict[str, Decimal]  # 기간별 매출원가 합계
    material_ratio: dict[str, Decimal]  # 재료비율 (%)
    labor_ratio: dict[str, Decimal]  # 인건비율 (%)
    overhead_ratio: dict[str, Decimal]  # 경비율 (%)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SGABreakdownResult:
    """판관비 분석 결과."""

    period_labels: list[str]
    items: list[CostItem]
    total_sga: dict[str, Decimal]
    sga_to_revenue_ratio: dict[str, Decimal]  # 판관비율 (%)
    warnings: list[str] = field(default_factory=list)


@dataclass
class PersonnelCostResult:
    """인건비 분석 결과."""

    period_labels: list[str]
    total_personnel: dict[str, Decimal]  # 기간별 총 인건비
    headcount: dict[str, int]  # 기간별 인원수
    cost_per_head: dict[str, Decimal]  # 기간별 1인당 인건비
    personnel_to_revenue: dict[str, Decimal]  # 인건비/매출 (%)
    department_breakdown: list[CostItem]  # 부서별 (가능 시)
    warnings: list[str] = field(default_factory=list)


# ── Core: Manufacturing Cost ─────────────────────────────


def compute_manufacturing_cost(
    cost_entries: list[dict[str, Any]],
    *,
    revenue_by_period: dict[str, Decimal] | None = None,
    period_key: str = "period",
    amount_key: str = "amount",
    category_key: str = "cost_category",
) -> tuple[ManufacturingCostResult, list[EvidenceLinkData]]:
    """제조원가 3요소를 분석한다.

    Args:
        cost_entries: 원가 데이터
            [{"period": "FY2024", "cost_category": "direct_material", "amount": "50000"}, ...]
        revenue_by_period: 기간별 매출 (비율 계산용)
        period_key: 기간 필드명
        amount_key: 금액 필드명
        category_key: 원가 분류 필드명
            값: "direct_material" | "direct_labor" | "manufacturing_overhead"
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []

    # 기간별 × 카테고리별 집계
    dm: dict[str, Decimal] = {}
    dl: dict[str, Decimal] = {}
    oh: dict[str, Decimal] = {}
    periods: set[str] = set()

    for e in cost_entries:
        period = str(e.get(period_key, "")).strip()
        cat = str(e.get(category_key, "")).strip().lower()
        raw = e.get(amount_key, "0")
        amount = _q(abs(Decimal(str(raw)))) if raw else ZERO

        if not period:
            continue
        periods.add(period)

        if cat in ("direct_material", "materials", "재료비", "직접재료비"):
            dm[period] = dm.get(period, ZERO) + amount
        elif cat in ("direct_labor", "labor", "인건비", "직접인건비", "노무비"):
            dl[period] = dl.get(period, ZERO) + amount
        elif cat in ("manufacturing_overhead", "overhead", "경비", "제조경비"):
            oh[period] = oh.get(period, ZERO) + amount

    period_labels = sorted(periods)

    # 합계
    total_cogs: dict[str, Decimal] = {}
    for p in period_labels:
        total_cogs[p] = _q(dm.get(p, ZERO) + dl.get(p, ZERO) + oh.get(p, ZERO))

    # 비율 계산
    mat_ratio: dict[str, Decimal] = {}
    lab_ratio: dict[str, Decimal] = {}
    oh_ratio: dict[str, Decimal] = {}
    for p in period_labels:
        total = total_cogs.get(p, ZERO)
        if total > ZERO:
            mat_ratio[p] = _pct(dm.get(p, ZERO) / total * HUNDRED)
            lab_ratio[p] = _pct(dl.get(p, ZERO) / total * HUNDRED)
            oh_ratio[p] = _pct(oh.get(p, ZERO) / total * HUNDRED)

    # Evidence
    for p in period_labels:
        for cat_name, cat_data in [("material", dm), ("labor", dl), ("overhead", oh)]:
            if cat_data.get(p, ZERO) > ZERO:
                evidence.append(
                    EvidenceLinkData(
                        target_type="manufacturing_cost",
                        source_type="GL",
                        source_id=f"cost:{cat_name}:{p}",
                        source_detail={
                            "period": p,
                            "category": cat_name,
                            "amount": str(cat_data[p]),
                        },
                    )
                )

    if not period_labels:
        warnings.append("COST_EMPTY: No manufacturing cost data")

    return ManufacturingCostResult(
        period_labels=period_labels,
        direct_materials=dm,
        direct_labor=dl,
        manufacturing_overhead=oh,
        total_cogs=total_cogs,
        material_ratio=mat_ratio,
        labor_ratio=lab_ratio,
        overhead_ratio=oh_ratio,
        warnings=warnings,
    ), evidence


# ── Core: SGA Breakdown ──────────────────────────────────


def compute_sga_breakdown(
    sga_entries: list[dict[str, Any]],
    *,
    revenue_by_period: dict[str, Decimal] | None = None,
    period_key: str = "period",
    amount_key: str = "amount",
    item_key: str = "account_name",
    top_n: int = 10,
) -> tuple[SGABreakdownResult, list[EvidenceLinkData]]:
    """판관비 항목별 분석.

    Args:
        sga_entries: 판관비 GL 데이터
        revenue_by_period: 기간별 매출 (비율 계산용)
        item_key: 항목명 필드
        top_n: 상위 N개 항목 (나머지 기타)
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []

    # 항목별 × 기간별 집계
    item_period: dict[str, dict[str, Decimal]] = {}
    periods: set[str] = set()

    for e in sga_entries:
        period = str(e.get(period_key, "")).strip()
        item_name = str(e.get(item_key, "")).strip()
        raw = e.get(amount_key, "0")
        amount = _q(abs(Decimal(str(raw)))) if raw else ZERO

        if not period or not item_name:
            continue
        periods.add(period)
        item_period.setdefault(item_name, {})
        item_period[item_name][period] = (
            item_period[item_name].get(period, ZERO) + amount
        )

    period_labels = sorted(periods)
    if not period_labels:
        warnings.append("SGA_EMPTY: No SGA data")
        return SGABreakdownResult(
            period_labels=[],
            items=[],
            total_sga={},
            sga_to_revenue_ratio={},
            warnings=warnings,
        ), evidence

    # 최신 기간 기준 정렬
    latest = period_labels[-1]
    item_totals = {
        name: data.get(latest, sum(data.values(), ZERO))
        for name, data in item_period.items()
    }
    sorted_items = sorted(item_totals.items(), key=lambda x: x[1], reverse=True)

    # Total SGA
    total_sga: dict[str, Decimal] = {}
    for p in period_labels:
        total_sga[p] = _q(sum(data.get(p, ZERO) for data in item_period.values()))

    # Top N + 기타
    items: list[CostItem] = []
    for rank, (name, _) in enumerate(sorted_items[:top_n]):
        data = item_period[name]
        share = ZERO
        if total_sga.get(latest, ZERO) > ZERO:
            share = _pct(data.get(latest, ZERO) / total_sga[latest] * HUNDRED)

        # YoY
        yoy = None
        fy_labels = [l for l in period_labels if l.startswith("FY")]
        if len(fy_labels) >= 2:
            prev = data.get(fy_labels[-2], ZERO)
            curr = data.get(fy_labels[-1], ZERO)
            if prev > ZERO:
                yoy = _pct((curr - prev) / prev * HUNDRED)

        items.append(
            CostItem(
                code=f"SGA-{rank + 1:03d}",
                name_ko=name,
                name_en=name,
                amounts_by_period=data,
                share_pct=share,
                yoy_pct=yoy,
            )
        )

    # 기타 합산
    if len(sorted_items) > top_n:
        others_data: dict[str, Decimal] = {}
        for name, _ in sorted_items[top_n:]:
            for p, amt in item_period[name].items():
                others_data[p] = others_data.get(p, ZERO) + amt
        others_share = ZERO
        if total_sga.get(latest, ZERO) > ZERO:
            others_share = _pct(
                others_data.get(latest, ZERO) / total_sga[latest] * HUNDRED
            )
        items.append(
            CostItem(
                code="SGA-ETC",
                name_ko="기타",
                name_en="Others",
                amounts_by_period=others_data,
                share_pct=others_share,
                yoy_pct=None,
            )
        )

    # SGA / Revenue ratio
    sga_rev_ratio: dict[str, Decimal] = {}
    if revenue_by_period:
        for p in period_labels:
            rev = revenue_by_period.get(p, ZERO)
            if rev > ZERO:
                sga_rev_ratio[p] = _pct(total_sga.get(p, ZERO) / rev * HUNDRED)

    return SGABreakdownResult(
        period_labels=period_labels,
        items=items,
        total_sga=total_sga,
        sga_to_revenue_ratio=sga_rev_ratio,
        warnings=warnings,
    ), evidence


# ── Core: Personnel Cost ─────────────────────────────────


def compute_personnel_cost(
    personnel_entries: list[dict[str, Any]],
    *,
    headcount_by_period: dict[str, int] | None = None,
    revenue_by_period: dict[str, Decimal] | None = None,
    period_key: str = "period",
    amount_key: str = "amount",
    department_key: str = "department",
) -> tuple[PersonnelCostResult, list[EvidenceLinkData]]:
    """인건비 분석.

    Args:
        personnel_entries: 인건비 GL 데이터
        headcount_by_period: 기간별 인원수
        revenue_by_period: 기간별 매출
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []

    # 기간별 총 인건비 + 부서별
    total_by_period: dict[str, Decimal] = {}
    dept_period: dict[str, dict[str, Decimal]] = {}
    periods: set[str] = set()

    for e in personnel_entries:
        period = str(e.get(period_key, "")).strip()
        dept = str(e.get(department_key, "전체")).strip() or "전체"
        raw = e.get(amount_key, "0")
        amount = _q(abs(Decimal(str(raw)))) if raw else ZERO

        if not period:
            continue
        periods.add(period)
        total_by_period[period] = total_by_period.get(period, ZERO) + amount
        dept_period.setdefault(dept, {})
        dept_period[dept][period] = dept_period[dept].get(period, ZERO) + amount

    period_labels = sorted(periods)
    headcount = headcount_by_period or {}

    # 1인당 인건비
    cost_per_head: dict[str, Decimal] = {}
    for p in period_labels:
        hc = headcount.get(p, 0)
        if hc > 0:
            cost_per_head[p] = _q(total_by_period.get(p, ZERO) / Decimal(str(hc)))

    # 인건비/매출 비율
    pers_rev: dict[str, Decimal] = {}
    if revenue_by_period:
        for p in period_labels:
            rev = revenue_by_period.get(p, ZERO)
            if rev > ZERO:
                pers_rev[p] = _pct(total_by_period.get(p, ZERO) / rev * HUNDRED)

    # 부서별 breakdown
    dept_items: list[CostItem] = []
    latest = period_labels[-1] if period_labels else ""
    for dept_name, data in sorted(
        dept_period.items(),
        key=lambda x: x[1].get(latest, ZERO),
        reverse=True,
    ):
        share = ZERO
        if total_by_period.get(latest, ZERO) > ZERO:
            share = _pct(data.get(latest, ZERO) / total_by_period[latest] * HUNDRED)
        dept_items.append(
            CostItem(
                code=f"DEPT-{dept_name}",
                name_ko=dept_name,
                name_en=dept_name,
                amounts_by_period=data,
                share_pct=share,
                yoy_pct=None,
            )
        )

    if not period_labels:
        warnings.append("PERSONNEL_EMPTY: No personnel cost data")

    return PersonnelCostResult(
        period_labels=period_labels,
        total_personnel=total_by_period,
        headcount=headcount,
        cost_per_head=cost_per_head,
        personnel_to_revenue=pers_rev,
        department_breakdown=dept_items,
        warnings=warnings,
    ), evidence
