"""금액(Decimal) 처리 규칙 (마스터파일 §8.1).

절대 규칙:
- 모든 금액은 Decimal 타입 (float 금지)
- 원화: 소수점 없음 (정수 처리)
- 외화: 소수점 4자리
- 라운딩: 원단위 반올림(거래별), 백만원 반올림(보고서)
- 차변/대변 합계 일치 검증 필수
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

# 정밀도 상수
KRW_QUANTIZE = Decimal("1")  # 원화: 정수
FOREIGN_QUANTIZE = Decimal("0.0001")  # 외화: 소수점 4자리
REPORT_QUANTIZE = Decimal("1000000")  # 보고서: 백만원 단위


def to_decimal(value: Any) -> Decimal:
    """값을 Decimal로 안전 변환한다.

    float 입력은 str 변환 후 처리하여 부동소수점 오차를 방지한다.

    Raises:
        TypeError: Decimal로 변환할 수 없는 타입.
        ValueError: 숫자로 변환할 수 없는 값.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        # float → str → Decimal (부동소수점 오차 방지)
        return Decimal(str(value))
    if isinstance(value, (int, str)):
        try:
            return Decimal(value)
        except InvalidOperation as e:
            raise ValueError(f"Cannot convert to Decimal: {value!r}") from e
    raise TypeError(f"Unsupported type for Decimal conversion: {type(value).__name__}")


def round_krw(amount: Decimal) -> Decimal:
    """원화 금액을 원단위 반올림한다."""
    return amount.quantize(KRW_QUANTIZE, rounding=ROUND_HALF_UP)


def round_foreign(amount: Decimal, places: int = 4) -> Decimal:
    """외화 금액을 지정 소수점 자리로 반올림한다."""
    quantize = Decimal(10) ** -places
    return amount.quantize(quantize, rounding=ROUND_HALF_UP)


def round_for_report(amount: Decimal) -> Decimal:
    """보고서용 백만원 단위 반올림."""
    return (amount / REPORT_QUANTIZE).quantize(
        KRW_QUANTIZE, rounding=ROUND_HALF_UP
    ) * REPORT_QUANTIZE


def check_balance(debit_total: Decimal, credit_total: Decimal) -> bool:
    """차변/대변 합계 일치를 검증한다.

    마스터파일 §8.1: 차변/대변 합계 일치 검증은 모든 처리 후 자동 실행.
    """
    return debit_total == credit_total


def assert_balance(
    debit_total: Decimal,
    credit_total: Decimal,
    *,
    label: str = "tie-out",
) -> None:
    """차변/대변 합계가 일치하지 않으면 예외를 발생시킨다.

    Raises:
        app.core.exceptions.DataIntegrityError
    """
    if debit_total != credit_total:
        from app.core.errors import ErrorCode
        from app.core.exceptions import DataIntegrityError

        diff = debit_total - credit_total
        raise DataIntegrityError(
            ErrorCode.INGEST_TB_MISMATCH,
            f"{label} failed: debit={debit_total}, credit={credit_total}, diff={diff}",
            context={
                "debit": str(debit_total),
                "credit": str(credit_total),
                "diff": str(diff),
            },
        )
