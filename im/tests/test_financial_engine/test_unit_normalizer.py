"""UnitNormalizer 단위 테스트.

한국 재무 데이터 금액 단위 정규화(원, 천원, 백만원, 억원, 조원) 기능을 검증합니다.

> 마지막 수정: 2026-02-09 16:28:44
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.financial_engine.exceptions import NormalizationError, UnitConversionError
from src.financial_engine.normalizer.unit_normalizer import (
    UnitNormalizer,
    UnitScale,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def normalizer() -> UnitNormalizer:
    """기본 UnitNormalizer 인스턴스."""
    return UnitNormalizer()


# ---------------------------------------------------------------------------
# normalize — 문자열 파싱 테스트
# ---------------------------------------------------------------------------


class TestNormalizeStringParsing:
    """문자열 입력에 대한 normalize 테스트."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("1,500백만원", Decimal("1500000000")),
            ("3.5억원", Decimal("350000000")),
        ],
        ids=["콤마_백만원", "소수점_억원"],
    )
    def test_normalize_string_with_unit(
        self, normalizer: UnitNormalizer, raw: str, expected: Decimal
    ) -> None:
        """문자열 내 단위를 감지하여 원(KRW) 단위로 변환한다."""
        assert normalizer.normalize(raw) == expected

    def test_normalize_negative_with_source_unit(
        self, normalizer: UnitNormalizer
    ) -> None:
        """명시적 source_unit과 음수 부호를 처리한다."""
        result = normalizer.normalize("-1,500", source_unit="천원")
        assert result == Decimal("-1500000")

    def test_normalize_parenthetical_negative(
        self, normalizer: UnitNormalizer
    ) -> None:
        """괄호 표기 음수를 처리한다: (500)백만원 → 음수."""
        result = normalizer.normalize("(500)백만원")
        assert result == Decimal("-500000000")

    def test_normalize_none_returns_zero(self, normalizer: UnitNormalizer) -> None:
        """None 입력은 Decimal('0')을 반환한다."""
        assert normalizer.normalize(None) == Decimal("0")

    def test_normalize_empty_string_returns_zero(
        self, normalizer: UnitNormalizer
    ) -> None:
        """빈 문자열 입력은 Decimal('0')을 반환한다."""
        assert normalizer.normalize("") == Decimal("0")


# ---------------------------------------------------------------------------
# normalize — 숫자 타입 입력 테스트
# ---------------------------------------------------------------------------


class TestNormalizeNumericInput:
    """Decimal / int / float 입력에 대한 normalize 테스트."""

    def test_normalize_decimal_with_source_unit(
        self, normalizer: UnitNormalizer
    ) -> None:
        """Decimal 값에 source_unit을 적용하여 원 단위로 변환한다."""
        result = normalizer.normalize(Decimal("100"), source_unit="백만원")
        assert result == Decimal("100000000")


# ---------------------------------------------------------------------------
# detect_unit
# ---------------------------------------------------------------------------


class TestDetectUnit:
    """detect_unit 메서드 테스트."""

    def test_detect_unit_억원(self, normalizer: UnitNormalizer) -> None:
        """'100억원' 에서 억원 UnitScale을 감지한다."""
        detected = normalizer.detect_unit("100억원")
        assert detected is not None
        assert isinstance(detected, UnitScale)
        assert detected.name == "억원"
        assert detected.multiplier == Decimal("100000000")


# ---------------------------------------------------------------------------
# convert
# ---------------------------------------------------------------------------


class TestConvert:
    """단위 간 변환 테스트."""

    def test_convert_억원_to_백만원(self, normalizer: UnitNormalizer) -> None:
        """1억원 = 100백만원."""
        result = normalizer.convert(Decimal("1"), from_unit="억원", to_unit="백만원")
        assert result == Decimal("100")


# ---------------------------------------------------------------------------
# normalize_batch
# ---------------------------------------------------------------------------


class TestNormalizeBatch:
    """배치 정규화 테스트."""

    def test_normalize_batch_basic(self, normalizer: UnitNormalizer) -> None:
        """여러 항목을 일괄 정규화한다."""
        data = {
            "매출액": "1,000백만원",
            "영업이익": "200백만원",
        }
        result = normalizer.normalize_batch(data)
        assert result["매출액"] == Decimal("1000000000")
        assert result["영업이익"] == Decimal("200000000")


# ---------------------------------------------------------------------------
# 에러 케이스
# ---------------------------------------------------------------------------


class TestNormalizerErrors:
    """에러 발생 시나리오 테스트."""

    def test_invalid_string_raises_normalization_error(
        self, normalizer: UnitNormalizer
    ) -> None:
        """파싱 불가능한 문자열은 NormalizationError를 발생시킨다."""
        with pytest.raises(NormalizationError):
            normalizer.normalize("가나다라")

    def test_unknown_source_unit_raises_unit_conversion_error(
        self, normalizer: UnitNormalizer
    ) -> None:
        """알 수 없는 source_unit은 UnitConversionError를 발생시킨다."""
        with pytest.raises(UnitConversionError):
            normalizer.normalize("100", source_unit="달러")
