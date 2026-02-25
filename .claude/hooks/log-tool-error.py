#!/usr/bin/env python3
"""PostToolUse / PostToolUseFailure hook: 도구 실행 에러를 logs/errors.jsonl에 자동 기록."""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

CATEGORY_RULES = [
    (["pytest", "test", "vitest", "playwright"], "test"),
    (["npm", "vite", "tsc", "webpack", "esbuild"], "build"),
    (["ruff", "eslint", "mypy", "flake8", "prettier"], "lint"),
    (["alembic", "migrate"], "migration"),
    (["git"], "git"),
    (["docker", "docker-compose"], "docker"),
    (["python", "node", "uvicorn", "gunicorn"], "runtime"),
]


def categorize(command: str) -> str:
    cmd = command.lower()
    for keywords, category in CATEGORY_RULES:
        if any(k in cmd for k in keywords):
            return category
    return "other"


def extract_snippet(text: str, max_chars: int = 500) -> str:
    if not text:
        return ""
    lines = text.strip().splitlines()
    error_lines = [
        line
        for line in lines
        if re.search(r"error|fail|traceback|exception|assert", line, re.IGNORECASE)
    ]
    target = error_lines[-10:] if error_lines else lines[-15:]
    snippet = "\n".join(target)
    return snippet[:max_chars]


def sanitize_str(value: str) -> str:
    """Windows 한글 경로 등에서 발생하는 surrogate 문자 제거."""
    return value.encode("utf-8", errors="replace").decode("utf-8")


def main():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    event = data.get("hook_event_name", "")
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", {})

    # PostToolUse (Bash): returnCode > 0만 기록
    if event == "PostToolUse":
        if tool_name != "Bash":
            sys.exit(0)
        stdout = tool_response.get("stdout", "") if isinstance(tool_response, dict) else str(tool_response)
        stderr = tool_response.get("stderr", "") if isinstance(tool_response, dict) else ""
        return_code = tool_response.get("returnCode", 0) if isinstance(tool_response, dict) else 0
        if not return_code or return_code == 0:
            sys.exit(0)
        command = tool_input.get("command", "") if isinstance(tool_input, dict) else str(tool_input)
        error_text = stderr or stdout

    # PostToolUseFailure: 모든 도구 실패 기록
    elif event == "PostToolUseFailure":
        return_code = 1
        command = ""
        if isinstance(tool_input, dict):
            command = tool_input.get("command", tool_input.get("file_path", ""))
        else:
            command = str(tool_input)
        error_text = data.get("error", "")

    else:
        sys.exit(0)

    # 프로젝트 디렉토리 결정
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", data.get("cwd", "."))
    log_path = Path(sanitize_str(project_dir)) / "logs" / "errors.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "session_id": sanitize_str(data.get("session_id", "")),
        "event": event,
        "tool_name": tool_name,
        "command": sanitize_str(command[:300]),
        "return_code": return_code,
        "error_snippet": sanitize_str(extract_snippet(error_text)),
        "category": categorize(command),
        "cwd": sanitize_str(data.get("cwd", "")),
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
