"""헬스케어/바이오 산업 모듈."""

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
class FDDHealthcareModule(FDDIndustryModule):
    """헬스케어/바이오 산업 FDD 모듈.

    임상시험 비용, R&D 파이프라인, 규제 비용, 로열티 부채 등 반영.
    """

    industry_id = "healthcare"
    industry_name_kr = "헬스케어/바이오"
    industry_name_en = "Healthcare/Biotech"

    def get_adjustment_rules(self) -> list[FDDAdjustmentRule]:
        return [
            FDDAdjustmentRule(
                rule_id="hc_clinical_trial",
                category="NORMALIZATION",
                keywords=[
                    "임상시험", "clinical trial", "Phase I", "Phase II", "Phase III",
                    "임상", "CRO", "clinical study",
                ],
                description_kr="임상시험 비용 정상화 (진행 단계별 차등)",
                description_en="Clinical trial cost normalization by phase",
                default_confidence=Decimal("60.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="hc_rnd",
                category="NORMALIZATION",
                keywords=["연구개발비", "R&D", "개발비", "연구비", "신약개발"],
                description_kr="R&D 비용 정상화",
                description_en="R&D expenditure normalization",
                default_confidence=Decimal("55.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="hc_regulatory",
                category="NON_RECURRING",
                keywords=[
                    "허가비용", "FDA", "식약처", "MFDS", "regulatory",
                    "인허가", "GMP", "cGMP",
                ],
                description_kr="규제/인허가 일회성 비용",
                description_en="Regulatory one-time filing costs",
                default_confidence=Decimal("65.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="hc_milestone",
                category="NON_RECURRING",
                keywords=["마일스톤", "milestone", "기술이전", "license-out", "upfront"],
                description_kr="마일스톤/기술이전 수익 정상화",
                description_en="Milestone/license-out revenue normalization",
                default_confidence=Decimal("70.00"),
                direction="DEDUCT",
            ),
            FDDAdjustmentRule(
                rule_id="hc_one_off",
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
                norm_id="hc_inventory",
                description=(
                    "헬스케어/바이오 기업은 원재료·재공품·완제품 재고가 중요. "
                    "유효기간 관리 및 GMP 요건으로 재고 수준 높음."
                ),
                typical_nwc_days=(30, 90),
                negative_nwc_acceptable=False,
                seasonal_pattern=None,
                key_categories=["AR", "INVENTORY", "AP", "ACCRUALS"],
            ),
        ]

    def get_debt_classifications(self) -> list[FDDDebtClassification]:
        return [
            FDDDebtClassification(
                rule_id="hc_royalty_debt",
                description="로열티 부채, 마일스톤 지급 의무, 조건부 대가(contingent consideration)",
                additional_debt_like_keywords=[
                    "로열티부채", "royalty obligation", "마일스톤지급",
                    "contingent consideration", "조건부대가", "earn-out",
                ],
                additional_cash_like_keywords=[
                    "정부보조금", "government grant", "연구지원금",
                ],
                special_treatments={
                    "CONTINGENT_CONSIDERATION": "공정가치 평가 필요 — NPV 방식",
                    "GOVERNMENT_GRANTS": "환급 의무 여부에 따라 NWC vs Debt-like 판단",
                },
            ),
        ]

    def get_narrative_templates(self) -> list[FDDNarrativeTemplate]:
        return [
            FDDNarrativeTemplate(
                section_id="executive_summary",
                template_text=(
                    "헬스케어/바이오 FDD 분석 시 고려 사항:\n"
                    "- 파이프라인 가치 및 임상 단계별 성공 확률 반영\n"
                    "- R&D 비용 자본화 여부의 EBITDA 영향\n"
                    "- 마일스톤/기술이전 수익의 비경상 처리"
                ),
                emphasis_areas=[
                    "R&D/매출 비율 및 파이프라인 rNPV",
                    "임상시험 단계별 비용 정상화",
                    "특허 잔여 수명 및 제네릭 리스크",
                    "규제 인허가(FDA/MFDS) 비용의 비경상 판단",
                ],
                terminology_overrides={
                    "매출액": "제품 매출 + 기술이전/로열티 수익",
                    "재고": "원료의약품·완제의약품 (유효기간 관리)",
                    "R&D": "임상시험 비용 + 기초연구 비용",
                },
            ),
        ]

    def get_kpi_benchmarks(self) -> list[FDDKPIBenchmark]:
        return [
            FDDKPIBenchmark(
                kpi_id="hc_rnd_revenue",
                name_kr="R&D/매출 비율",
                name_en="R&D/Revenue Ratio",
                unit="%",
                benchmark_range=(15.0, 40.0),
                formula="R&D Expense / Revenue × 100",
                higher_is_better=False,
            ),
            FDDKPIBenchmark(
                kpi_id="hc_gross_margin",
                name_kr="매출총이익률",
                name_en="Gross Margin",
                unit="%",
                benchmark_range=(55.0, 80.0),
                formula="Gross Profit / Revenue × 100",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="hc_pipeline_value",
                name_kr="파이프라인 rNPV",
                name_en="Pipeline rNPV",
                unit="M",
                benchmark_range=(50.0, 500.0),
                formula="Σ (Phase별 확률 × NPV)",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="hc_patent_life",
                name_kr="특허 잔여 수명",
                name_en="Patent Remaining Life",
                unit="years",
                benchmark_range=(5.0, 15.0),
                formula="특허 만료일 - 현재일",
                higher_is_better=True,
            ),
        ]
