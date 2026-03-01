"""숫자 포맷터 테스트 — 통화/퍼센트/성장 표시/NaN."""


import pytest

from src.design_renderer.components.number_formatter import (
    apply_table_number_format,
    format_currency,
    format_growth_indicator,
    format_number,
    format_percentage,
)
from src.design_renderer.im_document import Currency, NumberFormatConfig


@pytest.fixture
def krw_config() -> NumberFormatConfig:
    return NumberFormatConfig()


@pytest.fixture
def usd_config() -> NumberFormatConfig:
    return NumberFormatConfig(
        currency=Currency.USD,
        scale="$M",
        decimal_places_amount=1,
    )


class TestFormatCurrency:
    """통화 포맷팅."""

    def test_krw_basic(self, krw_config: NumberFormatConfig):
        """KRW 기본 포맷."""
        result = format_currency(150_000, krw_config)
        assert "150,000" in result
        assert "억원" in result

    def test_usd_basic(self, usd_config: NumberFormatConfig):
        """USD 기본 포맷."""
        result = format_currency(250.5, usd_config)
        assert "$" in result or "M" in result

    def test_none_value(self, krw_config: NumberFormatConfig):
        """None 값 → N/A."""
        result = format_currency(None, krw_config)
        assert result == "N/A"

    def test_zero_value(self, krw_config: NumberFormatConfig):
        """0 값 포맷."""
        result = format_currency(0, krw_config)
        assert "0" in result


class TestFormatPercentage:
    """퍼센트 포맷팅."""

    def test_basic(self, krw_config: NumberFormatConfig):
        """기본 퍼센트 변환."""
        result = format_percentage(0.152, krw_config)
        assert "15.2" in result
        assert "%" in result

    def test_with_sign_positive(self, krw_config: NumberFormatConfig):
        """양수 + 부호 표시."""
        result = format_percentage(0.152, krw_config, show_sign=True)
        assert "+" in result

    def test_negative(self, krw_config: NumberFormatConfig):
        """음수 퍼센트."""
        result = format_percentage(-0.031, krw_config)
        assert "-" in result
        assert "3.1" in result


class TestFormatGrowthIndicator:
    """성장률 표시 (화살표 + 색상)."""

    def test_positive_growth(self, krw_config: NumberFormatConfig):
        """양수 성장률 → 녹색 ▲."""
        text, color = format_growth_indicator(0.152, krw_config)
        assert "▲" in text or "+" in text
        # 녹색 계열
        assert color is not None

    def test_negative_growth(self, krw_config: NumberFormatConfig):
        """음수 성장률 → 적색 ▼."""
        text, color = format_growth_indicator(-0.031, krw_config)
        assert "▼" in text or "-" in text
        assert color is not None

    def test_zero_growth(self, krw_config: NumberFormatConfig):
        """0% 성장률."""
        text, color = format_growth_indicator(0.0, krw_config)
        assert text is not None


class TestFormatNumber:
    """일반 숫자 포맷팅."""

    def test_nan_returns_na(self, krw_config: NumberFormatConfig):
        """NaN → N/A."""
        result = format_number(float("nan"), krw_config)
        assert result == "N/A"

    def test_inf_returns_na(self, krw_config: NumberFormatConfig):
        """Inf → N/A."""
        result = format_number(float("inf"), krw_config)
        assert result == "N/A"

    def test_normal_number(self, krw_config: NumberFormatConfig):
        """일반 숫자 포맷."""
        result = format_number(12345, krw_config)
        assert "12,345" in result or "12345" in result


class TestApplyTableNumberFormat:
    """테이블 숫자 일괄 포맷."""

    def test_formats_2d_list(self, krw_config: NumberFormatConfig):
        """2D 리스트 포맷 적용."""
        table = [
            ["항목", 100_000, 200_000],
            ["매출", 150_000, 180_000],
        ]
        result = apply_table_number_format(
            table, krw_config, first_col_is_label=True
        )
        assert len(result) == 2
        assert result[0][0] == "항목"  # 레이블은 그대로
        assert isinstance(result[0][1], str)  # 숫자는 문자열로 변환
