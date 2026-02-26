#!/usr/bin/env python3
"""UserPromptSubmit hook: 하루 1회 전날 일일 리포트를 자동 생성한다.

동작:
1. logs/daily/{어제}.md 존재 여부 확인 (파일 존재 = 이미 생성됨 → 즉시 종료)
2. 없으면 generate_daily_report.py 실행하여 리포트 생성
3. 생성 결과를 Claude 컨텍스트로 전달
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


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
        # UserPromptSubmit 이벤트 — stdin 데이터 파싱
        data = json.loads(raw)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    project_dir = sanitize_str(
        os.environ.get("CLAUDE_PROJECT_DIR", data.get("cwd", "."))
    )
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    report_path = Path(project_dir) / "logs" / "daily" / f"{yesterday}.md"

    # 이미 리포트가 존재하면 즉시 종료 (0ms 오버헤드)
    if report_path.exists():
        sys.exit(0)

    # 전날 에러 데이터가 있는지 빠르게 확인
    errors_path = Path(project_dir) / "logs" / "errors.jsonl"
    prompts_path = Path(project_dir) / "logs" / "prompts.jsonl"

    has_data = False
    for log_path in [errors_path, prompts_path]:
        if log_path.exists():
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if yesterday in line[:30]:
                        has_data = True
                        break
            if has_data:
                break

    # git 커밋이 있는지도 확인
    if not has_data:
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--oneline",
                    f"--since={yesterday} 00:00:00",
                    f"--until={yesterday} 23:59:59",
                ],
                capture_output=True,
                text=True,
                cwd=project_dir,
                timeout=5,
            )
            if result.stdout.strip():
                has_data = True
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    if not has_data:
        sys.exit(0)

    # 리포트 생성 실행
    script_path = (
        Path(project_dir)
        / ".claude"
        / "skills"
        / "daily-report"
        / "scripts"
        / "generate_daily_report.py"
    )

    if not script_path.exists():
        sys.exit(0)

    try:
        subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--date",
                yesterday,
                "--project-dir",
                project_dir,
            ],
            timeout=30,
            capture_output=True,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        sys.exit(0)

    # 생성 성공 시 Claude에 컨텍스트 전달
    if report_path.exists():
        # 요약 추출 (파일 첫 20줄에서 요약 테이블 찾기)
        summary = ""
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[:25]
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("| 총 커밋") or stripped.startswith("| 에러 발생") or stripped.startswith("| 에러 수정"):
                    parts = stripped.split("|")
                    if len(parts) >= 3 and not parts[1].strip().startswith("---"):
                        summary += f"{parts[1].strip()}: {parts[2].strip()}, "
        except Exception:
            pass

        if summary:
            summary = summary.rstrip(", ")

        output = json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": f"[일일 리포트] {yesterday} 리포트가 자동 생성되었습니다. {summary}. 상세: logs/daily/{yesterday}.md",
                }
            },
            ensure_ascii=False,
        )
        print(output)

    sys.exit(0)


if __name__ == "__main__":
    main()
