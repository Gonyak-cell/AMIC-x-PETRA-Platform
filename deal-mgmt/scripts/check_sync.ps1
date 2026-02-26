# Non-recursive first
$folder = 'C:\Users\서지원\OneDrive - 주식회사 페트라브릿지파트너스\AMIC의 파일 - 1. AMIC\5. 기업 인수&합병\99_Archives\10_Pjt. Green\실사자료'

Write-Output "=== Subfolders ==="
Get-ChildItem -Path $folder -Directory | ForEach-Object { Write-Output $_.Name }

Write-Output ""
Write-Output "=== First subfolder files ==="
$sub = (Get-ChildItem -Path $folder -Directory | Select-Object -First 1).FullName
if ($sub) {
    $files = Get-ChildItem -Path $sub -File -ErrorAction SilentlyContinue | Select-Object -First 5
    foreach ($f in $files) {
        $name = $f.Name
        $size = $f.Length
        try {
            $stream = [System.IO.File]::OpenRead($f.FullName)
            $byte = $stream.ReadByte()
            $stream.Close()
            Write-Output "OK   : $name ($size bytes)"
        } catch {
            $msg = $_.Exception.Message
            Write-Output "FAIL : $name - $msg"
        }
    }

    Write-Output ""
    Write-Output "=== Deep files ==="
    $deepFiles = Get-ChildItem -Path $sub -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 5
    foreach ($f in $deepFiles) {
        $name = $f.Name
        $size = $f.Length
        try {
            $stream = [System.IO.File]::OpenRead($f.FullName)
            $byte = $stream.ReadByte()
            $stream.Close()
            Write-Output "OK   : $name ($size bytes)"
        } catch {
            $msg = $_.Exception.Message
            Write-Output "FAIL : $name - $msg"
        }
    }
}
