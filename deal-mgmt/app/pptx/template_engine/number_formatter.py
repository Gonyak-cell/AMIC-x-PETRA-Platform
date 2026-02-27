"""숫자 포맷팅 유틸리티 — 금액, 퍼센트, 음수 표기.

원본: im/src/design_renderer/components/number_formatter.py
deal-mgmt 독립 사용을 위해 의존성을 제거하고 단순화하였다.
"""

from __future__ import annotations

from .constants import NA_DISPLAY, THOUSANDS_SEPARATOR


def apply_thousands_sep(integer_str: str, sep: str = THOUSANDS_SEPARATOR) -> str:
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


def format_with_decimals(
    value: float,
    decimal_places: int = 0,
    sep: str = THOUSANDS_SEPARATOR,
) -> str:
    """소수점 + 천단위 구분 적용."""
    rounded = round(value, decimal_places)
    if decimal_places <= 0:
        return apply_thousands_sep(str(int(rounded)), sep)
    parts = f"{rounded:.{decimal_places}f}".split(".")
    integer_part = apply_thousands_sep(parts[0], sep)
    return f"{integer_part}.{parts[1]}"


def format_negative_parens(value: float | int | None, decimal_places: int = 0) -> str:
    """음수를 괄호 표기로 변환. 양수는 천단위 구분만 적용.

    Examples:
        >>> format_negative_parens(123456)
        '123,456'
        >>> format_negative_parens(-123456)
        '(123,456)'
        >>> format_negative_parens(0)
        '-'
    """
    if value is None:
        return NA_DISPLAY
    if value == 0:
        return "-"

    abs_formatted = format_with_decimals(abs(value), decimal_places)

    if value < 0:
        return f"({abs_formatted})"
    return abs_formatted


def format_currency_value(
    value: float | None,
    *,
    scale_factor: float = 1.0,
    decimal_places: int = 0,
    unit: str = "",
    show_unit: bool = True,
) -> str:
    """금액 포맷팅.

    Args:
        value: 원시 금액. None이면 N/A.
        scale_factor: 스케일링 (0.001 = 원→천원).
        decimal_places: 소수점 자릿수.
        unit: 단위 문자열 (예: "억원", "백만원").
        show_unit: 단위 표시 여부.

    Returns:
        포맷팅된 금액 문자열.
    """
    if value is None:
        return NA_DISPLAY

    scaled = value * scale_factor
    formatted = format_negative_parens(scaled, decimal_places)

    if show_unit and unit:
        return f"{formatted}{unit}"
    return formatted


def format_percentage(value: float | None, decimal_places: int = 1) -> str:
    """퍼센트 포맷팅.

    Args:
        value: 비율값 (0.15 = 15%). None이면 N/A.
        decimal_places: 소수점 자릿수.

    Returns:
        포맷팅된 퍼센트 문자열.
    """
    if value is None:
        return NA_DISPLAY

    pct = value * 100
    formatted = format_with_decimals(pct, decimal_places)
    return f"{formatted}%"


def format_cell_value(value: object) -> str:
    """셀 값을 문자열로 변환 (범용).

    - None → N/A
    - str → 그대로
    - int/float → 천단위 구분 + 음수 괄호
    """
    if value is None:
        return NA_DISPLAY
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return format_negative_parens(value)
    return str(value)
