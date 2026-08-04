# flow_run.ps1 -- boot the game, drive the Junkyard flow, mark the FLOW STATES, gate the frames.
#
# ⛔⛔ WHY THIS FILE IS IN THE REPO (task #139).
#   For weeks every wave brief said "use scratchpad\dh_run.ps1".  It was never in the repo:
#   it lived only in one session's scratchpad, undurable and unreviewable, and the gate that
#   consumes its marks documented a producer (`cs_run.ps1`) that no checkout had.  A harness
#   that cannot be run from a clean checkout is not a harness.  This file is dh_run.ps1 and
#   cs_run.ps1 merged, hardened, and made the single supported entry point.
#
# ⭐ IMMUNE TO THE PREVIOUS-LOG RACE, BY CONSTRUCTION -- NOT BY ORDERING.
#   The classic failure: a runner deletes BrnGame.log at some point around launch, a poller
#   reads it before this run has written anything, matches the PREVIOUS run's 'Entering Car
#   Select', marks bb_000000.bmp, and the car-select gate then scores the TITLE SCREEN and
#   passes.  A PASS measuring entirely the wrong frame.
#   Deleting the log before Start-Process only avoids that by ordering, and ordering is
#   exactly what drifts.  So this script ALSO refuses to parse a single byte until the log
#   file's LastWriteTime is at or after the launch instant (Wait-ForOwnLog below).  Marks can
#   only ever come from THIS process's own output.
#
# ⭐ SAMPLES BY FLOW STATE, NOT FRAME INDEX.  Frame counts shift with load timing, so every
#   mark is anchored to a log transition and records the newest dumped frame AT THAT INSTANT.
#   ⚠️ The cues below are the ones the game ACTUALLY prints -- verified against real logs on
#   2026-08-04.  In particular there is NO '[carselect] meState -> N' line and NO
#   'phase=DRIVING' line in BrnGame.log; `phase` is this script's own variable, and `meState`
#   only ever appears as a substring of "GameStateModule".  Do not add cues without grepping
#   a real log for them first.
#
# ⛔ NEVER capture a golden through BRN_WORLD_CAMFREE.  That flag is how a day-long
#   world-render regression hid: it was added by the very commit that broke the world, so
#   every shot taken through it looked fine while the default run was broken.  This script
#   CLEARS it (and the other camera/trace overrides) on every run and says so.
#
# ⚠️ Do NOT model this on is_run.ps1 / ut_shot.ps1: they latch $stopAccepting on the flyby cue
#   and never release it, so the flow parks at car select for ever.  The accept pump here
#   RESUMES once car select is up (that is the whole point of the FLYBY -> CARSELECT phase).
#
# Usage:
#   flow_run.ps1 -Frames -Gates                     # boot, dump frames, run BOTH gates
#   flow_run.ps1 -Frames -HoldCarSelect             # park at car select for a clean capture
#   flow_run.ps1                                    # plain boot, marks only, no frames
#   flow_run.ps1 -Frames -Gates -WriteGoldens       # RE-BANK both goldens (look first!)
#
# Exit code 0 = the run completed and any requested gates passed; 1 = something failed.
param(
  [string]$OutDir      = "",     # default: <repo>\scratch\flow_run\<timestamp>
  [int]$MaxSeconds     = 275,
  [switch]$Frames,
  [switch]$Gates,                # run frame_gate.ps1 + carselect_frame_gate.ps1 at the end
  [switch]$WriteGoldens,         # re-bank both goldens instead of checking them
  [switch]$HoldCarSelect,        # stay at car select instead of accepting through it
  [string]$FrameDir    = "",     # default: <repo>\scratch\flow_frames  (C: is tight; frames go to D:)
  [int]$LogWaitSeconds = 90
)
$ErrorActionPreference = 'Stop'

