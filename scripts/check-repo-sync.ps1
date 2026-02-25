# AMIC x PETRA Platform — 단독 리포 ↔ 모노레포 동기화 검증
# 사용법:
#   .\scripts\check-repo-sync.ps1           # 비교만
#   .\scripts\check-repo-sync.ps1 --fix     # 단독 리포 → 모노레포 동기화
#   .\scripts\check-repo-sync.ps1 --reverse # 모노레포 → 단독 리포 동기화
#   .\scripts\check-repo-sync.ps1 --module kiis  # 특정 모듈만 검사
#
# 배경: Session 22에서 KIIS 단독 리포 코드가 모노레포에 미반영되어
#       Docker 볼륨 마운트 시 이전 코드 실행 → 펀드 검색 0건 장애 발생

param(
    [switch]$Fix,
    [switch]$Reverse,
    [string]$Module = ""
)

$ErrorActionPreference = "Stop"

# ── 경로 설정 ────────────────────────────────────────────────
$MonoRoot = Split-Path -Parent $PSScriptRoot
$CodingRoot = Split-Path -Parent $MonoRoot

$Modules = @(
    @{
        Name       = "FDD"
        Standalone = Join-Path $CodingRoot "Auto FDD\backend"
        Mono       = Join-Path $MonoRoot "fdd\backend"
    },
    @{
        Name       = "KIIS"
        Standalone = Join-Path $CodingRoot "KIIS"
        Mono       = Join-Path $MonoRoot "kiis"
    },
    @{
        Name       = "IM"
        Standalone = Join-Path $CodingRoot "IM Module\auto-im-generator"
        Mono       = Join-Path $MonoRoot "im"
    }
)

# 특정 모듈만 필터
if ($Module) {
    $Modules = $Modules | Where-Object { $_.Name -eq $Module.ToUpper() }
    if (-not $Modules) {
        Write-Host "알 수 없는 모듈: $Module (FDD, KIIS, IM 중 선택)" -ForegroundColor Red
        exit 1
    }
}

# ── 제외 패턴 ────────────────────────────────────────────────
$ExcludeDirs = @(
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    ".env",
    "env",
    "node_modules",
    ".git",
    "alembic",
    "migrations",
    ".eggs",
    "*.egg-info",
    "dist",
    "build",
    ".tox",
    "output"
)

$ExcludeExtensions = @(".pyc", ".pyo", ".egg-info")

function Should-Exclude {
    param([string]$RelPath)
    foreach ($dir in $ExcludeDirs) {
        if ($RelPath -match "(^|[\\/])$([regex]::Escape($dir))([\\/]|$)") {
            return $true
        }
    }
    foreach ($ext in $ExcludeExtensions) {
        if ($RelPath.EndsWith($ext)) { return $true }
    }
    return $false
}

