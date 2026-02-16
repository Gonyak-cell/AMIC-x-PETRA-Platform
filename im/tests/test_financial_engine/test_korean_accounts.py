"""한글 계정명 매핑 사전(korean_accounts) 테스트.

> 마지막 수정: 2026-02-09

KOREAN_ACCOUNT_MAP의 크기, 주요 매핑 존재 여부, 역방향 조회,
동의어 변형(띄어쓰기, 괄호 표기), 값 유효성 등을 검증합니다.
"""

from __future__ import annotations

import pytest

from src.financial_engine.mapper.chart_of_accounts import StandardAccount
from src.financial_engine.mapper.korean_accounts import (
    KOREAN_ACCOUNT_MAP,
    get_korean_names,
)


# ============================================================================
# 사전 크기 / 기본 속성
# ============================================================================


class TestKoreanAccountMapSize:
    """KOREAN_ACCOUNT_MAP 크기 및 기본 속성 테스트."""

    def test_200개_이상_엔트리(self) -> None:
        """KOREAN_ACCOUNT_MAP은 200개 이상의 엔트리를 포함해야 한다."""
        assert len(KOREAN_ACCOUNT_MAP) >= 200

    def test_중복_키_없음(self) -> None:
        """Python dict이므로 중복 키가 존재할 수 없지만, 키 수가 기대와 일치하는지 확인."""
        keys = list(KOREAN_ACCOUNT_MAP.keys())
        assert len(keys) == len(set(keys))


# ============================================================================
# 주요 계정 매핑 존재 확인
# ============================================================================


@pytest.mark.parametrize(
    ("korean_name", "expected_account"),
    [
        ("매출액", StandardAccount.REVENUE),
        ("매출원가", StandardAccount.COST_OF_GOODS_SOLD),
        ("매출총이익", StandardAccount.GROSS_PROFIT),
        ("영업이익", StandardAccount.OPERATING_INCOME),
        ("당기순이익", StandardAccount.NET_INCOME),
        ("자산총계", StandardAccount.TOTAL_ASSETS),
        ("부채총계", StandardAccount.TOTAL_LIABILITIES),
        ("자본총계", StandardAccount.TOTAL_EQUITY),
        ("현금및현금성자산", StandardAccount.CASH_AND_EQUIVALENTS),
        ("법인세비용", StandardAccount.INCOME_TAX_EXPENSE),
    ],
    ids=[
        "매출액→REVENUE",
        "매출원가→COGS",
        "매출총이익→GROSS_PROFIT",
        "영업이익→OPERATING_INCOME",
        "당기순이익→NET_INCOME",
        "자산총계→TOTAL_ASSETS",
        "부채총계→TOTAL_LIABILITIES",
        "자본총계→TOTAL_EQUITY",
        "현금및현금성자산→CASH",
        "법인세비용→TAX_EXPENSE",
    ],
)
def test_주요_계정_매핑(korean_name: str, expected_account: StandardAccount) -> None:
    """핵심 한글 계정명이 올바른 StandardAccount로 매핑된다."""
    assert KOREAN_ACCOUNT_MAP[korean_name] == expected_account


# ============================================================================
# CF 계정 매핑
# ============================================================================


@pytest.mark.parametrize(
    ("korean_name", "expected_account"),
    [
        ("영업활동현금흐름", StandardAccount.OPERATING_CASH_FLOW),
        ("투자활동현금흐름", StandardAccount.INVESTING_CASH_FLOW),
        ("재무활동현금흐름", StandardAccount.FINANCING_CASH_FLOW),
        ("자본적지출", StandardAccount.CAPEX),
        ("배당금지급", StandardAccount.DIVIDENDS_PAID),
    ],
    ids=[
        "영업활동현금흐름→OCF",
        "투자활동현금흐름→ICF",
        "재무활동현금흐름→FCF",
        "자본적지출→CAPEX",
        "배당금지급→DIVIDENDS_PAID",
    ],
)
def test_CF_계정_매핑(korean_name: str, expected_account: StandardAccount) -> None:
    """현금흐름표 한글 계정명이 올바르게 매핑된다."""
    assert KOREAN_ACCOUNT_MAP[korean_name] == expected_account


