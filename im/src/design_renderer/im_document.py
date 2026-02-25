"""IMDocumentData — IM 문서 생성을 위한 통합 입력 스키마.

모든 섹션 렌더러의 입력이 되는 단일 진실 원천(Single Source of Truth).
SPEC.md 14개 섹션 + TITAN/COVENANT 양식을 모두 표현할 수 있다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.brand_extractor.models import BrandAssets


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TransactionType(str, Enum):
    """거래 유형."""

    MA = "M&A"
    IPO = "IPO"
    INVESTMENT = "투자유치"
    SECONDARY = "구주매각"
    OTHER = "기타"


class IMStyle(str, Enum):
    """IM 양식 스타일 (섹션 구성 프리셋)."""

    TITAN = "TITAN"  # 5섹션 구성
    COVENANT = "COVENANT"  # 6섹션 구성
    FULL = "FULL"  # SPEC 14섹션 전체
    TEASER = "TEASER"  # TM (Teaser Memorandum) 고정 4그룹 구성
    CUSTOM = "CUSTOM"  # sections 필드에서 직접 지정


class Currency(str, Enum):
    """통화."""

    KRW = "KRW"
    USD = "USD"
    EUR = "EUR"


# ---------------------------------------------------------------------------
# Section IDs (동적 구성용)
# ---------------------------------------------------------------------------

SECTION_IDS = [
    "cover",
    "disclaimer",
    "toc_divider",
    "deal_overview",
    "executive_summary",
    "investment_highlights",
    "company_overview",
    "business_model",
    "market_overview",
    "business_overview",
    "value_creation",
    "growth_strategy",
    "financial_analysis",
    "valuation",
    "management_team",
    "shareholder_structure",
    "transaction_structure",
    "appendix",
    "contact",
]

# TM (Teaser Memorandum) 전용 섹션 ID
TEASER_SECTION_IDS = [
    "target_positioning",
    "market_outlook",
    "demand_driver",
    "supply_driver",
    "target_overview",
    "target_highlights",
    "proforma_plan",
    "proforma_financials",
]

# 산업별 섹션 (Phase A1)
INDUSTRY_SECTION_IDS = [
    "industry_kpi",
    "industry_overview",
]

# 전체 유효 섹션 ID (검증용)
ALL_SECTION_IDS = SECTION_IDS + TEASER_SECTION_IDS + INDUSTRY_SECTION_IDS

# 프리셋 섹션 구성
TITAN_SECTIONS = [
    "cover",
    "disclaimer",
    "toc_divider",
    "executive_summary",
    "investment_highlights",
    "market_overview",
    "business_overview",
    "financial_analysis",
    "contact",
]

COVENANT_SECTIONS = [
    "cover",
    "disclaimer",
    "toc_divider",
    "executive_summary",
    "investment_highlights",
    "value_creation",
    "company_overview",
    "market_overview",
    "financial_analysis",
    "contact",
]

# TM (Teaser Memorandum) 고정 섹션 구성
# toc_divider는 pipeline에서 각 그룹 앞에 자동 삽입
TEASER_SECTIONS = [
    "cover",
    "disclaimer",
    # Group 1: Executive Summary
    "toc_divider",  # TOC (1)
    "executive_summary",
    "target_positioning",
    "investment_highlights",
    # Group 2: Market Opportunity
    "toc_divider",  # TOC (2)
    "market_outlook",
    "demand_driver",
    "supply_driver",
    # Group 3: TARGET HIGHLIGHTS
    "toc_divider",  # TOC (3)
    "target_overview",
    "target_highlights",
    # Group 4: Financial Summary
    "toc_divider",  # TOC (4)
    "proforma_plan",
    "proforma_financials",
    # End
    "contact",
]

# TM TOC 그룹 정의 (고정 구조)
TEASER_TOC_GROUPS: list[dict[str, Any]] = [
    {
        "key": "executive_summary",
        "title": "Executive Summary",
        "subsections": [
            ("executive_summary", "Executive Summary"),
            ("target_positioning", "Target Positioning"),
            ("investment_highlights", "Investment Highlights"),
        ],
    },
    {
        "key": "market_opportunity",
        "title": "Market Opportunity",
        "subsections": [
            ("market_outlook", "Market Outlook"),
            ("demand_driver", "Key Demand Driver"),
            ("supply_driver", "Key Supply Driver"),
        ],
    },
    {
        "key": "target_highlights",
        "title": "TARGET HIGHLIGHTS",
        "subsections": [
            ("target_overview", "Target Overview"),
            ("target_highlights", "Target Highlights"),
        ],
    },
    {
        "key": "financial_summary",
        "title": "Financial Summary",
        "subsections": [
            ("proforma_plan", "대상회사 Pro-Forma 사업계획"),
            ("proforma_financials", "대상회사 Pro-Forma 재무제표"),
        ],
    },
]


# ---------------------------------------------------------------------------
# Sub-dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ContactInfo:
    """연락처 정보."""

    name: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    company: str = ""


@dataclass
class DealStructure:
    """딜 구조 정보."""

    seller: str = ""  # 매각주체
    stake_pct: Optional[float] = None  # 매각 지분율 (0~1)
    deal_background: str = ""  # 거래 배경
    timeline: Optional[dict[str, str]] = None  # {"예비입찰": "2026-03", ...}
    old_shares: Optional[float] = None  # 구주 규모 (억원)
    new_shares: Optional[float] = None  # 신주 규모 (억원)
    valuation_low: Optional[float] = None  # 밸류에이션 하한 (억원)
    valuation_high: Optional[float] = None  # 밸류에이션 상한 (억원)
    valuation_method: str = ""  # "EV/EBITDA", "PER", "DCF" 등
    transaction_type: TransactionType = TransactionType.MA


@dataclass
class FinancialStatements:
    """재무제표 데이터.

    연결/별도 재무제표, 3~5년 분량.
    각 항목은 {연도: 금액} 딕셔너리.
    """

    # 손익계산서
    revenue: dict[str, float] = field(default_factory=dict)  # {"2023": 150_000, ...}
    cost_of_goods_sold: dict[str, float] = field(default_factory=dict)
    gross_profit: dict[str, float] = field(default_factory=dict)
    operating_income: dict[str, float] = field(default_factory=dict)
    ebitda: dict[str, float] = field(default_factory=dict)
    net_income: dict[str, float] = field(default_factory=dict)
    sga_expenses: dict[str, float] = field(default_factory=dict)  # 판관비

    # 재무상태표
    total_assets: dict[str, float] = field(default_factory=dict)
    total_liabilities: dict[str, float] = field(default_factory=dict)
    total_equity: dict[str, float] = field(default_factory=dict)
    cash_and_equivalents: dict[str, float] = field(default_factory=dict)
    total_debt: dict[str, float] = field(default_factory=dict)

    # 현금흐름표
    operating_cash_flow: dict[str, float] = field(default_factory=dict)
    investing_cash_flow: dict[str, float] = field(default_factory=dict)
    financing_cash_flow: dict[str, float] = field(default_factory=dict)
    capex: dict[str, float] = field(default_factory=dict)
    free_cash_flow: dict[str, float] = field(default_factory=dict)

    # 추가 항목 (유연하게 확장)
    extra: dict[str, dict[str, float]] = field(default_factory=dict)

    @property
    def years(self) -> list[str]:
        """데이터에 포함된 연도 목록 (정렬)."""
        all_years: set[str] = set()
        for fld in [self.revenue, self.operating_income, self.net_income]:
            all_years.update(fld.keys())
        return sorted(all_years)


@dataclass
class SegmentRevenue:
    """사업부별 매출 내역."""

    segments: dict[str, dict[str, float]] = field(default_factory=dict)
    # {"IT서비스": {"2023": 80_000, "2024": 95_000}, "SI": {...}, ...}


@dataclass
class ManagementMember:
    """경영진 정보."""

    name: str = ""
    title: str = ""  # 직위
    role: str = ""  # 담당 (예: "CEO", "CFO", "CTO")
    career: list[str] = field(default_factory=list)  # 주요 경력
    photo_url: Optional[str] = None


@dataclass
class ShareholderInfo:
    """주주 정보."""

    name: str = ""
    stake_pct: float = 0.0  # 지분율 (0~1)
    share_count: Optional[int] = None
    category: str = ""  # "최대주주", "특수관계인", "기관투자자", "소액주주" 등


@dataclass
class MarketData:
    """시장 분석 데이터."""

    tam: Optional[float] = None  # 전체 시장 규모 (억원)
    sam: Optional[float] = None  # 유효 시장 규모
    som: Optional[float] = None  # 획득 가능 시장 규모
    market_growth_rate: Optional[float] = None  # 시장 성장률 (0~1)
    market_cagr: Optional[float] = None  # 시장 CAGR
    competitors: list[dict[str, Any]] = field(default_factory=list)
    # [{"name": "경쟁사A", "revenue": 50_000, "market_share": 0.15}, ...]
    industry_trends: list[str] = field(default_factory=list)
    market_position: Optional[str] = None  # 시장 내 포지셔닝
    competitive_advantages: list[str] = field(default_factory=list)  # 경쟁 우위 요소
    regulatory_notes: Optional[str] = None  # 규제 환경 상세


@dataclass
class NumberFormatConfig:
    """문서 전역 숫자 표기 설정."""

    currency: Currency = Currency.KRW
    scale: str = "억원"  # "억원" | "백만원" | "$M" | "$B"
    decimal_places_pct: int = 1  # 퍼센트 소수 자릿수
    decimal_places_amount: int = 0  # 금액 소수 자릿수
    thousands_sep: str = ","  # 천단위 구분자
    negative_format: str = "minus"  # "minus" (-100) | "parens" ((100))
    na_display: str = "N/A"  # 값 없음 표시


@dataclass
class SourceCitation:
    """출처 메타데이터."""

    source_name: str = ""  # "금융감독원 전자공시시스템", "네이버 뉴스"
    url: Optional[str] = None  # 원본 URL
    access_date: str = ""  # 접근일 "2026-02-08"
    document_title: Optional[str] = None  # 리포트명 등


@dataclass
class ChartData:
    """차트 데이터."""

    chart_type: str = ""  # "waterfall" | "combo" | "stacked_bar" | "donut" | "line" | "hbar"
    title: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class GrowthStrategy:
    """성장 전략 데이터."""

    organic_growth: list[str] = field(default_factory=list)  # 유기적 성장 포인트
    new_business: list[str] = field(default_factory=list)  # 신규 사업
    ma_targets: list[str] = field(default_factory=list)  # M&A 대상/계획
    roadmap: dict[str, list[str]] = field(default_factory=dict)
    # {"2026": ["IT서비스 확대"], "2027": ["해외 진출"], ...}


@dataclass
class CompanyOverview:
    """회사 개요 정보."""

    history: list[dict[str, str]] = field(default_factory=list)
    # [{"year": "2005", "event": "설립"}, ...]
    business_model: str = ""
    business_description: str = ""  # AI 요약 또는 사업 개요 서술
    value_chain: list[str] = field(default_factory=list)
    key_products: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    employee_count: Optional[int] = None
    headquarters: str = ""
    established_date: str = ""
    locations: list[str] = field(default_factory=list)  # 추가 사업장/지사 위치
    organization: list[str] = field(default_factory=list)  # 조직 구조 (부서 리스트)
    departments: list[dict[str, str]] = field(default_factory=list)
    # [{"name": "개발본부", "head": "홍길동", "headcount": "50명"}, ...]


@dataclass
class ValuationData:
    """밸류에이션 상세 입력 데이터.

    계산기(financial_engine.calculator.valuation) 출력 또는
    사용자 직접 입력 데이터를 저장한다.

    Attributes:
        ev: 연도별 Enterprise Value.
        equity_value: 연도별 Equity Value.
        ev_ebitda: 연도별 EV/EBITDA 배수.
        pe_ratio: 연도별 P/E Ratio.
        ev_revenue: 연도별 EV/Revenue 배수.
        irr_scenarios: 시나리오별 IRR 결과.
        moic_scenarios: 시나리오별 MOIC.
        exit_analysis: 엑싯 분석 결과.
        sensitivity_data: 민감도 히트맵 데이터.
    """

    ev: dict[str, float] = field(default_factory=dict)
    equity_value: dict[str, float] = field(default_factory=dict)
    ev_ebitda: dict[str, float] = field(default_factory=dict)
    pe_ratio: dict[str, float] = field(default_factory=dict)
    ev_revenue: dict[str, float] = field(default_factory=dict)
    irr_scenarios: dict[str, dict[str, Any]] = field(default_factory=dict)
    moic_scenarios: dict[str, float] = field(default_factory=dict)
    exit_analysis: dict[str, dict[str, Any]] = field(default_factory=dict)
    sensitivity_data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Main Document Data
# ---------------------------------------------------------------------------


@dataclass
class IMDocumentData:
    """IM 문서 생성을 위한 통합 입력 데이터.

    모든 섹션 렌더러는 이 데이터 모델에서 필요한 값을 참조한다.
    지연 바인딩 패턴: 렌더러는 데이터를 캐시하지 않고, 렌더링 시점에 항상 참조.
    """

    # ── 기본 정보 (필수) ──
    project_name: str = ""  # 프로젝트명 (예: "Project TITAN")
    company_name_kr: str = ""  # 기업명 (한글)
    company_name_en: str = ""  # 기업명 (영문)
    corp_code: str = ""  # 법인등록번호 (DART용)
    website_url: str = ""  # 홈페이지 URL (브랜드 추출용)
    date: str = ""  # IM 작성일 (예: "2026-02-08")

    # ── 섹션 구성 ──
    im_style: IMStyle = IMStyle.FULL
    sections: list[str] = field(default_factory=lambda: list(SECTION_IDS))
    # 포함할 섹션 ID 리스트 (동적 구성). im_style != CUSTOM이면 프리셋 적용.

    # ── 산업 분류 (Phase A1) ──
    industry: str = ""  # 산업 식별자 ("tech", "manufacturing", "healthcare", ...)
    industry_data: dict[str, Any] = field(default_factory=dict)
    # 산업별 추가 데이터 (KPI 값, 운영 지표 등)
    # {"arr": 50_000, "nrr": 0.95, "churn_rate": 0.05, ...}

    # ── 재무 데이터 ──
    financial_statements: FinancialStatements = field(
        default_factory=FinancialStatements
    )
    management_financials: Optional[dict[str, Any]] = None  # 관리회계 기준 상세
    segment_revenue: Optional[SegmentRevenue] = None
    key_customers: list[str] = field(default_factory=list)

    # ── 딜 구조 ──
    deal_structure: Optional[DealStructure] = None

    # ── 밸류에이션 (Phase D1) ──
    valuation_data: Optional[ValuationData] = None

    # ── 정성 데이터 ──
    company_overview: Optional[CompanyOverview] = None
    market_data: Optional[MarketData] = None
    investment_highlights: list[str] = field(default_factory=list)
    growth_strategy: Optional[GrowthStrategy] = None

    # ── 인적 자원 ──
    management_team: list[ManagementMember] = field(default_factory=list)
    org_structure: Optional[dict[str, Any]] = None  # Graphviz DOT 데이터
    shareholders: list[ShareholderInfo] = field(default_factory=list)

    # ── AI 생성 내러티브 ──
    narratives: dict[str, str] = field(default_factory=dict)
    # {"executive_summary": "...", "investment_highlights": "...", ...}

    # ── 브랜딩 ──
    brand_assets: Optional[BrandAssets] = None  # BrandAssets 인스턴스 (None→AMIC 기본)

    # ── 차트 데이터 ──
    charts: dict[str, list[ChartData]] = field(default_factory=dict)
    # {"financial_analysis": [ChartData(...)], "market_overview": [...]}

    # ── 숫자 표기 설정 ──
    number_format: NumberFormatConfig = field(default_factory=NumberFormatConfig)

    # ── 출처 메타데이터 ──
    source_citations: dict[str, list[SourceCitation]] = field(default_factory=dict)
    # {"financial_analysis": [SourceCitation(...)], ...}

    # ── 파생 지표 (자동 계산) ──
    derived_metrics: Optional[dict[str, float]] = None
    # {"revenue_cagr_3y": 0.152, "ebitda_margin_latest": 0.234, ...}

    # ── 면책조항 ──
    disclaimer_text: str = (
        "본 자료는 정보 제공 목적으로만 작성되었으며, 투자 권유를 구성하지 않습니다. "
        "본 자료에 포함된 정보의 정확성, 완전성 또는 신뢰성에 대해 어떠한 보증도 하지 않습니다."
    )

    # ── 연락처 ──
    contacts: list[ContactInfo] = field(default_factory=list)

    def __post_init__(self) -> None:
        """im_style에 따라 sections 프리셋 적용."""
        if self.im_style == IMStyle.TITAN:
            self.sections = list(TITAN_SECTIONS)
        elif self.im_style == IMStyle.COVENANT:
            self.sections = list(COVENANT_SECTIONS)
        elif self.im_style == IMStyle.FULL:
            self.sections = list(SECTION_IDS)
        elif self.im_style == IMStyle.TEASER:
            self.sections = list(TEASER_SECTIONS)
        # CUSTOM: 사용자 지정 그대로 유지

    def get_active_sections(self) -> list[str]:
        """활성화된 섹션 ID 목록 반환 (유효한 ID만 필터).

        industry가 설정된 경우, 산업별 섹션(industry_kpi, industry_overview)이
        sections에 포함되어 있지 않더라도 financial_analysis 뒤에 자동 삽입된다.
        """
        valid_ids = set(ALL_SECTION_IDS)
        active = [s for s in self.sections if s in valid_ids]

        # 산업 모듈 활성화 시, 산업별 섹션 자동 추가
        if self.industry:
            offset = 0
            for sec_id in INDUSTRY_SECTION_IDS:
                if sec_id not in active:
                    try:
                        idx = active.index("financial_analysis") + 1 + offset
                    except ValueError:
                        idx = max(len(active) - 1, 0) + offset
                    active.insert(idx, sec_id)
                    offset += 1

        return active

    def compute_derived_metrics(self) -> None:
        """financial_statements에서 CAGR, YoY, 마진율 등 파생 지표 일괄 계산.

        계산된 지표는 self.derived_metrics에 저장되며,
        모든 섹션 렌더러가 공유한다.
        """
        fs = self.financial_statements
        years = fs.years
        metrics: dict[str, float] = {}

        if len(years) >= 2:
            # YoY 성장률 (최신 연도)
            latest, prev = years[-1], years[-2]
            if fs.revenue.get(prev) and fs.revenue.get(latest):
                metrics["revenue_yoy"] = (
                    fs.revenue[latest] - fs.revenue[prev]
                ) / abs(fs.revenue[prev])
            if fs.operating_income.get(prev) and fs.operating_income.get(latest):
                metrics["operating_income_yoy"] = (
                    fs.operating_income[latest] - fs.operating_income[prev]
                ) / abs(fs.operating_income[prev])
            if fs.net_income.get(prev) and fs.net_income.get(latest):
                metrics["net_income_yoy"] = (
                    fs.net_income[latest] - fs.net_income[prev]
                ) / abs(fs.net_income[prev])

        if len(years) >= 3:
            # CAGR (3년)
            first, last = years[-3], years[-1]
            if fs.revenue.get(first) and fs.revenue.get(last) and fs.revenue[first] > 0:
                metrics["revenue_cagr_3y"] = (
                    fs.revenue[last] / fs.revenue[first]
                ) ** (1.0 / 2) - 1

        if len(years) >= 5:
            # CAGR (5년)
            first, last = years[-5], years[-1]
            if fs.revenue.get(first) and fs.revenue.get(last) and fs.revenue[first] > 0:
                metrics["revenue_cagr_5y"] = (
                    fs.revenue[last] / fs.revenue[first]
                ) ** (1.0 / 4) - 1

        # 마진율 (최신 연도)
        if years:
            latest = years[-1]
            rev = fs.revenue.get(latest, 0)
            if rev and rev > 0:
                if fs.gross_profit.get(latest) is not None:
                    metrics["gross_margin_latest"] = fs.gross_profit[latest] / rev
                if fs.operating_income.get(latest) is not None:
                    metrics["operating_margin_latest"] = (
                        fs.operating_income[latest] / rev
                    )
                if fs.ebitda.get(latest) is not None:
                    metrics["ebitda_margin_latest"] = fs.ebitda[latest] / rev
                if fs.net_income.get(latest) is not None:
                    metrics["net_margin_latest"] = fs.net_income[latest] / rev

            # 부채비율
            equity = fs.total_equity.get(latest, 0)
            if equity and equity > 0:
                if fs.total_liabilities.get(latest) is not None:
                    metrics["debt_to_equity_latest"] = (
                        fs.total_liabilities[latest] / equity
                    )

        self.derived_metrics = metrics

    def validate_consistency(
        self, rendered_values: dict[str, list[tuple[str, Any]]]
    ) -> list[str]:
        """렌더링된 슬라이드들에서 동일 지표의 값 불일치 검출.

        Args:
            rendered_values: {지표명: [(섹션명, 값), ...]} 형태.
                예: {"revenue_2024": [("exec_summary", 15000), ("financial", 15000)]}

        Returns:
            불일치 경고 메시지 리스트. 빈 리스트면 일관성 통과.
        """
        warnings: list[str] = []
        for metric_name, occurrences in rendered_values.items():
            if len(occurrences) < 2:
                continue
            values = [v for _, v in occurrences]
            first_val = values[0]
            for section_name, val in occurrences[1:]:
                if val != first_val:
                    first_section = occurrences[0][0]
                    warnings.append(
                        f"불일치 감지: '{metric_name}' — "
                        f"'{first_section}'={first_val} vs "
                        f"'{section_name}'={val}"
                    )
        return warnings
