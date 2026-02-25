"""프롬프트 레지스트리 및 전체 프롬프트 패키지.

> 마지막 수정: 2026-02-12 10:39:21

모든 섹션 프롬프트와 산업별 변형을 등록하고, 기본 레지스트리를 제공한다.
"""

from src.narrative_generator.prompts.base import BasePrompt, PromptRegistry
from src.narrative_generator.prompts.industry_variants.base_variant import (
    IndustryConfig,
    IndustryVariant,
)
from src.narrative_generator.prompts.industry_variants.financial_services import (
    FinancialServicesVariant,
)
from src.narrative_generator.prompts.industry_variants.general import GeneralVariant
from src.narrative_generator.prompts.industry_variants.healthcare import (
    HealthcareVariant,
)
from src.narrative_generator.prompts.industry_variants.logistics import (
    LogisticsVariant,
)
from src.narrative_generator.prompts.industry_variants.manufacturing import (
    ManufacturingVariant,
)
from src.narrative_generator.prompts.industry_variants.tech import TechVariant
from src.narrative_generator.prompts.section_prompts.core import (
    BusinessOverviewPrompt,
    CompanyOverviewPrompt,
    DealOverviewPrompt,
    ExecutiveSummaryPrompt,
)
from src.narrative_generator.prompts.section_prompts.financial import (
    FinancialAnalysisPrompt,
    ShareholderStructurePrompt,
    TransactionStructurePrompt,
)
from src.narrative_generator.prompts.section_prompts.strategy import (
    GrowthStrategyPrompt,
    InvestmentHighlightsPrompt,
    MarketOverviewPrompt,
    ValueCreationPrompt,
)
from src.narrative_generator.prompts.section_prompts.supporting import (
    AppendixPrompt,
    BusinessModelPrompt,
    ContactPrompt,
    ManagementTeamPrompt,
)
from src.narrative_generator.prompts.section_prompts.teaser import (
    DemandDriverPrompt,
    MarketOutlookPrompt,
    ProformaFinancialsPrompt,
    ProformaPlanPrompt,
    SupplyDriverPrompt,
    TargetHighlightsPrompt,
    TargetOverviewPrompt,
    TargetPositioningPrompt,
)

# ---------------------------------------------------------------------------
# 산업별 변형 레지스트리
# ---------------------------------------------------------------------------

INDUSTRY_VARIANTS: dict[str, IndustryVariant] = {
    "general": GeneralVariant(),
    "tech": TechVariant(),
    "healthcare": HealthcareVariant(),
    "manufacturing": ManufacturingVariant(),
    "financial_services": FinancialServicesVariant(),
    "logistics": LogisticsVariant(),
}


def get_industry_variant(industry: str) -> IndustryVariant | None:
    """산업 식별자로 IndustryVariant를 조회한다."""
    return INDUSTRY_VARIANTS.get(industry)


# ---------------------------------------------------------------------------
# 기본 프롬프트 레지스트리 생성
# ---------------------------------------------------------------------------


def create_default_registry() -> PromptRegistry:
    """23개 섹션 프롬프트(IM 15종 + TM 8종)가 등록된 기본 레지스트리를 생성한다."""
    registry = PromptRegistry()

    # Core (T-N08)
    registry.register(ExecutiveSummaryPrompt())
    registry.register(CompanyOverviewPrompt())
    registry.register(BusinessOverviewPrompt())
    registry.register(DealOverviewPrompt())

    # Financial (T-N09)
    registry.register(FinancialAnalysisPrompt())
    registry.register(TransactionStructurePrompt())
    registry.register(ShareholderStructurePrompt())

    # Strategy (T-N10)
    registry.register(InvestmentHighlightsPrompt())
    registry.register(MarketOverviewPrompt())
    registry.register(ValueCreationPrompt())
    registry.register(GrowthStrategyPrompt())

    # Supporting (T-N11)
    registry.register(ManagementTeamPrompt())
    registry.register(BusinessModelPrompt())
    registry.register(AppendixPrompt())
    registry.register(ContactPrompt())

    # TM (Teaser Memorandum) 전용
    registry.register(TargetPositioningPrompt())
    registry.register(MarketOutlookPrompt())
    registry.register(DemandDriverPrompt())
    registry.register(SupplyDriverPrompt())
    registry.register(TargetOverviewPrompt())
    registry.register(TargetHighlightsPrompt())
    registry.register(ProformaPlanPrompt())
    registry.register(ProformaFinancialsPrompt())

    return registry


__all__ = [
    "BasePrompt",
    "PromptRegistry",
    "create_default_registry",
    "IndustryVariant",
    "IndustryConfig",
    "GeneralVariant",
    "TechVariant",
    "HealthcareVariant",
    "ManufacturingVariant",
    "FinancialServicesVariant",
    "LogisticsVariant",
    "INDUSTRY_VARIANTS",
    "get_industry_variant",
    "ExecutiveSummaryPrompt",
    "CompanyOverviewPrompt",
    "BusinessOverviewPrompt",
    "DealOverviewPrompt",
    "FinancialAnalysisPrompt",
    "TransactionStructurePrompt",
    "ShareholderStructurePrompt",
    "InvestmentHighlightsPrompt",
    "MarketOverviewPrompt",
    "ValueCreationPrompt",
    "GrowthStrategyPrompt",
    "ManagementTeamPrompt",
    "BusinessModelPrompt",
    "AppendixPrompt",
    "ContactPrompt",
    "TargetPositioningPrompt",
    "MarketOutlookPrompt",
    "DemandDriverPrompt",
    "SupplyDriverPrompt",
    "TargetOverviewPrompt",
    "TargetHighlightsPrompt",
    "ProformaPlanPrompt",
    "ProformaFinancialsPrompt",
]
