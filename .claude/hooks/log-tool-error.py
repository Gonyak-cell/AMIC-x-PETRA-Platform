#!/usr/bin/env python3
"""PostToolUse / PostToolUseFailure hook: 도구 실행 에러를 logs/errors.jsonl에 자동 기록."""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CATEGORY_RULES = [
    (["pytest", "test", "vitest", "playwright"], "test"),
    (["npm", "vite", "tsc", "webpack", "esbuild"], "build"),
    (["ruff", "eslint", "mypy", "flake8", "prettier"], "lint"),
    (["alembic", "migrate"], "migration"),
    (["git"], "git"),
    (["docker", "docker-compose"], "docker"),
    (["python", "node", "uvicorn", "gunicorn"], "runtime"),
    (["pip", "uv", "poetry", "conda"], "dependency"),
    (["ssh", "scp", "curl", "wget"], "network"),
]

# 에러 텍스트 기반 카테고리 분류 (command로 분류 안 될 때 사용)
ERROR_CATEGORY_RULES = [
    (["no such file", "filenotfounderror", "not found", "cannot find"], "path_error"),
    (["encoding", "unicode", "surrogate", "codec", "charmap"], "encoding_error"),
    (["permission denied", "access denied", "eacces"], "permission_error"),
    (["timeout", "timed out", "connection refused"], "network_error"),
    (["import", "modulenotfounderror", "no module named"], "import_error"),
]


def categorize(command: str, error_text: str = "") -> str:
    cmd = command.lower()
    for keywords, category in CATEGORY_RULES:
        if any(k in cmd for k in keywords):
            return category
    # command로 분류 안 되면 에러 텍스트로 시도
    if error_text:
        err_lower = error_text.lower()
        for keywords, category in ERROR_CATEGORY_RULES:
            if any(k in err_lower for k in keywords):
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


KST = timezone(timedelta(hours=9))

# Cascade 감지 설정
CASCADE_TIME_WINDOW_SEC = 300  # 5분 이내 연속 에러 = cascade
CASCADE_ALERT_THRESHOLD = 3  # 3회 연속 시 경고


def compute_cascade(
    log_path: Path, session_id: str, current_ts: datetime
) -> tuple[int, str, float | None]:
    """현재 세션의 cascade depth를 계산한다.

    Returns:
        (cascade_depth, preceding_category, time_since_last_error_sec)
    """
    if not log_path.exists() or not session_id:
        return 1, "", None

    # 파일 끝에서 최근 레코드만 읽기 (성능 보장)
    try:
        with open(log_path, "rb") as f:
            # 마지막 8KB만 읽어서 역순 파싱
            f.seek(0, 2)
            file_size = f.tell()
            read_size = min(file_size, 8192)
            f.seek(file_size - read_size)
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return 1, "", None

    lines = tail.strip().splitlines()
    session_errors: list[dict[str, str]] = []
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if rec.get("session_id") == session_id:
            session_errors.append(rec)
            if len(session_errors) >= 10:
                break

    if not session_errors:
        return 1, "", None

    # 가장 최근 에러와의 시간 차이 계산
    last = session_errors[0]
    last_ts_str = last.get("ts", "")
    preceding_cat = last.get("category", "")

    try:
        last_ts = datetime.fromisoformat(last_ts_str)
        delta = (current_ts - last_ts).total_seconds()
    except (ValueError, TypeError):
        return 1, preceding_cat, None

    if delta > CASCADE_TIME_WINDOW_SEC:
        return 1, preceding_cat, delta

    # cascade chain 길이 계산 (시간 윈도우 내 연속 에러)
    depth = 1
    prev_ts = current_ts
    for rec in session_errors:
        try:
            rec_ts = datetime.fromisoformat(rec.get("ts", ""))
        except (ValueError, TypeError):
            break
        gap = (prev_ts - rec_ts).total_seconds()
        if gap <= CASCADE_TIME_WINDOW_SEC:
            depth += 1
            prev_ts = rec_ts
        else:
            break

    return depth, preceding_cat, delta


def emit_cascade_alert(
    log_path: Path, session_id: str, depth: int, current_category: str
) -> None:
    """cascade_depth가 임계값 이상이면 stderr로 경고를 출력한다."""
    if depth < CASCADE_ALERT_THRESHOLD:
        return

    # 최근 에러 체인 요약 수집
    chain: list[str] = []
    try:
        with open(log_path, "rb") as f:
            f.seek(0, 2)
            file_size = f.tell()
            read_size = min(file_size, 8192)
            f.seek(file_size - read_size)
            tail = f.read().decode("utf-8", errors="replace")
        for line in reversed(tail.strip().splitlines()):
            try:
                rec = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if rec.get("session_id") == session_id:
                chain.append(rec.get("category", "unknown"))
                if len(chain) >= depth - 1:
                    break
    except OSError:
        pass

    chain.reverse()
    chain.append(current_category)

    chain_str = " → ".join(f"{i + 1}차: {cat}" for i, cat in enumerate(chain))

    print(
        f"\n⚠ CASCADE ALERT: 이 세션에서 {depth}회 연속 에러 발생\n"
        f"  {chain_str}\n"
        f"  → 근본 원인 재검토를 권장합니다. 표면 수정이 아닌 구조적 문제일 수 있습니다.\n",
        file=sys.stderr,
    )


def sanitize_str(value: str) -> str:
    """Windows 한글 경로 등에서 발생하는 surrogate 문자 제거.

    NOTE: .claude/skills/_shared/text_utils.py와 동일 구현.
    훅은 독립 프로세스로 import 불가하므로 인라인 복사.
    수정 시 text_utils.py 및 다른 훅 파일도 함께 수정할 것.
    """
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
        stdout = (
            tool_response.get("stdout", "")
            if isinstance(tool_response, dict)
            else str(tool_response)
        )
        stderr = (
            tool_response.get("stderr", "") if isinstance(tool_response, dict) else ""
        )
        return_code = (
            tool_response.get("returnCode", 0) if isinstance(tool_response, dict) else 0
        )
        if not return_code or return_code == 0:
            sys.exit(0)
        command = (
            tool_input.get("command", "")
            if isinstance(tool_input, dict)
            else str(tool_input)
        )
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

    now = datetime.now(KST)
    session_id = sanitize_str(data.get("session_id", ""))
    category = categorize(command, error_text)

    # Cascade 추적
    cascade_depth, preceding_category, time_since_last = compute_cascade(
        log_path, session_id, now
    )

    record = {
        "ts": now.isoformat(timespec="seconds"),
        "session_id": session_id,
        "event": event,
        "tool_name": tool_name,
        "command": sanitize_str(command[:300]),
        "return_code": return_code,
        "error_snippet": sanitize_str(extract_snippet(error_text)),
        "category": category,
        "cwd": sanitize_str(data.get("cwd", "")),
        "cascade_depth": cascade_depth,
        "preceding_category": preceding_category,
        "time_since_last_error": round(time_since_last, 1)
        if time_since_last is not None
        else None,
    }

    # Cascade 경고 출력 (파일 쓰기 전에 호출 — 방금 쓴 레코드 중복 방지)
    emit_cascade_alert(log_path, session_id, cascade_depth, category)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
