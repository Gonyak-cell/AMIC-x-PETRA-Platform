"""Financial 섹션 프롬프트 3개 (T-N09).

> 마지막 수정: 2026-02-10 11:52:29

Financial Analysis, Transaction Structure, Shareholder Structure.
"""

from __future__ import annotations

from typing import Any

from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.prompts.base import (
    BasePrompt,
    _format_financial_dict,
    _format_metrics_dict,
)


class FinancialAnalysisPrompt(BasePrompt):
    """Financial Analysis 섹션 프롬프트."""

    section_id = "financial_analysis"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}
        fs = data.financial_statements

        result["매출액"] = _format_financial_dict(fs.revenue)
        result["영업이익"] = _format_financial_dict(fs.operating_income)
        result["당기순이익"] = _format_financial_dict(fs.net_income)
        result["EBITDA"] = _format_financial_dict(fs.ebitda)
        result["매출총이익"] = _format_financial_dict(fs.gross_profit)
        result["판관비"] = _format_financial_dict(fs.sga_expenses)

        result["자산총계"] = _format_financial_dict(fs.total_assets)
        result["부채총계"] = _format_financial_dict(fs.total_liabilities)
        result["자본총계"] = _format_financial_dict(fs.total_equity)
        result["총차입금"] = _format_financial_dict(fs.total_debt)
        result["현금성자산"] = _format_financial_dict(fs.cash_and_equivalents)

        result["영업활동CF"] = _format_financial_dict(fs.operating_cash_flow)
        result["CAPEX"] = _format_financial_dict(fs.capex)
        result["FCF"] = _format_financial_dict(fs.free_cash_flow)

        if data.derived_metrics:
            result["파생지표"] = _format_metrics_dict(data.derived_metrics)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Financial Analysis (재무 분석)\n"
            "기업의 재무 성과를 다각도로 분석합니다.\n"
            "손익, 재무상태, 현금흐름의 트렌드와 핵심 지표를 설명합니다.\n"
            "정확한 수치를 반드시 포함하되, 단순 나열이 아닌 분석적 해석을 제공합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 재무 데이터를 바탕으로 Financial Analysis를 작성하십시오.\n"
            "1문단: 매출 및 수익성 트렌드 분석 (매출 성장률, EBITDA 마진 포함)\n"
            "2문단: 재무 건전성 분석 (부채비율, 유동성, 차입금 구조)\n"
            "3문단: 현금흐름 분석 (영업CF, CAPEX, FCF 동향)\n"
            "4문단: 핵심 재무 지표 요약 (ROE, CAGR 등)\n"
        )

    def get_token_budget(self) -> int:
        return 800


class TransactionStructurePrompt(BasePrompt):
    """Transaction Structure 섹션 프롬프트."""

    section_id = "transaction_structure"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.deal_structure:
            ds = data.deal_structure
            result["거래 유형"] = ds.transaction_type.value
            if ds.seller:
                result["매각주체"] = ds.seller
            if ds.stake_pct is not None:
                result["매각 지분율"] = f"{ds.stake_pct:.1%}"
            if ds.old_shares:
                result["구주"] = f"{ds.old_shares:,.0f}억원"
            if ds.new_shares:
                result["신주"] = f"{ds.new_shares:,.0f}억원"
            if ds.valuation_low and ds.valuation_high:
                result["밸류에이션"] = (
                    f"{ds.valuation_low:,.0f} ~ {ds.valuation_high:,.0f}억원"
                )
            if ds.valuation_method:
                result["밸류에이션 방법론"] = ds.valuation_method
            if ds.timeline:
                result["거래 일정"] = ds.timeline

        fs = data.financial_statements
        if fs.ebitda:
            result["EBITDA"] = _format_financial_dict(fs.ebitda)

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Transaction Structure (거래 구조)\n"
            "거래의 법적 구조, 자금 조달 방안, 밸류에이션 근거를 설명합니다.\n"
            "투자자가 거래 참여의 조건과 기대 수익을 이해할 수 있도록 합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Transaction Structure를 작성하십시오.\n"
            "1문단: 거래 구조 설명 (구주/신주 비율, 지분 구성)\n"
            "2문단: 밸류에이션 근거 및 방법론\n"
            "3문단: 거래 일정 및 절차\n"
        )

    def get_token_budget(self) -> int:
        return 500


class ShareholderStructurePrompt(BasePrompt):
    """Shareholder Structure 섹션 프롬프트."""

    section_id = "shareholder_structure"

    def extract_data(self, data: IMDocumentData) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if data.shareholders:
            shareholders_info = []
            for sh in data.shareholders:
                info = f"{sh.name} ({sh.category}): {sh.stake_pct:.1%}"
                if sh.share_count:
                    info += f" ({sh.share_count:,}주)"
                shareholders_info.append(info)
            result["주주 구성"] = shareholders_info

        if data.deal_structure and data.deal_structure.stake_pct is not None:
            result["매각 지분율"] = f"{data.deal_structure.stake_pct:.1%}"

        return result

    def _get_section_instruction(self) -> str:
        return (
            "## 섹션: Shareholder Structure (주주 구성)\n"
            "현재 주주 구성, 지분율, 거래 후 예상 변동을 설명합니다.\n"
            "최대주주, 특수관계인, 기관투자자 등 주주 유형별로 분석합니다.\n"
        )

    def _get_writing_instruction(self) -> str:
        return (
            "위 데이터를 바탕으로 Shareholder Structure를 작성하십시오.\n"
            "1문단: 현재 주주 구성 현황\n"
            "2문단: 주주 유형별 분석 및 지배구조 특징\n"
            "3문단: 거래에 따른 지분 변동 전망 (해당되는 경우)\n"
        )

    def get_token_budget(self) -> int:
        return 400
