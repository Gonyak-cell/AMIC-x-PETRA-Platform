$base = 'C:\Users\diedi\OneDrive\Documents\Coding\AMIC x PETRA Platform\amic-platform\src'

# Move pages (except LoginPage)
$pagesDir = Join-Path $base 'pages'
$fddPagesDir = Join-Path (Join-Path (Join-Path $base 'modules') 'fdd') 'pages'
$pages = Get-ChildItem $pagesDir -Filter '*.tsx' | Where-Object { $_.Name -ne 'LoginPage.tsx' }
foreach ($p in $pages) {
    $dst = Join-Path $fddPagesDir $p.Name
    Move-Item $p.FullName $dst -Force
}
Write-Host "Moved $($pages.Count) pages"

# Move FDD hooks
$hooksDir = Join-Path $base 'hooks'
$fddHooksDir = Join-Path (Join-Path (Join-Path $base 'modules') 'fdd') 'hooks'
foreach ($h in @('useReportVersions.ts', 'useVdr.ts')) {
    $src = Join-Path $hooksDir $h
    if (Test-Path $src) {
        $dst = Join-Path $fddHooksDir $h
        Move-Item $src $dst -Force
        Write-Host "Moved hook: $h"
    }
}

# Move FDD types (keep auth.ts)
$typesDir = Join-Path $base 'types'
$fddTypesDir = Join-Path (Join-Path (Join-Path $base 'modules') 'fdd') 'types'
$types = Get-ChildItem $typesDir -Filter '*.ts' | Where-Object { $_.Name -ne 'auth.ts' }
foreach ($t in $types) {
    $dst = Join-Path $fddTypesDir $t.Name
    Move-Item $t.FullName $dst -Force
}
Write-Host "Moved $($types.Count) types"

# Move FDD-specific components
foreach ($cd in @('deal', 'report', 'vdr')) {
    $srcDir = Join-Path (Join-Path $base 'components') $cd
    $dstDir = Join-Path (Join-Path (Join-Path (Join-Path $base 'modules') 'fdd') 'components') $cd
    if (Test-Path $srcDir) {
        Get-ChildItem $srcDir -File | ForEach-Object {
            $dst = Join-Path $dstDir $_.Name
            Move-Item $_.FullName $dst -Force
        }
        Remove-Item $srcDir -Force -Recurse -ErrorAction SilentlyContinue
        Write-Host "Moved components/$cd"
    }
}

Write-Host 'DONE'
