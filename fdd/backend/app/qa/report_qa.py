"""Report IR 수치 검증 — FDD-1602.

Report IR의 TableBlock 수치를 골든 데이터와 비교합니다.
순수 함수만 포함. DB 접근 금지.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

from app.qa.types import (
    QACheckType,
    QAFinding,
    QAResult,
    QASeverity,
    create_result_from_findings,
)
from app.qa.utils import (
    DEFAULT_NUMERIC_TOLERANCE,
    build_location_path,
    format_decimal_diff,
    safe_decimal,
)

REPORT_QA_VERSION = "0.1.0"


def compare_numeric_values(
    expected: Decimal | str | None,
    actual: Decimal | str | None,
    tolerance: Decimal = DEFAULT_NUMERIC_TOLERANCE,
) -> tuple[bool, Decimal | None, Decimal | None]:
    """두 수치 비교.

    Args:
        expected: 예상 값
        actual: 실제 값
        tolerance: 허용 오차

    Returns:
        (일치 여부, 예상 Decimal, 실제 Decimal)
    """
    exp = safe_decimal(expected)
    act = safe_decimal(actual)

    if exp is None and act is None:
        return True, None, None
    if exp is None or act is None:
        return False, exp, act

    match = abs(exp - act) <= tolerance
    return match, exp, act


def compare_table_rows(
    expected_rows: list[dict[str, Any]],
    actual_rows: list[dict[str, Any]],
    numeric_keys: list[str],
    location_prefix: str,
    tolerance: Decimal = DEFAULT_NUMERIC_TOLERANCE,
) -> list[QAFinding]:
    """테이블 행 단위 비교.

    Args:
        expected_rows: 예상 행 목록
        actual_rows: 실제 행 목록
        numeric_keys: 수치 비교할 컬럼 키 목록
        location_prefix: 위치 경로 접두사
        tolerance: 허용 오차

    Returns:
        발견 목록
    """
    findings: list[QAFinding] = []

    # 행 개수 비교
    if len(expected_rows) != len(actual_rows):
        findings.append(
            QAFinding(
                check_type=QACheckType.STRUCTURE_MISMATCH,
                severity=QASeverity.ERROR,
                location=location_prefix,
                message="Row count mismatch",
                expected=str(len(expected_rows)),
                actual=str(len(actual_rows)),
            )
        )
        # 행 개수가 다르면 최소 개수만큼 비교
        min_rows = min(len(expected_rows), len(actual_rows))
    else:
        min_rows = len(expected_rows)

    # 각 행 비교
    for row_idx in range(min_rows):
        exp_row = expected_rows[row_idx]
        act_row = actual_rows[row_idx]

        for key in numeric_keys:
            exp_val = exp_row.get(key)
            act_val = act_row.get(key)

            location = build_location_path(
                location_prefix,
                row_index=row_idx,
                col_key=key,
            )

            match, exp_dec, act_dec = compare_numeric_values(
                exp_val, act_val, tolerance
            )

            if match:
                # 통과 항목도 INFO로 기록
                findings.append(
                    QAFinding(
                        check_type=QACheckType.NUMERIC_DIFF,
                        severity=QASeverity.INFO,
                        location=location,
                        message="Match",
                        expected=str(exp_dec) if exp_dec else None,
                        actual=str(act_dec) if act_dec else None,
                    )
                )
            else:
                # 불일치
                if exp_dec is not None and act_dec is not None:
                    message = format_decimal_diff(exp_dec, act_dec)
                else:
                    message = f"Value mismatch: expected {exp_val}, got {act_val}"

                findings.append(
                    QAFinding(
                        check_type=QACheckType.NUMERIC_DIFF,
                        severity=QASeverity.ERROR,
                        location=location,
                        message=message,
                        expected=str(exp_val),
                        actual=str(act_val),
                    )
                )

    return findings


def compare_table_block(
    expected_block: dict[str, Any],
    actual_block: dict[str, Any],
    block_name: str,
    numeric_keys: list[str] | None = None,
    tolerance: Decimal = DEFAULT_NUMERIC_TOLERANCE,
) -> list[QAFinding]:
    """단일 TableBlock 비교.

    Args:
        expected_block: 예상 블록 딕셔너리
        actual_block: 실제 블록 딕셔너리
        block_name: 블록 이름 (위치 경로용)
        numeric_keys: 비교할 수치 컬럼 키 (None이면 자동 감지)
        tolerance: 허용 오차

    Returns:
        발견 목록
    """
    findings: list[QAFinding] = []
    location_prefix = f"block.{block_name}"

    # rows 비교
    exp_rows = expected_block.get("rows", [])
    act_rows = actual_block.get("rows", [])

    # numeric_keys 자동 감지
    if numeric_keys is None and exp_rows:
        numeric_keys = _detect_numeric_keys(exp_rows[0])

    if numeric_keys:
        row_findings = compare_table_rows(
            exp_rows,
            act_rows,
            numeric_keys,
            f"{location_prefix}/rows",
            tolerance,
        )
        findings.extend(row_findings)

    # footer_rows 비교
    exp_footer = expected_block.get("footer_rows", [])
    act_footer = actual_block.get("footer_rows", [])

    if exp_footer or act_footer:
        if numeric_keys is None and exp_footer:
            numeric_keys = _detect_numeric_keys(exp_footer[0])

        if numeric_keys:
            footer_findings = compare_table_rows(
                exp_footer,
                act_footer,
                numeric_keys,
                f"{location_prefix}/footer",
                tolerance,
            )
            findings.extend(footer_findings)

    return findings


def _detect_numeric_keys(row: dict[str, Any]) -> list[str]:
    """행에서 수치 키 자동 감지.

    Args:
        row: 샘플 행

    Returns:
        수치 필드 키 목록
    """
    numeric_keys = []
    for key, value in row.items():
        if value is None:
            continue
        if isinstance(value, (int, float, Decimal)):
            numeric_keys.append(key)
        elif isinstance(value, str):
            # 쉼표 제거 후 숫자인지 확인
            cleaned = value.replace(",", "").replace(" ", "").strip()
            if cleaned.lstrip("-").replace(".", "", 1).isdigit():
                numeric_keys.append(key)
    return numeric_keys


def compare_report_ir(
    expected_ir: dict[str, Any],
    actual_ir: dict[str, Any],
    numeric_keys_map: dict[str, list[str]] | None = None,
    tolerance: Decimal = DEFAULT_NUMERIC_TOLERANCE,
) -> tuple[QAResult, list[QAFinding]]:
    """Report IR 전체 비교.

    Args:
        expected_ir: 예상 Report IR dict
        actual_ir: 실제 Report IR dict
        numeric_keys_map: 블록별 수치 키 맵 (None이면 자동 감지)
        tolerance: 허용 오차

    Returns:
        (QAResult, findings 목록)
    """
    start_time = time.perf_counter()
    findings: list[QAFinding] = []

    # metadata 비교 (deal_id 일치 확인)
    exp_meta = expected_ir.get("metadata", {})
    act_meta = actual_ir.get("metadata", {})

    if exp_meta.get("deal_id") != act_meta.get("deal_id"):
        findings.append(
            QAFinding(
                check_type=QACheckType.STRUCTURE_MISMATCH,
                severity=QASeverity.WARNING,
                location="metadata/deal_id",
                message="Deal ID mismatch",
                expected=exp_meta.get("deal_id"),
                actual=act_meta.get("deal_id"),
            )
        )

    # sections 비교
    exp_sections = expected_ir.get("sections", [])
    act_sections = actual_ir.get("sections", [])

    if len(exp_sections) != len(act_sections):
        findings.append(
            QAFinding(
                check_type=QACheckType.STRUCTURE_MISMATCH,
                severity=QASeverity.ERROR,
                location="sections",
                message="Section count mismatch",
                expected=str(len(exp_sections)),
                actual=str(len(act_sections)),
            )
        )

    # 각 섹션(블록) 비교
    section_map = _build_section_map(act_sections)

    for idx, exp_section in enumerate(exp_sections):
        block_type = exp_section.get("type", "unknown")
        block_title = exp_section.get("title", f"section_{idx}")
        block_key = f"{block_type}:{block_title}"

        act_section = section_map.get(block_key)
        if act_section is None:
            # 동일 타입/제목의 섹션 없음
            findings.append(
                QAFinding(
                    check_type=QACheckType.STRUCTURE_MISMATCH,
                    severity=QASeverity.ERROR,
                    location=f"section.{idx}",
                    message=f"Missing section: {block_key}",
                    expected=block_key,
                    actual=None,
                )
            )
            continue

        # TableBlock만 상세 비교
        if block_type == "table":
            numeric_keys = None
            if numeric_keys_map and block_title in numeric_keys_map:
                numeric_keys = numeric_keys_map[block_title]

            block_findings = compare_table_block(
                exp_section,
                act_section,
                block_title,
                numeric_keys,
                tolerance,
            )
            findings.extend(block_findings)

    duration_ms = (time.perf_counter() - start_time) * 1000
    result = create_result_from_findings("report_numeric_diff", findings, duration_ms)

    return result, findings


def _build_section_map(sections: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """섹션 목록을 타입:제목 키로 인덱싱.

    Args:
        sections: 섹션 목록

    Returns:
        {type:title -> section} 맵
    """
    section_map: dict[str, dict[str, Any]] = {}
    for idx, section in enumerate(sections):
        block_type = section.get("type", "unknown")
        block_title = section.get("title", f"section_{idx}")
        key = f"{block_type}:{block_title}"
        section_map[key] = section
    return section_map


def run_report_qa(
    expected_ir: dict[str, Any],
    actual_ir: dict[str, Any],
    tolerance: Decimal = DEFAULT_NUMERIC_TOLERANCE,
) -> tuple[QAResult, list[QAFinding]]:
    """Report QA 전체 실행.

    compare_report_ir의 래퍼 함수.

    Args:
        expected_ir: 예상 Report IR
        actual_ir: 실제 Report IR
        tolerance: 허용 오차

    Returns:
        (QAResult, findings 목록)
    """
    return compare_report_ir(expected_ir, actual_ir, tolerance=tolerance)
