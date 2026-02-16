"""QA 공통 타입 테스트 — Sprint 8.

테스트 ID 규칙: T-QA-TYPE-{번호}
"""

from __future__ import annotations

import pytest

from app.qa.types import (
    QA_VERSION,
    QACheckType,
    QAFinding,
    QAResult,
    QASeverity,
    create_result_from_findings,
)


class TestQASeverity:
    """T-QA-TYPE-01: QASeverity enum 테스트."""

    def test_severity_values(self) -> None:
        """심각도 값이 올바른 순서인지 확인."""
        assert QASeverity.INFO < QASeverity.WARNING
        assert QASeverity.WARNING < QASeverity.ERROR
        assert QASeverity.ERROR < QASeverity.CRITICAL

    def test_severity_int_values(self) -> None:
        """심각도 정수 값 확인."""
        assert int(QASeverity.INFO) == 0
        assert int(QASeverity.WARNING) == 1
        assert int(QASeverity.ERROR) == 2
        assert int(QASeverity.CRITICAL) == 3


class TestQACheckType:
    """T-QA-TYPE-02: QACheckType enum 테스트."""

    def test_check_type_count(self) -> None:
        """검사 유형이 8개인지 확인."""
        assert len(QACheckType) == 8

    def test_check_type_names(self) -> None:
        """검사 유형 이름 확인."""
        expected = {
            "NUMERIC_DIFF",
            "PLACEHOLDER_MISSING",
            "TEXT_OVERFLOW",
            "EVIDENCE_MISSING",
            "EVIDENCE_BROKEN",
            "PERFORMANCE_SLA",
            "GOLDEN_MISMATCH",
            "STRUCTURE_MISMATCH",
        }
        actual = {ct.name for ct in QACheckType}
        assert actual == expected


class TestQAFinding:
    """T-QA-TYPE-03: QAFinding dataclass 테스트."""

    def test_finding_creation(self) -> None:
        """기본 Finding 생성."""
        finding = QAFinding(
            check_type=QACheckType.NUMERIC_DIFF,
            severity=QASeverity.ERROR,
            location="section.qoe/block.bridge/row.3",
            message="Expected 100.00, got 99.99",
            expected="100.00",
            actual="99.99",
        )
        assert finding.check_type == QACheckType.NUMERIC_DIFF
        assert finding.severity == QASeverity.ERROR
        assert "row.3" in finding.location
        assert finding.expected == "100.00"
        assert finding.actual == "99.99"

    def test_finding_immutable(self) -> None:
        """Finding은 불변(frozen)이어야 함."""
        finding = QAFinding(
            check_type=QACheckType.NUMERIC_DIFF,
            severity=QASeverity.INFO,
            location="test",
            message="test",
        )
        with pytest.raises(AttributeError):
            finding.message = "changed"  # type: ignore[misc]

    def test_finding_to_dict(self) -> None:
        """Finding -> dict 변환."""
        finding = QAFinding(
            check_type=QACheckType.EVIDENCE_MISSING,
            severity=QASeverity.WARNING,
            location="section.nwc",
            message="Missing evidence",
            context={"block_type": "table"},
        )
        d = finding.to_dict()
        assert d["check_type"] == "EVIDENCE_MISSING"
        assert d["severity"] == "WARNING"
        assert d["location"] == "section.nwc"
        assert d["context"]["block_type"] == "table"

    def test_finding_optional_fields(self) -> None:
        """선택 필드 기본값 확인."""
        finding = QAFinding(
            check_type=QACheckType.TEXT_OVERFLOW,
            severity=QASeverity.INFO,
            location="test",
            message="test",
        )
        assert finding.expected is None
        assert finding.actual is None
        assert finding.evidence_id is None
        assert finding.context == {}


