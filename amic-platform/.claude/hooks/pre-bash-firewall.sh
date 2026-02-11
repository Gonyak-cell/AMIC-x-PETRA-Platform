#!/usr/bin/env bash
set -euo pipefail
json=$(cat)
command=$(echo "$json" | jq -r '.tool_input.command // empty')
if echo "$command" | grep -qE 'rm -rf /|rm -rf \.|git reset --hard|git push.*--force|git clean -fd'; then
    echo "BLOCKED: Dangerous command detected: $command" >&2
    exit 2
fi
exit 0
