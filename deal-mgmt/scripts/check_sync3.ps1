# Step 1: 폴더 존재 확인
$folder = 'C:\Users\서지원\OneDrive - 주식회사 페트라브릿지파트너스\AMIC의 파일 - 1. AMIC\5. 기업 인수&합병\99_Archives\10_Pjt. Green\실사자료'

Write-Output "=== Step 1: Folder exists? ==="
Write-Output (Test-Path $folder)

Write-Output ""
Write-Output "=== Step 2: Top-level items ==="
try {
    $items = Get-ChildItem -Path $folder -ErrorAction Stop
    Write-Output "Count: $($items.Count)"
    foreach ($i in $items) {
        Write-Output "  [$($i.GetType().Name)] $($i.Name)"
    }
} catch {
    Write-Output "ERROR: $($_.Exception.Message)"
}

Write-Output ""
Write-Output "=== Step 3: dir command ==="
cmd /c "dir `"$folder`" /b" 2>&1 | Select-Object -First 10 | ForEach-Object { Write-Output $_ }

Write-Output ""
Write-Output "=== Step 4: First subfolder files ==="
$sub = Get-ChildItem -Path $folder -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
if ($sub) {
    Write-Output "Subfolder: $($sub.Name)"
    $subFiles = Get-ChildItem -Path $sub.FullName -File -ErrorAction SilentlyContinue | Select-Object -First 5
    Write-Output "Files: $($subFiles.Count)"
    foreach ($f in $subFiles) {
        Write-Output "  $($f.Name) ($($f.Length) bytes)"
    }
} else {
    Write-Output "No subfolders found"
}
