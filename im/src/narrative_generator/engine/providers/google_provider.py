"""Google Gemini 프로바이더 구현.

> 마지막 수정: 2026-02-11 21:38:33

Google Generative AI SDK의 GenerativeModel을 래핑한다.
주의: Gemini는 system instruction을 모델 초기화 시 설정하며,
messages가 아닌 contents를 사용한다.
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

DEFAULT_MODEL = "gemini-2.0-flash"


class GoogleProvider:
    """Google Gemini LLM 프로바이더.

    Args:
        api_key: Google AI API 키.
        default_model: 기본 모델명.
        client_factory: 테스트용 모델 팩토리 주입.
            ``(model_name, system_prompt) -> GenerativeModel`` 시그니처.
    """

    def __init__(
        self,
        api_key: str = "",
        default_model: str = DEFAULT_MODEL,
        client_factory: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._default_model = default_model
        self._client_factory = client_factory
        self._genai: Any = None
        self._available = False
        self._model_cache: dict[tuple[str, int], Any] = {}

        if client_factory is not None:
            self._available = True
        elif api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=api_key)
                self._genai = genai
                self._available = True
            except ImportError:
                logger.warning(
                    "google-generativeai 패키지 미설치 — Google 프로바이더 비활성"
                )

    @property
    def provider_name(self) -> ProviderName:
        return ProviderName.GOOGLE

    @property
    def is_available(self) -> bool:
        return self._available

    def _get_or_create_model(self, model_name: str, system_prompt: str) -> Any:
        """(model_name, system_prompt) 조합별 GenerativeModel을 캐싱한다."""
        cache_key = (model_name, hash(system_prompt))
        if cache_key not in self._model_cache:
            self._model_cache[cache_key] = self._genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt,
            )
        return self._model_cache[cache_key]

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
            if self._client_factory is not None:
                gen_model = self._client_factory(model_name, system_prompt)
            else:
                gen_model = self._get_or_create_model(model_name, system_prompt)

            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            response = gen_model.generate_content(
                user_prompt,
                generation_config=generation_config,
            )
            content = response.text if response.text else ""

            usage = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                um = response.usage_metadata
                usage = {
                    "prompt_tokens": getattr(um, "prompt_token_count", 0),
                    "completion_tokens": getattr(um, "candidates_token_count", 0),
                    "total_tokens": getattr(um, "total_token_count", 0),
                }

            return LLMResponse(
                text=content,
                provider=ProviderName.GOOGLE,
                model=model_name,
                usage=usage,
            )
        except Exception as exc:
            raise LLMAPIError(
                provider="google",
                original_error=str(exc),
            ) from exc
