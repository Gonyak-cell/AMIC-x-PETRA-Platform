"""FCF Bridge 분석 엔진 — EBITDA → OCF → CAPEX → FCF.

순수 함수만 포함. DB 접근 절대 금지.
모든 금액: Decimal. float 절대 금지.

Big 4 WP 수준의 FCF 분석:
- EBITDA → Working Capital 변동 → 세금 → OCF
- OCF → CAPEX(유지/성장 분리) → FCF
- FCF Conversion Ratio (FCF/EBITDA)
- 다기간 FCF 추이 + YoY
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
class FCFBridgeItem:
    """FCF Bridge 워터폴 항목."""

    code: str
    label_ko: str
    label_en: str
    amount: Decimal
    is_subtotal: bool = False
    is_total: bool = False


@dataclass
class FCFPeriodData:
    """단일 기간 FCF 데이터."""

    ebitda: Decimal = ZERO
    depreciation_amortization: Decimal = ZERO
    working_capital_change: Decimal = ZERO   # ΔAR + ΔInventory - ΔAP (증가 = 음수)
    tax_paid: Decimal = ZERO
    other_operating: Decimal = ZERO
    operating_cash_flow: Decimal = ZERO      # = EBITDA + WC변동 - tax + other
    total_capex: Decimal = ZERO
    maintenance_capex: Decimal = ZERO        # ≈ D&A (유지보수)
    growth_capex: Decimal = ZERO             # = total - maintenance
    other_investing: Decimal = ZERO
    free_cash_flow: Decimal = ZERO           # = OCF - CAPEX
    fcf_conversion: Decimal | None = None    # FCF / EBITDA (%)


@dataclass
class FCFBridgeResult:
    """FCF Bridge 분석 결과."""

    period_labels: list[str]
    periods: dict[str, FCFPeriodData]        # 기간별 FCF
    bridge_items: list[FCFBridgeItem]        # 최신 기간 워터폴 차트용
    summary_kpis: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class CAPEXAnalysisResult:
    """CAPEX 분석 결과."""

    period_labels: list[str]
    total_capex: dict[str, Decimal]
    maintenance_capex: dict[str, Decimal]
    growth_capex: dict[str, Decimal]
    capex_to_revenue: dict[str, Decimal]     # CAPEX / 매출 (%)
    capex_to_da: dict[str, Decimal]          # CAPEX / D&A (배수)
    asset_additions: dict[str, Decimal]      # 유무형자산 취득
    asset_disposals: dict[str, Decimal]      # 유무형자산 처분
    warnings: list[str] = field(default_factory=list)


# ── Core: FCF Bridge ────────────────────────────────────


def compute_fcf_bridge(
    fcf_inputs: dict[str, dict[str, Any]],
    *,
    period_key_order: list[str] | None = None,
) -> tuple[FCFBridgeResult, list[EvidenceLinkData]]:
    """EBITDA → OCF → CAPEX → FCF bridge를 계산한다.

    Args:
        fcf_inputs: 기간별 FCF 구성요소.
            {
                "FY2024": {
                    "ebitda": "50000",
                    "depreciation_amortization": "10000",
                    "delta_ar": "2000",         # AR 증가 (음의 CF 영향)
                    "delta_inventory": "1000",   # 재고 증가 (음의 CF 영향)
                    "delta_ap": "500",           # AP 증가 (양의 CF 영향)
                    "tax_paid": "8000",
                    "other_operating": "0",
                    "capex": "15000",            # 총 CAPEX (양수)
                    "other_investing": "0",
                },
                ...
            }
        period_key_order: 기간 정렬 순서 (없으면 sorted)

    Returns:
        (FCFBridgeResult, list[EvidenceLinkData])
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []

    if not fcf_inputs:
        return FCFBridgeResult(
            period_labels=[], periods={}, bridge_items=[],
            warnings=["FCF_EMPTY: No FCF input data"],
        ), evidence

    period_labels = period_key_order or sorted(fcf_inputs.keys())
    periods: dict[str, FCFPeriodData] = {}

    for p in period_labels:
        data = fcf_inputs.get(p, {})
        ebitda = _q(Decimal(str(data.get("ebitda", "0"))))
        da = _q(abs(Decimal(str(data.get("depreciation_amortization", "0")))))

        # Working capital changes (증가 = CF 감소 → 음수로 표현)
        delta_ar = _q(Decimal(str(data.get("delta_ar", "0"))))
        delta_inv = _q(Decimal(str(data.get("delta_inventory", "0"))))
        delta_ap = _q(Decimal(str(data.get("delta_ap", "0"))))
        wc_change = _q(-delta_ar - delta_inv + delta_ap)  # AP 증가는 양의 CF

        tax = _q(abs(Decimal(str(data.get("tax_paid", "0")))))
        other_op = _q(Decimal(str(data.get("other_operating", "0"))))

        # OCF = EBITDA + WC변동 - Tax + Other
        ocf = _q(ebitda + wc_change - tax + other_op)

        # CAPEX
        total_capex = _q(abs(Decimal(str(data.get("capex", "0")))))
        # 유지보수 CAPEX ≈ D&A (근사치)
        maint_capex = _q(min(da, total_capex))
        growth_capex = _q(total_capex - maint_capex)
        other_inv = _q(Decimal(str(data.get("other_investing", "0"))))

        # FCF = OCF - CAPEX
        fcf = _q(ocf - total_capex)

        # FCF Conversion
        fcf_conv = None
        if ebitda > ZERO:
            fcf_conv = _pct(fcf / ebitda * HUNDRED)
        elif ebitda < ZERO:
            warnings.append(f"FCF_NEGATIVE_EBITDA:{p}: EBITDA is negative")

        periods[p] = FCFPeriodData(
            ebitda=ebitda,
            depreciation_amortization=da,
            working_capital_change=wc_change,
            tax_paid=tax,
            other_operating=other_op,
            operating_cash_flow=ocf,
            total_capex=total_capex,
            maintenance_capex=maint_capex,
            growth_capex=growth_capex,
            other_investing=other_inv,
            free_cash_flow=fcf,
            fcf_conversion=fcf_conv,
        )

        # Evidence
        evidence.append(EvidenceLinkData(
            target_type="fcf_bridge",
            source_type="computed",
            source_id=f"fcf:{p}",
            source_detail={
                "period": p,
                "ebitda": str(ebitda),
                "ocf": str(ocf),
                "capex": str(total_capex),
                "fcf": str(fcf),
            },
        ))

    # 최신 기간 워터폴 차트용 bridge_items
    latest = period_labels[-1] if period_labels else ""
    bridge_items = _build_bridge_items(periods.get(latest, FCFPeriodData()))

    # Summary KPIs
    summary: dict[str, Any] = {}
    if latest and latest in periods:
        lp = periods[latest]
        summary["latest_fcf"] = str(lp.free_cash_flow)
        summary["latest_ocf"] = str(lp.operating_cash_flow)
        summary["latest_ebitda"] = str(lp.ebitda)
        summary["fcf_conversion"] = str(lp.fcf_conversion) if lp.fcf_conversion else "N/A"

    # 경고: 낮은 FCF conversion
    for p, pd in periods.items():
        if pd.fcf_conversion is not None and pd.fcf_conversion < Decimal("30"):
            warnings.append(
                f"FCF_LOW_CONVERSION:{p}: FCF conversion {pd.fcf_conversion}% is below 30%"
            )
        if pd.free_cash_flow < ZERO:
            warnings.append(f"FCF_NEGATIVE:{p}: Negative FCF ({pd.free_cash_flow})")

    return FCFBridgeResult(
        period_labels=period_labels,
        periods=periods,
        bridge_items=bridge_items,
        summary_kpis=summary,
        warnings=warnings,
    ), evidence


