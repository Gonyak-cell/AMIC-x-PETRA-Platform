#!/bin/bash
# PreToolUse hook: 보호 대상 백엔드 파일 편집 차단
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# 보호 대상 패턴
PROTECTED_PATTERNS=(".env" "migrations/versions/" "alembic/versions/" ".git/" ".key" ".pem")

for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "BLOCKED: '$FILE_PATH' is protected (matches '$pattern'). Use Alembic CLI for migrations." >&2
    exit 2
  fi
done

exit 0
