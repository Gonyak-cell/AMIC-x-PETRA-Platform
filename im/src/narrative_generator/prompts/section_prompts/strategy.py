"""Strategy 섹션 프롬프트 4개 (T-N10).

> 마지막 수정: 2026-02-10 11:52:29

Investment Highlights, Market Overview, Value Creation, Growth Strategy.
"""

from __future__ import annotations

from typing import Any

from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.prompts.base import (
    BasePrompt,
    _format_financial_dict,
    _format_metrics_dict,
)


class InvestmentHighlightsPrompt(BasePrompt):
    """Investment Highlights 섹션 프롬프트."""

    section_id = "investment_highlights"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.investment_highlights:
            result["투자 하이라이트"] = data.investment_highlights

        if data.derived_metrics:
            result["핵심 지표"] = _format_metrics_dict(data.derived_metrics)

        fs = data.financial_statements
        result["매출 추이"] = _format_financial_dict(fs.revenue)
        result["EBITDA 추이"] = _format_financial_dict(fs.ebitda)

        if data.market_data:
            md = data.market_data
            if md.market_growth_rate is not None:
                result["시장 성장률"] = f"{md.market_growth_rate:.1%}"
            if md.market_cagr is not None:
                result["시장 CAGR"] = f"{md.market_cagr:.1%}"

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Investment Highlights (투자 매력 포인트)\n"
            "투자자에게 가장 매력적인 요소들을 강조합니다.\n"
            "각 하이라이트는 구체적 수치와 함께 제시되어야 합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Investment Highlights를 작성하십시오.\n"
            "제공된 투자 하이라이트 항목을 중심으로, 각각에 대해 "
            "구체적 수치와 근거를 포함하여 2-3문장으로 설명하십시오.\n"
            "전체적으로 3-4문단으로 구성하십시오.\n"
        )

    def get_token_budget(self) -> int:
        return 600


class MarketOverviewPrompt(BasePrompt):
    """Market Overview 섹션 프롬프트."""

    section_id = "market_overview"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.market_data:
            md = data.market_data
            if md.tam is not None:
                result["TAM (전체시장)"] = f"{md.tam:,.0f}억원"
            if md.sam is not None:
                result["SAM (유효시장)"] = f"{md.sam:,.0f}억원"
            if md.som is not None:
                result["SOM (획득가능시장)"] = f"{md.som:,.0f}억원"
            if md.market_growth_rate is not None:
                result["시장 성장률"] = f"{md.market_growth_rate:.1%}"
            if md.market_cagr is not None:
                result["시장 CAGR"] = f"{md.market_cagr:.1%}"
            if md.competitors:
                result["경쟁사"] = md.competitors
            if md.industry_trends:
                result["산업 트렌드"] = md.industry_trends

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Market Overview (시장 분석)\n"
            "타겟 시장의 규모, 성장률, 주요 트렌드를 분석합니다.\n"
            "TAM/SAM/SOM 프레임워크와 경쟁 구도를 설명합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Market Overview를 작성하십시오.\n"
            "1문단: 시장 규모 및 성장률 (TAM/SAM/SOM 수치 포함)\n"
            "2문단: 주요 산업 트렌드 및 성장 동인\n"
            "3문단: 경쟁 구도 및 자사 포지셔닝\n"
        )

    def get_token_budget(self) -> int:
        return 700


class ValueCreationPrompt(BasePrompt):
    """Value Creation 섹션 프롬프트."""

    section_id = "value_creation"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.growth_strategy:
            gs = data.growth_strategy
            if gs.organic_growth:
                result["유기적 성장"] = gs.organic_growth
            if gs.new_business:
                result["신규 사업"] = gs.new_business
            if gs.ma_targets:
                result["M&A 계획"] = gs.ma_targets

        if data.derived_metrics:
            result["핵심 지표"] = _format_metrics_dict(data.derived_metrics)

        fs = data.financial_statements
        result["매출 추이"] = _format_financial_dict(fs.revenue)
        result["영업이익 추이"] = _format_financial_dict(fs.operating_income)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Value Creation (가치 창출)\n"
            "투자 후 기업가치를 향상시킬 수 있는 구체적 전략을 제시합니다.\n"
            "매출 성장, 수익성 개선, 운영 효율화 등의 관점에서 분석합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Value Creation 내러티브를 작성하십시오.\n"
            "1문단: 유기적 성장 기회 (매출 확대, 시장 점유율)\n"
            "2문단: 수익성 개선 레버 (원가 절감, 운영 효율화)\n"
            "3문단: 전략적 M&A 또는 신규 사업 기회\n"
        )

    def get_token_budget(self) -> int:
        return 500


class GrowthStrategyPrompt(BasePrompt):
    """Growth Strategy 섹션 프롬프트."""

    section_id = "growth_strategy"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.growth_strategy:
            gs = data.growth_strategy
            if gs.organic_growth:
                result["유기적 성장 전략"] = gs.organic_growth
            if gs.new_business:
                result["신규 사업 전략"] = gs.new_business
            if gs.ma_targets:
                result["M&A 전략"] = gs.ma_targets
            if gs.roadmap:
                result["로드맵"] = gs.roadmap

        if data.derived_metrics:
            key_metrics = {
                k: v
                for k, v in data.derived_metrics.items()
                if "cagr" in k or "growth" in k or "yoy" in k
            }
            if key_metrics:
                result["성장 지표"] = _format_metrics_dict(key_metrics)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Growth Strategy (성장 전략)\n"
            "단기/중기/장기 성장 전략을 구체적으로 제시합니다.\n"
            "유기적 성장, 신규 사업, M&A 전략을 포함합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Growth Strategy를 작성하십시오.\n"
            "1문단: 단기 성장 전략 (유기적 성장 중심)\n"
            "2문단: 중기 전략 (신규 사업, 시장 확장)\n"
            "3문단: 장기 비전 및 로드맵\n"
        )

    def get_token_budget(self) -> int:
        return 600
