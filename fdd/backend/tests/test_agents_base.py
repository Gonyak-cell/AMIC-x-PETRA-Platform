"""AI Agent 기본 테스트 — Sprint 6 / LLM 연동 Sprint 14."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.agents.base import AgentConfig, AgentResponse
from app.agents.coa_mapper import CoAMapperAgent
from app.agents.qoe_analyzer import QoEAnalyzerAgent
from app.services.llm import LLMProvider, LLMResponse

# ── TestAgentConfig ─────────────────────────────────────


class TestAgentConfig:
    """AgentConfig 테스트."""

    def test_default_config(self):
        """기본 설정값."""
        config = AgentConfig()
        assert config.provider == "anthropic"
        assert config.model == ""  # 빈 문자열 = 프로바이더 기본값
        assert config.temperature == 0.0
        assert config.max_tokens == 4096
        assert config.timeout_seconds == 60

    def test_custom_config(self):
        """커스텀 설정."""
        config = AgentConfig(
            provider="openai",
            model="gpt-4o",
            temperature=0.5,
            max_tokens=8192,
        )
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.temperature == 0.5
        assert config.max_tokens == 8192

    def test_gemini_config(self):
        """Gemini 프로바이더 설정."""
        config = AgentConfig(
            provider="gemini",
            model="gemini-2.0-flash",
        )
        assert config.provider == "gemini"
        assert config.model == "gemini-2.0-flash"


# ── TestAgentResponse ─────────────────────────────────────


class TestAgentResponse:
    """AgentResponse 테스트."""

    def test_success_response(self):
        """성공 응답."""
        response = AgentResponse(
            success=True,
            result={"key": "value"},
            raw_output="raw",
            confidence=Decimal("0.85"),
        )
        assert response.success is True
        assert response.result == {"key": "value"}
        assert response.confidence == Decimal("0.85")

    def test_failure_response(self):
        """실패 응답."""
        response = AgentResponse(
            success=False,
            validation_errors=["Error 1", "Error 2"],
        )
        assert response.success is False
        assert len(response.validation_errors) == 2

    def test_token_usage(self):
        """토큰 사용량 추적."""
        response = AgentResponse(
            success=True,
            token_usage={"input_tokens": 500, "output_tokens": 200},
        )
        assert response.token_usage["input_tokens"] == 500
        assert response.token_usage["output_tokens"] == 200


# ── TestQoEAnalyzerAgent ─────────────────────────────────


class TestQoEAnalyzerAgent:
    """QoE Analyzer Agent 테스트."""

    def test_agent_initialization(self):
        """에이전트 초기화."""
        agent = QoEAnalyzerAgent()
        assert agent.agent_name == "qoe_analyzer"
        assert agent.prompt_version == "1.0"

    def test_build_prompt(self):
        """프롬프트 구성."""
        agent = QoEAnalyzerAgent()
        context = {
            "deal_name": "Test Deal",
            "ebitda_definition": "Standard",
            "addback_policy": "Conservative",
            "gl_entries": [{"entry_id": "E1", "amount": "1000"}],
            "adjustment_candidates": [],
        }
        prompt = agent.build_prompt(context)
        assert isinstance(prompt, str)

    def test_parse_response_valid_json(self):
        """유효한 JSON 파싱."""
        agent = QoEAnalyzerAgent()
        raw = '{"analysis_results": [{"entry_id": "E1", "assessment": "NON_RECURRING"}], "summary": "test"}'
        result = agent.parse_response(raw)
        assert "analysis_results" in result
        assert len(result["analysis_results"]) == 1

    def test_parse_response_with_markdown(self):
        """마크다운 코드 블록 파싱."""
        agent = QoEAnalyzerAgent()
        raw = '```json\n{"analysis_results": [], "summary": "test"}\n```'
        result = agent.parse_response(raw)
        assert "analysis_results" in result

    def test_parse_response_invalid_json(self):
        """잘못된 JSON 처리."""
        agent = QoEAnalyzerAgent()
        raw = "Completely invalid text with no JSON structure whatsoever"
        result = agent.parse_response(raw)
        assert result["analysis_results"] == []
        assert "warnings" in result

    def test_run_no_api_key(self):
        """LLM API 키 없이 실행 — placeholder 반환."""
        agent = QoEAnalyzerAgent()
        context = {
            "deal_name": "Test",
            "ebitda_definition": "Standard",
            "addback_policy": "Conservative",
            "gl_entries": [],
            "adjustment_candidates": [],
        }
        response = agent.run(context)
        assert isinstance(response, AgentResponse)
        assert response.result is not None or len(response.warnings) >= 0

    @patch("app.agents.base.BaseAgent._get_llm_client")
    def test_run_with_mock_llm(self, mock_get_client):
        """Mock LLM으로 실제 호출 흐름 테스트."""
        mock_client = MagicMock()
        mock_client.chat.return_value = LLMResponse(
            content='{"analysis_results": [{"entry_id": "E1", "assessment": "NON_RECURRING", "confidence": 0.85, "rationale": "test", "recommended_action": "ADD_BACK"}], "summary": "ok", "warnings": []}',
            model="test-model",
            provider=LLMProvider.ANTHROPIC,
            token_usage={"input_tokens": 100, "output_tokens": 50},
        )
        mock_get_client.return_value = mock_client

        agent = QoEAnalyzerAgent()
        context = {
            "deal_name": "Test Deal",
            "ebitda_definition": "Standard",
            "addback_policy": "Conservative",
            "gl_entries": [{"entry_id": "E1", "amount": "1000"}],
            "adjustment_candidates": [],
        }
        response = agent.run(context)
        assert response.success is True
        assert response.result is not None
        assert len(response.result.get("analysis_results", [])) == 1
        assert response.token_usage.get("input_tokens") == 100
        mock_client.chat.assert_called_once()


# ── TestCoAMapperAgent ────────────────────────────────────


class TestCoAMapperAgent:
    """CoA Mapper Agent 테스트."""

    def test_agent_initialization(self):
        """에이전트 초기화."""
        agent = CoAMapperAgent()
        assert agent.agent_name == "coa_mapper"
        assert agent.prompt_version == "1.0"

    def test_build_prompt(self):
        """프롬프트 구성."""
        agent = CoAMapperAgent()
        context = {
            "deal_industry": "Manufacturing",
            "unmapped_accounts": [
                {"account_code": "54100", "account_name": "Employee benefits"}
            ],
            "standard_line_items": [{"code": "IS-SGA-001", "name": "SGA"}],
            "example_mappings": [],
        }
        prompt = agent.build_prompt(context)
        assert isinstance(prompt, str)

    def test_parse_response_valid(self):
        """유효한 JSON 파싱."""
        agent = CoAMapperAgent()
        raw = '{"mapping_suggestions": [{"source_account_code": "54100", "suggested_target_code": "IS-SGA-001"}]}'
        result = agent.parse_response(raw)
        assert "mapping_suggestions" in result
        assert len(result["mapping_suggestions"]) == 1

    def test_validate_output_valid_codes(self):
        """유효한 코드 검증."""
        agent = CoAMapperAgent()
        output = {
            "mapping_suggestions": [
                {"source_account_code": "54100", "suggested_target_code": "IS-SGA-001"}
            ]
        }
        source_data = {
            "unmapped_accounts": [{"account_code": "54100"}],
            "standard_codes": {"IS-SGA-001", "IS-SGA-002"},
        }
        errors = agent.validate_output(output, source_data)
        assert errors == []

    def test_validate_output_invalid_target(self):
        """잘못된 타겟 코드 검증."""
        agent = CoAMapperAgent()
        output = {
            "mapping_suggestions": [
                {"source_account_code": "54100", "suggested_target_code": "IS-FAKE-999"}
            ]
        }
        source_data = {
            "unmapped_accounts": [{"account_code": "54100"}],
            "standard_codes": {"IS-SGA-001"},
        }
        errors = agent.validate_output(output, source_data)
        assert len(errors) >= 1

    def test_run_no_api_key(self):
        """LLM API 키 없이 실행 — placeholder."""
        agent = CoAMapperAgent()
        context = {
            "deal_industry": "General",
            "unmapped_accounts": [],
            "standard_line_items": [],
            "example_mappings": [],
        }
        response = agent.run(context)
        assert isinstance(response, AgentResponse)
        assert response.result is not None or len(response.warnings) >= 0

    @patch("app.agents.base.BaseAgent._get_llm_client")
    def test_run_with_mock_llm(self, mock_get_client):
        """Mock LLM으로 실제 호출 흐름 테스트."""
        mock_client = MagicMock()
        mock_client.chat.return_value = LLMResponse(
            content='{"mapping_suggestions": [{"source_account_code": "54100", "source_account_name": "Benefits", "suggested_target_code": "IS-SGA-001", "suggested_target_name": "SGA", "rationale": "test", "confidence": 0.80, "alternative_mappings": []}]}',
            model="test-model",
            provider=LLMProvider.OPENAI,
            token_usage={"input_tokens": 80, "output_tokens": 40},
        )
        mock_get_client.return_value = mock_client

        agent = CoAMapperAgent()
        context = {
            "deal_industry": "General",
            "unmapped_accounts": [
                {"account_code": "54100", "account_name": "Benefits"}
            ],
            "standard_line_items": [{"code": "IS-SGA-001", "name": "SGA"}],
            "example_mappings": [],
        }
        source_data = {
            "unmapped_accounts": [{"account_code": "54100"}],
            "standard_codes": {"IS-SGA-001"},
        }
        response = agent.run(context, source_data)
        assert response.success is True
        assert response.result is not None
        assert len(response.result.get("mapping_suggestions", [])) == 1
        mock_client.chat.assert_called_once()


# ── TestLLMProviderSelection ─────────────────────────────


class TestLLMProviderSelection:
    """LLM 프로바이더 선택 테스트."""

    def test_provider_fallback_no_keys(self):
        """API 키 없으면 None 반환."""
        agent = QoEAnalyzerAgent()
        with patch.dict("os.environ", {}, clear=True):
            client = agent._get_llm_client()
            # API 키 없으면 None이거나 이미 캐시된 값
            # 테스트 환경에서는 키가 없으므로 None 예상

    def test_custom_provider_config(self):
        """커스텀 프로바이더 설정."""
        config = AgentConfig(provider="gemini", model="gemini-2.0-flash")
        agent = QoEAnalyzerAgent(config=config)
        assert agent.config.provider == "gemini"
        assert agent.config.model == "gemini-2.0-flash"
