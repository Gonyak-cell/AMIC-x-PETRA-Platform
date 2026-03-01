# -*- coding: utf-8 -*-
"""ConsistencyChecker 단위 테스트.

다기간 재무 데이터 일관성 검증기의 정확성을 검증합니다.
대규모 변동, 부호 반전, 이익잉여금 연속성, 데이터 누락, 설정 커스터마이징 등을 테스트합니다.

> 마지막 수정: 2026-02-09 16:29:23
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.financial_engine.validator.consistency_checker import (
    AnomalyType,
    ConsistencyChecker,
    ConsistencyConfig,
)


# ---------------------------------------------------------------------------
# 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
def checker() -> ConsistencyChecker:
    """기본 설정의 ConsistencyChecker를 반환한다."""
    return ConsistencyChecker()


# ---------------------------------------------------------------------------
# 테스트: 대규모 변동 탐지 (LARGE_CHANGE)
# ---------------------------------------------------------------------------


class TestLargeChangeDetection:
    """YoY 대규모 변동 탐지 테스트."""

    def test_large_change_detected(self, checker: ConsistencyChecker) -> None:
        """100→200 (100% 변동)은 50% 임계값을 초과하여 탐지된다."""
        data = {
            "매출액": {
                "2022": Decimal("100"),
                "2023": Decimal("200"),
            },
        }
        report = checker.check(data)
        large_changes = [
            a for a in report.anomalies if a.anomaly_type == AnomalyType.LARGE_CHANGE
        ]
        assert len(large_changes) >= 1
        assert large_changes[0].account == "매출액"
        assert large_changes[0].year == "2023"
        assert large_changes[0].severity == "warning"

    def test_no_anomaly_on_small_change(self, checker: ConsistencyChecker) -> None:
        """100→140 (40% 변동)은 50% 임계값 미만이므로 탐지되지 않는다."""
        data = {
            "매출액": {
                "2022": Decimal("100"),
                "2023": Decimal("140"),
            },
        }
        report = checker.check(data)
        large_changes = [
            a for a in report.anomalies if a.anomaly_type == AnomalyType.LARGE_CHANGE
        ]
        assert len(large_changes) == 0


# ---------------------------------------------------------------------------
# 테스트: 부호 반전 탐지 (SIGN_REVERSAL)
# ---------------------------------------------------------------------------


class TestSignReversalDetection:
    """부호 반전 탐지 테스트."""

    def test_sign_reversal_detected(self, checker: ConsistencyChecker) -> None:
        """양수→음수 전환이 탐지된다."""
        data = {
            "영업이익": {
                "2022": Decimal("10"),
                "2023": Decimal("-5"),
            },
        }
        report = checker.check(data)
        sign_reversals = [
            a for a in report.anomalies if a.anomaly_type == AnomalyType.SIGN_REVERSAL
        ]
        assert len(sign_reversals) >= 1
        assert sign_reversals[0].account == "영업이익"
        assert sign_reversals[0].severity == "warning"

    def test_no_sign_reversal_same_sign(self, checker: ConsistencyChecker) -> None:
        """같은 부호일 때는 부호 반전이 탐지되지 않는다."""
        data = {
            "영업이익": {
                "2022": Decimal("100"),
                "2023": Decimal("50"),
            },
        }
        report = checker.check(data)
        sign_reversals = [
            a for a in report.anomalies if a.anomaly_type == AnomalyType.SIGN_REVERSAL
        ]
        assert len(sign_reversals) == 0


# ---------------------------------------------------------------------------
# 테스트: 데이터 누락 탐지 (MISSING_DATA)
# ---------------------------------------------------------------------------


class TestMissingDataDetection:
    """데이터 누락 탐지 테스트."""

    def test_missing_data_detected(self, checker: ConsistencyChecker) -> None:
        """None 값이 포함되면 MISSING_DATA 이상 항목이 탐지된다."""
        data = {
            "매출액": {
                "2022": Decimal("100"),
                "2023": None,
            },
        }
        report = checker.check(data)
        missing = [
            a for a in report.anomalies if a.anomaly_type == AnomalyType.MISSING_DATA
        ]
        assert len(missing) >= 1
        assert missing[0].year == "2023"
        assert missing[0].severity == "warning"


# ---------------------------------------------------------------------------
# 테스트: 이익잉여금 연속성 (RETAINED_EARNINGS_MISMATCH)
# ---------------------------------------------------------------------------


class TestRetainedEarningsCheck:
    """이익잉여금 연속성 검증 테스트."""

    def test_retained_earnings_consistent(self, checker: ConsistencyChecker) -> None:
        """RE(t)=RE(t-1)+NI-Div 등식이 성립하면 이상 없음."""
        data = {
            "이익잉여금": {
                "2022": Decimal("1000"),
                "2023": Decimal("1100"),
            },
            "당기순이익": {
                "2022": Decimal("200"),
                "2023": Decimal("150"),
            },
            "배당금": {
                "2022": Decimal("0"),
                "2023": Decimal("50"),
            },
        }
        # RE(2023) = RE(2022) + NI(2023) - Div(2023) = 1000 + 150 - 50 = 1100 ✓
        report = checker.check(data)
        re_mismatches = [
            a
            for a in report.anomalies
            if a.anomaly_type == AnomalyType.RETAINED_EARNINGS_MISMATCH
        ]
        assert len(re_mismatches) == 0

    def test_retained_earnings_mismatch_detected(
        self, checker: ConsistencyChecker
    ) -> None:
        """RE(t) != RE(t-1)+NI-Div이면 불일치가 탐지된다."""
        data = {
            "이익잉여금": {
                "2022": Decimal("1000"),
                "2023": Decimal("1500"),  # 예상 1100이므로 불일치
            },
            "당기순이익": {
                "2022": Decimal("200"),
                "2023": Decimal("100"),
            },
        }
        # RE(2023) 예상 = 1000 + 100 - 0 = 1100, 실제 = 1500, 차이 = 400
        report = checker.check(data)
        re_mismatches = [
            a
            for a in report.anomalies
            if a.anomaly_type == AnomalyType.RETAINED_EARNINGS_MISMATCH
        ]
        assert len(re_mismatches) >= 1
        assert re_mismatches[0].severity == "error"


# ---------------------------------------------------------------------------
# 테스트: 커스텀 설정
# ---------------------------------------------------------------------------


class TestConsistencyCustomConfig:
    """커스텀 설정 테스트."""

    def test_custom_threshold(self) -> None:
        """large_change_threshold를 높이면 큰 변동도 탐지되지 않는다."""
        config = ConsistencyConfig(large_change_threshold=2.0)  # 200%
        checker = ConsistencyChecker(config=config)
        data = {
            "매출액": {
                "2022": Decimal("100"),
                "2023": Decimal("200"),  # 100% 변동 < 200% 임계값
            },
        }
        report = checker.check(data)
        large_changes = [
            a for a in report.anomalies if a.anomaly_type == AnomalyType.LARGE_CHANGE
        ]
        assert len(large_changes) == 0

    def test_config_property(self) -> None:
        """config 프로퍼티가 설정을 올바르게 반환한다."""
        config = ConsistencyConfig(large_change_threshold=0.3)
        checker = ConsistencyChecker(config=config)
        assert checker.config.large_change_threshold == 0.3


# ---------------------------------------------------------------------------
# 테스트: 전체 일관성
# ---------------------------------------------------------------------------


class TestOverallConsistency:
    """전체 일관성 판정 테스트."""

    def test_stable_data_is_consistent(self, checker: ConsistencyChecker) -> None:
        """안정적인 데이터는 is_consistent=True."""
        data = {
            "매출액": {
                "2022": Decimal("100"),
                "2023": Decimal("110"),  # 10% 변동
            },
        }
        report = checker.check(data)
        assert report.is_consistent is True
        assert len(report.anomalies) == 0

    def test_empty_data_handling(self, checker: ConsistencyChecker) -> None:
        """빈 데이터를 입력하면 이상 없이 처리된다."""
        report = checker.check({})
        assert report.is_consistent is True
        assert len(report.anomalies) == 0
        assert len(report.warnings) == 0
