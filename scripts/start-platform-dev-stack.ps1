param(
    [int]$FrontendPort = 5173,
    [int]$KiisPort = 8001,
    [int]$MaPort = 8003
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
            Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
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

    $pid = Get-ListeningProcessId -Port $Port
    if (-not $pid) {
        $pid = $process.Id
    }

    return @{
        Name = $Name
        Port = $Port
        Pid = $pid
        Reused = $false
    }
}

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
    -ArgumentList @("/c", "set DEAL_MGMT_PORT=$MaPort&& set DEAL_MGMT_RELOAD=false&& set PYTHONUTF8=1&& set PYTHONIOENCODING=utf-8&& python deal-mgmt/scripts/run_dev_server.py") `
    -WorkingDirectory $workspaceRoot `
    -OutLog (Join-Path $logsDir "deal-mgmt-dev-$MaPort.out.log") `
    -ErrLog (Join-Path $logsDir "deal-mgmt-dev-$MaPort.err.log") `
    -HealthUrl "http://127.0.0.1:$MaPort/health" `
    -ExpectedContent '"service":"deal-mgmt"'

$frontendResult = Start-BackgroundProcess `
    -Name "amic-platform" `
    -Port $FrontendPort `
    -FilePath "C:\Program Files\nodejs\npm.cmd" `
    -ArgumentList @("run", "dev", "--", "--host", "0.0.0.0", "--port", "$FrontendPort") `
    -WorkingDirectory (Join-Path $workspaceRoot "amic-platform") `
    -OutLog (Join-Path $logsDir "amic-platform-dev-$FrontendPort.out.log") `
    -ErrLog (Join-Path $logsDir "amic-platform-dev-$FrontendPort.err.log") `
    -HealthUrl "http://127.0.0.1:$FrontendPort/" `
    -ExpectedContent "AMIC x PETRA Platform"

foreach ($result in @($kiisResult, $maResult, $frontendResult)) {
    $status = if ($result.Reused) { "reused" } else { "started" }
    Write-Host ("{0} {1} on http://127.0.0.1:{2} (PID {3})" -f $status, $result.Name, $result.Port, $result.Pid)
}
