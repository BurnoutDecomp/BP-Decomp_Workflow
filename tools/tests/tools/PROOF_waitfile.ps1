# PROOF_waitfile.ps1 -- wait (polling, 10 s) until a text file gains a line matching -Pattern
# (counted from the line count at start), up to -MaxSec. Prints the new lines. Touches nothing.
param([Parameter(Mandatory=$true)][string]$File, [string]$Pattern = '.', [int]$MaxSec = 540)
$t0 = Get-Date
$n0 = if (Test-Path $File) { @(Get-Content $File).Count } else { 0 }
while ($true) {
  Start-Sleep -Seconds 10
  $lLines = if (Test-Path $File) { @(Get-Content $File) } else { @() }
  if ($lLines.Count -gt $n0) {
    $lNew = $lLines[$n0..($lLines.Count - 1)]
    if (@($lNew | Where-Object { $_ -match $Pattern }).Count -gt 0) { $lNew | ForEach-Object { Write-Host $_ }; exit 0 }
  }
  if (((Get-Date) - $t0).TotalSeconds -ge $MaxSec) {
    if ($lLines.Count -gt $n0) { $lLines[$n0..($lLines.Count - 1)] | ForEach-Object { Write-Host $_ } }
    Write-Host ("(no line matching /{0}/ after {1}s)" -f $Pattern, $MaxSec); exit 1
  }
}
