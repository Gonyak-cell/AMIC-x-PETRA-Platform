"""Multi-LLM 클라이언트 — Sprint 14.

Anthropic, OpenAI, Google Gemini를 통합 인터페이스로 제공.
에이전트별로 다른 프로바이더/모델 사용 가능.

사용 예:
    client = create_llm_client(LLMProvider.ANTHROPIC)
    response = client.chat(
        system_prompt="당신은 FDD 분석가입니다.",
        user_prompt="다음 계정을 분류하세요...",
        json_schema=schema,
    )
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMProvider(str, Enum):
    """지원 LLM 프로바이더."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"


@dataclass
class LLMResponse:
    """LLM 응답 표준 포맷."""

    content: str
    model: str
    provider: LLMProvider
    token_usage: dict[str, int] = field(default_factory=dict)
    finish_reason: str = ""


class LLMClient(ABC):
    """LLM 클라이언트 추상 기본 클래스."""

    provider: LLMProvider

    @abstractmethod
    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        json_schema: dict[str, Any] | None = None,
        timeout_seconds: int = 60,
    ) -> LLMResponse:
        """LLM에 채팅 요청을 보낸다.

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            model: 모델 ID (None이면 프로바이더 기본값)
            temperature: 온도 (0.0 = 결정론적)
            max_tokens: 최대 출력 토큰
            json_schema: JSON 스키마 (구조화 출력 강제)
            timeout_seconds: 타임아웃

        Returns:
            LLMResponse
        """

    @abstractmethod
    def is_available(self) -> bool:
        """API 키가 설정되어 사용 가능한지 확인한다."""


class AnthropicClient(LLMClient):
    """Anthropic Claude 클라이언트."""

    provider = LLMProvider.ANTHROPIC
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(self) -> None:
        self._api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._model = os.getenv("ANTHROPIC_MODEL_NAME", self.DEFAULT_MODEL)
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def is_available(self) -> bool:
        return bool(self._api_key)

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        json_schema: dict[str, Any] | None = None,
        timeout_seconds: int = 60,
    ) -> LLMResponse:
        client = self._get_client()
        model = model or self._model

        messages = [{"role": "user", "content": user_prompt}]

        # JSON 스키마가 있으면 시스템 프롬프트에 형식 지시 추가
        effective_system = system_prompt
        if json_schema:
            effective_system += (
                "\n\n반드시 다음 JSON 스키마에 맞는 JSON만 출력하세요. "
                "다른 텍스트 없이 순수 JSON만 반환하세요.\n"
                f"```json\n{json.dumps(json_schema, ensure_ascii=False, indent=2)}\n```"
            )

        logger.info(
            "Anthropic API call",
            extra={"ctx": {"model": model, "max_tokens": max_tokens}},
        )

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=effective_system,
            messages=messages,
            timeout=timeout_seconds,
        )

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        return LLMResponse(
            content=content,
            model=model,
            provider=self.provider,
            token_usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            finish_reason=response.stop_reason or "",
        )


class OpenAIClient(LLMClient):
    """OpenAI GPT 클라이언트."""

    provider = LLMProvider.OPENAI
    DEFAULT_MODEL = "gpt-4o"

    def __init__(self) -> None:
        self._api_key = os.getenv("OPENAI_API_KEY", "")
        self._model = os.getenv("OPENAI_MODEL_NAME", self.DEFAULT_MODEL)
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    def is_available(self) -> bool:
        return bool(self._api_key)

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        json_schema: dict[str, Any] | None = None,
        timeout_seconds: int = 60,
    ) -> LLMResponse:
        client = self._get_client()
        model = model or self._model

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout_seconds,
        }

        # JSON mode
        if json_schema:
            kwargs["response_format"] = {"type": "json_object"}

        logger.info(
            "OpenAI API call",
            extra={"ctx": {"model": model, "max_tokens": max_tokens}},
        )

        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        return LLMResponse(
            content=choice.message.content or "",
            model=model,
            provider=self.provider,
            token_usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            finish_reason=choice.finish_reason or "",
        )


