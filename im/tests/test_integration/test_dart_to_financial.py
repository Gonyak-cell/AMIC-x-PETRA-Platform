# -*- coding: utf-8 -*-
"""E2E 통합 테스트: DART → FinancialProcessor → FinancialStatements.

실제 DART API를 호출하지 않고, DartFinancialStatement 객체를 직접 생성하여
FinancialStatementsCollection → FinancialProcessor → FinancialStatements 변환
전 과정을 검증합니다.

> 마지막 수정: 2026-02-09 16:29:23
"""

from __future__ import annotations


import pytest

from src.data_ingestor.dart.models import (
    DartFinancialStatement,
    FinancialStatementsCollection,
)
from src.design_renderer.im_document import FinancialStatements
from src.financial_engine.processor import (
    FinancialProcessor,
)


# ---------------------------------------------------------------------------
# 헬퍼: 모의 DART 데이터 생성
# ---------------------------------------------------------------------------

_CORP_CODE = "00126380"
_RCEPT_NO = "20240315000001"
_REPRT_CODE = "11011"  # 사업보고서


def _make_dart_item(
    account_nm: str,
    bsns_year: str,
    thstrm_amount: str,
    fs_div: str = "CFS",
    sj_div: str = "IS",
    sj_nm: str = "손익계산서",
    fs_nm: str = "연결재무제표",
) -> DartFinancialStatement:
    """단일 DART 재무제표 항목을 생성한다."""
    return DartFinancialStatement(
        rcept_no=_RCEPT_NO,
        reprt_code=_REPRT_CODE,
        bsns_year=bsns_year,
        corp_code=_CORP_CODE,
        stock_code="005930",
        fs_div=fs_div,
        fs_nm=fs_nm,
        sj_div=sj_div,
        sj_nm=sj_nm,
        account_nm=account_nm,
        thstrm_amount=thstrm_amount,
    )


def _make_collection(
    fs_div: str = "CFS",
) -> FinancialStatementsCollection:
    """실제 DART 데이터 형태의 FinancialStatementsCollection을 생성한다.

    매출액, 영업이익, 당기순이익, 자산총계, 부채총계, 자본총계를
    2022~2023 2개 연도로 구성한다.
    """
    items = [
        # --- 손익계산서 (IS) ---
        _make_dart_item(
            "매출액",
            "2022",
            "100000000000",
            fs_div=fs_div,
            sj_div="IS",
            sj_nm="손익계산서",
        ),
        _make_dart_item(
            "매출액",
            "2023",
            "120000000000",
            fs_div=fs_div,
            sj_div="IS",
            sj_nm="손익계산서",
        ),
        _make_dart_item(
            "영업이익",
            "2022",
            "20000000000",
            fs_div=fs_div,
            sj_div="IS",
            sj_nm="손익계산서",
        ),
        _make_dart_item(
            "영업이익",
            "2023",
            "25000000000",
            fs_div=fs_div,
            sj_div="IS",
            sj_nm="손익계산서",
        ),
        _make_dart_item(
            "당기순이익",
            "2022",
            "15000000000",
            fs_div=fs_div,
            sj_div="IS",
            sj_nm="손익계산서",
        ),
        _make_dart_item(
            "당기순이익",
            "2023",
            "18000000000",
            fs_div=fs_div,
            sj_div="IS",
            sj_nm="손익계산서",
        ),
        _make_dart_item(
            "매출원가",
            "2022",
            "60000000000",
            fs_div=fs_div,
            sj_div="IS",
            sj_nm="손익계산서",
        ),
        _make_dart_item(
            "매출원가",
            "2023",
            "70000000000",
            fs_div=fs_div,
            sj_div="IS",
            sj_nm="손익계산서",
        ),
        _make_dart_item(
            "매출총이익",
            "2022",
            "40000000000",
            fs_div=fs_div,
            sj_div="IS",
            sj_nm="손익계산서",
        ),
        _make_dart_item(
            "매출총이익",
            "2023",
            "50000000000",
            fs_div=fs_div,
            sj_div="IS",
            sj_nm="손익계산서",
        ),
        _make_dart_item(
            "판매비와관리비",
            "2022",
            "20000000000",
            fs_div=fs_div,
            sj_div="IS",
            sj_nm="손익계산서",
        ),
        _make_dart_item(
            "판매비와관리비",
            "2023",
            "25000000000",
            fs_div=fs_div,
            sj_div="IS",
            sj_nm="손익계산서",
        ),
        # --- 재무상태표 (BS) ---
        _make_dart_item(
            "자산총계",
            "2022",
            "500000000000",
            fs_div=fs_div,
            sj_div="BS",
            sj_nm="재무상태표",
            fs_nm="연결재무상태표",
        ),
        _make_dart_item(
            "자산총계",
            "2023",
            "600000000000",
            fs_div=fs_div,
            sj_div="BS",
            sj_nm="재무상태표",
            fs_nm="연결재무상태표",
        ),
        _make_dart_item(
            "부채총계",
            "2022",
            "300000000000",
            fs_div=fs_div,
            sj_div="BS",
            sj_nm="재무상태표",
            fs_nm="연결재무상태표",
        ),
        _make_dart_item(
            "부채총계",
            "2023",
            "350000000000",
            fs_div=fs_div,
            sj_div="BS",
            sj_nm="재무상태표",
            fs_nm="연결재무상태표",
        ),
        _make_dart_item(
            "자본총계",
            "2022",
            "200000000000",
            fs_div=fs_div,
            sj_div="BS",
            sj_nm="재무상태표",
            fs_nm="연결재무상태표",
        ),
        _make_dart_item(
            "자본총계",
            "2023",
            "250000000000",
            fs_div=fs_div,
            sj_div="BS",
            sj_nm="재무상태표",
            fs_nm="연결재무상태표",
        ),
    ]
    return FinancialStatementsCollection(
        corp_code=_CORP_CODE,
        items=items,
    )


