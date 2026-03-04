"""Financial Engine 모듈 커스텀 예외 계층.

계정 매핑, 단위 정규화, 지표 계산, 데이터 검증에서 발생하는 예외를 정의합니다.
"""

from __future__ import annotations

from typing import Any


class FinancialEngineError(Exception):
    """Financial Engine 모듈 최상위 예외."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ============================================================================
# 계정 매핑 예외
# ============================================================================


class MappingError(FinancialEngineError):
    """계정 매핑 관련 예외."""

    pass


class AccountNotFoundError(MappingError):
    """한글 계정명에 대한 표준 계정 매핑을 찾을 수 없음."""

    def __init__(self, account_name: str, candidates: list[str] | None = None) -> None:
        super().__init__(
            message=f"계정 매핑 실패: '{account_name}'에 대한 표준 계정을 찾을 수 없습니다.",
            details={"account_name": account_name, "candidates": candidates or []},
        )
        self.account_name = account_name


class AmbiguousMappingError(MappingError):
    """한글 계정명이 여러 표준 계정에 매핑될 수 있음."""

    def __init__(self, account_name: str, candidates: list[dict[str, Any]]) -> None:
        super().__init__(
            message=f"모호한 계정 매핑: '{account_name}'에 대해 복수의 후보가 존재합니다.",
            details={"account_name": account_name, "candidates": candidates},
        )


# ============================================================================
# 정규화 예외
# ============================================================================


class NormalizationError(FinancialEngineError):
    """단위/통화 정규화 관련 예외."""

    pass


class UnitConversionError(NormalizationError):
    """단위 변환 실패."""

    def __init__(
        self, value: str, source_unit: str | None = None, reason: str = ""
    ) -> None:
        super().__init__(
            message=f"단위 변환 실패: '{value}'",
            details={"value": value, "source_unit": source_unit, "reason": reason},
        )


class CurrencyConversionError(NormalizationError):
    """통화 변환 실패."""

    def __init__(
        self,
        from_currency: str,
        to_currency: str,
        reason: str = "",
    ) -> None:
        super().__init__(
            message=f"통화 변환 실패: {from_currency} → {to_currency}",
            details={
                "from_currency": from_currency,
                "to_currency": to_currency,
                "reason": reason,
            },
        )


# ============================================================================
# 계산 예외
# ============================================================================


class CalculationError(FinancialEngineError):
    """지표 계산 관련 예외."""

    pass


class InsufficientDataError(CalculationError):
    """계산에 필요한 데이터 부족."""

    def __init__(self, metric: str, missing_fields: list[str]) -> None:
        super().__init__(
            message=f"데이터 부족: '{metric}' 계산에 필요한 항목이 없습니다.",
            details={"metric": metric, "missing_fields": missing_fields},
        )


# ============================================================================
# 검증 예외
# ============================================================================


class ValidationError(FinancialEngineError):
    """데이터 검증 관련 예외."""

    pass


class BalanceSheetError(ValidationError):
    """재무상태표 균형 검증 실패 (자산 ≠ 부채 + 자본)."""

    def __init__(self, year: str, difference: str) -> None:
        super().__init__(
            message=f"재무상태표 불균형 ({year}): 차이 {difference}",
            details={"year": year, "difference": difference},
        )


class ConsistencyError(ValidationError):
    """다기간 데이터 일관성 검증 실패."""

    def __init__(self, anomalies: list[dict[str, Any]]) -> None:
        super().__init__(
            message=f"데이터 일관성 검증 실패: {len(anomalies)}건의 이상 항목",
            details={"anomalies": anomalies},
        )
