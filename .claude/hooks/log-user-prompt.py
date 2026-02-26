#!/usr/bin/env python3
"""UserPromptSubmit hook: 사용자 지시를 logs/prompts.jsonl에 자동 기록."""
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CATEGORY_RULES = [
    (["구현", "implement", "만들", "추가", "생성", "create", "add", "build", "작성"], "implement"),
    (["수정", "fix", "고쳐", "버그", "에러", "오류", "error", "bug", "debug"], "fix"),
    (["리뷰", "review", "검토", "분석", "확인", "analyze", "check", "audit"], "review"),
    (["리팩토링", "refactor", "정리", "개선", "clean", "improve"], "refactor"),
    (["테스트", "test", "검증", "verify"], "test"),
    (["문서", "docs", "기록", "document", "작성"], "docs"),
    (["배포", "deploy", "빌드", "docker", "ci", "cd"], "deploy"),
]

# 민감 정보 마스킹 패턴
SENSITIVE_PATTERNS = [
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "[EMAIL]"),
    (re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"), "[JWT]"),
    (re.compile(r"(?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[^\s'\"]{8,}", re.IGNORECASE), "[REDACTED_SECRET]"),
]


def categorize(prompt: str) -> str:
    text = prompt.lower()
    for keywords, category in CATEGORY_RULES:
        if any(k in text for k in keywords):
            return category
    return "other"


def mask_sensitive(text: str) -> str:
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


KST = timezone(timedelta(hours=9))


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

    prompt = data.get("prompt", "")

    # 빈 프롬프트만 스킵
    if not prompt.strip():
        sys.exit(0)

    # 민감 정보 마스킹
    safe_prompt = mask_sensitive(prompt)

    # 500자 초과 시 truncate
    if len(safe_prompt) > 500:
        safe_prompt = safe_prompt[:300] + " [truncated]"

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", data.get("cwd", "."))
    log_path = Path(sanitize_str(project_dir)) / "logs" / "prompts.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "ts": datetime.now(KST).isoformat(timespec="seconds"),
        "session_id": sanitize_str(data.get("session_id", "")),
        "prompt": sanitize_str(safe_prompt),
        "prompt_len": len(prompt),
        "category": categorize(prompt),
        "cwd": sanitize_str(data.get("cwd", "")),
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
