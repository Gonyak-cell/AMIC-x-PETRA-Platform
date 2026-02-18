#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${CLAUDE_PROJECT_DIR:-}" ]]; then
    PROJECT_DIR="$CLAUDE_PROJECT_DIR"
else
    PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
fi

cd "$PROJECT_DIR"

if [[ ! -d ".git" ]]; then
    echo "INFO: Git 미초기화. 영향 테스트 스킵." >&2
    exit 0
fi

# Detect changed Python files across all backend modules
changed_files=$(git diff --name-only --diff-filter=ACMR HEAD 2>/dev/null | grep -E '^(fdd|kiis|im)/.*\.py$' || true)

if [[ -z "$changed_files" ]]; then
    echo "INFO: 변경된 백엔드 소스 파일 없음. 테스트 스킵." >&2
    exit 0
fi

# Group changed files by module
fdd_changed=$(echo "$changed_files" | grep '^fdd/' || true)
kiis_changed=$(echo "$changed_files" | grep '^kiis/' || true)
im_changed=$(echo "$changed_files" | grep '^im/' || true)

# Run tests per module
if [[ -n "$fdd_changed" ]]; then
    echo "FDD 모듈 변경 감지 — 테스트 실행 중..." >&2
    if [[ -d "fdd/backend/tests" ]]; then
        cd "$PROJECT_DIR/fdd/backend"
        python -m pytest tests/ -v --tb=short -q 2>&1 || echo "WARNING: FDD 테스트 일부 실패" >&2
        cd "$PROJECT_DIR"
    fi
fi

if [[ -n "$kiis_changed" ]]; then
    echo "KIIS 모듈 변경 감지 — 테스트 실행 중..." >&2
    if [[ -d "kiis/tests" ]]; then
        cd "$PROJECT_DIR/kiis"
        if command -v uv &>/dev/null; then
            uv run pytest tests/ -v --tb=short -q 2>&1 || echo "WARNING: KIIS 테스트 일부 실패" >&2
        else
            python -m pytest tests/ -v --tb=short -q 2>&1 || echo "WARNING: KIIS 테스트 일부 실패" >&2
        fi
        cd "$PROJECT_DIR"
    fi
fi

if [[ -n "$im_changed" ]]; then
    echo "IM 모듈 변경 감지 — 테스트 실행 중..." >&2
    if [[ -d "im/tests" ]]; then
        cd "$PROJECT_DIR/im"
        python -m pytest tests/ -v --tb=short -q 2>&1 || echo "WARNING: IM 테스트 일부 실패" >&2
        cd "$PROJECT_DIR"
    fi
fi

exit 0
