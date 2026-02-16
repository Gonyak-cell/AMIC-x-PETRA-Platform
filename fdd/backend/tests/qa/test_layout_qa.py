"""Layout QA 테스트 — FDD-1603.

테스트 ID 규칙: T-QA-LAYOUT-{번호}
"""

from __future__ import annotations

import pytest

from app.qa import (
    QACheckType,
    QASeverity,
    check_text_overflow,
    check_unsubstituted_placeholders,
    run_layout_qa,
)


class TestCheckUnsubstitutedPlaceholders:
    """T-QA-LAYOUT-01: Placeholder 검사 테스트."""

    def test_no_placeholders(self) -> None:
        """Placeholder 없는 IR."""
        ir = {
            "sections": [
                {"type": "text", "title": "Introduction", "content": "Normal text"},
            ]
        }
        findings = check_unsubstituted_placeholders(ir)
        assert len(findings) == 0

    def test_unsubstituted_simple(self) -> None:
        """단순 placeholder 미치환."""
        ir = {
            "sections": [
                {"type": "text", "content": "Hello {{NAME}}, welcome!"},
            ]
        }
        findings = check_unsubstituted_placeholders(ir)

        assert len(findings) == 1
        assert findings[0].check_type == QACheckType.PLACEHOLDER_MISSING
        assert findings[0].severity == QASeverity.WARNING
        assert "{{NAME}}" in findings[0].message

    def test_table_placeholder(self) -> None:
        """테이블 placeholder 미치환."""
        ir = {
            "sections": [
                {"type": "text", "content": "See {{TABLE:SUMMARY}}"},
            ]
        }
        findings = check_unsubstituted_placeholders(ir)

        assert len(findings) == 1
        assert "{{TABLE:SUMMARY}}" in findings[0].message

    def test_multiple_placeholders(self) -> None:
        """여러 placeholder."""
        ir = {
            "sections": [
                {"type": "text", "content": "{{VAR1}} and {{VAR2}}"},
            ]
        }
        findings = check_unsubstituted_placeholders(ir)
        assert len(findings) == 2

    def test_table_cell_placeholder(self) -> None:
        """테이블 셀 내 placeholder."""
        ir = {
            "sections": [
                {
                    "type": "table",
                    "rows": [{"col1": "Normal", "col2": "{{MISSING}}"}],
                }
            ]
        }
        findings = check_unsubstituted_placeholders(ir)

        assert len(findings) == 1
        assert "col.col2" in findings[0].location


class TestCheckTextOverflow:
    """T-QA-LAYOUT-02: 오버플로우 검사 테스트."""

    def test_no_overflow(self) -> None:
        """오버플로우 없음."""
        ir = {
            "sections": [
                {"type": "text", "content": "Short text"},
            ]
        }
        findings = check_text_overflow(ir, text_limit=100)
        assert len(findings) == 0

    def test_text_block_overflow(self) -> None:
        """텍스트 블록 오버플로우."""
        long_text = "A" * 600
        ir = {
            "sections": [
                {"type": "text", "content": long_text},
            ]
        }
        findings = check_text_overflow(ir, text_limit=500)

        assert len(findings) == 1
        assert findings[0].check_type == QACheckType.TEXT_OVERFLOW
        assert findings[0].severity == QASeverity.WARNING
        assert "600 chars" in findings[0].actual

    def test_claim_text_overflow(self) -> None:
        """Claim 텍스트 오버플로우."""
        long_claim = "B" * 700
        ir = {
            "sections": [
                {"type": "claim", "claim_text": long_claim},
            ]
        }
        findings = check_text_overflow(ir, text_limit=500)

        assert len(findings) == 1
        assert "claim_text" in findings[0].location

    def test_table_cell_overflow(self) -> None:
        """테이블 셀 오버플로우."""
        long_cell = "C" * 100
        ir = {
            "sections": [
                {
                    "type": "table",
                    "rows": [{"col1": "OK", "col2": long_cell}],
                }
            ]
        }
        findings = check_text_overflow(ir, cell_limit=50)

        assert len(findings) == 1
        assert "col.col2" in findings[0].location

    def test_custom_limits(self) -> None:
        """커스텀 제한값."""
        ir = {
            "sections": [
                {"type": "text", "content": "A" * 30},
            ]
        }
        # 제한 25 → 오버플로우
        findings = check_text_overflow(ir, text_limit=25)
        assert len(findings) == 1

        # 제한 50 → 통과
        findings = check_text_overflow(ir, text_limit=50)
        assert len(findings) == 0


class TestRunLayoutQA:
    """T-QA-LAYOUT-03: run_layout_qa 통합 테스트."""

    def test_all_pass(self) -> None:
        """모든 검사 통과."""
        ir = {
            "sections": [
                {"type": "text", "content": "Normal content"},
                {"type": "table", "rows": [{"a": "1", "b": "2"}]},
            ]
        }
        result, findings = run_layout_qa(ir)

        assert result.passed is True
        assert result.check_name == "layout_qa"
        assert result.warning_count == 0

    def test_mixed_issues(self) -> None:
        """여러 이슈 혼합."""
        ir = {
            "sections": [
                {"type": "text", "content": "{{MISSING}} " + "X" * 600},
            ]
        }
        result, findings = run_layout_qa(ir, text_limit=500)

        # Placeholder 1개 + Overflow 1개 = 2 warnings
        assert result.warning_count == 2
        assert result.passed is True  # WARNING은 통과

    def test_duration_measured(self) -> None:
        """실행 시간 측정."""
        ir = {"sections": []}
        result, _ = run_layout_qa(ir)

        assert result.duration_ms >= 0
