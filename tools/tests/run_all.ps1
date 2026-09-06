# run_all.ps1 -- run every case under tools\tests\cases\ (or a -Filter subset), one after the
# other, and print a one-line-per-case table. Each case's own run dir + REPORT.md is where the
# detail is. Exit 1 if any case did not end as expected.
#
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_all.ps1 [-Filter 'traffic_*'] [-Label post-fix]
param(
  [string]$Filter = '*',
  [string]$Label = ''
)
$ErrorActionPreference = 'Continue'
$cases = Get-ChildItem (Join-Path $PSScriptRoot 'cases') -Filter "$Filter.ps1" | Sort-Object Name
if ($cases.Count -eq 0) { Write-Host "[all] no cases match '$Filter'"; exit 2 }
$rows = @()
$bad = 0
foreach ($c in $cases) {
  $name = $c.BaseName
  Write-Host ""
  Write-Host ("[all] ================ {0} ================" -f $name)
  & (Join-Path $PSScriptRoot 'run_case.ps1') -Case $c.FullName -Label $Label
  $rc = $LASTEXITCODE
  $latest = Join-Path $PSScriptRoot ("..\..\scratch\bugtest\runs\{0}\latest.json" -f $name)
  $v = '?'; $ph = '?'; $as = '?'
  if (Test-Path $latest) { $j = Get-Content $latest -Raw | ConvertFrom-Json; $v = $j.verdict; $ph = $j.phase; $as = $j.asserts }
  if ($rc -ne 0) { $bad++ }
  $rows += ("{0,-40} {1,-5} phase={2,-9} asserts={3,-5} rc={4}" -f $name, $v, $ph, $as, $rc)
}
Write-Host ""
Write-Host "[all] ---- summary ----"
$rows | ForEach-Object { Write-Host "  $_" }
Write-Host ("[all] {0} case(s), {1} not as expected" -f $cases.Count, $bad)
exit $(if ($bad -gt 0) { 1 } else { 0 })
