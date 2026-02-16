"""파이프라인 통합 테스트 (T-I19).

> 마지막 수정: 2026-02-10 23:30:00

IMDocumentData 직렬화/역직렬화 라운드트립 + 파이프라인 통합 검증.
"""

from __future__ import annotations

import json
from dataclasses import asdict

import pytest

from src.api.tasks.serializers import dict_to_im_data, im_data_to_dict
from src.brand_extractor.models import BrandAssets, ExtractedColor, LogoCandidate
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
    SegmentRevenue,
    ShareholderInfo,
    SourceCitation,
    TransactionType,
)


def _make_full_im_data() -> IMDocumentData:
    """모든 중첩 dataclass를 포함한 IMDocumentData를 생성한다."""
    return IMDocumentData(
        project_name="Project TITAN",
        company_name_kr="테스트 주식회사",
        company_name_en="Test Corp",
        corp_code="00123456",
        website_url="https://test.co.kr",
        date="2026-02-10",
        im_style=IMStyle.FULL,
        financial_statements=FinancialStatements(
            revenue={"2023": 100_000.0, "2024": 120_000.0},
            operating_income={"2023": 15_000.0, "2024": 18_000.0},
            net_income={"2023": 10_000.0, "2024": 13_000.0},
            total_assets={"2023": 200_000.0, "2024": 250_000.0},
            total_equity={"2023": 80_000.0, "2024": 100_000.0},
        ),
        deal_structure=DealStructure(
            seller="기존주주",
            stake_pct=0.51,
            transaction_type=TransactionType.MA,
            valuation_low=500.0,
            valuation_high=700.0,
        ),
        company_overview=CompanyOverview(
            history=[{"year": "2005", "event": "설립"}],
            business_model="IT 서비스",
            key_products=["서비스A", "서비스B"],
            employee_count=500,
        ),
        market_data=MarketData(
            tam=500_000.0,
            sam=100_000.0,
            market_growth_rate=0.08,
            competitors=[{"name": "경쟁사A", "revenue": 50_000}],
        ),
        growth_strategy=GrowthStrategy(
            organic_growth=["신규 고객 확보"],
            roadmap={"2026": ["국내 확장"], "2027": ["해외 진출"]},
        ),
        management_team=[
            ManagementMember(
                name="홍길동", title="대표이사", role="CEO", career=["삼성전자 VP"]
            ),
        ],
        shareholders=[
            ShareholderInfo(name="홍길동", stake_pct=0.51, category="최대주주"),
        ],
        narratives={"executive_summary": "이 회사는 성장 잠재력이 높습니다."},
        charts={
            "financial_analysis": [
                ChartData(
                    chart_type="combo",
                    title="매출 추이",
                    data={"years": ["2023", "2024"], "values": [100, 120]},
                )
            ],
        },
        number_format=NumberFormatConfig(
            currency=Currency.KRW, scale="억원", decimal_places_pct=1
        ),
        segment_revenue=SegmentRevenue(
            segments={"IT서비스": {"2023": 80_000.0, "2024": 95_000.0}}
        ),
        source_citations={
            "financial_analysis": [
                SourceCitation(
                    source_name="금융감독원", url="https://dart.fss.or.kr"
                )
            ],
        },
        contacts=[
            ContactInfo(
                name="김담당", title="이사", email="kim@test.co.kr", phone="02-1234"
            ),
        ],
        investment_highlights=["높은 성장률", "안정적 현금흐름"],
    )


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


