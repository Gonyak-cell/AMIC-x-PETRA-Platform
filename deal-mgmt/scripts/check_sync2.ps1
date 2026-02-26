# OneDrive 파일 접근성 확인
$folder = 'C:\Users\서지원\OneDrive - 주식회사 페트라브릿지파트너스\AMIC의 파일 - 1. AMIC\5. 기업 인수&합병\99_Archives\10_Pjt. Green\실사자료'

$files = Get-ChildItem -Path $folder -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 10

$ok = 0
$fail = 0

foreach ($f in $files) {
    try {
        $stream = [System.IO.File]::OpenRead($f.FullName)
        $b = $stream.ReadByte()
        $stream.Close()
        $ok++
        Write-Output "OK  : $($f.Name) ($($f.Length) bytes)"
    } catch {
        $fail++
        Write-Output "FAIL: $($f.Name) - $($_.Exception.Message)"
    }
}

Write-Output ""
Write-Output "Result: OK=$ok, FAIL=$fail"

# attrib 확인 (OneDrive cloud-only = O attribute)
Write-Output ""
Write-Output "=== attrib check (first 5) ==="
$sample = Get-ChildItem -Path $folder -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 5
foreach ($f in $sample) {
    $attr = (attrib $f.FullName) 2>&1
    Write-Output $attr
}
