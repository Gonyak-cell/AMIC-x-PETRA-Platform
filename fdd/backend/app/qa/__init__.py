"""QA 모듈 — Sprint 8.

보고서 품질 자동 검사 모듈:
  - types: 공통 타입 (QASeverity, QACheckType, QAFinding, QAResult)
  - report_qa: 수치 diff 검증 (FDD-1602)
  - layout_qa: placeholder/overflow 검증 (FDD-1603)
  - evidence_qa: Evidence 커버리지 검증 (FDD-1604)
  - performance_qa: 성능 SLA 측정 (FDD-1605)
  - utils: 공통 유틸리티
"""

from typing import Any

from app.qa.types import (
    QA_VERSION,
    QACheckType,
    QAFinding,
    QAResult,
    QASeverity,
    create_result_from_findings,
)

# Report QA (FDD-1602)
from app.qa.report_qa import (
    REPORT_QA_VERSION,
    compare_numeric_values,
    compare_report_ir,
    compare_table_block,
    compare_table_rows,
    run_report_qa,
)

# Layout QA (FDD-1603)
from app.qa.layout_qa import (
    LAYOUT_QA_VERSION,
    check_text_overflow,
    check_unsubstituted_placeholders,
    run_layout_qa,
)

# Evidence QA (FDD-1604)
from app.qa.evidence_qa import (
    EVIDENCE_QA_VERSION,
    check_db_evidence_integrity,
    check_ir_evidence_coverage,
    check_required_evidence,
    run_evidence_qa,
)

# Performance QA (FDD-1605)
from app.qa.performance_qa import (
    DEFAULT_SLAS,
    PERFORMANCE_QA_VERSION,
    PerformanceMeasurement,
    PerformanceReport,
    SLADefinition,
    measure_operation,
    run_performance_qa,
)

__all__ = [
    # Types
    "QA_VERSION",
    "QASeverity",
    "QACheckType",
    "QAFinding",
    "QAResult",
    "create_result_from_findings",
    # Report QA
    "REPORT_QA_VERSION",
    "compare_numeric_values",
    "compare_table_rows",
    "compare_table_block",
    "compare_report_ir",
    "run_report_qa",
    # Layout QA
    "LAYOUT_QA_VERSION",
    "check_unsubstituted_placeholders",
    "check_text_overflow",
    "run_layout_qa",
    # Evidence QA
    "EVIDENCE_QA_VERSION",
    "check_ir_evidence_coverage",
    "check_required_evidence",
    "check_db_evidence_integrity",
    "run_evidence_qa",
    # Performance QA
    "PERFORMANCE_QA_VERSION",
    "SLADefinition",
    "DEFAULT_SLAS",
    "PerformanceMeasurement",
    "PerformanceReport",
    "measure_operation",
    "run_performance_qa",
    # Orchestrator
    "run_all_qa",
]


def run_all_qa(
    ir_dict: dict[str, Any],
    evidence_index: dict[str, Any],
    expected_ir: dict[str, Any] | None = None,
) -> list[QAResult]:
    """모든 QA 검사 실행.

    Args:
        ir_dict: 실제 Report IR 딕셔너리
        evidence_index: Evidence ID → 상세 정보 맵
        expected_ir: 예상 Report IR (골든 비교용, 선택)

    Returns:
        QAResult 목록
    """
    results: list[QAResult] = []

    # 1. Layout QA (항상 실행)
    layout_result, _ = run_layout_qa(ir_dict)
    results.append(layout_result)

    # 2. Evidence QA (항상 실행)
    evidence_result, _ = run_evidence_qa(ir_dict, evidence_index)
    results.append(evidence_result)

    # 3. Report QA (expected_ir가 있을 때만)
    if expected_ir:
        report_result, _ = run_report_qa(expected_ir, ir_dict)
        results.append(report_result)

    return results
