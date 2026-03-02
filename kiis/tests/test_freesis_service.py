"""FreeSIS 기관전용 사모펀드 GP 수집 서비스 테스트."""

from decimal import Decimal

import pytest

from app.services.freesis_service import (
    FreeSISGPItem,
    FreeSISService,
    FreeSISSyncResult,
)
from app.utils.numeric import safe_decimal, safe_int

# --- 유틸리티 함수 테스트 ---


class TestSafeDecimal:
    def test_valid_number(self) -> None:
        assert safe_decimal("12345.67") == Decimal("12345.67")

    def test_comma_separated(self) -> None:
        assert safe_decimal("1,234,567") == Decimal("1234567")

    def test_none(self) -> None:
        assert safe_decimal(None) is None

    def test_empty(self) -> None:
        assert safe_decimal("") is None

    def test_dash(self) -> None:
        assert safe_decimal("-") is None

    def test_zero(self) -> None:
        assert safe_decimal("0") is None

    def test_invalid(self) -> None:
        assert safe_decimal("N/A") is None

    def test_integer(self) -> None:
        assert safe_decimal(42) == Decimal("42")


class TestSafeInt:
    def test_valid(self) -> None:
        assert safe_int("42") == 42

    def test_comma(self) -> None:
        assert safe_int("1,234") == 1234

    def test_none(self) -> None:
        assert safe_int(None) is None

    def test_empty(self) -> None:
        assert safe_int("") is None

    def test_dash(self) -> None:
        assert safe_int("-") is None

    def test_float_string(self) -> None:
        assert safe_int("3.14") == 3


# --- 엑셀 파싱 테스트 (목 데이터) ---


MOCK_HEADER = ("운용사", "설정잔액", "펀드수", "자금유입", "자금유출")

MOCK_ROWS = [
    ("기관전용 PEF 통계 (2024.12월말 기준)",),  # 제목 행 (헤더 패턴 미포함)
    MOCK_HEADER,
    ("에이티유파트너스자산운용", "500,000", "3", "100,000", "50,000"),
    ("삼성자산운용", "350,000,000", "250", "10,000,000", "5,000,000"),
    ("합계", "350,500,000", "253", "10,100,000", "5,050,000"),
]


class TestFreeSISExcelParsing:
    def setup_method(self) -> None:
        self.service = FreeSISService()

    def test_find_header_row(self) -> None:
        idx = self.service._find_header_row(MOCK_ROWS)
        assert idx == 1

    def test_find_header_row_not_found(self) -> None:
        rows = [("A", "B", "C"), ("1", "2", "3")]
        idx = self.service._find_header_row(rows)
        assert idx is None

    def test_map_columns(self) -> None:
        col_map = self.service._map_columns(MOCK_HEADER)
        assert col_map["company_name"] == 0
        assert col_map["setting_balance"] == 1
        assert col_map["fund_count"] == 2
        assert col_map["fund_inflow"] == 3
        assert col_map["fund_outflow"] == 4

    def test_map_columns_partial(self) -> None:
        header = ("회사명", "순자산")
        col_map = self.service._map_columns(header)
        assert col_map["company_name"] == 0
        assert col_map["setting_balance"] == 1
        assert "fund_count" not in col_map

    def test_get_cell_valid(self) -> None:
        row = ("a", "b", "c")
        assert self.service._get_cell(row, 1) == "b"

    def test_get_cell_none_idx(self) -> None:
        row = ("a", "b", "c")
        assert self.service._get_cell(row, None) is None

    def test_get_cell_out_of_range(self) -> None:
        row = ("a",)
        assert self.service._get_cell(row, 5) is None


