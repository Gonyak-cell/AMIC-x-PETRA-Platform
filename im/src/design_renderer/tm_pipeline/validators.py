"""Anti-Hallucination 검증기 — 산술/출처/일관성 검증.

PPTX 생성 전에 IMDocumentData의 데이터 정합성을 검증한다.
AI 생성 콘텐츠의 수치 환각(hallucination)을 사전 탐지.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.design_renderer.im_document import IMDocumentData

# 산술/일관성 검증 시 허용 오차 (백만원 단위 기준, 0.01% 이내)
_TOLERANCE_ABSOLUTE = 1.0  # 백만원 단위 데이터 기준 절대 허용 오차
_TOLERANCE_RELATIVE = 0.0001  # 상대 허용 오차 (0.01%)

# 영업이익 검증 완화 허용 오차 (5%)
# 실제 재무제표에서 operating_income = GP - SGA - R&D - 기타 영업비용이므로
# GP - SGA만으로는 정확히 일치하지 않을 수 있다.
_TOLERANCE_RELATIVE_OP_INCOME = 0.05


def _within_tolerance(actual: float, expected: float) -> bool:
    """절대/상대 허용 오차 내 일치 여부 판별."""
    diff = abs(actual - expected)
    if diff <= _TOLERANCE_ABSOLUTE:
        return True
    if expected != 0.0 and diff / abs(expected) <= _TOLERANCE_RELATIVE:
        return True
    return False


@dataclass
class ValidationIssue:
    """검증 이슈 항목."""

    check_type: str  # "arithmetic", "source", "consistency"
    severity: str  # "warning", "error"
    message: str
    section_id: str = ""


@dataclass
class ValidationResult:
    """검증 결과."""

    issues: list[ValidationIssue] = field(default_factory=list)
    checks_run: int = 0

    @property
    def passed(self) -> bool:
        """에러 수준 이슈가 없으면 통과."""
        return not any(i.severity == "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        """에러 수."""
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        """경고 수."""
        return sum(1 for i in self.issues if i.severity == "warning")


class AntiHallucinationValidator:
    """Anti-Hallucination 검증기.

    IMDocumentData의 수치 정합성, 출처 존재 여부, 연도별 일관성을 검증한다.

    Args:
        data: 검증 대상 IMDocumentData.
    """

    def __init__(self, data: IMDocumentData) -> None:
        self._data = data

    def run_all(self) -> ValidationResult:
        """전체 검증 체인 실행.

        Returns:
            ValidationResult (이슈 목록, 실행 검증 수).
        """
        result = ValidationResult()

        # 각 검증기 순차 실행
        self._check_arithmetic(result)
        self._check_source_citations(result)
        self._check_consistency(result)

        return result

    def _check_arithmetic(self, result: ValidationResult) -> None:
        """산술 검증 — 세그먼트 합 = 총 매출 등."""
        fs = self._data.financial_statements
        seg = self._data.segment_revenue

        if not seg or not seg.segments:
            result.checks_run += 1
            return

        checked = False
        for year in fs.revenue:
            total_rev = fs.revenue[year]
            # 해당 연도 데이터가 있는 세그먼트만 합산
            seg_values = [
                seg_data[year] for seg_data in seg.segments.values() if year in seg_data
            ]
            if not seg_values:
                continue

            checked = True
            seg_sum = sum(seg_values)
            if not _within_tolerance(seg_sum, total_rev):
                result.issues.append(
                    ValidationIssue(
                        check_type="arithmetic",
                        severity="warning",
                        message=(
                            f"{year} 세그먼트 매출 합({seg_sum:,.0f}) ≠ "
                            f"총 매출({total_rev:,.0f}), "
                            f"차이: {abs(seg_sum - total_rev):,.0f}"
                        ),
                        section_id="financial_analysis",
                    )
                )

        if checked:
            result.checks_run += 1

    def _check_source_citations(self, result: ValidationResult) -> None:
        """출처 검증 — 주요 섹션에 출처 메타데이터 존재 여부."""
        result.checks_run += 1
        citations = self._data.source_citations

        # 재무 데이터가 있으면 출처도 있어야 함
        if self._data.financial_statements.revenue and not citations:
            result.issues.append(
                ValidationIssue(
                    check_type="source",
                    severity="warning",
                    message="재무 데이터 존재하나 출처 메타데이터 없음",
                    section_id="financial_analysis",
                )
            )

    def _check_consistency(self, result: ValidationResult) -> None:
        """일관성 검증 — gross_profit = revenue - COGS, operating_income = GP - SGA."""
        result.checks_run += 1
        fs = self._data.financial_statements

        for year in fs.revenue:
            # gross_profit = revenue - COGS
            rev = fs.revenue.get(year)
            cogs = fs.cost_of_goods_sold.get(year)
            gp = fs.gross_profit.get(year)

            if rev is not None and cogs is not None and gp is not None:
                expected_gp = rev - cogs
                if not _within_tolerance(gp, expected_gp):
                    result.issues.append(
                        ValidationIssue(
                            check_type="consistency",
                            severity="warning",
                            message=(
                                f"{year} gross_profit({gp:,.0f}) ≠ "
                                f"revenue({rev:,.0f}) - COGS({cogs:,.0f}) = "
                                f"{expected_gp:,.0f}"
                            ),
                            section_id="financial_analysis",
                        )
                    )

            # operating_income ≈ gross_profit - SGA (simplified)
            # 실제 재무제표에서는 R&D, 기타 영업비용 등이 추가로 차감되므로
            # 완화된 허용 오차(_TOLERANCE_RELATIVE_OP_INCOME = 5%)를 적용한다.
            sga = fs.sga_expenses.get(year)
            oi = fs.operating_income.get(year)

            if gp is not None and sga is not None and oi is not None:
                expected_oi = gp - sga
                diff = abs(oi - expected_oi)
                within = diff <= _TOLERANCE_ABSOLUTE or (
                    expected_oi != 0.0
                    and diff / abs(expected_oi) <= _TOLERANCE_RELATIVE_OP_INCOME
                )
                if not within:
                    result.issues.append(
                        ValidationIssue(
                            check_type="consistency",
                            severity="warning",
                            message=(
                                f"{year} operating_income({oi:,.0f}) ≠ "
                                f"gross_profit({gp:,.0f}) - SGA({sga:,.0f}) = "
                                f"{expected_oi:,.0f} "
                                f"(허용 오차 {_TOLERANCE_RELATIVE_OP_INCOME:.0%} 초과)"
                            ),
                            section_id="financial_analysis",
                        )
                    )