$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$exe  = Join-Path $root "build\game\Burnout_PC.exe"
$log  = Join-Path $root "build\game\BrnGame.log"
if ($OutDir   -eq "") { $OutDir   = Join-Path $root ("scratch\flow_run\" + (Get-Date).ToString('yyyyMMdd_HHmmss')) }
if ($FrameDir -eq "") { $FrameDir = Join-Path $root "scratch\flow_frames" }

if (-not (Test-Path $exe)) { Write-Host "[flow] FAIL: no exe at $exe -- build first."; exit 1 }
if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
New-Item -ItemType Directory -Force $OutDir | Out-Null

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class KBFLOW {
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, IntPtr extra);
  public static void Tap(byte vk) { keybd_event(vk,0,0,IntPtr.Zero); System.Threading.Thread.Sleep(60); keybd_event(vk,0,2,IntPtr.Zero); }
}
"@

Get-Process Burnout_PC -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
if (Test-Path $log) { Remove-Item $log -Force }

# --- environment: a DEFAULT run, with every override explicitly cleared -------------------
$env:BRN_INPUT_ALLOW_BACKGROUND = "1"
foreach ($v in @('BRN_RC_PROBE','BRN_DIRECTOR_TRACE','BRN_FORCE_DIRECTOR_CAMERA','BRN_WORLD_CAMFREE')) {
  Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}
Write-Host "[flow] DEFAULT run: BRN_WORLD_CAMFREE / FORCE_DIRECTOR_CAMERA / DIRECTOR_TRACE / RC_PROBE all cleared."

$framesOut = $null
if ($Frames) {
  # ⛔ BRN_FRAME_DUMP TAKES A DIRECTORY.  Set to a flag like '1' the game builds the path
  #   "1\bb_000000.bmp", fopen()s it relative to build\game\, gets NULL, and returns without
  #   writing OR logging anything -- and the gates then score whatever stale bitmaps were
  #   already in the dump dir.  Absolute path, created here, emptied here, echoed here.
  if (-not [System.IO.Path]::IsPathRooted($FrameDir)) {
    Write-Host "[flow] FAIL: -FrameDir '$FrameDir' is relative. The game resolves BRN_FRAME_DUMP"
    Write-Host "       against build\game\, not your cwd. Pass an absolute path."
    exit 1
  }
  if (Test-Path $FrameDir) { Remove-Item -Recurse -Force $FrameDir }
  New-Item -ItemType Directory -Force $FrameDir | Out-Null
  $framesOut = $FrameDir
  $env:BRN_FRAME_DUMP = $framesOut
  Write-Host "[flow] BRN_FRAME_DUMP = $framesOut  (emptied; every 30th present lands here)"
} else {
  Remove-Item Env:\BRN_FRAME_DUMP -ErrorAction SilentlyContinue
}

function Newest-Frame {
  if (-not $framesOut) { return "-" }
  $f = @(Get-ChildItem $framesOut -Filter *.bmp -ErrorAction SilentlyContinue | Sort-Object Name)
  if ($f.Count -eq 0) { return "-" }
  return $f[-1].Name
}

$evAccept = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::AutoReset, "Local\BurnoutPC_Input_Accept")

