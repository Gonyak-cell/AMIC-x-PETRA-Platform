#!/bin/bash
# Git pre-push hook — 단독 리포 ↔ 모노레포 동기화 경고
# 설치: .\scripts\install-hooks.ps1
# push를 차단하지 않고 경고만 출력합니다.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# PowerShell이 있으면 동기화 스크립트 실행
if command -v powershell.exe &>/dev/null; then
    echo ""
    echo "=== Repo Sync Check (pre-push) ==="
    powershell.exe -ExecutionPolicy Bypass -File "$REPO_ROOT/scripts/check-repo-sync.ps1" 2>/dev/null
    EXIT_CODE=$?

    if [ $EXIT_CODE -ne 0 ]; then
        echo ""
        echo "WARNING: 단독 리포와 모노레포 간 코드 불일치가 있습니다."
        echo "  docker compose에서 모노레포 코드가 사용됩니다."
        echo "  .\scripts\check-repo-sync.ps1 --fix 로 동기화하세요."
        echo ""
        # 경고만 — push는 허용
    fi
elif command -v pwsh &>/dev/null; then
    pwsh -ExecutionPolicy Bypass -File "$REPO_ROOT/scripts/check-repo-sync.ps1" 2>/dev/null
    EXIT_CODE=$?

    if [ $EXIT_CODE -ne 0 ]; then
        echo ""
        echo "WARNING: 단독 리포와 모노레포 간 코드 불일치가 있습니다."
        echo ""
    fi
fi

# 항상 push 허용 (exit 0)
exit 0