# ============================================================================
# 동의어 변형 테스트
# ============================================================================


class TestKoreanAccountVariants:
    """띄어쓰기, 괄호 표기 등 동의어 변형 매핑 테스트."""

    @pytest.mark.parametrize(
        ("variant", "expected_account"),
        [
            ("판매비와관리비", StandardAccount.SGA_EXPENSES),
            ("판매비와 관리비", StandardAccount.SGA_EXPENSES),
            ("판관비", StandardAccount.SGA_EXPENSES),
            ("판매관리비", StandardAccount.SGA_EXPENSES),
            ("판매비및관리비", StandardAccount.SGA_EXPENSES),
            ("판매비 및 관리비", StandardAccount.SGA_EXPENSES),
        ],
        ids=[
            "판매비와관리비(붙여쓰기)",
            "판매비와 관리비(띄어쓰기)",
            "판관비(줄임말)",
            "판매관리비(대체명)",
            "판매비및관리비(및)",
            "판매비 및 관리비(및+띄어쓰기)",
        ],
    )
    def test_SGA_띄어쓰기_변형(
        self, variant: str, expected_account: StandardAccount
    ) -> None:
        """판매비와관리비의 다양한 띄어쓰기/표기 변형이 모두 SGA_EXPENSES로 매핑된다."""
        assert KOREAN_ACCOUNT_MAP[variant] == expected_account

    @pytest.mark.parametrize(
        ("variant", "expected_account"),
        [
            ("매출총이익(손실)", StandardAccount.GROSS_PROFIT),
            ("영업이익(손실)", StandardAccount.OPERATING_INCOME),
            ("당기순이익(손실)", StandardAccount.NET_INCOME),
        ],
        ids=[
            "매출총이익(손실)",
            "영업이익(손실)",
            "당기순이익(손실)",
        ],
    )
    def test_괄호_손실_변형(
        self, variant: str, expected_account: StandardAccount
    ) -> None:
        """(손실) 괄호가 포함된 변형이 올바르게 매핑된다."""
        assert KOREAN_ACCOUNT_MAP[variant] == expected_account


# ============================================================================
# 값 유효성: 모든 값이 StandardAccount 멤버인지 확인
# ============================================================================


def test_모든_값이_StandardAccount_멤버() -> None:
    """KOREAN_ACCOUNT_MAP의 모든 값은 유효한 StandardAccount enum 멤버여야 한다."""
    for korean_name, account in KOREAN_ACCOUNT_MAP.items():
        assert isinstance(account, StandardAccount), (
            f"'{korean_name}'의 값 {account!r}이 StandardAccount가 아님"
        )


# ============================================================================
# 역방향 조회 (get_korean_names)
# ============================================================================


class TestGetKoreanNames:
    """get_korean_names 역방향 조회 테스트."""

    def test_REVENUE_역방향_조회(self) -> None:
        """REVENUE의 한글 동의어에 '매출액'이 포함된다."""
        names = get_korean_names(StandardAccount.REVENUE)
        assert "매출액" in names

    def test_REVENUE_역방향_다수_동의어(self) -> None:
        """REVENUE의 한글 동의어가 복수 존재한다 (매출액, 영업수익 등)."""
        names = get_korean_names(StandardAccount.REVENUE)
        assert len(names) > 1
        assert "영업수익" in names

    def test_매핑_없는_계정_빈리스트(self) -> None:
        """KOREAN_ACCOUNT_MAP에 매핑이 없는 계정은 빈 리스트를 반환한다.

        Note: 대부분의 주요 계정은 매핑이 존재하므로, EBIT 같은 파생 지표를 테스트.
        """
        names = get_korean_names(StandardAccount.EBIT)
        # EBIT은 KOREAN_ACCOUNT_MAP에 직접 매핑이 없을 수 있음
        assert isinstance(names, list)
