# AMIC x PETRA Platform — Git Hooks 설치
# 사용법: .\scripts\install-hooks.ps1

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$HooksDir = Join-Path $RepoRoot ".git\hooks"

Write-Host ""
Write-Host "=== Git Hooks 설치 ===" -ForegroundColor Cyan
Write-Host ""

# .git/hooks 디렉터리 확인
if (-not (Test-Path $HooksDir)) {
    Write-Host "오류: .git/hooks 디렉터리가 없습니다. Git 저장소인지 확인하세요." -ForegroundColor Red
    exit 1
}

# pre-push 훅 설치
$HookSource = Join-Path $PSScriptRoot "pre-push-sync-check.sh"
$HookTarget = Join-Path $HooksDir "pre-push"

if (Test-Path $HookTarget) {
    $existing = Get-Content $HookTarget -Raw -ErrorAction SilentlyContinue
    if ($existing -match "pre-push-sync-check") {
        Write-Host "  pre-push 훅이 이미 설치되어 있습니다." -ForegroundColor Yellow
    } else {
        # 기존 훅이 있으면 백업
        $backup = "$HookTarget.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item $HookTarget $backup
        Write-Host "  기존 pre-push 훅 백업: $backup" -ForegroundColor Yellow
        Copy-Item $HookSource $HookTarget -Force
        Write-Host "  pre-push 훅 설치 완료 (기존 훅 백업됨)" -ForegroundColor Green
    }
} else {
    Copy-Item $HookSource $HookTarget -Force
    Write-Host "  pre-push 훅 설치 완료" -ForegroundColor Green
}

Write-Host ""
Write-Host "설치 완료! git push 시 자동으로 동기화 검사가 실행됩니다." -ForegroundColor Green
Write-Host "  - push를 차단하지 않고 경고만 출력합니다." -ForegroundColor Gray
Write-Host "  - 불일치 발견 시: .\scripts\check-repo-sync.ps1 --fix" -ForegroundColor Gray
Write-Host ""
