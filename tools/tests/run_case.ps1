# run_case.ps1 -- run ONE bug-test case: boot the game through flow_run.ps1 with the case's
# scenario, then evaluate the case's checks against the evidence that run produced.
#
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case <name|path>
#   ... -ExpectFail          # RED mode: exit 0 only if the checks FAIL (the bug reproduces)
#   ... -NoRun -RunDir <dir> # re-evaluate the checks against a run already on disk (no boot)
#
# A CASE is a .ps1 under tools\tests\cases\ that RETURNS a hashtable -- see README.md and
# cases\baseline_boot_drive.ps1. Everything the run produced lands under ONE directory:
#
#   scratch\bugtest\runs\<case>\<timestamp>\
#       flow\BrnGame.log        the game's log for THIS run (copied by flow_run at the end)
#       flow\marks.txt          flow_run's summary: cues, phase, asserts, DIAGENV, DRIVE ...
#       frames\bb_*.bmp         only when the case sets Frames = $true
#       flow_run.console.log    everything flow_run printed
#       result.json             machine-readable verdict (+ exe/commit provenance)
#       REPORT.md               the same, for humans
#   scratch\bugtest\runs\<case>\latest.json   -> a pointer to the newest run's result
#
# ⛔ ONE GAME AT A TIME ON THIS BOX. flow_run takes the box lock (_box_lock.ps1); with many
# lanes queued the wait can be long, so this runner passes -LockTimeoutSec 7200 by default.
# A wait is announced by flow_run ("[box] waiting for the box") -- it is not a hang.
#
# ⭐ RED -> GREEN is the discipline, not a feature of this script. A case is written FIRST, run
# against the current build with -ExpectFail, and must FAIL there (RED = the bug reproduces
# and the checks measure it). Only then is the fix made, and the same case must PASS (GREEN).
# A case that passes before the fix measures nothing; a case nobody ran RED proves nothing.
#
# Exit code: 0 = verdict matches expectation (PASS, or FAIL under -ExpectFail); 1 otherwise;
# 2 = the runner itself could not run the case (bad case file, flow_run refused, ...).
param(
  [Parameter(Mandatory=$true)][string]$Case,
  [string]$RunDir       = "",     # default scratch\bugtest\runs\<case>\<timestamp>
  [string]$RunsRoot     = "",     # default <repo>\scratch\bugtest\runs
  [switch]$ExpectFail,            # RED mode
  [switch]$NoRun,                 # evaluate an existing -RunDir only
  [int]$LockTimeoutSec  = 7200,
  [string]$Label        = "",     # free text recorded in result.json (e.g. "pre-fix", "post-fix")
  [int]$Slot            = 0       # ⭐ PARALLEL SLOTS (2026-09-06, lane harness2). 0 == build\game,
                                  #   one game on the box, byte for byte what it has always been.
                                  #   n > 0 runs build\game_slots\<n>\Burnout_PC.exe -- a COPY of
                                  #   the same build, with its own log, its own harness input
                                  #   channels, its own box lock and its own Memcard_<n> profile --
                                  #   so k cases can run at once (run_all.ps1 -Parallel k). The
                                  #   scenario, the checks and the report are identical; only the
                                  #   instance moves.
                                  #   ⚠️ A parallel run SHARES THE GPU AND CPU, so its frame rate is
                                  #   lower than a solo run's. Every check in tools\tests\cases is a
                                  #   log line or a pixel, neither of which moves with contention --
                                  #   but a case whose check is ever a frame-rate or wall-clock
                                  #   number must be scored on a slot of its own.
)
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
. (Join-Path $PSScriptRoot '_checks.ps1')

