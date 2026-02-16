"""헬스케어/바이오 산업 모듈 (A2).

> 마지막 수정: 2026-02-11 14:00:00

파이프라인 차트, rNPV, 임상 데이터, 특허 수명주기, 시장접근성 등
헬스케어/바이오에 특화된 KPI·차트·재무 가중치를 정의한다.
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
class HealthcareModule(IndustryModule):
    """헬스케어/바이오 산업 모듈.

    R&D 파이프라인, rNPV, 임상 데이터, 특허 수명주기, 시장접근성 등
    바이오/제약 핵심 KPI와 재무 가중치를 제공한다.
    """

    industry_id = "healthcare"
    industry_name_kr = "헬스케어/바이오"
    industry_name_en = "Healthcare"

    def get_kpis(self) -> list[IndustryKPI]:
        """헬스케어 핵심 KPI 8개를 반환한다."""
        return [
            IndustryKPI(
                kpi_id="pipeline_count",
                name_kr="파이프라인 건수",
                name_en="Pipeline Count",
                unit=KPIUnit.COUNT,
                description="임상 단계별 파이프라인 총 건수",
                display_format="{:.0f}건",
                higher_is_better=True,
            ),
            IndustryKPI(
                kpi_id="rnpv",
                name_kr="위험조정순현재가치",
                name_en="Risk-adjusted NPV",
                unit=KPIUnit.CURRENCY_KRW,
                description="임상 성공 확률을 반영한 순현재가치",
                formula="Σ(단계별 성공확률 × 기대 현금흐름의 NPV)",
                display_format="{:,.0f}억원",
                higher_is_better=True,
            ),
            IndustryKPI(
                kpi_id="phase3_success",
                name_kr="Phase III 성공률",
                name_en="Phase III Success Rate",
                unit=KPIUnit.PERCENTAGE,
                description="Phase III 임상에서 승인까지 전환율",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(50, 70),
            ),
            IndustryKPI(
                kpi_id="patent_remaining",
                name_kr="특허 잔여기간",
                name_en="Patent Remaining Life",
                unit=KPIUnit.DAYS,
                description="주요 제품 특허의 가중평균 잔여기간",
                display_format="{:.0f}일",
                higher_is_better=True,
            ),
            IndustryKPI(
                kpi_id="rd_ratio",
                name_kr="R&D/매출 비율",
                name_en="R&D to Revenue Ratio",
                unit=KPIUnit.PERCENTAGE,
                description="매출 대비 R&D 투자 비율",
                formula="R&D 비용 / 매출액 × 100",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(15, 40),
            ),
            IndustryKPI(
                kpi_id="market_access",
                name_kr="시장접근성 점수",
                name_en="Market Access Score",
                unit=KPIUnit.PERCENTAGE,
                description="주요 시장 접근성 종합 평가 점수",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(50, 90),
            ),
            IndustryKPI(
                kpi_id="regulatory_status",
                name_kr="인허가 진행률",
                name_en="Regulatory Approval Rate",
                unit=KPIUnit.PERCENTAGE,
                description="인허가 신청 대비 승인 비율",
                display_format="{:.1f}%",
                higher_is_better=True,
            ),
            IndustryKPI(
                kpi_id="reimbursement",
                name_kr="급여 적용률",
                name_en="Reimbursement Coverage",
                unit=KPIUnit.PERCENTAGE,
                description="건강보험 급여 적용 제품 매출 비중",
                display_format="{:.1f}%",
                higher_is_better=True,
                benchmark_range=(60, 95),
            ),
        ]

    def get_financial_weights(self) -> dict[str, float]:
        """헬스케어 재무 가중치를 반환한다."""
        return {
            "rd_investment": 0.30,
            "pipeline_value": 0.25,
            "revenue_growth": 0.15,
            "gross_margin": 0.15,
            "patent_portfolio": 0.15,
        }

    def get_chart_recommendations(self) -> list[IndustryChartRecommendation]:
        """헬스케어 추천 차트 5개를 반환한다."""
        return [
            IndustryChartRecommendation(
                chart_type="stacked_bar",
                title_template="R&D 파이프라인 현황",
                target_section="industry_kpi",
                data_keys=["phase1", "phase2", "phase3", "approved"],
                priority=1,
                description="임상 단계별 파이프라인 분포",
            ),
            IndustryChartRecommendation(
                chart_type="waterfall",
                title_template="rNPV 산출 근거",
                target_section="industry_kpi",
                data_keys=["base_npv", "prob_adj", "cost_adj", "rnpv"],
                priority=1,
                description="rNPV 구성 요소 분해",
            ),
            IndustryChartRecommendation(
                chart_type="line",
                title_template="특허 수명주기",
                target_section="industry_overview",
                data_keys=["patent_years", "revenue_projection"],
                priority=2,
                description="특허 만료 일정과 매출 영향 예측",
            ),
            IndustryChartRecommendation(
                chart_type="donut",
                title_template="매출 구성 (제품별)",
                target_section="financial_analysis",
                data_keys=["product_revenue"],
                priority=2,
                description="제품별 매출 비중",
            ),
            IndustryChartRecommendation(
                chart_type="hbar",
                title_template="시장접근성 비교",
                target_section="industry_overview",
                data_keys=["market", "access_score"],
                priority=3,
                description="치료 영역별 시장접근성 점수 비교",
            ),
        ]

    def get_narrative_variant(self) -> IndustryVariant:
        """HealthcareVariant 인스턴스를 반환한다."""
        from src.narrative_generator.prompts.industry_variants.healthcare import (
            HealthcareVariant,
        )

        return HealthcareVariant()

    def get_risk_categories(self) -> list[RiskCategory]:
        """헬스케어 리스크 카테고리 4개를 반환한다."""
        return [
            RiskCategory(
                category_id="regulatory",
                name_kr="규제 리스크",
                name_en="Regulatory Risk",
                description="FDA/MFDS 등 인허가 지연·반려 리스크",
                risk_factors=[
                    "임상시험 설계 이슈",
                    "규제 기준 변경",
                    "허가 심사 지연",
                ],
            ),
            RiskCategory(
                category_id="clinical_trial",
                name_kr="임상시험 실패",
                name_en="Clinical Trial Failure",
                description="임상 단계에서의 유효성·안전성 실패 리스크",
                risk_factors=[
                    "Phase III 실패",
                    "부작용 발생",
                    "대조군 대비 비열등성 미입증",
                ],
            ),
            RiskCategory(
                category_id="patent_cliff",
                name_kr="특허 만료",
                name_en="Patent Cliff",
                description="주요 제품 특허 만료에 따른 매출 급감 리스크",
                risk_factors=[
                    "블록버스터 제품 특허 만료",
                    "제네릭/바이오시밀러 진입",
                    "후속 파이프라인 부재",
                ],
            ),
            RiskCategory(
                category_id="reimbursement_change",
                name_kr="급여 정책 변동",
                name_en="Reimbursement Policy Change",
                description="건강보험 급여·약가 정책 변경 리스크",
                risk_factors=[
                    "약가 인하 정책",
                    "급여 기준 변경",
                    "가치기반 급여(VBP) 도입",
                ],
            ),
        ]
