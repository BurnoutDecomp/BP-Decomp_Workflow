# PROOF_run.ps1 -- run a harness case with the shared box save restored around it.
#
#   powershell -ExecutionPolicy Bypass -File tools\tests\tools\PROOF_run.ps1 -Case <name> [-Repeat n] [-Label txt]
#
# Why: build\game\Memcard\Profile.sav is shared by every lane on the box, and a win/lose run banks
# results into it. The wave rule is "restore the pinned save before EVERY run and after it". Done
# outside the box lock, that copy can land in the middle of ANOTHER lane's run (it then boots a save
# it did not ask for). So each repetition here is its own child process that:
#   1. takes the box lock (the same mutex run_case/flow_run take; a Mutex is re-entrant for its
#      owning thread, so run_case's own Enter-BoxLock on this thread returns at once),
#   2. copies the pinned save over the box save,
#   3. runs run_case.ps1 in-process,
#   4. copies the pinned save back,
#   5. exits, which releases the lock, so other lanes can interleave between repetitions.
# Cases that set ProfileFixture park/restore the box save themselves; the restore here is harmless.
#
# Output: one "[PROOF] <case> rep i/n: PASS|FAIL exit=<n> run=<dir>" line per repetition.
param(
  [Parameter(Mandatory=$true)][string]$Case,
  [int]$Repeat = 1,
  [string]$Label = "",
  [switch]$ExpectFail,
  [string]$Pinned = "",
  [switch]$Child
)
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
if ($Pinned -eq "") { $Pinned = Join-Path $root 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700' }
$boxSave = Join-Path $root 'build\game\Memcard\Profile.sav'

if (-not $Child) {
  for ($i = 1; $i -le $Repeat; $i++) {
    $lArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $PSCommandPath, '-Case', $Case, '-Child', '-Pinned', $Pinned)
    if ($Label) { $lArgs += @('-Label', $Label) }
    if ($ExpectFail) { $lArgs += '-ExpectFail' }
    & powershell @lArgs
    $lExit = $LASTEXITCODE
    $lName = [IO.Path]::GetFileNameWithoutExtension($Case)
    $lLatest = Join-Path $root ("scratch\bugtest\runs\" + $lName + "\latest.json")
    $lRunDir = '?'; $lVerdict = '?'
    if (Test-Path $lLatest) {
      try { $lJ = Get-Content $lLatest -Raw | ConvertFrom-Json; $lRunDir = $lJ.run_dir; $lVerdict = $lJ.verdict } catch { }
    }
    Write-Host ("[PROOF] {0} rep {1}/{2}: {3} exit={4} run={5}" -f $lName, $i, $Repeat, $lVerdict, $lExit, $lRunDir)
  }
  exit 0
}

. (Join-Path $root 'tools\diagnostics\_box_lock.ps1')
Enter-BoxLock -TimeoutSec 7200 -Label "PROOF_run"
if (-not (Test-Path $Pinned)) { Write-Host "[PROOF] FAIL: pinned save $Pinned missing"; exit 2 }
Copy-Item $Pinned $boxSave -Force
Write-Host "[PROOF] restored the pinned save before the run"
$lCaseArgs = @{ Case = $Case }
if ($Label) { $lCaseArgs.Label = $Label }
if ($ExpectFail) { $lCaseArgs.ExpectFail = $true }
try {
  & (Join-Path $root 'tools\tests\run_case.ps1') @lCaseArgs
  $lExit = $LASTEXITCODE
} finally {
  Copy-Item $Pinned $boxSave -Force
  Write-Host "[PROOF] restored the pinned save after the run"
}
exit $lExit
