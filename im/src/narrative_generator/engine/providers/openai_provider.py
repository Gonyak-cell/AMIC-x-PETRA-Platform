"""OpenAI 프로바이더 구현 (GPT-4o 등).

> 마지막 수정: 2026-02-11 21:38:33
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

DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider:
    """OpenAI LLM 프로바이더.

    Args:
        api_key: OpenAI API 키.
        default_model: 기본 모델명.
        client: 주입된 OpenAI 클라이언트 (테스트용).
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
                from openai import OpenAI

                self._client = OpenAI(api_key=api_key)
                self._available = True
            except ImportError:
                logger.warning("openai 패키지 미설치 — OpenAI 프로바이더 비활성")

    @property
    def provider_name(self) -> ProviderName:
        return ProviderName.OPENAI

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
            response = self._client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or ""
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            return LLMResponse(
                text=content,
                provider=ProviderName.OPENAI,
                model=model_name,
                usage=usage,
            )
        except Exception as exc:
            raise LLMAPIError(
                provider="openai",
                original_error=str(exc),
            ) from exc
