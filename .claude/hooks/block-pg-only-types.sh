#!/usr/bin/env bash
# PreToolUse hook: PostgreSQL 전용 타입 직접 사용 차단 (ci-regression-prevention Guard 2)
# mapped_column(JSONB 또는 mapped_column(UUID(as_uuid 패턴 감지 시 차단
# JSON().with_variant(JSONB, "postgresql") 패턴은 허용
# 주의: Edit 도구는 변경 청크만 전달하므로 with_variant가 다른 줄에 있으면 오탐 가능. Write에서만 완전 검사.

if ! command -v jq &>/dev/null; then
  echo "BLOCKED: jq가 설치되어 있지 않아 Guard 2 검사를 수행할 수 없습니다. jq를 설치하세요." >&2
  exit 2
fi

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || FILE_PATH=""
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty' 2>/dev/null) || CONTENT=""

# .py 파일만 검사
if [[ "$FILE_PATH" != *.py ]]; then
  exit 0
fi

# 빈 콘텐츠면 스킵
if [[ -z "$CONTENT" ]]; then
  exit 0
fi

# mapped_column(JSONB 직접 사용 차단 (with_variant 패턴은 허용)
if echo "$CONTENT" | grep -qE 'mapped_column\([ \t]*JSONB' && ! echo "$CONTENT" | grep -q 'with_variant'; then
  echo "BLOCKED: '$FILE_PATH'에서 mapped_column(JSONB) 직접 사용 감지. JSON().with_variant(JSONB, \"postgresql\") 패턴을 사용하세요. (Guard 2)" >&2
  exit 2
fi

# mapped_column(UUID(as_uuid 직접 사용 차단
if echo "$CONTENT" | grep -qE 'mapped_column\([ \t]*UUID[ \t]*\('; then
  echo "BLOCKED: '$FILE_PATH'에서 mapped_column(UUID(as_uuid=True)) 직접 사용 감지. sqlalchemy.Uuid를 사용하세요. (Guard 2)" >&2
  exit 2
fi

exit 0
