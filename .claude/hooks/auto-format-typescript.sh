#!/usr/bin/env bash
# PostToolUse hook: Auto-format TypeScript/TSX files after Edit/Write
set -uo pipefail

json=$(cat)
file_path=$(echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")

if [[ -z "$file_path" ]]; then
    exit 0
fi

# Only process .ts and .tsx files
case "$file_path" in
    *.ts|*.tsx) ;;
    *) exit 0 ;;
esac

# Find the amic-platform directory (frontend root)
PLATFORM_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}/amic-platform"

if [[ ! -d "$PLATFORM_DIR/node_modules" ]]; then
    exit 0
fi

# Run ESLint --fix (suppress output to avoid context window pollution)
cd "$PLATFORM_DIR" 2>/dev/null || exit 0
npx eslint --fix "$file_path" > /dev/null 2>&1 || true

# Run Prettier --write
npx prettier --write "$file_path" > /dev/null 2>&1 || true

exit 0
