"""SI 매핑 관련 Pydantic 스키마."""

from __future__ import annotations

import re
import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

# ── 요청 ──────────────────────────────────────────────────
_KSIC_CODE_RE = re.compile(r"^[A-Za-z0-9]{1,10}$")


class SIMappingRequest(BaseModel):
    """SI 매핑 실행 요청."""

    ksic_codes: list[str] = Field(..., min_length=1, max_length=20)

    @field_validator("ksic_codes", mode="after")
    @classmethod
    def validate_ksic_elements(cls, codes: list[str]) -> list[str]:
        """각 KSIC 코드가 영숫자 1~10자리인지 검증."""
        for code in codes:
            if not _KSIC_CODE_RE.match(code):
                msg = f"KSIC 코드는 영숫자 1~10자리여야 합니다: {code!r}"
                raise ValueError(msg)
        return codes

    top_n: int = Field(default=5, ge=1, le=20)
    max_companies_per_panel: int = Field(default=50, ge=1, le=200)
    min_revenue: Decimal | None = Field(
        default=None, description="최소 매출액 필터 (원 단위, 예: 10_000_000_000 = 100억원)"
    )
    require_investment_history: bool = False


class BulkAddBuyersRequest(BaseModel):
    """SI 매핑 결과를 BuyerCandidate로 일괄 등록."""

    si_company_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100)


# ── 응답: SI 기업 ─────────────────────────────────────────
class SICompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    ksic_codes: list[str] | None = None
    revenue: Decimal | None = None
    revenue_year: int | None = None
    has_investment_history: bool = False
    description: str | None = None

    # 재무정보 (금융위 getSummFinaStat_V2)
    operating_profit: Decimal | None = None
    net_income: Decimal | None = None
    total_assets: Decimal | None = None
    total_debt: Decimal | None = None
    total_equity: Decimal | None = None
    capital_amount: Decimal | None = None
    debt_ratio: Decimal | None = None
    pretax_income: Decimal | None = None

    # 기업기본정보 (금융위 getCorpOutline_V2)
    representative: str | None = None
    founded_date: str | None = None
    address: str | None = None
    homepage: str | None = None
    employee_count: str | None = None
    industry_name: str | None = None
    main_business: str | None = None
    market_type: str | None = None
    market_type_name: str | None = None

    @field_serializer(
        "revenue",
        "operating_profit",
        "net_income",
        "total_assets",
        "total_debt",
        "total_equity",
        "capital_amount",
        "debt_ratio",
        "pretax_income",
    )
    @classmethod
    def _serialize_decimal(cls, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class SICandidateOut(BaseModel):
    """플랫 후보 — 테이블 렌더링용."""

    company: SICompanyOut
    relation: Literal["DIRECT", "BACKWARD", "FORWARD"]
    io_code: str | None = None
    io_name: str | None = None
    transaction_value: Decimal | None = None

    @field_serializer("transaction_value")
    @classmethod
    def _serialize_decimal(cls, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


# ── 응답: Value Chain 패널 ────────────────────────────────
class ValueChainPanel(BaseModel):
    """IO 코드 단위 패널 (전방/후방 각각)."""

    io_code: str
    io_name: str
    transaction_value: Decimal
    companies: list[SICompanyOut] = []

    @field_serializer("transaction_value")
    @classmethod
    def _serialize_decimal(cls, v: Decimal) -> str:
        return str(v)


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
    revenue_count: int = 0
    fina_stat_count: int = 0
    corp_basic_count: int = 0
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
    revenue: Decimal | None = None
    operating_income: Decimal | None = None
    net_income: Decimal | None = None
    total_assets: Decimal | None = None

    @field_serializer("revenue", "operating_income", "net_income", "total_assets")
    @classmethod
    def _serialize_decimal(cls, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


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


# ── ValueChain (VC) 매핑 스키마 ────────────────────────────


class VcChainCompany(BaseModel):
    """Value Chain 후보 기업."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    industry_name: str
    io_sector_name: str | None = None
    corp_type: str | None = None
    revenue: Decimal | None = None
    listing_code: str | None = None

    @field_serializer("revenue")
    @classmethod
    def _serialize_revenue(cls, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class VcChainPanel(BaseModel):
    """업종 단위 패널 (전방/후방 각각)."""

    industry_name: str
    coefficient: Decimal
    companies: list[VcChainCompany] = []

    @field_serializer("coefficient")
    @classmethod
    def _serialize_coefficient(cls, v: Decimal) -> str:
        return str(v)


class VcMappingResponse(BaseModel):
    """ValueChain 매핑 전체 결과."""

    target_industry: str
    forward_chains: list[VcChainPanel]
    backward_chains: list[VcChainPanel]
    competitors: list[VcChainCompany]
    total_forward: int
    total_backward: int
    total_competitors: int


class VcIndustrySuggestion(BaseModel):
    """업종명(1,574) 자동완성 결과."""

    industry_name: str
    company_count: int


class VcDataStats(BaseModel):
    """ValueChain 데이터 시딩 상태."""

    vc_companies_count: int
    vc_coefficients_count: int
    revenue_count: int
    is_seeded: bool


# ── 등록번호 기반 VC 매핑 ─────────────────────────────────


class VcCompanyLookupResult(BaseModel):
    """등록번호로 조회된 VC 기업 정보."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    industry_name: str
    io_sector_name: str | None = None
    corp_reg_no: str | None = None
    biz_reg_no: str | None = None
    revenue: Decimal | None = None

    @field_serializer("revenue")
    @classmethod
    def _serialize_revenue(cls, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class VcMappingByRegResponse(BaseModel):
    """등록번호 기반 VC 매핑 결과 (기업 정보 + 매핑 결과)."""

    company: VcCompanyLookupResult
    mapping: VcMappingResponse


class BulkAddVcBuyersRequest(BaseModel):
    """VC 매핑 결과 → BuyerCandidate 일괄 등록."""

    vc_company_ids: list[int] = Field(..., min_length=1, max_length=100)
