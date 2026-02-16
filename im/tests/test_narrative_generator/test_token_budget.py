"""TokenBudgetManager 단위 테스트.

> 마지막 수정: 2026-02-10 12:08:25

예산 조회, 예산 초과 검사, 텍스트 잘라내기를 테스트한다.
"""

from __future__ import annotations

from src.narrative_generator.engine.token_budget import (
    DEFAULT_BUDGET,
    DEFAULT_TOKEN_BUDGETS,
    TokenBudgetManager,
)


# ---------------------------------------------------------------------------
# TestTokenBudgetManager
# ---------------------------------------------------------------------------


class TestTokenBudgetManager:
    """TokenBudgetManager 예산 관리 테스트."""

    def test_get_budget_returns_correct_defaults(self) -> None:
        """등록된 섹션은 기본 예산, 미등록 섹션은 DEFAULT_BUDGET을 반환한다."""
        manager = TokenBudgetManager()

        # 등록된 섹션
        assert manager.get_budget("executive_summary") == 800
        assert manager.get_budget("financial_analysis") == 800
        assert manager.get_budget("contact") == 200
        assert manager.get_budget("appendix") == 300

        # 미등록 섹션
        assert manager.get_budget("unknown_section") == DEFAULT_BUDGET

    def test_check_budget_identifies_over_budget(self) -> None:
        """긴 텍스트가 예산 초과로 올바르게 식별되는지 확인한다."""
        manager = TokenBudgetManager()

        # 매우 긴 텍스트 (contact 예산 = 200 토큰)
        long_text = "테스트 문장입니다. " * 500
        result = manager.check_budget("contact", long_text)

        assert result.section_id == "contact"
        assert result.budget == 200
        assert result.actual > 200
        assert result.within_budget is False
        assert result.overage > 0

        # 짧은 텍스트
        short_text = "짧은 텍스트."
        result_short = manager.check_budget("executive_summary", short_text)

        assert result_short.within_budget is True
        assert result_short.overage == 0

    def test_truncate_to_budget_shortens_long_text(self) -> None:
        """긴 텍스트가 예산 내로 잘리는지 확인한다."""
        manager = TokenBudgetManager()

        # 긴 텍스트 생성 (약 300 토큰 이상)
        sentences = [f"이것은 {i}번째 테스트 문장입니다." for i in range(100)]
        long_text = " ".join(sentences)

        max_tokens = 50
        truncated = manager.truncate_to_budget(long_text, max_tokens)

        assert len(truncated) < len(long_text)
        # 잘린 텍스트는 원본보다 짧아야 함
        assert truncated != long_text

        # 이미 예산 내인 텍스트는 그대로 반환
        short_text = "짧은 텍스트입니다."
        result = manager.truncate_to_budget(short_text, 1000)
        assert result == short_text
