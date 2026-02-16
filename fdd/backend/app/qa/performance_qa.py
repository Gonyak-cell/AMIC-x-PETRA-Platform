"""Performance QA — SLA 측정 — FDD-1605.

GL 100만 라인 기준 성능 SLA 측정.
순수 함수만 포함. DB 접근 금지.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from app.qa.types import (
    QA_VERSION,
    QACheckType,
    QAFinding,
    QAResult,
    QASeverity,
    create_result_from_findings,
)

PERFORMANCE_QA_VERSION = "0.1.0"


@dataclass
class SLADefinition:
    """SLA 정의.

    Attributes:
        operation: 작업 이름
        max_seconds: 최대 허용 시간 (초)
        gl_line_threshold: GL 라인 수 임계값 (0 = 모든 크기)
        warning_threshold: 경고 임계값 비율 (기본 0.8)
    """

    operation: str
    max_seconds: float
    gl_line_threshold: int = 0
    warning_threshold: float = 0.8


# 기본 SLA 정의
DEFAULT_SLAS: dict[str, SLADefinition] = {
    "gl_ingest_100k": SLADefinition(
        operation="GL Ingest (100K lines)",
        max_seconds=30.0,
        gl_line_threshold=100_000,
    ),
    "gl_ingest_1m": SLADefinition(
        operation="GL Ingest (1M lines)",
        max_seconds=300.0,
        gl_line_threshold=1_000_000,
    ),
    "qoe_calc": SLADefinition(
        operation="QoE Calculation",
        max_seconds=60.0,
        gl_line_threshold=1_000_000,
    ),
    "nwc_calc": SLADefinition(
        operation="NWC Calculation",
        max_seconds=60.0,
        gl_line_threshold=1_000_000,
    ),
    "debt_calc": SLADefinition(
        operation="Net Debt Calculation",
        max_seconds=30.0,
        gl_line_threshold=1_000_000,
    ),
    "report_ir_gen": SLADefinition(
        operation="Report IR Generation",
        max_seconds=30.0,
        gl_line_threshold=1_000_000,
    ),
    "ppt_render": SLADefinition(
        operation="PPT Rendering",
        max_seconds=120.0,
        gl_line_threshold=1_000_000,
    ),
}


@dataclass
class PerformanceMeasurement:
    """성능 측정 결과.

    Attributes:
        operation: 작업 이름
        duration_seconds: 소요 시간 (초)
        sla_seconds: SLA 최대 시간 (초)
        passed: SLA 통과 여부
        data_size: 데이터 크기 (행 수 등)
        warning: 경고 상태 여부
    """

    operation: str
    duration_seconds: float
    sla_seconds: float
    passed: bool
    data_size: int = 0
    warning: bool = False

    @property
    def utilization(self) -> float:
        """SLA 사용률 (0.0 ~ 1.0+)."""
        if self.sla_seconds <= 0:
            return 0.0
        return self.duration_seconds / self.sla_seconds

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환."""
        return {
            "operation": self.operation,
            "duration_seconds": round(self.duration_seconds, 3),
            "sla_seconds": self.sla_seconds,
            "passed": self.passed,
            "warning": self.warning,
            "utilization": round(self.utilization, 3),
            "data_size": self.data_size,
        }


