"""금융서비스 산업 모듈.

> 마지막 수정: 2026-02-12 10:39:21

NIM, NPL, BIS, ROE, AUM 등 금융서비스 산업 특화 KPI·차트·
재무 가중치를 정의한다. 기존 FinancialServicesVariant와 연결된다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.industry.base import IndustryModule
from src.industry.models import (
    IndustryChartRecommendation,
    IndustryKPI,
    KPIUnit,
    RiskCategory,
)
from src.industry.registry import register_industry

if TYPE_CHECKING:
    from src.narrative_generator.prompts.industry_variants.base_variant import (
        IndustryVariant,
    )


@register_industry
class FinancialServicesModule(IndustryModule):
    """금융서비스 산업 모듈.

    은행, 보험, 증권, 자산운용 등 금융업의 핵심 KPI(NIM, NPL, BIS 등)와
    금융업 특화 재무 가중치를 제공한다.
    """

    industry_id = "financial_services"
    industry_name_kr = "금융서비스"
    industry_name_en = "Financial Services"

    def get_kpis(self) -> list[IndustryKPI]:
        """금융서비스 핵심 KPI 8개를 반환한다."""
        return [
            IndustryKPI(
                kpi_id="nim",
                name_kr="순이자마진",
                name_en="Net Interest Margin",
                unit=KPIUnit.PERCENTAGE,
                description="이자수익자산 대비 순이자수익 비율",
                formula="(이자수익 - 이자비용) / 이자수익자산 × 100",
                display_format="{:.2f}%",
                higher_is_better=True,
                benchmark_range=(1.5, 3.0),
            ),
            IndustryKPI(
                kpi_id="npl_ratio",
                name_kr="고정이하여신비율",
                name_en="Non-Performing Loan Ratio",
                unit=KPIUnit.PERCENTAGE,
                description="총여신 대비 고정이하여신 비율",
                formula="고정이하여신 / 총여신 × 100",
                display_format="{:.2f}%",
                higher_is_better=False,
                benchmark_range=(0.3, 2.0),
            ),
            IndustryKPI(
                kpi_id="bis_ratio",
                name_kr="BIS 자기자본비율",
                name_en="BIS Capital Adequacy Ratio",
                unit=KPIUnit.PERCENTAGE,
                description="위험가중자산 대비 자기자본 비율",
                formula="자기자본 / 위험가중자산 × 100",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(10.5, 16.0),
            ),
            IndustryKPI(
                kpi_id="roe",
                name_kr="자기자본이익률",
                name_en="Return on Equity",
                unit=KPIUnit.PERCENTAGE,
                description="자기자본 대비 당기순이익 비율",
                formula="당기순이익 / 자기자본 × 100",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(6, 15),
            ),
            IndustryKPI(
                kpi_id="roa",
                name_kr="총자산이익률",
                name_en="Return on Assets",
                unit=KPIUnit.PERCENTAGE,
                description="총자산 대비 당기순이익 비율",
                formula="당기순이익 / 총자산 × 100",
                display_format="{:.2f}%",
                higher_is_better=True,
                benchmark_range=(0.3, 1.0),
            ),
            IndustryKPI(
                kpi_id="ldr",
                name_kr="예대율",
                name_en="Loan to Deposit Ratio",
                unit=KPIUnit.PERCENTAGE,
                description="예금 대비 대출 비율",
                formula="총대출 / 총예금 × 100",
                display_format="{:.1f}%",
                higher_is_better=False,
                benchmark_range=(80, 100),
            ),
            IndustryKPI(
                kpi_id="aum",
                name_kr="운용자산규모",
                name_en="Assets Under Management",
                unit=KPIUnit.CURRENCY_KRW,
                description="수탁·운용 중인 자산 총규모",
                display_format="{:,.0f}억원",
                higher_is_better=True,
            ),
            IndustryKPI(
                kpi_id="cost_income",
                name_kr="비용수익비율",
                name_en="Cost to Income Ratio",
                unit=KPIUnit.PERCENTAGE,
                description="영업수익 대비 판관비 비율",
                formula="판관비 / 영업수익 × 100",
                display_format="{:.1f}%",
                higher_is_better=False,
                benchmark_range=(40, 60),
            ),
        ]

    def get_financial_weights(self) -> dict[str, float]:
        """금융서비스 재무 가중치를 반환한다."""
        return {
            "nim": 0.25,
            "asset_quality": 0.25,
            "capital_adequacy": 0.20,
            "profitability": 0.15,
            "efficiency": 0.15,
        }

    def get_chart_recommendations(self) -> list[IndustryChartRecommendation]:
        """금융서비스 추천 차트 5개를 반환한다."""
        return [
            IndustryChartRecommendation(
                chart_type="combo",
                title_template="{company_name} 이자수익·비이자수익 추이",
                target_section="financial_analysis",
                data_keys=["interest_income", "non_interest_income", "nim"],
                priority=1,
                description="이자수익, 비이자수익 규모 및 NIM 추이",
            ),
            IndustryChartRecommendation(
                chart_type="waterfall",
                title_template="대손충당금 브릿지",
                target_section="industry_kpi",
                data_keys=[
                    "beginning_provision",
                    "new_provision",
                    "write_off",
                    "recovery",
                    "ending_provision",
                ],
                priority=1,
                description="대손충당금 변동 요인 분해",
            ),
            IndustryChartRecommendation(
                chart_type="line",
                title_template="BIS 비율·Tier 1 추이",
                target_section="industry_kpi",
                data_keys=["bis_ratio", "tier1_ratio", "regulatory_min"],
                priority=2,
                description="BIS 자기자본비율 및 Tier 1 비율 추이",
            ),
            IndustryChartRecommendation(
                chart_type="stacked_bar",
                title_template="대출 포트폴리오 구성",
                target_section="industry_overview",
                data_keys=["corporate_loan", "retail_loan", "mortgage", "other_loan"],
                priority=2,
                description="여신 포트폴리오 구성 (기업/개인/주택/기타)",
            ),
            IndustryChartRecommendation(
                chart_type="hbar",
                title_template="수익원 비교",
                target_section="financial_analysis",
                data_keys=["net_interest", "fee_income", "trading", "other"],
                priority=3,
                description="수익원별 기여도 비교 (이자/수수료/트레이딩/기타)",
            ),
        ]

    def get_narrative_variant(self) -> IndustryVariant:
        """FinancialServicesVariant 인스턴스를 반환한다."""
        from src.narrative_generator.prompts.industry_variants.financial_services import (
            FinancialServicesVariant,
        )

        return FinancialServicesVariant()

    def get_risk_categories(self) -> list[RiskCategory]:
        """금융서비스 리스크 카테고리 4개를 반환한다."""
        return [
            RiskCategory(
                category_id="credit_risk",
                name_kr="신용 리스크",
                name_en="Credit Risk",
                description="차주의 채무 불이행에 따른 손실 리스크",
                risk_factors=[
                    "NPL 비율 상승 추세",
                    "특정 산업·지역 여신 집중",
                    "경기 둔화에 따른 대손 증가",
                ],
            ),
            RiskCategory(
                category_id="interest_rate_risk",
                name_kr="금리 리스크",
                name_en="Interest Rate Risk",
                description="금리 변동에 따른 수익성·자산가치 변동 리스크",
                risk_factors=[
                    "금리 인상기 예대마진 축소",
                    "채권 포트폴리오 평가손실",
                    "변동금리 대출 부실화",
                ],
            ),
            RiskCategory(
                category_id="regulatory_capital",
                name_kr="규제 자본",
                name_en="Regulatory Capital Risk",
                description="규제 자본 요건 충족 관련 리스크",
                risk_factors=[
                    "바젤 III/IV 규제 강화",
                    "시스템적 중요 금융기관(D-SIB) 추가 자본 부과",
                    "스트레스 테스트 미통과 리스크",
                ],
            ),
            RiskCategory(
                category_id="liquidity_risk",
                name_kr="유동성 리스크",
                name_en="Liquidity Risk",
                description="자금 조달 및 운용의 유동성 불일치 리스크",
                risk_factors=[
                    "예대율 규제 초과",
                    "단기 차입 의존도 증가",
                    "뱅크런 리스크",
                ],
            ),
        ]
