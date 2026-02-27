"""연결(Consolidation) 엔진 — Sprint 16 → Phase 3 확장.

멀티 엔티티 재무 데이터를 연결 기준으로 합산하고,
내부거래(IC) 제거 및 소수지분(minority interest)을 반영한다.

Phase 3 추가:
- IC 자동 감지 (GL 거래처 매칭 기반)
- FX 환율 변환 (원화 환산)
- 엔티티별 P&L 비교 분석

Pure function — DB 접근 없음.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

ENGINE_VERSION = "0.2.0"


@dataclass(frozen=True)
class EntityAccountData:
    """엔티티별 계정 데이터."""

    entity_id: str
    entity_code: str
    account_code: str
    account_name: str
    category: str
    amount: Decimal  # presentation currency로 변환 완료
    monthly_amounts: dict[str, Decimal] = field(default_factory=dict)


@dataclass(frozen=True)
class EliminationEntry:
    """내부거래 제거 항목."""

    description: str
    debit_entity: str
    credit_entity: str
    amount: Decimal
    account_category: str


@dataclass
class ConsolidationResult:
    """연결 분석 결과."""

    consolidated_totals: dict[str, Decimal]  # {category: total}
    entity_subtotals: dict[str, dict[str, Decimal]]  # {entity_code: {category: total}}
    eliminations: list[EliminationEntry]
    elimination_total: Decimal
    minority_interest: Decimal
    warnings: list[str]


@dataclass(frozen=True)
class EvidenceLinkData:
    """근거 링크 데이터."""

    source_type: str
    source_id: str
    label: str
    detail: str


def consolidate_entities(
    entity_accounts: dict[str, list[EntityAccountData]],
    ownership_pcts: dict[str, Decimal],
    ic_pairs: list[tuple[str, str, str, Decimal]] | None = None,
) -> tuple[ConsolidationResult, list[EvidenceLinkData]]:
    """엔티티별 데이터를 연결 기준으로 합산한다.

    Args:
        entity_accounts: {entity_id: [EntityAccountData, ...]}
        ownership_pcts: {entity_id: Decimal("100.0000")} — 지분율
        ic_pairs: [(debit_entity, credit_entity, category, amount), ...]
            수동 지정 내부거래 제거 항목 (v1: 수동만 지원)

    Returns:
        (ConsolidationResult, evidence_links)
    """
    warnings: list[str] = []
    evidence: list[EvidenceLinkData] = []

    # 1. 엔티티별 카테고리 소계 계산
    entity_subtotals: dict[str, dict[str, Decimal]] = {}
    all_categories: set[str] = set()

    for entity_id, accounts in entity_accounts.items():
        subtotals: dict[str, Decimal] = {}
        for acct in accounts:
            all_categories.add(acct.category)
            subtotals[acct.category] = (
                subtotals.get(acct.category, Decimal("0")) + acct.amount
            )

        entity_subtotals[accounts[0].entity_code if accounts else entity_id] = subtotals

    # 2. 단순 합산 (IC 제거 전)
    consolidated: dict[str, Decimal] = {}
    for cat in sorted(all_categories):
        total = Decimal("0")
        for subtotals in entity_subtotals.values():
            total += subtotals.get(cat, Decimal("0"))
        consolidated[cat] = total

    # 3. IC 제거 (수동 지정)
    eliminations: list[EliminationEntry] = []
    elimination_total = Decimal("0")

    if ic_pairs:
        for debit_entity, credit_entity, category, amount in ic_pairs:
            entry = EliminationEntry(
                description=f"IC elimination: {debit_entity} ↔ {credit_entity}",
                debit_entity=debit_entity,
                credit_entity=credit_entity,
                amount=amount,
                account_category=category,
            )
            eliminations.append(entry)
            elimination_total += amount

            # 연결 합산에서 IC 금액 차감
            if category in consolidated:
                consolidated[category] -= amount

            evidence.append(
                EvidenceLinkData(
                    source_type="ic_elimination",
                    source_id=f"{debit_entity}:{credit_entity}:{category}",
                    label=f"IC 제거: {category}",
                    detail=f"{debit_entity} ↔ {credit_entity}, {amount}",
                )
            )

    # 4. 소수지분(minority interest) 계산
    minority_interest = Decimal("0")
    for entity_id, accounts in entity_accounts.items():
        pct = ownership_pcts.get(entity_id, Decimal("100.0000"))
        if pct < Decimal("100.0000"):
            minority_pct = (Decimal("100.0000") - pct) / Decimal("100")
            entity_total = sum(a.amount for a in accounts)
            mi = (entity_total * minority_pct).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
            minority_interest += mi

            entity_code = accounts[0].entity_code if accounts else entity_id
            warnings.append(
                f"Entity {entity_code}: {pct}% ownership, minority interest = {mi}"
            )

    evidence.append(
        EvidenceLinkData(
            source_type="consolidation",
            source_id="summary",
            label="연결 분석 요약",
            detail=(
                f"엔티티 {len(entity_accounts)}개, "
                f"IC 제거 {len(eliminations)}건 ({elimination_total}), "
                f"소수지분 {minority_interest}"
            ),
        )
    )

    return (
        ConsolidationResult(
            consolidated_totals=consolidated,
            entity_subtotals=entity_subtotals,
            eliminations=eliminations,
            elimination_total=elimination_total,
            minority_interest=minority_interest,
            warnings=warnings,
        ),
        evidence,
    )


# ── IC 자동 감지 ─────────────────────────────────────────


@dataclass(frozen=True)
class ICCandidate:
    """IC 자동 감지 후보."""

    entity_a: str
    entity_b: str
    category: str
    amount_a: Decimal     # A가 인식한 금액
    amount_b: Decimal     # B가 인식한 금액 (부호 반대)
    difference: Decimal   # 불일치 금액
    confidence: str       # "HIGH", "MEDIUM", "LOW"


def detect_ic_transactions(
    entity_accounts: dict[str, list[EntityAccountData]],
    *,
    entity_names: dict[str, str] | None = None,
    tolerance_pct: Decimal = Decimal("5"),
) -> tuple[list[ICCandidate], list[EvidenceLinkData]]:
    """GL 거래처명 매칭 기반 IC 거래 자동 감지.

    두 엔티티가 동일 카테고리에서 상호 대칭적(매출↔매입 등) 거래를
    인식하면 IC 후보로 판정한다.

    Args:
        entity_accounts: {entity_id: [EntityAccountData, ...]}
        entity_names: {entity_code: entity_name} — 거래처명 매칭에 사용
        tolerance_pct: 금액 불일치 허용률 (%, 기본 5%)

    Returns:
        (list[ICCandidate], list[EvidenceLinkData])
    """
    evidence: list[EvidenceLinkData] = []
    entity_codes = list(entity_accounts.keys())
    names = entity_names or {}

    # 카테고리 쌍: 매출↔매입, AR↔AP 등
    _IC_CATEGORY_PAIRS = [
        ("REVENUE", "COGS"),
        ("REVENUE", "COST_OF_SALES"),
        ("AR", "AP"),
        ("TRADE_RECEIVABLES", "TRADE_PAYABLES"),
        ("OTHER_RECEIVABLES", "OTHER_PAYABLES"),
        ("INTEREST_INCOME", "INTEREST_EXPENSE"),
    ]

    # 엔티티별 카테고리 합산
    entity_cat_totals: dict[str, dict[str, Decimal]] = {}
    for eid, accounts in entity_accounts.items():
        code = accounts[0].entity_code if accounts else eid
        totals: dict[str, Decimal] = {}
        for acct in accounts:
            totals[acct.category] = totals.get(acct.category, Decimal("0")) + acct.amount
        entity_cat_totals[code] = totals

    candidates: list[ICCandidate] = []
    seen: set[tuple[str, str, str]] = set()

    codes = list(entity_cat_totals.keys())
    for i, code_a in enumerate(codes):
        for code_b in codes[i + 1:]:
            for cat_a, cat_b in _IC_CATEGORY_PAIRS:
                # A의 매출 vs B의 매입 (또는 반대)
                for (c1, c2), (e1, e2) in [
                    ((cat_a, cat_b), (code_a, code_b)),
                    ((cat_a, cat_b), (code_b, code_a)),
                ]:
                    key = tuple(sorted([e1, e2])) + (c1,)
                    if key in seen:
                        continue

                    amt_a = abs(entity_cat_totals.get(e1, {}).get(c1, Decimal("0")))
                    amt_b = abs(entity_cat_totals.get(e2, {}).get(c2, Decimal("0")))

                    if amt_a == Decimal("0") or amt_b == Decimal("0"):
                        continue

                    diff = abs(amt_a - amt_b)
                    ref_amt = max(amt_a, amt_b)
                    diff_pct = diff / ref_amt * Decimal("100") if ref_amt > Decimal("0") else Decimal("0")

                    if diff_pct <= tolerance_pct:
                        confidence = "HIGH" if diff_pct <= Decimal("1") else "MEDIUM"
                        seen.add(key)
                        candidates.append(ICCandidate(
                            entity_a=e1,
                            entity_b=e2,
                            category=c1,
                            amount_a=amt_a.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
                            amount_b=amt_b.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
                            difference=diff.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
                            confidence=confidence,
                        ))

                        evidence.append(EvidenceLinkData(
                            source_type="ic_detection",
                            source_id=f"ic:{e1}:{e2}:{c1}",
                            label=f"IC 후보: {e1}↔{e2} ({c1})",
                            detail=f"A={amt_a}, B={amt_b}, diff={diff_pct:.2f}%",
                        ))

    return candidates, evidence


# ── FX 환율 변환 ─────────────────────────────────────────


@dataclass(frozen=True)
class FXRate:
    """환율 정보."""

    source_currency: str          # "USD", "EUR" 등
    target_currency: str          # "KRW"
    period_end_rate: Decimal      # 기말 환율 (BS용)
    average_rate: Decimal         # 평균 환율 (IS용)
    period: str = ""              # "FY2024"


@dataclass
class FXConversionResult:
    """FX 변환 결과."""

    converted_accounts: list[EntityAccountData]
    fx_impact_by_entity: dict[str, Decimal]     # 환산 차이
    fx_rates_used: list[FXRate]
    warnings: list[str] = field(default_factory=list)


# BS vs IS 카테고리 분류
_IS_CATEGORIES = frozenset({
    "REVENUE", "COGS", "COST_OF_SALES", "SGA", "OPERATING_INCOME",
    "INTEREST_INCOME", "INTEREST_EXPENSE", "OTHER_INCOME", "OTHER_EXPENSE",
    "TAX_EXPENSE", "NET_INCOME", "DEPRECIATION", "AMORTIZATION",
    "PERSONNEL_COST", "RENT_EXPENSE", "MARKETING_EXPENSE",
})


def convert_fx(
    entity_accounts: list[EntityAccountData],
    fx_rate: FXRate,
    *,
    is_categories: frozenset[str] | None = None,
) -> tuple[FXConversionResult, list[EvidenceLinkData]]:
    """외화 계정을 표시 통화로 환산한다.

    BS 항목 → 기말환율, IS 항목 → 평균환율.

    Args:
        entity_accounts: 외화 기준 계정 데이터
        fx_rate: 적용 환율
        is_categories: IS 카테고리 집합 (없으면 기본값 사용)

    Returns:
        (FXConversionResult, list[EvidenceLinkData])
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []
    is_cats = is_categories or _IS_CATEGORIES

    converted: list[EntityAccountData] = []
    fx_impact: dict[str, Decimal] = {}

    for acct in entity_accounts:
        rate = fx_rate.average_rate if acct.category in is_cats else fx_rate.period_end_rate
        original = acct.amount
        converted_amount = (original * rate).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP,
        )

        # 월별 금액도 변환
        converted_monthly: dict[str, Decimal] = {}
        for m, amt in acct.monthly_amounts.items():
            converted_monthly[m] = (amt * fx_rate.average_rate).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP,
            )

        converted.append(EntityAccountData(
            entity_id=acct.entity_id,
            entity_code=acct.entity_code,
            account_code=acct.account_code,
            account_name=acct.account_name,
            category=acct.category,
            amount=converted_amount,
            monthly_amounts=converted_monthly,
        ))

        # FX impact 누적
        ecode = acct.entity_code
        fx_impact[ecode] = fx_impact.get(ecode, Decimal("0")) + converted_amount

    if fx_rate.period_end_rate != fx_rate.average_rate and fx_rate.average_rate != Decimal("0"):
        diff_pct = abs(fx_rate.period_end_rate - fx_rate.average_rate) / fx_rate.average_rate * Decimal("100")
        if diff_pct > Decimal("10"):
            warnings.append(
                f"FX_RATE_DIVERGENCE: End rate vs avg rate differs by {diff_pct:.1f}% "
                f"for {fx_rate.source_currency}"
            )

    evidence.append(EvidenceLinkData(
        source_type="fx_conversion",
        source_id=f"fx:{fx_rate.source_currency}:{fx_rate.target_currency}",
        label=f"FX 변환: {fx_rate.source_currency} → {fx_rate.target_currency}",
        detail=(
            f"기말={fx_rate.period_end_rate}, 평균={fx_rate.average_rate}, "
            f"변환 계정 {len(converted)}건"
        ),
    ))

    return FXConversionResult(
        converted_accounts=converted,
        fx_impact_by_entity=fx_impact,
        fx_rates_used=[fx_rate],
        warnings=warnings,
    ), evidence


