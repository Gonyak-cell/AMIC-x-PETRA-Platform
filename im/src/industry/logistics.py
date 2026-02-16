"""물류/운송 산업 모듈 (A2).

> 마지막 수정: 2026-02-11 14:00:00

네트워크 맵, Fleet, 정시 배송률, 톤km당 매출, 창고 가동률 등
물류/운송에 특화된 KPI·차트·재무 가중치를 정의한다.
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
class LogisticsModule(IndustryModule):
    """물류/운송 산업 모듈.

    정시 배송률, 플릿 가동률, 톤km당 매출, 창고 가동률 등
    물류 운영 핵심 KPI와 재무 가중치를 제공한다.
    """

    industry_id = "logistics"
    industry_name_kr = "물류/운송"
    industry_name_en = "Logistics"

    def get_kpis(self) -> list[IndustryKPI]:
        """물류 핵심 KPI 8개를 반환한다."""
        return [
            IndustryKPI(
                kpi_id="otd",
                name_kr="정시 배송률",
                name_en="On-Time Delivery Rate",
                unit=KPIUnit.PERCENTAGE,
                description="약속 시간 내 배송 완료 비율",
                formula="정시 배송 건수 / 총 배송 건수 × 100",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(90, 99),
            ),
            IndustryKPI(
                kpi_id="fleet_util",
                name_kr="플릿 가동률",
                name_en="Fleet Utilization",
                unit=KPIUnit.PERCENTAGE,
                description="보유 차량/선박의 실제 가동 비율",
                formula="가동 차량 수 / 보유 차량 수 × 100",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(70, 90),
            ),
            IndustryKPI(
                kpi_id="rev_per_tonkm",
                name_kr="톤km당 매출",
                name_en="Revenue per Ton-km",
                unit=KPIUnit.CUSTOM,
                description="물동량 단위당 매출 효율",
                formula="운송 매출 / 총 톤km",
                display_format="{:,.0f}원/톤km",
                higher_is_better=True,
            ),
            IndustryKPI(
                kpi_id="warehouse_util",
                name_kr="창고 가동률",
                name_en="Warehouse Utilization",
                unit=KPIUnit.PERCENTAGE,
                description="창고 사용 면적 / 총 가용 면적",
                formula="사용 면적 / 총 면적 × 100",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(75, 95),
            ),
            IndustryKPI(
                kpi_id="empty_run_ratio",
                name_kr="공차율",
                name_en="Empty Running Ratio",
                unit=KPIUnit.PERCENTAGE,
                description="빈 차량으로 운행하는 비율",
                formula="공차 km / 총 운행 km × 100",
                display_format="{:.1f}%",
                higher_is_better=False,
                benchmark_range=(15, 35),
            ),
            IndustryKPI(
                kpi_id="network_coverage",
                name_kr="네트워크 커버리지",
                name_en="Network Coverage",
                unit=KPIUnit.COUNT,
                description="운영 거점/노선 수",
                display_format="{:.0f}개",
                higher_is_better=True,
            ),
            IndustryKPI(
                kpi_id="uph",
                name_kr="시간당 처리량",
                name_en="Units Per Hour",
                unit=KPIUnit.COUNT,
                description="창고/물류센터 시간당 처리 건수",
                display_format="{:,.0f}건/h",
                higher_is_better=True,
            ),
            IndustryKPI(
                kpi_id="claims_ratio",
                name_kr="클레임 비율",
                name_en="Claims Ratio",
                unit=KPIUnit.PERCENTAGE,
                description="배송 건수 대비 클레임 발생 비율",
                formula="클레임 건수 / 총 배송 건수 × 100",
                display_format="{:.2f}%",
                higher_is_better=False,
                benchmark_range=(0.1, 2.0),
            ),
        ]

    def get_financial_weights(self) -> dict[str, float]:
        """물류 재무 가중치를 반환한다."""
        return {
            "revenue_growth": 0.20,
            "ebitda_margin": 0.25,
            "fleet_efficiency": 0.20,
            "network_density": 0.15,
            "working_capital": 0.20,
        }

    def get_chart_recommendations(self) -> list[IndustryChartRecommendation]:
        """물류 추천 차트 5개를 반환한다."""
        return [
            IndustryChartRecommendation(
                chart_type="combo",
                title_template="{company_name} 물동량·매출 추이",
                target_section="financial_analysis",
                data_keys=["volume_tonkm", "revenue"],
                priority=1,
                description="물동량과 매출 추이 비교",
            ),
            IndustryChartRecommendation(
                chart_type="hbar",
                title_template="네트워크 맵 (노선별 물동량)",
                target_section="industry_overview",
                data_keys=["route", "volume"],
                priority=1,
                description="주요 노선별 물동량 분포",
            ),
            IndustryChartRecommendation(
                chart_type="stacked_bar",
                title_template="Fleet 구성",
                target_section="industry_kpi",
                data_keys=["owned", "leased", "outsourced"],
                priority=2,
                description="차량 보유 형태별 구성 (자가/리스/외주)",
            ),
            IndustryChartRecommendation(
                chart_type="line",
                title_template="정시 배송률·클레임 추이",
                target_section="industry_kpi",
                data_keys=["otd", "claims_ratio"],
                priority=2,
                description="정시 배송률 및 클레임 비율 시계열",
            ),
            IndustryChartRecommendation(
                chart_type="donut",
                title_template="운송 모드 비중",
                target_section="industry_overview",
                data_keys=["road", "sea", "air", "rail"],
                priority=3,
                description="육상/해상/항공/철도 운송 모드 비중",
            ),
        ]

    def get_narrative_variant(self) -> IndustryVariant:
        """LogisticsVariant 인스턴스를 반환한다."""
        from src.narrative_generator.prompts.industry_variants.logistics import (
            LogisticsVariant,
        )

        return LogisticsVariant()

    def get_risk_categories(self) -> list[RiskCategory]:
        """물류 리스크 카테고리 4개를 반환한다."""
        return [
            RiskCategory(
                category_id="fuel_price",
                name_kr="유가 변동",
                name_en="Fuel Price Volatility",
                description="유류비 변동에 따른 운영 비용 변동 리스크",
                risk_factors=[
                    "국제 유가 급등",
                    "유류할증료 전가 한계",
                    "친환경 연료 전환 비용",
                ],
            ),
            RiskCategory(
                category_id="driver_shortage",
                name_kr="운전인력 부족",
                name_en="Driver Shortage",
                description="운전기사·물류인력 확보 어려움",
                risk_factors=[
                    "고령화에 따른 인력 감소",
                    "인건비 상승",
                    "근로시간 규제 강화",
                ],
            ),
            RiskCategory(
                category_id="regulatory_transport",
                name_kr="운송 규제",
                name_en="Transport Regulation",
                description="운송·환경 규제 변화에 따른 비용 증가",
                risk_factors=[
                    "배출가스 규제 강화",
                    "도로 통행 제한",
                    "위험물 운송 규제",
                ],
            ),
            RiskCategory(
                category_id="seasonal_demand",
                name_kr="계절성 수요",
                name_en="Seasonal Demand Risk",
                description="물동량 계절 변동에 따른 수익성 불안정",
                risk_factors=[
                    "비수기 가동률 하락",
                    "성수기 용량 부족",
                    "특수 이벤트(명절 등) 수요 집중",
                ],
            ),
        ]
