"""Anthropic Claude 프로바이더 구현.

> 마지막 수정: 2026-02-11 21:38:33

Anthropic SDK의 messages.create() API를 래핑한다.
주의: Anthropic SDK는 system 프롬프트를 messages 배열이 아닌
별도 ``system`` 파라미터로 전달한다.
"""

from __future__ import annotations

import logging
from typing import Any

from src.narrative_generator.engine.llm_provider import (
    LLMResponse,
    ProviderName,
)
from src.narrative_generator.exceptions import LLMAPIError

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class AnthropicProvider:
    """Anthropic Claude LLM 프로바이더.

    Args:
        api_key: Anthropic API 키.
        default_model: 기본 모델명.
        client: 주입된 Anthropic 클라이언트 (테스트용).
    """

    def __init__(
        self,
        api_key: str = "",
        default_model: str = DEFAULT_MODEL,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._default_model = default_model
        self._client = client
        self._available = False

        if client is not None:
            self._available = True
        elif api_key:
            try:
                from anthropic import Anthropic

                self._client = Anthropic(api_key=api_key)
                self._available = True
            except ImportError:
                logger.warning("anthropic 패키지 미설치 — Anthropic 프로바이더 비활성")

    @property
    def provider_name(self) -> ProviderName:
        return ProviderName.ANTHROPIC

    @property
    def is_available(self) -> bool:
        return self._available

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        model_name = model or self._default_model
        try:
            response = self._client.messages.create(
                model=model_name,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.content[0].text if response.content else ""
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": (
                        response.usage.input_tokens + response.usage.output_tokens
                    ),
                }
            return LLMResponse(
                text=content,
                provider=ProviderName.ANTHROPIC,
                model=model_name,
                usage=usage,
            )
        except Exception as exc:
            raise LLMAPIError(
                provider="anthropic",
                original_error=str(exc),
            ) from exc
