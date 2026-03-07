"""딜 셋업 AI 에이전트 — Pydantic 스키마."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models.enums import (
    BuyerTier,
    BuyerType,
    DDWorkstream,
    DealStructure,
    DealType,
    TransactionSide,
)

# ── 요청 ──────────────────────────────────────────────────


class DealSetupRequest(BaseModel):
    """자연어 딜 설명으로 AI 미리보기 요청."""

    description: str = Field(..., min_length=10, max_length=10000)
    lead_advisor_email: str = Field(
        ...,
        max_length=255,
        pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
    )


# ── AI 추출 미리보기 하위 구조 ─────────────────────────────


class DealSetupTransaction(BaseModel):
    """AI가 추출한 거래 기본 정보."""

    name: str
    deal_type: DealType
    side: TransactionSide
    target_company_name: str
    client_name: str
    estimated_deal_value: float | None = None
    currency: str = "KRW"
    deal_structure: DealStructure | None = None
    industry: str | None = None
    target_close_date: str | None = None
    notes: str | None = None


class DealSetupDDItem(BaseModel):
    """AI가 생성한 DD 체크리스트 항목."""

    workstream: DDWorkstream
    title: str
    description: str | None = None
    due_date: str | None = None


class DealSetupTimelineItem(BaseModel):
    """AI가 생성한 타임라인 이벤트."""

    event_type: str
    title: str
    description: str | None = None
    event_date: str


class DealSetupBuyerItem(BaseModel):
    """AI가 생성한 매수 후보."""

    company_name: str
    buyer_type: BuyerType | None = None
    tier: BuyerTier | None = None
    notes: str | None = None


# ── AI 미리보기 응답 ──────────────────────────────────────


class DealSetupPreview(BaseModel):
    """AI가 추출한 딜 구조 미리보기 — DB 저장 전 사용자 확인용."""

    transaction: DealSetupTransaction
    dd_checklist: list[DealSetupDDItem]
    timeline: list[DealSetupTimelineItem]
    buyer_candidates: list[DealSetupBuyerItem]
    cost_usd: float
    model_used: str


# ── 확인 후 저장 요청 ─────────────────────────────────────


class DealSetupConfirm(BaseModel):
    """사용자가 편집/확인 후 DB 저장 요청."""

    transaction: DealSetupTransaction
    dd_checklist: list[DealSetupDDItem]
    timeline: list[DealSetupTimelineItem]
    buyer_candidates: list[DealSetupBuyerItem]
    lead_advisor_email: str = Field(
        ...,
        max_length=255,
        pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
    )


# ── 저장 결과 ─────────────────────────────────────────────


class DealSetupResult(BaseModel):
    """DB 저장 결과."""

    transaction_id: uuid.UUID
    dd_checklist_count: int
    timeline_count: int
    buyer_count: int
