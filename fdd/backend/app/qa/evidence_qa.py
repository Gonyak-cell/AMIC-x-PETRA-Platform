"""Evidence QA — 누락/깨짐 검증 — FDD-1604.

Report IR 내 Evidence 참조 검증.
순수 함수만 포함. DB 접근 금지.
"""

from __future__ import annotations

import time
from typing import Any

from app.qa.types import (
    QACheckType,
    QAFinding,
    QAResult,
    QASeverity,
    create_result_from_findings,
)
from app.qa.utils import build_location_path

EVIDENCE_QA_VERSION = "0.1.0"


def check_ir_evidence_coverage(
    ir_dict: dict[str, Any],
    evidence_index: dict[str, Any],
) -> list[QAFinding]:
    """IR 블록 내 evidence_refs 참조 검증.

    Args:
        ir_dict: Report IR 딕셔너리
        evidence_index: Evidence ID → 상세 정보 맵

    Returns:
        발견 목록
    """
    findings: list[QAFinding] = []

    sections = ir_dict.get("sections", [])
    for idx, section in enumerate(sections):
        block_type = section.get("type", "unknown")
        block_title = section.get("title", f"section_{idx}")
        location_prefix = f"section.{idx}/{block_type}"

        # ClaimBlock: evidence_refs 필수
        if block_type == "claim":
            verified = section.get("verified", False)
            evidence_refs = section.get("evidence_refs", [])

            if verified and not evidence_refs:
                # verified=True인데 evidence 없음
                findings.append(
                    QAFinding(
                        check_type=QACheckType.EVIDENCE_MISSING,
                        severity=QASeverity.ERROR,
                        location=location_prefix,
                        message="Verified claim has no evidence references",
                        expected="at least 1 evidence_ref",
                        actual="0 evidence_refs",
                    )
                )

            # 각 evidence_ref가 evidence_index에 있는지 확인
            for ref_idx, ref in enumerate(evidence_refs):
                evidence_id = ref.get("evidence_id", "")
                if evidence_id and evidence_id not in evidence_index:
                    findings.append(
                        QAFinding(
                            check_type=QACheckType.EVIDENCE_BROKEN,
                            severity=QASeverity.ERROR,
                            location=f"{location_prefix}/evidence_refs.{ref_idx}",
                            message=f"Evidence ID not found in index: {evidence_id}",
                            expected="valid evidence_id",
                            actual=evidence_id,
                            evidence_id=evidence_id,
                        )
                    )
                elif evidence_id:
                    # 유효한 참조 - INFO로 기록
                    findings.append(
                        QAFinding(
                            check_type=QACheckType.EVIDENCE_MISSING,
                            severity=QASeverity.INFO,
                            location=f"{location_prefix}/evidence_refs.{ref_idx}",
                            message="Valid evidence reference",
                            evidence_id=evidence_id,
                        )
                    )

        # TableBlock: row 별 evidence (선택적 검사)
        elif block_type == "table":
            rows = section.get("rows", [])
            for row_idx, row in enumerate(rows):
                # separator 행은 건너뜀
                if row.get("row_style") == "separator":
                    continue

                evidence_ids = row.get("evidence_ids", [])
                # 테이블 행은 evidence 없어도 WARNING (선택적)
                # 여기서는 evidence_ids가 있으면 검증만 수행

                for eid in evidence_ids:
                    if eid not in evidence_index:
                        location = build_location_path(
                            location_prefix,
                            "rows",
                            row_index=row_idx,
                        )
                        findings.append(
                            QAFinding(
                                check_type=QACheckType.EVIDENCE_BROKEN,
                                severity=QASeverity.ERROR,
                                location=location,
                                message=f"Evidence ID not found: {eid}",
                                expected="valid evidence_id",
                                actual=eid,
                                evidence_id=eid,
                            )
                        )

        # IssueBlock: issue별 evidence (선택적)
        elif block_type == "issue":
            issues = section.get("issues", [])
            for issue_idx, issue in enumerate(issues):
                evidence_ids = issue.get("evidence_ids", [])
                for eid in evidence_ids:
                    if eid not in evidence_index:
                        location = f"{location_prefix}/issues.{issue_idx}"
                        findings.append(
                            QAFinding(
                                check_type=QACheckType.EVIDENCE_BROKEN,
                                severity=QASeverity.ERROR,
                                location=location,
                                message=f"Issue evidence not found: {eid}",
                                expected="valid evidence_id",
                                actual=eid,
                                evidence_id=eid,
                            )
                        )

    return findings


