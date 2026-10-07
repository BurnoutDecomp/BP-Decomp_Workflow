# PROOF_batch.ps1 -- run several cases one after another through PROOF_run.ps1 (box lock + pinned
# save restore around each run), appending one line per finished run to a progress file.
#
#   powershell -ExecutionPolicy Bypass -File tools\tests\tools\PROOF_batch.ps1 -Cases "a,b,b,c" [-Label x]
#     [-Progress <file>]   default scratch\gameplay_wave4\PROOF\batch_progress.txt
#
# A case named twice runs twice. The progress file gets "<time> <case> <verdict> exit=<n> run=<dir>"
# per run and "BATCH DONE" at the end, so a caller can poll it (PROOF_waitfile.ps1).
param(
  [Parameter(Mandatory=$true)][string]$Cases,
  [string]$Label = "",
  [string]$Progress = ""
)
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
if ($Progress -eq "") { $Progress = Join-Path $root 'scratch\gameplay_wave4\PROOF\batch_progress.txt' }
New-Item -ItemType Directory -Force (Split-Path $Progress -Parent) | Out-Null
("{0} BATCH START {1}" -f (Get-Date).ToString('HH:mm:ss'), $Cases) | Add-Content -Path $Progress -Encoding ASCII
foreach ($lsCase in ($Cases -split ',')) {
  $lsCase = $lsCase.Trim()
  if (-not $lsCase) { continue }
  $lArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PSScriptRoot 'PROOF_run.ps1'), '-Case', $lsCase)
  if ($Label) { $lArgs += @('-Label', $Label) }
  $lOut = & powershell @lArgs 2>&1
  $lLine = $lOut | Where-Object { "$_" -match '^\[PROOF\] .* rep \d+/\d+:' } | Select-Object -Last 1
  ("{0} {1}" -f (Get-Date).ToString('HH:mm:ss'), $(if ($lLine) { "$lLine" } else { "[PROOF] ${lsCase}: no result line" })) | Add-Content -Path $Progress -Encoding ASCII
}
("{0} BATCH DONE" -f (Get-Date).ToString('HH:mm:ss')) | Add-Content -Path $Progress -Encoding ASCII
