"""숫자 표기 규칙 엔진 — 통화, 퍼센트, 성장 지표 포맷팅.

IM 문서 전체에서 숫자의 가독성과 전문성을 보장한다.
NumberFormatConfig(im_document.py)에 정의된 전역 설정에 따라 포맷팅.
"""

from __future__ import annotations

import math
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS
from src.design_renderer.im_document import Currency, NumberFormatConfig


def _get_config(config: NumberFormatConfig | None) -> NumberFormatConfig:
    """None이면 기본 NumberFormatConfig 반환."""
    return config if config is not None else NumberFormatConfig()


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _apply_thousands_sep(integer_str: str, sep: str) -> str:
    """정수 문자열에 천단위 구분자 삽입."""
    negative = integer_str.startswith("-")
    digits = integer_str.lstrip("-")
    result_parts: list[str] = []
    for i, ch in enumerate(reversed(digits)):
        if i > 0 and i % 3 == 0:
            result_parts.append(sep)
        result_parts.append(ch)
    formatted = "".join(reversed(result_parts))
    return f"-{formatted}" if negative else formatted


def _format_with_decimals(
    value: float,
    decimal_places: int,
    thousands_sep: str,
) -> str:
    """소수점 + 천단위 구분 적용."""
    rounded = round(value, decimal_places)
    if decimal_places <= 0:
        return _apply_thousands_sep(str(int(rounded)), thousands_sep)
    parts = f"{rounded:.{decimal_places}f}".split(".")
    integer_part = _apply_thousands_sep(parts[0], thousands_sep)
    return f"{integer_part}.{parts[1]}"


def _format_negative(formatted: str, value: float, fmt: str) -> str:
    """음수 표기 형식 적용."""
    if value >= 0:
        return formatted
    # formatted는 이미 '-'가 포함되어 있을 수 있음
    abs_formatted = formatted.lstrip("-")
    if fmt == "parens":
        return f"({abs_formatted})"
    return f"-{abs_formatted}"


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------


def format_currency(
    value: float | None,
    config: NumberFormatConfig | None = None,
    *,
    show_unit: bool = True,
) -> str:
    """금액 포맷팅.

    스케일에 따라 자동 변환:
    - "억원": value를 억 단위로 표시 (value가 백만원 단위인 경우)
    - "$M": value를 M 단위로 표시
    - "$B": value를 B 단위로 표시
    - "백만원": 그대로

    Args:
        value: 금액 (원시 단위). None이면 N/A 반환.
        config: 숫자 표기 설정. None이면 KRW/억원 기본값.
        show_unit: 단위 표시 여부.

    Returns:
        포맷팅된 금액 문자열.

    Examples:
        >>> format_currency(150_000)
        '150,000억원'
        >>> format_currency(None)
        'N/A'
    """
    cfg = _get_config(config)
    if value is None:
        return cfg.na_display

    formatted = _format_with_decimals(
        abs(value), cfg.decimal_places_amount, cfg.thousands_sep
    )
    formatted = _format_negative(formatted, value, cfg.negative_format)

    if show_unit:
        unit = cfg.scale
        if cfg.currency == Currency.USD:
            if unit in ("$M", "$B"):
                return f"${formatted}{unit[-1]}"
            return f"${formatted}"
        if cfg.currency == Currency.EUR:
            return f"€{formatted}"
        # KRW
        return f"{formatted}{unit}"
    return formatted


def format_percentage(
    value: float | None,
    config: NumberFormatConfig | None = None,
    *,
    show_sign: bool = False,
) -> str:
    """퍼센트 포맷팅.

    Args:
        value: 비율 (0.152 → 15.2%). None이면 N/A.
        config: 숫자 표기 설정.
        show_sign: True이면 양수에 '+' 접두사.

    Returns:
        포맷팅된 퍼센트 문자열.

    Examples:
        >>> format_percentage(0.152)
        '15.2%'
        >>> format_percentage(-0.031, show_sign=True)
        '-3.1%'
    """
    cfg = _get_config(config)
    if value is None:
        return cfg.na_display

    pct_value = value * 100
    formatted = f"{pct_value:.{cfg.decimal_places_pct}f}"

    if show_sign and pct_value > 0:
        formatted = f"+{formatted}"

    return f"{formatted}%"


def format_growth_indicator(
    value: float | None,
    config: NumberFormatConfig | None = None,
) -> tuple[str, str]:
    """성장 지표 포맷팅 + 색상 반환.

    Args:
        value: 성장률 (0.152 → +15.2%). None이면 N/A.
        config: 숫자 표기 설정.

    Returns:
        (formatted_text, color_hex) 튜플.
        양수: ("▲ +15.2%", "#26C260")
        음수: ("▼ -3.1%", "#BC2C1A")
        영/None: ("— N/A", "#777777")

    Examples:
        >>> format_growth_indicator(0.152)
        ('▲ +15.2%', '#26C260')
        >>> format_growth_indicator(-0.031)
        ('▼ -3.1%', '#BC2C1A')
    """
    tokens = DEFAULT_TOKENS
    cfg = _get_config(config)

    if value is None:
        return f"— {cfg.na_display}", tokens.colors.text_secondary

    pct_str = format_percentage(value, config, show_sign=True)

    if value > 0:
        return f"▲ {pct_str}", tokens.colors.positive
    if value < 0:
        return f"▼ {pct_str}", tokens.colors.negative
    return f"— {pct_str}", tokens.colors.text_secondary


def format_number(
    value: float | None,
    config: NumberFormatConfig | None = None,
    *,
    decimal_places: int | None = None,
    unit: str = "",
) -> str:
    """범용 숫자 포맷팅.

    Args:
        value: 숫자. None이면 N/A.
        config: 숫자 표기 설정.
        decimal_places: 소수 자릿수 오버라이드. None이면 config 기본값.
        unit: 단위 접미사.

    Returns:
        포맷팅된 숫자 문자열.

    Examples:
        >>> format_number(1234567.89, decimal_places=1)
        '1,234,567.9'
    """
    cfg = _get_config(config)
    if value is None:
        return cfg.na_display

    # 문자열이면 그대로 반환
    if isinstance(value, str):
        return value

    if math.isnan(value) or math.isinf(value):
        return cfg.na_display

    dp = decimal_places if decimal_places is not None else cfg.decimal_places_amount
    formatted = _format_with_decimals(abs(value), dp, cfg.thousands_sep)
    formatted = _format_negative(formatted, value, cfg.negative_format)

    if unit:
        return f"{formatted}{unit}"
    return formatted


def apply_table_number_format(
    table_data: list[list[Any]],
    config: NumberFormatConfig | None = None,
    *,
    first_col_is_label: bool = True,
) -> list[list[str]]:
    """테이블 전체에 숫자 포맷 일괄 적용.

    Args:
        table_data: 2D 리스트. 각 셀은 float, None, 또는 str.
        config: 숫자 표기 설정.
        first_col_is_label: True이면 첫 번째 열은 포맷팅하지 않음.

    Returns:
        포맷팅된 문자열 2D 리스트.
    """
    cfg = _get_config(config)
    result: list[list[str]] = []

    for row in table_data:
        formatted_row: list[str] = []
        for col_idx, cell in enumerate(row):
            if first_col_is_label and col_idx == 0:
                formatted_row.append(str(cell) if cell is not None else "")
            elif cell is None:
                formatted_row.append(cfg.na_display)
            elif isinstance(cell, (int, float)):
                formatted_row.append(format_currency(cell, cfg, show_unit=False))
            else:
                formatted_row.append(str(cell))
        result.append(formatted_row)

    return result
