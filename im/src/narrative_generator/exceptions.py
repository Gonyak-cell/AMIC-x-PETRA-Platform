"""Narrative Generator 예외 계층.

> 마지막 수정: 2026-02-10 11:52:29

NarrativeGeneratorError를 기반으로 RAG, 프롬프트, LLM, Fact Check 도메인별
세분화된 예외를 제공한다.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class NarrativeGeneratorError(Exception):
    """Narrative Generator 모듈 최상위 예외.

    Attributes:
        message: 사람이 읽을 수 있는 오류 메시지.
        details: 프로그래밍 방식 접근을 위한 구조화된 컨텍스트.
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class ConfigurationError(NarrativeGeneratorError):
    """설정 관련 오류 (API 키 누락, 잘못된 값 등)."""

    def __init__(self, field: str, reason: str = "") -> None:
        detail = f" — {reason}" if reason else ""
        super().__init__(
            message=f"설정 오류: '{field}'{detail}",
            details={"field": field, "reason": reason},
        )


# ---------------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------------


class RAGError(NarrativeGeneratorError):
    """RAG 파이프라인 관련 오류 기반."""


class EmbeddingError(RAGError):
    """임베딩 생성 실패."""

    def __init__(self, text_length: int, original_error: str = "") -> None:
        super().__init__(
            message=f"임베딩 생성 실패: 텍스트 길이={text_length}자 — {original_error}",
            details={"text_length": text_length, "original_error": original_error},
        )


class VectorStoreError(RAGError):
    """벡터 DB 연동 오류."""

    def __init__(self, operation: str, original_error: str = "") -> None:
        super().__init__(
            message=f"벡터 스토어 오류: {operation} — {original_error}",
            details={"operation": operation, "original_error": original_error},
        )


class ChunkingError(RAGError):
    """문서 청킹 실패."""

    def __init__(self, reason: str = "") -> None:
        super().__init__(
            message=f"문서 청킹 실패: {reason}",
            details={"reason": reason},
        )


class RetrievalError(RAGError):
    """컨텍스트 검색 실패."""

    def __init__(self, query: str = "", original_error: str = "") -> None:
        super().__init__(
            message=f"컨텍스트 검색 실패: {original_error}",
            details={"query": query, "original_error": original_error},
        )


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


class PromptError(NarrativeGeneratorError):
    """프롬프트 관련 오류 기반."""


class PromptNotFoundError(PromptError):
    """등록되지 않은 섹션 ID로 프롬프트 조회 시도."""

    def __init__(self, section_id: str) -> None:
        super().__init__(
            message=f"프롬프트 미등록: section_id='{section_id}'",
            details={"section_id": section_id},
        )


class PromptBuildError(PromptError):
    """프롬프트 조립 중 오류 (데이터 부족 등)."""

    def __init__(self, section_id: str, reason: str = "") -> None:
        super().__init__(
            message=f"프롬프트 조립 실패: section_id='{section_id}' — {reason}",
            details={"section_id": section_id, "reason": reason},
        )


# ---------------------------------------------------------------------------
# LLM / Engine
# ---------------------------------------------------------------------------


class LLMError(NarrativeGeneratorError):
    """LLM 호출 관련 오류 기반."""


class LLMAPIError(LLMError):
    """LLM API 호출 실패 (네트워크, 인증, Rate Limit 등)."""

    def __init__(self, provider: str = "openai", original_error: str = "") -> None:
        super().__init__(
            message=f"LLM API 호출 실패 ({provider}): {original_error}",
            details={"provider": provider, "original_error": original_error},
        )


class TokenBudgetExceededError(LLMError):
    """섹션별 토큰 예산 초과."""

    def __init__(
        self,
        section_id: str,
        budget: int,
        actual: int,
    ) -> None:
        super().__init__(
            message=(f"토큰 예산 초과: section_id='{section_id}' " f"예산={budget}, 실제={actual}"),
            details={
                "section_id": section_id,
                "budget": budget,
                "actual": actual,
            },
        )


# ---------------------------------------------------------------------------
# Fact Check
# ---------------------------------------------------------------------------


class FactCheckError(NarrativeGeneratorError):
    """팩트 체크 관련 오류 기반."""


class NumericClaimError(FactCheckError):
    """수치 클레임 검증 실패."""

    def __init__(
        self,
        claim: str,
        expected: str = "",
        actual: str = "",
    ) -> None:
        super().__init__(
            message=f"수치 불일치: '{claim}' — 예상='{expected}', 실제='{actual}'",
            details={"claim": claim, "expected": expected, "actual": actual},
        )


class ConsistencyError(FactCheckError):
    """내러티브 간 일관성 위반."""

    def __init__(
        self,
        metric: str,
        sections: list[str] | None = None,
    ) -> None:
        super().__init__(
            message=f"내러티브 일관성 위반: 지표='{metric}', 섹션={sections}",
            details={"metric": metric, "sections": sections or []},
        )
