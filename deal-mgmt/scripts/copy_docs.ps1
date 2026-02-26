# Pjt. Green 실사자료 중 PDF/DOCX/HWP만 로컬로 복사
$src = 'C:\Users\서지원\OneDrive - 주식회사 페트라브릿지파트너스\AMIC의 파일 - 1. AMIC\5. 기업 인수&합병\99_Archives\10_Pjt. Green\실사자료'
$dst = 'C:\temp\ldd_docs'

if (-not (Test-Path $dst)) { New-Item -ItemType Directory -Path $dst -Force | Out-Null }

$exts = @('.pdf', '.docx', '.hwp', '.hwpx', '.xlsx')
$copied = 0
$failed = 0

Get-ChildItem -Path $src -Recurse -File | Where-Object { $exts -contains $_.Extension.ToLower() } | ForEach-Object {
    $target = Join-Path $dst $_.Name
    # Avoid name collision by appending index
    if (Test-Path $target) {
        $base = [System.IO.Path]::GetFileNameWithoutExtension($_.Name)
        $ext = $_.Extension
        $target = Join-Path $dst "$base`_$copied$ext"
    }
    try {
        Copy-Item -Path $_.FullName -Destination $target -Force -ErrorAction Stop
        $copied++
        if ($copied % 20 -eq 0) { Write-Output "  $copied files copied..." }
    } catch {
        $failed++
    }
}

Write-Output ""
Write-Output "Done: $copied copied, $failed failed"
Write-Output "Location: $dst"