def _build_bridge_items(pd: FCFPeriodData) -> list[FCFBridgeItem]:
    """워터폴 차트용 bridge 항목 생성."""
    return [
        FCFBridgeItem("FCF-EBITDA", "EBITDA", "EBITDA", pd.ebitda),
        FCFBridgeItem("FCF-WC", "운전자본 변동", "Working Capital Change", pd.working_capital_change),
        FCFBridgeItem("FCF-TAX", "법인세 납부", "Tax Paid", -pd.tax_paid),
        FCFBridgeItem("FCF-OTHER-OP", "기타 영업활동", "Other Operating", pd.other_operating),
        FCFBridgeItem(
            "FCF-OCF", "영업현금흐름", "Operating CF",
            pd.operating_cash_flow, is_subtotal=True,
        ),
        FCFBridgeItem("FCF-CAPEX", "CAPEX", "Capital Expenditures", -pd.total_capex),
        FCFBridgeItem(
            "FCF-FCF", "잉여현금흐름", "Free Cash Flow",
            pd.free_cash_flow, is_total=True,
        ),
    ]


# ── Core: CAPEX Analysis ────────────────────────────────


def compute_capex_analysis(
    capex_entries: list[dict[str, Any]],
    *,
    da_by_period: dict[str, Decimal] | None = None,
    revenue_by_period: dict[str, Decimal] | None = None,
    period_key: str = "period",
    amount_key: str = "amount",
    category_key: str = "capex_type",
) -> tuple[CAPEXAnalysisResult, list[EvidenceLinkData]]:
    """CAPEX 상세 분석.

    Args:
        capex_entries: CAPEX 항목 데이터
            [{"period": "FY2024", "capex_type": "acquisition", "amount": "15000"}, ...]
        da_by_period: 기간별 감가상각비 (유지보수 CAPEX 추정용)
        revenue_by_period: 기간별 매출 (비율 계산용)
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []

    total_capex: dict[str, Decimal] = {}
    additions: dict[str, Decimal] = {}
    disposals: dict[str, Decimal] = {}
    periods: set[str] = set()

    for e in capex_entries:
        period = str(e.get(period_key, "")).strip()
        cat = str(e.get(category_key, "")).strip().lower()
        raw = e.get(amount_key, "0")
        amount = _q(abs(Decimal(str(raw)))) if raw else ZERO

        if not period:
            continue
        periods.add(period)

        if cat in ("disposal", "처분", "매각"):
            disposals[period] = disposals.get(period, ZERO) + amount
        else:
            # acquisition, addition, 취득, etc.
            additions[period] = additions.get(period, ZERO) + amount

    period_labels = sorted(periods)

    for p in period_labels:
        total_capex[p] = _q(additions.get(p, ZERO))

    # 유지/성장 CAPEX 분리
    da = da_by_period or {}
    maint: dict[str, Decimal] = {}
    growth: dict[str, Decimal] = {}
    capex_to_da_ratio: dict[str, Decimal] = {}

    for p in period_labels:
        tc = total_capex.get(p, ZERO)
        da_val = da.get(p, ZERO)
        maint[p] = _q(min(da_val, tc))
        growth[p] = _q(tc - maint[p])
        if da_val > ZERO:
            capex_to_da_ratio[p] = _pct(tc / da_val)

    # CAPEX / Revenue
    capex_rev: dict[str, Decimal] = {}
    if revenue_by_period:
        for p in period_labels:
            rev = revenue_by_period.get(p, ZERO)
            if rev > ZERO:
                capex_rev[p] = _pct(total_capex.get(p, ZERO) / rev * HUNDRED)

    if not period_labels:
        warnings.append("CAPEX_EMPTY: No CAPEX data")

    # Evidence
    for p in period_labels:
        if total_capex.get(p, ZERO) > ZERO:
            evidence.append(EvidenceLinkData(
                target_type="capex_analysis",
                source_type="computed",
                source_id=f"capex:{p}",
                source_detail={
                    "period": p,
                    "total": str(total_capex[p]),
                    "maintenance": str(maint[p]),
                    "growth": str(growth[p]),
                },
            ))

    return CAPEXAnalysisResult(
        period_labels=period_labels,
        total_capex=total_capex,
        maintenance_capex=maint,
        growth_capex=growth,
        capex_to_revenue=capex_rev,
        capex_to_da=capex_to_da_ratio,
        asset_additions=additions,
        asset_disposals=disposals,
        warnings=warnings,
    ), evidence
