"""내러티브 간 일관성 체크 모듈 (T-N17).

> 마지막 수정: 2026-02-10 11:52:29

여러 섹션의 내러티브에서 동일 지표가 언급될 때 값이 일치하는지 검증한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.narrative_generator.engine.structured_output import (
    NumericClaim,
    SectionNarrative,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------


@dataclass
class ConflictDetail:
    """일관성 충돌 상세.

    Attributes:
        metric_context: 지표/컨텍스트 설명.
        section_a: 첫 번째 섹션 ID.
        value_a: 첫 번째 값.
        section_b: 두 번째 섹션 ID.
        value_b: 두 번째 값.
        claim_a: 원본 클레임 A.
        claim_b: 원본 클레임 B.
    """

    metric_context: str
    section_a: str
    value_a: float
    section_b: str
    value_b: float
    claim_a: NumericClaim
    claim_b: NumericClaim


@dataclass
class ConsistencyReport:
    """일관성 체크 보고서.

    Attributes:
        is_consistent: 전체 일관성 여부.
        total_comparisons: 비교 수행 횟수.
        conflicts: 발견된 충돌 리스트.
        warnings: 경고 메시지 리스트.
    """

    is_consistent: bool = True
    total_comparisons: int = 0
    conflicts: list[ConflictDetail] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ConsistencyChecker
# ---------------------------------------------------------------------------

# 동일 지표로 간주할 컨텍스트 키워드 그룹
_METRIC_GROUPS: list[list[str]] = [
    ["매출", "매출액", "revenue"],
    ["영업이익", "operating income", "operating profit"],
    ["순이익", "당기순이익", "net income"],
    ["ebitda", "상각전영업이익"],
    ["자산", "자산총계", "total assets"],
    ["부채", "부채총계", "total liabilities"],
    ["자본", "자본총계", "total equity"],
]

# 금액 일관성 허용 오차
_AMOUNT_TOLERANCE = 0.02  # ±2% (섹션 간 표현 차이 허용)
_PERCENT_TOLERANCE = 0.5  # ±0.5%p


class ConsistencyChecker:
    """내러티브 간 일관성 검사기."""

    def check(
        self,
        narratives: dict[str, SectionNarrative],
    ) -> ConsistencyReport:
        """여러 섹션의 내러티브 간 일관성을 검사한다.

        Args:
            narratives: {section_id: SectionNarrative} 딕셔너리.

        Returns:
            ConsistencyReport.
        """
        report = ConsistencyReport()

        # 모든 클레임을 메트릭 그룹별로 분류
        grouped_claims: dict[int, list[tuple[str, NumericClaim]]] = {}

        for section_id, narrative in narratives.items():
            for claim in narrative.key_claims:
                group_idx = self._find_metric_group(claim)
                if group_idx is not None:
                    if group_idx not in grouped_claims:
                        grouped_claims[group_idx] = []
                    grouped_claims[group_idx].append((section_id, claim))

        # 같은 그룹 내 클레임 간 비교
        for group_idx, claims_in_group in grouped_claims.items():
            if len(claims_in_group) < 2:
                continue

            # 같은 metric_type 내에서만 비교
            by_type: dict[str, list[tuple[str, NumericClaim]]] = {}
            for section_id, claim in claims_in_group:
                if claim.metric_type not in by_type:
                    by_type[claim.metric_type] = []
                by_type[claim.metric_type].append((section_id, claim))

            for metric_type, type_claims in by_type.items():
                for i in range(len(type_claims)):
                    for j in range(i + 1, len(type_claims)):
                        report.total_comparisons += 1
                        sec_a, claim_a = type_claims[i]
                        sec_b, claim_b = type_claims[j]

                        if sec_a == sec_b:
                            continue

                        if not self._values_consistent(claim_a, claim_b):
                            conflict = ConflictDetail(
                                metric_context=_METRIC_GROUPS[group_idx][0],
                                section_a=sec_a,
                                value_a=claim_a.value,
                                section_b=sec_b,
                                value_b=claim_b.value,
                                claim_a=claim_a,
                                claim_b=claim_b,
                            )
                            report.conflicts.append(conflict)
                            report.is_consistent = False
                            report.warnings.append(
                                f"일관성 위반: '{_METRIC_GROUPS[group_idx][0]}' "
                                f"'{sec_a}'={claim_a.value} vs "
                                f"'{sec_b}'={claim_b.value}"
                            )

        logger.info(
            "일관성 검사 완료: 비교=%d, 충돌=%d",
            report.total_comparisons,
            len(report.conflicts),
        )

        return report

    @staticmethod
    def _find_metric_group(claim: NumericClaim) -> int | None:
        """클레임이 속하는 메트릭 그룹 인덱스를 반환한다."""
        context_lower = claim.context.lower()
        for i, keywords in enumerate(_METRIC_GROUPS):
            if any(kw in context_lower for kw in keywords):
                return i
        return None

    @staticmethod
    def _values_consistent(a: NumericClaim, b: NumericClaim) -> bool:
        """두 클레임의 값이 일관되는지 확인한다."""
        if a.metric_type == "percentage":
            return abs(a.value - b.value) <= _PERCENT_TOLERANCE

        # 금액/배수 비교
        if a.value == 0 and b.value == 0:
            return True
        if a.value == 0 or b.value == 0:
            return False
        return (
            abs(a.value - b.value) / max(abs(a.value), abs(b.value))
            <= _AMOUNT_TOLERANCE
        )