# --- launch ------------------------------------------------------------------------------
$t0 = Get-Date                      # THE launch instant; the gates' freshness cut-off.
$p  = Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -PassThru
Write-Host ("[flow] pid={0} frames={1} hold={2} max={3}s  RUNSTART {4}" -f `
            $p.Id, [bool]$Frames, [bool]$HoldCarSelect, $MaxSeconds, $t0.ToString('o'))

# ⭐ THE ANTI-RACE GATE.  Nothing below reads the log until the file on disk was written by
#   THIS run.  A leftover log from a previous boot can never contribute a mark.
function Wait-ForOwnLog {
  $deadline = (Get-Date).AddSeconds($LogWaitSeconds)
  while ((Get-Date) -lt $deadline) {
    if ($p.HasExited) { return $false }
    if (Test-Path $log) {
      $li = Get-Item $log -ErrorAction SilentlyContinue
      if ($li -and $li.LastWriteTime -ge $t0) { return $true }
    }
    Start-Sleep -Milliseconds 200
  }
  return $false
}
if (-not (Wait-ForOwnLog)) {
  Write-Host "[flow] FAIL: no log written by THIS run within ${LogWaitSeconds}s (stale log ignored on purpose)."
  Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
  exit 1
}
Write-Host "[flow] log confirmed fresh (mtime >= launch) -- previous-run marks are impossible."

# --- flow-state cues.  VERIFIED PRESENT in real logs; see the banner. --------------------
$cues = @(
  @('flyby',    '\[Intro\] state 9 -> 3'),
  @('carsel',   'Entering Car Select'),
  @('livery',   'CSL : Entering Car Select'),
  @('accept',   'CSM : SendStateEvent\( "ACCEPT" \)'),
  @('exitjy',   'action 4 -> ExitJunkyard'),
  @('strfin',   'signalling StreamingFinished'),
  @('exitst',   'CarSelectManager::UpdateExitState')
)

$lastAccept = Get-Date
$seenAsserts = 0
$phase = 'BOOT'          # BOOT -> FLYBY (quiet) -> CARSELECT (pump again) -> DRIVING
$acceptGap = 2.0
$marks = @{}
$markFrame = @{}

while ($true) {
  $elapsed = ((Get-Date) - $t0).TotalSeconds
  if ($elapsed -gt $MaxSeconds) { Write-Host "[flow] max seconds"; break }
  if ($p.HasExited) { Write-Host ("[flow] game exited early at {0:f1}s" -f $elapsed); break }

  $txt = Get-Content $log -Raw -ErrorAction SilentlyContinue
  if ($null -ne $txt) {
    $n = ([regex]::Matches($txt, '\[ASSERT \d+\]')).Count
    if ($n -gt $seenAsserts) {
      $seenAsserts = $n
      for ($k = 0; $k -lt 3; $k++) { [KBFLOW]::Tap(0x23); Start-Sleep -Milliseconds 120 }
      Write-Host ("[flow] dismissed assert #{0} at {1:f1}s" -f $n, $elapsed)
    }

    foreach ($m in $cues) {
      if (-not $marks.ContainsKey($m[0]) -and $txt -match $m[1]) {
        $marks[$m[0]] = $elapsed
        $markFrame[$m[0]] = Newest-Frame
        Write-Host ("[flow] {0,-8} at {1,6:f1}s  frame={2}" -f $m[0], $elapsed, $markFrame[$m[0]])
      }
    }

    if ($phase -eq 'BOOT'      -and $marks.ContainsKey('flyby'))  { $phase = 'FLYBY' }
    if ($phase -eq 'FLYBY'     -and $marks.ContainsKey('carsel')) { $phase = 'CARSELECT'; $acceptGap = 3.0; $lastAccept = Get-Date }
    if ($phase -eq 'CARSELECT' -and $marks.ContainsKey('exitst')) { $phase = 'DRIVING' }
  }

  $pump = ($phase -eq 'BOOT') -or (($phase -eq 'CARSELECT') -and (-not $HoldCarSelect))
  if ($pump -and ((Get-Date) - $lastAccept).TotalSeconds -ge $acceptGap) {
    $evAccept.Set() | Out-Null
    $lastAccept = Get-Date
  }
  Start-Sleep -Milliseconds 250
}

$endFrame = Newest-Frame
$endElapsed = ((Get-Date) - $t0).TotalSeconds
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
Remove-Item Env:\BRN_FRAME_DUMP -ErrorAction SilentlyContinue
Copy-Item $log (Join-Path $OutDir "BrnGame.log") -ErrorAction SilentlyContinue

# --- marks.txt.  RUNSTART FIRST: it is what the gates use to reject stale dumps. ----------
$summary = @()
$summary += ("RUNSTART {0}" -f $t0.ToString('o'))
$summary += ("FRAMEDIR {0}" -f $(if ($framesOut) { $framesOut } else { "-" }))
foreach ($k in @('flyby','carsel','livery','accept','exitjy','strfin','exitst')) {
  if ($marks.ContainsKey($k)) { $summary += ("{0,-8} {1,6:f1}s  frame={2}" -f $k, $marks[$k], $markFrame[$k]) }
  else                        { $summary += ("{0,-8} (never)" -f $k) }
}
$summary += ("END      {0,6:f1}s  frame={1}" -f $endElapsed, $endFrame)
$summary += ("asserts={0} phase={1}" -f $seenAsserts, $phase)
$marksPath = Join-Path $OutDir "marks.txt"
$summary | Set-Content $marksPath

Write-Host ("[flow] asserts={0} phase={1} endframe={2}" -f $seenAsserts, $phase, $endFrame)
$summary | ForEach-Object { Write-Host "[flow]   $_" }
if ($framesOut) {
  $fc = @(Get-ChildItem $framesOut -Filter *.bmp -ErrorAction SilentlyContinue)
  Write-Host ("[flow] frames={0} {1:f0} MB -> {2}" -f $fc.Count, (($fc | Measure-Object Length -Sum).Sum/1MB), $framesOut)
}
Write-Host "[flow] out -> $OutDir"

# --- gates -------------------------------------------------------------------------------
if (-not $Gates -and -not $WriteGoldens) { exit 0 }
if (-not $framesOut) { Write-Host "[flow] FAIL: -Gates needs -Frames."; exit 1 }

$rc = 0
$gh = Join-Path $PSScriptRoot 'golden_junkyard_handover.csv'
$gc = Join-Path $PSScriptRoot 'golden_junkyard_carselect.csv'

Write-Host "`n[flow] ---- chase / post-handover gate ----"
if ($WriteGoldens) { & (Join-Path $PSScriptRoot 'frame_gate.ps1') -FrameDir $framesOut -Marks $marksPath -WriteGolden $gh }
else               { & (Join-Path $PSScriptRoot 'frame_gate.ps1') -FrameDir $framesOut -Marks $marksPath -Golden $gh }
if ($LASTEXITCODE -ne 0) { $rc = 1 }

Write-Host "`n[flow] ---- car-select gate ----"
if ($WriteGoldens) { & (Join-Path $PSScriptRoot 'carselect_frame_gate.ps1') -FrameDir $framesOut -Marks $marksPath -WriteGolden $gc }
else               { & (Join-Path $PSScriptRoot 'carselect_frame_gate.ps1') -FrameDir $framesOut -Marks $marksPath -Golden $gc }
if ($LASTEXITCODE -ne 0) { $rc = 1 }

Write-Host ("`n[flow] {0}" -f $(if ($rc -eq 0) { "ALL GATES PASS" } else { "*** GATES FAILED ***" }))
exit $rc