# ── 엔티티별 P&L 비교 ───────────────────────────────────


@dataclass
class EntityPLComparison:
    """엔티티별 P&L 비교 결과."""

    entity_codes: list[str]
    categories: list[str]
    amounts: dict[str, dict[str, Decimal]]  # {entity_code: {category: amount}}
    shares: dict[str, dict[str, Decimal]]   # {entity_code: {category: share%}}
    total_row: dict[str, Decimal]           # {category: consolidated_total}
    warnings: list[str] = field(default_factory=list)


def compare_entity_pl(
    entity_accounts: dict[str, list[EntityAccountData]],
    *,
    categories: list[str] | None = None,
) -> tuple[EntityPLComparison, list[EvidenceLinkData]]:
    """엔티티별 P&L을 비교 분석한다.

    Args:
        entity_accounts: {entity_id: [EntityAccountData, ...]}
        categories: 비교할 카테고리 목록 (없으면 자동 감지)

    Returns:
        (EntityPLComparison, list[EvidenceLinkData])
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []

    # 엔티티별 카테고리 합산
    entity_totals: dict[str, dict[str, Decimal]] = {}
    all_cats: set[str] = set()

    for entity_id, accounts in entity_accounts.items():
        code = accounts[0].entity_code if accounts else entity_id
        totals: dict[str, Decimal] = {}
        for acct in accounts:
            all_cats.add(acct.category)
            totals[acct.category] = totals.get(acct.category, Decimal("0")) + acct.amount
        entity_totals[code] = totals

    cat_list = categories or sorted(all_cats)
    entity_codes = sorted(entity_totals.keys())

    # 연결 합계
    total_row: dict[str, Decimal] = {}
    for cat in cat_list:
        total_row[cat] = sum(
            entity_totals.get(ec, {}).get(cat, Decimal("0"))
            for ec in entity_codes
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    # 엔티티별 비중
    shares: dict[str, dict[str, Decimal]] = {}
    for ec in entity_codes:
        shares[ec] = {}
        for cat in cat_list:
            amt = entity_totals.get(ec, {}).get(cat, Decimal("0"))
            total = total_row.get(cat, Decimal("0"))
            if total != Decimal("0"):
                shares[ec][cat] = (amt / total * Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP,
                )
            else:
                shares[ec][cat] = Decimal("0")

    # 지배적 엔티티 경고
    for cat in cat_list:
        for ec in entity_codes:
            share_val = shares.get(ec, {}).get(cat, Decimal("0"))
            if abs(share_val) > Decimal("90") and len(entity_codes) > 1:
                warnings.append(
                    f"ENTITY_DOMINANT: {ec} accounts for {share_val}% of {cat}"
                )

    evidence.append(EvidenceLinkData(
        source_type="entity_comparison",
        source_id="pl_comparison",
        label="엔티티별 P&L 비교",
        detail=f"엔티티 {len(entity_codes)}개, 카테고리 {len(cat_list)}개",
    ))

    return EntityPLComparison(
        entity_codes=entity_codes,
        categories=cat_list,
        amounts=entity_totals,
        shares=shares,
        total_row=total_row,
        warnings=warnings,
    ), evidence
