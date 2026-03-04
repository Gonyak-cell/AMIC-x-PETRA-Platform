"""물류 산업 모듈."""

from __future__ import annotations

from decimal import Decimal

from app.industry.base import FDDIndustryModule
from app.industry.models import (
    FDDAdjustmentRule,
    FDDDebtClassification,
    FDDKPIBenchmark,
    FDDNarrativeTemplate,
    FDDNWCNorm,
)
from app.industry.registry import register_fdd_industry


@register_fdd_industry
class FDDLogisticsModule(FDDIndustryModule):
    """물류 산업 FDD 모듈.

    연료비 정상화, 감가상각 정상화, 차량/선박 금융리스 등 반영.
    """

    industry_id = "logistics"
    industry_name_kr = "물류"
    industry_name_en = "Logistics"

    def get_adjustment_rules(self) -> list[FDDAdjustmentRule]:
        return [
            FDDAdjustmentRule(
                rule_id="log_fuel_normalization",
                category="NORMALIZATION",
                keywords=[
                    "유류비",
                    "연료비",
                    "fuel cost",
                    "경유",
                    "diesel",
                    "LNG",
                    "CNG",
                    "유류대",
                    "주유",
                ],
                description_kr="유류비 정상화 (유가 변동 제거)",
                description_en="Fuel cost normalization (oil price volatility removal)",
                default_confidence=Decimal("60.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="log_depreciation",
                category="NORMALIZATION",
                keywords=[
                    "감가상각",
                    "depreciation",
                    "차량감가",
                    "선박감가",
                    "항공기감가",
                    "fleet depreciation",
                ],
                description_kr="운송수단 감가상각 정상화 (내용연수 검토)",
                description_en="Fleet depreciation normalization (useful life review)",
                default_confidence=Decimal("55.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="log_fleet_disposal",
                category="NON_RECURRING",
                keywords=[
                    "차량매각",
                    "선박매각",
                    "fleet disposal",
                    "처분손익",
                    "자산처분",
                    "asset disposal",
                ],
                description_kr="운송수단 일회성 처분손익",
                description_en="Fleet disposal one-time gain/loss",
                default_confidence=Decimal("70.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="log_route_optimization",
                category="NON_RECURRING",
                keywords=[
                    "노선개편",
                    "route optimization",
                    "네트워크재편",
                    "허브이전",
                    "거점이전",
                ],
                description_kr="노선/네트워크 재편 일회성 비용",
                description_en="Route/network optimization one-time cost",
                default_confidence=Decimal("65.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="log_one_off",
                category="NON_RECURRING",
                keywords=["일회성", "비경상", "one-off", "one-time", "non-recurring"],
                description_kr="일회성 비용/수익 조정",
                description_en="One-off cost/revenue adjustment",
                default_confidence=Decimal("60.00"),
                direction="ADD_BACK",
            ),
        ]

    def get_nwc_norms(self) -> list[FDDNWCNorm]:
        return [
            FDDNWCNorm(
                norm_id="log_freight_receivable",
                description=(
                    "물류업은 매출채권(운임채권)이 높고, 선급 운임·보험료가 NWC에 영향. "
                    "대형 화주 의존도가 높으면 AR 집중도 리스크."
                ),
                typical_nwc_days=(20, 60),
                negative_nwc_acceptable=False,
                seasonal_pattern="Q4_HIGH",
                key_categories=["AR", "AP", "PREPAID_EXPENSES", "ACCRUALS"],
            ),
        ]

    def get_debt_classifications(self) -> list[FDDDebtClassification]:
        return [
            FDDDebtClassification(
                rule_id="log_fleet_finance",
                description="차량/선박/항공기 금융리스, 운영리스(IFRS 16) — 물류업 핵심 부채",
                additional_debt_like_keywords=[
                    "차량리스",
                    "선박금융",
                    "ship finance",
                    "항공기금융",
                    "fleet lease",
                    "운송장비리스",
                    "차량할부",
                ],
                additional_cash_like_keywords=[
                    "운임선수금",
                    "freight prepayment",
                ],
                special_treatments={
                    "LEASE_LIABILITIES": "운송수단 리스가 주요 — 운영리스 vs 금융리스 구분 필수",
                    "FUEL_HEDGING": "유류 헤지 파생상품은 시가평가 후 net debt 판단",
                },
            ),
        ]

    def get_narrative_templates(self) -> list[FDDNarrativeTemplate]:
        return [
            FDDNarrativeTemplate(
                section_id="executive_summary",
                template_text=(
                    "물류 산업 FDD 분석 시 고려 사항:\n"
                    "- 유류비 변동의 EBITDA 정상화 (유가 노이즈 제거)\n"
                    "- 운송수단(차량/선박) 리스부채의 Net Debt 포함 여부\n"
                    "- 차량가동률과 고정비 레버리지 효과"
                ),
                emphasis_areas=[
                    "유류비/매출 비율 추세 및 유가 정상화",
                    "차량가동률(Fleet Utilization) 및 고정비 구조",
                    "IFRS 16 리스부채의 Net Debt 분류",
                    "톤·km당 매출 및 네트워크 효율성",
                ],
                terminology_overrides={
                    "매출액": "운임수익 (화물 + 택배 + 포워딩)",
                    "설비투자": "차량·선박·항공기 구입 및 교체",
                    "감가상각": "운송수단 감가상각 (내용연수 검토 필수)",
                },
            ),
        ]

    def get_kpi_benchmarks(self) -> list[FDDKPIBenchmark]:
        return [
            FDDKPIBenchmark(
                kpi_id="log_ebitda_margin",
                name_kr="EBITDA 마진",
                name_en="EBITDA Margin",
                unit="%",
                benchmark_range=(8.0, 18.0),
                formula="EBITDA / Revenue × 100",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="log_fleet_utilization",
                name_kr="차량가동률",
                name_en="Fleet Utilization Rate",
                unit="%",
                benchmark_range=(70.0, 95.0),
                formula="Active Fleet / Total Fleet × 100",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="log_revenue_per_ton_km",
                name_kr="톤·km당 매출",
                name_en="Revenue per Ton-km",
                unit="KRW",
                benchmark_range=(50.0, 200.0),
                formula="Revenue / Total Ton-km",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="log_fuel_cost_ratio",
                name_kr="유류비 비중",
                name_en="Fuel Cost Ratio",
                unit="%",
                benchmark_range=(15.0, 35.0),
                formula="Fuel Cost / Revenue × 100",
                higher_is_better=False,
            ),
        ]
