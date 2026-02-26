"""ReportValidationEngine — WP 교차검증.

Report IR 섹션 간 수치 정합성을 검증한다.
순수 함수만 포함. DB 접근 금지.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.qa.types import (
    QACheckType,
    QAFinding,
    QAResult,
    QASeverity,
    create_result_from_findings,
)
from app.qa.utils import DEFAULT_NUMERIC_TOLERANCE, safe_decimal

VALIDATION_VERSION = "0.1.0"

# ── 허용 오차 ──────────────────────────────────────────────
# 교차검증에는 일반 QA보다 넓은 오차 허용 (반올림 차이 감안)
CROSS_TOLERANCE = Decimal("1.00")


@dataclass(frozen=True)
class ValidationRule:
    """교차검증 규칙 정의."""

    rule_id: str
    title_ko: str
    title_en: str
    severity: QASeverity = QASeverity.ERROR


@dataclass
class ValidationResult:
    """검증 결과."""

    rule_id: str
    passed: bool
    message: str
    expected: str | None = None
    actual: str | None = None
    severity: QASeverity = QASeverity.ERROR


# ── 교차검증 규칙 카탈로그 ──────────────────────────────────
RULES: dict[str, ValidationRule] = {
    "IS_QOE_REVENUE": ValidationRule(
        "IS_QOE_REVENUE",
        "IS 매출 = QoE Bridge 매출",
        "IS Revenue == QoE Bridge Revenue",
    ),
    "QOE_EBITDA_BRIDGE": ValidationRule(
        "QOE_EBITDA_BRIDGE",
        "Adjusted EBITDA = Reported + 조정합계",
        "Adjusted EBITDA == Reported + Total Adjustments",
    ),
    "DEBT_NET": ValidationRule(
        "DEBT_NET",
        "순차입금 = 총차입금 - 현금",
        "Net Debt == Total Debt - Cash",
    ),
    "REVENUE_BREAKDOWN_TOTAL": ValidationRule(
        "REVENUE_BREAKDOWN_TOTAL",
        "매출 breakdown 합계 = IS 매출",
        "Revenue breakdown total == IS Revenue",
        QASeverity.WARNING,
    ),
    "FCF_BRIDGE_MATH": ValidationRule(
        "FCF_BRIDGE_MATH",
        "FCF = OCF - CAPEX",
        "FCF == Operating CF - Total CAPEX",
    ),
    "COMMENTARY_DIRECTION": ValidationRule(
        "COMMENTARY_DIRECTION",
        "코멘터리 방향 ↔ 실제 YoY 일치",
        "Commentary direction matches actual YoY",
        QASeverity.WARNING,
    ),
}


# ── 헬퍼 함수 ─────────────────────────────────────────────

def _extract_value_from_sections(
    sections: list[dict[str, Any]],
    block_title_pattern: str,
    row_label_pattern: str,
    value_key: str = "amount",
) -> Decimal | None:
    """Report IR 섹션에서 특정 블록/행의 수치를 추출한다."""
    for section in sections:
        title = section.get("title", "")
        if not re.search(block_title_pattern, title, re.IGNORECASE):
            continue

        for row in section.get("rows", []):
            label = row.get("label", row.get("label_ko", ""))
            if re.search(row_label_pattern, label, re.IGNORECASE):
                val = row.get(value_key)
                if val is not None:
                    return safe_decimal(val)

        # footer_rows 도 검색
        for row in section.get("footer_rows", []):
            label = row.get("label", row.get("label_ko", ""))
            if re.search(row_label_pattern, label, re.IGNORECASE):
                val = row.get(value_key)
                if val is not None:
                    return safe_decimal(val)

    return None


def _extract_footer_value(
    sections: list[dict[str, Any]],
    block_title_pattern: str,
    footer_label_pattern: str,
    value_key: str = "amount",
) -> Decimal | None:
    """Footer에서 수치 추출."""
    for section in sections:
        title = section.get("title", "")
        if not re.search(block_title_pattern, title, re.IGNORECASE):
            continue
        for row in section.get("footer_rows", []):
            label = row.get("label", row.get("label_ko", ""))
            if re.search(footer_label_pattern, label, re.IGNORECASE):
                val = row.get(value_key)
                if val is not None:
                    return safe_decimal(val)
    return None


def _values_match(
    a: Decimal | None,
    b: Decimal | None,
    tolerance: Decimal = CROSS_TOLERANCE,
) -> bool:
    """두 Decimal 값이 허용 오차 내에서 일치하는지 확인."""
    if a is None or b is None:
        return False
    return abs(a - b) <= tolerance


# ── 개별 검증 함수 ─────────────────────────────────────────

def validate_is_qoe_revenue(
    sections: list[dict[str, Any]],
    tolerance: Decimal = CROSS_TOLERANCE,
) -> ValidationResult:
    """IS 매출 == QoE Bridge 매출."""
    is_revenue = _extract_value_from_sections(
        sections, r"IS|손익계산서|Income Statement", r"매출액|Revenue|매출"
    )
    qoe_revenue = _extract_value_from_sections(
        sections, r"QoE Bridge", r"매출|Revenue|Reported Revenue"
    )

    if is_revenue is None or qoe_revenue is None:
        return ValidationResult(
            rule_id="IS_QOE_REVENUE",
            passed=True,  # 데이터 부재 시 스킵
            message="데이터 부재로 검증 스킵",
            severity=QASeverity.INFO,
        )

    passed = _values_match(is_revenue, qoe_revenue, tolerance)
    return ValidationResult(
        rule_id="IS_QOE_REVENUE",
        passed=passed,
        message="IS 매출 = QoE Bridge 매출" if passed else "IS 매출 ≠ QoE Bridge 매출",
        expected=str(is_revenue),
        actual=str(qoe_revenue),
    )


def validate_qoe_ebitda_bridge(
    sections: list[dict[str, Any]],
    tolerance: Decimal = CROSS_TOLERANCE,
) -> ValidationResult:
    """Adjusted EBITDA == Reported + Total Adjustments."""
    reported = _extract_value_from_sections(
        sections, r"QoE Bridge", r"Reported.*EBITDA|보고.*EBITDA"
    )
    adjustments = _extract_value_from_sections(
        sections, r"QoE Bridge", r"Total.*Adjust|조정.*합계|순조정"
    )
    adjusted = _extract_value_from_sections(
        sections, r"QoE Bridge", r"Adjusted.*EBITDA|조정.*EBITDA"
    )

    if reported is None or adjusted is None:
        return ValidationResult(
            rule_id="QOE_EBITDA_BRIDGE",
            passed=True,
            message="데이터 부재로 검증 스킵",
            severity=QASeverity.INFO,
        )

    adj_total = adjustments if adjustments is not None else Decimal("0")
    expected_adjusted = reported + adj_total

    passed = _values_match(expected_adjusted, adjusted, tolerance)
    return ValidationResult(
        rule_id="QOE_EBITDA_BRIDGE",
        passed=passed,
        message="EBITDA Bridge 정합" if passed else "EBITDA Bridge 불일치",
        expected=str(expected_adjusted),
        actual=str(adjusted),
    )


def validate_debt_net(
    sections: list[dict[str, Any]],
    tolerance: Decimal = CROSS_TOLERANCE,
) -> ValidationResult:
    """Net Debt == Total Debt - Cash."""
    total_debt = _extract_value_from_sections(
        sections, r"Net Debt|Debt Schedule|순차입금",
        r"Total.*Debt|차입금.*합계|총차입금"
    )
    cash = _extract_value_from_sections(
        sections, r"Net Debt|Debt Schedule|순차입금",
        r"Cash|현금|현금성"
    )
    net_debt = _extract_value_from_sections(
        sections, r"Net Debt|Debt Schedule|순차입금",
        r"Net Debt|순차입금"
    )

    if total_debt is None or cash is None or net_debt is None:
        return ValidationResult(
            rule_id="DEBT_NET",
            passed=True,
            message="데이터 부재로 검증 스킵",
            severity=QASeverity.INFO,
        )

    expected_net = total_debt - cash
    passed = _values_match(expected_net, net_debt, tolerance)
    return ValidationResult(
        rule_id="DEBT_NET",
        passed=passed,
        message="Net Debt 정합" if passed else "Net Debt 불일치",
        expected=str(expected_net),
        actual=str(net_debt),
    )


def validate_fcf_bridge_math(
    sections: list[dict[str, Any]],
    tolerance: Decimal = CROSS_TOLERANCE,
) -> ValidationResult:
    """FCF == OCF - CAPEX."""
    ocf = _extract_value_from_sections(
        sections, r"FCF Bridge", r"Operating.*Cash|영업.*현금|OCF"
    )
    capex = _extract_value_from_sections(
        sections, r"FCF Bridge", r"Total.*CAPEX|CAPEX.*합계|총.*CAPEX"
    )
    fcf = _extract_value_from_sections(
        sections, r"FCF Bridge", r"Free Cash Flow|FCF|잉여현금"
    )

    if ocf is None or capex is None or fcf is None:
        return ValidationResult(
            rule_id="FCF_BRIDGE_MATH",
            passed=True,
            message="데이터 부재로 검증 스킵",
            severity=QASeverity.INFO,
        )

    expected_fcf = ocf - capex
    passed = _values_match(expected_fcf, fcf, tolerance)
    return ValidationResult(
        rule_id="FCF_BRIDGE_MATH",
        passed=passed,
        message="FCF Bridge 정합" if passed else "FCF Bridge 불일치",
        expected=str(expected_fcf),
        actual=str(fcf),
    )


def validate_revenue_breakdown_total(
    sections: list[dict[str, Any]],
    tolerance: Decimal = CROSS_TOLERANCE,
) -> ValidationResult:
    """매출 breakdown 합계 == IS 매출."""
    is_revenue = _extract_value_from_sections(
        sections, r"IS|손익계산서|Income Statement", r"매출액|Revenue"
    )
    breakdown_total = _extract_footer_value(
        sections, r"거래처별|Revenue by Customer|매출.*Customer",
        r"합계|Total|전체"
    )

    if is_revenue is None or breakdown_total is None:
        return ValidationResult(
            rule_id="REVENUE_BREAKDOWN_TOTAL",
            passed=True,
            message="데이터 부재로 검증 스킵",
            severity=QASeverity.INFO,
        )

    passed = _values_match(is_revenue, breakdown_total, tolerance)
    return ValidationResult(
        rule_id="REVENUE_BREAKDOWN_TOTAL",
        passed=passed,
        message="매출 breakdown 합계 일치" if passed else "매출 breakdown 합계 불일치",
        expected=str(is_revenue),
        actual=str(breakdown_total),
        severity=RULES["REVENUE_BREAKDOWN_TOTAL"].severity,
    )


def validate_commentary_direction(
    commentary_text: str,
    metric_name: str,
    actual_yoy: Decimal,
) -> ValidationResult:
    """코멘터리 내 증가/감소 표현이 실제 YoY 방향과 일치하는지 확인."""
    increase_words = {"증가", "상승", "성장", "개선", "확대", "increase", "grew", "improved"}
    decrease_words = {"감소", "하락", "축소", "악화", "위축", "decrease", "declined", "deteriorated"}

    text_lower = commentary_text.lower()
    mentions_increase = any(w in text_lower for w in increase_words)
    mentions_decrease = any(w in text_lower for w in decrease_words)

    if not mentions_increase and not mentions_decrease:
        return ValidationResult(
            rule_id="COMMENTARY_DIRECTION",
            passed=True,
            message="방향 표현 없음 (스킵)",
            severity=QASeverity.INFO,
        )

    actual_direction = "increase" if actual_yoy > Decimal("0") else "decrease"
    commentary_direction = "increase" if mentions_increase and not mentions_decrease else "decrease"

    passed = actual_direction == commentary_direction
    return ValidationResult(
        rule_id="COMMENTARY_DIRECTION",
        passed=passed,
        message=f"{metric_name}: 코멘터리 방향 일치" if passed else f"{metric_name}: 코멘터리 방향 불일치",
        expected=actual_direction,
        actual=commentary_direction,
        severity=RULES["COMMENTARY_DIRECTION"].severity,
    )


# ── 메인 검증 오케스트레이터 ───────────────────────────────

def run_cross_validation(
    report_ir: dict[str, Any],
    tolerance: Decimal = CROSS_TOLERANCE,
) -> tuple[QAResult, list[QAFinding]]:
    """Report IR 전체 교차검증.

    Args:
        report_ir: Report IR 딕셔너리
        tolerance: 허용 오차

    Returns:
        (QAResult, findings 목록)
    """
    start_time = time.perf_counter()
    findings: list[QAFinding] = []
    sections = report_ir.get("sections", [])

    # 검증 함수 목록
    validators = [
        validate_is_qoe_revenue,
        validate_qoe_ebitda_bridge,
        validate_debt_net,
        validate_fcf_bridge_math,
        validate_revenue_breakdown_total,
    ]

    for validator in validators:
        result = validator(sections, tolerance)
        rule = RULES.get(result.rule_id)
        severity = result.severity if not result.passed else QASeverity.INFO

        findings.append(
            QAFinding(
                check_type=QACheckType.NUMERIC_DIFF,
                severity=severity,
                location=f"cross_validation/{result.rule_id}",
                message=result.message,
                expected=result.expected,
                actual=result.actual,
            )
        )

    duration_ms = (time.perf_counter() - start_time) * 1000
    qa_result = create_result_from_findings(
        "cross_validation", findings, duration_ms
    )
    return qa_result, findings


def run_full_validation(
    report_ir: dict[str, Any],
    tolerance: Decimal = CROSS_TOLERANCE,
) -> dict[str, Any]:
    """전체 검증 실행 + 요약 반환.

    Args:
        report_ir: Report IR 딕셔너리
        tolerance: 허용 오차

    Returns:
        검증 결과 요약 딕셔너리
    """
    qa_result, findings = run_cross_validation(report_ir, tolerance)

    passed_rules = [f for f in findings if f.severity == QASeverity.INFO]
    warning_rules = [f for f in findings if f.severity == QASeverity.WARNING]
    error_rules = [f for f in findings if f.severity == QASeverity.ERROR]

    return {
        "version": VALIDATION_VERSION,
        "overall_passed": qa_result.passed,
        "total_rules": len(findings),
        "passed": len(passed_rules),
        "warnings": len(warning_rules),
        "errors": len(error_rules),
        "rules": [
            {
                "rule_id": f.location.split("/")[-1],
                "status": "PASS" if f.severity == QASeverity.INFO else f.severity.name,
                "message": f.message,
                "expected": f.expected,
                "actual": f.actual,
            }
            for f in findings
        ],
        "qa_result": qa_result.to_dict(),
    }
