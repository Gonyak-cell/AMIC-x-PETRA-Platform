"""내부/외부 보고서 비교 검증 — FDD-1404.

내부용과 외부용 보고서를 비교하여 마스킹 적절성을 검증한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.services.masking.engine import DistributionMode


@dataclass
class ComparisonIssue:
    """비교 검증에서 발견된 문제."""

    severity: str  # "error" | "warning"
    location: str
    message: str
    detail: str | None = None


@dataclass
class ComparisonResult:
    """내부/외부 비교 결과."""

    internal_mode: str
    external_mode: str
    total_checks: int
    passed: int
    failed: int
    issues: list[ComparisonIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.failed == 0


def compare_reports(
    internal_ir: dict[str, Any],
    external_ir: dict[str, Any],
    external_mode: DistributionMode,
) -> ComparisonResult:
    """내부/외부 Report IR을 비교 검증한다."""
    issues: list[ComparisonIssue] = []
    total_checks = 0
    passed = 0

    # 1. 모드 표시 검증
    total_checks += 1
    if external_ir.get("distribution_mode") == external_mode.value:
        passed += 1
    else:
        issues.append(ComparisonIssue(
            severity="error",
            location="root.distribution_mode",
            message="외부 보고서에 배포 모드가 올바르게 표시되지 않음",
        ))

    # 2. 섹션별 비교
    int_sections = internal_ir.get("sections", [])
    ext_sections = external_ir.get("sections", [])

    total_checks += 1
    if len(int_sections) >= len(ext_sections):
        passed += 1
    else:
        issues.append(ComparisonIssue(
            severity="warning",
            location="sections",
            message="외부 보고서에 내부 보고서보다 많은 섹션이 포함됨",
        ))

    # 3. 블록별 금액 마스킹 검증
    for i, ext_section in enumerate(ext_sections):
        for j, ext_block in enumerate(ext_section.get("blocks", [])):
            location = f"sections[{i}].blocks[{j}]"
            block_type = ext_block.get("type", "")

            if block_type == "table":
                checks, pass_count, block_issues = _check_table_masking(
                    location, ext_block
                )
                total_checks += checks
                passed += pass_count
                issues.extend(block_issues)

            elif block_type == "kpi":
                total_checks += 1
                value = str(ext_block.get("value", ""))
                if _is_masked_value(value):
                    passed += 1
                else:
                    issues.append(ComparisonIssue(
                        severity="error",
                        location=f"{location}.value",
                        message="KPI 값이 마스킹되지 않음",
                        detail=f"value={value}",
                    ))

    return ComparisonResult(
        internal_mode=DistributionMode.INTERNAL.value,
        external_mode=external_mode.value,
        total_checks=total_checks,
        passed=passed,
        failed=total_checks - passed,
        issues=issues,
    )


def check_sensitive_data_leak(
    external_ir: dict[str, Any],
    sensitive_patterns: list[str] | None = None,
) -> list[ComparisonIssue]:
    """외부 보고서에서 민감정보 누출을 검사한다 — FDD-1405."""
    if sensitive_patterns is None:
        sensitive_patterns = []

    issues: list[ComparisonIssue] = []
    text_content = _extract_all_text(external_ir)

    for pattern in sensitive_patterns:
        for location, text in text_content:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(ComparisonIssue(
                    severity="error",
                    location=location,
                    message=f"민감정보 패턴 감지: {pattern}",
                    detail=f"matched in: {text[:100]}...",
                ))

    # 이메일 패턴 검사
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    for location, text in text_content:
        matches = re.findall(email_pattern, text)
        for match in matches:
            issues.append(ComparisonIssue(
                severity="error",
                location=location,
                message="이메일 주소 누출 감지",
                detail=f"email={match}",
            ))

    # 전화번호 패턴 검사 (한국)
    phone_pattern = r"0\d{1,2}[-)\s]?\d{3,4}[-\s]?\d{4}"
    for location, text in text_content:
        matches = re.findall(phone_pattern, text)
        for match in matches:
            issues.append(ComparisonIssue(
                severity="warning",
                location=location,
                message="전화번호 누출 가능성",
                detail=f"phone={match}",
            ))

    return issues


# ── Private helpers ───────────────────────────────────


def _check_table_masking(
    location: str, block: dict[str, Any]
) -> tuple[int, int, list[ComparisonIssue]]:
    """테이블 블록의 마스킹 상태를 검사한다."""
    checks = 0
    passed = 0
    issues: list[ComparisonIssue] = []

    for i, row in enumerate(block.get("rows", [])):
        cells = row if isinstance(row, list) else list(row.values()) if isinstance(row, dict) else []
        for j, cell in enumerate(cells):
            if isinstance(cell, (int, float)) and not isinstance(cell, bool):
                checks += 1
                issues.append(ComparisonIssue(
                    severity="warning",
                    location=f"{location}.rows[{i}][{j}]",
                    message="마스킹되지 않은 숫자 값 발견",
                    detail=f"value={cell}",
                ))

    if checks == 0:
        checks = 1
        passed = 1

    return checks, passed, issues


def _is_masked_value(value: str) -> bool:
    """값이 마스킹되었는지 확인한다."""
    masked_indicators = ["X", "[금액 숨김]", "[마스킹됨]", "K~", "M~", "B~"]
    return any(indicator in value for indicator in masked_indicators)


def _extract_all_text(data: Any, path: str = "root") -> list[tuple[str, str]]:
    """중첩 구조에서 모든 텍스트를 추출한다."""
    results: list[tuple[str, str]] = []

    if isinstance(data, str):
        results.append((path, data))
    elif isinstance(data, dict):
        for key, value in data.items():
            results.extend(_extract_all_text(value, f"{path}.{key}"))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            results.extend(_extract_all_text(item, f"{path}[{i}]"))

    return results
