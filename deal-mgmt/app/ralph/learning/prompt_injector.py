"""학습된 패턴을 LLM 프롬프트에 주입한다.

PatternAggregator에서 추출한 과거 학습 패턴을
LDDSectionAnalyzer나 RalphMemoGenerator의 시스템 프롬프트에 추가한다.
"""

from __future__ import annotations


class LearningPromptInjector:
    """학습된 패턴을 LLM 프롬프트에 주입한다."""

    def enrich_system_prompt(
        self,
        base_prompt: str,
        patterns: list[str],
    ) -> str:
        """기본 프롬프트에 '과거 학습' 섹션을 추가한다.

        Args:
            base_prompt: 원본 시스템 프롬프트
            patterns: PatternAggregator에서 반환된 패턴 목록

        Returns:
            학습 패턴이 주입된 시스템 프롬프트
        """
        if not patterns:
            return base_prompt

        learning_section = "\n\n---\n\n## 과거 반복에서 학습된 패턴\n\n"
        learning_section += "아래는 이전 문서 생성에서 축적된 품질 패턴입니다. "
        learning_section += "이를 참고하여 동일한 실수를 반복하지 않고, 높은 점수를 받은 패턴을 따르세요.\n\n"
        learning_section += "\n".join(patterns)

        return base_prompt + learning_section

    def enrich_feedback(
        self,
        existing_feedback: list[str],
        patterns: list[str],
    ) -> list[str]:
        """기존 피드백에 학습 패턴을 추가한다.

        Fresh Context에서 이전 반복 피드백과 함께 전달.
        """
        if not patterns:
            return existing_feedback

        enriched = list(existing_feedback)
        enriched.append("[학습 패턴] " + " | ".join(p for p in patterns if not p.startswith("##")))
        return enriched