# ── 비교 함수 ────────────────────────────────────────────────
function Get-PyFiles {
    param([string]$Root)
    if (-not (Test-Path $Root)) { return @() }
    Get-ChildItem -Path $Root -Recurse -File -Filter "*.py" -ErrorAction SilentlyContinue |
        ForEach-Object {
            $rel = $_.FullName.Substring($Root.Length).TrimStart('\', '/')
            if (-not (Should-Exclude $rel)) {
                try {
                    $hash = (Get-FileHash $_.FullName -Algorithm MD5 -ErrorAction Stop).Hash
                    [PSCustomObject]@{
                        RelPath  = $rel
                        FullPath = $_.FullName
                        Hash     = $hash
                    }
                } catch {
                    # OneDrive 클라우드 파일 등 읽기 실패 시 건너뜀
                }
            }
        }
}

function Compare-Module {
    param(
        [string]$Name,
        [string]$StandalonePath,
        [string]$MonoPath
    )

    Write-Host ""
    Write-Host "[$Name] 동기화 확인 중..." -ForegroundColor Cyan

    # 경로 존재 확인
    if (-not (Test-Path $StandalonePath)) {
        Write-Host "  ! 단독 리포 경로 없음: $StandalonePath" -ForegroundColor Yellow
        return @{ Matched = 0; Mismatched = 0; OnlyStandalone = 0; OnlyMono = 0; Details = @() }
    }
    if (-not (Test-Path $MonoPath)) {
        Write-Host "  ! 모노레포 경로 없음: $MonoPath" -ForegroundColor Yellow
        return @{ Matched = 0; Mismatched = 0; OnlyStandalone = 0; OnlyMono = 0; Details = @() }
    }

    $standaloneFiles = @(Get-PyFiles $StandalonePath)
    $monoFiles = @(Get-PyFiles $MonoPath)

    $standaloneMap = @{}
    foreach ($f in $standaloneFiles) { $standaloneMap[$f.RelPath] = $f }

    $monoMap = @{}
    foreach ($f in $monoFiles) { $monoMap[$f.RelPath] = $f }

    $allPaths = ($standaloneMap.Keys + $monoMap.Keys) | Sort-Object -Unique

    $matched = 0
    $mismatched = 0
    $onlyStandalone = 0
    $onlyMono = 0
    $details = @()

    foreach ($rel in $allPaths) {
        $inStandalone = $standaloneMap.ContainsKey($rel)
        $inMono = $monoMap.ContainsKey($rel)

        if ($inStandalone -and $inMono) {
            if ($standaloneMap[$rel].Hash -eq $monoMap[$rel].Hash) {
                $matched++
            } else {
                $mismatched++
                # 최종 수정 시간으로 어느 쪽이 최신인지 판단
                $sTime = (Get-Item $standaloneMap[$rel].FullPath).LastWriteTime
                $mTime = (Get-Item $monoMap[$rel].FullPath).LastWriteTime
                $newer = if ($sTime -gt $mTime) { "standalone" } else { "monorepo" }
                $detail = @{ Path = $rel; Type = "mismatch"; Newer = $newer }
                $details += $detail
                Write-Host ("  X {0} — 불일치 ({1}가 최신, {2})" -f $rel, $(if ($newer -eq "standalone") {"단독 리포"} else {"모노레포"}), $(if ($newer -eq "standalone") {$sTime.ToString("MM/dd HH:mm")} else {$mTime.ToString("MM/dd HH:mm")})) -ForegroundColor Red
            }
        } elseif ($inStandalone -and -not $inMono) {
            $onlyStandalone++
            $details += @{ Path = $rel; Type = "only_standalone" }
            Write-Host "  + $rel — 단독 리포에만 존재" -ForegroundColor Yellow
        } else {
            $onlyMono++
            $details += @{ Path = $rel; Type = "only_mono" }
            Write-Host "  - $rel — 모노레포에만 존재" -ForegroundColor DarkYellow
        }
    }

    if ($mismatched -eq 0 -and $onlyStandalone -eq 0 -and $onlyMono -eq 0) {
        Write-Host ("  OK 모든 파일 일치 ({0}개 파일)" -f $matched) -ForegroundColor Green
    } else {
        Write-Host ("  일치: {0} | 불일치: {1} | 단독리포만: {2} | 모노레포만: {3}" -f $matched, $mismatched, $onlyStandalone, $onlyMono) -ForegroundColor Gray
    }

    return @{
        Matched        = $matched
        Mismatched     = $mismatched
        OnlyStandalone = $onlyStandalone
        OnlyMono       = $onlyMono
        Details        = $details
    }
}

# ── 동기화 함수 ──────────────────────────────────────────────
function Sync-Files {
    param(
        [string]$SourceRoot,
        [string]$DestRoot,
        [array]$Details,
        [string]$Direction
    )

    $copied = 0
    foreach ($d in $Details) {
        $srcFile = Join-Path $SourceRoot $d.Path
        $dstFile = Join-Path $DestRoot $d.Path

        if ($d.Type -eq "mismatch") {
            # 불일치: 소스가 최신일 때만 복사
            $shouldCopy = $false
            if ($Direction -eq "to_mono" -and $d.Newer -eq "standalone") {
                $shouldCopy = $true
            } elseif ($Direction -eq "to_standalone" -and $d.Newer -eq "monorepo") {
                $shouldCopy = $true
            }

            if ($shouldCopy) {
                $dstDir = Split-Path $dstFile -Parent
                if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
                Copy-Item $srcFile $dstFile -Force
                Write-Host "  -> $($d.Path)" -ForegroundColor Green
                $copied++
            } else {
                Write-Host "  == $($d.Path) — 대상이 최신, 건너뜀" -ForegroundColor DarkGray
            }
        } elseif ($d.Type -eq "only_standalone" -and $Direction -eq "to_mono") {
            # 단독 리포에만 있는 파일 → 모노레포로 복사
            $dstDir = Split-Path $dstFile -Parent
            if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
            Copy-Item $srcFile $dstFile -Force
            Write-Host "  +> $($d.Path)" -ForegroundColor Green
            $copied++
        } elseif ($d.Type -eq "only_mono" -and $Direction -eq "to_standalone") {
            # 모노레포에만 있는 파일 → 단독 리포로 복사
            $srcFile = Join-Path $SourceRoot $d.Path
            $dstFile = Join-Path $DestRoot $d.Path
            $dstDir = Split-Path $dstFile -Parent
            if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
            Copy-Item $srcFile $dstFile -Force
            Write-Host "  +> $($d.Path)" -ForegroundColor Green
            $copied++
        }
    }
    return $copied
}

# ── 로깅 모듈 동기화 검증 ─────────────────────────────────────
# log_context.py, log_decorators.py는 4개 백엔드에서 동일해야 함
# logging.py, log_middleware.py는 백엔드별 차이(SERVICE_NAME, import 경로)가 있으므로 존재 여부만 확인

$LoggingBackends = @(
    @{ Name = "FDD";       CorePath = Join-Path $MonoRoot "fdd\backend\app\core" },
    @{ Name = "KIIS";      CorePath = Join-Path $MonoRoot "kiis\app\core" },
    @{ Name = "IM";        CorePath = Join-Path $MonoRoot "im\src\api\core" },
    @{ Name = "Deal-mgmt"; CorePath = Join-Path $MonoRoot "deal-mgmt\app\core" }
)

# 동일해야 하는 파일 (해시 비교)
$IdenticalFiles = @("log_context.py", "log_decorators.py")
# 존재만 확인하는 파일 (백엔드별 차이 허용)
$ExistFiles = @("logging.py", "log_middleware.py")

function Check-LoggingSync {
    Write-Host ""
    Write-Host "[Logging] 구조화 로깅 모듈 동기화 확인..." -ForegroundColor Cyan

    $drifted = 0

    # 동일해야 하는 파일: 해시 비교
    foreach ($fileName in $IdenticalFiles) {
        $hashes = @{}
        foreach ($be in $LoggingBackends) {
            $filePath = Join-Path $be.CorePath $fileName
            if (Test-Path $filePath) {
                $h = (Get-FileHash $filePath -Algorithm MD5 -ErrorAction SilentlyContinue).Hash
                $hashes[$be.Name] = $h
            } else {
                $hashes[$be.Name] = $null
                Write-Host "  ! $fileName — $($be.Name)에 존재하지 않음" -ForegroundColor Red
                $drifted++
            }
        }

        $uniqueHashes = ($hashes.Values | Where-Object { $_ -ne $null } | Sort-Object -Unique)
        if ($uniqueHashes.Count -gt 1) {
            Write-Host "  X $fileName — 백엔드 간 불일치 감지" -ForegroundColor Red
            foreach ($be in $LoggingBackends) {
                if ($hashes[$be.Name]) {
                    Write-Host "    $($be.Name): $($hashes[$be.Name].Substring(0, 8))..." -ForegroundColor Gray
                }
            }
            $drifted++
        } elseif ($uniqueHashes.Count -eq 1 -and ($hashes.Values | Where-Object { $_ -eq $null }).Count -eq 0) {
            Write-Host "  OK $fileName — 4개 백엔드 동일" -ForegroundColor Green
        }
    }

    # 존재 여부만 확인하는 파일
    foreach ($fileName in $ExistFiles) {
        $missing = @()
        foreach ($be in $LoggingBackends) {
            $filePath = Join-Path $be.CorePath $fileName
            if (-not (Test-Path $filePath)) {
                $missing += $be.Name
            }
        }
        if ($missing.Count -gt 0) {
            Write-Host "  ! $fileName — 누락: $($missing -join ', ')" -ForegroundColor Red
            $drifted++
        } else {
            Write-Host "  OK $fileName — 4개 백엔드 존재 확인" -ForegroundColor Green
        }
    }

    return $drifted
}

# ── 메인 실행 ────────────────────────────────────────────────
Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  Repo Sync Check — Standalone vs Monorepo" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

if ($Fix) {
    Write-Host "  모드: --fix (단독 리포 -> 모노레포)" -ForegroundColor Yellow
} elseif ($Reverse) {
    Write-Host "  모드: --reverse (모노레포 -> 단독 리포)" -ForegroundColor Yellow
} else {
    Write-Host "  모드: 비교만 (수정 없음)" -ForegroundColor Gray
}

$totalMismatched = 0
$totalSynced = 0

foreach ($mod in $Modules) {
    $result = Compare-Module -Name $mod.Name -StandalonePath $mod.Standalone -MonoPath $mod.Mono
    $totalMismatched += ($result.Mismatched + $result.OnlyStandalone + $result.OnlyMono)

    if ($result.Details.Count -gt 0) {
        if ($Fix) {
            Write-Host ""
            Write-Host "  [$($mod.Name)] 단독 리포 -> 모노레포 동기화..." -ForegroundColor Yellow
            $synced = Sync-Files -SourceRoot $mod.Standalone -DestRoot $mod.Mono -Details $result.Details -Direction "to_mono"
            $totalSynced += $synced
        } elseif ($Reverse) {
            Write-Host ""
            Write-Host "  [$($mod.Name)] 모노레포 -> 단독 리포 동기화..." -ForegroundColor Yellow
            $synced = Sync-Files -SourceRoot $mod.Mono -DestRoot $mod.Standalone -Details $result.Details -Direction "to_standalone"
            $totalSynced += $synced
        }
    }
}

# ── 로깅 모듈 동기화 검증 ──────────────────────────────────────
$loggingDrift = Check-LoggingSync
$totalMismatched += $loggingDrift

# ── 결과 요약 ────────────────────────────────────────────────
Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan

if ($totalMismatched -eq 0) {
    Write-Host "  OK 모든 모듈 동기화 완료" -ForegroundColor Green
    exit 0
} else {
    if ($Fix -or $Reverse) {
        Write-Host "  $totalSynced 개 파일 동기화 완료" -ForegroundColor Green
    } else {
        Write-Host "  $totalMismatched 개 파일 불일치 발견" -ForegroundColor Red
        Write-Host ""
        Write-Host "  해결 방법:" -ForegroundColor Gray
        Write-Host "    .\scripts\check-repo-sync.ps1 --fix      # 단독 리포 -> 모노레포" -ForegroundColor Gray
        Write-Host "    .\scripts\check-repo-sync.ps1 --reverse  # 모노레포 -> 단독 리포" -ForegroundColor Gray
        if ($loggingDrift -gt 0) {
            Write-Host "    로깅 모듈 불일치: log_context.py, log_decorators.py를 수동 동기화하세요" -ForegroundColor Gray
        }
    }
    exit 1
}
