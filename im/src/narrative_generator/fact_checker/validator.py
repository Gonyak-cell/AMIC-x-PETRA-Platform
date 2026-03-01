"""수치 검증 모듈 (T-N16).

> 마지막 수정: 2026-02-10 11:52:29

내러티브에서 추출된 수치 클레임을 재무 데이터와 대조하여 검증한다.
허용 오차: 금액 ±1%, 퍼센트 ±0.1%p.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.engine.structured_output import (
    NumericClaim,
    SectionNarrative,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------


@dataclass
class ClaimVerification:
    """단일 클레임 검증 결과.

    Attributes:
        claim: 검증 대상 클레임.
        verified: 검증 통과 여부.
        expected_value: 재무 데이터에서의 기대값 (없으면 None).
        tolerance_used: 사용된 허용 오차.
        note: 검증 참고사항.
    """

    claim: NumericClaim
    verified: bool
    expected_value: float | None = None
    tolerance_used: float = 0.0
    note: str = ""


@dataclass
class FactCheckReport:
    """팩트 체크 보고서.

    Attributes:
        section_id: 검사한 섹션 ID.
        claims_checked: 검사한 클레임 수.
        claims_verified: 검증 통과한 클레임 수.
        claims_failed: 검증 실패한 클레임 수.
        claims_unverifiable: 검증 불가능한 클레임 수 (대조 데이터 없음).
        details: 개별 클레임 검증 결과 리스트.
        pass_rate: 검증 통과율 (0.0~1.0).
    """

    section_id: str
    claims_checked: int = 0
    claims_verified: int = 0
    claims_failed: int = 0
    claims_unverifiable: int = 0
    details: list[ClaimVerification] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """검증 통과율 (검증 불가 클레임은 실패로 간주)."""
        total = self.claims_verified + self.claims_failed + self.claims_unverifiable
        if total == 0:
            return 1.0  # 검증할 클레임이 없으면 통과
        return self.claims_verified / total


# ---------------------------------------------------------------------------
# 허용 오차 상수
# ---------------------------------------------------------------------------

AMOUNT_TOLERANCE = 0.01  # 금액 ±1%
PERCENT_TOLERANCE = 0.1  # 퍼센트 ±0.1%p
MULTIPLE_TOLERANCE = 0.1  # 배수 ±0.1


# ---------------------------------------------------------------------------
# FactValidator
# ---------------------------------------------------------------------------


class FactValidator:
    """내러티브 수치 검증기.

    내러티브에서 추출된 NumericClaim을 IMDocumentData의 재무 데이터와 대조한다.
    """

    def validate(
        self,
        narrative: SectionNarrative,
        data: IMDocumentData,
    ) -> FactCheckReport:
        """섹션 내러티브의 수치 클레임을 검증한다.

        Args:
            narrative: 검증할 SectionNarrative.
            data: 대조할 IMDocumentData.

        Returns:
            FactCheckReport.
        """
        report = FactCheckReport(section_id=narrative.section_id)
        reference_values = self._build_reference(data)

        for claim in narrative.key_claims:
            report.claims_checked += 1
            verification = self._verify_claim(claim, reference_values)
            report.details.append(verification)

            if verification.expected_value is None:
                report.claims_unverifiable += 1
            elif verification.verified:
                report.claims_verified += 1
            else:
                report.claims_failed += 1

        logger.info(
            "팩트 체크 완료: section='%s', 검사=%d, 통과=%d, 실패=%d, 불가=%d",
            narrative.section_id,
            report.claims_checked,
            report.claims_verified,
            report.claims_failed,
            report.claims_unverifiable,
        )

        return report

    def _verify_claim(
        self,
        claim: NumericClaim,
        reference: dict[str, float],
    ) -> ClaimVerification:
        """단일 클레임을 검증한다."""
        # 클레임의 컨텍스트에서 가장 가까운 참조값을 찾기
        matched_key, matched_value = self._find_matching_reference(claim, reference)

        if matched_value is None:
            return ClaimVerification(
                claim=claim,
                verified=False,  # 대조 불가 시 검증 실패 처리 (사람 검토 필요)
                note="대조 데이터 없음 (검증 불가 — needs_human_review)",
            )

        # 허용 오차 내인지 확인
        if claim.metric_type == "amount":
            tolerance = AMOUNT_TOLERANCE
            # 원 단위로 비교
            within = _within_tolerance(claim.value, matched_value, tolerance)
        elif claim.metric_type == "percentage":
            tolerance = PERCENT_TOLERANCE
            within = abs(claim.value - matched_value) <= tolerance
        elif claim.metric_type == "multiple":
            tolerance = MULTIPLE_TOLERANCE
            within = abs(claim.value - matched_value) <= tolerance
        else:
            tolerance = AMOUNT_TOLERANCE
            within = _within_tolerance(claim.value, matched_value, tolerance)

        return ClaimVerification(
            claim=claim,
            verified=within,
            expected_value=matched_value,
            tolerance_used=tolerance,
            note=f"참조키: {matched_key}" if matched_key else "",
        )

    def _find_matching_reference(
        self,
        claim: NumericClaim,
        reference: dict[str, float],
    ) -> tuple[str, float | None]:
        """클레임에 대응하는 참조값을 찾는다."""
        context_lower = claim.context.lower()

        # 금액 클레임: 컨텍스트의 키워드로 매칭
        for ref_key, ref_value in reference.items():
            key_parts = ref_key.lower().split("_")
            # 키의 주요 부분이 컨텍스트에 포함되면 매칭
            if any(part in context_lower for part in key_parts if len(part) > 1):
                # 금액 클레임은 원 단위로 비교
                if claim.metric_type == "amount":
                    if _within_tolerance(claim.value, ref_value, 0.05):
                        return ref_key, ref_value
                elif claim.metric_type == "percentage":
                    # 퍼센트는 직접 비교
                    if abs(claim.value - ref_value * 100) <= 1.0:
                        return ref_key, ref_value * 100

        return "", None

    def _build_reference(self, data: IMDocumentData) -> dict[str, float]:
        """IMDocumentData에서 참조 수치 딕셔너리를 구성한다."""
        ref: dict[str, float] = {}
        fs = data.financial_statements

        # 연도별 재무 데이터
        for field_name in [
            "revenue",
            "cost_of_goods_sold",
            "gross_profit",
            "operating_income",
            "ebitda",
            "net_income",
            "total_assets",
            "total_liabilities",
            "total_equity",
            "cash_and_equivalents",
            "total_debt",
            "operating_cash_flow",
            "capex",
            "free_cash_flow",
        ]:
            year_data = getattr(fs, field_name, {})
            if isinstance(year_data, dict):
                for year, value in year_data.items():
                    ref[f"{field_name}_{year}"] = value

        # 파생 지표
        if data.derived_metrics:
            for key, value in data.derived_metrics.items():
                ref[key] = value

        return ref


def _within_tolerance(actual: float, expected: float, tolerance: float) -> bool:
    """두 값이 허용 오차 내인지 확인한다."""
    if expected == 0:
        return actual == 0
    return abs(actual - expected) / abs(expected) <= tolerance
