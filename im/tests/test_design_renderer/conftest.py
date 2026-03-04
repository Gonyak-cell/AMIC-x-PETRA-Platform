"""테스트 공유 픽스처 — IMDocumentData (TITAN/COVENANT/FULL) + 보조 픽스처."""

from pathlib import Path

import pytest

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import (
    ChartData,
    CompanyOverview,
    ContactInfo,
    Currency,
    DealStructure,
    FinancialStatements,
    GrowthStrategy,
    IMDocumentData,
    IMStyle,
    ManagementMember,
    MarketData,
    NumberFormatConfig,
    ShareholderInfo,
    SourceCitation,
    TransactionType,
)
from src.design_renderer.security import SecurityOptions


# ---------------------------------------------------------------------------
# 재무 데이터
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_financial_statements() -> FinancialStatements:
    """3개년 재무 데이터 — 모든 렌더러 테스트에 충분한 최소 데이터."""
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
# IMDocumentData 프리셋
# ---------------------------------------------------------------------------


@pytest.fixture
def titan_data(minimal_financial_statements: FinancialStatements) -> IMDocumentData:
    """TITAN 프리셋 (9개 섹션) — 최소 필수 데이터."""
    data = IMDocumentData(
        project_name="Project TITAN",
        company_name_kr="테스트기업",
        company_name_en="Test Corp",
        date="2026-02-08",
        im_style=IMStyle.TITAN,
        financial_statements=minimal_financial_statements,
        investment_highlights=[
            "매출 CAGR 22.5% (3개년)",
            "영업이익률 18.7%로 업계 상위",
            "안정적 현금흐름 및 낮은 부채비율",
        ],
        contacts=[
            ContactInfo(
                name="홍길동",
                title="Managing Director",
                email="hong@amic.co.kr",
                phone="02-1234-5678",
                company="AMIC",
            )
        ],
        narratives={
            "executive_summary": "테스트기업은 국내 IT 서비스 시장의 선도기업으로...",
            "financial_analysis": "최근 3개년 매출은 연평균 22.5% 성장하였으며...",
            "market_overview": "국내 IT 서비스 시장 규모는...",
            "business_overview": "테스트기업의 사업 구조는...",
            "investment_highlights": "테스트기업의 투자 매력은...",
        },
        market_data=MarketData(
            tam=500_000,
            sam=200_000,
            som=50_000,
            market_growth_rate=0.08,
        ),
    )
    data.compute_derived_metrics()
    return data


@pytest.fixture
def covenant_data(minimal_financial_statements: FinancialStatements) -> IMDocumentData:
    """COVENANT 프리셋 (10개 섹션) — value_creation 포함."""
    data = IMDocumentData(
        project_name="Project COVENANT",
        company_name_kr="테스트기업",
        company_name_en="Test Corp",
        date="2026-02-08",
        im_style=IMStyle.COVENANT,
        financial_statements=minimal_financial_statements,
        investment_highlights=[
            "전략적 파트너십을 통한 시너지",
            "디지털 전환 선도",
        ],
        market_data=MarketData(
            tam=500_000,
            sam=200_000,
            som=50_000,
            market_growth_rate=0.08,
        ),
        company_overview=CompanyOverview(
            history=[{"year": "2010", "event": "설립"}],
            business_model="B2B IT 서비스",
            key_products=["클라우드 인프라"],
            employee_count=300,
        ),
        contacts=[ContactInfo(name="김철수", title="Partner", email="kim@amic.co.kr")],
        narratives={
            "executive_summary": "테스트기업은...",
            "value_creation": "가치 창출 전략은...",
            "company_overview": "회사 개요...",
            "market_overview": "시장 개요...",
            "financial_analysis": "재무 분석...",
            "investment_highlights": "투자 하이라이트...",
        },
    )
    data.compute_derived_metrics()
    return data


