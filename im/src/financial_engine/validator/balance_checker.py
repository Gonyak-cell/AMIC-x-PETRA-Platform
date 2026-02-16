"""Financial Engine -- Balance Checker (T-F10).

재무상태표 균형 검증기: 자산 = 부채 + 자본 등식을 검증합니다.

각 연도의 총자산, 총부채, 총자본 데이터를 받아 균형 등식이 성립하는지 확인하며,
절대 허용 오차(tolerance)와 비율 허용 오차(tolerance_pct) 두 가지 기준을 지원합니다.

사용 예시:
    from decimal import Decimal
    from src.financial_engine.validator.balance_checker import (
        BalanceChecker,
        BalanceCheckConfig,
    )

    checker = BalanceChecker()
    report = checker.check(
        total_assets={"2022": Decimal("50000"), "2023": Decimal("60000")},
        total_liabilities={"2022": Decimal("30000"), "2023": Decimal("35000")},
        total_equity={"2022": Decimal("20000"), "2023": Decimal("25000")},
    )
    assert report.all_balanced is True

> 마지막 수정: 2026-02-09 16:09:11
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 설정 & 결과 데이터 클래스
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BalanceCheckConfig:
    """균형 검증 설정.

    Attributes:
        tolerance: 절대 허용 오차 (원 단위). 기본값 1,000원.
        tolerance_pct: 비율 허용 오차. 기본값 0.001 (0.1%).
    """

    tolerance: Decimal = Decimal("1000")
    tolerance_pct: float = 0.001


@dataclass(frozen=True)
class BalanceCheckResult:
    """단일 연도의 균형 검증 결과.

    Attributes:
        year: 검증 대상 연도.
        total_assets: 총자산.
        total_liabilities: 총부채.
        total_equity: 총자본.
        difference: 차이 = 총자산 - (총부채 + 총자본).
        is_balanced: 균형 여부 (허용 오차 이내이면 True).
    """

    year: str
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    difference: Decimal
    is_balanced: bool


@dataclass
class BalanceCheckReport:
    """전체 연도 균형 검증 보고서.

    Attributes:
        results: 연도별 검증 결과 목록.
        all_balanced: 모든 검증 연도가 균형인 경우 True.
        warnings: 경고 메시지 목록 (값 누락, 불균형 상세 등).
    """

    results: list[BalanceCheckResult] = field(default_factory=list)
    all_balanced: bool = True
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# BalanceChecker 클래스
# ---------------------------------------------------------------------------


class BalanceChecker:
    """재무상태표 균형 검증기.

    자산 = 부채 + 자본 등식을 기반으로 각 연도의 재무상태표 데이터를
    검증합니다. 절대 허용 오차와 비율 허용 오차 중 하나라도 충족하면
    해당 연도는 '균형'으로 판정합니다.

    Args:
        config: 균형 검증 설정. None이면 기본 설정을 사용합니다.

    Examples:
        >>> from decimal import Decimal
        >>> checker = BalanceChecker()
        >>> result = checker.check_year("2023", Decimal("100000"), Decimal("60000"), Decimal("40000"))
        >>> result.is_balanced
        True
    """

    def __init__(self, config: BalanceCheckConfig | None = None) -> None:
        self._config = config or BalanceCheckConfig()

    @property
    def config(self) -> BalanceCheckConfig:
        """현재 설정을 반환합니다."""
        return self._config

    def check(
        self,
        total_assets: dict[str, Decimal | None],
        total_liabilities: dict[str, Decimal | None],
        total_equity: dict[str, Decimal | None],
    ) -> BalanceCheckReport:
        """전체 연도에 대해 재무상태표 균형을 검증합니다.

        ``total_assets``에 포함된 모든 연도를 순회하며 균형 등식을 확인합니다.
        특정 연도에서 값이 ``None``인 항목이 있으면 해당 연도를 건너뛰고
        경고를 기록합니다.

        Args:
            total_assets: 연도별 총자산 ``{연도: Decimal | None}``.
            total_liabilities: 연도별 총부채 ``{연도: Decimal | None}``.
            total_equity: 연도별 총자본 ``{연도: Decimal | None}``.

        Returns:
            BalanceCheckReport: 전체 검증 보고서.
        """
        results: list[BalanceCheckResult] = []
        warnings: list[str] = []
        all_balanced = True

        # 모든 연도를 합집합으로 수집하되, 정렬하여 일관된 순서로 처리
        all_years = sorted(
            set(total_assets.keys())
            | set(total_liabilities.keys())
            | set(total_equity.keys())
        )

        for year in all_years:
            assets = total_assets.get(year)
            liabilities = total_liabilities.get(year)
            equity = total_equity.get(year)

            # None 값이 있는 연도는 건너뛰기
            missing_fields: list[str] = []
            if assets is None:
                missing_fields.append("총자산")
            if liabilities is None:
                missing_fields.append("총부채")
            if equity is None:
                missing_fields.append("총자본")

            if missing_fields:
                msg = (
                    f"{year}년: 값 누락으로 균형 검증을 건너뜁니다 "
                    f"(누락 항목: {', '.join(missing_fields)})"
                )
                warnings.append(msg)
                logger.warning(msg)
                continue

            # 타입 단언: 위에서 None 검사를 통과했으므로 Decimal 확정
            assert assets is not None  # noqa: S101
            assert liabilities is not None  # noqa: S101
            assert equity is not None  # noqa: S101

            result = self.check_year(year, assets, liabilities, equity)
            results.append(result)

            if not result.is_balanced:
                all_balanced = False
                msg = (
                    f"{year}년: 재무상태표 불균형 - "
                    f"자산({assets:,}) != 부채({liabilities:,}) + 자본({equity:,}), "
                    f"차이: {result.difference:,}"
                )
                warnings.append(msg)
                logger.warning(msg)

        return BalanceCheckReport(
            results=results,
            all_balanced=all_balanced,
            warnings=warnings,
        )

    def check_year(
        self,
        year: str,
        assets: Decimal,
        liabilities: Decimal,
        equity: Decimal,
    ) -> BalanceCheckResult:
        """단일 연도의 재무상태표 균형을 검증합니다.

        균형 등식: 자산 = 부채 + 자본
        차이 = 자산 - (부채 + 자본)

        다음 조건 중 하나라도 충족하면 '균형'으로 판정합니다:
        - ``abs(차이) <= tolerance`` (절대 허용 오차)
        - ``abs(차이) / max(abs(자산), 1) <= tolerance_pct`` (비율 허용 오차)

        Args:
            year: 검증 대상 연도 문자열.
            assets: 총자산.
            liabilities: 총부채.
            equity: 총자본.

        Returns:
            BalanceCheckResult: 해당 연도의 검증 결과.

        Examples:
            >>> from decimal import Decimal
            >>> checker = BalanceChecker()
            >>> r = checker.check_year("2023", Decimal("100000"), Decimal("60000"), Decimal("40000"))
            >>> r.is_balanced
            True
            >>> r.difference
            Decimal('0')
        """
        difference = assets - (liabilities + equity)
        abs_diff = abs(difference)

        # 기준 1: 절대 허용 오차
        within_absolute = abs_diff <= self._config.tolerance

        # 기준 2: 비율 허용 오차 (분모는 max(|자산|, 1)로 0 나누기 방지)
        denominator = max(abs(assets), Decimal("1"))
        ratio = float(abs_diff / denominator)
        within_percentage = ratio <= self._config.tolerance_pct

        is_balanced = within_absolute or within_percentage

        return BalanceCheckResult(
            year=year,
            total_assets=assets,
            total_liabilities=liabilities,
            total_equity=equity,
            difference=difference,
            is_balanced=is_balanced,
        )
