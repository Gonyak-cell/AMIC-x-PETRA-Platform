"""Multi-LLM 클라이언트 테스트 — Sprint 14."""

from unittest.mock import patch

import pytest

from app.services.llm.client import (
    AnthropicClient,
    GeminiClient,
    LLMProvider,
    LLMResponse,
    OpenAIClient,
    create_llm_client,
    get_available_provider,
)


class TestLLMProvider:
    """LLMProvider enum 테스트."""

    def test_provider_values(self):
        assert LLMProvider.ANTHROPIC == "anthropic"
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.GEMINI == "gemini"

    def test_provider_from_string(self):
        assert LLMProvider("anthropic") == LLMProvider.ANTHROPIC
        assert LLMProvider("openai") == LLMProvider.OPENAI
        assert LLMProvider("gemini") == LLMProvider.GEMINI


class TestCreateLLMClient:
    """create_llm_client 팩토리 테스트."""

    def test_create_anthropic(self):
        client = create_llm_client("anthropic")
        assert isinstance(client, AnthropicClient)
        assert client.provider == LLMProvider.ANTHROPIC

    def test_create_openai(self):
        client = create_llm_client("openai")
        assert isinstance(client, OpenAIClient)
        assert client.provider == LLMProvider.OPENAI

    def test_create_gemini(self):
        client = create_llm_client("gemini")
        assert isinstance(client, GeminiClient)
        assert client.provider == LLMProvider.GEMINI

    def test_create_with_enum(self):
        client = create_llm_client(LLMProvider.ANTHROPIC)
        assert isinstance(client, AnthropicClient)

    def test_create_invalid_provider(self):
        with pytest.raises(ValueError):
            create_llm_client("invalid_provider")


class TestClientAvailability:
    """API 키 존재 여부 테스트."""

    def test_anthropic_no_key(self):
        with patch.dict("os.environ", {}, clear=True):
            client = AnthropicClient()
            assert client.is_available() is False

    def test_anthropic_with_key(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            client = AnthropicClient()
            assert client.is_available() is True

    def test_openai_no_key(self):
        with patch.dict("os.environ", {}, clear=True):
            client = OpenAIClient()
            assert client.is_available() is False

    def test_openai_with_key(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            client = OpenAIClient()
            assert client.is_available() is True

    def test_gemini_no_key(self):
        with patch.dict("os.environ", {}, clear=True):
            client = GeminiClient()
            assert client.is_available() is False

    def test_gemini_with_key(self):
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "AIza-test"}):
            client = GeminiClient()
            assert client.is_available() is True


class TestGetAvailableProvider:
    """자동 프로바이더 탐색 테스트."""

    def test_no_keys_returns_none(self):
        with patch.dict("os.environ", {}, clear=True):
            result = get_available_provider()
            assert result is None

    def test_anthropic_priority(self):
        with patch.dict(
            "os.environ",
            {
                "ANTHROPIC_API_KEY": "sk-ant",
                "OPENAI_API_KEY": "sk-oai",
            },
        ):
            result = get_available_provider()
            assert result is not None
            assert result.provider == LLMProvider.ANTHROPIC

    def test_openai_fallback(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-oai"}, clear=True):
            result = get_available_provider()
            assert result is not None
            assert result.provider == LLMProvider.OPENAI

    def test_gemini_fallback(self):
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "AIza"}, clear=True):
            result = get_available_provider()
            assert result is not None
            assert result.provider == LLMProvider.GEMINI


class TestLLMResponse:
    """LLMResponse 데이터 클래스 테스트."""

    def test_basic_response(self):
        resp = LLMResponse(
            content='{"result": "ok"}',
            model="claude-sonnet-4-5-20250929",
            provider=LLMProvider.ANTHROPIC,
            token_usage={"input_tokens": 100, "output_tokens": 50},
            finish_reason="end_turn",
        )
        assert resp.content == '{"result": "ok"}'
        assert resp.model == "claude-sonnet-4-5-20250929"
        assert resp.provider == LLMProvider.ANTHROPIC
        assert resp.token_usage["input_tokens"] == 100

    def test_default_values(self):
        resp = LLMResponse(
            content="test",
            model="gpt-4o",
            provider=LLMProvider.OPENAI,
        )
        assert resp.token_usage == {}
        assert resp.finish_reason == ""
