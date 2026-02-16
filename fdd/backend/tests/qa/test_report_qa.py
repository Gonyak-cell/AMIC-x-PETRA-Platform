"""Report QA 테스트 — FDD-1602.

테스트 ID 규칙: T-QA-REPORT-{번호}
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.qa import (
    QACheckType,
    QASeverity,
    compare_numeric_values,
    compare_report_ir,
    compare_table_block,
    compare_table_rows,
    run_report_qa,
)


class TestCompareNumericValues:
    """T-QA-REPORT-01: 수치 비교 테스트."""

    def test_exact_match(self) -> None:
        """정확히 일치하는 경우."""
        match, exp, act = compare_numeric_values(
            Decimal("100.0000"),
            Decimal("100.0000"),
        )
        assert match is True
        assert exp == Decimal("100.0000")
        assert act == Decimal("100.0000")

    def test_within_tolerance(self) -> None:
        """허용 오차 내 일치."""
        match, _, _ = compare_numeric_values(
            Decimal("100.0000"),
            Decimal("100.00005"),
            tolerance=Decimal("0.0001"),
        )
        assert match is True

    def test_outside_tolerance(self) -> None:
        """허용 오차 초과 불일치."""
        match, _, _ = compare_numeric_values(
            Decimal("100.0000"),
            Decimal("100.0002"),
            tolerance=Decimal("0.0001"),
        )
        assert match is False

    def test_string_values(self) -> None:
        """문자열 값 비교."""
        match, exp, act = compare_numeric_values("100.00", "100.00")
        assert match is True
        assert exp == Decimal("100.00")

    def test_none_values(self) -> None:
        """None 값 처리."""
        match, _, _ = compare_numeric_values(None, None)
        assert match is True

        match, _, _ = compare_numeric_values(Decimal("100"), None)
        assert match is False


class TestCompareTableRows:
    """T-QA-REPORT-02: 테이블 행 비교 테스트."""

    def test_matching_rows(self) -> None:
        """일치하는 행."""
        expected = [{"amount": "100.00", "label": "Revenue"}]
        actual = [{"amount": "100.00", "label": "Revenue"}]
        findings = compare_table_rows(expected, actual, ["amount"], "test")

        assert len(findings) == 1
        assert findings[0].severity == QASeverity.INFO  # 일치

    def test_numeric_diff(self) -> None:
        """수치 불일치."""
        expected = [{"amount": "100.00"}]
        actual = [{"amount": "99.00"}]
        findings = compare_table_rows(expected, actual, ["amount"], "test")

        assert any(f.severity == QASeverity.ERROR for f in findings)
        assert any("100.00" in (f.expected or "") for f in findings)

    def test_row_count_mismatch(self) -> None:
        """행 개수 불일치."""
        expected = [{"a": "1"}, {"a": "2"}, {"a": "3"}]
        actual = [{"a": "1"}, {"a": "2"}]
        findings = compare_table_rows(expected, actual, ["a"], "test")

        structure_findings = [f for f in findings if f.check_type == QACheckType.STRUCTURE_MISMATCH]
        assert len(structure_findings) == 1
        assert structure_findings[0].expected == "3"
        assert structure_findings[0].actual == "2"

    def test_multiple_numeric_keys(self) -> None:
        """여러 수치 키 비교."""
        expected = [{"col1": "100", "col2": "200"}]
        actual = [{"col1": "100", "col2": "200"}]
        findings = compare_table_rows(expected, actual, ["col1", "col2"], "test")

        # 2개 컬럼 × 1행 = 2개 INFO findings
        info_findings = [f for f in findings if f.severity == QASeverity.INFO]
        assert len(info_findings) == 2


class TestCompareTableBlock:
    """T-QA-REPORT-03: TableBlock 비교 테스트."""

    def test_matching_block(self) -> None:
        """일치하는 블록."""
        expected = {
            "type": "table",
            "title": "QoE Bridge",
            "rows": [{"category": "Revenue", "amount": "1000.00"}],
            "footer_rows": [{"category": "Total", "amount": "1000.00"}],
        }
        actual = expected.copy()

        findings = compare_table_block(expected, actual, "qoe_bridge", ["amount"])
        errors = [f for f in findings if f.severity == QASeverity.ERROR]
        assert len(errors) == 0

    def test_auto_detect_numeric_keys(self) -> None:
        """수치 키 자동 감지."""
        expected = {
            "rows": [{"label": "Test", "value": "123.45", "notes": "text"}],
        }
        actual = {
            "rows": [{"label": "Test", "value": "123.45", "notes": "text"}],
        }

        findings = compare_table_block(expected, actual, "test")
        # value가 수치로 감지되어 비교됨
        assert len(findings) >= 1


class TestCompareReportIR:
    """T-QA-REPORT-04: Report IR 전체 비교 테스트."""

    def test_matching_ir(self) -> None:
        """일치하는 IR."""
        ir = {
            "metadata": {"deal_id": "abc-123"},
            "sections": [
                {"type": "table", "title": "QoE", "rows": [{"amount": "100"}]},
            ],
        }
        result, findings = compare_report_ir(ir, ir)

        assert result.passed is True
        errors = [f for f in findings if f.severity == QASeverity.ERROR]
        assert len(errors) == 0

    def test_section_count_mismatch(self) -> None:
        """섹션 개수 불일치."""
        expected_ir = {
            "metadata": {"deal_id": "abc"},
            "sections": [
                {"type": "table", "title": "A"},
                {"type": "table", "title": "B"},
            ],
        }
        actual_ir = {
            "metadata": {"deal_id": "abc"},
            "sections": [{"type": "table", "title": "A"}],
        }

        result, findings = compare_report_ir(expected_ir, actual_ir)
        structure_findings = [f for f in findings if f.check_type == QACheckType.STRUCTURE_MISMATCH]
        assert any("Section count" in f.message for f in structure_findings)

    def test_missing_section(self) -> None:
        """누락된 섹션."""
        expected_ir = {
            "metadata": {"deal_id": "abc"},
            "sections": [{"type": "table", "title": "Missing"}],
        }
        actual_ir = {
            "metadata": {"deal_id": "abc"},
            "sections": [{"type": "table", "title": "Different"}],
        }

        result, findings = compare_report_ir(expected_ir, actual_ir)
        assert result.passed is False


class TestRunReportQA:
    """T-QA-REPORT-05: run_report_qa 통합 테스트."""

    def test_full_qa_pass(self) -> None:
        """전체 QA 통과."""
        ir = {
            "metadata": {"deal_id": "test-001"},
            "sections": [
                {
                    "type": "table",
                    "title": "Summary",
                    "rows": [
                        {"item": "Revenue", "fy2024": "1000000.0000"},
                        {"item": "EBITDA", "fy2024": "200000.0000"},
                    ],
                },
            ],
        }
        result, findings = run_report_qa(ir, ir)

        assert result.passed is True
        assert result.check_name == "report_numeric_diff"
        assert result.duration_ms > 0

    def test_full_qa_fail(self) -> None:
        """전체 QA 실패."""
        expected = {
            "metadata": {"deal_id": "test-001"},
            "sections": [
                {"type": "table", "title": "T1", "rows": [{"val": "100"}]},
            ],
        }
        actual = {
            "metadata": {"deal_id": "test-001"},
            "sections": [
                {"type": "table", "title": "T1", "rows": [{"val": "999"}]},
            ],
        }
        result, findings = run_report_qa(expected, actual)

        assert result.passed is False
        assert result.error_count > 0