@pytest.fixture
def full_data(minimal_financial_statements: FinancialStatements) -> IMDocumentData:
    """FULL 프리셋 (18개 섹션) — 전체 필드 채움."""
    data = IMDocumentData(
        project_name="Project FULL",
        company_name_kr="테스트기업",
        company_name_en="Test Corp",
        corp_code="00123456",
        website_url="https://test-corp.co.kr",
        date="2026-02-08",
        im_style=IMStyle.FULL,
        financial_statements=minimal_financial_statements,
        deal_structure=DealStructure(
            seller="테스트PE",
            stake_pct=0.60,
            deal_background="전략적 포트폴리오 재구성",
            transaction_type=TransactionType.MA,
            valuation_low=500_000,
            valuation_high=700_000,
            valuation_method="EV/EBITDA",
            timeline={"예비입찰": "2026-03", "본입찰": "2026-05"},
        ),
        company_overview=CompanyOverview(
            history=[
                {"year": "2010", "event": "설립"},
                {"year": "2015", "event": "코스닥 상장"},
                {"year": "2020", "event": "해외 진출"},
            ],
            business_model="B2B IT 서비스",
            value_chain=["기획", "개발", "운영"],
            key_products=["클라우드 인프라", "데이터 분석"],
            certifications=["ISO 27001", "ISMS-P"],
            employee_count=500,
            headquarters="서울특별시 강남구",
            established_date="2010-03-15",
        ),
        market_data=MarketData(
            tam=500_000,
            sam=200_000,
            som=50_000,
            market_growth_rate=0.08,
            market_cagr=0.12,
            competitors=[
                {"name": "경쟁사A", "revenue": 80_000, "market_share": 0.15},
                {"name": "경쟁사B", "revenue": 60_000, "market_share": 0.10},
            ],
            industry_trends=["클라우드 전환 가속", "AI 기반 자동화"],
        ),
        investment_highlights=[
            "매출 CAGR 22.5%",
            "업계 최고 영업이익률",
            "안정적 현금흐름",
        ],
        growth_strategy=GrowthStrategy(
            organic_growth=["기존 사업 확대"],
            new_business=["AI SaaS 플랫폼"],
            ma_targets=["보안 스타트업 인수"],
            roadmap={"2026": ["AI 플랫폼 베타"], "2027": ["글로벌 론칭"]},
        ),
        management_team=[
            ManagementMember(
                name="이대표",
                title="대표이사",
                role="CEO",
                career=["前 삼성전자 VP", "서울대 경영학과"],
            ),
            ManagementMember(
                name="박부사장",
                title="부사장",
                role="CFO",
                career=["前 JP Morgan", "고려대 경제학과"],
            ),
        ],
        shareholders=[
            ShareholderInfo(name="테스트PE", stake_pct=0.60, category="최대주주"),
            ShareholderInfo(name="이대표", stake_pct=0.20, category="특수관계인"),
            ShareholderInfo(name="소액주주", stake_pct=0.20, category="소액주주"),
        ],
        narratives={
            "executive_summary": "테스트기업은 국내 IT 서비스 시장의 선도기업으로...",
            "financial_analysis": "최근 3개년 매출은 연평균 22.5% 성장하였으며...",
            "market_overview": "국내 IT 서비스 시장은...",
            "deal_overview": "본 딜은...",
            "company_overview": "회사 개요...",
            "business_overview": "사업 개요...",
            "investment_highlights": "투자 하이라이트...",
            "value_creation": "가치 창출...",
            "growth_strategy": "성장 전략...",
            "business_model": "비즈니스 모델...",
            "valuation": "밸류에이션 요약: EV/EBITDA 10.0x 기준...",
        },
        contacts=[
            ContactInfo(
                name="홍길동",
                title="Managing Director",
                email="hong@amic.co.kr",
                phone="02-1234-5678",
            ),
        ],
        source_citations={
            "financial_analysis": [
                SourceCitation(
                    source_name="금융감독원 전자공시시스템",
                    url="https://dart.fss.or.kr",
                    access_date="2026-02-08",
                ),
            ],
            "market_overview": [
                SourceCitation(
                    source_name="한국IDC 보고서",
                    access_date="2026-01",
                    document_title="2025 IT 서비스 시장 전망",
                ),
            ],
        },
        charts={
            "financial_analysis": [
                ChartData(
                    chart_type="combo",
                    title="매출 및 영업이익 추이",
                    data={
                        "categories": ["2022", "2023", "2024"],
                        "bar_series": [
                            {"name": "매출", "values": [100_000, 120_000, 150_000]}
                        ],
                        "line_series": [
                            {
                                "name": "영업이익률",
                                "values": [0.15, 0.167, 0.187],
                            }
                        ],
                    },
                ),
            ],
        },
    )
    data.compute_derived_metrics()
    return data


# ---------------------------------------------------------------------------
# 보조 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
def default_tokens() -> IMDesignTokens:
    """기본 디자인 토큰."""
    return DEFAULT_TOKENS


@pytest.fixture
def number_format_config() -> NumberFormatConfig:
    """기본 숫자 포맷 설정."""
    return NumberFormatConfig()


@pytest.fixture
def usd_number_format_config() -> NumberFormatConfig:
    """USD 숫자 포맷 설정."""
    return NumberFormatConfig(
        currency=Currency.USD,
        scale="$M",
        decimal_places_amount=1,
    )


@pytest.fixture
def security_options() -> SecurityOptions:
    """기본 보안 옵션."""
    return SecurityOptions(
        pdf_password="test1234",
        watermark_text="CONFIDENTIAL",
        watermark_opacity=0.2,
        pptx_read_only=True,
    )


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    """임시 출력 디렉토리."""
    out = tmp_path / "output"
    out.mkdir()
    return out
