"""Factual Optimism 톤 어댑터.

> 마지막 수정: 2026-02-10 11:52:29

IM 문서의 톤은 "Factual Optimism" — 사실에 기반하되 긍정적으로 서술한다.
이 모듈은 LLM 프롬프트에 톤 가이드를 주입하고, 생성된 텍스트의 톤을 검증한다.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 톤 프로필
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToneProfile:
    """내러티브 톤 프로필.

    Attributes:
        name: 프로필 이름.
        description: 프로필 설명.
        system_instruction: LLM 시스템 프롬프트에 포함될 톤 지시문.
        positive_markers: 긍정적 톤 지표 단어/구문.
        negative_markers: 부정적 톤 지표 (IM에서 사용하면 안 되는 표현).
        neutral_alternatives: 부정적 표현 → 중립/긍정적 대안 매핑.
    """

    name: str
    description: str
    system_instruction: str
    positive_markers: tuple[str, ...] = ()
    negative_markers: tuple[str, ...] = ()
    neutral_alternatives: tuple[tuple[str, str], ...] = ()


# ---------------------------------------------------------------------------
# 기본 톤: Factual Optimism
# ---------------------------------------------------------------------------


FACTUAL_OPTIMISM = ToneProfile(
    name="factual_optimism",
    description="사실에 기반한 긍정적 서술. 투자 매력도를 객관적 데이터로 뒷받침한다.",
    system_instruction=(
        "## 톤 가이드라인: Factual Optimism\n"
        "- 모든 서술은 제공된 재무 데이터와 사실에 근거해야 합니다.\n"
        "- 긍정적 성과를 강조하되, 수치적 근거를 반드시 함께 제시합니다.\n"
        "- '~할 것으로 기대됩니다', '~할 전망입니다' 등 미래 전망은 "
        "근거 데이터와 함께만 사용합니다.\n"
        "- 부정적 지표(매출 감소, 적자 등)는 사실을 숨기지 않되, "
        "개선 방향이나 구조적 맥락을 함께 설명합니다.\n"
        "- 과장 표현('획기적', '혁명적', '압도적')은 사용하지 않습니다.\n"
        "- 투자자의 관점에서 핵심 투자 매력 포인트가 자연스럽게 드러나도록 합니다.\n"
        "- 전문적이면서도 읽기 쉬운 문체를 유지합니다.\n"
    ),
    positive_markers=(
        "견조한 성장",
        "안정적인",
        "지속적인",
        "개선",
        "강화",
        "확대",
        "효율적",
        "차별화된",
        "경쟁력",
        "시장 선도",
    ),
    negative_markers=(
        "획기적",
        "혁명적",
        "압도적",
        "독보적",
        "유일무이",
        "완벽한",
        "최고의",
        "전무후무",
    ),
    neutral_alternatives=(
        ("급격한 하락", "조정 국면"),
        ("심각한 적자", "수익성 개선이 필요한 구간"),
        ("실패", "기대에 미치지 못한 성과"),
        ("위기", "도전적 환경"),
        ("문제", "개선 과제"),
    ),
)


# ---------------------------------------------------------------------------
# 톤 어댑터
# ---------------------------------------------------------------------------


class ToneAdapter:
    """내러티브 톤 관리 어댑터.

    LLM 프롬프트에 톤 가이드를 주입하고, 생성된 텍스트의 톤을 검증한다.

    Args:
        profile: 적용할 톤 프로필. 기본값은 FACTUAL_OPTIMISM.
    """

    def __init__(self, profile: ToneProfile | None = None) -> None:
        self._profile = profile or FACTUAL_OPTIMISM

    @property
    def profile(self) -> ToneProfile:
        """현재 톤 프로필."""
        return self._profile

    def get_system_instruction(self) -> str:
        """LLM 시스템 프롬프트에 포함할 톤 지시문을 반환한다."""
        return self._profile.system_instruction

    def check_tone(self, text: str) -> ToneCheckResult:
        """생성된 텍스트의 톤을 검사한다.

        Args:
            text: 검사할 텍스트.

        Returns:
            ToneCheckResult: 검사 결과.
        """
        text_lower = text.lower()

        found_negative: list[str] = []
        for marker in self._profile.negative_markers:
            if marker in text_lower:
                found_negative.append(marker)

        found_positive: list[str] = []
        for marker in self._profile.positive_markers:
            if marker in text_lower:
                found_positive.append(marker)

        suggestions: list[str] = []
        for negative, alternative in self._profile.neutral_alternatives:
            if negative in text_lower:
                suggestions.append(f"'{negative}' → '{alternative}'")

        is_appropriate = len(found_negative) == 0

        return ToneCheckResult(
            is_appropriate=is_appropriate,
            negative_markers_found=found_negative,
            positive_markers_found=found_positive,
            suggestions=suggestions,
        )


@dataclass(frozen=True)
class ToneCheckResult:
    """톤 검사 결과.

    Attributes:
        is_appropriate: 톤이 적절한지 여부.
        negative_markers_found: 발견된 부정적 마커 목록.
        positive_markers_found: 발견된 긍정적 마커 목록.
        suggestions: 개선 제안 목록.
    """

    is_appropriate: bool
    negative_markers_found: list[str]
    positive_markers_found: list[str]
    suggestions: list[str]
