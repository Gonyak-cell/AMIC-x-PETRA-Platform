"""DocumentRenderingSpec — JSON → IMDocumentData 변환 스키마.

외부 JSON 입력을 Pydantic 모델로 검증한 후 IMDocumentData 데이터클래스로
변환하는 브릿지 계층.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.design_renderer.im_document import (
    ChartData,
    CompanyOverview,
    ContactInfo,
    DealStructure,
    FinancialStatements,
    GrowthStrategy,
    IMDocumentData,
    IMStyle,
    ManagementMember,
    MarketData,
    ShareholderInfo,
    SourceCitation,
    TransactionType,
)

# 입력 크기 제한 상수
_MAX_NARRATIVE_LENGTH = 100_000  # 섹션당 최대 문자 수
_MAX_NARRATIVE_SECTIONS = 30  # 최대 내러티브 섹션 수
_MAX_CHART_KEYS = 200  # 차트 data dict 최대 키 수

# 기본 연락처 (환경설정으로 오버라이드 가능)
_DEFAULT_CONTACT_NAME = "AMIC & PetraBridge Partners"
_DEFAULT_CONTACT_EMAIL = "info@amic.kr"
_DEFAULT_CONTACT_COMPANY = "AMIC Law & PetraBridge Partners"

logger = logging.getLogger(__name__)


class ChartSpec(BaseModel):
    """차트 데이터 스펙."""

    chart_type: str
    title: str
    data: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("data")
    @classmethod
    def validate_data_size(cls, v: dict[str, Any]) -> dict[str, Any]:
        """차트 데이터 크기 제한."""
        if len(v) > _MAX_CHART_KEYS:
            msg = f"차트 data 키 수 {len(v)}개 (최대 {_MAX_CHART_KEYS}개)"
            raise ValueError(msg)
        return v


class FinancialDataSpec(BaseModel):
    """재무 데이터 스펙 — 연도별 딕셔너리."""

    revenue: dict[str, float] = Field(default_factory=dict)
    cost_of_goods_sold: dict[str, float] = Field(default_factory=dict)
    gross_profit: dict[str, float] = Field(default_factory=dict)
    operating_income: dict[str, float] = Field(default_factory=dict)
    ebitda: dict[str, float] = Field(default_factory=dict)
    net_income: dict[str, float] = Field(default_factory=dict)
    sga_expenses: dict[str, float] = Field(default_factory=dict)
    total_assets: dict[str, float] = Field(default_factory=dict)
    total_liabilities: dict[str, float] = Field(default_factory=dict)
    total_equity: dict[str, float] = Field(default_factory=dict)
    cash_and_equivalents: dict[str, float] = Field(default_factory=dict)
    total_debt: dict[str, float] = Field(default_factory=dict)
    operating_cash_flow: dict[str, float] = Field(default_factory=dict)
    investing_cash_flow: dict[str, float] = Field(default_factory=dict)
    financing_cash_flow: dict[str, float] = Field(default_factory=dict)
    capex: dict[str, float] = Field(default_factory=dict)
    free_cash_flow: dict[str, float] = Field(default_factory=dict)

    def to_financial_statements(self) -> FinancialStatements:
        """FinancialStatements 데이터클래스로 변환."""
        return FinancialStatements(
            revenue=self.revenue,
            cost_of_goods_sold=self.cost_of_goods_sold,
            gross_profit=self.gross_profit,
            operating_income=self.operating_income,
            ebitda=self.ebitda,
            net_income=self.net_income,
            sga_expenses=self.sga_expenses,
            total_assets=self.total_assets,
            total_liabilities=self.total_liabilities,
            total_equity=self.total_equity,
            cash_and_equivalents=self.cash_and_equivalents,
            total_debt=self.total_debt,
            operating_cash_flow=self.operating_cash_flow,
            investing_cash_flow=self.investing_cash_flow,
            financing_cash_flow=self.financing_cash_flow,
            capex=self.capex,
            free_cash_flow=self.free_cash_flow,
        )


class DealStructureSpec(BaseModel):
    """딜 구조 스펙."""

    seller: str = ""
    stake_pct: float | None = None
    deal_background: str = ""
    valuation_low: float | None = None
    valuation_high: float | None = None
    valuation_method: str = ""
    transaction_type: str = "M&A"

    def to_deal_structure(self) -> DealStructure:
        """DealStructure 데이터클래스로 변환."""
        tx_type = TransactionType.MA
        matched = False
        for t in TransactionType:
            if t.value == self.transaction_type:
                tx_type = t
                matched = True
                break
        if not matched:
            logger.warning(
                "transaction_type '%s' 매핑 실패 — 기본값 M&A 적용",
                self.transaction_type,
            )
        return DealStructure(
            seller=self.seller,
            stake_pct=self.stake_pct,
            deal_background=self.deal_background,
            valuation_low=self.valuation_low,
            valuation_high=self.valuation_high,
            valuation_method=self.valuation_method,
            transaction_type=tx_type,
        )


class DocumentRenderingSpec(BaseModel):
    """JSON 입력 → IMDocumentData 변환 스키마.

    외부 시스템(프론트엔드, API 등)에서 전달받는 문서 생성 스펙.
    """

    document_type: str = Field(description="문서 유형: IM, TM, DM")
    project_name: str
    company_name_kr: str
    company_name_en: str = ""
    date: str = ""

    # 재무 데이터
    financial_data: FinancialDataSpec = Field(default_factory=FinancialDataSpec)

    # 내러티브
    narrative_sections: dict[str, str] = Field(default_factory=dict)

    # 차트
    charts: dict[str, list[ChartSpec]] = Field(default_factory=dict)

    # 딜 구조
    deal_structure: DealStructureSpec | None = None

    # 투자 하이라이트
    investment_highlights: list[str] = Field(default_factory=list)

    # 경쟁사
    competitors: list[dict[str, Any]] = Field(default_factory=list)

    # 경영진
    management_team: list[dict[str, str]] = Field(default_factory=list)

    # 주주
    shareholders: list[dict[str, Any]] = Field(default_factory=list)

    # 회사 개요
    company_overview: dict[str, Any] = Field(default_factory=dict)

    # 성장 전략
    growth_strategy: dict[str, Any] = Field(default_factory=dict)

    # 출처
    source_citations: dict[str, list[dict[str, str]]] = Field(default_factory=dict)

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, v: str) -> str:
        """문서 유형 검증."""
        allowed = {"IM", "TM", "DM"}
        upper = v.upper()
        if upper not in allowed:
            msg = f"document_type '{v[:20]}'은 허용되지 않음. 허용: {allowed}"
            raise ValueError(msg)
        return upper

    @field_validator("narrative_sections")
    @classmethod
    def validate_narrative_sections(cls, v: dict[str, str]) -> dict[str, str]:
        """내러티브 섹션 크기 제한."""
        if len(v) > _MAX_NARRATIVE_SECTIONS:
            msg = f"내러티브 섹션 수 {len(v)}개 (최대 {_MAX_NARRATIVE_SECTIONS}개)"
            raise ValueError(msg)
        for key, text in v.items():
            if len(text) > _MAX_NARRATIVE_LENGTH:
                msg = (
                    f"내러티브 '{key}' 길이 {len(text)}자 "
                    f"(최대 {_MAX_NARRATIVE_LENGTH}자)"
                )
                raise ValueError(msg)
        return v

    def _resolve_im_style(self) -> IMStyle:
        """document_type → IMStyle 매핑."""
        mapping = {
            "IM": IMStyle.FULL,
            "TM": IMStyle.TEASER,
            "DM": IMStyle.DM,
        }
        return mapping[self.document_type]

    def _build_charts(self) -> dict[str, list[ChartData]]:
        """ChartSpec → ChartData 변환."""
        result: dict[str, list[ChartData]] = {}
        for section_id, chart_list in self.charts.items():
            result[section_id] = [
                ChartData(
                    chart_type=c.chart_type,
                    title=c.title,
                    data=c.data,
                    options=c.options,
                )
                for c in chart_list
            ]
        return result

    def _build_source_citations(self) -> dict[str, list[SourceCitation]]:
        """출처 딕셔너리 → SourceCitation 변환."""
        result: dict[str, list[SourceCitation]] = {}
        for section_id, citations in self.source_citations.items():
            result[section_id] = [
                SourceCitation(
                    source_name=c.get("source_name", ""),
                    url=c.get("url"),
                    access_date=c.get("access_date", ""),
                    document_title=c.get("document_title"),
                )
                for c in citations
            ]
        return result

    def _build_management_team(self) -> list[ManagementMember]:
        """경영진 딕셔너리 → ManagementMember 변환."""
        return [
            ManagementMember(
                name=m.get("name", ""),
                title=m.get("title", ""),
                role=m.get("role", ""),
            )
            for m in self.management_team
        ]

    def _build_shareholders(self) -> list[ShareholderInfo]:
        """주주 딕셔너리 → ShareholderInfo 변환."""
        return [
            ShareholderInfo(
                name=s.get("name", ""),
                stake_pct=s.get("stake_pct", 0.0),
                category=s.get("category", ""),
            )
            for s in self.shareholders
        ]

    def _build_company_overview(self) -> CompanyOverview | None:
        """회사 개요 딕셔너리 → CompanyOverview 변환."""
        if not self.company_overview:
            return None
        co = self.company_overview
        return CompanyOverview(
            headquarters=co.get("headquarters", ""),
            established_date=co.get("established_date", ""),
            employee_count=co.get("employee_count"),
            key_products=co.get("key_products", []),
            business_description=co.get("business_description", ""),
        )

    def _build_growth_strategy(self) -> GrowthStrategy | None:
        """성장 전략 딕셔너리 → GrowthStrategy 변환."""
        if not self.growth_strategy:
            return None
        gs = self.growth_strategy
        return GrowthStrategy(
            organic_growth=gs.get("organic_growth", []),
            new_business=gs.get("new_business", []),
            ma_targets=gs.get("ma_targets", []),
            roadmap=gs.get("roadmap", {}),
        )

    def to_im_document_data(self) -> IMDocumentData:
        """Pydantic 스펙 → IMDocumentData 데이터클래스 변환.

        Returns:
            파이프라인 입력용 IMDocumentData (파생 지표 미계산 상태).
        """
        data = IMDocumentData(
            project_name=self.project_name,
            company_name_kr=self.company_name_kr,
            company_name_en=self.company_name_en,
            date=self.date,
            im_style=self._resolve_im_style(),
            financial_statements=self.financial_data.to_financial_statements(),
            narratives=self.narrative_sections,
            charts=self._build_charts(),
            investment_highlights=self.investment_highlights,
            management_team=self._build_management_team(),
            shareholders=self._build_shareholders(),
            company_overview=self._build_company_overview(),
            source_citations=self._build_source_citations(),
            contacts=[
                ContactInfo(
                    name=_DEFAULT_CONTACT_NAME,
                    email=_DEFAULT_CONTACT_EMAIL,
                    company=_DEFAULT_CONTACT_COMPANY,
                )
            ],
        )

        # 딜 구조
        if self.deal_structure:
            data.deal_structure = self.deal_structure.to_deal_structure()

        # 시장 데이터
        if self.competitors:
            data.market_data = MarketData(competitors=self.competitors)

        # 성장 전략
        if self.growth_strategy:
            data.growth_strategy = self._build_growth_strategy()

        return data
