#!/usr/bin/env bash
set -euo pipefail
json=$(cat)
command=$(echo "$json" | jq -r '.tool_input.command // empty')

if echo "$command" | grep -qiE 'DROP\s+TABLE|DROP\s+DATABASE|TRUNCATE\s+TABLE|DELETE\s+FROM\s+\w+\s*;|DELETE\s+FROM\s+\w+\s*$'; then
    echo "BLOCKED: 파괴적 DB 명령 감지: $command" >&2
    echo "WHERE 절 없는 DELETE 또는 DROP/TRUNCATE는 허용되지 않습니다." >&2
    exit 2
fi

if echo "$command" | grep -qE 'alembic\s+downgrade\s+base'; then
    echo "BLOCKED: alembic downgrade base는 모든 마이그레이션을 롤백합니다. 수동으로 실행하세요." >&2
    exit 2
fi

exit 0
