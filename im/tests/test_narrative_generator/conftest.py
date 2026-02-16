"""Narrative Generator 테스트 공유 픽스처.

> 마지막 수정: 2026-02-10 12:08:25

IMDocumentData, FinancialStatements 등 내러티브 생성 테스트에서 공유하는
pytest 픽스처를 정의한다. 외부 API 호출 없이 모든 테스트가 동작해야 한다.
"""

from __future__ import annotations

import pytest

from src.design_renderer.im_document import (
    CompanyOverview,
    ContactInfo,
    DealStructure,
    FinancialStatements,
    GrowthStrategy,
    IMDocumentData,
    IMStyle,
    ManagementMember,
    MarketData,
    ShareholderInfo,
    TransactionType,
)


# ---------------------------------------------------------------------------
# 최소 재무 데이터 (3개년)
# ---------------------------------------------------------------------------


@pytest.fixture()
def minimal_financial_statements() -> FinancialStatements:
    """3개년 최소 재무 데이터."""
    return FinancialStatements(
        revenue={"2022": 100_000, "2023": 120_000, "2024": 150_000},
        cost_of_goods_sold={"2022": 60_000, "2023": 70_000, "2024": 85_000},
        gross_profit={"2022": 40_000, "2023": 50_000, "2024": 65_000},
        operating_income={"2022": 15_000, "2023": 20_000, "2024": 28_000},
        ebitda={"2022": 20_000, "2023": 26_000, "2024": 35_000},
        net_income={"2022": 10_000, "2023": 14_000, "2024": 20_000},
        sga_expenses={"2022": 25_000, "2023": 30_000, "2024": 37_000},
        total_assets={"2022": 200_000, "2023": 250_000, "2024": 300_000},
        total_liabilities={"2022": 80_000, "2023": 90_000, "2024": 100_000},
        total_equity={"2022": 120_000, "2023": 160_000, "2024": 200_000},
        cash_and_equivalents={"2022": 30_000, "2023": 40_000, "2024": 55_000},
        total_debt={"2022": 50_000, "2023": 45_000, "2024": 40_000},
        operating_cash_flow={"2022": 18_000, "2023": 24_000, "2024": 32_000},
        capex={"2022": 5_000, "2023": 6_000, "2024": 8_000},
        free_cash_flow={"2022": 13_000, "2023": 18_000, "2024": 24_000},
    )


# ---------------------------------------------------------------------------
# 최소 IMDocumentData
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_im_data(
    minimal_financial_statements: FinancialStatements,
) -> IMDocumentData:
    """내러티브 생성 테스트용 최소 IMDocumentData."""
    data = IMDocumentData(
        project_name="Project TEST",
        company_name_kr="테스트기업",
        company_name_en="Test Corp",
        corp_code="00123456",
        date="2026-02-10",
        im_style=IMStyle.FULL,
        financial_statements=minimal_financial_statements,
        investment_highlights=[
            "매출 CAGR 22.5% (3개년)",
            "영업이익률 18.7%로 업계 상위",
            "안정적 현금흐름 및 낮은 부채비율",
        ],
        market_data=MarketData(
            tam=500_000,
            sam=200_000,
            som=50_000,
            market_growth_rate=0.08,
        ),
        deal_structure=DealStructure(
            seller="테스트PE",
            stake_pct=0.60,
            deal_background="전략적 포트폴리오 재구성",
            transaction_type=TransactionType.MA,
            valuation_low=500_000,
            valuation_high=700_000,
            valuation_method="EV/EBITDA",
        ),
        company_overview=CompanyOverview(
            history=[{"year": "2010", "event": "설립"}],
            business_model="B2B IT 서비스",
            key_products=["클라우드 인프라"],
            employee_count=300,
        ),
        management_team=[
            ManagementMember(
                name="이대표",
                title="대표이사",
                role="CEO",
                career=["前 삼성전자 VP"],
            ),
        ],
        shareholders=[
            ShareholderInfo(name="테스트PE", stake_pct=0.60, category="최대주주"),
        ],
        growth_strategy=GrowthStrategy(
            organic_growth=["기존 사업 확대"],
            new_business=["AI SaaS 플랫폼"],
        ),
        contacts=[
            ContactInfo(
                name="홍길동",
                title="Managing Director",
                email="hong@amic.co.kr",
            ),
        ],
        narratives={
            "executive_summary": "테스트기업은 국내 IT 서비스 시장의 선도기업으로...",
            "financial_analysis": "최근 3개년 매출은 연평균 22.5% 성장하였으며...",
        },
    )
    data.compute_derived_metrics()
    return data
