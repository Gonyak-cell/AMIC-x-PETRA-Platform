param(
    [int]$FrontendPort = 5173,
    [int]$KiisPort = 8001,
    [int]$MaPort = 8003,
    [int]$FddPort = 8000,
    [switch]$IncludeFdd,
    [string]$FddDatabaseUrl = ""
)

$ErrorActionPreference = "Stop"

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$logsDir = Join-Path $workspaceRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

function Get-ListeningProcessId {
    param([int]$Port)

    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $connection) {
        return $null
    }

    return $connection.OwningProcess
}

function Wait-ForHttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30,
        [string]$ExpectedContent
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            $body = if ($null -ne $response.Content) { [string]$response.Content } else { "" }
            if (
                $response.StatusCode -ge 200 -and
                $response.StatusCode -lt 500 -and
                (
                    [string]::IsNullOrWhiteSpace($ExpectedContent) -or
                    $body.Contains($ExpectedContent)
                )
            ) {
                return
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    } while ((Get-Date) -lt $deadline)

    throw "Timed out waiting for $Url"
}

function Test-HttpOk {
    param(
        [string]$Url,
        [string]$ExpectedContent
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        $body = if ($null -ne $response.Content) { [string]$response.Content } else { "" }
        return (
            $response.StatusCode -ge 200 -and
            $response.StatusCode -lt 500 -and
            (
                [string]::IsNullOrWhiteSpace($ExpectedContent) -or
                $body.Contains($ExpectedContent)
            )
        )
    } catch {
        return $false
    }
}

function Get-ProcessSummary {
    param([int]$ProcessId)

    if (-not $ProcessId) {
        return $null
    }

    return Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue |
        Select-Object -First 1 ProcessId, Name, CommandLine
}

function Write-PortIdentity {
    param(
        [string]$Name,
        [int]$Port,
        [string]$HealthUrl,
        [string]$ExpectedContent
    )

    $existingPid = Get-ListeningProcessId -Port $Port
    if (-not $existingPid) {
        Write-Host ("preflight {0}: port {1} is free" -f $Name, $Port)
        return
    }

    $summary = Get-ProcessSummary -ProcessId $existingPid
    $commandLine = if ($summary -and $summary.CommandLine) { $summary.CommandLine } else { "<unknown>" }
    $matchesExpected = Test-HttpOk -Url $HealthUrl -ExpectedContent $ExpectedContent
    $healthState = if ($matchesExpected) { "expected app" } elseif (Test-HttpOk -Url $HealthUrl) { "other healthy app" } else { "listener without expected health marker" }
    Write-Host ("preflight {0}: port {1} -> PID {2}, {3}, command: {4}" -f $Name, $Port, $existingPid, $healthState, $commandLine)
}

function Find-AvailableFrontendPort {
    param(
        [int]$PreferredPort,
        [string]$ExpectedContent
    )

    $port = $PreferredPort
    while ($true) {
        $frontendPid = Get-ListeningProcessId -Port $port
        if (-not $frontendPid) {
            return $port
        }
        if (Test-HttpOk -Url "http://127.0.0.1:$port/" -ExpectedContent $ExpectedContent) {
            return $port
        }
        $summary = Get-ProcessSummary -ProcessId $frontendPid
        $commandLine = if ($summary -and $summary.CommandLine) { $summary.CommandLine } else { "<unknown>" }
        Write-Host ("frontend port {0} is occupied by another app (PID {1}, command: {2}); trying {3}" -f $port, $frontendPid, $commandLine, ($port + 1))
        $port += 1
    }
}

