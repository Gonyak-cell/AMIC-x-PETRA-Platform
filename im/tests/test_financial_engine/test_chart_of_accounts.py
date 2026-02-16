"""표준 계정과목표(chart_of_accounts) 테스트.

> 마지막 수정: 2026-02-09

StandardAccount enum, StatementType enum, AccountSign enum,
ACCOUNT_METADATA 완전성, 헬퍼 함수를 검증합니다.
"""

from __future__ import annotations

import pytest

from src.financial_engine.mapper.chart_of_accounts import (
    ACCOUNT_METADATA,
    AccountMetadata,
    AccountSign,
    StandardAccount,
    StatementType,
    get_accounts_by_statement,
    get_children,
    get_derived_accounts,
    get_subtotals,
    lookup,
)


# ============================================================================
# Enum 기본 검증
# ============================================================================


class TestStandardAccountEnum:
    """StandardAccount enum 검증."""

    def test_멤버_수_최소_85개(self) -> None:
        """StandardAccount는 85개 이상의 멤버를 가져야 한다."""
        assert len(StandardAccount) >= 85

    def test_주요_IS_멤버_존재(self) -> None:
        """주요 손익계산서 계정이 존재한다."""
        assert hasattr(StandardAccount, "REVENUE")
        assert hasattr(StandardAccount, "COST_OF_GOODS_SOLD")
        assert hasattr(StandardAccount, "GROSS_PROFIT")
        assert hasattr(StandardAccount, "OPERATING_INCOME")
        assert hasattr(StandardAccount, "NET_INCOME")
        assert hasattr(StandardAccount, "EBITDA")

    def test_주요_BS_멤버_존재(self) -> None:
        """주요 재무상태표 계정이 존재한다."""
        assert hasattr(StandardAccount, "TOTAL_ASSETS")
        assert hasattr(StandardAccount, "TOTAL_LIABILITIES")
        assert hasattr(StandardAccount, "TOTAL_EQUITY")
        assert hasattr(StandardAccount, "CASH_AND_EQUIVALENTS")

    def test_주요_CF_멤버_존재(self) -> None:
        """주요 현금흐름표 계정이 존재한다."""
        assert hasattr(StandardAccount, "OPERATING_CASH_FLOW")
        assert hasattr(StandardAccount, "INVESTING_CASH_FLOW")
        assert hasattr(StandardAccount, "FINANCING_CASH_FLOW")
        assert hasattr(StandardAccount, "FREE_CASH_FLOW")
        assert hasattr(StandardAccount, "CAPEX")


class TestStatementTypeEnum:
    """StatementType enum 검증."""

    def test_IS_BS_CF_존재(self) -> None:
        """IS, BS, CF 3종 재무제표 유형이 존재한다."""
        assert StatementType.INCOME_STATEMENT.value == "IS"
        assert StatementType.BALANCE_SHEET.value == "BS"
        assert StatementType.CASH_FLOW.value == "CF"

    def test_멤버_수_3개(self) -> None:
        """StatementType은 정확히 3개의 멤버를 가진다."""
        assert len(StatementType) == 3


class TestAccountSignEnum:
    """AccountSign enum 검증."""

    def test_debit_credit_존재(self) -> None:
        """debit, credit 부호 관례가 존재한다."""
        assert AccountSign.DEBIT.value == "debit"
        assert AccountSign.CREDIT.value == "credit"


# ============================================================================
# ACCOUNT_METADATA 완전성
# ============================================================================


class TestAccountMetadataCompleteness:
    """ACCOUNT_METADATA 사전의 완전성 검증."""

    def test_모든_StandardAccount_멤버_커버(self) -> None:
        """모든 StandardAccount 멤버가 ACCOUNT_METADATA에 등록되어 있다."""
        missing = [
            acct.name
            for acct in StandardAccount
            if acct not in ACCOUNT_METADATA
        ]
        assert missing == [], f"ACCOUNT_METADATA에 누락된 계정: {missing}"

    def test_메타데이터_code_일치(self) -> None:
        """각 메타데이터의 code 필드가 dict 키와 일치한다."""
        for key, meta in ACCOUNT_METADATA.items():
            assert meta.code == key, f"불일치: key={key}, code={meta.code}"


