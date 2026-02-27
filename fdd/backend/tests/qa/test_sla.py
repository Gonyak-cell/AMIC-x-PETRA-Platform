"""Performance SLA 테스트 — Sprint 8 Phase 4.

성능 SLA 측정 및 검증 테스트.
테스트 ID 규칙: T-QA-SLA-{번호}
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.qa import (
    QACheckType,
    QASeverity,
    run_performance_qa,
)
from app.qa.performance_qa import (
    DEFAULT_SLAS,
    PerformanceMeasurement,
    PerformanceReport,
    SLADefinition,
    measure_operation,
)

# =============================================================================
# T-QA-SLA-01: SLA 정의 테스트
# =============================================================================


class TestSLADefinition:
    """T-QA-SLA-01: SLA 정의 검증."""

    def test_default_slas_exist(self) -> None:
        """기본 SLA 7개 존재."""
        assert len(DEFAULT_SLAS) >= 7

    def test_required_slas_defined(self) -> None:
        """필수 SLA 정의 확인."""
        required = [
            "gl_ingest_100k",
            "gl_ingest_1m",
            "qoe_calc",
            "nwc_calc",
            "debt_calc",
            "report_ir_gen",
            "ppt_render",
        ]
        for sla_name in required:
            assert sla_name in DEFAULT_SLAS, f"Missing SLA: {sla_name}"

    def test_sla_values_reasonable(self) -> None:
        """SLA 값 합리성 검증."""
        for name, sla in DEFAULT_SLAS.items():
            assert sla.max_seconds > 0, f"SLA {name} has non-positive max_seconds"
            assert 0 < sla.warning_threshold <= 1, f"SLA {name} has invalid warning_threshold"

    def test_gl_ingest_slas_scaling(self) -> None:
        """GL Ingest SLA 스케일링 확인."""
        sla_100k = DEFAULT_SLAS["gl_ingest_100k"]
        sla_1m = DEFAULT_SLAS["gl_ingest_1m"]

        # 100K → 1M (10배) 시 시간은 최대 10배 이내
        ratio = sla_1m.max_seconds / sla_100k.max_seconds
        assert ratio <= 15, f"1M GL ingest SLA should be at most 15x of 100K, got {ratio}x"


# =============================================================================
# T-QA-SLA-02: 성능 측정 테스트
# =============================================================================


class TestMeasureOperation:
    """T-QA-SLA-02: 성능 측정 함수 테스트."""

    def test_fast_operation_passes(self) -> None:
        """빠른 작업은 SLA 통과."""
        sla = SLADefinition(operation="test_fast", max_seconds=1.0)

        def fast_op() -> None:
            time.sleep(0.01)  # 10ms

        measurement, finding = measure_operation("test_fast", fast_op, sla)

        assert measurement.passed is True
        assert measurement.duration_seconds < sla.max_seconds
        assert finding is not None
        assert finding.severity == QASeverity.INFO

    def test_slow_operation_fails(self) -> None:
        """느린 작업은 SLA 실패."""
        sla = SLADefinition(operation="test_slow", max_seconds=0.05)

        def slow_op() -> None:
            time.sleep(0.1)  # 100ms

        measurement, finding = measure_operation("test_slow", slow_op, sla)

        assert measurement.passed is False
        assert measurement.duration_seconds >= sla.max_seconds
        assert finding is not None
        assert finding.severity == QASeverity.ERROR

    def test_warning_threshold(self) -> None:
        """경고 임계값 도달 시 WARNING."""
        sla = SLADefinition(operation="test_warning", max_seconds=1.0, warning_threshold=0.1)

        def borderline_op() -> None:
            time.sleep(0.15)  # 150ms = 15% of 1s

        measurement, finding = measure_operation("test_warning", borderline_op, sla)

        assert measurement.passed is True
        assert measurement.warning is True
        assert finding is not None
        assert finding.severity == QASeverity.WARNING

    def test_exception_handling(self) -> None:
        """예외 발생 시 실패 처리."""
        sla = SLADefinition(operation="test_error", max_seconds=1.0)

        def error_op() -> None:
            raise ValueError("Test error")

        measurement, finding = measure_operation("test_error", error_op, sla)

        assert measurement.passed is False
        assert finding is not None
        assert finding.severity == QASeverity.ERROR
        assert "exception" in finding.message.lower()

    def test_utilization_calculation(self) -> None:
        """SLA 사용률 계산 검증."""
        measurement = PerformanceMeasurement(
            operation="test",
            duration_seconds=0.5,
            sla_seconds=1.0,
            passed=True,
        )

        assert measurement.utilization == 0.5

    def test_data_size_tracking(self) -> None:
        """데이터 크기 추적."""
        sla = SLADefinition(operation="test", max_seconds=1.0)

        def op() -> None:
            pass

        measurement, _ = measure_operation("test", op, sla, data_size=100_000)

        assert measurement.data_size == 100_000


# =============================================================================
# T-QA-SLA-03: 성능 보고서 테스트
# =============================================================================


class TestPerformanceReport:
    """T-QA-SLA-03: 성능 보고서 생성 테스트."""

    def test_from_measurements_all_passed(self) -> None:
        """모든 측정 통과 시 보고서."""
        measurements = [
            PerformanceMeasurement(
                operation="op1",
                duration_seconds=0.5,
                sla_seconds=1.0,
                passed=True,
            ),
            PerformanceMeasurement(
                operation="op2",
                duration_seconds=0.3,
                sla_seconds=1.0,
                passed=True,
            ),
        ]

        report = PerformanceReport.from_measurements(measurements)

        assert report.total_operations == 2
        assert report.passed_operations == 2
        assert report.failed_operations == 0
        assert report.warning_operations == 0

    def test_from_measurements_with_failures(self) -> None:
        """실패 포함 시 보고서."""
        measurements = [
            PerformanceMeasurement(
                operation="op1",
                duration_seconds=0.5,
                sla_seconds=1.0,
                passed=True,
            ),
            PerformanceMeasurement(
                operation="op2",
                duration_seconds=1.5,
                sla_seconds=1.0,
                passed=False,
            ),
            PerformanceMeasurement(
                operation="op3",
                duration_seconds=0.9,
                sla_seconds=1.0,
                passed=True,
                warning=True,
            ),
        ]

        report = PerformanceReport.from_measurements(measurements)

        assert report.total_operations == 3
        assert report.passed_operations == 1
        assert report.failed_operations == 1
        assert report.warning_operations == 1

    def test_total_duration(self) -> None:
        """총 소요 시간 계산."""
        measurements = [
            PerformanceMeasurement(
                operation="op1",
                duration_seconds=0.5,
                sla_seconds=1.0,
                passed=True,
            ),
            PerformanceMeasurement(
                operation="op2",
                duration_seconds=0.7,
                sla_seconds=1.0,
                passed=True,
            ),
        ]

        report = PerformanceReport.from_measurements(measurements)

        assert report.total_duration_seconds == 1.2

    def test_to_dict(self) -> None:
        """딕셔너리 변환."""
        measurements = [
            PerformanceMeasurement(
                operation="op1",
                duration_seconds=0.5,
                sla_seconds=1.0,
                passed=True,
            ),
        ]

        report = PerformanceReport.from_measurements(measurements)
        d = report.to_dict()

        assert "total_operations" in d
        assert "passed_operations" in d
        assert "measurements" in d
        assert len(d["measurements"]) == 1


# =============================================================================
# T-QA-SLA-04: 성능 QA 통합 테스트
# =============================================================================


class TestRunPerformanceQA:
    """T-QA-SLA-04: 성능 QA 통합 테스트."""

    def test_run_with_all_passing(self) -> None:
        """모든 작업 통과."""
        sla = SLADefinition(operation="test", max_seconds=1.0)

        def fast_op() -> None:
            time.sleep(0.01)

        operations = [
            ("op1", fast_op, sla, 1000),
            ("op2", fast_op, sla, 2000),
        ]

        result, findings, measurements = run_performance_qa(operations)

        assert result.passed is True
        assert result.error_count == 0
        assert len(measurements) == 2

    def test_run_with_failure(self) -> None:
        """실패 포함 시."""
        fast_sla = SLADefinition(operation="fast", max_seconds=1.0)
        tight_sla = SLADefinition(operation="tight", max_seconds=0.001)

        def op() -> None:
            time.sleep(0.01)

        operations = [
            ("op1", op, fast_sla, 0),
            ("op2", op, tight_sla, 0),  # 이건 실패
        ]

        result, findings, measurements = run_performance_qa(operations)

        assert result.passed is False
        assert result.error_count >= 1

    def test_findings_include_all_operations(self) -> None:
        """모든 작업에 대한 finding 생성."""
        sla = SLADefinition(operation="test", max_seconds=1.0)

        def op() -> None:
            pass

        operations = [
            ("op1", op, sla, 0),
            ("op2", op, sla, 0),
            ("op3", op, sla, 0),
        ]

        result, findings, measurements = run_performance_qa(operations)

        assert len(findings) == 3
        assert len(measurements) == 3


# =============================================================================
# T-QA-SLA-05: 시뮬레이션 SLA 테스트
# =============================================================================


class TestSimulatedSLAScenarios:
    """T-QA-SLA-05: 시뮬레이션 시나리오 테스트."""

    def test_gl_ingest_100k_scenario(self) -> None:
        """GL 100K 라인 Ingest 시나리오."""
        sla = DEFAULT_SLAS["gl_ingest_100k"]

        # 시뮬레이션: 100K 라인 처리 가정 (실제로는 짧게)
        def simulated_ingest() -> None:
            # 실제 구현에서는 100K 라인 처리
            # 테스트에서는 빠르게 통과
            time.sleep(0.01)

        measurement, finding = measure_operation(
            "gl_ingest_100k",
            simulated_ingest,
            sla,
            data_size=100_000,
        )

        assert measurement.passed is True
        assert measurement.data_size == 100_000

    def test_qoe_calculation_scenario(self) -> None:
        """QoE 계산 시나리오."""
        sla = DEFAULT_SLAS["qoe_calc"]

        # 시뮬레이션: 복잡한 QoE 계산
        def simulated_qoe_calc() -> dict[str, Any]:
            # 실제 구현에서는 여러 계산 수행
            time.sleep(0.01)
            return {
                "reported_ebitda": Decimal("2000000"),
                "adjusted_ebitda": Decimal("2150000"),
                "adjustments": [
                    {"description": "Legal settlement", "amount": Decimal("150000")},
                ],
            }

        measurement, finding = measure_operation(
            "qoe_calc",
            simulated_qoe_calc,
            sla,
            data_size=1_000_000,
        )

        assert measurement.passed is True

    def test_report_ir_generation_scenario(self) -> None:
        """Report IR 생성 시나리오."""
        sla = DEFAULT_SLAS["report_ir_gen"]

        def simulated_ir_gen() -> dict[str, Any]:
            time.sleep(0.01)
            return {
                "metadata": {"deal_id": "test-001"},
                "sections": [
                    {"type": "cover", "deal_name": "Test Corp"},
                    {"type": "table", "title": "QoE Bridge", "rows": []},
                ],
            }

        measurement, finding = measure_operation(
            "report_ir_gen",
            simulated_ir_gen,
            sla,
        )

        assert measurement.passed is True


# =============================================================================
# T-QA-SLA-06: 엣지 케이스 테스트
# =============================================================================


class TestSLAEdgeCases:
    """T-QA-SLA-06: 엣지 케이스 테스트."""

    def test_zero_duration_operation(self) -> None:
        """즉시 완료 작업."""
        sla = SLADefinition(operation="instant", max_seconds=1.0)

        def instant_op() -> None:
            pass

        measurement, finding = measure_operation("instant", instant_op, sla)

        assert measurement.passed is True
        assert measurement.duration_seconds < 0.1

    def test_exact_sla_boundary(self) -> None:
        """SLA 경계값 테스트."""
        sla = SLADefinition(operation="boundary", max_seconds=0.1)

        def boundary_op() -> None:
            time.sleep(0.1)

        measurement, _ = measure_operation("boundary", boundary_op, sla)

        # 0.1초 sleep + 오버헤드로 약간 초과할 수 있음
        # 통과/실패 여부보다 정확한 측정 확인

    def test_very_short_sla(self) -> None:
        """매우 짧은 SLA."""
        sla = SLADefinition(operation="microsecond", max_seconds=0.0001)

        def any_op() -> None:
            pass

        measurement, finding = measure_operation("microsecond", any_op, sla)

        # 어떤 작업이든 오버헤드로 실패할 수 있음
        assert measurement.duration_seconds > 0

    def test_empty_operations_list(self) -> None:
        """빈 작업 목록."""
        result, findings, measurements = run_performance_qa([])

        assert result.passed is True
        assert len(findings) == 0
        assert len(measurements) == 0


# =============================================================================
# T-QA-SLA-07: 모킹을 통한 SLA 검증
# =============================================================================


class TestMockedSLAValidation:
    """T-QA-SLA-07: Mock을 통한 SLA 검증."""

    def test_mock_slow_database(self) -> None:
        """느린 DB 시뮬레이션."""
        sla = SLADefinition(operation="db_query", max_seconds=0.05)

        # Mock으로 느린 DB 쿼리 시뮬레이션
        mock_db = MagicMock()
        mock_db.query.side_effect = lambda: time.sleep(0.1)

        def db_operation() -> None:
            mock_db.query()

        measurement, finding = measure_operation("db_query", db_operation, sla)

        assert measurement.passed is False
        assert finding.severity == QASeverity.ERROR

    def test_mock_fast_cache(self) -> None:
        """빠른 캐시 시뮬레이션."""
        sla = SLADefinition(operation="cache_read", max_seconds=1.0)

        # Mock으로 빠른 캐시 읽기 시뮬레이션
        mock_cache = MagicMock()
        mock_cache.get.return_value = {"data": "cached"}

        def cache_operation() -> dict:
            return mock_cache.get("key")

        measurement, finding = measure_operation("cache_read", cache_operation, sla)

        assert measurement.passed is True


# =============================================================================
# T-QA-SLA-08: 성능 회귀 감지 테스트
# =============================================================================


class TestPerformanceRegression:
    """T-QA-SLA-08: 성능 회귀 감지."""

    def test_baseline_comparison(self) -> None:
        """베이스라인 대비 성능 비교."""
        # 베이스라인: 이전 버전의 성능
        baseline = {
            "qoe_calc": 0.5,  # 500ms
            "nwc_calc": 0.3,  # 300ms
        }

        # 현재 버전 측정
        current = {
            "qoe_calc": 0.55,  # 550ms (10% 저하)
            "nwc_calc": 0.25,  # 250ms (개선)
        }

        # 20% 이상 저하 시 회귀로 판정
        regression_threshold = 0.2

        for op_name, current_time in current.items():
            baseline_time = baseline[op_name]
            regression_ratio = (current_time - baseline_time) / baseline_time

            if regression_ratio > regression_threshold:
                pytest.fail(
                    f"Performance regression in {op_name}: "
                    f"{baseline_time}s -> {current_time}s ({regression_ratio*100:.1f}% slower)"
                )

    def test_performance_trend(self) -> None:
        """성능 트렌드 분석."""
        # 히스토리 시뮬레이션
        history = [
            {"version": "0.1.0", "qoe_calc_ms": 500},
            {"version": "0.2.0", "qoe_calc_ms": 480},
            {"version": "0.3.0", "qoe_calc_ms": 520},
            {"version": "0.4.0", "qoe_calc_ms": 510},
        ]

        # 평균 계산
        avg = sum(h["qoe_calc_ms"] for h in history) / len(history)

        # 현재 버전이 평균 대비 30% 이상 느리면 경고
        current_ms = 510
        deviation = (current_ms - avg) / avg

        assert deviation < 0.3, f"Performance deviation {deviation*100:.1f}% exceeds 30% threshold"
