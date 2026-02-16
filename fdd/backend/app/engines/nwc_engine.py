"""NWC (Net Working Capital) 계산 엔진 — FDD-601/602/603.

순수 함수만 포함. DB 접근 절대 금지.
모든 금액: Decimal. float 절대 금지.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.industry.models import FDDIndustryContext

ENGINE_VERSION = "0.1.0"

# Quantize constant — 4 decimal places
Q4 = Decimal("0.0001")


# -- Data Types ---------------------------------------------------


@dataclass(frozen=True)
class EvidenceLinkData:
    """Evidence link data (엔진 -> 서비스 출력용, DB 저장 전)."""

    target_type: str
    source_type: str
    source_id: str
    source_detail: dict[str, Any] | None = None


@dataclass(frozen=True)
class BSAccountData:
    """BS 계정 데이터 (서비스 -> 엔진 입력용)."""

    account_code: str
    account_name: str
    category: str  # LineItemCategory value (AR, INVENTORY, AP, etc.)
    amount: Decimal  # 기준일 잔액
    upload_file_id: str  # TB 원천 파일 ID
    monthly_amounts: dict[str, Decimal]  # {"2025-01": Decimal(...), ...}


@dataclass(frozen=True)
class NWCDefinition:
    """NWC 분류 정의 — FDD-601.

    어떤 카테고리가 above-the-line WC인지 정의.
    """

    # 기본 WC 자산 카테고리 (Cash 제외)
    wc_asset_categories: frozenset[str] = frozenset(
        {
            "AR",
            "INVENTORY",
            "OTHER_CURRENT_ASSETS",
        }
    )
    # 기본 WC 부채 카테고리 (Debt 제외)
    wc_liability_categories: frozenset[str] = frozenset(
        {
            "AP",
            "ACCRUALS",
            "OTHER_CURRENT_LIABILITIES",
        }
    )
    # 사용자가 below-the-line으로 이동시킨 코드
    below_line_codes: frozenset[str] = frozenset()
    # 사용자가 제외시킨 코드
    excluded_codes: frozenset[str] = frozenset()


@dataclass
class NWCItemResult:
    """개별 NWC 항목 결과."""

    account_code: str
    account_name: str
    category: str
    classification: str  # "ABOVE_LINE" | "BELOW_LINE" | "EXCLUDED"
    amount: Decimal
    monthly_amounts: dict[str, str]  # {"2025-01": "1234.5678", ...}
    is_asset: bool  # True=자산, False=부채


@dataclass
class NWCSummaryResult:
    """NWC 계산 요약 결과."""

    total_current_assets: Decimal
    total_current_liabilities: Decimal
    net_working_capital: Decimal
    items: list[NWCItemResult]
    category_breakdown: dict[str, Any]
    monthly_trend: dict[str, dict[str, str]]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PegResult:
    """Peg 산정 결과 — FDD-603."""

    method: str  # PegMethod value
    target_nwc: Decimal
    delta: Decimal  # reference_nwc - target
    description: str


# -- Helpers ------------------------------------------------------


def _q(amount: Decimal) -> Decimal:
    """NUMERIC(18,4) 정밀도로 반올림."""
    return amount.quantize(Q4, rounding=ROUND_HALF_UP)


# -- BS Sign Convention -------------------------------------------
# BS 계정 부호 규칙:
#   자산 (Asset): 차변(양수) → 그대로
#   부채 (Liability): 대변(음수) → 부호 반전하여 양수로 표시
#   TB에서 부채는 음수잔액 → 절대값으로 변환

_ASSET_CATEGORIES = frozenset(
    {
        "CASH",
        "AR",
        "INVENTORY",
        "OTHER_CURRENT_ASSETS",
        "PPE",
        "INTANGIBLES",
        "OTHER_NONCURRENT_ASSETS",
    }
)

_LIABILITY_CATEGORIES = frozenset(
    {
        "AP",
        "ACCRUALS",
        "OTHER_CURRENT_LIABILITIES",
        "DEBT",
        "LEASE_LIABILITIES",
        "OTHER_NONCURRENT_LIABILITIES",
    }
)


def _is_asset_category(category: str) -> bool:
    return category in _ASSET_CATEGORIES


def _is_liability_category(category: str) -> bool:
    return category in _LIABILITY_CATEGORIES


# -- FDD-601: NWC Classification -----------------------------------


def classify_nwc_items(
    bs_accounts: list[BSAccountData],
    definition: NWCDefinition,
) -> tuple[list[NWCItemResult], list[EvidenceLinkData]]:
    """BS 계정을 WC 항목으로 분류한다.

    Args:
        bs_accounts: BS 계정 데이터 리스트 (TB 기준)
        definition: NWC 분류 정의

    Returns:
        (NWC 항목 리스트, evidence links)
    """
    items: list[NWCItemResult] = []
    evidence: list[EvidenceLinkData] = []

    all_wc_categories = (
        definition.wc_asset_categories | definition.wc_liability_categories
    )

    for acct in bs_accounts:
        # 분류 결정
        if acct.account_code in definition.excluded_codes:
            classification = "EXCLUDED"
        elif acct.account_code in definition.below_line_codes:
            classification = "BELOW_LINE"
        elif acct.category in all_wc_categories:
            classification = "ABOVE_LINE"
        else:
            classification = "EXCLUDED"

        is_asset = _is_asset_category(acct.category)

        # BS 부호 정규화: 자산=양수, 부채=양수(절대값)
        normalized_amount = _q(acct.amount) if is_asset else _q(abs(acct.amount))

        # 월별 금액도 정규화
        monthly_str: dict[str, str] = {}
        for month, amt in acct.monthly_amounts.items():
            if is_asset:
                monthly_str[month] = str(_q(amt))
            else:
                monthly_str[month] = str(_q(abs(amt)))

        items.append(
            NWCItemResult(
                account_code=acct.account_code,
                account_name=acct.account_name,
                category=acct.category,
                classification=classification,
                amount=normalized_amount,
                monthly_amounts=monthly_str,
                is_asset=is_asset,
            )
        )

        # Evidence link
        evidence.append(
            EvidenceLinkData(
                target_type="nwc_calculation",
                source_type="TB",
                source_id=acct.upload_file_id,
                source_detail={
                    "account_code": acct.account_code,
                    "account_name": acct.account_name,
                    "amount": str(normalized_amount),
                    "category": acct.category,
                    "classification": classification,
                },
            )
        )

    return items, evidence


# -- FDD-602: NWC Calculation + Monthly Trend ---------------------


def calculate_nwc(
    items: list[NWCItemResult],
    industry_context: FDDIndustryContext | None = None,
) -> NWCSummaryResult:
    """NWC를 계산하고 월별 트렌드를 구한다.

    NWC = Σ(above-line assets) - Σ(above-line liabilities)

    Args:
        items: 분류된 NWC 항목 리스트

    Returns:
        NWCSummaryResult
    """
    total_ca = Decimal("0")
    total_cl = Decimal("0")

    # Category breakdown
    cat_breakdown: dict[str, dict[str, Any]] = {}
    # Monthly aggregation
    monthly_ca: dict[str, Decimal] = {}
    monthly_cl: dict[str, Decimal] = {}

    for item in items:
        if item.classification != "ABOVE_LINE":
            continue

        # Category breakdown 집계
        if item.category not in cat_breakdown:
            cat_breakdown[item.category] = {
                "total": Decimal("0"),
                "count": 0,
                "is_asset": item.is_asset,
                "accounts": [],
            }
        cat_breakdown[item.category]["total"] += item.amount
        cat_breakdown[item.category]["count"] += 1
        cat_breakdown[item.category]["accounts"].append(
            {
                "code": item.account_code,
                "name": item.account_name,
                "amount": str(item.amount),
            }
        )

        # 자산/부채 합계
        if item.is_asset:
            total_ca += item.amount
        else:
            total_cl += item.amount

        # 월별 집계
        for month, amt_str in item.monthly_amounts.items():
            amt = Decimal(amt_str)
            if item.is_asset:
                monthly_ca[month] = monthly_ca.get(month, Decimal("0")) + amt
            else:
                monthly_cl[month] = monthly_cl.get(month, Decimal("0")) + amt

    total_ca = _q(total_ca)
    total_cl = _q(total_cl)
    nwc = _q(total_ca - total_cl)

    # Category breakdown 문자열 변환
    for cat_key in cat_breakdown:
        cat_breakdown[cat_key]["total"] = str(_q(cat_breakdown[cat_key]["total"]))

    # Monthly trend
    all_months = sorted(set(monthly_ca.keys()) | set(monthly_cl.keys()))
    monthly_trend: dict[str, dict[str, str]] = {}
    for month in all_months:
        ca = _q(monthly_ca.get(month, Decimal("0")))
        cl = _q(monthly_cl.get(month, Decimal("0")))
        monthly_trend[month] = {
            "current_assets": str(ca),
            "current_liabilities": str(cl),
            "nwc": str(_q(ca - cl)),
        }

    # Warnings
    warnings: list[str] = []
    if nwc < Decimal("0"):
        # 산업별 음의 NWC 허용 여부 체크
        negative_ok = False
        if industry_context:
            for norm in industry_context.nwc_norms:
                if norm.negative_nwc_acceptable:
                    negative_ok = True
                    break
        if negative_ok:
            warnings.append(
                f"NWC_NEGATIVE_INDUSTRY_OK: Net Working Capital is negative "
                f"(typical for {industry_context.industry_name_en})"  # type: ignore[union-attr]
            )
        else:
            warnings.append("NWC_NEGATIVE: Net Working Capital is negative")

    # 산업별 추가 경고 (계절성, NWC 일수 범위 등)
    if industry_context:
        for norm in industry_context.nwc_norms:
            if norm.seasonal_pattern:
                warnings.append(
                    f"NWC_SEASONAL: {norm.seasonal_pattern} — {norm.description}"
                )

    return NWCSummaryResult(
        total_current_assets=total_ca,
        total_current_liabilities=total_cl,
        net_working_capital=nwc,
        items=items,
        category_breakdown=cat_breakdown,
        monthly_trend=monthly_trend,
        warnings=warnings,
    )


# -- FDD-603: Peg Simulation (6 scenarios) -----------------------


_PEG_DESCRIPTIONS: dict[str, str] = {
    "LTM_AVERAGE": "Last 12 Months Average NWC",
    "TTM": "Trailing Twelve Months (last month end NWC)",
    "LAST_MONTH": "Most recent month-end NWC",
    "MAX": "Maximum monthly NWC over the period",
    "MIN": "Minimum monthly NWC over the period",
    "CUSTOM": "User-defined target NWC",
}


def calculate_peg(
    monthly_nwc: dict[str, Decimal],
    method: str,
    custom_value: Decimal | None = None,
) -> PegResult:
    """단일 Peg 시나리오를 계산한다.

    Args:
        monthly_nwc: 월별 NWC {"2025-01": Decimal(...), ...}
        method: PegMethod value
        custom_value: CUSTOM 일 때 사용자 지정값

    Returns:
        PegResult
    """
    if not monthly_nwc:
        return PegResult(
            method=method,
            target_nwc=Decimal("0"),
            delta=Decimal("0"),
            description=_PEG_DESCRIPTIONS.get(method, method),
        )

    sorted_months = sorted(monthly_nwc.keys())
    values = [monthly_nwc[m] for m in sorted_months]

    if method == "LTM_AVERAGE":
        # Last 12 months average
        ltm_values = values[-12:] if len(values) >= 12 else values
        target = _q(sum(ltm_values, Decimal("0")) / Decimal(str(len(ltm_values))))
    elif method == "TTM":
        # Last month (same as LAST_MONTH but semantically different)
        target = _q(values[-1])
    elif method == "LAST_MONTH":
        target = _q(values[-1])
    elif method == "MAX":
        target = _q(max(values))
    elif method == "MIN":
        target = _q(min(values))
    elif method == "CUSTOM":
        target = _q(custom_value) if custom_value is not None else Decimal("0")
    else:
        target = Decimal("0")

    # Delta = reference NWC (last month) - peg target
    reference_nwc = _q(values[-1])
    delta = _q(reference_nwc - target)

    return PegResult(
        method=method,
        target_nwc=target,
        delta=delta,
        description=_PEG_DESCRIPTIONS.get(method, method),
    )


def simulate_all_pegs(
    monthly_nwc: dict[str, Decimal],
    custom_value: Decimal | None = None,
) -> list[PegResult]:
    """6종 Peg 시나리오를 모두 시뮬레이션한다 — FDD-603.

    Returns:
        6개 PegResult 리스트
    """
    methods = [
        "LTM_AVERAGE",
        "TTM",
        "LAST_MONTH",
        "MAX",
        "MIN",
        "CUSTOM",
    ]
    return [calculate_peg(monthly_nwc, m, custom_value) for m in methods]
