"""Ralph Loop LLM 클라이언트 — 멀티 프로바이더 폴백 + 비용 추적.

IM 모듈의 LLMProvider 패턴을 참조하되, Ralph Loop 특화:
- async (system, user) -> str 시그니처 통일
- 비용 추적 내장
- 폴백 체인 (Anthropic → OpenAI → Google)
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── 비용 추적 ─────────────────────────────────────────────────────────────────

# 1K 토큰당 USD (2026-02 기준 추정)
COST_PER_1K: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514":  {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5-20251001": {"input": 0.001, "output": 0.005},
    "gpt-4o":                    {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini":               {"input": 0.00015, "output": 0.0006},
    "gemini-2.0-flash":          {"input": 0.0001, "output": 0.0004},
}


@dataclass
class CostTracker:
    """LLM 호출 비용 누적 추적기."""

    accumulated_usd: float = 0.0
    call_count: int = 0
    usage_by_model: dict[str, dict[str, int]] = field(default_factory=dict)

    def add(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """호출 비용을 기록하고 해당 호출 비용을 반환한다."""
        rates = COST_PER_1K.get(model, {"input": 0.003, "output": 0.015})
        cost = (input_tokens / 1000) * rates["input"] + (output_tokens / 1000) * rates["output"]
        self.accumulated_usd += cost
        self.call_count += 1

        if model not in self.usage_by_model:
            self.usage_by_model[model] = {"input_tokens": 0, "output_tokens": 0}
        self.usage_by_model[model]["input_tokens"] += input_tokens
        self.usage_by_model[model]["output_tokens"] += output_tokens

        return cost


# ── 어댑터 추상 클래스 ────────────────────────────────────────────────────────


class _LLMAdapter(ABC):
    """LLM 프로바이더 어댑터 인터페이스."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    async def generate(
        self, system: str, user: str, *, model: str | None = None
    ) -> tuple[str, str, int, int]:
        """(text, model_used, input_tokens, output_tokens)를 반환."""
        ...


# ── Anthropic 어댑터 ─────────────────────────────────────────────────────────


