#!/usr/bin/env bash
# [INACTIVE] 이 훅은 settings.json에서 제거됨 (2026-03-02).
# 사유: protect-backend-files.sh가 migrations/versions/ 경로를 이미 차단하므로,
#       이 훅이 실행되기 전에 Edit/Write가 먼저 차단됨 (데드 코드).
# 재활성화 시: settings.json의 PreToolUse Edit|Write 매처에 등록 필요.
#              단, protect-backend-files.sh보다 앞에 배치해야 실행됨.
# PreToolUse hook: Alembic 마이그레이션 파일의 빈 downgrade() 방지
# migrations/versions/*.py 생성 시 downgrade() 본문이 pass만 있으면 경고

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty')

# migrations/versions/*.py 파일만 검사
if [[ "$FILE_PATH" != *migrations/versions/*.py ]]; then
  exit 0
fi

# 빈 콘텐츠면 스킵
if [[ -z "$CONTENT" ]]; then
  exit 0
fi

# downgrade() 함수가 존재하지 않으면 차단
if ! echo "$CONTENT" | grep -q 'def downgrade'; then
  echo "BLOCKED: 마이그레이션 파일에 downgrade() 함수가 없습니다. 롤백을 위해 반드시 구현하세요." >&2
  exit 2
fi

# downgrade() 본문이 pass만 있으면 경고 (차단하지 않음 — 의도적 pass일 수 있음)
if echo "$CONTENT" | grep -A3 'def downgrade' | grep -qE '^[[:space:]]*pass[[:space:]]*$'; then
  echo "WARNING: downgrade() 본문이 pass만 포함합니다. 실제 롤백 로직을 구현하세요." >&2
fi

exit 0
