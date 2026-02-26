"""섹션 렌더러 패키지 — 32종 섹션별 HTML/PPTX 듀얼 렌더러 (IM 18종 + TM 8종 + DM 6종).

렌더러 레지스트리를 통해 section_id로 렌더러를 조회할 수 있다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.design_renderer.section_renderers.base import (
    BaseSectionRenderer,
    RendererError,
    RendererNotFoundError,
)

if TYPE_CHECKING:
    pass

# 렌더러 레지스트리 (그룹별 구현 완료 시 점진적 등록)
RENDERER_REGISTRY: dict[str, type[BaseSectionRenderer]] = {}


def get_renderer(section_id: str) -> BaseSectionRenderer:
    """section_id로 렌더러 인스턴스를 생성하여 반환.

    Args:
        section_id: SECTION_IDS 중 하나.

    Returns:
        해당 섹션의 렌더러 인스턴스.

    Raises:
        RendererNotFoundError: 미등록 section_id.
    """
    if section_id not in RENDERER_REGISTRY:
        raise RendererNotFoundError(
            f"미등록 섹션 렌더러: '{section_id}'. "
            f"등록된 렌더러: {list(RENDERER_REGISTRY.keys())}"
        )
    cls = RENDERER_REGISTRY[section_id]
    return cls()


def register_renderer(cls: type[BaseSectionRenderer]) -> type[BaseSectionRenderer]:
    """렌더러 클래스를 레지스트리에 등록하는 데코레이터.

    Usage::

        @register_renderer
        class CoverRenderer(BaseSectionRenderer):
            section_id = "cover"
            ...
    """
    RENDERER_REGISTRY[cls.section_id] = cls
    return cls


# F-α Core 렌더러 등록 (import 시 @register_renderer 데코레이터 실행)
from src.design_renderer.section_renderers.contact import ContactRenderer
from src.design_renderer.section_renderers.cover import CoverRenderer
from src.design_renderer.section_renderers.disclaimer import DisclaimerRenderer
from src.design_renderer.section_renderers.toc_divider import TOCDividerRenderer

# F-β Deal/Company 렌더러
from src.design_renderer.section_renderers.business_overview import BusinessOverviewRenderer
from src.design_renderer.section_renderers.company_overview import CompanyOverviewRenderer
from src.design_renderer.section_renderers.deal_overview import DealOverviewRenderer
from src.design_renderer.section_renderers.executive_summary import ExecutiveSummaryRenderer

# F-γ Strategy 렌더러
from src.design_renderer.section_renderers.growth_strategy import GrowthStrategyRenderer
from src.design_renderer.section_renderers.investment_highlights import InvestmentHighlightsRenderer
from src.design_renderer.section_renderers.market_overview import MarketOverviewRenderer
from src.design_renderer.section_renderers.value_creation import ValueCreationRenderer

# F-δ Financial 렌더러
from src.design_renderer.section_renderers.financial_analysis import FinancialAnalysisRenderer
from src.design_renderer.section_renderers.shareholder_structure import ShareholderStructureRenderer
from src.design_renderer.section_renderers.transaction_structure import TransactionStructureRenderer

# F-ε Supporting 렌더러
from src.design_renderer.section_renderers.appendix import AppendixRenderer
from src.design_renderer.section_renderers.business_model import BusinessModelRenderer
from src.design_renderer.section_renderers.management_team import ManagementTeamRenderer

# F-η Valuation 렌더러
from src.design_renderer.section_renderers.valuation import ValuationRenderer

# F-ζ Industry 렌더러
from src.design_renderer.section_renderers.industry_kpi import IndustryKPIRenderer
from src.design_renderer.section_renderers.industry_overview import IndustryOverviewRenderer

# F-θ TM (Teaser Memorandum) 전용 렌더러
from src.design_renderer.section_renderers.market_drivers import (
    DemandDriverRenderer,
    MarketOutlookRenderer,
    SupplyDriverRenderer,
)
from src.design_renderer.section_renderers.proforma import (
    ProformaFinancialsRenderer,
    ProformaPlanRenderer,
)
from src.design_renderer.section_renderers.target_positioning import (
    TargetPositioningRenderer,
)
from src.design_renderer.section_renderers.tm_aliases import (
    TargetHighlightsRenderer,
    TargetOverviewRenderer,
)

# F-ι DM (Discussion Memorandum) 전용 렌더러
from src.design_renderer.section_renderers.dm_market_trends import DmMarketTrendsRenderer
from src.design_renderer.section_renderers.dm_deal_structure import DmDealStructureRenderer
from src.design_renderer.section_renderers.dm_investment_thesis import DmInvestmentThesisRenderer
from src.design_renderer.section_renderers.dm_valuation import DmValuationRenderer
from src.design_renderer.section_renderers.dm_risk_assessment import DmRiskAssessmentRenderer
from src.design_renderer.section_renderers.dm_summary import DmSummaryRenderer

__all__ = [
    "BaseSectionRenderer",
    "RendererError",
    "RendererNotFoundError",
    "RENDERER_REGISTRY",
    "get_renderer",
    "register_renderer",
    # F-α Core
    "CoverRenderer",
    "DisclaimerRenderer",
    "TOCDividerRenderer",
    "ContactRenderer",
    # F-β Deal/Company
    "DealOverviewRenderer",
    "ExecutiveSummaryRenderer",
    "CompanyOverviewRenderer",
    "BusinessOverviewRenderer",
    # F-γ Strategy
    "InvestmentHighlightsRenderer",
    "MarketOverviewRenderer",
    "ValueCreationRenderer",
    "GrowthStrategyRenderer",
    # F-δ Financial
    "FinancialAnalysisRenderer",
    "TransactionStructureRenderer",
    "ShareholderStructureRenderer",
    # F-ε Supporting
    "ManagementTeamRenderer",
    "BusinessModelRenderer",
    "AppendixRenderer",
    # F-η Valuation
    "ValuationRenderer",
    # F-ζ Industry
    "IndustryKPIRenderer",
    "IndustryOverviewRenderer",
    # F-θ TM (Teaser)
    "TargetPositioningRenderer",
    "MarketOutlookRenderer",
    "DemandDriverRenderer",
    "SupplyDriverRenderer",
    "ProformaPlanRenderer",
    "ProformaFinancialsRenderer",
    "TargetOverviewRenderer",
    "TargetHighlightsRenderer",
    # F-ι DM (Discussion Memo)
    "DmMarketTrendsRenderer",
    "DmDealStructureRenderer",
    "DmInvestmentThesisRenderer",
    "DmValuationRenderer",
    "DmRiskAssessmentRenderer",
    "DmSummaryRenderer",
]
