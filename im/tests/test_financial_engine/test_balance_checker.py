# -*- coding: utf-8 -*-
"""BalanceChecker 단위 테스트.

재무상태표 균형 검증기(자산 = 부채 + 자본)의 정확성을 검증합니다.
절대 허용 오차, 비율 허용 오차, None 값 처리, 다중 연도 혼합 등을 테스트합니다.

> 마지막 수정: 2026-02-09 16:29:23
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.financial_engine.validator.balance_checker import (
    BalanceCheckConfig,
    BalanceCheckReport,
    BalanceCheckResult,
    BalanceChecker,
)


# ---------------------------------------------------------------------------
# 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
def checker() -> BalanceChecker:
    """기본 설정의 BalanceChecker를 반환한다."""
    return BalanceChecker()


# ---------------------------------------------------------------------------
# 테스트: BalanceChecker.check_year / check
# ---------------------------------------------------------------------------


class TestBalanceCheckerBalanced:
    """균형인 경우 테스트."""

    def test_perfectly_balanced(self, checker: BalanceChecker) -> None:
        """자산 == 부채 + 자본이면 is_balanced=True, difference=0."""
        report = checker.check(
            total_assets={"2023": Decimal("100000")},
            total_liabilities={"2023": Decimal("60000")},
            total_equity={"2023": Decimal("40000")},
        )
        assert report.all_balanced is True
        assert len(report.results) == 1
        assert report.results[0].is_balanced is True
        assert report.results[0].difference == Decimal("0")

    def test_within_absolute_tolerance(self, checker: BalanceChecker) -> None:
        """차이가 절대 허용 오차(1000원) 이내이면 균형으로 판정."""
        # 자산 100500 != 부채 60000 + 자본 40000 = 100000, 차이 500 < 1000
        report = checker.check(
            total_assets={"2023": Decimal("100500")},
            total_liabilities={"2023": Decimal("60000")},
            total_equity={"2023": Decimal("40000")},
        )
        assert report.all_balanced is True
        assert report.results[0].difference == Decimal("500")

    def test_within_percentage_tolerance(self, checker: BalanceChecker) -> None:
        """차이가 비율 허용 오차(0.1%) 이내이면 균형으로 판정.

        절대 허용 오차를 매우 작게 설정하여 비율 허용 오차만 통과하도록 테스트.
        """
        # 자산 10,000,000, 부채+자본 = 9,995,000, 차이 5000
        # 비율 = 5000 / 10,000,000 = 0.0005 < 0.001 (0.1%)
        # 절대 허용 오차를 1로 설정하면 5000 > 1이므로 절대 기준은 미충족
        config = BalanceCheckConfig(tolerance=Decimal("1"), tolerance_pct=0.001)
        custom_checker = BalanceChecker(config=config)
        report = custom_checker.check(
            total_assets={"2023": Decimal("10000000")},
            total_liabilities={"2023": Decimal("6000000")},
            total_equity={"2023": Decimal("3995000")},
        )
        assert report.all_balanced is True
        assert report.results[0].is_balanced is True


class TestBalanceCheckerUnbalanced:
    """불균형인 경우 테스트."""

    def test_unbalanced_large_difference(self, checker: BalanceChecker) -> None:
        """차이가 허용 오차를 초과하면 is_balanced=False."""
        # 자산 100000, 부채+자본 = 80000, 차이 20000 >> 1000
        report = checker.check(
            total_assets={"2023": Decimal("100000")},
            total_liabilities={"2023": Decimal("50000")},
            total_equity={"2023": Decimal("30000")},
        )
        assert report.all_balanced is False
        assert report.results[0].is_balanced is False
        assert report.results[0].difference == Decimal("20000")
        assert len(report.warnings) >= 1


class TestBalanceCheckerNoneValues:
    """None 값 처리 테스트."""

    def test_none_values_skipped_with_warnings(self, checker: BalanceChecker) -> None:
        """None 값이 포함된 연도는 건너뛰고 경고를 기록한다."""
        report = checker.check(
            total_assets={"2023": None},
            total_liabilities={"2023": Decimal("60000")},
            total_equity={"2023": Decimal("40000")},
        )
        # 결과 없음 (건너뜀), all_balanced는 True (검증된 항목이 없으므로)
        assert len(report.results) == 0
        assert len(report.warnings) >= 1
        assert "누락" in report.warnings[0]


class TestBalanceCheckerMultipleYears:
    """다중 연도 테스트."""

    def test_multiple_years_mixed(self, checker: BalanceChecker) -> None:
        """여러 연도 중 일부만 균형인 경우 all_balanced=False."""
        report = checker.check(
            total_assets={
                "2022": Decimal("100000"),
                "2023": Decimal("200000"),
            },
            total_liabilities={
                "2022": Decimal("60000"),
                "2023": Decimal("100000"),
            },
            total_equity={
                "2022": Decimal("40000"),  # 균형
                "2023": Decimal("50000"),  # 불균형: 200000 - 150000 = 50000
            },
        )
        assert report.all_balanced is False
        # 2022년은 균형, 2023년은 불균형
        year_map = {r.year: r for r in report.results}
        assert year_map["2022"].is_balanced is True
        assert year_map["2023"].is_balanced is False


class TestBalanceCheckerCheckYear:
    """check_year 단일 연도 검증 테스트."""

    def test_check_year_single(self, checker: BalanceChecker) -> None:
        """check_year로 단일 연도를 직접 검증한다."""
        result = checker.check_year(
            "2023",
            Decimal("500000"),
            Decimal("300000"),
            Decimal("200000"),
        )
        assert isinstance(result, BalanceCheckResult)
        assert result.year == "2023"
        assert result.is_balanced is True
        assert result.difference == Decimal("0")


class TestBalanceCheckerCustomConfig:
    """커스텀 설정 테스트."""

    def test_custom_tolerance(self) -> None:
        """커스텀 tolerance 설정이 적용되는지 확인한다."""
        # tolerance=0으로 설정하면 미세한 차이도 불균형
        strict_config = BalanceCheckConfig(
            tolerance=Decimal("0"),
            tolerance_pct=0.0,
        )
        strict_checker = BalanceChecker(config=strict_config)

        result = strict_checker.check_year(
            "2023",
            Decimal("100001"),
            Decimal("60000"),
            Decimal("40000"),
        )
        assert result.is_balanced is False
        assert result.difference == Decimal("1")

    def test_config_property(self) -> None:
        """config 프로퍼티가 설정을 올바르게 반환한다."""
        config = BalanceCheckConfig(tolerance=Decimal("5000"), tolerance_pct=0.01)
        checker = BalanceChecker(config=config)
        assert checker.config.tolerance == Decimal("5000")
        assert checker.config.tolerance_pct == 0.01
