param(
    [string]$SourcePath = 'D:\04_App\Platform',
    [string]$TargetPath = (Join-Path ([Environment]::GetFolderPath('UserProfile')) 'App\02_Platform'),
    [int]$RetrySeconds = 5,
    [int]$MaxWaitMinutes = 720
)

$ErrorActionPreference = 'Stop'

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$sourceParent = Split-Path -Parent $SourcePath
$sourceName = Split-Path -Leaf $SourcePath
$backupPath = Join-Path $sourceParent ($sourceName + '.pre-migration-backup-' + $timestamp)
$logDir = Join-Path $TargetPath 'logs'
$logPath = Join-Path $logDir 'finalize-platform-migration.log'
$deadline = (Get-Date).AddMinutes($MaxWaitMinutes)

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-Log {
    param([string]$Message)

    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath $logPath -Value $line
}

function Test-JunctionTarget {
    param(
        [string]$PathToCheck,
        [string]$ExpectedTarget
    )

    if (-not (Test-Path -LiteralPath $PathToCheck)) {
        return $false
    }

    $item = Get-Item -LiteralPath $PathToCheck -Force
    if (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        return $false
    }

    $resolvedPath = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $PathToCheck).Path).TrimEnd('\')
    $resolvedTarget = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $ExpectedTarget).Path).TrimEnd('\')
    return $resolvedPath -eq $resolvedTarget
}

Write-Log "Finalize migration watcher started. Source=$SourcePath Target=$TargetPath Backup=$backupPath"

while ((Get-Date) -lt $deadline) {
    try {
        if (Test-JunctionTarget -PathToCheck $SourcePath -ExpectedTarget $TargetPath) {
            Write-Log 'Source path already points to target. Nothing to do.'
            exit 0
        }

        if ((-not (Test-Path -LiteralPath $SourcePath)) -and (Test-Path -LiteralPath $backupPath)) {
            Write-Log 'Source path already renamed. Attempting to create junction.'
            $mklinkOutput = cmd /c "mklink /J `"$SourcePath`" `"$TargetPath`""
            Write-Log ($mklinkOutput | Out-String).Trim()
            if (Test-JunctionTarget -PathToCheck $SourcePath -ExpectedTarget $TargetPath) {
                Write-Log 'Junction created after previously moving source.'
                exit 0
            }
        }

        if (-not (Test-Path -LiteralPath $SourcePath)) {
            Write-Log 'Source path is missing and no backup path exists yet. Waiting.'
            Start-Sleep -Seconds $RetrySeconds
            continue
        }

        Write-Log 'Attempting to rename source directory to backup path.'
        Rename-Item -LiteralPath $SourcePath -NewName (Split-Path -Leaf $backupPath)
        Write-Log 'Source directory renamed successfully.'

        $mklinkOutput = cmd /c "mklink /J `"$SourcePath`" `"$TargetPath`""
        Write-Log ($mklinkOutput | Out-String).Trim()

        if (Test-JunctionTarget -PathToCheck $SourcePath -ExpectedTarget $TargetPath) {
            Write-Log 'Junction created successfully.'
            exit 0
        }

        Write-Log 'Rename succeeded but junction verification failed. Retrying.'
    }
    catch {
        Write-Log ('Retry after failure: ' + $_.Exception.Message)
    }

    Start-Sleep -Seconds $RetrySeconds
}

Write-Log 'Timed out waiting to finalize migration.'
exit 1