def check_required_evidence(
    ir_dict: dict[str, Any],
    required_evidence_rules: dict[str, int],
) -> list[QAFinding]:
    """필수 Evidence 존재 여부 검사.

    Args:
        ir_dict: Report IR 딕셔너리
        required_evidence_rules: {"claim": 1, "table_row": 0, ...} 형태

    Returns:
        발견 목록
    """
    findings: list[QAFinding] = []

    claim_min = required_evidence_rules.get("claim", 1)
    table_row_min = required_evidence_rules.get("table_row", 0)

    sections = ir_dict.get("sections", [])
    for idx, section in enumerate(sections):
        block_type = section.get("type", "unknown")
        location_prefix = f"section.{idx}/{block_type}"

        if block_type == "claim" and claim_min > 0:
            evidence_refs = section.get("evidence_refs", [])
            if len(evidence_refs) < claim_min:
                findings.append(
                    QAFinding(
                        check_type=QACheckType.EVIDENCE_MISSING,
                        severity=QASeverity.WARNING,
                        location=location_prefix,
                        message=f"Claim has fewer than {claim_min} evidence refs",
                        expected=f">= {claim_min}",
                        actual=str(len(evidence_refs)),
                    )
                )
            else:
                findings.append(
                    QAFinding(
                        check_type=QACheckType.EVIDENCE_MISSING,
                        severity=QASeverity.INFO,
                        location=location_prefix,
                        message="Claim evidence requirement met",
                        expected=f">= {claim_min}",
                        actual=str(len(evidence_refs)),
                    )
                )

        elif block_type == "table" and table_row_min > 0:
            rows = section.get("rows", [])
            for row_idx, row in enumerate(rows):
                if row.get("row_style") == "separator":
                    continue
                evidence_ids = row.get("evidence_ids", [])
                if len(evidence_ids) < table_row_min:
                    location = build_location_path(
                        location_prefix,
                        "rows",
                        row_index=row_idx,
                    )
                    findings.append(
                        QAFinding(
                            check_type=QACheckType.EVIDENCE_MISSING,
                            severity=QASeverity.WARNING,
                            location=location,
                            message="Table row missing required evidence",
                            expected=f">= {table_row_min}",
                            actual=str(len(evidence_ids)),
                        )
                    )

    return findings


def check_db_evidence_integrity(
    evidence_links: list[dict[str, Any]],
) -> list[QAFinding]:
    """DB EvidenceLink 무결성 검사.

    Args:
        evidence_links: DB에서 조회한 EvidenceLink 목록

    Returns:
        발견 목록
    """
    findings: list[QAFinding] = []

    for link in evidence_links:
        link_id = link.get("id", "unknown")
        target_type = link.get("target_type")
        target_id = link.get("target_id")
        source_type = link.get("source_type")
        source_id = link.get("source_id")

        # 필수 필드 검사
        if not target_type or not target_id:
            findings.append(
                QAFinding(
                    check_type=QACheckType.EVIDENCE_BROKEN,
                    severity=QASeverity.ERROR,
                    location=f"evidence_link/{link_id}",
                    message="Missing target_type or target_id",
                    expected="non-empty target",
                    actual=f"target_type={target_type}, target_id={target_id}",
                )
            )

        if not source_type or not source_id:
            findings.append(
                QAFinding(
                    check_type=QACheckType.EVIDENCE_BROKEN,
                    severity=QASeverity.ERROR,
                    location=f"evidence_link/{link_id}",
                    message="Missing source_type or source_id",
                    expected="non-empty source",
                    actual=f"source_type={source_type}, source_id={source_id}",
                )
            )

    return findings


def run_evidence_qa(
    ir_dict: dict[str, Any],
    evidence_index: dict[str, Any],
    required_rules: dict[str, int] | None = None,
) -> tuple[QAResult, list[QAFinding]]:
    """Evidence QA 전체 실행.

    Args:
        ir_dict: Report IR 딕셔너리
        evidence_index: Evidence ID → 상세 정보 맵
        required_rules: 필수 evidence 규칙 (선택)

    Returns:
        (QAResult, findings 목록)
    """
    start_time = time.perf_counter()
    findings: list[QAFinding] = []

    # IR 내 evidence 참조 검증
    coverage_findings = check_ir_evidence_coverage(ir_dict, evidence_index)
    findings.extend(coverage_findings)

    # 필수 evidence 규칙 검사
    if required_rules:
        required_findings = check_required_evidence(ir_dict, required_rules)
        findings.extend(required_findings)

    duration_ms = (time.perf_counter() - start_time) * 1000
    result = create_result_from_findings("evidence_qa", findings, duration_ms)

    return result, findings
