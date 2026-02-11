# AMIC x PETRA Platform — 전체 서비스 헬스 체크
# 사용법: .\scripts\health-check.ps1

$ErrorActionPreference = "SilentlyContinue"

$services = @(
    @{ Name = "Frontend (nginx)"; Url = "http://localhost:3000" },
    @{ Name = "Frontend (Vite)";  Url = "http://localhost:5173" },
    @{ Name = "FDD API";          Url = "http://localhost:8000/health" },
    @{ Name = "KIIS API";         Url = "http://localhost:8001/health" },
    @{ Name = "IM API";           Url = "http://localhost:8002/health" },
    @{ Name = "Elasticsearch";    Url = "http://localhost:9200/_cluster/health" }
)

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  AMIC x PETRA Platform — Health Check" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host ("{0,-22} {1,-10} {2,-10}" -f "Service", "Status", "Time(ms)")
Write-Host ("{0,-22} {1,-10} {2,-10}" -f "-------", "------", "--------")

foreach ($svc in $services) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $response = Invoke-WebRequest -Uri $svc.Url -TimeoutSec 5 -UseBasicParsing
        $sw.Stop()
        $status = "OK"
        $color = "Green"
    }
    catch {
        $sw.Stop()
        $status = "DOWN"
        $color = "Red"
    }

    $elapsed = $sw.ElapsedMilliseconds
    Write-Host ("{0,-22} " -f $svc.Name) -NoNewline
    Write-Host ("{0,-10} " -f $status) -ForegroundColor $color -NoNewline
    Write-Host ("{0,-10}" -f "${elapsed}ms")
}

# Docker 컨테이너 상태
Write-Host ""
Write-Host "--- Docker Container Status ---" -ForegroundColor DarkGray
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>$null

Write-Host ""
