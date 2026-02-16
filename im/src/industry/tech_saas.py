"""Tech/SaaS 산업 모듈 (A2).

> 마지막 수정: 2026-02-11 14:00:00

ARR Bridge, NRR/Churn, 코호트, TAM/SAM/SOM 퍼널, Rule of 40 등
SaaS/구독 비즈니스에 특화된 KPI·차트·재무 가중치를 정의한다.
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
class TechSaaSModule(IndustryModule):
    """Tech/SaaS 산업 모듈.

    SaaS/구독 비즈니스 모델의 핵심 KPI(ARR, NRR, Churn, LTV/CAC 등)와
    Rule of 40 기반 재무 가중치를 제공한다.
    """

    industry_id = "tech"
    industry_name_kr = "테크/SaaS"
    industry_name_en = "Technology/SaaS"

    def get_kpis(self) -> list[IndustryKPI]:
        """SaaS 핵심 KPI 8개를 반환한다."""
        return [
            IndustryKPI(
                kpi_id="arr",
                name_kr="연간 반복 매출",
                name_en="Annual Recurring Revenue",
                unit=KPIUnit.CURRENCY_KRW,
                description="연간 기준 반복 매출(MRR × 12)",
                formula="MRR × 12",
                display_format="{:,.0f}억원",
                higher_is_better=True,
            ),
            IndustryKPI(
                kpi_id="nrr",
                name_kr="순매출유지율",
                name_en="Net Revenue Retention",
                unit=KPIUnit.PERCENTAGE,
                description="기존 고객 기반 매출 유지·확장 비율",
                formula="(기초ARR + 확장 - 축소 - 이탈) / 기초ARR × 100",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(100, 130),
            ),
            IndustryKPI(
                kpi_id="gross_churn",
                name_kr="총 이탈률",
                name_en="Gross Churn Rate",
                unit=KPIUnit.PERCENTAGE,
                description="기간 내 이탈·축소된 매출 비율",
                formula="(이탈ARR + 축소ARR) / 기초ARR × 100",
                display_format="{:.1f}%",
                higher_is_better=False,
                benchmark_range=(3, 10),
            ),
            IndustryKPI(
                kpi_id="cac",
                name_kr="고객획득비용",
                name_en="Customer Acquisition Cost",
                unit=KPIUnit.CURRENCY_KRW,
                description="신규 고객 1사 획득에 소요되는 비용",
                formula="영업·마케팅비 / 신규 고객 수",
                display_format="{:,.0f}억원",
                higher_is_better=False,
            ),
            IndustryKPI(
                kpi_id="ltv_cac",
                name_kr="LTV/CAC 비율",
                name_en="LTV to CAC Ratio",
                unit=KPIUnit.RATIO,
                description="고객생애가치 대비 획득비용 비율",
                formula="LTV / CAC",
                display_format="{:.1f}x",
                higher_is_better=True,
                benchmark_range=(3.0, 5.0),
            ),
            IndustryKPI(
                kpi_id="rule_of_40",
                name_kr="Rule of 40",
                name_en="Rule of 40",
                unit=KPIUnit.PERCENTAGE,
                description="매출 성장률 + 영업이익률 합산",
                formula="매출 성장률(%) + 영업이익률(%)",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(40, 80),
            ),
            IndustryKPI(
                kpi_id="tam_sam_som",
                name_kr="TAM/SAM/SOM",
                name_en="Total Addressable Market",
                unit=KPIUnit.CURRENCY_KRW,
                description="전체/유효/획득가능 시장 규모",
                display_format="{:,.0f}억원",
                higher_is_better=True,
            ),
            IndustryKPI(
                kpi_id="cohort_retention",
                name_kr="코호트 잔존율",
                name_en="Cohort Retention Rate",
                unit=KPIUnit.PERCENTAGE,
                description="가입 코호트별 N개월 후 잔존 비율",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(70, 95),
            ),
        ]

    def get_financial_weights(self) -> dict[str, float]:
        """SaaS 재무 가중치를 반환한다."""
        return {
            "revenue_growth": 0.30,
            "gross_margin": 0.20,
            "nrr": 0.20,
            "rule_of_40": 0.15,
            "ltv_cac_ratio": 0.15,
        }

    def get_chart_recommendations(self) -> list[IndustryChartRecommendation]:
        """SaaS 추천 차트 5개를 반환한다."""
        return [
            IndustryChartRecommendation(
                chart_type="combo",
                title_template="{company_name} ARR 추이",
                target_section="financial_analysis",
                data_keys=["arr", "arr_growth"],
                priority=1,
                description="연간 반복 매출 및 성장률 추이",
            ),
            IndustryChartRecommendation(
                chart_type="waterfall",
                title_template="ARR Bridge 분석",
                target_section="industry_kpi",
                data_keys=["new_arr", "expansion", "contraction", "churn"],
                priority=1,
                description="ARR 변동 요인 분해 (신규/확장/축소/이탈)",
            ),
            IndustryChartRecommendation(
                chart_type="line",
                title_template="코호트 잔존율 추이",
                target_section="industry_kpi",
                data_keys=["cohort_month", "retention_pct"],
                priority=2,
                description="가입 코호트별 잔존율 시계열",
            ),
            IndustryChartRecommendation(
                chart_type="donut",
                title_template="TAM/SAM/SOM 퍼널",
                target_section="industry_overview",
                data_keys=["tam", "sam", "som"],
                priority=2,
                description="시장 규모 퍼널 (전체→유효→획득가능)",
            ),
            IndustryChartRecommendation(
                chart_type="stacked_bar",
                title_template="매출 구성 (신규 vs 기존)",
                target_section="financial_analysis",
                data_keys=["new_revenue", "existing_revenue"],
                priority=3,
                description="신규 고객 vs 기존 고객 매출 비중",
            ),
        ]

    def get_narrative_variant(self) -> IndustryVariant:
        """TechVariant 인스턴스를 반환한다."""
        from src.narrative_generator.prompts.industry_variants.tech import (
            TechVariant,
        )

        return TechVariant()

    def get_risk_categories(self) -> list[RiskCategory]:
        """Tech/SaaS 리스크 카테고리 4개를 반환한다."""
        return [
            RiskCategory(
                category_id="churn_risk",
                name_kr="고객 이탈",
                name_en="Customer Churn",
                description="고객 이탈률 증가 및 NRR 하락 리스크",
                risk_factors=[
                    "이탈률 증가 추세",
                    "주요 고객 집중도",
                    "경쟁 제품 전환 비용 하락",
                ],
            ),
            RiskCategory(
                category_id="competition",
                name_kr="경쟁 심화",
                name_en="Market Competition",
                description="시장 경쟁 심화에 따른 CAC 상승 및 가격 압박",
                risk_factors=[
                    "CAC 상승 추세",
                    "대형 플랫폼 진입",
                    "오픈소스 대체재 등장",
                ],
            ),
            RiskCategory(
                category_id="tech_obsolescence",
                name_kr="기술 진부화",
                name_en="Technology Obsolescence",
                description="기술 패러다임 전환에 따른 제품 경쟁력 하락",
                risk_factors=[
                    "AI/자동화에 의한 대체",
                    "레거시 아키텍처 한계",
                    "보안 취약점 리스크",
                ],
            ),
            RiskCategory(
                category_id="scaling",
                name_kr="확장성",
                name_en="Scaling Risk",
                description="빠른 성장에 따른 인프라·조직 확장 리스크",
                risk_factors=[
                    "인프라 비용 증가",
                    "핵심 인력 확보 어려움",
                    "해외 시장 진출 불확실성",
                ],
            ),
        ]
