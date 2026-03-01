#!/usr/bin/env bash
# PreToolUse hook: [dependency-groups] (PEP 735) 사용 차단 (ci-regression-prevention Guard 7)
# pip은 [project.optional-dependencies]만 인식. [dependency-groups]는 uv 전용.

if ! command -v jq &>/dev/null; then
  echo "BLOCKED: jq가 설치되어 있지 않아 Guard 7 검사를 수행할 수 없습니다. jq를 설치하세요." >&2
  exit 2
fi

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || FILE_PATH=""
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty' 2>/dev/null) || CONTENT=""

# pyproject.toml 파일만 검사
if [[ "$(basename "$FILE_PATH" 2>/dev/null)" != "pyproject.toml" ]]; then
  exit 0
fi

# 빈 콘텐츠면 스킵
if [[ -z "$CONTENT" ]]; then
  exit 0
fi

# [dependency-groups] 패턴 감지 시 차단
if echo "$CONTENT" | grep -q '\[dependency-groups\]'; then
  echo "BLOCKED: '$FILE_PATH'에서 [dependency-groups] (PEP 735) 사용 감지. pip에서 인식 불가하여 CI 실패. [project.optional-dependencies]를 사용하세요. (Guard 7)" >&2
  exit 2
fi

exit 0
