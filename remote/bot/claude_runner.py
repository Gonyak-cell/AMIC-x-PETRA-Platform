"""
Claude Code CLI 실행기 — claude -p 서브프로세스를 관리한다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_APPEND = (
    "You are operating via Telegram remote control for the AMIC x PETRA Platform monorepo. "
    "Keep responses under 3000 characters when possible. Use code blocks for code. "
    "Structure: amic-platform/ (React frontend), fdd/ (FDD backend), "
    "kiis/ (KIIS backend), im/ (IM backend), deal-mgmt/ (MA backend)."
)


@dataclass
class ClaudeResult:
    text: str
    cost_usd: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_seconds: float = 0.0
    is_error: bool = False


async def run_claude(
    prompt: str,
    *,
    cwd: str | Path,
    allowed_tools: list[str] | None = None,
    continue_session: bool = False,
    model: str | None = None,
    max_turns: int = 10,
    max_budget_usd: float = 2.0,
    timeout: int = 300,
    output_json: bool = True,
) -> ClaudeResult:
    """claude -p 명령을 비대화형으로 실행하고 결과를 반환한다."""
    start = time.monotonic()

    cmd: list[str] = ["claude", "-p", prompt]

    if allowed_tools:
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])

    if continue_session:
        cmd.append("--continue")

    if model:
        cmd.extend(["--model", model])

    cmd.extend(["--max-turns", str(max_turns)])
    cmd.extend(["--max-budget-usd", str(max_budget_usd)])

    if output_json:
        cmd.extend(["--output-format", "json"])

    cmd.extend(["--append-system-prompt", SYSTEM_PROMPT_APPEND])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        duration = time.monotonic() - start
        raw_out = stdout.decode("utf-8", errors="replace").strip() if stdout else ""
        raw_err = stderr.decode("utf-8", errors="replace").strip() if stderr else ""

        # JSON 출력 파싱 시도
        if output_json and raw_out:
            return _parse_json_output(raw_out, raw_err, duration)

        # 일반 텍스트 출력
        text = raw_out or "(응답이 비어 있습니다)"
        if raw_err:
            text += f"\n\n⚠️ stderr:\n{raw_err}"

        return ClaudeResult(text=text, duration_seconds=duration)

    except asyncio.TimeoutError:
        try:
            proc.kill()  # type: ignore[possibly-undefined]
        except OSError:
            pass
        duration = time.monotonic() - start
        return ClaudeResult(
            text=f"⏰ Claude가 {timeout}초 안에 응답하지 못했습니다.",
            duration_seconds=duration,
            is_error=True,
        )

    except FileNotFoundError:
        return ClaudeResult(
            text=(
                "❌ 'claude' 명령어를 찾을 수 없습니다.\n"
                "Claude Code CLI가 설치되어 있고 PATH에 등록되어 있는지 확인하세요."
            ),
            duration_seconds=time.monotonic() - start,
            is_error=True,
        )

    except Exception as e:
        return ClaudeResult(
            text=f"❌ 오류 발생: {type(e).__name__}: {e}",
            duration_seconds=time.monotonic() - start,
            is_error=True,
        )


def _parse_json_output(
    raw_out: str, raw_err: str, duration: float
) -> ClaudeResult:
    """--output-format json 결과를 파싱한다."""
    try:
        data = json.loads(raw_out)
        text = data.get("result", raw_out)
        cost = data.get("cost_usd")
        input_tokens = data.get("num_input_tokens")
        output_tokens = data.get("num_output_tokens")

        if raw_err:
            text += f"\n\n⚠️ stderr:\n{raw_err}"

        return ClaudeResult(
            text=text,
            cost_usd=cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_seconds=duration,
        )
    except (json.JSONDecodeError, KeyError):
        # JSON 파싱 실패 시 원시 텍스트 반환
        text = raw_out
        if raw_err:
            text += f"\n\n⚠️ stderr:\n{raw_err}"
        return ClaudeResult(text=text, duration_seconds=duration)


async def run_shell(
    cmd: str,
    *,
    cwd: str | Path,
    timeout: int = 120,
) -> str:
    """Claude CLI 없이 셸 명령을 직접 실행한다 (프로젝트 명령어용)."""
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        out = stdout.decode("utf-8", errors="replace").strip() if stdout else ""
        err = stderr.decode("utf-8", errors="replace").strip() if stderr else ""

        result = out
        if err:
            result += f"\n\n⚠️ stderr:\n{err}"
        if not result.strip():
            result = "(출력 없음)"

        return result

    except asyncio.TimeoutError:
        try:
            proc.kill()  # type: ignore[possibly-undefined]
        except OSError:
            pass
        return f"⏰ 명령이 {timeout}초 안에 완료되지 못했습니다."

    except Exception as e:
        return f"❌ 오류 발생: {type(e).__name__}: {e}"
