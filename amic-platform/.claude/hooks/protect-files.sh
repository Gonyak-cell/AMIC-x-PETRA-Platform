#!/usr/bin/env bash
set -euo pipefail
json=$(cat)
file_path=$(echo "$json" | jq -r '.tool_input.file_path // empty')
protected_patterns=(".env" "package-lock.json" ".claude/settings.local.json" "node_modules/" "dist/" "*.key" "*.pem")
for pattern in "${protected_patterns[@]}"; do
    if [[ "$file_path" == *"$pattern"* ]]; then
        echo "BLOCKED: $file_path is a protected file (matched: $pattern)" >&2
        exit 2
    fi
done
exit 0
