"""Layout QA — placeholder/overflow 검증 — FDD-1603.

Report IR 내 미치환 placeholder 및 오버플로우 검출.
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
from app.qa.utils import (
    CELL_OVERFLOW_LIMIT,
    TEXT_OVERFLOW_LIMIT,
    build_location_path,
    find_placeholders,
)

LAYOUT_QA_VERSION = "0.1.0"


def check_unsubstituted_placeholders(
    ir_dict: dict[str, Any],
) -> list[QAFinding]:
    """IR 내 미치환 placeholder 검출.

    Args:
        ir_dict: Report IR 딕셔너리

    Returns:
        발견 목록
    """
    findings: list[QAFinding] = []

    sections = ir_dict.get("sections", [])
    for idx, section in enumerate(sections):
        block_type = section.get("type", "unknown")
        block_title = section.get("title", f"section_{idx}")
        location_prefix = f"section.{idx}/{block_type}"

        # 텍스트 필드 검사
        text_fields = _extract_text_fields(section)
        for field_name, text in text_fields:
            if not text or not isinstance(text, str):
                continue

            placeholders = find_placeholders(text)
            for full_match, var_name in placeholders:
                location = build_location_path(location_prefix, field_name)
                findings.append(
                    QAFinding(
                        check_type=QACheckType.PLACEHOLDER_MISSING,
                        severity=QASeverity.WARNING,
                        location=location,
                        message=f"Unsubstituted placeholder: {full_match}",
                        expected="(substituted value)",
                        actual=full_match,
                        context={"variable_name": var_name},
                    )
                )

        # 테이블 행 내 placeholder 검사
        if block_type == "table":
            rows = section.get("rows", [])
            for row_idx, row in enumerate(rows):
                for key, value in row.items():
                    if not value or not isinstance(value, str):
                        continue
                    placeholders = find_placeholders(value)
                    for full_match, var_name in placeholders:
                        location = build_location_path(
                            location_prefix,
                            "rows",
                            row_index=row_idx,
                            col_key=key,
                        )
                        findings.append(
                            QAFinding(
                                check_type=QACheckType.PLACEHOLDER_MISSING,
                                severity=QASeverity.WARNING,
                                location=location,
                                message=f"Unsubstituted placeholder in table: {full_match}",
                                expected="(substituted value)",
                                actual=full_match,
                                context={"variable_name": var_name},
                            )
                        )

    return findings


def check_text_overflow(
    ir_dict: dict[str, Any],
    text_limit: int = TEXT_OVERFLOW_LIMIT,
    cell_limit: int = CELL_OVERFLOW_LIMIT,
) -> list[QAFinding]:
    """TextBlock/TableCell 오버플로우 검출.

    Args:
        ir_dict: Report IR 딕셔너리
        text_limit: 텍스트 블록 최대 글자 수
        cell_limit: 테이블 셀 최대 글자 수

    Returns:
        발견 목록
    """
    findings: list[QAFinding] = []

    sections = ir_dict.get("sections", [])
    for idx, section in enumerate(sections):
        block_type = section.get("type", "unknown")
        location_prefix = f"section.{idx}/{block_type}"

        # Text 블록 오버플로우
        if block_type == "text":
            content = section.get("content", "")
            if isinstance(content, str) and len(content) > text_limit:
                findings.append(
                    QAFinding(
                        check_type=QACheckType.TEXT_OVERFLOW,
                        severity=QASeverity.WARNING,
                        location=f"{location_prefix}/content",
                        message=f"Text overflow: {len(content)} chars (limit: {text_limit})",
                        expected=f"<= {text_limit} chars",
                        actual=f"{len(content)} chars",
                    )
                )

        # Claim 블록 오버플로우
        elif block_type == "claim":
            claim_text = section.get("claim_text", "")
            if isinstance(claim_text, str) and len(claim_text) > text_limit:
                findings.append(
                    QAFinding(
                        check_type=QACheckType.TEXT_OVERFLOW,
                        severity=QASeverity.WARNING,
                        location=f"{location_prefix}/claim_text",
                        message=f"Claim text overflow: {len(claim_text)} chars",
                        expected=f"<= {text_limit} chars",
                        actual=f"{len(claim_text)} chars",
                    )
                )

        # Table 블록 셀 오버플로우
        elif block_type == "table":
            rows = section.get("rows", [])
            for row_idx, row in enumerate(rows):
                for key, value in row.items():
                    if not isinstance(value, str):
                        continue
                    if len(value) > cell_limit:
                        location = build_location_path(
                            location_prefix,
                            "rows",
                            row_index=row_idx,
                            col_key=key,
                        )
                        findings.append(
                            QAFinding(
                                check_type=QACheckType.TEXT_OVERFLOW,
                                severity=QASeverity.WARNING,
                                location=location,
                                message=f"Cell overflow: {len(value)} chars",
                                expected=f"<= {cell_limit} chars",
                                actual=f"{len(value)} chars",
                            )
                        )

    return findings


def _extract_text_fields(section: dict[str, Any]) -> list[tuple[str, Any]]:
    """섹션에서 텍스트 필드 추출.

    Args:
        section: 섹션 딕셔너리

    Returns:
        [(필드명, 값), ...] 목록
    """
    text_field_names = [
        "title",
        "content",
        "claim_text",
        "description",
        "deal_name",
        "target_name",
        "prepared_by",
        "confidentiality",
        "introduction",
        "date",  # cover block date (문자열일 경우)
    ]
    results = []
    for field_name in text_field_names:
        if field_name in section:
            results.append((field_name, section[field_name]))

    # issues 내 텍스트
    for issue_idx, issue in enumerate(section.get("issues", [])):
        if "title" in issue:
            results.append((f"issues.{issue_idx}.title", issue["title"]))
        if "description" in issue:
            results.append((f"issues.{issue_idx}.description", issue["description"]))

    # steps 내 텍스트 (methodology)
    for step_idx, step in enumerate(section.get("steps", [])):
        if "title" in step:
            results.append((f"steps.{step_idx}.title", step["title"]))
        if "description" in step:
            results.append((f"steps.{step_idx}.description", step["description"]))

    return results


def _check_metadata_placeholders(ir_dict: dict[str, Any]) -> list[QAFinding]:
    """metadata 내 placeholder 검사.

    Args:
        ir_dict: Report IR 딕셔너리

    Returns:
        발견 목록
    """
    findings: list[QAFinding] = []
    metadata = ir_dict.get("metadata", {})

    for field_name, value in metadata.items():
        if not value or not isinstance(value, str):
            continue
        placeholders = find_placeholders(value)
        for full_match, var_name in placeholders:
            findings.append(
                QAFinding(
                    check_type=QACheckType.PLACEHOLDER_MISSING,
                    severity=QASeverity.WARNING,
                    location=f"metadata/{field_name}",
                    message=f"Unsubstituted placeholder in metadata: {full_match}",
                    expected="(substituted value)",
                    actual=full_match,
                    context={"variable_name": var_name},
                )
            )
    return findings


def run_layout_qa(
    ir_dict: dict[str, Any],
    text_limit: int = TEXT_OVERFLOW_LIMIT,
    cell_limit: int = CELL_OVERFLOW_LIMIT,
) -> tuple[QAResult, list[QAFinding]]:
    """Layout QA 전체 실행.

    Args:
        ir_dict: Report IR 딕셔너리
        text_limit: 텍스트 블록 최대 글자 수
        cell_limit: 테이블 셀 최대 글자 수

    Returns:
        (QAResult, findings 목록)
    """
    start_time = time.perf_counter()
    findings: list[QAFinding] = []

    # Metadata placeholder 검사
    metadata_findings = _check_metadata_placeholders(ir_dict)
    findings.extend(metadata_findings)

    # Placeholder 검사
    placeholder_findings = check_unsubstituted_placeholders(ir_dict)
    findings.extend(placeholder_findings)

    # Overflow 검사
    overflow_findings = check_text_overflow(ir_dict, text_limit, cell_limit)
    findings.extend(overflow_findings)

    duration_ms = (time.perf_counter() - start_time) * 1000
    result = create_result_from_findings("layout_qa", findings, duration_ms)

    return result, findings
