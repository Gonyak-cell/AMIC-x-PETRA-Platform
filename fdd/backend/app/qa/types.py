"""QA 공통 타입 정의 — Sprint 8.

모든 QA 모듈에서 사용하는 공통 타입을 정의합니다.
순수 데이터 타입만 포함. 비즈니스 로직 없음.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import Any

QA_VERSION = "0.1.0"


class QASeverity(IntEnum):
    """QA 발견 심각도.

    INFO: 정보성 (통과)
    WARNING: 경고 (진행 가능하나 검토 권장)
    ERROR: 오류 (수정 권장)
    CRITICAL: 치명적 (진행 불가)
    """

    INFO = 0
    WARNING = 1
    ERROR = 2
    CRITICAL = 3


class QACheckType(IntEnum):
    """QA 검사 유형."""

    NUMERIC_DIFF = auto()  # 수치 불일치
    PLACEHOLDER_MISSING = auto()  # Placeholder 미치환
    TEXT_OVERFLOW = auto()  # 텍스트 오버플로우
    EVIDENCE_MISSING = auto()  # Evidence 누락
    EVIDENCE_BROKEN = auto()  # Evidence 링크 깨짐
    PERFORMANCE_SLA = auto()  # 성능 SLA 미달
    GOLDEN_MISMATCH = auto()  # 골든 데이터 불일치
    STRUCTURE_MISMATCH = auto()  # 구조 불일치 (행/열 개수 등)


@dataclass(frozen=True)
class QAFinding:
    """단일 QA 발견 항목.

    Attributes:
        check_type: 검사 유형
        severity: 심각도
        location: 위치 (예: "section.qoe/block.bridge/row.3/col.fy2024")
        message: 발견 설명
        expected: 예상 값 (선택)
        actual: 실제 값 (선택)
        evidence_id: 관련 Evidence ID (선택)
        context: 추가 컨텍스트 (선택)
    """

    check_type: QACheckType
    severity: QASeverity
    location: str
    message: str
    expected: str | None = None
    actual: str | None = None
    evidence_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환."""
        return {
            "check_type": self.check_type.name,
            "severity": self.severity.name,
            "location": self.location,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
            "evidence_id": self.evidence_id,
            "context": self.context,
        }


@dataclass
class QAResult:
    """QA 검사 결과.

    Attributes:
        check_name: 검사 이름 (예: "report_numeric_diff")
        passed: 전체 통과 여부
        total_checks: 총 검사 항목 수
        passed_checks: 통과한 항목 수
        warning_count: 경고 수
        error_count: 오류 수
        critical_count: 치명적 오류 수
        findings: 발견 목록
        duration_ms: 검사 소요 시간 (밀리초)
        qa_version: QA 모듈 버전
    """

    check_name: str
    passed: bool
    total_checks: int
    passed_checks: int
    warning_count: int = 0
    error_count: int = 0
    critical_count: int = 0
    findings: list[QAFinding] = field(default_factory=list)
    duration_ms: float = 0.0
    qa_version: str = QA_VERSION

    @property
    def failed_checks(self) -> int:
        """실패한 검사 항목 수."""
        return self.total_checks - self.passed_checks

    @property
    def pass_rate(self) -> float:
        """통과율 (0.0 ~ 1.0)."""
        if self.total_checks == 0:
            return 1.0
        return self.passed_checks / self.total_checks

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환."""
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warning_count": self.warning_count,
            "error_count": self.error_count,
            "critical_count": self.critical_count,
            "pass_rate": round(self.pass_rate, 4),
            "findings": [f.to_dict() for f in self.findings],
            "duration_ms": round(self.duration_ms, 2),
            "qa_version": self.qa_version,
        }


def create_result_from_findings(
    check_name: str,
    findings: list[QAFinding],
    duration_ms: float = 0.0,
) -> QAResult:
    """발견 목록에서 QAResult를 생성.

    Args:
        check_name: 검사 이름
        findings: 발견 목록
        duration_ms: 소요 시간

    Returns:
        집계된 QAResult
    """
    warning_count = sum(1 for f in findings if f.severity == QASeverity.WARNING)
    error_count = sum(1 for f in findings if f.severity == QASeverity.ERROR)
    critical_count = sum(1 for f in findings if f.severity == QASeverity.CRITICAL)

    # ERROR 또는 CRITICAL이 있으면 실패
    passed = error_count == 0 and critical_count == 0

    # 총 검사 = 발견 수 (INFO 제외)
    total_checks = len(findings)
    passed_checks = sum(1 for f in findings if f.severity == QASeverity.INFO)

    return QAResult(
        check_name=check_name,
        passed=passed,
        total_checks=total_checks,
        passed_checks=passed_checks,
        warning_count=warning_count,
        error_count=error_count,
        critical_count=critical_count,
        findings=findings,
        duration_ms=duration_ms,
        qa_version=QA_VERSION,
    )
