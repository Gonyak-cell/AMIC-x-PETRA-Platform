"""테크/SaaS 산업 모듈."""

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
class FDDTechSaaSModule(FDDIndustryModule):
    """테크/SaaS 산업 FDD 모듈.

    R&D 자본화, SBC, SaaS 지표(ARR/NRR), 음의 NWC 허용 등 반영.
    """

    industry_id = "tech"
    industry_name_kr = "테크/SaaS"
    industry_name_en = "Technology/SaaS"

    def get_adjustment_rules(self) -> list[FDDAdjustmentRule]:
        return [
            FDDAdjustmentRule(
                rule_id="tech_rnd_capitalize",
                category="NORMALIZATION",
                keywords=["연구개발비", "R&D", "개발비상각", "연구비", "기술개발"],
                description_kr="R&D 비용 자본화/정상화 조정",
                description_en="R&D capitalization normalization",
                default_confidence=Decimal("65.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="tech_sbc",
                category="NON_RECURRING",
                keywords=[
                    "주식보상",
                    "스톡옵션",
                    "stock compensation",
                    "SBC",
                    "RSU",
                    "stock-based",
                    "주식매수선택권",
                ],
                description_kr="주식기반보상 비용 add-back",
                description_en="Stock-based compensation add-back",
                default_confidence=Decimal("75.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="tech_customer_acquisition",
                category="NORMALIZATION",
                keywords=[
                    "고객획득",
                    "CAC",
                    "마케팅비",
                    "프로모션",
                    "acquisition cost",
                ],
                description_kr="고객획득비용 정상화 (성장 투자 vs 운영비)",
                description_en="Customer acquisition cost normalization",
                default_confidence=Decimal("50.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="tech_hosting_migration",
                category="NON_RECURRING",
                keywords=["클라우드이전", "마이그레이션", "migration", "인프라전환"],
                description_kr="일회성 클라우드/인프라 이전 비용",
                description_en="One-time cloud/infrastructure migration cost",
                default_confidence=Decimal("70.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="tech_one_off",
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
                norm_id="tech_saas_nwc",
                description=(
                    "SaaS 기업은 선수수익(deferred revenue) 구조로 "
                    "음의 NWC가 일반적. 매출채권이 낮고 선불 구독 모델."
                ),
                typical_nwc_days=(-30, 15),
                negative_nwc_acceptable=True,
                seasonal_pattern=None,
                key_categories=["AR", "DEFERRED_REVENUE", "ACCRUALS"],
            ),
            FDDNWCNorm(
                norm_id="tech_prepaid_hosting",
                description="선급 호스팅/클라우드 비용이 NWC에 포함될 수 있음",
                typical_nwc_days=(-30, 15),
                negative_nwc_acceptable=True,
                seasonal_pattern=None,
                key_categories=["PREPAID_EXPENSES"],
            ),
        ]

    def get_debt_classifications(self) -> list[FDDDebtClassification]:
        return [
            FDDDebtClassification(
                rule_id="tech_convertible",
                description="전환사채(CB), SAFE 등 테크 스타트업 전형적 자금조달 — debt-like 분류",
                additional_debt_like_keywords=[
                    "전환사채",
                    "convertible",
                    "CB",
                    "SAFE",
                    "신주인수권부사채",
                    "BW",
                    "메자닌",
                ],
                additional_cash_like_keywords=[],
                special_treatments={
                    "LEASE_LIABILITIES": "사무실 리스 — 일반적으로 유의미",
                    "DEFERRED_REVENUE": "선수수익은 NWC 항목으로 분류 (debt-like 제외)",
                },
            ),
        ]

    def get_narrative_templates(self) -> list[FDDNarrativeTemplate]:
        return [
            FDDNarrativeTemplate(
                section_id="executive_summary",
                template_text=(
                    "SaaS/구독 모델 특성을 반영한 FDD 분석:\n"
                    "- ARR/MRR 기반 수익 지속성 평가\n"
                    "- 높은 R&D 비중의 EBITDA 정상화 관점\n"
                    "- 음의 NWC 구조(선수수익)의 긍정적 해석"
                ),
                emphasis_areas=[
                    "ARR/MRR 성장률 및 NRR (순매출유지율)",
                    "R&D 자본화/SBC 조정의 EBITDA 영향",
                    "CAC 회수 기간 및 LTV/CAC 비율",
                    "이탈률(Churn Rate) 추세와 수익 지속성",
                ],
                terminology_overrides={
                    "매출액": "ARR 또는 매출액",
                    "재고": "해당 없음 (소프트웨어/서비스)",
                    "설비투자": "R&D 투자 및 클라우드 인프라",
                },
            ),
        ]

    def get_kpi_benchmarks(self) -> list[FDDKPIBenchmark]:
        return [
            FDDKPIBenchmark(
                kpi_id="tech_arr_growth",
                name_kr="ARR 성장률",
                name_en="ARR Growth Rate",
                unit="%",
                benchmark_range=(20.0, 80.0),
                formula="(ARR_t - ARR_t-1) / ARR_t-1 × 100",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="tech_nrr",
                name_kr="순매출유지율",
                name_en="Net Revenue Retention (NRR)",
                unit="%",
                benchmark_range=(100.0, 130.0),
                formula="(시작 ARR + 확장 - 축소 - 이탈) / 시작 ARR × 100",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="tech_rule_of_40",
                name_kr="Rule of 40",
                name_en="Rule of 40",
                unit="%",
                benchmark_range=(40.0, 80.0),
                formula="Revenue Growth % + EBITDA Margin %",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="tech_ltv_cac",
                name_kr="LTV/CAC 비율",
                name_en="LTV/CAC Ratio",
                unit="x",
                benchmark_range=(3.0, 5.0),
                formula="Customer Lifetime Value / Customer Acquisition Cost",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="tech_gross_margin",
                name_kr="매출총이익률",
                name_en="Gross Margin",
                unit="%",
                benchmark_range=(60.0, 85.0),
                formula="Gross Profit / Revenue × 100",
                higher_is_better=True,
            ),
        ]