class GeminiClient(LLMClient):
    """Google Gemini 클라이언트."""

    provider = LLMProvider.GEMINI
    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(self) -> None:
        self._api_key = os.getenv("GOOGLE_API_KEY", "")
        self._model = os.getenv("GOOGLE_MODEL_NAME", self.DEFAULT_MODEL)
        self._client: Any = None
        # 모델 인스턴스 캐싱 (system_prompt hash → GenerativeModel)
        self._model_cache: dict[str, Any] = {}

    def _get_client(self) -> Any:
        if self._client is None:
            import google.generativeai as genai

            genai.configure(api_key=self._api_key)
            self._client = genai
        return self._client

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _get_safety_settings(self) -> list[dict[str, str]]:
        """금융 분석에 적합한 안전 설정을 반환한다.

        'high risk', 'critical' 등 금융 용어가 차단되지 않도록
        모든 안전 카테고리를 BLOCK_NONE으로 설정.
        """
        return [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

    def _get_model_instance(
        self,
        model_name: str,
        system_prompt: str,
        generation_config: dict[str, Any],
    ) -> Any:
        """system_prompt 해시 기반 캐싱된 모델 인스턴스를 반환한다."""
        import hashlib

        genai = self._get_client()
        cache_key = hashlib.md5(f"{model_name}:{system_prompt}".encode()).hexdigest()

        if cache_key not in self._model_cache:
            self._model_cache[cache_key] = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt,
                generation_config=generation_config,
                safety_settings=self._get_safety_settings(),
            )

        return self._model_cache[cache_key]

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        json_schema: dict[str, Any] | None = None,
        timeout_seconds: int = 60,
    ) -> LLMResponse:
        model_name = model or self._model

        generation_config: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        if json_schema:
            generation_config["response_mime_type"] = "application/json"

        model_instance = self._get_model_instance(
            model_name,
            system_prompt,
            generation_config,
        )

        logger.info(
            "Gemini API call",
            extra={"ctx": {"model": model_name, "max_tokens": max_tokens}},
        )

        response = model_instance.generate_content(
            user_prompt,
            request_options={"timeout": timeout_seconds},
        )

        content = response.text or ""
        token_usage: dict[str, int] = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            token_usage = {
                "input_tokens": getattr(
                    response.usage_metadata, "prompt_token_count", 0
                ),
                "output_tokens": getattr(
                    response.usage_metadata, "candidates_token_count", 0
                ),
            }

        return LLMResponse(
            content=content,
            model=model_name,
            provider=self.provider,
            token_usage=token_usage,
            finish_reason="stop",
        )


# ── Factory ──────────────────────────────────────────────


_PROVIDERS: dict[LLMProvider, type[LLMClient]] = {
    LLMProvider.ANTHROPIC: AnthropicClient,
    LLMProvider.OPENAI: OpenAIClient,
    LLMProvider.GEMINI: GeminiClient,
}


def create_llm_client(provider: LLMProvider | str) -> LLMClient:
    """LLM 클라이언트를 생성한다.

    Args:
        provider: 프로바이더 이름 또는 LLMProvider enum

    Returns:
        해당 프로바이더의 LLMClient 인스턴스

    Raises:
        ValueError: 지원하지 않는 프로바이더
    """
    if isinstance(provider, str):
        provider = LLMProvider(provider.lower())

    client_cls = _PROVIDERS.get(provider)
    if client_cls is None:
        raise ValueError(
            f"지원하지 않는 LLM 프로바이더: {provider}. "
            f"사용 가능: {[p.value for p in LLMProvider]}"
        )

    return client_cls()


def get_available_provider() -> LLMClient | None:
    """사용 가능한 프로바이더를 우선순위 순으로 찾는다.

    우선순위: Anthropic > OpenAI > Gemini
    """
    for provider in [LLMProvider.ANTHROPIC, LLMProvider.OPENAI, LLMProvider.GEMINI]:
        client = create_llm_client(provider)
        if client.is_available():
            logger.info(
                "LLM provider selected",
                extra={"ctx": {"provider": provider.value}},
            )
            return client

    return None
