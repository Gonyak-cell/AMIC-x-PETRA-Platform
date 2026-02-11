#!/usr/bin/env bash
set -euo pipefail
json=$(cat)
file_path=$(echo "$json" | jq -r '.tool_input.file_path // empty')
if [[ "$file_path" == *.ts || "$file_path" == *.tsx || "$file_path" == *.css || "$file_path" == *.json ]]; then
    cd "$CLAUDE_PROJECT_DIR"
    npx prettier --write "$file_path" 2>/dev/null || true
fi
exit 0
