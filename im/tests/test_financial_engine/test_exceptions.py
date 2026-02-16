"""Financial Engine 예외 계층 테스트.

> 마지막 수정: 2026-02-09

예외 클래스의 상속 관계, message/details 필드 전파, 특수 파라미터 검증을
테스트합니다.
"""

from __future__ import annotations

import pytest

from src.financial_engine.exceptions import (
    AccountNotFoundError,
    AmbiguousMappingError,
    BalanceSheetError,
    CalculationError,
    ConsistencyError,
    CurrencyConversionError,
    FinancialEngineError,
    InsufficientDataError,
    MappingError,
    NormalizationError,
    UnitConversionError,
    ValidationError,
)


# ============================================================================
# 최상위 예외
# ============================================================================


class TestFinancialEngineError:
    """FinancialEngineError 기본 동작 테스트."""

    def test_메시지_저장(self) -> None:
        """message 속성이 올바르게 저장된다."""
        exc = FinancialEngineError("테스트 오류")
        assert exc.message == "테스트 오류"
        assert str(exc) == "테스트 오류"

    def test_details_기본값_빈딕셔너리(self) -> None:
        """details 미지정 시 빈 dict가 기본값이다."""
        exc = FinancialEngineError("오류")
        assert exc.details == {}

    def test_details_전달(self) -> None:
        """details dict가 올바르게 전달된다."""
        details = {"key": "value", "count": 42}
        exc = FinancialEngineError("오류", details=details)
        assert exc.details == details
        assert exc.details["key"] == "value"

    def test_Exception_상속(self) -> None:
        """FinancialEngineError는 Exception의 서브클래스이다."""
        assert issubclass(FinancialEngineError, Exception)


# ============================================================================
# 상속 관계 테스트
# ============================================================================


@pytest.mark.parametrize(
    ("child_cls", "parent_cls"),
    [
        (MappingError, FinancialEngineError),
        (AccountNotFoundError, MappingError),
        (AmbiguousMappingError, MappingError),
        (NormalizationError, FinancialEngineError),
        (UnitConversionError, NormalizationError),
        (CurrencyConversionError, NormalizationError),
        (CalculationError, FinancialEngineError),
        (InsufficientDataError, CalculationError),
        (ValidationError, FinancialEngineError),
        (BalanceSheetError, ValidationError),
        (ConsistencyError, ValidationError),
    ],
    ids=[
        "MappingError→FinancialEngineError",
        "AccountNotFoundError→MappingError",
        "AmbiguousMappingError→MappingError",
        "NormalizationError→FinancialEngineError",
        "UnitConversionError→NormalizationError",
        "CurrencyConversionError→NormalizationError",
        "CalculationError→FinancialEngineError",
        "InsufficientDataError→CalculationError",
        "ValidationError→FinancialEngineError",
        "BalanceSheetError→ValidationError",
        "ConsistencyError→ValidationError",
    ],
)
def test_예외_상속_관계(child_cls: type, parent_cls: type) -> None:
    """자식 예외는 부모 예외의 서브클래스여야 한다."""
    assert issubclass(child_cls, parent_cls)


# ============================================================================
# 개별 예외 details 검증
# ============================================================================


class TestAccountNotFoundError:
    """AccountNotFoundError 세부 테스트."""

    def test_account_name_저장(self) -> None:
        """account_name 속성이 올바르게 저장된다."""
        exc = AccountNotFoundError("미상계정")
        assert exc.account_name == "미상계정"
        assert exc.details["account_name"] == "미상계정"

    def test_candidates_기본값_빈리스트(self) -> None:
        """candidates 미지정 시 빈 list가 기본값이다."""
        exc = AccountNotFoundError("미상계정")
        assert exc.details["candidates"] == []

    def test_candidates_전달(self) -> None:
        """candidates 리스트가 details에 올바르게 전달된다."""
        exc = AccountNotFoundError("미상계정", candidates=["매출액", "매출원가"])
        assert exc.details["candidates"] == ["매출액", "매출원가"]

    def test_메시지_포맷(self) -> None:
        """오류 메시지에 계정명이 포함된다."""
        exc = AccountNotFoundError("특이계정")
        assert "특이계정" in str(exc)


class TestAmbiguousMappingError:
    """AmbiguousMappingError 세부 테스트."""

    def test_details_candidates_전달(self) -> None:
        """복수 후보 목록이 details에 올바르게 전달된다."""
        candidates = [
            {"account": "REVENUE", "score": 95},
            {"account": "OPERATING_INCOME", "score": 85},
        ]
        exc = AmbiguousMappingError("영업수익", candidates=candidates)
        assert exc.details["account_name"] == "영업수익"
        assert len(exc.details["candidates"]) == 2


class TestUnitConversionError:
    """UnitConversionError 세부 테스트."""

    def test_details_필드_전달(self) -> None:
        """value, source_unit, reason이 details에 전달된다."""
        exc = UnitConversionError(value="abc", source_unit="백만원", reason="숫자 아님")
        assert exc.details["value"] == "abc"
        assert exc.details["source_unit"] == "백만원"
        assert exc.details["reason"] == "숫자 아님"


class TestCurrencyConversionError:
    """CurrencyConversionError 세부 테스트."""

    def test_details_통화_정보(self) -> None:
        """from_currency, to_currency, reason이 details에 전달된다."""
        exc = CurrencyConversionError("KRW", "USD", reason="환율 미설정")
        assert exc.details["from_currency"] == "KRW"
        assert exc.details["to_currency"] == "USD"
        assert exc.details["reason"] == "환율 미설정"


class TestInsufficientDataError:
    """InsufficientDataError 세부 테스트."""

    def test_details_metric_missing_fields(self) -> None:
        """metric, missing_fields가 details에 전달된다."""
        exc = InsufficientDataError("EBITDA", ["DEPRECIATION", "AMORTIZATION"])
        assert exc.details["metric"] == "EBITDA"
        assert exc.details["missing_fields"] == ["DEPRECIATION", "AMORTIZATION"]


class TestBalanceSheetError:
    """BalanceSheetError 세부 테스트."""

    def test_details_year_difference(self) -> None:
        """year, difference가 details에 전달된다."""
        exc = BalanceSheetError(year="2024", difference="50,000,000")
        assert exc.details["year"] == "2024"
        assert exc.details["difference"] == "50,000,000"


class TestConsistencyError:
    """ConsistencyError 세부 테스트."""

    def test_details_anomalies(self) -> None:
        """anomalies 리스트가 details에 전달된다."""
        anomalies = [
            {"account": "REVENUE", "year": "2023", "issue": "음수"},
        ]
        exc = ConsistencyError(anomalies=anomalies)
        assert exc.details["anomalies"] == anomalies
        assert "1건" in str(exc)
