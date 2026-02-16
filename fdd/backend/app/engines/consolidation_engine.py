"""연결(Consolidation) 엔진 — Sprint 16.

멀티 엔티티 재무 데이터를 연결 기준으로 합산하고,
내부거래(IC) 제거 및 소수지분(minority interest)을 반영한다.

Pure function — DB 접근 없음.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

ENGINE_VERSION = "0.1.0"


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

        entity_subtotals[acct.entity_code if accounts else entity_id] = subtotals

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
