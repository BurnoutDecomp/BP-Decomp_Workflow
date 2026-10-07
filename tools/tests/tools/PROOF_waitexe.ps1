# PROOF_waitexe.ps1 -- wait (polling, 10 s) until build\game\Burnout_PC.exe is newer than it was at
# start, or CLAIMS.md grows, up to -MaxSec. Prints what changed. Touches nothing.
param([int]$MaxSec = 540, [string]$Claims = "")
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$exe = Join-Path $root 'build\game\Burnout_PC.exe'
if ($Claims -eq "") { $Claims = Join-Path $root 'scratch\gameplay_wave4\CLAIMS.md' }
$t0 = Get-Date
$lExe0 = if (Test-Path $exe) { (Get-Item $exe).LastWriteTime } else { [datetime]::MinValue }
$lClaims0 = if (Test-Path $Claims) { (Get-Item $Claims).Length } else { 0 }
while ($true) {
  Start-Sleep -Seconds 10
  $lExe = if (Test-Path $exe) { (Get-Item $exe).LastWriteTime } else { [datetime]::MinValue }
  $lClaims = if (Test-Path $Claims) { (Get-Item $Claims).Length } else { 0 }
  if ($lExe -ne $lExe0) { Write-Host ("EXE changed: {0:HH:mm:ss} -> {1:HH:mm:ss}" -f $lExe0, $lExe); exit 0 }
  if ($lClaims -ne $lClaims0) { Write-Host ("CLAIMS grew: {0} -> {1} bytes" -f $lClaims0, $lClaims); exit 0 }
  if (((Get-Date) - $t0).TotalSeconds -ge $MaxSec) { Write-Host ("no change after {0}s" -f $MaxSec); exit 1 }
}
