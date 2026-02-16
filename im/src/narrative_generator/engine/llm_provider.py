"""LLM 프로바이더 추상화 계층.

> 마지막 수정: 2026-02-11 21:38:33

서로 다른 LLM 프로바이더(OpenAI, Anthropic, Google)를
통합된 인터페이스로 래핑한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable


class ProviderName(str, Enum):
    """지원되는 LLM 프로바이더 식별자."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


@dataclass(frozen=True)
class LLMResponse:
    """LLM 호출 결과.

    Attributes:
        text: 생성된 텍스트.
        provider: 사용된 프로바이더 식별자.
        model: 사용된 모델명.
        usage: 토큰 사용량 (선택적).
    """

    text: str
    provider: ProviderName
    model: str
    usage: dict[str, int] | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """LLM 프로바이더 프로토콜.

    모든 프로바이더는 이 인터페이스를 구현해야 한다.
    """

    @property
    def provider_name(self) -> ProviderName:
        """프로바이더 식별자."""
        ...

    @property
    def is_available(self) -> bool:
        """프로바이더가 사용 가능한지 (API 키 설정 + 패키지 설치)."""
        ...

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """텍스트를 생성한다.

        Args:
            system_prompt: 시스템 프롬프트.
            user_prompt: 유저 프롬프트.
            model: 모델명 (None이면 프로바이더 기본값 사용).
            temperature: 생성 온도.
            max_tokens: 최대 응답 토큰 수.

        Returns:
            LLMResponse.

        Raises:
            LLMAPIError: API 호출 실패 시.
        """
        ...
