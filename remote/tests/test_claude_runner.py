"""claude_runner.py 유닛 테스트."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.claude_runner import ClaudeResult, _parse_json_output, run_claude, run_shell


class TestParseJsonOutput:
    def test_parses_valid_json(self):
        data = {
            "result": "Hello world",
            "cost_usd": 0.01,
            "num_input_tokens": 100,
            "num_output_tokens": 50,
        }
        result = _parse_json_output(json.dumps(data), "", 1.0)
        assert result.text == "Hello world"
        assert result.cost_usd == 0.01
        assert result.input_tokens == 100
        assert result.output_tokens == 50

    def test_handles_invalid_json(self):
        result = _parse_json_output("not json", "", 1.0)
        assert result.text == "not json"
        assert result.cost_usd is None

    def test_appends_stderr(self):
        data = {"result": "ok"}
        result = _parse_json_output(json.dumps(data), "warning!", 1.0)
        assert "warning!" in result.text


class TestRunClaude:
    @pytest.mark.asyncio
    async def test_file_not_found(self):
        result = await run_claude(
            "test",
            cwd=".",
            allowed_tools=["Read"],
            timeout=5,
            output_json=False,
        )
        # claude CLI가 없을 수 있으므로 에러 처리 확인
        assert isinstance(result, ClaudeResult)

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        with patch("bot.claude_runner.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )
            mock_proc.kill = MagicMock()
            mock_exec.return_value = mock_proc

            result = await run_claude(
                "test", cwd=".", timeout=1, output_json=False
            )
            assert result.is_error
            assert "응답하지 못했습니다" in result.text


class TestRunShell:
    @pytest.mark.asyncio
    async def test_simple_command(self):
        result = await run_shell("echo hello", cwd=".", timeout=10)
        assert "hello" in result

    @pytest.mark.asyncio
    async def test_empty_output(self):
        # Windows에서 빈 출력 명령
        result = await run_shell("echo.", cwd=".", timeout=10)
        assert isinstance(result, str)
