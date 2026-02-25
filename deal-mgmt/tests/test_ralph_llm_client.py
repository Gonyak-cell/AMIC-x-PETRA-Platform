"""Ralph LLM Client 단위 테스트.

CostTracker, RalphLLMClient 폴백 체인, from_settings 팩토리를 검증한다.
"""

import pytest

from app.ralph.llm_client import COST_PER_1K, CostTracker, RalphLLMClient


# ── CostTracker ──────────────────────────────────────────────────────────────


class TestCostTracker:
    def test_initial_state(self):
        ct = CostTracker()
        assert ct.accumulated_usd == 0.0
        assert ct.call_count == 0
        assert ct.usage_by_model == {}

    def test_add_known_model(self):
        ct = CostTracker()
        cost = ct.add("gpt-4o", input_tokens=1000, output_tokens=500)
        expected = (1000 / 1000) * 0.0025 + (500 / 1000) * 0.01
        assert cost == pytest.approx(expected)
        assert ct.accumulated_usd == pytest.approx(expected)
        assert ct.call_count == 1
        assert ct.usage_by_model["gpt-4o"]["input_tokens"] == 1000
        assert ct.usage_by_model["gpt-4o"]["output_tokens"] == 500

    def test_add_unknown_model_uses_default(self):
        ct = CostTracker()
        cost = ct.add("unknown-model", input_tokens=1000, output_tokens=1000)
        default_cost = (1000 / 1000) * 0.003 + (1000 / 1000) * 0.015
        assert cost == pytest.approx(default_cost)

    def test_multiple_calls_accumulate(self):
        ct = CostTracker()
        c1 = ct.add("gpt-4o", 500, 200)
        c2 = ct.add("gpt-4o", 300, 100)
        assert ct.accumulated_usd == pytest.approx(c1 + c2)
        assert ct.call_count == 2
        assert ct.usage_by_model["gpt-4o"]["input_tokens"] == 800
        assert ct.usage_by_model["gpt-4o"]["output_tokens"] == 300

    def test_multiple_models(self):
        ct = CostTracker()
        ct.add("gpt-4o", 100, 50)
        ct.add("claude-sonnet-4-20250514", 200, 100)
        assert len(ct.usage_by_model) == 2
        assert ct.call_count == 2


# ── COST_PER_1K 테이블 ───────────────────────────────────────────────────────


class TestCostTable:
    def test_all_models_have_input_output(self):
        for model, rates in COST_PER_1K.items():
            assert "input" in rates, f"{model}에 input 비율이 없음"
            assert "output" in rates, f"{model}에 output 비율이 없음"
            assert rates["input"] > 0
            assert rates["output"] > 0

    def test_known_models_present(self):
        expected = {"claude-sonnet-4-20250514", "gpt-4o", "gemini-2.0-flash"}
        assert expected.issubset(set(COST_PER_1K.keys()))


# ── RalphLLMClient ────────────────────────────────────────────────────────────


