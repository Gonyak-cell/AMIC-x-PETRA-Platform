"""Financial Engine -- Consistency Checker (T-F11).

다기간 재무 데이터 일관성 검증기: YoY 대규모 변동, 부호 반전,
이익잉여금 연속성, 데이터 누락 등의 이상 항목을 탐지합니다.

연도별 재무 데이터를 입력받아 연속 연도 쌍을 비교하고,
설정된 기준을 초과하는 변동이나 논리적 모순을 ConsistencyAnomaly로 보고합니다.

사용 예시:
    from decimal import Decimal
    from src.financial_engine.validator.consistency_checker import (
        ConsistencyChecker,
        ConsistencyConfig,
    )

    checker = ConsistencyChecker()
    data = {
        "매출액": {"2022": Decimal("100"), "2023": Decimal("200")},
        "당기순이익": {"2022": Decimal("10"), "2023": Decimal("15")},
    }
    report = checker.check(data)
    assert report.is_consistent is True or len(report.anomalies) > 0

> 마지막 수정: 2026-02-09 16:17:05
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum, unique

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enum & 데이터 클래스
# ---------------------------------------------------------------------------


@unique
class AnomalyType(str, Enum):
    """이상 항목 유형."""

    LARGE_CHANGE = "large_change"
    SIGN_REVERSAL = "sign_reversal"
    RETAINED_EARNINGS_MISMATCH = "re_mismatch"
    MISSING_DATA = "missing_data"


@dataclass(frozen=True)
class ConsistencyAnomaly:
    """단일 이상 항목.

    Attributes:
        anomaly_type: 이상 항목 유형.
        account: 계정명 또는 코드.
        year: 해당 연도.
        description: 상세 설명 (한글).
        severity: 심각도 ("warning" | "error").
    """

    anomaly_type: AnomalyType
    account: str
    year: str
    description: str
    severity: str


@dataclass(frozen=True)
class ConsistencyConfig:
    """일관성 검증 설정.

    Attributes:
        large_change_threshold: YoY 변동률 기준 (기본 0.5 = 50%).
        check_sign_reversal: 부호 반전 검사 여부.
        check_retained_earnings: 이익잉여금 연속성 검사 여부.
        check_missing_data: 데이터 누락 검사 여부.
    """

    large_change_threshold: float = 0.5
    check_sign_reversal: bool = True
    check_retained_earnings: bool = True
    check_missing_data: bool = True


@dataclass
class ConsistencyReport:
    """일관성 검증 보고서.

    Attributes:
        anomalies: 탐지된 이상 항목 목록.
        is_consistent: 이상 항목이 없으면 True.
        warnings: 경고 메시지 목록.
    """

    anomalies: list[ConsistencyAnomaly] = field(default_factory=list)
    is_consistent: bool = True
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ConsistencyChecker 클래스
# ---------------------------------------------------------------------------


class ConsistencyChecker:
    """다기간 재무 데이터 일관성 검증기.

    연도별 재무 데이터를 입력받아 연속 연도 쌍을 비교하고,
    대규모 변동, 부호 반전, 이익잉여금 불일치, 데이터 누락 등의
    이상 항목을 탐지합니다.

    Args:
        config: 일관성 검증 설정. None이면 기본 설정을 사용합니다.

    Examples:
        >>> from decimal import Decimal
        >>> checker = ConsistencyChecker()
        >>> data = {"매출액": {"2022": Decimal("100"), "2023": Decimal("200")}}
        >>> report = checker.check(data)
        >>> len(report.anomalies) >= 1
        True
    """

    def __init__(self, config: ConsistencyConfig | None = None) -> None:
        self._config = config or ConsistencyConfig()

    @property
    def config(self) -> ConsistencyConfig:
        """현재 설정을 반환합니다."""
        return self._config

    def check(
        self,
        data: dict[str, dict[str, Decimal | None]],
    ) -> ConsistencyReport:
        """전체 데이터에 대해 일관성 검증을 수행합니다.

        Args:
            data: {계정명: {연도: 값}} 형태의 재무 데이터.
                  예: {"매출액": {"2022": Decimal("100"), "2023": Decimal("200")}}

        연도를 정렬한 뒤 연속 쌍을 비교하여:
        1. large_change 검사: |curr - prev| / |prev| > threshold
        2. sign_reversal 검사: prev > 0 and curr < 0 (또는 반대)
        3. missing_data 검사: 연도가 있지만 값이 None

        severity 규칙:
        - LARGE_CHANGE: "warning"
        - SIGN_REVERSAL: "warning"
        - MISSING_DATA: "warning"
        - RETAINED_EARNINGS_MISMATCH: "error"

        Returns:
            ConsistencyReport: 탐지된 모든 이상 항목을 포함한 보고서.
        """
        anomalies: list[ConsistencyAnomaly] = []
        warnings: list[str] = []

        for account, year_data in data.items():
            years = sorted(year_data.keys())

            # --- missing_data 검사 ---
            if self._config.check_missing_data:
                for year in years:
                    if year_data[year] is None:
                        anomaly = ConsistencyAnomaly(
                            anomaly_type=AnomalyType.MISSING_DATA,
                            account=account,
                            year=year,
                            description=f"'{account}' 계정의 {year}년 데이터가 누락되었습니다.",
                            severity="warning",
                        )
                        anomalies.append(anomaly)
                        msg = f"MISSING_DATA: {account} {year}"
                        warnings.append(msg)
                        logger.warning(msg)

            # --- 연속 연도 쌍 비교 ---
            for i in range(len(years) - 1):
                prev_year = years[i]
                curr_year = years[i + 1]
                prev_val = year_data[prev_year]
                curr_val = year_data[curr_year]

                # large_change 검사: prev가 0이거나 None이면 건너뜀
                if (
                    prev_val is not None
                    and curr_val is not None
                    and prev_val != Decimal("0")
                ):
                    abs_prev = abs(prev_val)
                    change_ratio = float(abs(curr_val - prev_val) / abs_prev)
                    if change_ratio > self._config.large_change_threshold:
                        pct = change_ratio * 100
                        anomaly = ConsistencyAnomaly(
                            anomaly_type=AnomalyType.LARGE_CHANGE,
                            account=account,
                            year=curr_year,
                            description=(
                                f"'{account}' 계정이 {prev_year}→{curr_year} 기간 동안 "
                                f"{pct:.1f}% 변동하였습니다 "
                                f"({prev_val} → {curr_val})."
                            ),
                            severity="warning",
                        )
                        anomalies.append(anomaly)
                        msg = f"LARGE_CHANGE: {account} {curr_year} ({pct:.1f}%)"
                        warnings.append(msg)
                        logger.warning(msg)

                # sign_reversal 검사: 둘 다 non-zero, non-None일 때만
                if self._config.check_sign_reversal:
                    if (
                        prev_val is not None
                        and curr_val is not None
                        and prev_val != Decimal("0")
                        and curr_val != Decimal("0")
                    ):
                        prev_positive = prev_val > Decimal("0")
                        curr_positive = curr_val > Decimal("0")
                        if prev_positive != curr_positive:
                            direction = "양→음" if prev_positive else "음→양"
                            anomaly = ConsistencyAnomaly(
                                anomaly_type=AnomalyType.SIGN_REVERSAL,
                                account=account,
                                year=curr_year,
                                description=(
                                    f"'{account}' 계정이 {prev_year}→{curr_year} 기간 동안 "
                                    f"부호가 반전되었습니다 ({direction}: {prev_val} → {curr_val})."
                                ),
                                severity="warning",
                            )
                            anomalies.append(anomaly)
                            msg = f"SIGN_REVERSAL: {account} {curr_year} ({direction})"
                            warnings.append(msg)
                            logger.warning(msg)

        # --- 이익잉여금 연속성 검사 ---
        if (
            self._config.check_retained_earnings
            and "이익잉여금" in data
            and "당기순이익" in data
        ):
            re_anomalies = self.check_retained_earnings(
                retained_earnings=data["이익잉여금"],
                net_income=data["당기순이익"],
                dividends=data.get("배당금"),
            )
            anomalies.extend(re_anomalies)
            for a in re_anomalies:
                msg = f"RE_MISMATCH: {a.account} {a.year}"
                warnings.append(msg)
                logger.warning(msg)

        is_consistent = len(anomalies) == 0

        return ConsistencyReport(
            anomalies=anomalies,
            is_consistent=is_consistent,
            warnings=warnings,
        )

    def check_retained_earnings(
        self,
        retained_earnings: dict[str, Decimal | None],
        net_income: dict[str, Decimal | None],
        dividends: dict[str, Decimal | None] | None = None,
    ) -> list[ConsistencyAnomaly]:
        """이익잉여금 연속성을 검증합니다: RE(t) ≈ RE(t-1) + NI(t) - Div(t).

        기타포괄손익 등으로 인해 정확히 일치하지 않을 수 있으므로
        5% 허용 오차를 적용합니다.

        Args:
            retained_earnings: 연도별 이익잉여금.
            net_income: 연도별 당기순이익.
            dividends: 연도별 배당금 (None이면 0으로 처리).

        Returns:
            RETAINED_EARNINGS_MISMATCH 유형의 이상 항목 목록.
        """
        anomalies: list[ConsistencyAnomaly] = []
        dividends = dividends or {}

        years = sorted(retained_earnings.keys())

        for i in range(len(years) - 1):
            prev_year = years[i]
            curr_year = years[i + 1]

            re_prev = retained_earnings.get(prev_year)
            re_curr = retained_earnings.get(curr_year)
            ni_curr = net_income.get(curr_year)
            div_curr = dividends.get(curr_year)

            # 필수 값 누락 시 건너뜀
            if re_prev is None or re_curr is None or ni_curr is None:
                continue

            div_val = div_curr if div_curr is not None else Decimal("0")
            expected = re_prev + ni_curr - div_val
            diff = abs(re_curr - expected)

            # tolerance: max(|RE(t)|, 1) * 0.05
            tolerance = max(abs(re_curr), Decimal("1")) * Decimal("0.05")

            if diff > tolerance:
                anomaly = ConsistencyAnomaly(
                    anomaly_type=AnomalyType.RETAINED_EARNINGS_MISMATCH,
                    account="이익잉여금",
                    year=curr_year,
                    description=(
                        f"이익잉여금 연속성 불일치 ({curr_year}): "
                        f"실제 RE={re_curr}, 예상 RE={expected} "
                        f"(RE(t-1)={re_prev} + NI={ni_curr} - Div={div_val}), "
                        f"차이={diff}."
                    ),
                    severity="error",
                )
                anomalies.append(anomaly)

        return anomalies