def measure_operation(
    operation_name: str,
    func: Callable[[], Any],
    sla: SLADefinition,
    data_size: int = 0,
) -> tuple[PerformanceMeasurement, QAFinding | None]:
    """단일 작업 성능 측정.

    Args:
        operation_name: 작업 이름
        func: 측정할 함수 (인자 없음)
        sla: SLA 정의
        data_size: 데이터 크기 (선택)

    Returns:
        (PerformanceMeasurement, QAFinding 또는 None)
    """
    start = time.perf_counter()
    try:
        func()
    except Exception as e:
        # 예외 발생 시에도 시간 측정
        elapsed = time.perf_counter() - start
        return PerformanceMeasurement(
            operation=operation_name,
            duration_seconds=elapsed,
            sla_seconds=sla.max_seconds,
            passed=False,
            data_size=data_size,
        ), QAFinding(
            check_type=QACheckType.PERFORMANCE_SLA,
            severity=QASeverity.ERROR,
            location=f"performance/{operation_name}",
            message=f"Operation failed with exception: {e}",
            expected="successful completion",
            actual=str(type(e).__name__),
        )

    elapsed = time.perf_counter() - start
    passed = elapsed <= sla.max_seconds
    warning = not passed or (elapsed > sla.max_seconds * sla.warning_threshold)

    finding: QAFinding | None = None
    if not passed:
        finding = QAFinding(
            check_type=QACheckType.PERFORMANCE_SLA,
            severity=QASeverity.ERROR,
            location=f"performance/{operation_name}",
            message=f"SLA exceeded: {elapsed:.2f}s > {sla.max_seconds}s",
            expected=f"<= {sla.max_seconds}s",
            actual=f"{elapsed:.2f}s",
            context={"data_size": data_size, "utilization": round(elapsed / sla.max_seconds, 3)},
        )
    elif warning:
        finding = QAFinding(
            check_type=QACheckType.PERFORMANCE_SLA,
            severity=QASeverity.WARNING,
            location=f"performance/{operation_name}",
            message=f"SLA warning: {elapsed:.2f}s > {sla.max_seconds * sla.warning_threshold:.2f}s (80% threshold)",
            expected=f"<= {sla.max_seconds * sla.warning_threshold:.2f}s",
            actual=f"{elapsed:.2f}s",
            context={"data_size": data_size, "utilization": round(elapsed / sla.max_seconds, 3)},
        )
    else:
        finding = QAFinding(
            check_type=QACheckType.PERFORMANCE_SLA,
            severity=QASeverity.INFO,
            location=f"performance/{operation_name}",
            message=f"SLA passed: {elapsed:.2f}s <= {sla.max_seconds}s",
            expected=f"<= {sla.max_seconds}s",
            actual=f"{elapsed:.2f}s",
            context={"data_size": data_size, "utilization": round(elapsed / sla.max_seconds, 3)},
        )

    measurement = PerformanceMeasurement(
        operation=operation_name,
        duration_seconds=elapsed,
        sla_seconds=sla.max_seconds,
        passed=passed,
        warning=warning and passed,
        data_size=data_size,
    )

    return measurement, finding


def run_performance_qa(
    operations: list[tuple[str, Callable[[], Any], SLADefinition, int]],
) -> tuple[QAResult, list[QAFinding], list[PerformanceMeasurement]]:
    """성능 QA 전체 실행.

    Args:
        operations: [(이름, 함수, SLA, 데이터크기), ...] 목록

    Returns:
        (QAResult, findings 목록, measurements 목록)
    """
    start_time = time.perf_counter()
    findings: list[QAFinding] = []
    measurements: list[PerformanceMeasurement] = []

    for op_name, func, sla, data_size in operations:
        measurement, finding = measure_operation(op_name, func, sla, data_size)
        measurements.append(measurement)
        if finding:
            findings.append(finding)

    duration_ms = (time.perf_counter() - start_time) * 1000
    result = create_result_from_findings("performance_qa", findings, duration_ms)

    return result, findings, measurements


@dataclass
class PerformanceReport:
    """성능 리포트.

    Attributes:
        total_operations: 총 작업 수
        passed_operations: 통과한 작업 수
        warning_operations: 경고 작업 수
        failed_operations: 실패한 작업 수
        measurements: 측정 결과 목록
        total_duration_seconds: 총 소요 시간
    """

    total_operations: int = 0
    passed_operations: int = 0
    warning_operations: int = 0
    failed_operations: int = 0
    measurements: list[PerformanceMeasurement] = field(default_factory=list)
    total_duration_seconds: float = 0.0

    @classmethod
    def from_measurements(
        cls,
        measurements: list[PerformanceMeasurement],
    ) -> PerformanceReport:
        """측정 결과에서 리포트 생성."""
        total = len(measurements)
        passed = sum(1 for m in measurements if m.passed and not m.warning)
        warning = sum(1 for m in measurements if m.passed and m.warning)
        failed = sum(1 for m in measurements if not m.passed)
        total_duration = sum(m.duration_seconds for m in measurements)

        return cls(
            total_operations=total,
            passed_operations=passed,
            warning_operations=warning,
            failed_operations=failed,
            measurements=measurements,
            total_duration_seconds=total_duration,
        )

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환."""
        return {
            "total_operations": self.total_operations,
            "passed_operations": self.passed_operations,
            "warning_operations": self.warning_operations,
            "failed_operations": self.failed_operations,
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "measurements": [m.to_dict() for m in self.measurements],
        }
