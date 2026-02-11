# AMIC x PETRA Platform — 로그 조회
# 사용법:
#   .\scripts\logs.ps1                 # 전체 로그
#   .\scripts\logs.ps1 -Service fdd-api  # 특정 서비스 로그
#   .\scripts\logs.ps1 -Tail 50         # 최근 50줄

param(
    [string]$Service = "",
    [int]$Tail = 100,
    [switch]$NoFollow
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot

try {
    $composeArgs = @("compose", "logs")
    if (-not $NoFollow) { $composeArgs += "-f" }
    $composeArgs += "--tail=$Tail"
    if ($Service -ne "") { $composeArgs += $Service }

    & docker @composeArgs
}
finally {
    Pop-Location
}
