#!/usr/bin/env bash
# PreToolUse: Python 코드 작성 시 ruff 위반 패턴 사전 차단 (UP041, B017)
# 대상: Edit|Write 도구로 .py 파일 수정 시
set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || FILE_PATH=""
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty' 2>/dev/null) || CONTENT=""

# .py 파일만 검사
[[ "$FILE_PATH" != *.py ]] && exit 0
# 빈 콘텐츠면 스킵
[[ -z "$CONTENT" ]] && exit 0

ERRORS=""

# UP041: asyncio.TimeoutError → TimeoutError (빌트인 사용)
if echo "$CONTENT" | grep -qE '(except|raise)\s+asyncio\.TimeoutError'; then
    ERRORS="${ERRORS}\n- UP041: asyncio.TimeoutError 대신 빌트인 TimeoutError를 사용하세요"
fi

# UP041: from asyncio import TimeoutError (불필요한 import)
if echo "$CONTENT" | grep -qE 'from asyncio import.*TimeoutError'; then
    ERRORS="${ERRORS}\n- UP041: from asyncio import TimeoutError 불필요 — 빌트인 TimeoutError 직접 사용"
fi

# B017: pytest.raises(Exception/BaseException) without match=
if echo "$CONTENT" | grep -qE 'pytest\.raises\(\s*(Exception|BaseException)\s*\)'; then
    ERRORS="${ERRORS}\n- B017: pytest.raises(Exception)에 match= 인자를 추가하세요"
fi

if [[ -n "$ERRORS" ]]; then
    echo "BLOCKED: '$FILE_PATH'에서 ruff 위반 패턴 감지:" >&2
    echo -e "$ERRORS" >&2
    exit 2
fi

exit 0