function Start-BackgroundProcess {
    param(
        [string]$Name,
        [int]$Port,
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory,
        [string]$OutLog,
        [string]$ErrLog,
        [string]$HealthUrl,
        [string]$ExpectedContent
    )

    $existingPid = Get-ListeningProcessId -Port $Port
    if ($existingPid) {
        if (Test-HttpOk -Url $HealthUrl -ExpectedContent $ExpectedContent) {
            return @{
                Name = $Name
                Port = $Port
                Pid = $existingPid
                Reused = $true
            }
        }

        if (Test-HttpOk -Url $HealthUrl) {
            $processSummary = Get-ProcessSummary -ProcessId $existingPid
            $commandLine = if ($processSummary -and $processSummary.CommandLine) {
                $processSummary.CommandLine
            } else {
                "<unknown>"
            }
            throw (
                "Port $Port is already serving a different app. " +
                "Expected '$Name' at $HealthUrl but found another healthy process " +
                "(PID $existingPid, command: $commandLine). " +
                "Start with a different port or stop the conflicting app."
            )
        }

        if (-not (Test-HttpOk -Url $HealthUrl)) {
            $processSummary = Get-ProcessSummary -ProcessId $existingPid
            $commandLine = if ($processSummary -and $processSummary.CommandLine) {
                $processSummary.CommandLine
            } else {
                "<unknown>"
            }
            throw (
                "Port $Port already has a listener but did not expose the expected '$Name' health marker " +
                "(PID $existingPid, command: $commandLine). Stop it manually or choose another port."
            )
        }
    }

    $existingPid = Get-ListeningProcessId -Port $Port
    if ($existingPid) {
        return @{
            Name = $Name
            Port = $Port
            Pid = $existingPid
            Reused = $true
        }
    }

    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $OutLog `
        -RedirectStandardError $ErrLog `
        -PassThru

    Wait-ForHttpOk -Url $HealthUrl -ExpectedContent $ExpectedContent

    $listenerPid = Get-ListeningProcessId -Port $Port
    if (-not $listenerPid) {
        $listenerPid = $process.Id
    }

    return @{
        Name = $Name
        Port = $Port
        Pid = $listenerPid
        Reused = $false
    }
}

function Initialize-FddLocalDevDatabase {
    param(
        [string]$DatabaseUrl,
        [string]$WorkingDirectory
    )

    if ([string]::IsNullOrWhiteSpace($DatabaseUrl) -or -not $DatabaseUrl.StartsWith("sqlite")) {
        return
    }

    $previousDatabaseUrl = $env:DATABASE_URL
    $previousAuthEnabled = $env:AUTH_ENABLED
    $previousPythonUtf8 = $env:PYTHONUTF8
    $previousPythonIoEncoding = $env:PYTHONIOENCODING
    try {
        $env:DATABASE_URL = $DatabaseUrl
        $env:AUTH_ENABLED = "false"
        $env:PYTHONUTF8 = "1"
        $env:PYTHONIOENCODING = "utf-8"
        $initScript = @'
from app.database import Base, engine
import app.main  # noqa: F401 - importing registers models with metadata

Base.metadata.create_all(bind=engine)
print(f"initialized FDD local dev database: {engine.url}")
'@
        Push-Location $WorkingDirectory
        try {
            $initScript | python - | Write-Host
        } finally {
            Pop-Location
        }
    } finally {
        $env:DATABASE_URL = $previousDatabaseUrl
        $env:AUTH_ENABLED = $previousAuthEnabled
        $env:PYTHONUTF8 = $previousPythonUtf8
        $env:PYTHONIOENCODING = $previousPythonIoEncoding
    }
}

Write-PortIdentity -Name "frontend" -Port $FrontendPort -HealthUrl "http://127.0.0.1:$FrontendPort/" -ExpectedContent "AMIC x PETRA Platform"
Write-PortIdentity -Name "kiis" -Port $KiisPort -HealthUrl "http://127.0.0.1:$KiisPort/health" -ExpectedContent '"service":"kiis"'
Write-PortIdentity -Name "deal-mgmt" -Port $MaPort -HealthUrl "http://127.0.0.1:$MaPort/health" -ExpectedContent '"service":"deal-mgmt"'
if ($IncludeFdd) {
    Write-PortIdentity -Name "fdd" -Port $FddPort -HealthUrl "http://127.0.0.1:$FddPort/health" -ExpectedContent '"db":"ok"'
}

$ResolvedFrontendPort = Find-AvailableFrontendPort -PreferredPort $FrontendPort -ExpectedContent "AMIC x PETRA Platform"

