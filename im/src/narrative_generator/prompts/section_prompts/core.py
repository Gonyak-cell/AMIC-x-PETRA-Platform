"""Core 섹션 프롬프트 4개 (T-N08).

> 마지막 수정: 2026-02-10 11:52:29

Executive Summary, Company Overview, Business Overview, Deal Overview.
"""

from __future__ import annotations

from typing import Any

from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.prompts.base import (
    BasePrompt,
    _format_financial_dict,
    _format_metrics_dict,
)


class ExecutiveSummaryPrompt(BasePrompt):
    """Executive Summary 섹션 프롬프트."""

    section_id = "executive_summary"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        """전체 요약에 필요한 핵심 데이터를 추출한다."""
        result: dict[str, Any] = {}

        fs = data.financial_statements
        result["매출액"] = _format_financial_dict(fs.revenue)
        result["영업이익"] = _format_financial_dict(fs.operating_income)
        result["당기순이익"] = _format_financial_dict(fs.net_income)
        result["EBITDA"] = _format_financial_dict(fs.ebitda)

        if data.derived_metrics:
            result["파생지표"] = _format_metrics_dict(data.derived_metrics)

        if data.investment_highlights:
            result["투자 하이라이트"] = data.investment_highlights

        if data.deal_structure:
            ds = data.deal_structure
            result["거래유형"] = ds.transaction_type.value
            if ds.valuation_method:
                result["밸류에이션 방법"] = ds.valuation_method

        if data.market_data and data.market_data.tam:
            result["시장규모(TAM)"] = f"{data.market_data.tam:,.0f}억원"

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Executive Summary (경영진 요약)\n"
            "이 섹션은 IM 문서의 첫인상을 결정하는 가장 중요한 부분입니다.\n"
            "기업의 핵심 가치, 재무 하이라이트, 투자 매력도를 간결하게 전달합니다.\n"
            "투자자가 이 섹션만 읽고도 기업의 매력을 파악할 수 있어야 합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Executive Summary를 작성하십시오.\n"
            "1문단: 기업 소개 및 핵심 사업 (1-2문장)\n"
            "2문단: 재무 하이라이트 (매출, 수익성, 성장률 수치 포함)\n"
            "3문단: 시장 기회 및 경쟁 우위\n"
            "4문단: 투자 매력 포인트 요약\n"
        )

    def get_token_budget(self) -> int:
        return 800


class CompanyOverviewPrompt(BasePrompt):
    """Company Overview 섹션 프롬프트."""

    section_id = "company_overview"

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
            if co.business_model:
                result["비즈니스 모델"] = co.business_model
            if co.key_products:
                result["주요 제품/서비스"] = co.key_products
            if co.certifications:
                result["인증/특허"] = co.certifications
            if co.history:
                result["연혁"] = [f"{h['year']}: {h['event']}" for h in co.history]
            if co.value_chain:
                result["가치사슬"] = co.value_chain

        fs = data.financial_statements
        if fs.revenue:
            result["매출 추이"] = _format_financial_dict(fs.revenue)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Company Overview (회사 개요)\n"
            "기업의 설립 배경, 핵심 사업, 연혁, 조직 구성을 소개합니다.\n"
            "비즈니스 모델과 가치 사슬을 중심으로 기업의 정체성을 전달합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Company Overview를 작성하십시오.\n"
            "1문단: 기업 설립 배경과 현재 사업 영역\n"
            "2문단: 비즈니스 모델과 핵심 경쟁력\n"
            "3문단: 주요 연혁 및 성장 스토리\n"
        )

    def get_token_budget(self) -> int:
        return 600


class BusinessOverviewPrompt(BasePrompt):
    """Business Overview 섹션 프롬프트."""

    section_id = "business_overview"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.segment_revenue:
            for seg_name, seg_data in data.segment_revenue.segments.items():
                result[f"사업부 '{seg_name}' 매출"] = _format_financial_dict(seg_data)

        if data.key_customers:
            result["주요 고객사"] = data.key_customers

        fs = data.financial_statements
        result["전체 매출"] = _format_financial_dict(fs.revenue)
        result["매출총이익"] = _format_financial_dict(fs.gross_profit)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Business Overview (사업 현황)\n"
            "사업부별 매출 구성, 주요 고객, 제품/서비스 포트폴리오를 분석합니다.\n"
            "매출 다변화 수준과 주요 고객 의존도를 객관적으로 서술합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Business Overview를 작성하십시오.\n"
            "1문단: 전체 사업 구조와 매출 구성\n"
            "2문단: 사업부별 현황 및 성장 동인\n"
            "3문단: 주요 고객 관계 및 매출 안정성\n"
        )

    def get_token_budget(self) -> int:
        return 600


class DealOverviewPrompt(BasePrompt):
    """Deal Overview 섹션 프롬프트."""

    section_id = "deal_overview"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.deal_structure:
            ds = data.deal_structure
            result["거래 유형"] = ds.transaction_type.value
            if ds.seller:
                result["매각주체"] = ds.seller
            if ds.stake_pct is not None:
                result["매각 지분율"] = f"{ds.stake_pct:.1%}"
            if ds.deal_background:
                result["거래 배경"] = ds.deal_background
            if ds.valuation_low and ds.valuation_high:
                result["밸류에이션 범위"] = (
                    f"{ds.valuation_low:,.0f}억원 ~ {ds.valuation_high:,.0f}억원"
                )
            if ds.valuation_method:
                result["밸류에이션 방법"] = ds.valuation_method
            if ds.old_shares:
                result["구주 규모"] = f"{ds.old_shares:,.0f}억원"
            if ds.new_shares:
                result["신주 규모"] = f"{ds.new_shares:,.0f}억원"
            if ds.timeline:
                result["타임라인"] = ds.timeline

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Deal Overview (거래 개요)\n"
            "거래의 구조, 배경, 밸류에이션, 일정을 설명합니다.\n"
            "투자자가 거래의 핵심 조건을 빠르게 이해할 수 있도록 합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Deal Overview를 작성하십시오.\n"
            "1문단: 거래의 배경과 목적\n"
            "2문단: 거래 구조 (구주/신주, 지분율, 밸류에이션)\n"
            "3문단: 예상 일정 및 프로세스\n"
        )

    def get_token_budget(self) -> int:
        return 500
