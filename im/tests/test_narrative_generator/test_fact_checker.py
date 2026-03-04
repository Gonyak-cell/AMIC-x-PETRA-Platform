"""FactValidator, ConsistencyChecker, ConfidenceScorer 단위 테스트.

> 마지막 수정: 2026-02-10 12:08:25

수치 검증, 내러티브 간 일관성 검사, 신뢰도 평가를 테스트한다.
외부 API 호출 없이 모든 테스트가 동작한다.
"""

from __future__ import annotations


from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.engine.structured_output import (
    NumericClaim,
    SectionNarrative,
)
from src.narrative_generator.fact_checker.confidence import (
    ConfidenceResult,
    ConfidenceScorer,
)
from src.narrative_generator.fact_checker.consistency import (
    ConsistencyChecker,
    ConsistencyReport,
)
from src.narrative_generator.fact_checker.validator import (
    FactCheckReport,
    FactValidator,
)


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _make_narrative(
    section_id: str,
    text: str,
    claims: list[NumericClaim] | None = None,
) -> SectionNarrative:
    """테스트용 SectionNarrative를 생성한다."""
    return SectionNarrative(
        section_id=section_id,
        text=text,
        key_claims=claims or [],
    )


def _make_amount_claim(
    raw_text: str,
    value: float,
    unit: str = "억원",
    context: str = "",
) -> NumericClaim:
    """테스트용 금액 NumericClaim을 생성한다."""
    return NumericClaim(
        raw_text=raw_text,
        metric_type="amount",
        value=value,
        unit=unit,
        context=context or raw_text,
    )


def _make_pct_claim(
    raw_text: str,
    value: float,
    context: str = "",
) -> NumericClaim:
    """테스트용 퍼센트 NumericClaim을 생성한다."""
    return NumericClaim(
        raw_text=raw_text,
        metric_type="percentage",
        value=value,
        unit="%",
        context=context or raw_text,
    )


# ---------------------------------------------------------------------------
# TestFactValidator
# ---------------------------------------------------------------------------


class TestFactValidator:
    """FactValidator 수치 검증 테스트."""

    def test_validate_with_matching_data(self, sample_im_data: IMDocumentData) -> None:
        """수치 클레임이 재무 데이터와 일치할 때 검증을 통과하는지 확인한다."""
        validator = FactValidator()

        # 클레임 없는 내러티브 (모든 검증 통과)
        narrative = _make_narrative(
            section_id="executive_summary",
            text="테스트기업은 안정적인 성장세를 유지하고 있습니다.",
            claims=[],
        )

        report = validator.validate(narrative, sample_im_data)

        assert isinstance(report, FactCheckReport)
        assert report.section_id == "executive_summary"
        assert report.claims_checked == 0
        assert report.pass_rate == 1.0  # 검증할 클레임 없으면 1.0


# ---------------------------------------------------------------------------
# TestConsistencyChecker
# ---------------------------------------------------------------------------


class TestConsistencyChecker:
    """ConsistencyChecker 일관성 검사 테스트."""

    def test_consistent_narratives(self) -> None:
        """동일 지표에 동일 값을 언급하는 내러티브가 일관성을 통과하는지 확인한다."""
        checker = ConsistencyChecker()

        # 같은 매출 값 (150,000,000,000원 = 1,500억원)
        claim_a = _make_amount_claim(
            "1,500억원", 150_000_000_000, context="매출 1,500억원"
        )
        claim_b = _make_amount_claim(
            "1,500억원", 150_000_000_000, context="매출액은 1,500억원"
        )

        narratives = {
            "executive_summary": _make_narrative(
                "executive_summary",
                "매출 1,500억원을 달성하였습니다.",
                [claim_a],
            ),
            "financial_analysis": _make_narrative(
                "financial_analysis",
                "매출액은 1,500억원을 기록하였습니다.",
                [claim_b],
            ),
        }

        report = checker.check(narratives)

        assert isinstance(report, ConsistencyReport)
        assert report.is_consistent is True
        assert len(report.conflicts) == 0

    def test_inconsistent_narratives(self) -> None:
        """동일 지표에 상이한 값을 언급하면 일관성 위반이 감지되는지 확인한다."""
        checker = ConsistencyChecker()

        # 매출 값이 크게 다름
        claim_a = _make_amount_claim(
            "1,500억원", 150_000_000_000, context="매출 1,500억원"
        )
        claim_b = _make_amount_claim(
            "2,000억원", 200_000_000_000, context="매출 2,000억원"
        )

        narratives = {
            "executive_summary": _make_narrative(
                "executive_summary",
                "매출 1,500억원을 달성하였습니다.",
                [claim_a],
            ),
            "financial_analysis": _make_narrative(
                "financial_analysis",
                "매출 2,000억원을 기록하였습니다.",
                [claim_b],
            ),
        }

        report = checker.check(narratives)

        assert isinstance(report, ConsistencyReport)
        assert report.is_consistent is False
        assert len(report.conflicts) >= 1
        assert len(report.warnings) >= 1


# ---------------------------------------------------------------------------
# TestConfidenceScorer
# ---------------------------------------------------------------------------


class TestConfidenceScorer:
    """ConfidenceScorer 신뢰도 평가 테스트."""

    def test_score_returns_valid_range(self) -> None:
        """신뢰도 점수가 0.0~1.0 범위 내인지 확인한다."""
        scorer = ConfidenceScorer(threshold=0.7)

        # 적절한 길이와 구조를 가진 내러티브
        text = (
            "테스트기업은 국내 IT 서비스 시장의 선도기업입니다.\n\n"
            "최근 3개년 매출은 연평균 22.5% 성장하였으며, "
            "영업이익률은 18.7%를 기록하고 있습니다.\n\n"
            "시장 점유율 확대와 신사업 진출을 통해 "
            "지속적인 성장이 기대됩니다.\n\n"
            "안정적인 현금흐름과 낮은 부채비율은 "
            "투자 매력도를 높이는 핵심 요인입니다."
        )

        narrative = _make_narrative(
            section_id="executive_summary",
            text=text,
        )

        # 팩트 체크 보고서 (클레임 없음 -> pass_rate=1.0)
        fact_report = FactCheckReport(section_id="executive_summary")

        result = scorer.score(narrative, fact_report)

        assert isinstance(result, ConfidenceResult)
        assert 0.0 <= result.overall_score <= 1.0
        assert 0.0 <= result.fact_check_score <= 1.0
        assert 0.0 <= result.structure_score <= 1.0
        assert 0.0 <= result.length_score <= 1.0
        assert result.section_id == "executive_summary"
        assert isinstance(result.is_confident, bool)
