"""Performance QA 테스트 — FDD-1605.

테스트 ID 규칙: T-QA-PERF-{번호}
"""

from __future__ import annotations

import time

import pytest

from app.qa import (
    DEFAULT_SLAS,
    QACheckType,
    QASeverity,
    PerformanceMeasurement,
    PerformanceReport,
    SLADefinition,
    measure_operation,
    run_performance_qa,
)


class TestSLADefinition:
    """T-QA-PERF-01: SLA 정의 테스트."""

    def test_default_slas_exist(self) -> None:
        """기본 SLA 정의 존재."""
        assert "qoe_calc" in DEFAULT_SLAS
        assert "nwc_calc" in DEFAULT_SLAS
        assert "debt_calc" in DEFAULT_SLAS
        assert "report_ir_gen" in DEFAULT_SLAS

    def test_sla_properties(self) -> None:
        """SLA 속성 확인."""
        sla = SLADefinition(
            operation="Test Op",
            max_seconds=30.0,
            gl_line_threshold=100_000,
            warning_threshold=0.8,
        )
        assert sla.operation == "Test Op"
        assert sla.max_seconds == 30.0
        assert sla.warning_threshold == 0.8


class TestMeasureOperation:
    """T-QA-PERF-02: 작업 측정 테스트."""

    def test_fast_operation_pass(self) -> None:
        """빠른 작업 통과."""
        sla = SLADefinition("Fast Op", max_seconds=1.0)

        def fast_func() -> None:
            pass

        measurement, finding = measure_operation("fast", fast_func, sla)

        assert measurement.passed is True
        assert measurement.duration_seconds < 1.0
        assert finding.severity == QASeverity.INFO

    def test_slow_operation_fail(self) -> None:
        """느린 작업 실패."""
        sla = SLADefinition("Slow Op", max_seconds=0.01)

        def slow_func() -> None:
            time.sleep(0.05)

        measurement, finding = measure_operation("slow", slow_func, sla)

        assert measurement.passed is False
        assert finding.severity == QASeverity.ERROR
        assert "SLA exceeded" in finding.message

    def test_warning_threshold(self) -> None:
        """경고 임계값."""
        sla = SLADefinition("Warn Op", max_seconds=0.1, warning_threshold=0.5)

        def medium_func() -> None:
            time.sleep(0.06)  # 60% of 0.1

        measurement, finding = measure_operation("medium", medium_func, sla)

        # 0.06 > 0.05 (50% of 0.1) 이므로 WARNING
        assert measurement.passed is True
        assert measurement.warning is True
        assert finding.severity == QASeverity.WARNING

    def test_exception_handling(self) -> None:
        """예외 발생 시 처리."""
        sla = SLADefinition("Error Op", max_seconds=1.0)

        def error_func() -> None:
            raise ValueError("Test error")

        measurement, finding = measure_operation("error", error_func, sla)

        assert measurement.passed is False
        assert "exception" in finding.message.lower()

    def test_data_size_tracking(self) -> None:
        """데이터 크기 추적."""
        sla = SLADefinition("Size Op", max_seconds=1.0)
        measurement, _ = measure_operation("test", lambda: None, sla, data_size=100_000)

        assert measurement.data_size == 100_000


class TestPerformanceMeasurement:
    """T-QA-PERF-03: 측정 결과 테스트."""

    def test_utilization_calculation(self) -> None:
        """사용률 계산."""
        m = PerformanceMeasurement(
            operation="test",
            duration_seconds=30.0,
            sla_seconds=100.0,
            passed=True,
        )
        assert m.utilization == 0.3

    def test_utilization_zero_sla(self) -> None:
        """SLA가 0일 때 사용률."""
        m = PerformanceMeasurement(
            operation="test",
            duration_seconds=10.0,
            sla_seconds=0.0,
            passed=False,
        )
        assert m.utilization == 0.0

    def test_to_dict(self) -> None:
        """딕셔너리 변환."""
        m = PerformanceMeasurement(
            operation="test",
            duration_seconds=5.123456,
            sla_seconds=10.0,
            passed=True,
            data_size=50000,
        )
        d = m.to_dict()

        assert d["operation"] == "test"
        assert d["duration_seconds"] == 5.123
        assert d["utilization"] == 0.512
        assert d["data_size"] == 50000


class TestRunPerformanceQA:
    """T-QA-PERF-04: run_performance_qa 통합 테스트."""

    def test_multiple_operations(self) -> None:
        """여러 작업 측정."""
        sla_fast = SLADefinition("Fast", max_seconds=1.0)
        sla_slow = SLADefinition("Slow", max_seconds=0.01)

        operations = [
            ("fast_op", lambda: None, sla_fast, 0),
            ("slow_op", lambda: time.sleep(0.02), sla_slow, 0),
        ]

        result, findings, measurements = run_performance_qa(operations)

        assert len(measurements) == 2
        assert result.error_count >= 1  # slow_op 실패

    def test_empty_operations(self) -> None:
        """빈 작업 목록."""
        result, findings, measurements = run_performance_qa([])

        assert result.passed is True
        assert len(measurements) == 0


class TestPerformanceReport:
    """T-QA-PERF-05: 성능 리포트 테스트."""

    def test_from_measurements(self) -> None:
        """측정 결과에서 리포트 생성."""
        measurements = [
            PerformanceMeasurement("op1", 5.0, 10.0, True, warning=False),
            PerformanceMeasurement("op2", 8.5, 10.0, True, warning=True),
            PerformanceMeasurement("op3", 15.0, 10.0, False),
        ]

        report = PerformanceReport.from_measurements(measurements)

        assert report.total_operations == 3
        assert report.passed_operations == 1  # op1 (passed, no warning)
        assert report.warning_operations == 1  # op2
        assert report.failed_operations == 1  # op3
        assert report.total_duration_seconds == 28.5

    def test_to_dict(self) -> None:
        """리포트 딕셔너리 변환."""
        m = PerformanceMeasurement("op", 5.0, 10.0, True)
        report = PerformanceReport.from_measurements([m])
        d = report.to_dict()

        assert "total_operations" in d
        assert "measurements" in d
        assert len(d["measurements"]) == 1
