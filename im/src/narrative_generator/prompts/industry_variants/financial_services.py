"""금융서비스 산업 변형 (T-N12).

> 마지막 수정: 2026-02-10 11:52:29
"""

from __future__ import annotations

from src.narrative_generator.prompts.industry_variants.base_variant import (
    IndustryConfig,
    IndustryVariant,
)


class FinancialServicesVariant(IndustryVariant):
    """금융서비스 산업 프롬프트 변형."""

    config = IndustryConfig(
        industry_id="financial_services",
        industry_name_kr="금융서비스",
        industry_name_en="Financial Services",
    )

    def get_industry_context(self) -> str:
        return (
            "금융서비스 산업의 IM 작성 시 다음 사항에 유의하십시오:\n"
            "- 순이자마진(NIM)과 비이자수익 비중이 수익 구조의 핵심입니다.\n"
            "- 자산건전성(NPL 비율, 대손충당금)이 리스크 평가의 기본입니다.\n"
            "- BIS 자기자본비율 등 규제 자본 요건 충족 여부가 중요합니다.\n"
            "- 예대율(Loan-to-Deposit Ratio)로 유동성 리스크를 평가합니다.\n"
            "- ROE가 금융업의 가장 중요한 수익성 지표입니다.\n"
            "- 운용자산(AUM) 규모와 수수료 수익 구조를 분석합니다.\n"
        )

    def get_terminology_overrides(self) -> dict[str, str]:
        return {
            "매출액": "영업수익 (이자수익 + 비이자수익)",
            "영업이익": "충당금적립전이익 또는 영업이익",
            "COGS": "해당 없음 (이자비용으로 대체)",
            "재고": "대출 포트폴리오",
        }

    def get_emphasis_areas(self) -> list[str]:
        return [
            "NIM (순이자마진) 추이 및 금리 민감도",
            "자산건전성 (NPL 비율, 대손충당금 적립률)",
            "BIS 자기자본비율 및 규제 자본 버퍼",
            "ROE 및 ROA 수익성 분석",
            "예대율 및 유동성 관리",
            "AUM (운용자산) 규모 및 수수료 수익 구조",
        ]
