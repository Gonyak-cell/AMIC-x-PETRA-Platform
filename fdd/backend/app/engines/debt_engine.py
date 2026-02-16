"""Net Debt 계산 엔진 — FDD-701/702/703/704.

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
    category: str  # LineItemCategory value
    amount: Decimal  # 기준일 잔액 (TB 자연 부호)
    upload_file_id: str


@dataclass(frozen=True)
class DebtOptions:
    """Net Debt 계산 옵션."""

    include_lease_liabilities: bool = False  # FDD-704: IFRS 16
    include_deferred_revenue: bool = False  # FDD-703: 선수금


@dataclass(frozen=True)
class DebtItemData:
    """Net Debt 개별 항목 (엔진 출력용)."""

    item_type: str  # DebtItemType value
    description: str
    amount: Decimal  # 양수
    source_account_code: str | None = None
    source_account_name: str | None = None
    detection_method: str = "auto_classification"
    confidence_score: Decimal = Decimal("90.00")


@dataclass
class NetDebtResult:
    """Net Debt 계산 결과."""

    gross_debt: Decimal
    cash_and_equivalents: Decimal
    net_debt: Decimal
    debt_like_total: Decimal
    cash_like_total: Decimal
    adjusted_net_debt: Decimal
    balance_check_error: Decimal
    items: list[DebtItemData]
    category_breakdown: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DebtCandidateData:
    """Debt-like 후보 (엔진 출력용) — FDD-702."""

    item_type: str
    description: str
    amount: Decimal
    detection_method: str
    confidence_score: Decimal
    source_account_code: str | None = None
    source_account_name: str | None = None


# -- Helpers ------------------------------------------------------


def _q(amount: Decimal) -> Decimal:
    """NUMERIC(18,4) 정밀도로 반올림."""
    return amount.quantize(Q4, rounding=ROUND_HALF_UP)


# -- Category Mapping ---------------------------------------------
# BS 카테고리 → DebtItemType 매핑

_GROSS_DEBT_CATEGORIES = frozenset({"DEBT"})
_CASH_CATEGORIES = frozenset({"CASH"})
_LEASE_CATEGORIES = frozenset({"LEASE_LIABILITIES"})

# Debt-like 키워드 (FDD-702)
_DEBT_LIKE_KEYWORDS: list[str] = [
    "충당부채",
    "퇴직급여",
    "장기미지급",
    "provision",
    "pension",
    "retirement benefit",
    "long-term payable",
    "deferred",
]

# 선수금/이연수익 키워드 (FDD-703)
_DEFERRED_REVENUE_KEYWORDS: list[str] = [
    "선수금",
    "선수수익",
    "이연수익",
    "계약부채",
    "deferred revenue",
    "advance from customer",
    "contract liability",
    "unearned revenue",
]


# -- FDD-701: Net Debt Calculation ---------------------------------


def calculate_net_debt(
    bs_accounts: list[BSAccountData],
    options: DebtOptions,
) -> tuple[NetDebtResult, list[EvidenceLinkData]]:
    """Net Debt를 계산한다.

    Net Debt = Gross Debt - Cash & Equivalents
    Adjusted Net Debt = Net Debt + Debt-like - Cash-like

    Args:
        bs_accounts: BS 계정 데이터 (TB 기준)
        options: 계산 옵션 (IFRS 16, deferred revenue)

    Returns:
        (NetDebtResult, evidence links)
    """
    items: list[DebtItemData] = []
    evidence: list[EvidenceLinkData] = []

    for acct in bs_accounts:
        item = _classify_account(acct, options)
        if item is not None:
            items.append(item)
            evidence.append(
                EvidenceLinkData(
                    target_type="net_debt_calculation",
                    source_type="TB",
                    source_id=acct.upload_file_id,
                    source_detail={
                        "account_code": acct.account_code,
                        "account_name": acct.account_name,
                        "amount": str(item.amount),
                        "item_type": item.item_type,
                    },
                )
            )

    # Aggregate by type
    gross_debt = _q(
        sum(
            (i.amount for i in items if i.item_type == "GROSS_DEBT"),
            Decimal("0"),
        )
    )
    cash = _q(
        sum(
            (i.amount for i in items if i.item_type == "CASH"),
            Decimal("0"),
        )
    )
    debt_like = _q(
        sum(
            (i.amount for i in items if i.item_type == "DEBT_LIKE"),
            Decimal("0"),
        )
    )
    cash_like = _q(
        sum(
            (i.amount for i in items if i.item_type == "CASH_LIKE"),
            Decimal("0"),
        )
    )

    net_debt = _q(gross_debt - cash)
    adjusted = _q(net_debt + debt_like - cash_like)

    # Balance check
    balance_error = _q(gross_debt - cash + debt_like - cash_like - adjusted)

    # Category breakdown
    cat_breakdown: dict[str, Any] = {}
    for item in items:
        if item.item_type not in cat_breakdown:
            cat_breakdown[item.item_type] = {
                "total": Decimal("0"),
                "count": 0,
                "accounts": [],
            }
        cat_breakdown[item.item_type]["total"] += item.amount
        cat_breakdown[item.item_type]["count"] += 1
        cat_breakdown[item.item_type]["accounts"].append(
            {
                "code": item.source_account_code,
                "name": item.source_account_name,
                "amount": str(item.amount),
            }
        )

    for key in cat_breakdown:
        cat_breakdown[key]["total"] = str(_q(cat_breakdown[key]["total"]))

    # Warnings
    warnings: list[str] = []
    if net_debt < Decimal("0"):
        warnings.append("DEBT_NET_NEGATIVE: Net Debt is negative (cash exceeds debt)")
    if options.include_lease_liabilities:
        warnings.append(
            "DEBT_IFRS16_INCLUDED: IFRS 16 lease liabilities included in debt-like"
        )

    result = NetDebtResult(
        gross_debt=gross_debt,
        cash_and_equivalents=cash,
        net_debt=net_debt,
        debt_like_total=debt_like,
        cash_like_total=cash_like,
        adjusted_net_debt=adjusted,
        balance_check_error=balance_error,
        items=items,
        category_breakdown=cat_breakdown,
        warnings=warnings,
    )

    return result, evidence


def _classify_account(
    acct: BSAccountData,
    options: DebtOptions,
) -> DebtItemData | None:
    """BS 계정을 Debt/Cash/Debt-like/Cash-like로 분류한다."""
    cat = acct.category
    # BS 부호: 부채는 음수 → 절대값
    abs_amount = _q(abs(acct.amount))

    if abs_amount == Decimal("0"):
        return None

    # 1. Gross Debt (DEBT category)
    if cat in _GROSS_DEBT_CATEGORIES:
        return DebtItemData(
            item_type="GROSS_DEBT",
            description=acct.account_name,
            amount=abs_amount,
            source_account_code=acct.account_code,
            source_account_name=acct.account_name,
            detection_method="auto_classification",
            confidence_score=Decimal("95.00"),
        )

    # 2. Cash & Equivalents (CASH category)
    if cat in _CASH_CATEGORIES:
        return DebtItemData(
            item_type="CASH",
            description=acct.account_name,
            amount=abs_amount,
            source_account_code=acct.account_code,
            source_account_name=acct.account_name,
            detection_method="auto_classification",
            confidence_score=Decimal("95.00"),
        )

    # 3. Lease Liabilities (FDD-704)
    if cat in _LEASE_CATEGORIES and options.include_lease_liabilities:
        return DebtItemData(
            item_type="DEBT_LIKE",
            description=f"[IFRS 16] {acct.account_name}",
            amount=abs_amount,
            source_account_code=acct.account_code,
            source_account_name=acct.account_name,
            detection_method="lease_rule",
            confidence_score=Decimal("90.00"),
        )

    # 4. Deferred Revenue (FDD-703)
    if options.include_deferred_revenue:
        combined_text = acct.account_name.lower()
        for kw in _DEFERRED_REVENUE_KEYWORDS:
            if kw.lower() in combined_text:
                return DebtItemData(
                    item_type="DEBT_LIKE",
                    description=f"[Deferred Revenue] {acct.account_name}",
                    amount=abs_amount,
                    source_account_code=acct.account_code,
                    source_account_name=acct.account_name,
                    detection_method="deferred_revenue_rule",
                    confidence_score=Decimal("75.00"),
                )

    return None


# -- FDD-702: Debt-like Candidate Detection -----------------------


def detect_debt_like_candidates(
    bs_accounts: list[BSAccountData],
    industry_context: FDDIndustryContext | None = None,
) -> list[DebtCandidateData]:
    """Debt-like / Cash-like 후보를 룰 기반으로 감지한다.

    이미 GROSS_DEBT/CASH로 분류된 항목은 제외.
    항상 옵션 무관하게 후보를 반환 (사용자가 선택).

    Args:
        bs_accounts: BS 계정 데이터
        industry_context: 산업 컨텍스트 (None이면 기존 동작)

    Returns:
        후보 리스트 (confidence DESC 정렬)
    """
    candidates: list[DebtCandidateData] = []
    skip_categories = _GROSS_DEBT_CATEGORIES | _CASH_CATEGORIES

    # 산업별 추가 키워드 구축
    extra_debt_keywords: list[str] = []
    extra_cash_keywords: list[str] = []
    if industry_context:
        for dc in industry_context.debt_classifications:
            extra_debt_keywords.extend(dc.additional_debt_like_keywords)
            extra_cash_keywords.extend(dc.additional_cash_like_keywords)

    for acct in bs_accounts:
        if acct.category in skip_categories:
            continue

        abs_amount = _q(abs(acct.amount))
        if abs_amount == Decimal("0"):
            continue

        combined_text = acct.account_name.lower()

        # Rule 1: Lease liabilities → Debt-like candidate
        if acct.category in _LEASE_CATEGORIES:
            candidates.append(
                DebtCandidateData(
                    item_type="DEBT_LIKE",
                    description=f"[IFRS 16 Lease] {acct.account_name}",
                    amount=abs_amount,
                    detection_method="lease_rule",
                    confidence_score=Decimal("90.00"),
                    source_account_code=acct.account_code,
                    source_account_name=acct.account_name,
                )
            )
            continue

        # Rule 2: Industry-specific debt-like keywords (before generic)
        matched = False
        for kw in extra_debt_keywords:
            if kw.lower() in combined_text:
                candidates.append(
                    DebtCandidateData(
                        item_type="DEBT_LIKE",
                        description=f"[Industry Debt-like: {kw}] {acct.account_name}",
                        amount=abs_amount,
                        detection_method="industry_keyword",
                        confidence_score=Decimal("75.00"),
                        source_account_code=acct.account_code,
                        source_account_name=acct.account_name,
                    )
                )
                matched = True
                break

        if matched:
            continue

        # Rule 3: Industry-specific cash-like keywords
        for kw in extra_cash_keywords:
            if kw.lower() in combined_text:
                candidates.append(
                    DebtCandidateData(
                        item_type="CASH_LIKE",
                        description=f"[Industry Cash-like: {kw}] {acct.account_name}",
                        amount=abs_amount,
                        detection_method="industry_keyword",
                        confidence_score=Decimal("70.00"),
                        source_account_code=acct.account_code,
                        source_account_name=acct.account_name,
                    )
                )
                matched = True
                break

        if matched:
            continue

        # Rule 4: Generic debt-like keyword matching
        for kw in _DEBT_LIKE_KEYWORDS:
            if kw.lower() in combined_text:
                candidates.append(
                    DebtCandidateData(
                        item_type="DEBT_LIKE",
                        description=f"[Keyword: {kw}] {acct.account_name}",
                        amount=abs_amount,
                        detection_method="keyword",
                        confidence_score=Decimal("70.00"),
                        source_account_code=acct.account_code,
                        source_account_name=acct.account_name,
                    )
                )
                break

        # Rule 5: Deferred revenue → Debt-like candidate
        for kw in _DEFERRED_REVENUE_KEYWORDS:
            if kw.lower() in combined_text:
                candidates.append(
                    DebtCandidateData(
                        item_type="DEBT_LIKE",
                        description=f"[Deferred Revenue] {acct.account_name}",
                        amount=abs_amount,
                        detection_method="deferred_revenue_rule",
                        confidence_score=Decimal("75.00"),
                        source_account_code=acct.account_code,
                        source_account_name=acct.account_name,
                    )
                )
                break

    # Sort by confidence DESC, amount DESC
    candidates.sort(key=lambda c: (c.confidence_score, c.amount), reverse=True)
    return candidates
