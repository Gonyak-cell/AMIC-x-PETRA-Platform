"""Consolidation (연결 분석) Pydantic 스키마 — Sprint 16."""

from decimal import Decimal

from pydantic import BaseModel, Field


class ICPairInput(BaseModel):
    """내부거래(IC) 제거 항목 입력."""

    debit_entity: str = Field(..., description="차변 엔티티 코드")
    credit_entity: str = Field(..., description="대변 엔티티 코드")
    category: str = Field(..., description="표준 라인아이템 카테고리 (e.g. AR)")
    amount: Decimal = Field(..., gt=Decimal("0"))


class ConsolidationRequest(BaseModel):
    """연결 분석 실행 요청."""

    ic_pairs: list[ICPairInput] | None = None


class EliminationEntryRead(BaseModel):
    """IC 제거 항목 응답."""

    description: str
    debit_entity: str
    credit_entity: str
    amount: Decimal
    account_category: str


class ConsolidationResultRead(BaseModel):
    """연결 분석 결과 응답."""

    consolidated_totals: dict[str, Decimal]
    entity_subtotals: dict[str, dict[str, Decimal]]
    eliminations: list[EliminationEntryRead]
    elimination_total: Decimal
    minority_interest: Decimal
    warnings: list[str]


class EntitySummary(BaseModel):
    """연결 분석용 엔티티 요약."""

    id: str
    code: str
    name: str
    entity_type: str
    functional_currency: str
    ownership_pct: Decimal | None