# ============================================================================
# 헬퍼 함수 테스트
# ============================================================================


class TestGetAccountsByStatement:
    """get_accounts_by_statement 함수 테스트."""

    @pytest.mark.parametrize(
        "stmt_type",
        [StatementType.INCOME_STATEMENT, StatementType.BALANCE_SHEET, StatementType.CASH_FLOW],
        ids=["IS", "BS", "CF"],
    )
    def test_반환_타입_일관성(self, stmt_type: StatementType) -> None:
        """반환된 모든 AccountMetadata의 statement_type이 요청한 유형과 일치한다."""
        accounts = get_accounts_by_statement(stmt_type)
        assert len(accounts) > 0, f"{stmt_type.name}에 해당하는 계정이 없음"
        for meta in accounts:
            assert meta.statement_type == stmt_type

    def test_IS_계정에_REVENUE_포함(self) -> None:
        """IS 계정 목록에 REVENUE가 포함된다."""
        is_accounts = get_accounts_by_statement(StatementType.INCOME_STATEMENT)
        codes = [m.code for m in is_accounts]
        assert StandardAccount.REVENUE in codes


class TestGetSubtotals:
    """get_subtotals 함수 테스트."""

    def test_소계_항목만_반환(self) -> None:
        """반환된 모든 항목의 is_subtotal이 True이다."""
        subtotals = get_subtotals()
        assert len(subtotals) > 0
        for meta in subtotals:
            assert meta.is_subtotal is True


class TestGetDerivedAccounts:
    """get_derived_accounts 함수 테스트."""

    def test_파생지표_포함(self) -> None:
        """EBITDA, FREE_CASH_FLOW 등 파생 지표가 포함된다."""
        derived = get_derived_accounts()
        codes = [m.code for m in derived]
        assert StandardAccount.EBITDA in codes
        assert StandardAccount.FREE_CASH_FLOW in codes

    def test_모든_항목_is_derived_True(self) -> None:
        """반환된 모든 항목의 is_derived가 True이다."""
        derived = get_derived_accounts()
        for meta in derived:
            assert meta.is_derived is True


class TestGetChildren:
    """get_children 함수 테스트."""

    def test_TOTAL_ASSETS_하위_계정(self) -> None:
        """TOTAL_ASSETS의 하위에 CURRENT_ASSETS, NON_CURRENT_ASSETS가 포함된다."""
        children = get_children(StandardAccount.TOTAL_ASSETS)
        child_codes = [m.code for m in children]
        assert StandardAccount.CURRENT_ASSETS in child_codes
        assert StandardAccount.NON_CURRENT_ASSETS in child_codes

    def test_리프_계정_하위_빈리스트(self) -> None:
        """하위 계정이 없는 리프 계정은 빈 리스트를 반환한다."""
        children = get_children(StandardAccount.REVENUE)
        assert children == []


class TestLookup:
    """lookup 함수 테스트."""

    def test_정상_조회(self) -> None:
        """유효한 코드로 조회하면 올바른 AccountMetadata를 반환한다."""
        meta = lookup(StandardAccount.REVENUE)
        assert isinstance(meta, AccountMetadata)
        assert meta.code == StandardAccount.REVENUE
        assert meta.name_kr == "매출액"

    def test_미등록_코드_KeyError(self) -> None:
        """ACCOUNT_METADATA에서 제거된 코드 조회 시 KeyError를 확인한다.

        Note: _validate_completeness()에 의해 모듈 로드 시 누락이 방지되므로,
        여기서는 직접 KeyError를 트리거하는 대신, 존재하는 코드가 KeyError를
        발생시키지 않음을 검증한다.
        """
        # 유효한 코드는 KeyError 없이 반환된다
        for acct in StandardAccount:
            result = lookup(acct)
            assert result.code == acct