class TestFreeSISParseLogic:
    """parse_freesis_excel의 내부 로직 테스트 (실제 엑셀 파일 없이)."""

    def setup_method(self) -> None:
        self.service = FreeSISService()

    def test_parse_mock_rows(self) -> None:
        """목 데이터로 파싱 로직을 테스트한다."""
        header_idx = self.service._find_header_row(MOCK_ROWS)
        assert header_idx is not None

        header = MOCK_ROWS[header_idx]
        col_map = self.service._map_columns(header)

        items: list[FreeSISGPItem] = []
        for row in MOCK_ROWS[header_idx + 1 :]:
            name_idx = col_map["company_name"]
            if name_idx >= len(row):
                continue
            name = row[name_idx]
            if not name or not str(name).strip():
                continue
            name_str = str(name).strip()
            if name_str in ("합계", "소계", "전체", "총계", "Total", "합 계"):
                continue

            items.append(
                FreeSISGPItem(
                    company_name=name_str,
                    setting_balance=safe_decimal(self.service._get_cell(row, col_map.get("setting_balance"))),
                    fund_count=safe_int(self.service._get_cell(row, col_map.get("fund_count"))),
                    fund_inflow=safe_decimal(self.service._get_cell(row, col_map.get("fund_inflow"))),
                    fund_outflow=safe_decimal(self.service._get_cell(row, col_map.get("fund_outflow"))),
                    reference_date="2024-12",
                )
            )

        assert len(items) == 2  # 합계 행 제외
        assert items[0].company_name == "에이티유파트너스자산운용"
        assert items[0].setting_balance == Decimal("500000")
        assert items[0].fund_count == 3
        assert items[1].company_name == "삼성자산운용"
        assert items[1].setting_balance == Decimal("350000000")

    def test_aggregate_rows_excluded(self) -> None:
        """합계/소계/전체 등 집계 행이 제외되는지 확인한다."""
        rows_with_aggregates = [
            MOCK_HEADER,
            ("테스트운용사", "100", "1", "10", "5"),
            ("합계", "100", "1", "10", "5"),
            ("소계", "100", "1", "10", "5"),
            ("전체", "100", "1", "10", "5"),
            ("총계", "100", "1", "10", "5"),
            ("Total", "100", "1", "10", "5"),
        ]
        header_idx = self.service._find_header_row(rows_with_aggregates)
        assert header_idx == 0

        count = 0
        for row in rows_with_aggregates[1:]:
            name = str(row[0]).strip()
            if name not in ("합계", "소계", "전체", "총계", "Total", "합 계"):
                count += 1
        assert count == 1


# --- 데이터 모델 테스트 ---


class TestFreeSISGPItem:
    def test_defaults(self) -> None:
        item = FreeSISGPItem(company_name="테스트")
        assert item.company_name == "테스트"
        assert item.setting_balance is None
        assert item.fund_count is None
        assert item.fund_inflow is None
        assert item.fund_outflow is None
        assert item.reference_date is None


class TestFreeSISSyncResult:
    def test_defaults(self) -> None:
        result = FreeSISSyncResult()
        assert result.total_items == 0
        assert result.created == 0
        assert result.updated == 0
        assert result.matched_existing == 0
        assert result.errors == []

    def test_errors_independent(self) -> None:
        """errors 리스트가 인스턴스 간 공유되지 않는지 확인."""
        r1 = FreeSISSyncResult()
        r2 = FreeSISSyncResult()
        r1.errors.append("A")
        assert r2.errors == []


# --- 헤더 패턴 매칭 테스트 ---


class TestHeaderPatternVariations:
    """다양한 FreeSIS 엑셀 헤더 형식에 대한 매칭 테스트."""

    def setup_method(self) -> None:
        self.service = FreeSISService()

    def test_alternative_header_variant_1(self) -> None:
        header = ("번호", "운용회사", "설정액")
        col_map = self.service._map_columns(header)
        assert col_map["company_name"] == 1
        assert col_map["setting_balance"] == 2

    def test_alternative_header_variant_2(self) -> None:
        header = ("자산운용사", "순자산", "설정수")
        col_map = self.service._map_columns(header)
        assert col_map["company_name"] == 0
        assert col_map["setting_balance"] == 1
        assert col_map["fund_count"] == 2

    @pytest.mark.parametrize(
        "header_cell",
        ["운용사", "운용회사", "회사명", "자산운용사"],
    )
    def test_all_company_name_patterns(self, header_cell: str) -> None:
        rows = [(header_cell, "잔액"), ("테스트운용사", "100")]
        idx = self.service._find_header_row(rows)
        assert idx == 0
