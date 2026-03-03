"""신뢰도 점수 모듈 (T-N18).

> 마지막 수정: 2026-02-10 11:52:29

내러티브의 품질과 신뢰도를 0.0~1.0 점수로 산출한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.narrative_generator.engine.structured_output import SectionNarrative
from src.narrative_generator.fact_checker.validator import FactCheckReport

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfidenceResult:
    """신뢰도 평가 결과.

    Attributes:
        section_id: 섹션 식별자.
        overall_score: 종합 신뢰도 점수 (0.0~1.0).
        fact_check_score: 수치 검증 점수.
        structure_score: 구조 적절성 점수.
        length_score: 길이 적절성 점수.
        is_confident: 신뢰도 임계값 통과 여부.
    """

    section_id: str
    overall_score: float
    fact_check_score: float
    structure_score: float
    length_score: float
    is_confident: bool


# ---------------------------------------------------------------------------
# 가중치 상수
# ---------------------------------------------------------------------------

WEIGHT_FACT_CHECK = 0.4
WEIGHT_STRUCTURE = 0.3
WEIGHT_LENGTH = 0.3

# 적정 길이 범위 (토큰 수 기준)
MIN_ACCEPTABLE_LENGTH = 50  # 최소 토큰
MAX_ACCEPTABLE_LENGTH = 1200  # 최대 토큰

# 적정 문단 수
MIN_PARAGRAPHS = 2
MAX_PARAGRAPHS = 6

DEFAULT_CONFIDENCE_THRESHOLD = 0.7


# ---------------------------------------------------------------------------
# ConfidenceScorer
# ---------------------------------------------------------------------------


class ConfidenceScorer:
    """내러티브 신뢰도 평가기.

    Args:
        threshold: 신뢰도 임계값 (기본 0.7). 이 값 미만이면 경고.
    """

    def __init__(self, threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> None:
        self._threshold = threshold

    @property
    def threshold(self) -> float:
        """신뢰도 임계값."""
        return self._threshold

    def score(
        self,
        narrative: SectionNarrative,
        fact_report: FactCheckReport,
    ) -> ConfidenceResult:
        """내러티브의 신뢰도를 평가한다.

        Args:
            narrative: 평가할 SectionNarrative.
            fact_report: 수치 검증 보고서.

        Returns:
            ConfidenceResult.
        """
        # 1. 수치 검증 점수 (40%)
        fact_score = self._score_fact_check(fact_report)

        # 2. 구조 적절성 점수 (30%)
        structure_score = self._score_structure(narrative.text)

        # 3. 길이 적절성 점수 (30%)
        length_score = self._score_length(narrative.text)

        # 가중 평균
        overall = (
            WEIGHT_FACT_CHECK * fact_score
            + WEIGHT_STRUCTURE * structure_score
            + WEIGHT_LENGTH * length_score
        )

        is_confident = overall >= self._threshold

        if not is_confident:
            logger.warning(
                "신뢰도 임계값 미달: section='%s', 점수=%.2f (임계=%.2f)",
                narrative.section_id,
                overall,
                self._threshold,
            )

        return ConfidenceResult(
            section_id=narrative.section_id,
            overall_score=round(overall, 3),
            fact_check_score=round(fact_score, 3),
            structure_score=round(structure_score, 3),
            length_score=round(length_score, 3),
            is_confident=is_confident,
        )

    @staticmethod
    def _score_fact_check(report: FactCheckReport) -> float:
        """수치 검증 통과율 기반 점수."""
        return report.pass_rate

    @staticmethod
    def _score_structure(text: str) -> float:
        """텍스트 구조 적절성 점수.

        문단 수, 문장 길이 다양성을 평가한다.
        """
        if not text:
            return 0.0

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        n_paragraphs = len(paragraphs)

        # 한 줄로 된 텍스트는 줄바꿈 기준으로도 시도
        if n_paragraphs <= 1:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
            n_paragraphs = len(paragraphs)

        # 문단 수 점수 (MIN~MAX 사이가 최적)
        if MIN_PARAGRAPHS <= n_paragraphs <= MAX_PARAGRAPHS:
            paragraph_score = 1.0
        elif n_paragraphs < MIN_PARAGRAPHS:
            paragraph_score = n_paragraphs / MIN_PARAGRAPHS
        else:
            # 과도하게 많은 문단은 약간 감점
            paragraph_score = max(0.5, 1.0 - (n_paragraphs - MAX_PARAGRAPHS) * 0.1)

        # 문장 다양성 점수 (모든 문장이 비슷한 길이면 감점)
        import re

        sentences = re.split(r"[.!?。]\s+", text)
        sentences = [s for s in sentences if len(s) > 5]

        if len(sentences) < 2:
            diversity_score = 0.5
        else:
            lengths = [len(s) for s in sentences]
            avg_len = sum(lengths) / len(lengths)
            if avg_len == 0:
                diversity_score = 0.5
            else:
                variance = sum((length - avg_len) ** 2 for length in lengths) / len(
                    lengths
                )
                cv = (variance**0.5) / avg_len  # 변동 계수
                # cv가 0.2~0.8 사이면 적절한 다양성
                if 0.2 <= cv <= 0.8:
                    diversity_score = 1.0
                elif cv < 0.2:
                    diversity_score = 0.7  # 너무 균일
                else:
                    diversity_score = 0.8  # 너무 불균일

        return paragraph_score * 0.6 + diversity_score * 0.4

    @staticmethod
    def _score_length(text: str) -> float:
        """텍스트 길이 적절성 점수."""
        if not text:
            return 0.0

        # 간이 토큰 카운트
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            token_count = len(enc.encode(text))
        except ImportError:
            token_count = max(1, int(len(text) / 3.5))

        if MIN_ACCEPTABLE_LENGTH <= token_count <= MAX_ACCEPTABLE_LENGTH:
            return 1.0
        elif token_count < MIN_ACCEPTABLE_LENGTH:
            return max(0.1, token_count / MIN_ACCEPTABLE_LENGTH)
        else:
            # 너무 긴 텍스트는 약간 감점
            excess_ratio = token_count / MAX_ACCEPTABLE_LENGTH
            return max(0.5, 1.0 / excess_ratio)
