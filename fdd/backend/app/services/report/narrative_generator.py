"""FDD 내러티브 생성기 — LLM 라우터 기반.

보고서 섹션별로 최적의 LLM을 사용하여 분석 내러티브를 생성한다.
- Executive Summary: Anthropic (장문 일관성)
- QoE/NWC/Debt Commentary: OpenAI (수치 정확도)
- Methodology: Gemini (비용 효율)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.logging import get_logger
from app.agents.guardrails import validate_narrative_claims
from app.services.llm.routing import FDDModelRouter, FDDModelRouter as _

logger = get_logger(__name__)


class FDDNarrativeGenerator:
    """FDD 보고서 내러티브 생성기.

    Args:
        router: FDD 모델 라우터 인스턴스
    """

    def __init__(self, router: FDDModelRouter):
        self._router = router

    def generate_executive_summary(
        self,
        deal_name: str,
        industry_name: str,
        qoe_data: dict[str, Any] | None = None,
        nwc_data: dict[str, Any] | None = None,
        debt_data: dict[str, Any] | None = None,
    ) -> str:
        """Executive Summary를 생성한다 (Anthropic 라우팅).

        Args:
            deal_name: 딜 이름
            industry_name: 산업 이름
            qoe_data: QoE 분석 요약 데이터
            nwc_data: NWC 분석 요약 데이터
            debt_data: Net Debt 분석 요약 데이터

        Returns:
            생성된 Executive Summary 텍스트
        """
        data_points = []
        if qoe_data:
            data_points.append(
                f"- Reported EBITDA: {qoe_data.get('reported_ebitda', 'N/A')}\n"
                f"- Adjusted EBITDA: {qoe_data.get('adjusted_ebitda', 'N/A')}\n"
                f"- Total Adjustments: {qoe_data.get('total_adjustments', 'N/A')}"
            )
        if nwc_data:
            data_points.append(
                f"- Net Working Capital: {nwc_data.get('net_working_capital', 'N/A')}\n"
                f"- Peg Target: {nwc_data.get('peg_target', 'N/A')}"
            )
        if debt_data:
            data_points.append(
                f"- Net Debt: {debt_data.get('net_debt', 'N/A')}\n"
                f"- Adjusted Net Debt: {debt_data.get('adjusted_net_debt', 'N/A')}"
            )

        system_prompt = (
            "You are a senior Financial Due Diligence analyst writing an executive summary. "
            "Be concise, professional, and focus on key findings. "
            "Do NOT invent or calculate any numbers — only reference the data provided. "
            "Write in English. Keep it under 300 words."
        )
        user_prompt = (
            f"Deal: {deal_name}\n"
            f"Industry: {industry_name}\n\n"
            f"Analysis Results:\n" + "\n\n".join(data_points) + "\n\n"
            "Write a professional executive summary covering the key FDD findings."
        )

        response = self._router.generate(
            "executive_summary",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=1024,
        )

        # Guardrails: 내러티브 수치 교차검증
        known_values: dict[str, str] = {}
        for source in [qoe_data, nwc_data, debt_data]:
            if source:
                for k, v in source.items():
                    known_values[k] = str(v)
        warnings = validate_narrative_claims(response.text, known_values)
        if warnings:
            logger.warning("Executive Summary guardrail warnings: %s", warnings)

        return response.text

    def generate_qoe_commentary(
        self,
        reported_ebitda: str,
        adjusted_ebitda: str,
        total_adjustments: str,
        adjustment_count: int,
        industry_name: str,
    ) -> str:
        """QoE 분석 코멘터리를 생성한다 (OpenAI 라우팅).

        Args:
            reported_ebitda: Reported EBITDA 금액 문자열
            adjusted_ebitda: Adjusted EBITDA 금액 문자열
            total_adjustments: 총 조정 금액 문자열
            adjustment_count: 조정 항목 수
            industry_name: 산업 이름

        Returns:
            생성된 QoE 코멘터리 텍스트
        """
        system_prompt = (
            "You are a Financial Due Diligence analyst writing a QoE analysis commentary. "
            "Reference the exact numbers provided. Do NOT calculate new values. "
            "Write 2-3 concise paragraphs in English."
        )
        user_prompt = (
            f"Industry: {industry_name}\n"
            f"Reported EBITDA: {reported_ebitda}\n"
            f"Total Adjustments: {total_adjustments} ({adjustment_count} items)\n"
            f"Adjusted EBITDA: {adjusted_ebitda}\n\n"
            "Write a professional QoE analysis commentary."
        )

        response = self._router.generate(
            "qoe_analysis_narrative",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=768,
        )

        # Guardrails: QoE 수치 교차검증
        known_values = {
            "reported_ebitda": reported_ebitda,
            "adjusted_ebitda": adjusted_ebitda,
            "total_adjustments": total_adjustments,
        }
        warnings = validate_narrative_claims(response.text, known_values)
        if warnings:
            logger.warning("QoE commentary guardrail warnings: %s", warnings)

        return response.text

    def generate_methodology(
        self,
        deal_name: str,
        industry_name: str,
        scope: list[str],
    ) -> str:
        """방법론 설명을 생성한다 (Gemini 라우팅).

        Args:
            deal_name: 딜 이름
            industry_name: 산업 이름
            scope: FDD 범위 목록 (예: ["QoE", "NWC", "Net Debt"])

        Returns:
            생성된 방법론 텍스트
        """
        system_prompt = (
            "You are writing the methodology section of a Financial Due Diligence report. "
            "Describe the standard FDD methodology steps professionally. "
            "Keep it factual and under 200 words. Write in English."
        )
        user_prompt = (
            f"Deal: {deal_name}\n"
            f"Industry: {industry_name}\n"
            f"Scope: {', '.join(scope)}\n\n"
            "Write the methodology section."
        )

        response = self._router.generate(
            "methodology_description",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=512,
        )
        return response.text

    def generate_risk_narrative(
        self,
        issues: list[dict[str, Any]],
        industry_name: str,
    ) -> str:
        """리스크 내러티브를 생성한다 (Anthropic 라우팅).

        Args:
            issues: Issue 리스트 (title, severity, category 포함)
            industry_name: 산업 이름

        Returns:
            생성된 리스크 내러티브 텍스트
        """
        if not issues:
            return ""

        issue_summary = "\n".join(
            f"- [{issue.get('severity', 'medium').upper()}] {issue.get('title', 'N/A')} "
            f"(Category: {issue.get('category', 'N/A')})"
            for issue in issues[:10]
        )

        system_prompt = (
            "You are a senior FDD analyst writing a risk assessment narrative. "
            "Summarize the key risks identified during the analysis. "
            "Be professional and actionable. Write in English. Under 250 words."
        )
        user_prompt = (
            f"Industry: {industry_name}\n"
            f"Issues Identified ({len(issues)} total):\n{issue_summary}\n\n"
            "Write a risk assessment narrative."
        )

        response = self._router.generate(
            "risk_narrative",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=768,
        )
        return response.text
