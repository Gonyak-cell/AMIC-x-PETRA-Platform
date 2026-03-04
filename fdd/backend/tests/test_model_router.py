"""FDDModelRouter 단위 테스트 — Phase 6.

멀티모델 라우터의 resolve, generate, fallback 로직 검증.
실제 LLM API 호출 없이 mock 프로바이더로 테스트.
"""

from unittest.mock import MagicMock

import pytest

from app.services.llm.client import LLMClient, LLMProvider, LLMResponse
from app.services.llm.routing.model_router import (
    DEFAULT_FDD_ROUTING,
    FDDModelRouter,
    RoutingDecision,
)


def _make_mock_client(provider: LLMProvider, *, available: bool = True) -> LLMClient:
    """사용 가능/불가능한 mock LLMClient를 생성한다."""
    client = MagicMock(spec=LLMClient)
    client.provider = provider
    client.is_available.return_value = available
    client.chat.return_value = LLMResponse(
        content="mock response",
        model=f"mock-{provider.value}",
        provider=provider,
        token_usage={"prompt_tokens": 10, "completion_tokens": 20},
    )
    return client


def _make_all_available() -> dict[str, LLMClient]:
    """3개 프로바이더 모두 사용 가능한 mock 세트."""
    return {
        "openai": _make_mock_client(LLMProvider.OPENAI),
        "anthropic": _make_mock_client(LLMProvider.ANTHROPIC),
        "gemini": _make_mock_client(LLMProvider.GEMINI),
    }


class TestResolve:
    """FDDModelRouter.resolve() 테스트."""

    def test_quantitative_routes_to_openai(self):
        """정량 섹션은 OpenAI로 라우팅."""
        router = FDDModelRouter(providers=_make_all_available())
        decision = router.resolve("qoe_adjustment_classification")
        assert decision.provider == "openai"
        assert decision.is_fallback is False

    def test_strategic_routes_to_anthropic(self):
        """전략 섹션은 Anthropic으로 라우팅."""
        router = FDDModelRouter(providers=_make_all_available())
        decision = router.resolve("executive_summary")
        assert decision.provider == "anthropic"
        assert decision.is_fallback is False

    def test_support_routes_to_gemini(self):
        """지원 섹션은 Gemini로 라우팅."""
        router = FDDModelRouter(providers=_make_all_available())
        decision = router.resolve("methodology_description")
        assert decision.provider == "gemini"
        assert decision.is_fallback is False

    def test_fallback_when_primary_unavailable(self):
        """primary 불가 시 폴백 체인 순회."""
        providers = _make_all_available()
        providers["openai"] = _make_mock_client(LLMProvider.OPENAI, available=False)

        router = FDDModelRouter(providers=providers)
        decision = router.resolve("qoe_adjustment_classification")

        assert decision.provider == "anthropic"  # openai 폴백 → anthropic
        assert decision.is_fallback is True
        assert decision.original_provider == "openai"

    def test_fallback_chain_second(self):
        """primary + 1차 폴백 불가 시 2차 폴백."""
        providers = _make_all_available()
        providers["openai"] = _make_mock_client(LLMProvider.OPENAI, available=False)
        providers["anthropic"] = _make_mock_client(
            LLMProvider.ANTHROPIC, available=False
        )

        router = FDDModelRouter(providers=providers)
        decision = router.resolve("qoe_adjustment_classification")

        assert decision.provider == "gemini"  # openai → anthropic(X) → gemini
        assert decision.is_fallback is True

    def test_no_providers_raises_runtime_error(self):
        """모든 프로바이더 불가 시 RuntimeError."""
        providers = {
            "openai": _make_mock_client(LLMProvider.OPENAI, available=False),
            "anthropic": _make_mock_client(LLMProvider.ANTHROPIC, available=False),
            "gemini": _make_mock_client(LLMProvider.GEMINI, available=False),
        }
        router = FDDModelRouter(providers=providers)

        with pytest.raises(RuntimeError, match="사용 가능한 프로바이더가 없습니다"):
            router.resolve("qoe_adjustment_classification")

    def test_unknown_section_defaults_to_openai(self):
        """미등록 섹션은 openai로 기본 라우팅."""
        router = FDDModelRouter(providers=_make_all_available())
        decision = router.resolve("unknown_section_xyz")
        assert decision.provider == "openai"


class TestGenerate:
    """FDDModelRouter.generate() 테스트."""

    def test_generate_returns_fdd_llm_response(self):
        """generate()가 FDDLLMResponse를 올바르게 반환."""
        providers = _make_all_available()
        router = FDDModelRouter(providers=providers)

        response = router.generate(
            "executive_summary",
            system_prompt="You are a FDD analyst.",
            user_prompt="Summarize this deal.",
        )

        assert response.text == "mock response"
        assert response.provider == "anthropic"
        assert response.section_id == "executive_summary"
        assert response.is_fallback is False

    def test_generate_calls_correct_provider_client(self):
        """generate()가 라우팅된 프로바이더의 chat()을 호출."""
        providers = _make_all_available()
        router = FDDModelRouter(providers=providers)

        router.generate(
            "coa_mapping",
            system_prompt="system",
            user_prompt="user",
            temperature=0.1,
            max_tokens=2048,
        )

        providers["openai"].chat.assert_called_once()
        providers["anthropic"].chat.assert_not_called()
        providers["gemini"].chat.assert_not_called()

    def test_generate_with_fallback(self):
        """primary 불가 시 fallback provider로 generate."""
        providers = _make_all_available()
        providers["anthropic"] = _make_mock_client(
            LLMProvider.ANTHROPIC, available=False
        )

        router = FDDModelRouter(providers=providers)
        response = router.generate(
            "executive_summary",
            system_prompt="system",
            user_prompt="user",
        )

        assert response.provider == "openai"  # anthropic → openai
        assert response.is_fallback is True
        assert response.original_provider == "anthropic"


class TestProperties:
    """FDDModelRouter 프로퍼티 테스트."""

    def test_available_providers(self):
        """available_providers가 사용 가능한 것만 반환."""
        providers = _make_all_available()
        providers["gemini"] = _make_mock_client(LLMProvider.GEMINI, available=False)

        router = FDDModelRouter(providers=providers)
        available = router.available_providers
        assert "openai" in available
        assert "anthropic" in available
        assert "gemini" not in available

    def test_routing_summary(self):
        """routing_summary가 현재 라우팅 맵을 반환."""
        router = FDDModelRouter(providers=_make_all_available())
        summary = router.routing_summary
        assert summary == DEFAULT_FDD_ROUTING

    def test_custom_routing_map(self):
        """커스텀 라우팅 맵을 주입할 수 있어야 한다."""
        custom_map = {"my_section": "gemini"}
        router = FDDModelRouter(
            providers=_make_all_available(),
            routing_map=custom_map,
        )
        decision = router.resolve("my_section")
        assert decision.provider == "gemini"
