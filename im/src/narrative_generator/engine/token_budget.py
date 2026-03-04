"""토큰 예산 관리 모듈 (T-N14).

> 마지막 수정: 2026-02-13

섹션별 토큰 예산을 관리하고, 생성된 텍스트가 예산 내인지 검증한다.
프로바이더별 토큰 카운팅을 지원한다 (OpenAI: tiktoken, 기타: 근사치).
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 프로바이더별 문자/토큰 비율 (근사치)
# ---------------------------------------------------------------------------

PROVIDER_CHAR_RATIOS: dict[str, float] = {
    "openai": 3.5,  # cl100k_base
    "anthropic": 3.3,  # Claude tokenizer ~approximate
    "google": 3.0,  # SentencePiece ~approximate
}

# ---------------------------------------------------------------------------
# 토큰 카운터
# ---------------------------------------------------------------------------


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """텍스트의 토큰 수를 계산한다.

    tiktoken이 없으면 근사치(문자 수 / 3.5)를 사용한다.

    Args:
        text: 토큰 수를 계산할 텍스트.
        encoding_name: tiktoken 인코딩 이름.

    Returns:
        토큰 수.
    """
    if not text:
        return 0
    try:
        import tiktoken

        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except ImportError:
        return max(1, int(len(text) / 3.5))


def count_tokens_for_provider(text: str, provider: str) -> int:
    """프로바이더에 맞는 토큰 수를 계산한다.

    OpenAI는 tiktoken cl100k_base를 사용하고,
    Anthropic/Google은 문자 비율 근사치를 사용한다.

    Args:
        text: 토큰 수를 계산할 텍스트.
        provider: 프로바이더 이름 ("openai", "anthropic", "google").

    Returns:
        토큰 수.
    """
    if not text:
        return 0
    if provider == "openai":
        return count_tokens(text, "cl100k_base")
    ratio = PROVIDER_CHAR_RATIOS.get(provider, 3.5)
    return max(1, int(len(text) / ratio))


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BudgetCheckResult:
    """토큰 예산 검사 결과.

    Attributes:
        section_id: 섹션 식별자.
        budget: 할당된 예산 (토큰 수).
        actual: 실제 토큰 수.
        within_budget: 예산 내 여부.
        overage: 초과 토큰 수 (0이면 예산 내).
    """

    section_id: str
    budget: int
    actual: int
    within_budget: bool
    overage: int


# ---------------------------------------------------------------------------
# 기본 섹션별 토큰 예산
# ---------------------------------------------------------------------------

DEFAULT_TOKEN_BUDGETS: dict[str, int] = {
    "executive_summary": 800,
    "company_overview": 600,
    "business_overview": 600,
    "deal_overview": 500,
    "financial_analysis": 800,
    "transaction_structure": 500,
    "shareholder_structure": 400,
    "investment_highlights": 600,
    "market_overview": 700,
    "value_creation": 500,
    "growth_strategy": 600,
    "management_team": 500,
    "business_model": 500,
    "appendix": 300,
    "contact": 200,
}

DEFAULT_BUDGET = 500  # 미등록 섹션의 기본 예산


# ---------------------------------------------------------------------------
# TokenBudgetManager
# ---------------------------------------------------------------------------


class TokenBudgetManager:
    """섹션별 토큰 예산 관리자.

    Args:
        budgets: 섹션별 예산 딕셔너리. None이면 DEFAULT_TOKEN_BUDGETS 사용.
        encoding_name: tiktoken 인코딩 이름.
    """

    def __init__(
        self,
        budgets: dict[str, int] | None = None,
        encoding_name: str = "cl100k_base",
    ) -> None:
        self._budgets = budgets or dict(DEFAULT_TOKEN_BUDGETS)
        self._encoding_name = encoding_name

    def get_budget(self, section_id: str) -> int:
        """섹션의 토큰 예산을 반환한다."""
        return self._budgets.get(section_id, DEFAULT_BUDGET)

    def allocate(self, sections: list[str]) -> dict[str, int]:
        """주어진 섹션 목록에 대한 예산을 반환한다.

        Args:
            sections: 섹션 ID 리스트.

        Returns:
            {section_id: budget} 딕셔너리.
        """
        return {s: self.get_budget(s) for s in sections}

    def check_budget(self, section_id: str, text: str) -> BudgetCheckResult:
        """텍스트가 섹션 예산 내인지 검사한다.

        Args:
            section_id: 섹션 식별자.
            text: 검사할 텍스트.

        Returns:
            BudgetCheckResult.
        """
        budget = self.get_budget(section_id)
        actual = count_tokens(text, self._encoding_name)
        overage = max(0, actual - budget)

        return BudgetCheckResult(
            section_id=section_id,
            budget=budget,
            actual=actual,
            within_budget=actual <= budget,
            overage=overage,
        )

    def truncate_to_budget(self, text: str, max_tokens: int) -> str:
        """텍스트를 문장 단위로 잘라 토큰 예산에 맞춘다.

        마지막 완전한 문장까지만 유지한다.

        Args:
            text: 원본 텍스트.
            max_tokens: 최대 토큰 수.

        Returns:
            잘린 텍스트 (예산 내).
        """
        if count_tokens(text, self._encoding_name) <= max_tokens:
            return text

        # 문장 단위로 분할
        sentences = _split_sentences(text)
        result_sentences: list[str] = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = count_tokens(sentence, self._encoding_name)
            if current_tokens + sentence_tokens > max_tokens:
                break
            result_sentences.append(sentence)
            current_tokens += sentence_tokens

        if not result_sentences:
            # 첫 문장도 예산 초과 시 문자 단위로 자르기
            try:
                import tiktoken

                enc = tiktoken.get_encoding(self._encoding_name)
                tokens = enc.encode(text)[:max_tokens]
                return str(enc.decode(tokens))
            except ImportError:
                # 근사치 기반 자르기
                char_limit = int(max_tokens * 3.5)
                return text[:char_limit]

        return " ".join(result_sentences)

    @property
    def total_budget(self) -> int:
        """등록된 모든 섹션의 총 예산."""
        return sum(self._budgets.values())


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분할한다."""
    import re

    # 마침표/느낌표/물음표 후 공백으로 분할
    parts = re.split(r"(?<=[.!?。])\s+", text)
    return [p.strip() for p in parts if p.strip()]
