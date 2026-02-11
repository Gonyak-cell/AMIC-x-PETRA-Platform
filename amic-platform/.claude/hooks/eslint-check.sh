#!/usr/bin/env bash
set -euo pipefail
json=$(cat)
file_path=$(echo "$json" | jq -r '.tool_input.file_path // empty')
if [[ "$file_path" == *.ts || "$file_path" == *.tsx ]]; then
    cd "$CLAUDE_PROJECT_DIR"
    npx eslint --no-error-on-unmatched-pattern "$file_path" 2>/dev/null || echo "ESLint issues in $file_path" >&2
fi
exit 0
