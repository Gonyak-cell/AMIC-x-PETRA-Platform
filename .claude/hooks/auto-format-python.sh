#!/usr/bin/env bash
set -euo pipefail
json=$(cat)
file_path=$(echo "$json" | jq -r '.tool_input.file_path // empty')
if [[ "$file_path" == *.py ]]; then
    cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || exit 0

    RUFF_CMD=""
    if command -v uv &>/dev/null; then
        RUFF_CMD="uv run ruff"
    elif command -v ruff &>/dev/null; then
        RUFF_CMD="ruff"
    else
        echo "WARNING: ruff not found" >&2
        exit 0
    fi

    # Phase 1: 자동 수정 (UP041, F401 등 --fix로 해결 가능한 것)
    $RUFF_CMD check --fix --quiet "$file_path" 2>/dev/null || true
    # Phase 2: 포맷팅
    $RUFF_CMD format --quiet "$file_path" 2>/dev/null || true
    # Phase 3: 잔여 에러 Claude에게 피드백 (자동 수정 불가 항목)
    REMAINING=$($RUFF_CMD check "$file_path" 2>/dev/null) || true
    if [[ -n "$REMAINING" ]]; then
        echo "⚠ ruff 잔여 에러 (수동 수정 필요):" >&2
        echo "$REMAINING" >&2
    fi
fi
exit 0
