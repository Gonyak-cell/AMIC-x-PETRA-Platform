"""섹션 렌더러 공통 포맷팅 유틸리티.

여러 렌더러에서 중복되던 금액/퍼센트/배수 포맷 함수를 통합한다.
"""

from __future__ import annotations


def fmt_amount(val: float | int | None, scale: str = "") -> str:
    """금액 포맷팅.

    Args:
        val: 숫자 값. None이면 "N/A".
        scale: 단위 접미사 (예: "억원", "백만원"). 기본 빈 문자열.

    Returns:
        콤마 구분 금액 문자열.
    """
    if val is None:
        return "N/A"
    return f"{val:,.0f}{scale}"


def fmt_pct(val: float | None, *, already_percent: bool = False) -> str:
    """퍼센트 포맷팅.

    Args:
        val: 숫자 값. None이면 "N/A".
        already_percent: True이면 val이 이미 %값 (예: 12.3).
            False이면 val이 소수점 비율 (예: 0.123).

    Returns:
        퍼센트 문자열 (예: "12.3%").
    """
    if val is None:
        return "N/A"
    pct = val if already_percent else val * 100
    return f"{pct:.1f}%"


def fmt_multiple(val: float | None) -> str:
    """배수 포맷팅.

    Args:
        val: 배수 값. None이면 "N/A".

    Returns:
        배수 문자열 (예: "8.5x").
    """
    if val is None:
        return "N/A"
    return f"{val:.1f}x"