class TestRalphLLMClient:
    def test_no_keys_not_available(self):
        client = RalphLLMClient()
        assert client.is_available is False

    def test_with_fake_key_adapter_registered(self):
        """API 키가 있으면 어댑터가 등록되지만, 라이브러리 없으면 is_available=False."""
        client = RalphLLMClient(anthropic_api_key="sk-test")
        # 어댑터는 등록되었으나, 라이브러리 설치 여부에 따라 is_available이 결정
        assert len(client._adapters) == 1
        assert client._adapters[0].provider_name == "anthropic"

    def test_fallback_order(self):
        """어댑터 등록 순서: Anthropic → OpenAI → Google."""
        client = RalphLLMClient(
            anthropic_api_key="a",
            openai_api_key="b",
            google_api_key="c",
        )
        assert len(client._adapters) == 3
        providers = [a.provider_name for a in client._adapters]
        assert providers == ["anthropic", "openai", "google"]

    def test_empty_key_not_registered(self):
        """빈 키는 어댑터로 등록되지 않는다."""
        client = RalphLLMClient(
            anthropic_api_key="",
            openai_api_key="real",
            google_api_key="",
        )
        assert len(client._adapters) == 1
        assert client._adapters[0].provider_name == "openai"

    def test_cost_tracker_property(self):
        client = RalphLLMClient()
        assert client.total_cost_usd == 0.0
        client.cost_tracker.add("gpt-4o", 1000, 500)
        assert client.total_cost_usd > 0

    def test_from_settings(self):
        """Settings 객체에서 팩토리 생성."""

        class FakeSettings:
            ANTHROPIC_API_KEY = "sk-ant-test"
            OPENAI_API_KEY = ""
            GOOGLE_API_KEY = "gai-test"
            RALPH_PRIMARY_MODEL = "claude-haiku-4-5-20251001"
            RALPH_JUDGE_MODEL = "gpt-4o-mini"

        client = RalphLLMClient.from_settings(FakeSettings())
        assert len(client._adapters) == 2
        assert client._adapters[0].provider_name == "anthropic"
        assert client._adapters[1].provider_name == "google"
        assert client._primary_model == "claude-haiku-4-5-20251001"
        assert client._judge_model == "gpt-4o-mini"

    def test_from_settings_missing_attrs(self):
        """Settings에 속성이 없어도 기본값으로 동작."""

        class EmptySettings:
            pass

        client = RalphLLMClient.from_settings(EmptySettings())
        assert len(client._adapters) == 0
        assert client.is_available is False

    @pytest.mark.asyncio
    async def test_call_no_provider_raises(self):
        """사용 가능한 프로바이더가 없으면 RuntimeError."""
        client = RalphLLMClient()
        with pytest.raises(RuntimeError, match="사용 가능한 LLM 프로바이더"):
            await client.call("system", "user")

    @pytest.mark.asyncio
    async def test_call_fallback_on_failure(self):
        """첫 어댑터 실패 시 두 번째 어댑터로 폴백."""
        client = RalphLLMClient(anthropic_api_key="a", openai_api_key="b")

        call_log = []

        # 첫 번째 어댑터: 실패
        async def fail_generate(system, user, *, model=None):
            call_log.append("anthropic")
            raise ConnectionError("fail")

        # 두 번째 어댑터: 성공
        async def ok_generate(system, user, *, model=None):
            call_log.append("openai")
            return "response text", "gpt-4o", 100, 50

        # Mock is_available
        client._adapters[0].is_available  # noqa: B018 — 접근만
        type(client._adapters[0]).is_available = property(lambda self: True)
        type(client._adapters[1]).is_available = property(lambda self: True)
        client._adapters[0].generate = fail_generate
        client._adapters[1].generate = ok_generate

        result = await client.call("sys", "usr")
        assert result == "response text"
        assert call_log == ["anthropic", "openai"]
        assert client.cost_tracker.call_count == 1

    @pytest.mark.asyncio
    async def test_call_success_first_adapter(self):
        """첫 어댑터 성공 시 바로 반환, 두 번째는 호출하지 않는다."""
        client = RalphLLMClient(anthropic_api_key="a", openai_api_key="b")

        async def ok_generate(system, user, *, model=None):
            return "claude response", "claude-sonnet-4-20250514", 200, 100

        type(client._adapters[0]).is_available = property(lambda self: True)
        type(client._adapters[1]).is_available = property(lambda self: True)
        client._adapters[0].generate = ok_generate

        result = await client.call("sys", "usr")
        assert result == "claude response"
        assert client.cost_tracker.call_count == 1

    @pytest.mark.asyncio
    async def test_call_with_model_fallback_to_call(self):
        """call_with_model에서 모든 어댑터 실패 시 기본 call로 폴백."""
        client = RalphLLMClient(openai_api_key="b")

        call_count = {"model": 0, "default": 0}

        async def fail_model(system, user, *, model=None):
            if model == "specific-model":
                call_count["model"] += 1
                raise ValueError("model not supported")
            call_count["default"] += 1
            return "default response", "gpt-4o", 50, 25

        type(client._adapters[0]).is_available = property(lambda self: True)
        client._adapters[0].generate = fail_model

        result = await client.call_with_model("sys", "usr", model="specific-model")
        assert result == "default response"
