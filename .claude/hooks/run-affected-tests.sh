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

# Detect changed files across all modules
all_changed=$(git diff --name-only --diff-filter=ACMR HEAD 2>/dev/null || true)
changed_py=$(echo "$all_changed" | grep -E '^(fdd|kiis|im|deal-mgmt)/.*\.py$' || true)
changed_ts=$(echo "$all_changed" | grep -E '^amic-platform/.*\.(ts|tsx)$' || true)

if [[ -z "$changed_py" && -z "$changed_ts" ]]; then
    echo "INFO: 변경된 소스 파일 없음. 테스트 스킵." >&2
    exit 0
fi

# Group changed Python files by module
fdd_changed=$(echo "$changed_py" | grep '^fdd/' || true)
kiis_changed=$(echo "$changed_py" | grep '^kiis/' || true)
im_changed=$(echo "$changed_py" | grep '^im/' || true)
dealmgmt_changed=$(echo "$changed_py" | grep '^deal-mgmt/' || true)

# Run backend tests per module
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

if [[ -n "$dealmgmt_changed" ]]; then
    echo "deal-mgmt 모듈 변경 감지 — 테스트 실행 중..." >&2
    if [[ -d "deal-mgmt/tests" ]]; then
        cd "$PROJECT_DIR/deal-mgmt"
        python -m pytest tests/ -v --tb=short -q 2>&1 || echo "WARNING: deal-mgmt 테스트 일부 실패" >&2
        cd "$PROJECT_DIR"
    fi
fi

# Run frontend lint & typecheck if TS/TSX files changed
if [[ -n "$changed_ts" ]]; then
    echo "프론트엔드 변경 감지 — lint & typecheck 실행 중..." >&2
    if [[ -d "amic-platform/node_modules" ]]; then
        cd "$PROJECT_DIR/amic-platform"
        npx tsc -b --noEmit 2>&1 || echo "WARNING: TypeScript 타입체크 실패" >&2
        npm run lint 2>&1 || echo "WARNING: ESLint 실패" >&2
        cd "$PROJECT_DIR"
    else
        echo "INFO: amic-platform/node_modules 없음. 프론트엔드 검증 스킵." >&2
    fi
fi

exit 0
