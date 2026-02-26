"""DM (Discussion Memorandum) 전용 섹션 프롬프트 5개.

Market Trends, Deal Structure, Investment Thesis,
Risk Assessment, Summary & Recommendations.

dm_valuation은 기존 valuation 프롬프트를 재사용하므로 별도 정의 불필요.
"""

from __future__ import annotations

from typing import Any

from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.prompts.base import (
    BasePrompt,
    _format_financial_dict,
    _format_metrics_dict,
)


# ---------------------------------------------------------------------------
# (1) Market & Transaction Trends — 시장 및 거래 동향
# ---------------------------------------------------------------------------


class DmMarketTrendsPrompt(BasePrompt):
    """DM Market & Transaction Trends 섹션 프롬프트."""

    section_id = "dm_market_trends"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        md = data.market_data
        if md:
            if md.tam is not None:
                result["시장규모(TAM)"] = f"{md.tam:,.0f}억원"
            if md.market_cagr is not None:
                result["시장 CAGR"] = f"{md.market_cagr * 100:.1f}%"
            elif md.market_growth_rate is not None:
                result["시장 성장률"] = f"{md.market_growth_rate * 100:.1f}%"
            if md.industry_trends:
                result["산업 트렌드"] = md.industry_trends
            if md.competitors:
                comp_info = []
                for c in md.competitors:
                    name = c.get("name", "")
                    ms = c.get("market_share")
                    ms_str = f" (점유율 {ms * 100:.1f}%)" if ms else ""
                    comp_info.append(f"{name}{ms_str}")
                result["주요 경쟁사"] = comp_info
            if md.regulatory_notes:
                result["규제 환경"] = md.regulatory_notes

        if data.deal_structure:
            ds = data.deal_structure
            if ds.transaction_type:
                result["거래 유형"] = ds.transaction_type.value

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Market & Transaction Trends (시장 및 거래 동향)\n"
            "대상회사가 속한 시장의 규모, 성장성, M&A 거래 트렌드를 분석합니다.\n"
            "내부 투자위원회 검토 자료로서, 객관적 데이터에 기반한 분석적 톤을 유지합니다.\n"
            "Discussion Memorandum의 도입부로, 거래 검토의 배경을 설명합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Market & Transaction Trends를 작성하십시오.\n"
            "1문단: 시장 규모 및 성장 전망 (정량적 데이터 기반)\n"
            "2문단: 최근 M&A 거래 동향 및 밸류에이션 트렌드\n"
            "3문단: 규제 환경 및 시장 구조적 변화\n"
        )

    def get_token_budget(self) -> int:
        return 500


# ---------------------------------------------------------------------------
# (2) Deal Structure Considerations — 거래 구조 분석
# ---------------------------------------------------------------------------


class DmDealStructurePrompt(BasePrompt):
    """DM Deal Structure Considerations 섹션 프롬프트."""

    section_id = "dm_deal_structure"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        ds = data.deal_structure
        if ds:
            if ds.transaction_type:
                result["거래 유형"] = ds.transaction_type.value
            if ds.seller:
                result["매각 주체"] = ds.seller
            if ds.stake_pct is not None:
                result["매각 지분"] = f"{ds.stake_pct * 100:.1f}%"
            if ds.valuation_method:
                result["밸류에이션 방법"] = ds.valuation_method
            if ds.valuation_low is not None and ds.valuation_high is not None:
                result["밸류에이션 범위"] = (
                    f"{ds.valuation_low:,.0f}억원 ~ {ds.valuation_high:,.0f}억원"
                )
            if ds.deal_background:
                result["거래 배경"] = ds.deal_background

        fs = data.financial_statements
        if fs.ebitda:
            result["EBITDA 추이"] = _format_financial_dict(fs.ebitda)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Deal Structure Considerations (거래 구조 분석)\n"
            "거래의 구조, 매각 조건, 밸류에이션 기준 등을 분석합니다.\n"
            "투자위원회가 거래 참여 여부를 판단할 수 있도록 핵심 조건을 정리합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Deal Structure Considerations를 작성하십시오.\n"
            "1문단: 거래 개요 (유형, 매각 주체, 지분 구조)\n"
            "2문단: 밸류에이션 기준 및 적정 가격 범위 분석\n"
            "3문단: 거래 구조상 주요 고려사항 및 조건\n"
        )

    def get_token_budget(self) -> int:
        return 500


# ---------------------------------------------------------------------------
# (3) Investment Thesis — 투자 근거
# ---------------------------------------------------------------------------


