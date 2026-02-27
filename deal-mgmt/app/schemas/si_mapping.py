"""SI 매핑 관련 Pydantic 스키마."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


# ── 요청 ──────────────────────────────────────────────────
class SIMappingRequest(BaseModel):
    """SI 매핑 실행 요청."""

    ksic_codes: list[str] = Field(..., min_length=1)
    top_n: int = Field(default=5, ge=1, le=20)
    max_companies_per_panel: int = Field(default=50, ge=1, le=200)
    min_revenue: float | None = Field(default=None)
    require_investment_history: bool = False


class BulkAddBuyersRequest(BaseModel):
    """SI 매핑 결과를 BuyerCandidate로 일괄 등록."""

    si_company_ids: list[uuid.UUID] = Field(..., min_length=1)


# ── 응답: SI 기업 ─────────────────────────────────────────
class SICompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    ksic_codes: list[str] | None = None
    revenue: float | None = None
    has_investment_history: bool = False
    description: str | None = None


class SICandidateOut(BaseModel):
    """플랫 후보 — 테이블 렌더링용."""

    company: SICompanyOut
    relation: str  # DIRECT | BACKWARD | FORWARD
    io_code: str | None = None
    io_name: str | None = None
    transaction_value: float | None = None


# ── 응답: Value Chain 패널 ────────────────────────────────
class ValueChainPanel(BaseModel):
    """IO 코드 단위 패널 (전방/후방 각각)."""

    io_code: str
    io_name: str
    transaction_value: float
    companies: list[SICompanyOut] = []


class SIMappingResponse(BaseModel):
    """SI 매핑 전체 결과."""

    target_ksic_codes: list[str]
    target_io_codes: list[str]
    direct_peers: list[SICompanyOut]
    backward_chain: list[ValueChainPanel]
    forward_chain: list[ValueChainPanel]
    all_candidates: list[SICandidateOut]


# ── 일괄 등록 결과 ────────────────────────────────────────
class BulkAddBuyersResponse(BaseModel):
    added_count: int
    skipped_count: int
    buyer_ids: list[uuid.UUID]


# ── KSIC 자동완성 ─────────────────────────────────────────
class KsicSuggestion(BaseModel):
    code: str
    name: str


# ── 데이터 통계 ───────────────────────────────────────────
class SIDataStats(BaseModel):
    si_companies_count: int
    ksic_io_mappings_count: int
    io_transactions_count: int
    is_seeded: bool


# ── 딥다이브 ───────────────────────────────────────────────
class CompanyOverview(BaseModel):
    """DART 기업개황."""

    corp_code: str
    corp_name: str
    ceo_nm: str = ""
    est_dt: str = ""
    induty_code: str = ""
    adres: str = ""
    hm_url: str = ""


class FinancialSummary(BaseModel):
    """연도별 재무 요약."""

    bsns_year: str
    revenue: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    total_assets: float | None = None


class DeepDiveDisclosure(BaseModel):
    """공시 항목."""

    rcept_dt: str
    report_nm: str
    rcept_no: str


class SanctionItem(BaseModel):
    """제재 항목."""

    date: str
    type: str
    content: str


class DeepDiveResponse(BaseModel):
    """SI 기업 딥다이브 결과."""

    company: SICompanyOut
    overview: CompanyOverview | None = None
    financials: list[FinancialSummary] = []
    disclosures: list[DeepDiveDisclosure] = []
    sanctions: list[SanctionItem] = []
    dart_available: bool = False
