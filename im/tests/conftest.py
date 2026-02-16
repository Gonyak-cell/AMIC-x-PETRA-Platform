"""Pytest configuration and shared fixtures.

> 마지막 수정: 2026-02-11 21:00:00
"""

import pytest


# ---------------------------------------------------------------------------
# 환경 체크 + 마커 자동 스킵
# ---------------------------------------------------------------------------


def _is_playwright_installed() -> bool:
    """Playwright + chromium 브라우저 설치 여부."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # 브라우저 바이너리 존재 확인 (실제 실행 X)
            p.chromium.executable_path  # noqa: B018
        return True
    except Exception:
        return False


def _is_plotly_installed() -> bool:
    """Plotly + Kaleido 설치 여부."""
    try:
        import plotly.graph_objects as go  # noqa: F401
        import kaleido  # noqa: F401

        return True
    except ImportError:
        return False


HAS_PLAYWRIGHT = _is_playwright_installed()
HAS_PLOTLY = _is_plotly_installed()


def pytest_addoption(parser):
    """커스텀 pytest CLI 옵션 등록."""
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="골든 파일을 현재 출력으로 업데이트 (비교 대신 덮어쓰기)",
    )


def pytest_configure(config):
    """마커 등록."""
    config.addinivalue_line("markers", "requires_browser: Playwright 브라우저 필요")
    config.addinivalue_line("markers", "requires_plotly: Plotly + Kaleido 필요")
    config.addinivalue_line("markers", "golden: 골든 파일 스냅샷 테스트")


def pytest_collection_modifyitems(config, items):
    """마커 기반 조건부 스킵."""
    skip_browser = pytest.mark.skip(reason="Playwright 미설치 또는 브라우저 미설정")
    skip_plotly = pytest.mark.skip(reason="Plotly/Kaleido 미설치")

    for item in items:
        if "requires_browser" in item.keywords and not HAS_PLAYWRIGHT:
            item.add_marker(skip_browser)
        if "requires_plotly" in item.keywords and not HAS_PLOTLY:
            item.add_marker(skip_plotly)


# ---------------------------------------------------------------------------
# 공유 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
def update_golden(request) -> bool:
    """--update-golden CLI 옵션 값 반환."""
    return request.config.getoption("--update-golden")


@pytest.fixture
def sample_financial_data():
    """샘플 재무 데이터 (테스트용)"""
    return {
        "revenue": [10000, 15000, 22000, 30000],
        "operating_profit": [1000, 1800, 3000, 4500],
        "depreciation": [500, 600, 700, 800],
        "years": ["2021", "2022", "2023", "2024"],
    }


@pytest.fixture
def sample_im_data():
    """완전한 IMDocumentData — 전체 테스트 모듈에서 공유 가능한 샘플 데이터.

    design_renderer의 full_data 픽스처와 독립적인 자체 완결형.
    """
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
        SourceCitation,
        TransactionType,
    )

    fs = FinancialStatements(
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

    data = IMDocumentData(
        project_name="Project SAMPLE",
        company_name_kr="샘플기업",
        company_name_en="Sample Corp",
        corp_code="00999999",
        website_url="https://sample-corp.co.kr",
        date="2026-02-11",
        im_style=IMStyle.FULL,
        financial_statements=fs,
        deal_structure=DealStructure(
            seller="샘플PE",
            stake_pct=0.55,
            deal_background="전략적 포트폴리오 재편",
            transaction_type=TransactionType.MA,
            valuation_low=400_000,
            valuation_high=600_000,
            valuation_method="EV/EBITDA",
            timeline={"예비입찰": "2026-04", "본입찰": "2026-06"},
        ),
        company_overview=CompanyOverview(
            history=[
                {"year": "2008", "event": "설립"},
                {"year": "2015", "event": "코스닥 상장"},
                {"year": "2022", "event": "해외 사업 확대"},
            ],
            business_model="B2B 솔루션",
            value_chain=["기획", "개발", "운영", "유지보수"],
            key_products=["클라우드 플랫폼", "AI 분석 솔루션"],
            certifications=["ISO 27001", "ISMS-P"],
            employee_count=450,
            headquarters="서울특별시 강남구",
            established_date="2008-06-01",
        ),
        market_data=MarketData(
            tam=600_000,
            sam=250_000,
            som=60_000,
            market_growth_rate=0.10,
            market_cagr=0.14,
            competitors=[
                {"name": "경쟁사X", "revenue": 90_000, "market_share": 0.18},
                {"name": "경쟁사Y", "revenue": 70_000, "market_share": 0.12},
            ],
            industry_trends=["디지털 전환", "AI 자동화"],
        ),
        investment_highlights=[
            "매출 CAGR 22.5%",
            "업계 최고 수준 영업이익률",
            "안정적 현금흐름 기반 성장",
        ],
        growth_strategy=GrowthStrategy(
            organic_growth=["기존 사업 확대"],
            new_business=["AI 플랫폼"],
            ma_targets=["보안 스타트업 인수"],
            roadmap={"2026": ["베타 출시"], "2027": ["글로벌 론칭"]},
        ),
        management_team=[
            ManagementMember(
                name="김대표",
                title="대표이사",
                role="CEO",
                career=["前 대기업 VP", "서울대 경영학과"],
            ),
            ManagementMember(
                name="박CFO",
                title="부사장",
                role="CFO",
                career=["前 골드만삭스", "고려대 경제학과"],
            ),
        ],
        shareholders=[
            ShareholderInfo(name="샘플PE", stake_pct=0.55, category="최대주주"),
            ShareholderInfo(name="김대표", stake_pct=0.25, category="특수관계인"),
            ShareholderInfo(name="소액주주", stake_pct=0.20, category="소액주주"),
        ],
        narratives={
            "executive_summary": "샘플기업은 국내 IT 솔루션 시장의 선도기업으로...",
            "financial_analysis": "최근 3개년 매출은 연평균 22.5% 성장...",
            "market_overview": "국내 IT 솔루션 시장은...",
            "deal_overview": "본 딜은...",
            "company_overview": "회사 개요...",
            "business_overview": "사업 개요...",
            "investment_highlights": "투자 하이라이트...",
            "value_creation": "가치 창출...",
            "growth_strategy": "성장 전략...",
            "business_model": "비즈니스 모델...",
            "valuation": "밸류에이션 요약...",
        },
        contacts=[
            ContactInfo(
                name="이담당",
                title="Managing Director",
                email="lee@sample.co.kr",
                phone="02-9999-1234",
                company="AMIC",
            ),
        ],
        source_citations={
            "financial_analysis": [
                SourceCitation(
                    source_name="금융감독원 전자공시시스템",
                    url="https://dart.fss.or.kr",
                    access_date="2026-02-11",
                ),
            ],
        },
    )
    data.compute_derived_metrics()
    return data
