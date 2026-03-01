"""공용 숫자 변환 유틸리티.

CSV/Excel 파싱 시 안전한 Decimal/int 변환을 제공한다.
"""

from decimal import Decimal, InvalidOperation


def safe_decimal(value: object) -> Decimal | None:
    """안전한 Decimal 변환.

    - None, 빈 문자열, "-", "0" → None
    - 쉼표 구분 숫자 지원 ("1,234,567" → 1234567)
    - 변환 불가 시 None 반환
    """
    if value is None:
        return None
    try:
        s = str(value).strip().replace(",", "")
        if s in ("", "-", "0"):
            return None
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def safe_int(value: object) -> int | None:
    """안전한 int 변환.

    - None, 빈 문자열, "-" → None
    - 쉼표 구분 숫자 지원 ("1,234" → 1234)
    - 소수점 숫자 → 정수 절삭 ("3.14" → 3)
    - 변환 불가 시 None 반환
    """
    if value is None:
        return None
    try:
        s = str(value).strip().replace(",", "")
        if s in ("", "-"):
            return None
        return int(float(s))
    except (ValueError, TypeError):
        return None
