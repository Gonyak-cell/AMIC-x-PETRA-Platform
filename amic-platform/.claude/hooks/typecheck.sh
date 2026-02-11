#!/usr/bin/env bash
set -euo pipefail
cd "$CLAUDE_PROJECT_DIR"
echo "Running TypeScript type check..." >&2
npx tsc --noEmit 2>&1 || echo "WARNING: TypeScript type errors detected." >&2
exit 0