$kiisResult = Start-BackgroundProcess `
    -Name "kiis" `
    -Port $KiisPort `
    -FilePath "cmd.exe" `
    -ArgumentList @("/c", "set KIIS_PORT=$KiisPort&& set KIIS_RELOAD=false&& set KIIS_SCHEDULER_ENABLED=true&& set PYTHONUTF8=1&& set PYTHONIOENCODING=utf-8&& python kiis/scripts/run_dev_server.py") `
    -WorkingDirectory $workspaceRoot `
    -OutLog (Join-Path $logsDir "kiis-dev-$KiisPort.out.log") `
    -ErrLog (Join-Path $logsDir "kiis-dev-$KiisPort.err.log") `
    -HealthUrl "http://127.0.0.1:$KiisPort/health" `
    -ExpectedContent '"service":"kiis"'

$maResult = Start-BackgroundProcess `
    -Name "deal-mgmt" `
    -Port $MaPort `
    -FilePath "cmd.exe" `
    -ArgumentList @("/c", "set ENV=local&& set DEAL_MGMT_PORT=$MaPort&& set DEAL_MGMT_RELOAD=false&& set PYTHONUTF8=1&& set PYTHONIOENCODING=utf-8&& python deal-mgmt/scripts/run_dev_server.py") `
    -WorkingDirectory $workspaceRoot `
    -OutLog (Join-Path $logsDir "deal-mgmt-dev-$MaPort.out.log") `
    -ErrLog (Join-Path $logsDir "deal-mgmt-dev-$MaPort.err.log") `
    -HealthUrl "http://127.0.0.1:$MaPort/health" `
    -ExpectedContent '"service":"deal-mgmt"'

$fddResult = $null
if ($IncludeFdd) {
    $resolvedFddDatabaseUrl = if ([string]::IsNullOrWhiteSpace($FddDatabaseUrl)) {
        if ([string]::IsNullOrWhiteSpace($env:FDD_DATABASE_URL)) {
            "sqlite:///./fdd_local_dev.db"
        } else {
            $env:FDD_DATABASE_URL
        }
    } else {
        $FddDatabaseUrl
    }
    $fddBackendDir = Join-Path $workspaceRoot "fdd/backend"
    Initialize-FddLocalDevDatabase -DatabaseUrl $resolvedFddDatabaseUrl -WorkingDirectory $fddBackendDir

    $fddResult = Start-BackgroundProcess `
        -Name "fdd" `
        -Port $FddPort `
        -FilePath "cmd.exe" `
        -ArgumentList @("/c", "set DATABASE_URL=$resolvedFddDatabaseUrl&& set AUTH_ENABLED=false&& set PYTHONUTF8=1&& set PYTHONIOENCODING=utf-8&& python -m uvicorn app.main:app --host 0.0.0.0 --port $FddPort") `
        -WorkingDirectory $fddBackendDir `
        -OutLog (Join-Path $logsDir "fdd-dev-$FddPort.out.log") `
        -ErrLog (Join-Path $logsDir "fdd-dev-$FddPort.err.log") `
        -HealthUrl "http://127.0.0.1:$FddPort/health" `
        -ExpectedContent '"db":"ok"'
}

$frontendResult = Start-BackgroundProcess `
    -Name "amic-platform" `
    -Port $ResolvedFrontendPort `
    -FilePath "C:\Program Files\nodejs\npm.cmd" `
    -ArgumentList @("run", "dev", "--", "--host", "0.0.0.0", "--port", "$ResolvedFrontendPort") `
    -WorkingDirectory (Join-Path $workspaceRoot "amic-platform") `
    -OutLog (Join-Path $logsDir "amic-platform-dev-$ResolvedFrontendPort.out.log") `
    -ErrLog (Join-Path $logsDir "amic-platform-dev-$ResolvedFrontendPort.err.log") `
    -HealthUrl "http://127.0.0.1:$ResolvedFrontendPort/" `
    -ExpectedContent "AMIC x PETRA Platform"

foreach ($result in @($kiisResult, $maResult, $fddResult, $frontendResult)) {
    if (-not $result) { continue }
    $status = if ($result.Reused) { "reused" } else { "started" }
    Write-Host ("{0} {1} on http://127.0.0.1:{2} (PID {3})" -f $status, $result.Name, $result.Port, $result.Pid)
}
