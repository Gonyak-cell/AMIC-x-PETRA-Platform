# AMIC x PETRA Platform — 프로덕션 환경 시작
# 사용법: .\scripts\prod-up.ps1

param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot

try {
    # .env 파일 확인
    if (-not (Test-Path ".env")) {
        Write-Host "[ERROR] .env 파일이 없습니다." -ForegroundColor Red
        Write-Host "  .env.production.example을 .env로 복사하고 값을 설정하세요:" -ForegroundColor Yellow
        Write-Host "  cp .env.production.example .env" -ForegroundColor Yellow
        exit 1
    }

    # CHANGE_ME 값 확인
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "CHANGE_ME") {
        Write-Host "[WARN] .env 파일에 CHANGE_ME 값이 남아 있습니다!" -ForegroundColor Red
        Write-Host "  모든 CHANGE_ME 값을 실제 값으로 변경하세요." -ForegroundColor Yellow

        $confirm = Read-Host "  그래도 계속하시겠습니까? (y/N)"
        if ($confirm -ne "y") {
            Write-Host "[ABORT] 중단합니다." -ForegroundColor Yellow
            exit 0
        }
    }

    # Docker Compose 실행 (prod overlay)
    $args = @("compose", "-f", "docker-compose.yml", "-f", "docker-compose.prod.yml", "up", "-d")
    if ($Build) { $args += "--build" }

    Write-Host "[START] 프로덕션 환경을 시작합니다..." -ForegroundColor Cyan
    & docker @args

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Docker Compose 실행 실패" -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  AMIC x PETRA Platform - PRODUCTION" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  HTTP:   http://localhost" -ForegroundColor White
    Write-Host "  HTTPS:  https://localhost" -ForegroundColor White
    Write-Host ""
    Write-Host "  로그: .\scripts\logs.ps1" -ForegroundColor DarkGray
    Write-Host "  헬스: .\scripts\health-check.ps1" -ForegroundColor DarkGray
    Write-Host ""
}
finally {
    Pop-Location
}
