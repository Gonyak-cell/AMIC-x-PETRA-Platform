# OneDrive 경로 탐색
Write-Output "=== OneDrive folders in user home ==="
Get-ChildItem 'C:\Users\서지원' -Directory | Where-Object { $_.Name -like '*OneDrive*' -or $_.Name -like '*페트라*' } | ForEach-Object {
    Write-Output "  $($_.FullName)"
}

$p1 = "C:\Users\서지원\OneDrive - 주식회사 페트라브릿지파트너스"
Write-Output ""
Write-Output "OneDrive root exists: $(Test-Path $p1)"

if (Test-Path $p1) {
    Write-Output ""
    Write-Output "=== OneDrive root contents ==="
    Get-ChildItem $p1 -Directory | ForEach-Object { Write-Output "  $($_.Name)" }

    $p2 = Join-Path $p1 "AMIC의 파일 - 1. AMIC"
    Write-Output ""
    Write-Output "AMIC folder exists: $(Test-Path $p2)"

    if (Test-Path $p2) {
        Write-Output "=== AMIC contents ==="
        Get-ChildItem $p2 -Directory | ForEach-Object { Write-Output "  $($_.Name)" }

        # & 포함 폴더 찾기
        $maFolder = Get-ChildItem $p2 -Directory | Where-Object { $_.Name -like '*인수*' -or $_.Name -like '*합병*' }
        if ($maFolder) {
            Write-Output ""
            Write-Output "MA folder: $($maFolder.FullName)"

            $archives = Join-Path $maFolder.FullName "99_Archives"
            Write-Output "Archives exists: $(Test-Path $archives)"

            if (Test-Path $archives) {
                Write-Output ""
                Write-Output "=== Archives contents ==="
                Get-ChildItem $archives -Directory | ForEach-Object { Write-Output "  $($_.Name)" }

                $green = Get-ChildItem $archives -Directory | Where-Object { $_.Name -like '*Green*' }
                if ($green) {
                    Write-Output ""
                    Write-Output "Pjt Green: $($green.FullName)"
                    Write-Output "=== Pjt Green contents ==="
                    Get-ChildItem $green.FullName | ForEach-Object { Write-Output "  [$($_.GetType().Name)] $($_.Name)" }

                    $silsa = Get-ChildItem $green.FullName -Directory | Where-Object { $_.Name -like '*실사*' }
                    if ($silsa) {
                        Write-Output ""
                        Write-Output "실사자료: $($silsa.FullName)"
                        $fileCount = (Get-ChildItem $silsa.FullName -Recurse -File -ErrorAction SilentlyContinue).Count
                        Write-Output "Total files (recursive): $fileCount"

                        # 읽기 테스트
                        $testFiles = Get-ChildItem $silsa.FullName -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 5
                        foreach ($f in $testFiles) {
                            try {
                                $stream = [System.IO.File]::OpenRead($f.FullName)
                                $b = $stream.ReadByte()
                                $stream.Close()
                                Write-Output "OK  : $($f.Name) ($($f.Length) bytes)"
                            } catch {
                                Write-Output "FAIL: $($f.Name) - $($_.Exception.Message)"
                            }
                        }
                    } else {
                        Write-Output "실사자료 폴더 없음"
                    }
                } else {
                    Write-Output "Pjt Green 폴더 없음"
                }
            }
        } else {
            Write-Output "MA 폴더 없음"
        }
    }
}
