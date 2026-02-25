"""TM (Teaser Memorandum) 전용 섹션 프롬프트 8개.

Target Positioning, Market Outlook, Demand/Supply Driver,
Target Overview/Highlights, Pro-Forma Plan/Financials.
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
# (1) Target Positioning — 대상회사 시장 포지셔닝
# ---------------------------------------------------------------------------


class TargetPositioningPrompt(BasePrompt):
    """Target Positioning 섹션 프롬프트."""

    section_id = "target_positioning"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.company_overview:
            co = data.company_overview
            if co.key_products:
                result["주요 제품/서비스"] = co.key_products
            if co.business_model:
                result["비즈니스 모델"] = co.business_model

        md = data.market_data
        if md:
            if md.tam is not None:
                result["시장규모(TAM)"] = f"{md.tam:,.0f}억원"
            if md.market_cagr is not None:
                result["시장 CAGR"] = f"{md.market_cagr * 100:.1f}%"
            if md.competitors:
                comp_info = []
                for c in md.competitors:
                    name = c.get("name", "")
                    ms = c.get("market_share")
                    ms_str = f" (점유율 {ms * 100:.1f}%)" if ms else ""
                    comp_info.append(f"{name}{ms_str}")
                result["주요 경쟁사"] = comp_info

        if data.investment_highlights:
            result["투자 포인트"] = data.investment_highlights

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Target Positioning (대상회사 포지셔닝)\n"
            "대상회사가 속한 시장에서의 경쟁 위치와 차별화 요인을 분석합니다.\n"
            "경쟁사 대비 강점을 객관적 데이터로 뒷받침해야 합니다.\n"
            "Teaser Memorandum의 핵심 섹션으로, 투자자의 관심을 유도해야 합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Target Positioning을 작성하십시오.\n"
            "1문단: 대상회사의 시장 내 포지션 요약\n"
            "2문단: 핵심 경쟁 우위 및 차별화 요인\n"
            "3문단: 경쟁사 대비 강점 (수치 기반)\n"
        )

    def get_token_budget(self) -> int:
        return 600


# ---------------------------------------------------------------------------
# (2) Market Outlook — 시장 전망
# ---------------------------------------------------------------------------


class MarketOutlookPrompt(BasePrompt):
    """Market Outlook 섹션 프롬프트."""

    section_id = "market_outlook"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        md = data.market_data
        if md:
            if md.tam is not None:
                result["TAM"] = f"{md.tam:,.0f}억원"
            if md.sam is not None:
                result["SAM"] = f"{md.sam:,.0f}억원"
            if md.som is not None:
                result["SOM"] = f"{md.som:,.0f}억원"
            if md.market_cagr is not None:
                result["시장 CAGR"] = f"{md.market_cagr * 100:.1f}%"
            elif md.market_growth_rate is not None:
                result["시장 성장률"] = f"{md.market_growth_rate * 100:.1f}%"
            if md.industry_trends:
                result["산업 트렌드"] = md.industry_trends

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Market Outlook (시장 전망)\n"
            "대상회사가 영위하는 시장의 규모, 성장성, 주요 트렌드를 분석합니다.\n"
            "TAM/SAM/SOM 프레임워크를 활용하여 시장 기회를 정량화합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Market Outlook을 작성하십시오.\n"
            "1문단: 전체 시장 규모 및 성장 전망 (TAM/SAM/SOM)\n"
            "2문단: 시장 성장을 이끄는 구조적 동인\n"
            "3문단: 주요 산업 트렌드 및 기회\n"
        )

    def get_token_budget(self) -> int:
        return 600


# ---------------------------------------------------------------------------
# (3) Key Demand Driver — 핵심 수요 드라이버
# ---------------------------------------------------------------------------


class DemandDriverPrompt(BasePrompt):
    """Key Demand Driver 섹션 프롬프트."""

    section_id = "demand_driver"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        md = data.market_data
        if md:
            if md.market_cagr is not None:
                result["시장 CAGR"] = f"{md.market_cagr * 100:.1f}%"
            if md.market_growth_rate is not None:
                result["연 성장률"] = f"{md.market_growth_rate * 100:.1f}%"
            if md.tam is not None:
                result["TAM"] = f"{md.tam:,.0f}억원"

        if data.derived_metrics:
            result["파생지표"] = _format_metrics_dict(data.derived_metrics)

        fs = data.financial_statements
        if fs.revenue:
            result["매출 추이"] = _format_financial_dict(fs.revenue)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Key Demand Driver (핵심 수요 드라이버)\n"
            "시장 수요를 견인하는 구조적·단기적 요인을 분석합니다.\n"
            "정책 변화, 기술 발전, 인구 구조 변화 등 수요 측면의 핵심 동인을\n"
            "정량적 데이터와 함께 제시합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Key Demand Driver를 작성하십시오.\n"
            "1문단: 시장 수요 성장의 구조적 배경\n"
            "2문단: 주요 수요 드라이버 분석 (정량적 근거 포함)\n"
            "3문단: 대상회사에 미치는 수요 측면의 긍정적 영향\n"
        )

    def get_token_budget(self) -> int:
        return 500


# ---------------------------------------------------------------------------
# (4) Key Supply Driver — 핵심 공급 드라이버
# ---------------------------------------------------------------------------


class SupplyDriverPrompt(BasePrompt):
    """Key Supply Driver 섹션 프롬프트."""

    section_id = "supply_driver"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        md = data.market_data
        if md and md.competitors:
            comp_info = []
            for c in md.competitors:
                name = c.get("name", "")
                rev = c.get("revenue")
                ms = c.get("market_share")
                parts = [name]
                if rev is not None:
                    parts.append(f"매출 {rev:,.0f}")
                if ms is not None:
                    parts.append(f"점유율 {ms * 100:.1f}%")
                comp_info.append(" | ".join(parts))
            result["경쟁사 현황"] = comp_info

        if data.company_overview and data.company_overview.certifications:
            result["인증/특허"] = data.company_overview.certifications

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Key Supply Driver (핵심 공급 드라이버)\n"
            "시장 공급 환경과 경쟁 구도를 분석합니다.\n"
            "진입 장벽, 경쟁사 현황, 공급 측면의 구조적 특성을 다룹니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Key Supply Driver를 작성하십시오.\n"
            "1문단: 시장 공급 환경 및 경쟁 구도 개요\n"
            "2문단: 주요 경쟁사 분석 및 시장 점유율\n"
            "3문단: 진입 장벽 및 대상회사의 공급 측면 경쟁력\n"
        )

    def get_token_budget(self) -> int:
        return 500


# ---------------------------------------------------------------------------
# (5) Target Overview — 대상회사 개요 (TM 관점)
# ---------------------------------------------------------------------------


class TargetOverviewPrompt(BasePrompt):
    """Target Overview 섹션 프롬프트 (CompanyOverview TM 변형)."""

    section_id = "target_overview"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.company_overview:
            co = data.company_overview
            if co.established_date:
                result["설립일"] = co.established_date
            if co.headquarters:
                result["본사"] = co.headquarters
            if co.employee_count:
                result["임직원 수"] = f"{co.employee_count:,}명"
            if co.key_products:
                result["주요 제품/서비스"] = co.key_products
            if co.business_model:
                result["비즈니스 모델"] = co.business_model

        fs = data.financial_statements
        if fs.revenue:
            result["매출 추이"] = _format_financial_dict(fs.revenue)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Target Overview (대상회사 개요)\n"
            "Teaser Memorandum에서의 기업 소개 섹션입니다.\n"
            "기업의 핵심 정보를 간결하게 전달하되, 투자 매력도를 부각합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Target Overview를 작성하십시오.\n"
            "1문단: 기업 개요 (설립, 본사, 핵심 사업)\n"
            "2문단: 비즈니스 모델 및 제품/서비스 경쟁력\n"
            "3문단: 최근 재무 성과 하이라이트\n"
        )

    def get_token_budget(self) -> int:
        return 500


# ---------------------------------------------------------------------------
# (6) Target Highlights — 투자 매력 포인트
# ---------------------------------------------------------------------------


class TargetHighlightsPrompt(BasePrompt):
    """Target Highlights 섹션 프롬프트 (BusinessOverview TM 변형)."""

    section_id = "target_highlights"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.investment_highlights:
            result["투자 하이라이트"] = data.investment_highlights

        if data.segment_revenue:
            for seg_name, seg_data in data.segment_revenue.segments.items():
                result[f"사업부 '{seg_name}' 매출"] = _format_financial_dict(seg_data)

        if data.key_customers:
            result["주요 고객사"] = data.key_customers

        fs = data.financial_statements
        if fs.revenue:
            result["매출 추이"] = _format_financial_dict(fs.revenue)
        if fs.operating_income:
            result["영업이익 추이"] = _format_financial_dict(fs.operating_income)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Target Highlights (투자 매력 포인트)\n"
            "대상회사의 핵심 투자 매력을 집중적으로 부각합니다.\n"
            "사업부별 실적, 고객 포트폴리오, 성장 동력을 중심으로 서술합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Target Highlights를 작성하십시오.\n"
            "1문단: 핵심 투자 매력 요약\n"
            "2문단: 사업부별 실적 및 성장 동력\n"
            "3문단: 고객 포트폴리오 및 매출 안정성\n"
        )

    def get_token_budget(self) -> int:
        return 600


# ---------------------------------------------------------------------------
# (7) Pro-Forma Plan — 사업계획 핵심 가정
# ---------------------------------------------------------------------------


class ProformaPlanPrompt(BasePrompt):
    """Pro-Forma Plan 섹션 프롬프트."""

    section_id = "proforma_plan"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

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
            "## 섹션: Pro-Forma Plan (사업계획 핵심 가정)\n"
            "인수 후 사업계획의 핵심 가정과 시너지 효과를 제시합니다.\n"
            "매출 성장, 수익성 개선, 비용 절감 등의 핵심 동인을 정량적으로 서술합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Pro-Forma Plan을 작성하십시오.\n"
            "1문단: 사업계획의 핵심 가정 요약\n"
            "2문단: 매출 성장 및 수익성 개선 시나리오\n"
            "3문단: 기대 시너지 효과 및 가치 창출 계획\n"
        )

    def get_token_budget(self) -> int:
        return 600


# ---------------------------------------------------------------------------
# (8) Pro-Forma Financials — 재무 지표 분석
# ---------------------------------------------------------------------------


class ProformaFinancialsPrompt(BasePrompt):
    """Pro-Forma Financials 섹션 프롬프트."""

    section_id = "proforma_financials"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        fs = data.financial_statements
        result["매출액"] = _format_financial_dict(fs.revenue)
        result["영업이익"] = _format_financial_dict(fs.operating_income)
        result["EBITDA"] = _format_financial_dict(fs.ebitda)
        result["당기순이익"] = _format_financial_dict(fs.net_income)

        if data.derived_metrics:
            result["파생지표"] = _format_metrics_dict(data.derived_metrics)

        if data.deal_structure:
            ds = data.deal_structure
            if ds.valuation_low and ds.valuation_high:
                result["밸류에이션 범위"] = (
                    f"{ds.valuation_low:,.0f}억원 ~ {ds.valuation_high:,.0f}억원"
                )

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Pro-Forma Financials (재무 지표 분석)\n"
            "대상회사의 과거 실적을 기반으로 향후 재무 전망을 분석합니다.\n"
            "P&L, 마진, 성장률 등 핵심 재무 지표를 중심으로 서술합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Pro-Forma Financials를 작성하십시오.\n"
            "1문단: 매출 및 수익성 추이 분석\n"
            "2문단: 핵심 재무 지표 (EBITDA 마진, 성장률, ROE 등)\n"
            "3문단: 재무 전망 및 밸류에이션 시사점\n"
        )

    def get_token_budget(self) -> int:
        return 600