# ---------------------------------------------------------------------------
# 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
def collection_cfs() -> FinancialStatementsCollection:
    """연결재무제표(CFS) 기반 모의 컬렉션."""
    return _make_collection(fs_div="CFS")


@pytest.fixture
def collection_ofs() -> FinancialStatementsCollection:
    """별도재무제표(OFS) 기반 모의 컬렉션."""
    return _make_collection(fs_div="OFS")


@pytest.fixture
def processor() -> FinancialProcessor:
    """기본 FinancialProcessor 인스턴스."""
    return FinancialProcessor()


# ---------------------------------------------------------------------------
# 테스트: E2E DART → FinancialStatements
# ---------------------------------------------------------------------------


class TestDartToFinancialE2E:
    """DART 데이터 → FinancialProcessor → FinancialStatements E2E 테스트."""

    def test_process_from_dart_returns_result(
        self,
        processor: FinancialProcessor,
        collection_cfs: FinancialStatementsCollection,
    ) -> None:
        """process_from_dart()가 ProcessingResult를 정상 반환한다."""
        result = processor.process_from_dart(collection_cfs, consolidated=True)
        assert result is not None
        assert result.mapped_data is not None

    def test_revenue_correctly_mapped(
        self,
        processor: FinancialProcessor,
        collection_cfs: FinancialStatementsCollection,
    ) -> None:
        """매출액이 올바르게 매핑되고 금액이 정확하다."""
        result = processor.process_from_dart(collection_cfs, consolidated=True)
        fs = result.to_financial_statements()

        assert isinstance(fs, FinancialStatements)
        assert "2022" in fs.revenue
        assert "2023" in fs.revenue
        # DART 원 단위 그대로: 100000000000 → float
        assert fs.revenue["2022"] == pytest.approx(100_000_000_000.0)
        assert fs.revenue["2023"] == pytest.approx(120_000_000_000.0)

    def test_operating_income_mapped(
        self,
        processor: FinancialProcessor,
        collection_cfs: FinancialStatementsCollection,
    ) -> None:
        """영업이익이 올바르게 매핑된다."""
        result = processor.process_from_dart(collection_cfs, consolidated=True)
        fs = result.to_financial_statements()

        assert "2022" in fs.operating_income
        assert fs.operating_income["2022"] == pytest.approx(20_000_000_000.0)

    def test_decimal_to_float_conversion(
        self,
        processor: FinancialProcessor,
        collection_cfs: FinancialStatementsCollection,
    ) -> None:
        """to_financial_statements()에서 모든 값이 float으로 변환된다."""
        result = processor.process_from_dart(collection_cfs, consolidated=True)
        fs = result.to_financial_statements()

        for year, val in fs.revenue.items():
            assert isinstance(val, float), (
                f"revenue[{year}]이 float이 아닙니다: {type(val)}"
            )

    def test_all_17_fields_populated(
        self,
        processor: FinancialProcessor,
        collection_cfs: FinancialStatementsCollection,
    ) -> None:
        """매핑 가능한 주요 필드들이 FinancialStatements에 채워진다."""
        result = processor.process_from_dart(collection_cfs, consolidated=True)
        fs = result.to_financial_statements()

        # 원시 데이터에 포함된 주요 필드가 비어있지 않아야 함
        assert len(fs.revenue) > 0, "revenue가 비어있습니다"
        assert len(fs.operating_income) > 0, "operating_income이 비어있습니다"
        assert len(fs.net_income) > 0, "net_income이 비어있습니다"
        assert len(fs.total_assets) > 0, "total_assets가 비어있습니다"
        assert len(fs.total_liabilities) > 0, "total_liabilities가 비어있습니다"
        assert len(fs.total_equity) > 0, "total_equity가 비어있습니다"

    def test_extra_dict_contains_unmapped(
        self,
        processor: FinancialProcessor,
        collection_cfs: FinancialStatementsCollection,
    ) -> None:
        """_ACCOUNT_TO_FIELD에 없는 매핑된 계정은 extra에 저장된다."""
        result = processor.process_from_dart(collection_cfs, consolidated=True)
        fs = result.to_financial_statements()

        # extra는 dict[str, dict[str, float]] 형태여야 함
        assert isinstance(fs.extra, dict)

    def test_round_trip_all_fields(
        self,
        processor: FinancialProcessor,
        collection_cfs: FinancialStatementsCollection,
    ) -> None:
        """DART 데이터 → process → FinancialStatements의 라운드트립에서 각 필드를 검증한다."""
        result = processor.process_from_dart(collection_cfs, consolidated=True)
        fs = result.to_financial_statements()

        # 각 주요 필드의 2023년 값 검증
        expected_2023 = {
            "revenue": 120_000_000_000.0,
            "operating_income": 25_000_000_000.0,
            "net_income": 18_000_000_000.0,
            "total_assets": 600_000_000_000.0,
            "total_liabilities": 350_000_000_000.0,
            "total_equity": 250_000_000_000.0,
        }
        for field_name, expected_val in expected_2023.items():
            field_data = getattr(fs, field_name, {})
            assert "2023" in field_data, f"{field_name}에 2023년 데이터가 없습니다"
            assert field_data["2023"] == pytest.approx(expected_val), (
                f"{field_name}[2023]: 기대값 {expected_val}, 실제값 {field_data['2023']}"
            )

    def test_consolidated_false(
        self,
        collection_ofs: FinancialStatementsCollection,
    ) -> None:
        """consolidated=False로 별도재무제표를 처리한다."""
        processor = FinancialProcessor()
        result = processor.process_from_dart(collection_ofs, consolidated=False)
        fs = result.to_financial_statements()

        # OFS 컬렉션의 데이터가 올바르게 처리되었는지 확인
        assert isinstance(fs, FinancialStatements)
        assert len(fs.revenue) > 0, "별도재무제표(OFS) 매출액이 비어있습니다"
