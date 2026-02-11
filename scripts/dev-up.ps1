# AMIC x PETRA Platform — 개발 환경 시작
# 사용법: .\scripts\dev-up.ps1

param(
    [switch]$Build,
    [switch]$NoDetach
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot

try {
    # .env 파일 확인
    if (-not (Test-Path ".env")) {
        Write-Host "[INFO] .env 파일이 없습니다. .env.example을 복사합니다..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "[INFO] .env 파일이 생성되었습니다. API 키를 설정해 주세요." -ForegroundColor Yellow
    }

    # Docker Compose 실행
    $composeArgs = @("compose", "up")
    if (-not $NoDetach) { $composeArgs += "-d" }
    if ($Build) { $composeArgs += "--build" }

    Write-Host "[START] 개발 환경을 시작합니다..." -ForegroundColor Cyan
    & docker @composeArgs

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Docker Compose 실행 실패" -ForegroundColor Red
        exit 1
    }

    # 서비스 대기
    Write-Host ""
    Write-Host "[WAIT] 서비스가 준비될 때까지 대기 중..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10

    # 접속 정보 출력
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  AMIC x PETRA Platform - DEV" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Frontend (nginx):  http://localhost:3000" -ForegroundColor White
    Write-Host "  Frontend (Vite):   http://localhost:5173" -ForegroundColor White
    Write-Host ""
    Write-Host "  FDD API:           http://localhost:8000" -ForegroundColor White
    Write-Host "  KIIS API:          http://localhost:8001" -ForegroundColor White
    Write-Host "  IM API:            http://localhost:8002" -ForegroundColor White
    Write-Host ""
    Write-Host "  FDD DB:            localhost:5433" -ForegroundColor DarkGray
    Write-Host "  KIIS DB:           localhost:5434" -ForegroundColor DarkGray
    Write-Host "  IM DB:             localhost:5435" -ForegroundColor DarkGray
    Write-Host "  KIIS Redis:        localhost:6379" -ForegroundColor DarkGray
    Write-Host "  IM Redis:          localhost:6380" -ForegroundColor DarkGray
    Write-Host "  Elasticsearch:     localhost:9200" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  로그 조회: .\scripts\logs.ps1" -ForegroundColor DarkGray
    Write-Host "  종료:      .\scripts\dev-down.ps1" -ForegroundColor DarkGray
    Write-Host ""
}
finally {
    Pop-Location
}
