"""KVIC 모태펀드 자조합 운용사정보 수집 서비스 테스트."""

from decimal import Decimal
from pathlib import Path

import pytest

from app.services.kvic_service import (
    KVICFundOperator,
    KVICService,
    KVICSyncResult,
)
from app.utils.numeric import safe_decimal

# --- 유틸리티 함수 테스트 ---


class TestSafeDecimal:
    def test_valid(self) -> None:
        assert safe_decimal("12345") == Decimal("12345")

    def test_comma(self) -> None:
        assert safe_decimal("1,234,567") == Decimal("1234567")

    def test_none(self) -> None:
        assert safe_decimal(None) is None

    def test_dash(self) -> None:
        assert safe_decimal("-") is None


# --- CSV/Excel 파싱 테스트 (목 데이터) ---

# 실제 파일 형식과 동일한 3컬럼 헤더
MOCK_HEADER_REAL = ("대표운영사", "운영사구분", "자조합 규모(백만원)")

MOCK_ROWS_REAL = [
    MOCK_HEADER_REAL,
    ("스틱벤처스", "벤처투자회사", "33400"),
    ("엘비인베스트먼트", "벤처투자회사", "25000"),
    ("한화투자증권", "신기술사", "20000"),
    ("이너시아인베스트먼트파트너스", "LLC", "80000"),
    ("합계", "", "158400"),
]

# 확장된 6컬럼 헤더 (조합명 포함 시)
MOCK_HEADER_EXTENDED = ("조합명", "대표운용사", "대표자", "연락처", "조합규모", "결성일")

MOCK_ROWS_EXTENDED = [
    ("KVIC 자조합 현황",),  # 제목 행
    MOCK_HEADER_EXTENDED,
    ("에이티유 1호 PEF", "에이티유파트너스자산운용", "홍길동", "02-1234-5678", "50,000", "2020-01-01"),
    ("에이티유 2호 PEF", "에이티유파트너스자산운용", "홍길동", "02-1234-5678", "80,000", "2021-06-15"),
    ("IMM 크레딧 1호", "IMM인베스트먼트", "김투자", "02-9876-5432", "200,000", "2019-03-01"),
    ("합계", "", "", "", "330,000", ""),
]


class TestKVICParsing:
    def setup_method(self) -> None:
        self.service = KVICService()

    def test_find_header_row_real_format(self) -> None:
        idx = self.service._find_header_row(MOCK_ROWS_REAL)
        assert idx == 0

    def test_find_header_row_extended(self) -> None:
        idx = self.service._find_header_row(MOCK_ROWS_EXTENDED)
        assert idx == 1

    def test_find_header_row_not_found(self) -> None:
        rows = [("A", "B", "C"), ("1", "2", "3")]
        idx = self.service._find_header_row(rows)
        assert idx is None

    def test_map_columns_real_format(self) -> None:
        col_map = self.service._map_columns(MOCK_HEADER_REAL)
        assert col_map["operator_name"] == 0
        assert col_map["operator_type"] == 1
        assert col_map["fund_size"] == 2

    def test_map_columns_extended(self) -> None:
        col_map = self.service._map_columns(MOCK_HEADER_EXTENDED)
        assert col_map["fund_name"] == 0
        assert col_map["operator_name"] == 1
        assert col_map["representative"] == 2
        assert col_map["phone"] == 3
        assert col_map["fund_size"] == 4
        assert col_map["established_date"] == 5

    def test_parse_rows_real_format(self) -> None:
        items = self.service._parse_rows(MOCK_ROWS_REAL)
        assert len(items) == 4  # 합계 행 제외
        assert items[0].operator_name == "스틱벤처스"
        assert items[0].operator_type == "벤처투자회사"
        assert items[0].fund_size == Decimal("33400")
        assert items[3].operator_name == "이너시아인베스트먼트파트너스"
        assert items[3].operator_type == "LLC"

    def test_parse_rows_extended(self) -> None:
        items = self.service._parse_rows(MOCK_ROWS_EXTENDED)
        assert len(items) == 3  # 합계 행 제외
        assert items[0].operator_name == "에이티유파트너스자산운용"
        assert items[0].fund_name == "에이티유 1호 PEF"
        assert items[0].fund_size == Decimal("50000")

    def test_aggregate_row_excluded(self) -> None:
        items = self.service._parse_rows(MOCK_ROWS_REAL)
        names = [item.operator_name for item in items]
        assert "합계" not in names

    def test_empty_operator_skipped(self) -> None:
        rows = [
            MOCK_HEADER_REAL,
            ("", "벤처투자회사", "100"),
            ("테스트운용사", "벤처투자회사", "200"),
        ]
        items = self.service._parse_rows(rows)
        assert len(items) == 1
        assert items[0].operator_name == "테스트운용사"


class TestKVICCSVParsing:
    def setup_method(self) -> None:
        self.service = KVICService()

    def test_parse_utf8_csv(self) -> None:
        csv_content = ("대표운영사,운영사구분,자조합 규모(백만원)\n테스트운용사,벤처투자회사,50000\n").encode(
            "utf-8-sig"
        )
        items = self.service.parse_kvic_csv(csv_content)
        assert len(items) == 1
        assert items[0].operator_name == "테스트운용사"
        assert items[0].operator_type == "벤처투자회사"
        assert items[0].fund_size == Decimal("50000")

    def test_parse_cp949_csv(self) -> None:
        csv_content = (
            "대표운영사,운영사구분,자조합 규모(백만원)\n스틱벤처스,벤처투자회사,33400\n한화투자증권,신기술사,20000\n"
        ).encode("cp949")
        items = self.service.parse_kvic_csv(csv_content)
        assert len(items) == 2
        assert items[0].operator_name == "스틱벤처스"
        assert items[1].operator_name == "한화투자증권"

    def test_parse_empty_csv(self) -> None:
        items = self.service.parse_kvic_csv(b"")
        assert items == []


