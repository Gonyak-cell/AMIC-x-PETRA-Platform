#!/usr/bin/env bash
set -euo pipefail
json=$(cat)
command=$(echo "$json" | jq -r '.tool_input.command // empty')

# Only check on git commit commands
if ! echo "$command" | grep -qE 'git\s+commit'; then
    exit 0
fi

if [[ -n "${CLAUDE_PROJECT_DIR:-}" ]]; then
    PROJECT_DIR="$CLAUDE_PROJECT_DIR"
else
    PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
fi

cd "$PROJECT_DIR"

# Scan staged Python and YAML files across all backend modules
staged_files=$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null | grep -E '\.(py|yml|yaml)$' || true)

if [[ -z "$staged_files" ]]; then
    exit 0
fi

found_secrets=false
while IFS= read -r file; do
    if grep -nE '(api_key|secret|password|token)\s*=\s*["\x27][A-Za-z0-9+/=]{16,}' "$file" 2>/dev/null; then
        echo "WARNING: 잠재적 하드코딩 시크릿 감지: $file" >&2
        found_secrets=true
    fi
done <<< "$staged_files"

if [[ "$found_secrets" == "true" ]]; then
    echo "시크릿이 감지되었습니다. 환경변수를 사용하세요." >&2
    exit 2
fi

exit 0
