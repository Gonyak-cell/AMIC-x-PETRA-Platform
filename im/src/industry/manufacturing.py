"""제조업 산업 모듈 (A2).

> 마지막 수정: 2026-02-11 14:00:00

CAPA/가동률, 원가구조, 공급망 맵, CAPEX 분리, Lean/자동화 등
제조업에 특화된 KPI·차트·재무 가중치를 정의한다.
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
class ManufacturingModule(IndustryModule):
    """제조업 산업 모듈.

    설비 효율(OEE), 원가구조, 공급망, CAPEX 등
    제조업 핵심 운영 KPI와 재무 가중치를 제공한다.
    """

    industry_id = "manufacturing"
    industry_name_kr = "제조업"
    industry_name_en = "Manufacturing"

    def get_kpis(self) -> list[IndustryKPI]:
        """제조업 핵심 KPI 8개를 반환한다."""
        return [
            IndustryKPI(
                kpi_id="oee",
                name_kr="설비종합효율",
                name_en="Overall Equipment Effectiveness",
                unit=KPIUnit.PERCENTAGE,
                description="가용률 × 성능효율 × 품질률",
                formula="가용률 × 성능효율 × 품질률",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(60, 85),
            ),
            IndustryKPI(
                kpi_id="capacity_util",
                name_kr="CAPA 가동률",
                name_en="Capacity Utilization",
                unit=KPIUnit.PERCENTAGE,
                description="실제 생산량 / 최대 생산 능력",
                formula="실제 생산량 / 최대 CAPA × 100",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(70, 95),
            ),
            IndustryKPI(
                kpi_id="yield_rate",
                name_kr="수율",
                name_en="Yield Rate",
                unit=KPIUnit.PERCENTAGE,
                description="양품 수량 / 총 생산 수량",
                formula="양품 수 / 총 생산 수 × 100",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(90, 99),
            ),
            IndustryKPI(
                kpi_id="cogs_ratio",
                name_kr="원가율",
                name_en="Cost of Goods Sold Ratio",
                unit=KPIUnit.PERCENTAGE,
                description="매출원가 / 매출액 비율",
                formula="매출원가 / 매출액 × 100",
                display_format="{:.1f}%",
                higher_is_better=False,
                benchmark_range=(50, 80),
            ),
            IndustryKPI(
                kpi_id="inventory_turnover",
                name_kr="재고회전율",
                name_en="Inventory Turnover",
                unit=KPIUnit.RATE,
                description="연간 매출원가 / 평균 재고자산",
                formula="매출원가 / 평균 재고",
                display_format="{:.1f}회",
                higher_is_better=True,
                benchmark_range=(4, 12),
            ),
            IndustryKPI(
                kpi_id="capex_ratio",
                name_kr="CAPEX/매출 비율",
                name_en="CAPEX to Revenue Ratio",
                unit=KPIUnit.PERCENTAGE,
                description="자본적 지출 / 매출액 비율",
                formula="CAPEX / 매출액 × 100",
                display_format="{:.1f}%",
                higher_is_better=False,
                benchmark_range=(5, 20),
            ),
            IndustryKPI(
                kpi_id="supply_chain_lead",
                name_kr="공급 리드타임",
                name_en="Supply Chain Lead Time",
                unit=KPIUnit.DAYS,
                description="원자재 발주~입고까지 소요일",
                display_format="{:.0f}일",
                higher_is_better=False,
                benchmark_range=(7, 60),
            ),
            IndustryKPI(
                kpi_id="automation_level",
                name_kr="자동화 수준",
                name_en="Automation Level",
                unit=KPIUnit.PERCENTAGE,
                description="자동화 공정 비율",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(30, 80),
            ),
        ]

    def get_financial_weights(self) -> dict[str, float]:
        """제조업 재무 가중치를 반환한다."""
        return {
            "ebitda_margin": 0.25,
            "capex_efficiency": 0.20,
            "inventory_turnover": 0.20,
            "revenue_growth": 0.15,
            "working_capital": 0.20,
        }

    def get_chart_recommendations(self) -> list[IndustryChartRecommendation]:
        """제조업 추천 차트 5개를 반환한다."""
        return [
            IndustryChartRecommendation(
                chart_type="combo",
                title_template="{company_name} 매출·영업이익 추이",
                target_section="financial_analysis",
                data_keys=["revenue", "operating_income", "operating_margin"],
                priority=1,
                description="매출 및 영업이익 추이와 마진율",
            ),
            IndustryChartRecommendation(
                chart_type="stacked_bar",
                title_template="원가 구조 분석",
                target_section="industry_kpi",
                data_keys=["material", "labor", "overhead", "depreciation"],
                priority=1,
                description="매출원가 항목별 구성 비중",
            ),
            IndustryChartRecommendation(
                chart_type="hbar",
                title_template="공급망 맵 (주요 거래처)",
                target_section="industry_overview",
                data_keys=["supplier", "purchase_ratio"],
                priority=2,
                description="주요 거래처별 매입 비중",
            ),
            IndustryChartRecommendation(
                chart_type="waterfall",
                title_template="CAPEX 분리 (유지보수 vs 성장)",
                target_section="industry_kpi",
                data_keys=["maintenance_capex", "growth_capex"],
                priority=2,
                description="유지보수 CAPEX와 성장 CAPEX 구분",
            ),
            IndustryChartRecommendation(
                chart_type="line",
                title_template="가동률·수율 추이",
                target_section="industry_overview",
                data_keys=["capacity_util", "yield_rate"],
                priority=3,
                description="CAPA 가동률 및 수율 시계열",
            ),
        ]

    def get_narrative_variant(self) -> IndustryVariant:
        """ManufacturingVariant 인스턴스를 반환한다."""
        from src.narrative_generator.prompts.industry_variants.manufacturing import (
            ManufacturingVariant,
        )

        return ManufacturingVariant()

    def get_risk_categories(self) -> list[RiskCategory]:
        """제조업 리스크 카테고리 4개를 반환한다."""
        return [
            RiskCategory(
                category_id="supply_chain",
                name_kr="공급망 리스크",
                name_en="Supply Chain Risk",
                description="원자재 조달 불안정 및 공급망 단절 리스크",
                risk_factors=[
                    "주요 원자재 단일 소싱",
                    "글로벌 공급망 교란",
                    "핵심 부품 리드타임 증가",
                ],
            ),
            RiskCategory(
                category_id="commodity_price",
                name_kr="원자재 가격",
                name_en="Commodity Price Risk",
                description="원자재·에너지 가격 변동에 따른 원가 압박",
                risk_factors=[
                    "원자재 가격 급등",
                    "에너지 비용 상승",
                    "환율 변동에 따른 수입 원가 증가",
                ],
            ),
            RiskCategory(
                category_id="regulatory_compliance",
                name_kr="규제 준수",
                name_en="Regulatory Compliance",
                description="환경·안전·품질 규제 강화에 따른 비용 증가",
                risk_factors=[
                    "탄소배출 규제 강화",
                    "안전 기준 변경",
                    "유해물질 관리 규제",
                ],
            ),
            RiskCategory(
                category_id="capex_cycle",
                name_kr="CAPEX 사이클",
                name_en="CAPEX Cycle Risk",
                description="대규모 설비 투자의 타이밍·회수 리스크",
                risk_factors=[
                    "과잉 투자에 따른 가동률 하락",
                    "기술 변화로 인한 설비 진부화",
                    "투자 회수 기간 장기화",
                ],
            ),
        ]
