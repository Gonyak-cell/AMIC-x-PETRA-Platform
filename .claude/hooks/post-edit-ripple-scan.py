#!/usr/bin/env python3
"""PostToolUse hook: Python 파일 수정 후 영향받는 파일을 자동 탐색하여 경고.

Edit/Write로 .py 파일 수정 시 트리거.
수정된 파일에서 정의된 심볼(class, def, 상수)을 추출하고,
같은 모듈 내에서 해당 심볼을 참조하는 다른 파일을 찾아 stderr로 경고 출력.
"""

import json
import os
import re
import subprocess
import sys

# 모노레포 모듈 디렉토리 (이 범위 내에서만 탐색)
MODULE_DIRS = ["fdd", "kiis", "im", "deal-mgmt"]

# 무시할 디렉토리 패턴
IGNORE_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv", "alembic"}

# grep 노이즈가 큰 일반적 짧은 이름 제외
SHORT_SYMBOL_STOPWORDS = {
    "app",
    "get",
    "set",
    "run",
    "log",
    "put",
    "add",
    "new",
    "old",
    "key",
    "val",
    "cmd",
    "msg",
    "err",
    "res",
    "req",
    "row",
    "col",
    "tmp",
    "buf",
    "obj",
    "cls",
    "api",
    "url",
    "env",
    "cfg",
    "doc",
    "tag",
    "Map",
    "ctx",
}

# 심볼 추출 패턴
CLASS_PATTERN = re.compile(r"^class\s+(\w+)")
FUNC_PATTERN = re.compile(r"^(?:async\s+)?def\s+(\w+)")
CONST_PATTERN = re.compile(r"^([A-Z][A-Z_0-9]+)\s*[=:]")


def sanitize_str(value: str) -> str:
    """Windows 한글 경로 등에서 발생하는 surrogate 문자 제거."""
    return value.encode("utf-8", errors="replace").decode("utf-8")


def detect_module(file_path: str, project_dir: str) -> str | None:
    """파일이 속한 모듈 디렉토리를 감지한다."""
    rel = os.path.relpath(file_path, project_dir).replace("\\", "/")
    for mod in MODULE_DIRS:
        if rel.startswith(mod + "/"):
            return mod
    return None


def extract_symbols(content: str) -> list[str]:
    """파일 콘텐츠에서 클래스, 함수, 상수 심볼을 추출한다."""
    symbols: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        # 들여쓰기된 메서드/내부 함수는 제외 (최상위만)
        if line and not line[0].isspace():
            for pattern in (CLASS_PATTERN, FUNC_PATTERN, CONST_PATTERN):
                m = pattern.match(stripped)
                if m:
                    sym = m.group(1)
                    # private, 짧은 일반명, 테스트 함수 제외
                    if (
                        len(sym) >= 3
                        and not sym.startswith("_")
                        and sym != "main"
                        and sym not in SHORT_SYMBOL_STOPWORDS
                    ):
                        symbols.append(sym)
    return list(dict.fromkeys(symbols))  # 중복 제거, 순서 유지


def find_references(symbol: str, module_dir: str, source_file: str) -> list[str]:
    """모듈 내에서 심볼을 참조하는 파일을 grep으로 탐색한다."""
    try:
        result = subprocess.run(
            ["grep", "-rlw", "--include=*.py", symbol, module_dir],
            capture_output=True,
            text=True,
            timeout=3,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            return []
        files = [
            f
            for f in result.stdout.strip().splitlines()
            if f and os.path.normpath(f) != os.path.normpath(source_file)
        ]
        # __pycache__ 등 무시
        files = [
            f
            for f in files
            if not any(ign in f.replace("\\", "/") for ign in IGNORE_DIRS)
        ]
        return files[:10]  # 최대 10개
    except (subprocess.TimeoutExpired, OSError):
        return []


def main() -> None:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if not file_path or not file_path.endswith(".py"):
        sys.exit(0)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", data.get("cwd", "."))
    module = detect_module(file_path, project_dir)
    if not module:
        sys.exit(0)

    module_dir = os.path.join(project_dir, module)
    if not os.path.isdir(module_dir):
        sys.exit(0)

    # 심볼 추출용 콘텐츠 결정
    # Write: content에 전체 파일 내용이 있음
    # Edit: new_string은 변경 조각뿐이므로 파일 전체를 읽어야 함
    is_edit = "old_string" in tool_input
    content = ""
    if not is_edit:
        content = tool_input.get("content", "")
    if not content:
        # Edit이거나 Write의 content가 비어있으면 파일 전체를 읽음
        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            sys.exit(0)

    symbols = extract_symbols(content)
    if not symbols:
        sys.exit(0)

    # 심볼별 참조 파일 탐색
    all_refs: dict[str, list[str]] = {}
    for sym in symbols[:8]:  # 성능 제한: 최대 8개 심볼만
        refs = find_references(sym, module_dir, file_path)
        if refs:
            all_refs[sym] = refs

    if not all_refs:
        sys.exit(0)

    # 참조 파일을 flatten하여 고유 목록 생성
    unique_files: dict[str, list[str]] = {}  # file -> [symbols]
    for sym, files in all_refs.items():
        for f in files:
            rel_f = os.path.relpath(f, project_dir).replace("\\", "/")
            if rel_f not in unique_files:
                unique_files[rel_f] = []
            unique_files[rel_f].append(sym)

    if not unique_files:
        sys.exit(0)

    rel_source = os.path.relpath(file_path, project_dir).replace("\\", "/")
    count = len(unique_files)

    msg_lines = [
        f"\u26a0 Ripple Alert: {rel_source} \uc218\uc815\ub428",
        f"  \u2192 \uc601\ud5a5\ubc1b\ub294 \ud30c\uc77c {count}\uac1c \ubc1c\uacac:",
    ]
    for fpath, syms in list(unique_files.items())[:8]:
        sym_str = ", ".join(syms[:3])
        if len(syms) > 3:
            sym_str += f" \uc678 {len(syms) - 3}\uac1c"
        msg_lines.append(f"    - {fpath} ({sym_str} \ucc38\uc870)")

    if count > 8:
        msg_lines.append(f"    ... \uc678 {count - 8}\uac1c \ud30c\uc77c")

    msg_lines.append(
        "  \u2192 \uc774 \ud30c\uc77c\ub4e4\ub3c4 \uc218\uc815\uc774 \ud544\uc694\ud55c\uc9c0 \ud655\uc778\ud558\uc138\uc694."
    )

    print("\n".join(msg_lines), file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