class TestQAResult:
    """T-QA-TYPE-04: QAResult dataclass 테스트."""

    def test_result_creation(self) -> None:
        """기본 Result 생성."""
        result = QAResult(
            check_name="report_numeric_diff",
            passed=True,
            total_checks=10,
            passed_checks=10,
        )
        assert result.check_name == "report_numeric_diff"
        assert result.passed is True
        assert result.total_checks == 10
        assert result.qa_version == QA_VERSION

    def test_result_failed_checks(self) -> None:
        """failed_checks 계산 확인."""
        result = QAResult(
            check_name="test",
            passed=False,
            total_checks=10,
            passed_checks=7,
        )
        assert result.failed_checks == 3

    def test_result_pass_rate(self) -> None:
        """pass_rate 계산 확인."""
        result = QAResult(
            check_name="test",
            passed=False,
            total_checks=10,
            passed_checks=8,
        )
        assert result.pass_rate == 0.8

    def test_result_pass_rate_zero_checks(self) -> None:
        """검사 항목이 0일 때 pass_rate는 1.0."""
        result = QAResult(
            check_name="test",
            passed=True,
            total_checks=0,
            passed_checks=0,
        )
        assert result.pass_rate == 1.0

    def test_result_to_dict(self) -> None:
        """Result -> dict 변환."""
        finding = QAFinding(
            check_type=QACheckType.NUMERIC_DIFF,
            severity=QASeverity.ERROR,
            location="test",
            message="test",
        )
        result = QAResult(
            check_name="test",
            passed=False,
            total_checks=5,
            passed_checks=4,
            error_count=1,
            findings=[finding],
            duration_ms=123.456,
        )
        d = result.to_dict()
        assert d["check_name"] == "test"
        assert d["passed"] is False
        assert d["failed_checks"] == 1
        assert d["pass_rate"] == 0.8
        assert d["duration_ms"] == 123.46
        assert len(d["findings"]) == 1


class TestCreateResultFromFindings:
    """T-QA-TYPE-05: create_result_from_findings 함수 테스트."""

    def test_all_info_findings(self) -> None:
        """모두 INFO면 passed=True."""
        findings = [
            QAFinding(
                check_type=QACheckType.NUMERIC_DIFF,
                severity=QASeverity.INFO,
                location=f"row.{i}",
                message="OK",
            )
            for i in range(5)
        ]
        result = create_result_from_findings("test", findings, 100.0)
        assert result.passed is True
        assert result.total_checks == 5
        assert result.passed_checks == 5
        assert result.warning_count == 0
        assert result.error_count == 0
        assert result.duration_ms == 100.0

    def test_warning_findings(self) -> None:
        """WARNING만 있으면 passed=True (경고는 통과)."""
        findings = [
            QAFinding(
                check_type=QACheckType.TEXT_OVERFLOW,
                severity=QASeverity.WARNING,
                location="test",
                message="Overflow",
            ),
        ]
        result = create_result_from_findings("test", findings)
        assert result.passed is True
        assert result.warning_count == 1
        assert result.error_count == 0

    def test_error_findings(self) -> None:
        """ERROR가 있으면 passed=False."""
        findings = [
            QAFinding(
                check_type=QACheckType.NUMERIC_DIFF,
                severity=QASeverity.INFO,
                location="row.1",
                message="OK",
            ),
            QAFinding(
                check_type=QACheckType.NUMERIC_DIFF,
                severity=QASeverity.ERROR,
                location="row.2",
                message="Mismatch",
            ),
        ]
        result = create_result_from_findings("test", findings)
        assert result.passed is False
        assert result.error_count == 1
        assert result.passed_checks == 1  # INFO 1개

    def test_critical_findings(self) -> None:
        """CRITICAL이 있으면 passed=False."""
        findings = [
            QAFinding(
                check_type=QACheckType.EVIDENCE_BROKEN,
                severity=QASeverity.CRITICAL,
                location="test",
                message="Broken link",
            ),
        ]
        result = create_result_from_findings("test", findings)
        assert result.passed is False
        assert result.critical_count == 1

    def test_empty_findings(self) -> None:
        """빈 findings는 passed=True."""
        result = create_result_from_findings("test", [])
        assert result.passed is True
        assert result.total_checks == 0
        assert result.pass_rate == 1.0
