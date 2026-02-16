"""일반(General) 산업 모듈 — 산업 미지정 시 기본 범용 모듈.

> 마지막 수정: 2026-02-12 10:39:21

산업 특화 KPI가 없는 경우에도 기본적인 재무/영업 KPI를
제공하여 industry_kpi, industry_overview 섹션이 비어있지 않게 한다.
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
class GeneralModule(IndustryModule):
    """범용 산업 모듈.

    산업 미분류 기업에 대해 기본 재무·영업 KPI와
    범용 차트·리스크 카테고리를 제공한다.
    """

    industry_id = "general"
    industry_name_kr = "일반"
    industry_name_en = "General"

    def get_kpis(self) -> list[IndustryKPI]:
        """범용 재무 KPI 8개를 반환한다."""
        return [
            IndustryKPI(
                kpi_id="revenue_growth",
                name_kr="매출 성장률",
                name_en="Revenue Growth",
                unit=KPIUnit.PERCENTAGE,
                description="전년 대비 매출 증가율",
                formula="(당기 매출 - 전기 매출) / 전기 매출 × 100",
                display_format="{:.1f}%",
                higher_is_better=True,
            ),
            IndustryKPI(
                kpi_id="operating_margin",
                name_kr="영업이익률",
                name_en="Operating Margin",
                unit=KPIUnit.PERCENTAGE,
                description="매출 대비 영업이익 비율",
                formula="영업이익 / 매출 × 100",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(5, 20),
            ),
            IndustryKPI(
                kpi_id="ebitda_margin",
                name_kr="EBITDA 마진",
                name_en="EBITDA Margin",
                unit=KPIUnit.PERCENTAGE,
                description="매출 대비 EBITDA 비율",
                formula="EBITDA / 매출 × 100",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(10, 30),
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
                benchmark_range=(8, 20),
            ),
            IndustryKPI(
                kpi_id="debt_to_equity",
                name_kr="부채비율",
                name_en="Debt to Equity Ratio",
                unit=KPIUnit.PERCENTAGE,
                description="총부채 대비 자기자본 비율",
                formula="총부채 / 자기자본 × 100",
                display_format="{:.1f}%",
                higher_is_better=False,
                benchmark_range=(50, 200),
            ),
            IndustryKPI(
                kpi_id="current_ratio",
                name_kr="유동비율",
                name_en="Current Ratio",
                unit=KPIUnit.RATIO,
                description="유동자산 대비 유동부채 비율",
                formula="유동자산 / 유동부채",
                display_format="{:.2f}x",
                higher_is_better=True,
                benchmark_range=(1.0, 2.5),
            ),
            IndustryKPI(
                kpi_id="net_income_growth",
                name_kr="순이익 성장률",
                name_en="Net Income Growth",
                unit=KPIUnit.PERCENTAGE,
                description="전년 대비 당기순이익 증가율",
                formula="(당기순이익 - 전기순이익) / 전기순이익 × 100",
                display_format="{:.1f}%",
                higher_is_better=True,
            ),
            IndustryKPI(
                kpi_id="free_cash_flow",
                name_kr="잉여현금흐름",
                name_en="Free Cash Flow",
                unit=KPIUnit.CURRENCY_KRW,
                description="영업활동 현금흐름에서 CAPEX를 차감한 잉여현금",
                formula="영업활동CF - CAPEX",
                display_format="{:,.0f}억원",
                higher_is_better=True,
            ),
        ]

    def get_financial_weights(self) -> dict[str, float]:
        """범용 재무 가중치를 반환한다."""
        return {
            "revenue_growth": 0.20,
            "ebitda_margin": 0.25,
            "roe": 0.20,
            "leverage": 0.15,
            "cash_flow": 0.20,
        }

    def get_chart_recommendations(self) -> list[IndustryChartRecommendation]:
        """범용 추천 차트 5개를 반환한다."""
        return [
            IndustryChartRecommendation(
                chart_type="combo",
                title_template="{company_name} 매출·영업이익 추이",
                target_section="financial_analysis",
                data_keys=["revenue", "operating_income"],
                priority=1,
                description="매출액 및 영업이익 추이 (bar + line)",
            ),
            IndustryChartRecommendation(
                chart_type="line",
                title_template="수익성 지표 추이",
                target_section="financial_analysis",
                data_keys=["operating_margin", "ebitda_margin", "roe"],
                priority=1,
                description="영업이익률, EBITDA 마진, ROE 추이",
            ),
            IndustryChartRecommendation(
                chart_type="waterfall",
                title_template="이익 브릿지",
                target_section="industry_kpi",
                data_keys=["revenue", "cogs", "opex", "ebitda"],
                priority=2,
                description="매출에서 EBITDA까지의 이익 브릿지",
            ),
            IndustryChartRecommendation(
                chart_type="stacked_bar",
                title_template="비용 구조",
                target_section="industry_kpi",
                data_keys=["cogs", "sga", "rd"],
                priority=2,
                description="매출원가, 판관비, R&D 비용 구성",
            ),
            IndustryChartRecommendation(
                chart_type="hbar",
                title_template="재무 건전성 비교",
                target_section="industry_overview",
                data_keys=["current_ratio", "debt_equity"],
                priority=3,
                description="유동비율, 부채비율 등 건전성 지표",
            ),
        ]

    def get_narrative_variant(self) -> IndustryVariant:
        """GeneralVariant 인스턴스를 반환한다."""
        from src.narrative_generator.prompts.industry_variants.general import (
            GeneralVariant,
        )

        return GeneralVariant()

    def get_risk_categories(self) -> list[RiskCategory]:
        """범용 리스크 카테고리 4개를 반환한다."""
        return [
            RiskCategory(
                category_id="macro_risk",
                name_kr="거시경제",
                name_en="Macroeconomic Risk",
                description="금리, 환율, 경기 변동에 따른 리스크",
                risk_factors=[
                    "금리 인상에 따른 차입비용 증가",
                    "환율 변동에 따른 수출입 영향",
                    "경기 둔화에 따른 수요 감소",
                ],
            ),
            RiskCategory(
                category_id="competition",
                name_kr="경쟁 심화",
                name_en="Market Competition",
                description="시장 내 경쟁 격화에 따른 매출·마진 압박",
                risk_factors=[
                    "가격 경쟁 심화",
                    "신규 진입자 증가",
                    "대체재 등장",
                ],
            ),
            RiskCategory(
                category_id="regulatory",
                name_kr="규제 리스크",
                name_en="Regulatory Risk",
                description="법규 변경 및 규제 강화 리스크",
                risk_factors=[
                    "산업 규제 강화",
                    "세법 변경",
                    "환경·안전 규제 신설",
                ],
            ),
            RiskCategory(
                category_id="operational",
                name_kr="운영 리스크",
                name_en="Operational Risk",
                description="내부 운영상의 리스크",
                risk_factors=[
                    "핵심 인력 이탈",
                    "IT 시스템 장애",
                    "공급망 불안정",
                ],
            ),
        ]
