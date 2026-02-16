"""Evidence QA 테스트 — FDD-1604.

테스트 ID 규칙: T-QA-EVIDENCE-{번호}
"""

from __future__ import annotations

import pytest

from app.qa import (
    QACheckType,
    QASeverity,
    check_db_evidence_integrity,
    check_ir_evidence_coverage,
    check_required_evidence,
    run_evidence_qa,
)


class TestCheckIrEvidenceCoverage:
    """T-QA-EVIDENCE-01: IR Evidence 커버리지 테스트."""

    def test_valid_claim_evidence(self) -> None:
        """유효한 Claim evidence."""
        ir = {
            "sections": [
                {
                    "type": "claim",
                    "claim_text": "Revenue increased by 10%",
                    "verified": True,
                    "evidence_refs": [
                        {"evidence_id": "ev-001", "description": "TB Revenue"}
                    ],
                }
            ]
        }
        evidence_index = {"ev-001": {"source_type": "TB"}}

        findings = check_ir_evidence_coverage(ir, evidence_index)
        info_findings = [f for f in findings if f.severity == QASeverity.INFO]
        assert len(info_findings) >= 1

    def test_verified_claim_no_evidence(self) -> None:
        """verified=True인데 evidence 없음."""
        ir = {
            "sections": [
                {
                    "type": "claim",
                    "claim_text": "Some claim",
                    "verified": True,
                    "evidence_refs": [],
                }
            ]
        }
        findings = check_ir_evidence_coverage(ir, {})

        error_findings = [f for f in findings if f.severity == QASeverity.ERROR]
        assert len(error_findings) == 1
        assert error_findings[0].check_type == QACheckType.EVIDENCE_MISSING

    def test_broken_evidence_ref(self) -> None:
        """존재하지 않는 evidence 참조."""
        ir = {
            "sections": [
                {
                    "type": "claim",
                    "verified": True,
                    "evidence_refs": [{"evidence_id": "invalid-id"}],
                }
            ]
        }
        evidence_index = {"ev-001": {}}

        findings = check_ir_evidence_coverage(ir, evidence_index)
        broken_findings = [f for f in findings if f.check_type == QACheckType.EVIDENCE_BROKEN]
        assert len(broken_findings) == 1
        assert broken_findings[0].evidence_id == "invalid-id"

    def test_unverified_claim_ok(self) -> None:
        """verified=False면 evidence 없어도 OK."""
        ir = {
            "sections": [
                {
                    "type": "claim",
                    "verified": False,
                    "evidence_refs": [],
                }
            ]
        }
        findings = check_ir_evidence_coverage(ir, {})
        errors = [f for f in findings if f.severity == QASeverity.ERROR]
        assert len(errors) == 0

    def test_table_row_evidence(self) -> None:
        """테이블 행 evidence 검증."""
        ir = {
            "sections": [
                {
                    "type": "table",
                    "rows": [
                        {"label": "Row1", "evidence_ids": ["ev-001"]},
                        {"label": "Row2", "evidence_ids": ["invalid-002"]},
                    ],
                }
            ]
        }
        evidence_index = {"ev-001": {}}

        findings = check_ir_evidence_coverage(ir, evidence_index)
        broken = [f for f in findings if f.check_type == QACheckType.EVIDENCE_BROKEN]
        assert len(broken) == 1
        assert broken[0].evidence_id == "invalid-002"


class TestCheckRequiredEvidence:
    """T-QA-EVIDENCE-02: 필수 Evidence 규칙 테스트."""

    def test_claim_requirement_met(self) -> None:
        """Claim 필수 evidence 충족."""
        ir = {
            "sections": [
                {
                    "type": "claim",
                    "evidence_refs": [{"evidence_id": "e1"}, {"evidence_id": "e2"}],
                }
            ]
        }
        findings = check_required_evidence(ir, {"claim": 1})

        info_findings = [f for f in findings if f.severity == QASeverity.INFO]
        assert len(info_findings) >= 1

    def test_claim_requirement_not_met(self) -> None:
        """Claim 필수 evidence 미충족."""
        ir = {
            "sections": [
                {"type": "claim", "evidence_refs": []},
            ]
        }
        findings = check_required_evidence(ir, {"claim": 1})

        warnings = [f for f in findings if f.severity == QASeverity.WARNING]
        assert len(warnings) == 1
        assert "fewer than 1" in warnings[0].message

    def test_table_row_requirement(self) -> None:
        """테이블 행 필수 evidence."""
        ir = {
            "sections": [
                {
                    "type": "table",
                    "rows": [
                        {"evidence_ids": []},
                        {"evidence_ids": ["e1"]},
                    ],
                }
            ]
        }
        findings = check_required_evidence(ir, {"table_row": 1})

        warnings = [f for f in findings if f.severity == QASeverity.WARNING]
        assert len(warnings) == 1  # 첫 번째 행만

    def test_separator_rows_skipped(self) -> None:
        """separator 행은 검사 제외."""
        ir = {
            "sections": [
                {
                    "type": "table",
                    "rows": [
                        {"row_style": "separator", "evidence_ids": []},
                    ],
                }
            ]
        }
        findings = check_required_evidence(ir, {"table_row": 1})
        assert len(findings) == 0


class TestCheckDbEvidenceIntegrity:
    """T-QA-EVIDENCE-03: DB Evidence 무결성 테스트."""

    def test_valid_evidence_link(self) -> None:
        """유효한 evidence link."""
        links = [
            {
                "id": "link-001",
                "target_type": "qoe_adjustment",
                "target_id": "adj-001",
                "source_type": "GL",
                "source_id": "entry-001",
            }
        ]
        findings = check_db_evidence_integrity(links)
        assert len(findings) == 0

    def test_missing_target(self) -> None:
        """target 정보 누락."""
        links = [
            {
                "id": "link-001",
                "target_type": None,
                "target_id": "adj-001",
                "source_type": "GL",
                "source_id": "entry-001",
            }
        ]
        findings = check_db_evidence_integrity(links)

        errors = [f for f in findings if f.check_type == QACheckType.EVIDENCE_BROKEN]
        assert len(errors) == 1
        assert "target_type" in errors[0].message

    def test_missing_source(self) -> None:
        """source 정보 누락."""
        links = [
            {
                "id": "link-002",
                "target_type": "account_mapping",
                "target_id": "map-001",
                "source_type": None,
                "source_id": "",
            }
        ]
        findings = check_db_evidence_integrity(links)
        assert len(findings) >= 1


class TestRunEvidenceQA:
    """T-QA-EVIDENCE-04: run_evidence_qa 통합 테스트."""

    def test_all_pass(self) -> None:
        """모든 검사 통과."""
        ir = {
            "sections": [
                {
                    "type": "claim",
                    "verified": True,
                    "evidence_refs": [{"evidence_id": "ev-001"}],
                }
            ]
        }
        evidence_index = {"ev-001": {"source_type": "TB"}}

        result, findings = run_evidence_qa(ir, evidence_index)
        assert result.passed is True
        assert result.check_name == "evidence_qa"

    def test_with_required_rules(self) -> None:
        """필수 규칙 포함 검사."""
        ir = {
            "sections": [
                {"type": "claim", "verified": False, "evidence_refs": []},
            ]
        }
        result, findings = run_evidence_qa(
            ir,
            {},
            required_rules={"claim": 1},
        )

        # verified=False라 MISSING ERROR 없고,
        # required_rules로 WARNING 발생
        assert result.warning_count >= 1