# --- resolve + load the case -------------------------------------------------------------
$casePath = $Case
if (-not (Test-Path $casePath)) { $casePath = Join-Path $PSScriptRoot ("cases\" + $Case + ".ps1") }
if (-not (Test-Path $casePath)) { Write-Host "[case] FAIL: no case '$Case' (tried $casePath)"; exit 2 }
$casePath = (Resolve-Path $casePath).Path
$lCase = & $casePath
if ($lCase -isnot [hashtable]) { Write-Host "[case] FAIL: $casePath must RETURN a hashtable (see README.md)"; exit 2 }
if (-not $lCase.Name) { $lCase.Name = [IO.Path]::GetFileNameWithoutExtension($casePath) }
if (-not $lCase.Checks -or $lCase.Checks.Count -eq 0) { Write-Host "[case] FAIL: case '$($lCase.Name)' has no Checks"; exit 2 }
$lRun = if ($lCase.Run) { $lCase.Run } else { @{} }

if ($RunsRoot -eq "") { $RunsRoot = Join-Path $root "scratch\bugtest\runs" }
$caseRoot = Join-Path $RunsRoot $lCase.Name
if ($NoRun) {
  if ($RunDir -eq "") { Write-Host "[case] FAIL: -NoRun needs -RunDir <existing run>"; exit 2 }
  if (-not (Test-Path $RunDir)) { Write-Host "[case] FAIL: -RunDir '$RunDir' does not exist"; exit 2 }
} elseif ($RunDir -eq "") {
  $RunDir = Join-Path $caseRoot (Get-Date).ToString('yyyyMMdd_HHmmss')
}
New-Item -ItemType Directory -Force $RunDir | Out-Null
$RunDir = (Resolve-Path $RunDir).Path
$flowOut  = Join-Path $RunDir 'flow'
$frameDir = Join-Path $RunDir 'frames'
$consoleLog = Join-Path $RunDir 'flow_run.console.log'

Write-Host ("[case] {0}  ({1})" -f $lCase.Name, $casePath)
if ($lCase.Bug)  { Write-Host ("[case] bug:  {0}" -f $lCase.Bug) }
Write-Host ("[case] run dir: {0}" -f $RunDir)

# --- provenance: which exe, which commits ----------------------------------------------------
# The exe THIS run will execute -- a slot runs its own copy, and a provenance stamp naming the
# wrong binary would be worse than none (see flow_run's EXE PROVENANCE banner).
$exeDir = if ($Slot -gt 0) { Join-Path $root ('build\game_slots\' + $Slot) } else { Join-Path $root 'build\game' }
$exe = Join-Path $exeDir 'Burnout_PC.exe'
$prov = @{
  exe_mtime   = $(if (Test-Path $exe) { (Get-Item $exe).LastWriteTime.ToString('o') } else { 'MISSING' })
  exe_size    = $(if (Test-Path $exe) { (Get-Item $exe).Length } else { 0 })
  b5_head     = (git -C (Join-Path $root 'b5-decomp') rev-parse --short HEAD 2>$null)
  parent_head = (git -C $root rev-parse --short HEAD 2>$null)
  b5_dirty    = ((git -C (Join-Path $root 'b5-decomp') status --porcelain 2>$null | Where-Object { $_ -notmatch '^\?\?' } | Measure-Object).Count)
}

# --- run flow_run ----------------------------------------------------------------------------
$flowExit = $null
$profileAside = $null
# FreshProfile parks THIS SLOT's save. Slot n's profile is build\game\Memcard_<n>\Profile.sav
# (the game suffixes the directory from BRN_HARNESS_SLOT), so parking slot 0's would leave slot n
# on the returning path and quietly measure the wrong boot.
$profile = if ($Slot -gt 0) { Join-Path $root ('build\game\Memcard_' + $Slot + '\Profile.sav') }
           else             { Join-Path $root 'build\game\Memcard\Profile.sav' }
if (-not $NoRun) {
  # A SLOT's exe is staged by flow_run itself (under the lock, after its kill sweep), so only
  # slot 0 must already have one at this point.
  if ($Slot -le 0 -and -not (Test-Path $exe)) { Write-Host "[case] FAIL: no exe at $exe -- build first (tools\tests\build_exe_locked.ps1)"; exit 2 }
  $lArgs = @{}
  foreach ($k in $lRun.Keys) { $lArgs[$k] = $lRun[$k] }
  $lArgs['OutDir'] = $flowOut
  $lArgs['LockTimeoutSec'] = $LockTimeoutSec
  if ($Slot -gt 0) { $lArgs['Slot'] = $Slot }
  if ($lCase.Frames) { $lArgs['Frames'] = $true; $lArgs['FrameDir'] = $frameDir }
  if ($lCase.DiagEnv) { $lArgs['DiagEnv'] = "$($lCase.DiagEnv)" }
  # ⭐ FreshProfile: the game takes a different boot path when Memcard\Profile.sav exists
  #   (returning player). A case that needs the first-boot path (the autosave prompt, the new-
  #   profile junkyard intro) sets FreshProfile = $true; the save is parked beside the run and put
  #   back afterwards, whatever happens.
  if ($lCase.FreshProfile -and (Test-Path $profile)) {
    $profileAside = Join-Path $RunDir 'Profile.sav.aside'
    Move-Item $profile $profileAside -Force
    Write-Host "[case] FreshProfile: parked $profile -> $profileAside"
  }
  # ⭐ Setup: A STIMULUS THAT HAS TO RUN *ALONGSIDE* THE BOOT (2026-09-06, lane quiet).
  #   Every Check runs after flow_run has returned, which is the right shape for a check and the
  #   wrong shape for a stimulus that must happen WHILE the game is up -- e.g. holding real keys
  #   down on the desktop from another window, which is the only honest way to ask "does the game
  #   read input it was not given?". A case that needed that had to be launched by hand in two
  #   commands, so it could not be part of a sweep at all, and in a sweep it silently measured
  #   nothing instead of failing.
  #   `Setup` is an optional scriptblock on the case. It is called with one context hashtable
  #   BEFORE flow_run starts and must RETURN either nothing or a System.Diagnostics.Process,
  #   which is killed here if it outlives the run -- so a stimulus can never leak past its case.
  #     Root / RunDir / Slot / Case  -- the obvious ones
  #     GameLog                      -- THIS SLOT's live BrnGame.log (slot n has its own; a
  #                                     helper that polls build\game\BrnGame.log would watch the
  #                                     wrong instance in a -Parallel sweep)
  #   A case with no Setup key behaves exactly as before.
  $lSetupProc = $null
  if ($lCase.Setup) {
    $lSetupCtx = @{ Root = $root; RunDir = $RunDir; Slot = $Slot; Case = $lCase
                    GameLog = (Join-Path $exeDir 'BrnGame.log') }
    Write-Host "[case] Setup: running the case's concurrent stimulus"
    $lSetupProc = & $lCase.Setup $lSetupCtx
    if ($lSetupProc -is [System.Diagnostics.Process]) {
      Write-Host ("[case] Setup: started pid {0}; it will be killed if it outlives the run" -f $lSetupProc.Id)
    } else { $lSetupProc = $null }
  }
  $argText = ($lArgs.GetEnumerator() | ForEach-Object { if ($_.Value -is [bool] -or $_.Value -is [switch]) { "-$($_.Key)" } else { "-$($_.Key) '$($_.Value)'" } }) -join ' '
  Write-Host "[case] flow_run.ps1 $argText"
  $t0 = Get-Date
  try {
    & (Join-Path $root 'tools\diagnostics\flow_run.ps1') @lArgs *>&1 | Tee-Object -FilePath $consoleLog | ForEach-Object { Write-Host "  | $_" }
    $flowExit = $LASTEXITCODE
  } finally {
    if ($lSetupProc -and -not $lSetupProc.HasExited) {
      Write-Host ("[case] Setup: pid {0} outlived the run -- stopping it" -f $lSetupProc.Id)
      try { $lSetupProc.Kill() } catch { }
    }
    if ($profileAside -and (Test-Path $profileAside)) {
      if (Test-Path $profile) { Remove-Item $profile -Force }
      Move-Item $profileAside $profile -Force
      Write-Host "[case] FreshProfile: restored $profile"
    }
  }
  Write-Host ("[case] flow_run exit={0} after {1:f0}s" -f $flowExit, ((Get-Date) - $t0).TotalSeconds)
}

# --- gather evidence ------------------------------------------------------------------------
$logPath = Join-Path $flowOut 'BrnGame.log'
$marksPath = Join-Path $flowOut 'marks.txt'
if (-not (Test-Path $logPath)) { Write-Host "[case] FAIL: no $logPath -- flow_run did not produce a run (see $consoleLog)"; exit 2 }
$logLines = [IO.File]::ReadAllLines($logPath)
$lM = Parse-Marks $marksPath

# The cue-name -> regex table, read from flow_run.ps1 itself so LogValue After='<cue>' cannot drift.
$cueRegex = @{}
foreach ($l in (Get-Content (Join-Path $root 'tools\diagnostics\flow_run.ps1'))) {
  if ($l -match "^\s*@\('([^']+)',\s*'((?:[^']|'')*)'") { $cueRegex[$Matches[1]] = $Matches[2] -replace "''", "'" }
}

$ctx = @{
  Log = $logPath; LogLines = $logLines; Marks = $lM.Marks; MarksText = $lM.Text; Phase = $lM.Phase
  Asserts = $lM.Asserts; FrameDir = $frameDir; RunDir = $RunDir; Case = $lCase; CueRegex = $cueRegex
}

# --- evaluate ----------------------------------------------------------------------------------
$results = @()
$allPass = $true
Write-Host ""
Write-Host ("[case] ---- checks ({0}) ----" -f $lCase.Checks.Count)
$i = 0
foreach ($chk in $lCase.Checks) {
  $i++
  $r = Invoke-Check $chk $ctx
  $name = if ($chk.Name) { "$($chk.Name)" } else { "check $i ($($chk.Kind))" }
  $results += @{ name = $name; kind = "$($chk.Kind)"; pass = [bool]$r.Pass; detail = "$($r.Detail)" }
  if (-not $r.Pass) { $allPass = $false }
  Write-Host ("  [{0}] {1,-44} {2}" -f $(if ($r.Pass) { 'PASS' } else { 'FAIL' }), $name, $r.Detail)
}

$verdict = if ($allPass) { 'PASS' } else { 'FAIL' }
$expected = if ($ExpectFail) { 'FAIL' } else { 'PASS' }
$asExpected = ($verdict -eq $expected)
Write-Host ""
if ($ExpectFail) {
  if ($asExpected) { Write-Host "[case] RED confirmed: '$($lCase.Name)' FAILS on this build -- the case reproduces the bug." }
  else             { Write-Host "[case] *** NOT RED: '$($lCase.Name)' PASSES on this build -- the case does NOT reproduce the bug. ***" }
} else {
  if ($asExpected) { Write-Host "[case] GREEN: '$($lCase.Name)' PASSES." }
  else             { Write-Host "[case] *** FAIL: '$($lCase.Name)' ***" }
}
Write-Host ("[case] marks: phase={0} asserts={1}  flow_exit={2}" -f $lM.Phase, $lM.Asserts, $flowExit)

# --- record ------------------------------------------------------------------------------------
$result = @{
  case = $lCase.Name; case_path = $casePath; bug = "$($lCase.Bug)"; area = "$($lCase.Area)"
  label = $Label; when = (Get-Date).ToString('o'); run_dir = $RunDir; slot = $Slot
  verdict = $verdict; expected = $expected; as_expected = $asExpected
  phase = $lM.Phase; asserts = $lM.Asserts; flow_exit = $flowExit
  checks = $results; provenance = $prov
}
$result | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $RunDir 'result.json') -Encoding UTF8
New-Item -ItemType Directory -Force $caseRoot | Out-Null
$result | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $caseRoot 'latest.json') -Encoding UTF8

$md = @()
$md += "# $($lCase.Name) -- $verdict" + $(if ($Label) { " ($Label)" } else { "" })
$md += ""
if ($lCase.Bug) { $md += "Bug: $($lCase.Bug)"; $md += "" }
$md += "Run: ``$RunDir``  exe $($prov.exe_mtime)  b5 $($prov.b5_head)  parent $($prov.parent_head)" + $(if ($prov.b5_dirty -gt 0) { "  (b5 tree has $($prov.b5_dirty) uncommitted tracked change(s))" } else { "" })
$md += "Phase: $($lM.Phase)  asserts=$($lM.Asserts)  flow_exit=$flowExit  expected=$expected  as_expected=$asExpected"
$md += ""
$md += "| verdict | check | detail |"
$md += "|---|---|---|"
foreach ($r in $results) { $md += ("| {0} | {1} | {2} |" -f $(if ($r.pass) { 'PASS' } else { '**FAIL**' }), $r.name, ($r.detail -replace '\|', '\|')) }
$md += ""
$md += "marks.txt:"
$md += '```'
$md += $lM.Text
$md += '```'
$md -join "`n" | Set-Content (Join-Path $RunDir 'REPORT.md') -Encoding UTF8
Write-Host "[case] report -> $(Join-Path $RunDir 'REPORT.md')"

if ($asExpected) { exit 0 } else { exit 1 }
