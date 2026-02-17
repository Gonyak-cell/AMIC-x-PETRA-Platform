"""제조업 산업 모듈."""

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
class FDDManufacturingModule(FDDIndustryModule):
    """제조업 산업 FDD 모듈.

    CAPEX 정상화, 재고평가 조정, 높은 재고·계절성, 설비금융 등 반영.
    """

    industry_id = "manufacturing"
    industry_name_kr = "제조업"
    industry_name_en = "Manufacturing"

    def get_adjustment_rules(self) -> list[FDDAdjustmentRule]:
        return [
            FDDAdjustmentRule(
                rule_id="mfg_capex_normalization",
                category="NORMALIZATION",
                keywords=[
                    "설비투자", "CAPEX", "자본적지출", "capital expenditure",
                    "시설투자", "생산설비",
                ],
                description_kr="CAPEX 정상화 (유지보수 vs 성장 CAPEX 구분)",
                description_en="CAPEX normalization (maintenance vs growth)",
                default_confidence=Decimal("60.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="mfg_inventory_valuation",
                category="NORMALIZATION",
                keywords=[
                    "재고평가", "재고자산", "inventory", "평가손실",
                    "재고감모", "obsolescence", "write-down",
                ],
                description_kr="재고평가 손실/감모 조정",
                description_en="Inventory valuation/write-down adjustment",
                default_confidence=Decimal("65.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="mfg_plant_closure",
                category="NON_RECURRING",
                keywords=[
                    "공장폐쇄", "plant closure", "라인철거", "사업장이전",
                    "공장이전", "relocation",
                ],
                description_kr="공장 폐쇄/이전 일회성 비용",
                description_en="Plant closure/relocation one-time cost",
                default_confidence=Decimal("75.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="mfg_warranty",
                category="NORMALIZATION",
                keywords=["품질보증", "warranty", "하자보수", "A/S", "보증비용"],
                description_kr="품질보증 비용 정상화",
                description_en="Warranty cost normalization",
                default_confidence=Decimal("55.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="mfg_one_off",
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
                norm_id="mfg_high_inventory",
                description=(
                    "제조업은 원재료·재공품·완제품 3단계 재고로 NWC 수준이 높음. "
                    "재고회전일수 관리가 핵심. Q4 수요 증가로 계절성 있음."
                ),
                typical_nwc_days=(45, 120),
                negative_nwc_acceptable=False,
                seasonal_pattern="Q4_HIGH",
                key_categories=["AR", "INVENTORY", "AP", "PREPAID_EXPENSES"],
            ),
        ]

    def get_debt_classifications(self) -> list[FDDDebtClassification]:
        return [
            FDDDebtClassification(
                rule_id="mfg_equipment_finance",
                description="설비금융, 리스부채, 장기 구매 계약 — 제조업 고유 부채 항목",
                additional_debt_like_keywords=[
                    "설비금융", "equipment finance", "산업은행", "시설자금",
                    "팩토링", "factoring",
                ],
                additional_cash_like_keywords=[
                    "매출채권보험금", "insurance receivable",
                ],
                special_treatments={
                    "LEASE_LIABILITIES": "공장·설비 리스가 주요 — IFRS 16 적용 판단 필수",
                    "CAPEX_COMMITMENTS": "미이행 CAPEX 약정은 debt-like 고려",
                },
            ),
        ]

    def get_narrative_templates(self) -> list[FDDNarrativeTemplate]:
        return [
            FDDNarrativeTemplate(
                section_id="executive_summary",
                template_text=(
                    "제조업 FDD 분석 시 고려 사항:\n"
                    "- CAPEX 구분 (유지보수 vs 성장) 및 EBITDA 영향\n"
                    "- 재고 3단계(원재료·재공품·완제품) 평가 적정성\n"
                    "- 설비 가동률과 감가상각 정상화"
                ),
                emphasis_areas=[
                    "CAPEX/매출 비율 및 유지보수 CAPEX 수준",
                    "재고회전율 추세 및 진부화 위험",
                    "설비종합효율(OEE) 및 가동률",
                    "원재료 가격 변동의 EBITDA 영향",
                ],
                terminology_overrides={
                    "매출원가": "제조원가 (원재료+노무+제조경비)",
                    "설비투자": "CAPEX (유지보수 + 성장)",
                    "재고": "원재료·재공품·완제품 3단계 재고",
                },
            ),
        ]

    def get_kpi_benchmarks(self) -> list[FDDKPIBenchmark]:
        return [
            FDDKPIBenchmark(
                kpi_id="mfg_oee",
                name_kr="설비종합효율",
                name_en="OEE (Overall Equipment Effectiveness)",
                unit="%",
                benchmark_range=(60.0, 85.0),
                formula="Availability × Performance × Quality",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="mfg_inventory_turnover",
                name_kr="재고회전율",
                name_en="Inventory Turnover",
                unit="x",
                benchmark_range=(4.0, 12.0),
                formula="COGS / Average Inventory",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="mfg_capex_revenue",
                name_kr="CAPEX/매출 비율",
                name_en="CAPEX/Revenue Ratio",
                unit="%",
                benchmark_range=(5.0, 20.0),
                formula="CAPEX / Revenue × 100",
                higher_is_better=False,
            ),
            FDDKPIBenchmark(
                kpi_id="mfg_ebitda_margin",
                name_kr="EBITDA 마진",
                name_en="EBITDA Margin",
                unit="%",
                benchmark_range=(10.0, 20.0),
                formula="EBITDA / Revenue × 100",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="mfg_yield_rate",
                name_kr="수율",
                name_en="Yield Rate",
                unit="%",
                benchmark_range=(90.0, 99.0),
                formula="Good Output / Total Output × 100",
                higher_is_better=True,
            ),
        ]
