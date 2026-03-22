# Windows Tesseract installation helper
# Usage: .\scripts\install-tesseract-windows.ps1

$ErrorActionPreference = "Stop"

function Test-TesseractInstalled {
    $cmd = Get-Command tesseract -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        Write-Host "Tesseract already available: $($cmd.Source)" -ForegroundColor Green
        & $cmd.Source --version | Select-Object -First 1
        return $true
    }
    return $false
}

if (Test-TesseractInstalled) {
    exit 0
}

Write-Host "Tesseract binary not found on PATH. Trying package managers..." -ForegroundColor Yellow

$installed = $false

if (Get-Command winget -ErrorAction SilentlyContinue) {
    $wingetIds = @(
        "UB-Mannheim.TesseractOCR",
        "Tesseract-OCR.Tesseract"
    )
    foreach ($pkg in $wingetIds) {
        try {
            Write-Host "Trying winget package: $pkg" -ForegroundColor Cyan
            winget install --id $pkg -e --accept-source-agreements --accept-package-agreements
            if (Test-TesseractInstalled) {
                $installed = $true
                break
            }
        }
        catch {
            Write-Host ("winget install failed for {0}: {1}" -f $pkg, $_.Exception.Message) -ForegroundColor Yellow
        }
    }
}

if (-not $installed -and (Get-Command choco -ErrorAction SilentlyContinue)) {
    try {
        Write-Host "Trying chocolatey package: tesseract" -ForegroundColor Cyan
        choco install tesseract -y
        if (Test-TesseractInstalled) {
            $installed = $true
        }
    }
    catch {
        Write-Host "choco install failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

if (-not $installed) {
    Write-Host ""
    Write-Host "Automatic install did not complete." -ForegroundColor Red
    Write-Host "Install Tesseract manually, then set TESSERACT_CMD in your .env if needed." -ForegroundColor Yellow
    Write-Host "Example:" -ForegroundColor DarkGray
    Write-Host '  TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe' -ForegroundColor DarkGray
    exit 1
}

Write-Host ""
Write-Host "Tesseract installation looks ready." -ForegroundColor Green
Write-Host "If the binary is not on PATH for the app runtime, set TESSERACT_CMD in .env." -ForegroundColor Yellow
