# ===================================================================
# AMIC x PETRA Platform — GitHub Secrets 등록 스크립트
# ===================================================================
# 사용법: powershell -ExecutionPolicy Bypass -File scripts/setup-github-secrets.ps1
# 사전조건: gh auth login 완료 상태
# ===================================================================

$ErrorActionPreference = "Stop"

# gh CLI 확인
try {
    gh auth status 2>&1 | Out-Null
} catch {
    Write-Host "ERROR: gh CLI가 인증되지 않았습니다. 'gh auth login'을 먼저 실행하세요." -ForegroundColor Red
    exit 1
}

$repo = gh repo view --json nameWithOwner -q .nameWithOwner 2>&1
Write-Host "GitHub Repo: $repo" -ForegroundColor Cyan
Write-Host ""

# -------------------------------------------------------------------
# 1. Sentry Secrets (4개)
# -------------------------------------------------------------------
Write-Host "=== Sentry Secrets ===" -ForegroundColor Yellow
Write-Host "Sentry 프로젝트가 준비되었다면 아래 값을 입력하세요."
Write-Host "건너뛰려면 Enter를 누르세요."
Write-Host ""

$sentryDsn = Read-Host "VITE_SENTRY_DSN (예: https://abc@o123.ingest.sentry.io/456)"
$sentryAuthToken = Read-Host "SENTRY_AUTH_TOKEN (예: sntrys_eyJ...)"
$sentryOrg = Read-Host "SENTRY_ORG (예: amic-petra)"
$sentryProject = Read-Host "SENTRY_PROJECT (예: amic-platform)"

$sentrySecrets = @{
    "VITE_SENTRY_DSN"  = $sentryDsn
    "SENTRY_AUTH_TOKEN" = $sentryAuthToken
    "SENTRY_ORG"        = $sentryOrg
    "SENTRY_PROJECT"    = $sentryProject
}

foreach ($key in $sentrySecrets.Keys) {
    $val = $sentrySecrets[$key]
    if ($val -and $val.Trim() -ne "") {
        Write-Host "  Setting $key..." -ForegroundColor Green -NoNewline
        $val | gh secret set $key
        Write-Host " Done"
    } else {
        Write-Host "  Skipping $key (empty)" -ForegroundColor DarkGray
    }
}

Write-Host ""

# -------------------------------------------------------------------
# 2. Deploy Secrets (4개)
# -------------------------------------------------------------------
Write-Host "=== Deploy Secrets ===" -ForegroundColor Yellow
Write-Host "배포 서버가 준비되었다면 아래 값을 입력하세요."
Write-Host "건너뛰려면 Enter를 누르세요."
Write-Host ""

$deployHost = Read-Host "DEPLOY_HOST (예: 123.456.789.10)"
$deployUser = Read-Host "DEPLOY_USER (예: ubuntu)"
$deployPath = Read-Host "DEPLOY_PATH (예: /opt/amic-platform)"

$deploySecrets = @{
    "DEPLOY_HOST" = $deployHost
    "DEPLOY_USER" = $deployUser
    "DEPLOY_PATH" = $deployPath
}

foreach ($key in $deploySecrets.Keys) {
    $val = $deploySecrets[$key]
    if ($val -and $val.Trim() -ne "") {
        Write-Host "  Setting $key..." -ForegroundColor Green -NoNewline
        $val | gh secret set $key
        Write-Host " Done"
    } else {
        Write-Host "  Skipping $key (empty)" -ForegroundColor DarkGray
    }
}

# SSH Key는 파일 경로로 입력받음
Write-Host ""
$sshKeyPath = Read-Host "DEPLOY_SSH_KEY 파일 경로 (예: ~/.ssh/amic_deploy)"
if ($sshKeyPath -and $sshKeyPath.Trim() -ne "") {
    $expandedPath = [System.Environment]::ExpandEnvironmentVariables($sshKeyPath.Replace("~", $env:USERPROFILE))
    if (Test-Path $expandedPath) {
        Write-Host "  Setting DEPLOY_SSH_KEY from file..." -ForegroundColor Green -NoNewline
        Get-Content $expandedPath -Raw | gh secret set DEPLOY_SSH_KEY
        Write-Host " Done"
    } else {
        Write-Host "  ERROR: 파일을 찾을 수 없습니다: $expandedPath" -ForegroundColor Red
    }
} else {
    Write-Host "  Skipping DEPLOY_SSH_KEY (empty)" -ForegroundColor DarkGray
}

Write-Host ""

# -------------------------------------------------------------------
# 결과 확인
# -------------------------------------------------------------------
Write-Host "=== 등록된 Secrets ===" -ForegroundColor Cyan
gh secret list

Write-Host ""
Write-Host "완료! 누락된 시크릿은 나중에 개별 등록 가능:" -ForegroundColor Green
Write-Host '  echo "VALUE" | gh secret set SECRET_NAME' -ForegroundColor DarkGray
Write-Host '  gh secret set SECRET_NAME < file.txt' -ForegroundColor DarkGray
