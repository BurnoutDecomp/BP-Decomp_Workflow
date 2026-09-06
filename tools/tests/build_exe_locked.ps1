# build_exe_locked.ps1 -- rebuild build\game\Burnout_PC.exe, ONE BUILD AT A TIME, never while
# a harness run is live.
#
#   powershell -ExecutionPolicy Bypass -File tools\tests\build_exe_locked.ps1 [-Label <lane>]
#
# Why a wrapper: the exe is shared by every lane on this box. The link needs the exe unlocked
# (a running game locks it), and a harness run needs the exe it started with to stay put. Both
# are the same rule flow_run already enforces for runs -- so this script takes THE SAME box lock
# (_box_lock.ps1) for the duration of the build. A build waits for a run to finish; a run waits
# for a build to finish. Nobody's measurement is taken against a half-linked exe.
#
# The build itself is the repo's own incremental driver (tools\build\build.py exe, Python 3.11+
# -- 3.10 is rejected by tomllib). Measured 2026-09-06: 655 changed TUs in 57 s, jobs=9.
#
# ⛔ It does NOT kill a running game. If Burnout_PC.exe is locked (someone is playing, or a
#   harness escaped the lock) build.py refuses at the link and this script exits 1 saying so.
# ⛔ It does NOT fix anyone's compile errors. A red build prints the first errors and the log
#   path; if the failing file is not yours, do not edit it -- report it and retry later. Lanes are
#   file-disjoint on purpose; run tools\work\selfcheck.py on your own TUs BEFORE you come here.
#
# Exit code = build.py's (0 = linked, exe + .cgsmap refreshed).
param(
  [string]$Label = "",
  [int]$TimeoutSec = 7200,
  [string]$LogDir = ""
)
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
. (Join-Path $root 'tools\diagnostics\_box_lock.ps1')

$py = 'C:\Users\Niaz\AppData\Local\Programs\Python\Python311\python.exe'
if (-not (Test-Path $py)) {
  $py = (Get-Command python -ErrorAction SilentlyContinue).Source
  if (-not $py) { Write-Host "[build] FAIL: no Python 3.11+ found"; exit 1 }
}
if ($LogDir -eq "") { $LogDir = Join-Path $root 'scratch\bugtest\build' }
New-Item -ItemType Directory -Force $LogDir | Out-Null
$tag = if ($Label) { $Label -replace '[^A-Za-z0-9_-]', '_' } else { 'build' }
$log = Join-Path $LogDir ("{0}_{1}.log" -f (Get-Date).ToString('yyyyMMdd_HHmmss'), $tag)

Write-Host ("[build] waiting for the box lock{0} ..." -f $(if ($Label) { " ($Label)" } else { "" }))
Enter-BoxLock -TimeoutSec $TimeoutSec -Label ("build" + $(if ($Label) { ":$Label" } else { "" }))
Write-Host "[build] got the box. Building (log -> $log)"

# ⭐⭐ THE EXE STAGING LOCK (2026-09-06, parallel slots -- lane harness2).
#   WHICH LOCKS A BUILD TAKES, AND WHY IT IS NOT ALL OF THEM.
#   The box lock above is now PER SLOT (`Local\BurnoutPC_FlowRun[_<n>]`), and this script keeps
#   taking only SLOT 0's -- deliberately. A slot run executes its OWN COPY of the exe out of
#   build\game_slots\<n>\, so a link into build\game\Burnout_PC.exe can neither be blocked by it
#   (the copy holds the lock, not the original) nor disturb it (its bytes are not being written).
#   Taking every slot lock would only make a build wait for runs it cannot affect.
#   ⛔ WHAT DOES NEED SERIALISING is the moment a slot COPIES that exe in: a copy taken mid-link
#   is a slot booting a half-written binary, which fails in ways that look nothing like a build
#   failure. `slots.ps1` takes this same narrow mutex around its copy, so the two cannot overlap.
#   Order is box-then-stage in both scripts, so there is no cycle.
#   ⚠️ CONSEQUENCE, STATED PLAINLY: a slot run that started BEFORE a build keeps running the exe
#   it started with. That is correct (a measurement must not change under itself) and it is
#   attributable -- the slot carries the matching Burnout_PC.exe.provenance.json, which flow_run
#   prints as `[flow] exe <sha> b5=<head>` on every run.
$lStage = New-Object System.Threading.Mutex($false, "Local\BurnoutPC_ExeStage")
$lStageGot = $false
try { $lStageGot = $lStage.WaitOne([TimeSpan]::FromSeconds($TimeoutSec)) }
catch [System.Threading.AbandonedMutexException] { $lStageGot = $true }
if (-not $lStageGot) {
  Write-Host "[build] FAIL: the exe staging lock stayed busy for $TimeoutSec s (a slot is copying the exe in)."
  exit 1
}

$t0 = Get-Date
Push-Location $root
try {
  & $py (Join-Path $root 'tools\build\build.py') exe *> $log
  $rc = $LASTEXITCODE
} finally { Pop-Location; $lStage.ReleaseMutex(); $lStage.Close() }
$secs = ((Get-Date) - $t0).TotalSeconds

$lines = Get-Content $log
$summary = $lines | Where-Object { $_ -match '^compile: |^link|errors: |LNK1104|unresolved external|error C\d+|fatal error' } | Select-Object -First 25
foreach ($s in $summary) { Write-Host "  | $s" }
if ($rc -eq 0) {
  $exe = Join-Path $root 'build\game\Burnout_PC.exe'
  Write-Host ("[build] OK in {0:f0}s -> {1} ({2:N0} bytes, {3})" -f $secs, $exe, (Get-Item $exe).Length, (Get-Item $exe).LastWriteTime)
} else {
  Write-Host ("[build] *** FAILED (exit {0}) after {1:f0}s -- full log: {2}" -f $rc, $secs, $log)
  $errs = $lines | Where-Object { $_ -match 'error C\d+|LNK\d+|fatal error' } | Select-Object -First 15
  foreach ($e in $errs) { Write-Host "  ! $e" }
}
exit $rc
