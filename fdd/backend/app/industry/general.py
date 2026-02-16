"""일반(General) 산업 모듈 — 기본 폴백."""

from __future__ import annotations

from decimal import Decimal

from app.industry.base import FDDIndustryModule
from app.industry.models import (
    FDDAdjustmentRule,
    FDDDebtClassification,
    FDDKPIBenchmark,
    FDDNWCNorm,
)
from app.industry.registry import register_fdd_industry


@register_fdd_industry
class FDDGeneralModule(FDDIndustryModule):
    """범용 산업 모듈. 산업 미지정 시 기본값으로 사용."""

    industry_id = "general"
    industry_name_kr = "일반"
    industry_name_en = "General"

    def get_adjustment_rules(self) -> list[FDDAdjustmentRule]:
        return [
            FDDAdjustmentRule(
                rule_id="gen_one_off",
                category="NON_RECURRING",
                keywords=["일회성", "비경상", "one-off", "one-time", "non-recurring"],
                description_kr="일회성 비용/수익 조정",
                description_en="One-off cost/revenue adjustment",
                default_confidence=Decimal("60.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="gen_restructuring",
                category="NON_RECURRING",
                keywords=["구조조정", "restructuring", "희망퇴직", "정리해고"],
                description_kr="구조조정 비용 add-back",
                description_en="Restructuring cost add-back",
                default_confidence=Decimal("70.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="gen_litigation",
                category="NON_RECURRING",
                keywords=["소송", "litigation", "분쟁", "합의금", "settlement"],
                description_kr="소송/합의 비용 조정",
                description_en="Litigation/settlement cost adjustment",
                default_confidence=Decimal("65.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="gen_related_party",
                category="NORMALIZATION",
                keywords=["특수관계", "related party", "관계자거래", "특관자"],
                description_kr="특수관계자 거래 정상화",
                description_en="Related party transaction normalization",
                default_confidence=Decimal("55.00"),
                direction="ADD_BACK",
            ),
        ]

    def get_nwc_norms(self) -> list[FDDNWCNorm]:
        return [
            FDDNWCNorm(
                norm_id="gen_standard",
                description="일반적인 NWC 수준",
                typical_nwc_days=(15, 60),
                negative_nwc_acceptable=False,
                seasonal_pattern=None,
                key_categories=["AR", "AP", "INVENTORY", "ACCRUALS"],
            ),
        ]

    def get_debt_classifications(self) -> list[FDDDebtClassification]:
        return [
            FDDDebtClassification(
                rule_id="gen_standard",
                description="일반 부채 분류 기준",
                additional_debt_like_keywords=[],
                additional_cash_like_keywords=[],
                special_treatments={},
            ),
        ]

    def get_kpi_benchmarks(self) -> list[FDDKPIBenchmark]:
        return [
            FDDKPIBenchmark(
                kpi_id="gen_ebitda_margin",
                name_kr="EBITDA 마진",
                name_en="EBITDA Margin",
                unit="%",
                benchmark_range=(10.0, 25.0),
                formula="EBITDA / Revenue × 100",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="gen_revenue_growth",
                name_kr="매출 성장률",
                name_en="Revenue Growth",
                unit="%",
                benchmark_range=(3.0, 15.0),
                formula="(Revenue_t - Revenue_t-1) / Revenue_t-1 × 100",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="gen_debt_equity",
                name_kr="부채비율",
                name_en="Debt/Equity Ratio",
                unit="x",
                benchmark_range=(0.5, 2.0),
                formula="Total Debt / Total Equity",
                higher_is_better=False,
            ),
        ]