# --- 실제 파일 파싱 테스트 ---

REAL_CSV_PATH = (
    Path(__file__).resolve().parent.parent / "app" / "data" / "한국벤처투자_모태펀드 자조합 운용사정보_20251212.csv"
)


@pytest.mark.skipif(not REAL_CSV_PATH.exists(), reason="KVIC CSV 파일 미존재")
class TestRealKVICFile:
    """실제 KVIC CSV 파일 파싱 테스트."""

    def setup_method(self) -> None:
        self.service = KVICService()
        with open(REAL_CSV_PATH, "rb") as f:
            self.items = self.service.parse_kvic_csv(f.read())

    def test_total_items(self) -> None:
        assert len(self.items) >= 1400

    def test_unique_operators(self) -> None:
        operators = {item.operator_name for item in self.items}
        assert len(operators) >= 300

    def test_operator_types(self) -> None:
        types = {item.operator_type for item in self.items if item.operator_type}
        assert "벤처투자회사" in types
        assert "신기술사" in types

    def test_fund_sizes_present(self) -> None:
        with_size = [i for i in self.items if i.fund_size is not None]
        assert len(with_size) == len(self.items)

    def test_no_aggregate_rows(self) -> None:
        names = [item.operator_name for item in self.items]
        assert "합계" not in names
        assert "소계" not in names

    def test_known_operators_present(self) -> None:
        operators = {item.operator_name for item in self.items}
        # 상위 운용사가 포함되어야 함
        assert "한국벤처투자" in operators
        assert "한국투자파트너스" in operators


# --- 헤더 패턴 매칭 테스트 ---


class TestHeaderPatternVariations:
    def setup_method(self) -> None:
        self.service = KVICService()

    def test_gp_header(self) -> None:
        header = ("펀드명", "GP", "대표이사")
        col_map = self.service._map_columns(header)
        assert col_map["fund_name"] == 0
        assert col_map["operator_name"] == 1
        assert col_map["representative"] == 2

    def test_alternative_headers(self) -> None:
        header = ("자조합명", "운용회사", "대표자", "전화번호", "약정총액", "설립일")
        col_map = self.service._map_columns(header)
        assert col_map["fund_name"] == 0
        assert col_map["operator_name"] == 1
        assert col_map["representative"] == 2
        assert col_map["phone"] == 3
        assert col_map["fund_size"] == 4
        assert col_map["established_date"] == 5

    @pytest.mark.parametrize(
        "header_cell",
        ["대표운영사", "대표운용사", "운영사", "운용사", "운용회사", "GP"],
    )
    def test_all_operator_patterns(self, header_cell: str) -> None:
        rows = [(header_cell, "구분", "규모"), ("테스트운용사", "VC", "100")]
        idx = self.service._find_header_row(rows)
        assert idx == 0


# --- 데이터 모델 테스트 ---


class TestKVICFundOperator:
    def test_defaults(self) -> None:
        item = KVICFundOperator(fund_name="테스트펀드", operator_name="테스트운용사")
        assert item.operator_type == ""
        assert item.representative == ""
        assert item.phone == ""
        assert item.fund_size is None
        assert item.established_date == ""


class TestKVICSyncResult:
    def test_defaults(self) -> None:
        result = KVICSyncResult()
        assert result.total_items == 0
        assert result.unique_operators == 0
        assert result.created == 0
        assert result.updated == 0
        assert result.matched_existing == 0
        assert result.errors == []

    def test_errors_independent(self) -> None:
        r1 = KVICSyncResult()
        r2 = KVICSyncResult()
        r1.errors.append("A")
        assert r2.errors == []


# --- 중복 제거 로직 테스트 ---


class TestOperatorDedup:
    """동일 운용사가 여러 조합에 등장할 때 중복 제거 로직 테스트."""

    def test_dedup_keeps_largest_fund(self) -> None:
        items = [
            KVICFundOperator(fund_name="1호", operator_name="테스트운용사", fund_size=Decimal("50000")),
            KVICFundOperator(fund_name="2호", operator_name="테스트운용사", fund_size=Decimal("80000")),
            KVICFundOperator(fund_name="3호", operator_name="다른운용사", fund_size=Decimal("30000")),
        ]
        operator_map: dict[str, KVICFundOperator] = {}
        for item in items:
            name = item.operator_name
            existing = operator_map.get(name)
            if existing is None or (
                item.fund_size and (existing.fund_size is None or item.fund_size > existing.fund_size)
            ):
                operator_map[name] = item

        assert len(operator_map) == 2
        assert operator_map["테스트운용사"].fund_size == Decimal("80000")
        assert operator_map["테스트운용사"].fund_name == "2호"

    def test_fund_count_tracking(self) -> None:
        items = [
            KVICFundOperator(fund_name="1호", operator_name="A운용사"),
            KVICFundOperator(fund_name="2호", operator_name="A운용사"),
            KVICFundOperator(fund_name="3호", operator_name="A운용사"),
            KVICFundOperator(fund_name="1호", operator_name="B운용사"),
        ]
        kvic_fund_counts: dict[str, int] = {}
        for item in items:
            name = item.operator_name
            kvic_fund_counts[name] = kvic_fund_counts.get(name, 0) + 1

        assert kvic_fund_counts["A운용사"] == 3
        assert kvic_fund_counts["B운용사"] == 1
