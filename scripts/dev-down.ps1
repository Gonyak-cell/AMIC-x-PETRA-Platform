# AMIC x PETRA Platform — 개발 환경 종료
# 사용법: .\scripts\dev-down.ps1 [-Volumes]

param(
    [switch]$Volumes
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot

try {
    $composeArgs = @("compose", "down")
    if ($Volumes) {
        Write-Host "[WARN] 볼륨을 함께 삭제합니다 (DB 데이터 포함)." -ForegroundColor Yellow
        $composeArgs += "-v"
    }

    Write-Host "[STOP] 개발 환경을 종료합니다..." -ForegroundColor Cyan
    & docker @composeArgs

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[DONE] 모든 서비스가 종료되었습니다." -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Docker Compose 종료 실패" -ForegroundColor Red
    }
}
finally {
    Pop-Location
}