class _AnthropicAdapter(_LLMAdapter):
    """Anthropic (Claude) 어댑터."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        self._api_key = api_key
        self._model = model
        self._client = None

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    async def generate(
        self, system: str, user: str, *, model: str | None = None
    ) -> tuple[str, str, int, int]:
        import anthropic

        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)

        model_id = model or self._model
        response = await self._client.messages.create(
            model=model_id,
            max_tokens=4096,
            temperature=0.3,
            system=system,
            messages=[{"role": "user", "content": user}],
        )

        text = response.content[0].text if response.content else ""
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        return text, model_id, input_tokens, output_tokens


# ── OpenAI 어댑터 ────────────────────────────────────────────────────────────


class _OpenAIAdapter(_LLMAdapter):
    """OpenAI (GPT-4o) 어댑터."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self._api_key = api_key
        self._model = model
        self._client = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    async def generate(
        self, system: str, user: str, *, model: str | None = None
    ) -> tuple[str, str, int, int]:
        import openai

        if self._client is None:
            self._client = openai.AsyncOpenAI(api_key=self._api_key)

        model_id = model or self._model
        response = await self._client.chat.completions.create(
            model=model_id,
            temperature=0.3,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        text = response.choices[0].message.content or ""
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        return text, model_id, input_tokens, output_tokens


# ── Google 어댑터 ────────────────────────────────────────────────────────────


class _GoogleAdapter(_LLMAdapter):
    """Google (Gemini) 어댑터 — 동기 API를 async 래핑."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self._api_key = api_key
        self._model = model
        self._configured = False

    @property
    def provider_name(self) -> str:
        return "google"

    @property
    def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            import google.generativeai  # noqa: F401
            return True
        except ImportError:
            return False

    async def generate(
        self, system: str, user: str, *, model: str | None = None
    ) -> tuple[str, str, int, int]:
        import google.generativeai as genai

        if not self._configured:
            genai.configure(api_key=self._api_key)
            self._configured = True

        model_id = model or self._model

        def _sync_call() -> tuple[str, int, int]:
            gm = genai.GenerativeModel(
                model_name=model_id,
                system_instruction=system,
            )
            response = gm.generate_content(
                user,
                generation_config=genai.GenerationConfig(temperature=0.3, max_output_tokens=4096),
            )
            text = response.text or ""
            # Gemini usage 추출
            usage = getattr(response, "usage_metadata", None)
            inp = getattr(usage, "prompt_token_count", 0) if usage else 0
            out = getattr(usage, "candidates_token_count", 0) if usage else 0
            return text, inp, out

        text, input_tokens, output_tokens = await asyncio.to_thread(_sync_call)
        return text, model_id, input_tokens, output_tokens


# ── 메인 클라이언트 ──────────────────────────────────────────────────────────


class RalphLLMClient:
    """Ralph Loop 전용 LLM 클라이언트.

    - 멀티 프로바이더 폴백 체인 (Anthropic → OpenAI → Google)
    - 비용 추적 내장
    - `call()` 메서드가 `async (system, user) -> str` 시그니처 제공
    """

    def __init__(
        self,
        *,
        anthropic_api_key: str = "",
        openai_api_key: str = "",
        google_api_key: str = "",
        primary_model: str = "claude-sonnet-4-20250514",
        judge_model: str = "gpt-4o",
    ) -> None:
        self._adapters: list[_LLMAdapter] = []
        self._cost_tracker = CostTracker()
        self._primary_model = primary_model
        self._judge_model = judge_model

        # 폴백 순서: Anthropic → OpenAI → Google
        if anthropic_api_key:
            self._adapters.append(_AnthropicAdapter(anthropic_api_key, primary_model))
        if openai_api_key:
            self._adapters.append(_OpenAIAdapter(openai_api_key, judge_model))
        if google_api_key:
            self._adapters.append(_GoogleAdapter(google_api_key))

    @classmethod
    def from_settings(cls, settings) -> RalphLLMClient:
        """Settings 객체에서 인스턴스를 생성한다."""
        return cls(
            anthropic_api_key=getattr(settings, "ANTHROPIC_API_KEY", ""),
            openai_api_key=getattr(settings, "OPENAI_API_KEY", ""),
            google_api_key=getattr(settings, "GOOGLE_API_KEY", ""),
            primary_model=getattr(settings, "RALPH_PRIMARY_MODEL", "claude-sonnet-4-20250514"),
            judge_model=getattr(settings, "RALPH_JUDGE_MODEL", "gpt-4o"),
        )

    @property
    def is_available(self) -> bool:
        """사용 가능한 프로바이더가 하나라도 있는지."""
        return any(a.is_available for a in self._adapters)

    @property
    def cost_tracker(self) -> CostTracker:
        return self._cost_tracker

    @property
    def total_cost_usd(self) -> float:
        return self._cost_tracker.accumulated_usd

    async def call(self, system: str, user: str) -> str:
        """LLM 호출 — 폴백 체인 순서대로 시도, 비용 자동 기록.

        이 메서드의 시그니처 `async (str, str) -> str`는
        LDDSectionAnalyzer, LLMJudgeGate 등의 `llm_call` 파라미터와 호환.
        """
        last_error: Exception | None = None

        for adapter in self._adapters:
            if not adapter.is_available:
                continue
            try:
                text, model_used, inp, out = await adapter.generate(system, user)
                self._cost_tracker.add(model_used, inp, out)
                logger.debug(
                    "LLM 호출 성공: provider=%s, model=%s, tokens=%d+%d, cost=$%.4f",
                    adapter.provider_name, model_used, inp, out, self._cost_tracker.accumulated_usd,
                )
                return text
            except Exception as exc:
                last_error = exc
                logger.warning("LLM 호출 실패 (%s): %s — 다음 프로바이더로 폴백", adapter.provider_name, exc)

        raise RuntimeError(
            f"사용 가능한 LLM 프로바이더가 없습니다. 마지막 에러: {last_error}"
        )

    async def call_with_model(self, system: str, user: str, *, model: str) -> str:
        """특정 모델을 지정하여 호출한다 (Judge Panel용)."""
        for adapter in self._adapters:
            if not adapter.is_available:
                continue
            try:
                text, model_used, inp, out = await adapter.generate(system, user, model=model)
                self._cost_tracker.add(model_used, inp, out)
                return text
            except Exception:
                continue
        return await self.call(system, user)  # 폴백

    async def call_for_provider(self, system: str, user: str, *, provider: str) -> str:
        """특정 프로바이더를 지정하여 호출한다 (LDD 라우터용).

        지정된 프로바이더가 사용 불가하거나 실패하면 나머지로 폴백.
        """
        # 1. 지정된 프로바이더 먼저 시도
        for adapter in self._adapters:
            if adapter.provider_name == provider and adapter.is_available:
                try:
                    text, model_used, inp, out = await adapter.generate(system, user)
                    self._cost_tracker.add(model_used, inp, out)
                    logger.debug(
                        "프로바이더 지정 호출 성공: provider=%s, model=%s",
                        provider, model_used,
                    )
                    return text
                except Exception as exc:
                    logger.warning(
                        "프로바이더 지정 호출 실패 (%s): %s — 폴백 시도",
                        provider, exc,
                    )
                    break

        # 2. 폴백: 지정 프로바이더 외 나머지 순회
        last_error: Exception | None = None
        for adapter in self._adapters:
            if adapter.provider_name == provider or not adapter.is_available:
                continue
            try:
                text, model_used, inp, out = await adapter.generate(system, user)
                self._cost_tracker.add(model_used, inp, out)
                logger.info(
                    "프로바이더 폴백 성공: 원래=%s, 폴백=%s",
                    provider, adapter.provider_name,
                )
                return text
            except Exception as exc:
                last_error = exc
                continue

        # 3. 모두 실패 → 기본 call()
        return await self.call(system, user)

    async def call_parallel(
        self,
        tasks: list[tuple[str, str, str]],
    ) -> list[str]:
        """여러 프로바이더를 병렬 호출한다 (Stage 3/4 듀얼 분석용).

        Args:
            tasks: [(system_prompt, user_prompt, provider_name), ...]

        Returns:
            각 태스크의 응답 문자열 리스트 (순서 보장).
        """
        import asyncio

        async def _single(system: str, user: str, provider: str) -> str:
            return await self.call_for_provider(system, user, provider=provider)

        coros = [_single(s, u, p) for s, u, p in tasks]
        return await asyncio.gather(*coros)