class DmInvestmentThesisPrompt(BasePrompt):
    """DM Investment Thesis 섹션 프롬프트."""

    section_id = "dm_investment_thesis"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.investment_highlights:
            result["투자 하이라이트"] = data.investment_highlights

        if data.company_overview:
            co = data.company_overview
            if co.key_products:
                result["주요 제품/서비스"] = co.key_products
            if co.business_model:
                result["비즈니스 모델"] = co.business_model

        fs = data.financial_statements
        if fs.revenue:
            result["매출 추이"] = _format_financial_dict(fs.revenue)
        if fs.operating_income:
            result["영업이익 추이"] = _format_financial_dict(fs.operating_income)

        if data.derived_metrics:
            result["파생지표"] = _format_metrics_dict(data.derived_metrics)

        if data.growth_strategy:
            result["성장 전략"] = data.growth_strategy

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Investment Thesis (투자 근거)\n"
            "대상회사에 대한 투자 근거와 핵심 논점을 정리합니다.\n"
            "투자위원회가 투자 매력도를 평가할 수 있도록 논리적 근거를 제시합니다.\n"
            "긍정적 요소뿐 아니라 주의 사항도 균형 있게 다룹니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Investment Thesis를 작성하십시오.\n"
            "1문단: 핵심 투자 근거 요약 (비즈니스 매력도)\n"
            "2문단: 재무적 성과 기반의 투자 논거 (성장성, 수익성)\n"
            "3문단: 성장 전략 및 가치 창출 잠재력\n"
        )

    def get_token_budget(self) -> int:
        return 600


# ---------------------------------------------------------------------------
# (4) Risk Assessment — 리스크 분석
# ---------------------------------------------------------------------------


class DmRiskAssessmentPrompt(BasePrompt):
    """DM Risk Assessment 섹션 프롬프트."""

    section_id = "dm_risk_assessment"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        md = data.market_data
        if md:
            if md.regulatory_notes:
                result["규제 환경"] = md.regulatory_notes
            if md.competitors:
                result["경쟁 구도"] = [c.get("name", "") for c in md.competitors]

        if data.company_overview:
            co = data.company_overview
            if co.key_products:
                result["주요 제품/서비스"] = co.key_products

        if data.deal_structure:
            ds = data.deal_structure
            if ds.transaction_type:
                result["거래 유형"] = ds.transaction_type.value
            if ds.valuation_method:
                result["밸류에이션 방법"] = ds.valuation_method

        fs = data.financial_statements
        if fs.revenue:
            result["매출 추이"] = _format_financial_dict(fs.revenue)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Risk Assessment (리스크 분석)\n"
            "투자 시 예상되는 리스크 요인과 완화 방안을 분석합니다.\n"
            "시장 리스크, 운영 리스크, 규제 리스크, 거래 리스크 등을 포괄합니다.\n"
            "투자위원회가 리스크를 인지하고 대응 전략을 수립할 수 있도록 합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Risk Assessment를 작성하십시오.\n"
            "1문단: 시장 및 경쟁 리스크 (경쟁 심화, 시장 변동성)\n"
            "2문단: 운영 및 규제 리스크 (핵심 인력, 규제 변화)\n"
            "3문단: 거래 리스크 및 완화 방안 (밸류에이션, 실사 이슈)\n"
        )

    def get_token_budget(self) -> int:
        return 500


# ---------------------------------------------------------------------------
# (5) Summary & Recommendations — 요약 및 권고
# ---------------------------------------------------------------------------


class DmSummaryPrompt(BasePrompt):
    """DM Summary & Recommendations 섹션 프롬프트."""

    section_id = "dm_summary"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.deal_structure:
            ds = data.deal_structure
            if ds.transaction_type:
                result["거래 유형"] = ds.transaction_type.value
            if ds.valuation_method:
                result["밸류에이션 방법"] = ds.valuation_method
            if ds.stake_pct is not None:
                result["매각 지분"] = f"{ds.stake_pct * 100:.1f}%"

        if data.investment_highlights:
            result["투자 하이라이트"] = data.investment_highlights

        fs = data.financial_statements
        if fs.revenue:
            result["매출 추이"] = _format_financial_dict(fs.revenue)
        if fs.ebitda:
            result["EBITDA 추이"] = _format_financial_dict(fs.ebitda)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Summary & Recommendations (요약 및 권고)\n"
            "Discussion Memorandum 전체를 요약하고, 투자위원회에 대한 권고사항을 제시합니다.\n"
            "거래 참여 여부에 대한 명확한 의견과 근거를 포함합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Summary & Recommendations를 작성하십시오.\n"
            "1문단: 거래 및 대상회사 핵심 요약\n"
            "2문단: 투자 매력도 평가 (강점 vs 리스크)\n"
            "3문단: 권고사항 (참여 권고/조건부 참여/불참 권고 중 택1, 근거 제시)\n"
        )

    def get_token_budget(self) -> int:
        return 400
