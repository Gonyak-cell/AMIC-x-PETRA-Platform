"""금융서비스 산업 모듈."""

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
class FDDFinancialServicesModule(FDDIndustryModule):
    """금융서비스 산업 FDD 모듈.

    대손충당금 정상화, 예수금/대출금 특수 취급, 후순위채·조건부자본 등 반영.
    """

    industry_id = "financial_services"
    industry_name_kr = "금융서비스"
    industry_name_en = "Financial Services"

    def get_adjustment_rules(self) -> list[FDDAdjustmentRule]:
        return [
            FDDAdjustmentRule(
                rule_id="fin_provision",
                category="NORMALIZATION",
                keywords=[
                    "대손충당금",
                    "provision",
                    "loan loss",
                    "ECL",
                    "기대신용손실",
                    "충당금전입",
                    "대손상각",
                ],
                description_kr="대손충당금 정상화 (경기 순환 반영)",
                description_en="Loan loss provision normalization (through-the-cycle)",
                default_confidence=Decimal("55.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="fin_trading_pnl",
                category="NORMALIZATION",
                keywords=[
                    "트레이딩손익",
                    "trading P&L",
                    "유가증권평가",
                    "FVTPL",
                    "단기매매",
                    "파생상품",
                ],
                description_kr="트레이딩/투자 손익 정상화",
                description_en="Trading/investment P&L normalization",
                default_confidence=Decimal("50.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="fin_regulatory_fine",
                category="NON_RECURRING",
                keywords=[
                    "과징금",
                    "regulatory fine",
                    "제재",
                    "penalty",
                    "벌금",
                    "금감원",
                    "FSS",
                ],
                description_kr="규제 과징금/벌금 일회성 처리",
                description_en="Regulatory fine/penalty one-time treatment",
                default_confidence=Decimal("80.00"),
                direction="ADD_BACK",
            ),
            FDDAdjustmentRule(
                rule_id="fin_one_off",
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
                norm_id="fin_deposit_loan",
                description=(
                    "금융서비스는 예수금·대출금이 핵심 영업자산/부채. "
                    "전통적 NWC 개념 적용이 제한적 — "
                    "규제자본 관점의 분석이 더 유의미."
                ),
                typical_nwc_days=(0, 0),
                negative_nwc_acceptable=True,
                seasonal_pattern=None,
                key_categories=["DEPOSITS", "LOANS", "ACCRUALS"],
            ),
        ]

    def get_debt_classifications(self) -> list[FDDDebtClassification]:
        return [
            FDDDebtClassification(
                rule_id="fin_subordinated",
                description="후순위채, 조건부자본, 예수금 — 금융기관 특수 부채 항목",
                additional_debt_like_keywords=[
                    "후순위채",
                    "subordinated debt",
                    "조건부자본",
                    "contingent capital",
                    "CoCo",
                    "신종자본증권",
                    "영구채",
                    "perpetual bond",
                    "하이브리드",
                ],
                additional_cash_like_keywords=[
                    "지급준비금",
                    "reserve",
                    "중앙은행예치금",
                ],
                special_treatments={
                    "CUSTOMER_DEPOSITS": "예수금은 영업부채 — debt-like 제외 (NWC 항목)",
                    "REPO_LIABILITIES": "RP 매도는 단기 자금조달 — debt-like 판단 필요",
                    "REGULATORY_CAPITAL": "규제자본 요건 충족 여부 별도 분석 필요",
                },
            ),
        ]

    def get_narrative_templates(self) -> list[FDDNarrativeTemplate]:
        return [
            FDDNarrativeTemplate(
                section_id="executive_summary",
                template_text=(
                    "금융서비스 FDD 분석 시 고려 사항:\n"
                    "- 대손충당금 정상화 (경기 순환 반영, TTC 관점)\n"
                    "- 트레이딩/투자 손익의 EBITDA 제외 여부\n"
                    "- 규제자본 비율이 사업 지속성에 미치는 영향"
                ),
                emphasis_areas=[
                    "대손충당금(ECL) 정상화 및 Through-the-Cycle 분석",
                    "트레이딩 P&L vs 핵심 영업이익 구분",
                    "BIS 자본비율 / 규제자본 충족 여부",
                    "순이자마진(NIM) 추세 및 금리 민감도",
                ],
                terminology_overrides={
                    "매출액": "영업수익 (이자수익 + 비이자수익)",
                    "재고": "해당 없음 (금융서비스)",
                    "EBITDA": "Pre-Provision Operating Profit (PPOP)",
                },
            ),
        ]

    def get_kpi_benchmarks(self) -> list[FDDKPIBenchmark]:
        return [
            FDDKPIBenchmark(
                kpi_id="fin_roe",
                name_kr="자기자본이익률",
                name_en="Return on Equity (ROE)",
                unit="%",
                benchmark_range=(8.0, 18.0),
                formula="Net Income / Average Equity × 100",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="fin_nim",
                name_kr="순이자마진",
                name_en="Net Interest Margin (NIM)",
                unit="%",
                benchmark_range=(1.5, 4.0),
                formula="(Interest Income - Interest Expense) / Average Earning Assets × 100",
                higher_is_better=True,
            ),
            FDDKPIBenchmark(
                kpi_id="fin_cost_income",
                name_kr="경비율",
                name_en="Cost-to-Income Ratio",
                unit="%",
                benchmark_range=(40.0, 65.0),
                formula="Operating Expenses / Operating Income × 100",
                higher_is_better=False,
            ),
            FDDKPIBenchmark(
                kpi_id="fin_npl_ratio",
                name_kr="고정이하여신비율",
                name_en="NPL Ratio",
                unit="%",
                benchmark_range=(0.5, 3.0),
                formula="Non-Performing Loans / Total Loans × 100",
                higher_is_better=False,
            ),
        ]
