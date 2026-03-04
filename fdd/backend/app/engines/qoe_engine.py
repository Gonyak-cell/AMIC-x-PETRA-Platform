"""QoE (Adjusted EBITDA) 계산 엔진 — FDD-501/502/503.

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


# ── Data Types ───────────────────────────────────────────


@dataclass(frozen=True)
class CategoryTotal:
    """카테고리별 합계 (서비스 → 엔진 입력용)."""

    category: str  # LineItemCategory value
    total: Decimal
    account_count: int
    accounts: list[dict[str, Any]]  # [{code, name, amount, ...}]


@dataclass(frozen=True)
class EvidenceLinkData:
    """Evidence link data (엔진 → 서비스 출력용, DB 저장 전)."""

    target_type: str
    source_type: str  # "TB" or "GL"
    source_id: str
    source_detail: dict[str, Any] | None = None
    transaction_id: str | None = None


@dataclass
class ReportedEBITDAResult:
    """Reported EBITDA 계산 결과."""

    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    sga: Decimal
    depreciation_amortization: Decimal
    other_operating: Decimal
    operating_income: Decimal
    reported_ebitda: Decimal
    category_breakdown: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AdjustmentCandidateData:
    """조정 후보 (엔진 출력용)."""

    category: str  # AdjustmentCategory value
    description: str
    amount: Decimal
    detection_method: str
    confidence_score: Decimal
    source_account_code: str | None = None
    source_account_name: str | None = None
    source_entry_ids: list[str] | None = None


@dataclass
class QoEBridgeResult:
    """QoE Bridge 구축 결과."""

    reported_ebitda: Decimal
    adjustments: list[AdjustmentCandidateData]
    total_adjustments: Decimal
    adjusted_ebitda: Decimal
    balance_check_error: Decimal


# ── Sign Convention ──────────────────────────────────────
# TB 잔액 부호 규칙:
#   Revenue(매출) → 대변(음수) → P&L에서 양수로 부호 반전
#   COGS/SGA/D&A  → 차변(양수) → 그대로 사용
#   Other Operating Income → 대변(음수) → 양수로 반전
#
# EBITDA = Revenue - COGS - SGA + Other Operating
#        = Operating Income + D&A

_SIGN_NEGATE_CATEGORIES = frozenset(
    {
        "REVENUE",
        "OTHER_OPERATING_INCOME",
        "INTEREST_INCOME",
    }
)


def _q(amount: Decimal) -> Decimal:
    """NUMERIC(18,4) 정밀도로 반올림."""
    return amount.quantize(Q4, rounding=ROUND_HALF_UP)


# ── FDD-501: Reported EBITDA ─────────────────────────────


def calculate_reported_ebitda(
    category_totals: list[CategoryTotal],
) -> tuple[ReportedEBITDAResult, list[EvidenceLinkData]]:
    """Reported EBITDA를 계산한다.

    EBITDA = Operating Income + D&A
           = Revenue - COGS - SGA + Other Operating
    (D&A is NOT subtracted from EBITDA.)

    Args:
        category_totals: 카테고리별 합계 (TB 자연 부호).

    Returns:
        (ReportedEBITDAResult, evidence links)
    """
    # Build category map
    cat_map: dict[str, Decimal] = {}
    cat_details: dict[str, dict[str, Any]] = {}
    for ct in category_totals:
        cat_map[ct.category] = ct.total
        cat_details[ct.category] = {
            "raw_total": str(ct.total),
            "account_count": ct.account_count,
            "accounts": ct.accounts,
        }

    # Extract raw amounts (TB natural sign)
    revenue_raw = cat_map.get("REVENUE", Decimal("0"))
    cogs_raw = cat_map.get("COGS", Decimal("0"))
    sga_raw = cat_map.get("SGA", Decimal("0"))
    da_raw = cat_map.get("DEPRECIATION_AMORTIZATION", Decimal("0"))
    other_op_raw = cat_map.get("OTHER_OPERATING_INCOME", Decimal("0"))

    # Normalize signs for P&L presentation
    revenue = _q(-revenue_raw)  # 대변(음수) → 양수
    cogs = _q(cogs_raw)  # 차변(양수) → 그대로
    sga = _q(sga_raw)  # 차변(양수) → 그대로
    da = _q(da_raw)  # 차변(양수) → 그대로
    other_op = _q(-other_op_raw)  # 대변(음수) → 양수

    # Calculations
    gross_profit = _q(revenue - cogs)
    operating_income = _q(gross_profit - sga - da + other_op)
    reported_ebitda = _q(operating_income + da)

    # Warnings
    warnings: list[str] = []
    if reported_ebitda < Decimal("0"):
        warnings.append("QOE_NEGATIVE_EBITDA: Reported EBITDA is negative")

    # Evidence links — one per source TB account
    evidence: list[EvidenceLinkData] = []
    for ct in category_totals:
        for acct in ct.accounts:
            evidence.append(
                EvidenceLinkData(
                    target_type="qoe_calculation",
                    source_type="TB",
                    source_id=str(acct.get("upload_file_id", "")),
                    source_detail={
                        "account_code": acct.get("code", ""),
                        "account_name": acct.get("name", ""),
                        "amount": str(acct.get("amount", "0")),
                        "category": ct.category,
                    },
                )
            )

    result = ReportedEBITDAResult(
        revenue=revenue,
        cogs=cogs,
        gross_profit=gross_profit,
        sga=sga,
        depreciation_amortization=da,
        other_operating=other_op,
        operating_income=operating_income,
        reported_ebitda=reported_ebitda,
        category_breakdown=cat_details,
        warnings=warnings,
    )

    return result, evidence


# ── FDD-503: Adjustment Candidate Detection ──────────────

# 비경상 키워드
_NON_RECURRING_KEYWORDS: list[str] = [
    "소송",
    "구조조정",
    "일회성",
    "정리",
    "폐기",
    "처분손",
    "화재",
    "재해",
    "벌금",
    "과태료",
    "합의금",
    "위약금",
    "restructuring",
    "litigation",
    "one-time",
    "one-off",
    "write-off",
    "impairment",
    "severance",
    "settlement",
]

# 정상화 키워드 (오너/관계사)
_NORMALIZATION_KEYWORDS: list[str] = [
    "관계사",
    "특수관계",
    "임원",
    "대표이사",
    "오너",
    "related party",
    "owner",
    "director",
    "executive compensation",
]


def detect_adjustment_candidates(
    gl_entries: list[dict[str, Any]],
    non_operating_codes: set[str],
    total_revenue: Decimal,
    industry_context: FDDIndustryContext | None = None,
) -> list[AdjustmentCandidateData]:
    """조정 후보를 룰 기반으로 감지한다 (v1).

    Detection methods:
    1. industry_rule: 산업별 조정 규칙 키워드 매칭 (산업 컨텍스트 있을 때)
    2. keyword: description/account_name에 비경상 키워드 포함
    3. owner_keyword: 관계사/오너 관련 키워드 → NORMALIZATION
    4. non_operating: NON_OPERATING 계정 매핑된 항목
    5. year_end: 결산일 근처(12/28-31) 대규모 전표

    Args:
        gl_entries: GL 전표 데이터 (dict 리스트)
        non_operating_codes: 영업외 항목으로 매핑된 계정코드 set
        total_revenue: 매출 총액 (중요성 판단 기준)
        industry_context: 산업 컨텍스트 (None이면 기존 동작)

    Returns:
        조정 후보 리스트 (confidence DESC 정렬)
    """
    candidates: list[AdjustmentCandidateData] = []
    seen_entry_ids: set[str] = set()

    # 산업별 조정 규칙 → 키워드/카테고리/신뢰도 맵 구축
    industry_rules: list[tuple[list[str], str, Decimal, str]] = []
    if industry_context:
        for rule in industry_context.adjustment_rules:
            industry_rules.append(
                (
                    [kw.lower() for kw in rule.keywords],
                    rule.category,
                    rule.default_confidence,
                    rule.description_kr,
                )
            )

    # Materiality threshold: max(Revenue x 1%, 1,000,000원)
    materiality = max(
        _q(abs(total_revenue) * Decimal("0.01")),
        Decimal("1000000.0000"),
    )

    for entry in gl_entries:
        entry_id = str(entry.get("entry_id", ""))
        amount_str = str(entry.get("amount", "0"))
        amount = Decimal(amount_str) if amount_str else Decimal("0")
        abs_amount = abs(amount)
        description = str(entry.get("description", ""))
        account_name = str(entry.get("account_name", ""))
        account_code = str(entry.get("account_code", ""))
        entry_date = str(entry.get("entry_date", ""))

        if abs_amount < materiality:
            continue

        combined_text = f"{description} {account_name}".lower()

        # Method 0: Industry-specific rule matching (highest priority)
        matched = False
        if industry_rules:
            for (
                rule_keywords,
                rule_category,
                rule_confidence,
                rule_desc,
            ) in industry_rules:
                for kw in rule_keywords:
                    if kw in combined_text and entry_id not in seen_entry_ids:
                        candidates.append(
                            AdjustmentCandidateData(
                                category=rule_category,
                                description=f"[Industry: {rule_desc}] {description or account_name}",
                                amount=_q(amount),
                                detection_method="industry_rule",
                                confidence_score=rule_confidence,
                                source_account_code=account_code,
                                source_account_name=account_name,
                                source_entry_ids=[entry_id] if entry_id else None,
                            )
                        )
                        seen_entry_ids.add(entry_id)
                        matched = True
                        break
                if matched:
                    break

        if matched:
            continue

        # Method 1: Non-recurring keyword matching
        matched = False
        for kw in _NON_RECURRING_KEYWORDS:
            if kw.lower() in combined_text and entry_id not in seen_entry_ids:
                candidates.append(
                    AdjustmentCandidateData(
                        category="NON_RECURRING",
                        description=f"[Keyword: {kw}] {description or account_name}",
                        amount=_q(amount),
                        detection_method="keyword",
                        confidence_score=Decimal("70.00"),
                        source_account_code=account_code,
                        source_account_name=account_name,
                        source_entry_ids=[entry_id] if entry_id else None,
                    )
                )
                seen_entry_ids.add(entry_id)
                matched = True
                break

        if matched:
            continue

        # Method 2: Normalization keyword (owner/related party)
        for kw in _NORMALIZATION_KEYWORDS:
            if kw.lower() in combined_text and entry_id not in seen_entry_ids:
                candidates.append(
                    AdjustmentCandidateData(
                        category="NORMALIZATION",
                        description=(
                            f"[Owner/Related: {kw}] {description or account_name}"
                        ),
                        amount=_q(amount),
                        detection_method="keyword",
                        confidence_score=Decimal("60.00"),
                        source_account_code=account_code,
                        source_account_name=account_name,
                        source_entry_ids=[entry_id] if entry_id else None,
                    )
                )
                seen_entry_ids.add(entry_id)
                matched = True
                break

        if matched:
            continue

        # Method 3: Non-operating account flag
        if account_code in non_operating_codes and entry_id not in seen_entry_ids:
            candidates.append(
                AdjustmentCandidateData(
                    category="NON_OPERATING",
                    description=f"[Non-operating account] {account_name}",
                    amount=_q(amount),
                    detection_method="non_operating",
                    confidence_score=Decimal("80.00"),
                    source_account_code=account_code,
                    source_account_name=account_name,
                    source_entry_ids=[entry_id] if entry_id else None,
                )
            )
            seen_entry_ids.add(entry_id)
            continue

        # Method 4: Year-end large entries (12/28-31, >= 5x materiality)
        if (
            entry_date.endswith(("-12-28", "-12-29", "-12-30", "-12-31"))
            and abs_amount >= materiality * 5
            and entry_id not in seen_entry_ids
        ):
            candidates.append(
                AdjustmentCandidateData(
                    category="NON_RECURRING",
                    description=(
                        f"[Year-end large entry] {description or account_name}"
                    ),
                    amount=_q(amount),
                    detection_method="year_end",
                    confidence_score=Decimal("50.00"),
                    source_account_code=account_code,
                    source_account_name=account_name,
                    source_entry_ids=[entry_id] if entry_id else None,
                )
            )
            seen_entry_ids.add(entry_id)

    # Sort by confidence DESC, amount DESC
    candidates.sort(key=lambda c: (c.confidence_score, abs(c.amount)), reverse=True)
    return candidates


# ── FDD-502: QoE Bridge ──────────────────────────────────


def build_qoe_bridge(
    reported_ebitda: Decimal,
    adjustments: list[AdjustmentCandidateData],
) -> QoEBridgeResult:
    """QoE Bridge를 구축한다.

    Bridge: Reported EBITDA + Σ(Adjustments) = Adjusted EBITDA
    Balance check: error must be exactly 0.0000.

    Args:
        reported_ebitda: Reported EBITDA
        adjustments: 승인된 조정항목 리스트

    Returns:
        QoEBridgeResult with balance verification
    """
    total_adj = _q(sum((a.amount for a in adjustments), Decimal("0")))
    adjusted_ebitda = _q(reported_ebitda + total_adj)

    # Balance check: Reported + Total Adj - Adjusted should be exactly 0
    balance_error = _q(reported_ebitda + total_adj - adjusted_ebitda)

    return QoEBridgeResult(
        reported_ebitda=reported_ebitda,
        adjustments=adjustments,
        total_adjustments=total_adj,
        adjusted_ebitda=adjusted_ebitda,
        balance_check_error=balance_error,
    )