class TestSerializationRoundTrip:
    """IMDocumentData 직렬화/역직렬화 라운드트립 검증."""

    def test_im_data_to_dict_roundtrip(self) -> None:
        """전체 필드 라운드트립: to_dict → to_im_data → 비교."""
        original = _make_full_im_data()
        serialized = im_data_to_dict(original)

        # JSON 직렬화 가능한지 확인
        json_str = json.dumps(serialized, ensure_ascii=False)
        assert len(json_str) > 0

        # 역직렬화
        restored = dict_to_im_data(serialized)

        # 핵심 필드 비교
        assert restored.project_name == original.project_name
        assert restored.company_name_kr == original.company_name_kr
        assert restored.corp_code == original.corp_code
        assert restored.im_style == original.im_style
        assert restored.date == original.date

    def test_financial_statements_roundtrip(self) -> None:
        """FinancialStatements 라운드트립."""
        original = _make_full_im_data()
        serialized = im_data_to_dict(original)
        restored = dict_to_im_data(serialized)

        assert isinstance(restored.financial_statements, FinancialStatements)
        assert restored.financial_statements.revenue == {"2023": 100_000.0, "2024": 120_000.0}

    def test_deal_structure_roundtrip(self) -> None:
        """DealStructure + TransactionType enum 라운드트립."""
        original = _make_full_im_data()
        serialized = im_data_to_dict(original)
        restored = dict_to_im_data(serialized)

        assert isinstance(restored.deal_structure, DealStructure)
        assert restored.deal_structure.transaction_type == TransactionType.MA
        assert restored.deal_structure.stake_pct == 0.51

    def test_serialization_enums(self) -> None:
        """IMStyle, TransactionType, Currency enum 직렬화/복원."""
        original = _make_full_im_data()
        serialized = im_data_to_dict(original)

        # Enum이 문자열로 직렬화됨
        assert serialized["im_style"] == "FULL"
        assert serialized["deal_structure"]["transaction_type"] == "M&A"
        assert serialized["number_format"]["currency"] == "KRW"

        # 복원 후 Enum 타입
        restored = dict_to_im_data(serialized)
        assert restored.im_style == IMStyle.FULL
        assert restored.number_format.currency == Currency.KRW

    def test_serialization_with_none_optionals(self) -> None:
        """Optional 필드가 None인 경우 처리."""
        data = IMDocumentData(
            company_name_kr="테스트",
            im_style=IMStyle.TITAN,
        )
        serialized = im_data_to_dict(data)
        restored = dict_to_im_data(serialized)

        assert restored.deal_structure is None
        assert restored.company_overview is None
        assert restored.market_data is None
        assert restored.brand_assets is None

    def test_nested_lists_roundtrip(self) -> None:
        """ManagementMember, ShareholderInfo, ContactInfo 리스트 라운드트립."""
        original = _make_full_im_data()
        serialized = im_data_to_dict(original)
        restored = dict_to_im_data(serialized)

        assert len(restored.management_team) == 1
        assert isinstance(restored.management_team[0], ManagementMember)
        assert restored.management_team[0].name == "홍길동"

        assert len(restored.shareholders) == 1
        assert isinstance(restored.shareholders[0], ShareholderInfo)

        assert len(restored.contacts) == 1
        assert isinstance(restored.contacts[0], ContactInfo)

    def test_charts_and_citations_roundtrip(self) -> None:
        """ChartData, SourceCitation dict[str, list[...]] 라운드트립."""
        original = _make_full_im_data()
        serialized = im_data_to_dict(original)
        restored = dict_to_im_data(serialized)

        assert "financial_analysis" in restored.charts
        assert isinstance(restored.charts["financial_analysis"][0], ChartData)
        assert restored.charts["financial_analysis"][0].chart_type == "combo"

        assert "financial_analysis" in restored.source_citations
        assert isinstance(
            restored.source_citations["financial_analysis"][0], SourceCitation
        )

    def test_serialization_with_brand_assets(self) -> None:
        """BrandAssets (ExtractedColor tuple 포함) 직렬화/복원."""
        brand = BrandAssets(
            company_name="테스트",
            primary_color="#FF0000",
            secondary_color="#00FF00",
            confidence=0.9,
            source="website",
        )
        data = IMDocumentData(
            company_name_kr="테스트",
            brand_assets=brand,
        )
        serialized = im_data_to_dict(data)
        restored = dict_to_im_data(serialized)

        assert isinstance(restored.brand_assets, BrandAssets)
        assert restored.brand_assets.primary_color == "#FF0000"
        assert restored.brand_assets.confidence == 0.9
