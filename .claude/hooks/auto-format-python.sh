#!/usr/bin/env bash
set -euo pipefail
json=$(cat)
file_path=$(echo "$json" | jq -r '.tool_input.file_path // empty')
if [[ "$file_path" == *.py ]]; then
    cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || exit 0
    if command -v uv &>/dev/null; then
        uv run ruff check --fix --quiet "$file_path" 2>/dev/null || true
        uv run ruff format --quiet "$file_path" 2>/dev/null || true
    elif command -v ruff &>/dev/null; then
        ruff check --fix --quiet "$file_path" 2>/dev/null || true
        ruff format --quiet "$file_path" 2>/dev/null || true
    else
        echo "WARNING: ruff not found. Install: pip install ruff" >&2
    fi
fi
exit 0
