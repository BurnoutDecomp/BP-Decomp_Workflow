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
# ⭐ IT CAN DRIVE (2026-08-12).  -Drive holds the throttle and -Steer holds a lock once the flow
#   reaches DRIVING, through the game's ORDINARY input chain: the input leaf's harness event
#   channel fills maActionInfo[0] (accelerate) / [1] (brake) / [2] (handbrake) and mfStickLX
#   (steer), which is where the right trigger / left trigger / X / left stick land, and
#   BridgeControllerToWorld reads them into PlayerVehicleControls exactly as it does for a pad.
#   Nothing here writes a velocity, a force, or a physics field.
#   ⚠️ THE DRIVING EVENTS ARE MANUAL-RESET, the four menu events AUTO-RESET, and the difference
#   is the whole point: an auto-reset event is a TAP (one input update observes it), a
#   manual-reset event is a HOLD (every update between Set() and Reset() observes it).  A pedal
#   you can only tap for one frame cannot drive a car.  The game side does not know or care --
#   it is one zero-timeout wait for both.
#
# Usage:
#   flow_run.ps1 -Frames -Gates                     # boot, dump frames, run BOTH gates
#   flow_run.ps1 -Frames -HoldCarSelect             # park at car select for a clean capture
#   flow_run.ps1                                    # plain boot, marks only, no frames
#   flow_run.ps1 -Frames -Gates -WriteGoldens       # RE-BANK both goldens (look first!)
#   flow_run.ps1 -Frames -Drive                     # ... then hold the throttle, dead straight
#   flow_run.ps1 -Frames -Drive -Steer right        # ... and hold full right lock
#   flow_run.ps1 -Frames -Drive -SteerScript "0:left,3.5:none"        # AIM, then run straight
#   flow_run.ps1 -Frames -Drive -ThrottleScript "0:accel,20:brake"    # ... and back off / reverse
#   flow_run.ps1 -Drive -Teleport "2958,12.5,-1764,90"                # PUT THE CAR THERE, then drive
#
# ⭐ AIMING (2026-08-15, walls leg 5).  -Steer holds ONE lock for the whole run, so a driven car
#   can only circle: it can never be lined up on a chosen wall FACE and driven into it head-on.
#   -SteerScript / -ThrottleScript are seconds->token schedules over the SAME manual-reset
#   channels, so "turn for 3.5 s, then straight" becomes expressible and a head-on wall test
#   becomes possible.  ⛔ NO new game code and no new channel: the game still sees nothing but
#   the ordinary pad bits it already reads for -Steer.  The time base for both schedules is
#   seconds since THE FIRST INPUT IS APPLIED (the DRIVING mark + -DriveDelay), not since launch
#   and not since the DRIVING mark -- so a schedule is unaffected by boot/stream timing drift,
#   which is the whole reason marks are anchored to flow states in the first place.
#   An entry is <seconds>:<token>[+<token>...]; the newest entry whose time has passed wins.
#     -SteerScript    tokens: none | left | right
#     -ThrottleScript tokens: none | accel | brake | handbrake   (combine with '+')
#   A schedule REPLACES the corresponding fixed hold; the other channel keeps its old behaviour.
#
# Exit code 0 = the run completed and any requested gates passed; 1 = something failed.
param(
  [string]$OutDir      = "",     # default: <repo>\scratch\flow_run\<timestamp>
  [int]$MaxSeconds     = 275,
  [switch]$Frames,
  [switch]$Gates,                # run frame_gate.ps1 + carselect_frame_gate.ps1 at the end
  [switch]$WriteGoldens,         # re-bank both goldens instead of checking them
  [switch]$HoldCarSelect,        # stay at car select instead of accepting through it
  [switch]$Drive,                # hold ACCELERATE once the flow reaches DRIVING
  [ValidateSet('none','left','right')]
  [string]$Steer       = 'none', # hold a steering lock alongside -Drive
  [string]$SteerScript = "",     # "0:left,3.5:none"      -- overrides -Steer when non-empty
  [string]$ThrottleScript = "",  # "0:accel,20:brake"     -- overrides the plain throttle hold
  [double]$DriveDelay  = 6.0,    # seconds after the DRIVING mark before any input is applied
  [double]$DriveSeconds= 0,      # 0 = hold until the run ends
  [string]$FrameDir    = "",     # default: <repo>\scratch\flow_frames  (C: is tight; frames go to D:)
  [int]$FrameEvery     = 30,     # dump PERIOD in presents; 1 = every present (see the note below)
  [int]$LogWaitSeconds = 90,
  [switch]$MotionProbe,          # opt IN to the [motion] pose/velocity trace (BRN_MOTION_PROBE=1)
  [int]$TriCacheProbe  = 0,      # opt IN to the [tricache] world-collision cache trace; the VALUE
                                 # is the sampling period in frames (1 => the game's default 60).
                                 # ⚠️ A PERIOD, not a switch: 60 frames is 29 m at this build's top
                                 # speed, so the default sampling steps straight over an impact.
  [int]$TractionProbe  = 0,      # opt IN to the [traction] per-WHEEL line trace; also a PERIOD in
                                 # frames. This is the link BELOW the cache: [tricache] says how
                                 # many triangle batches a car was offered, [traction] says where
                                 # each wheel's probe segment actually went and whether it hit.
  [string]$Teleport    = "",     # "x,y,z[,headingDeg]" -- put the player car there, ONCE, through
                                 # the game's own place-on-track path (see the banner below).
  [double]$TeleportArm = 0       # metres the car must have driven before the teleport fires
                                 # (0 = leave the game's own default of 8 m).
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
# ⚠️ BRN_MOTION_PROBE IS IN THIS LIST DELIBERATELY (added 2026-08-15, walls leg 7).  It was the one
# probe env var this script neither set nor cleared, so a leftover `$env:BRN_MOTION_PROBE` from an
# earlier command in the same shell rode into the next run -- and that run then announced itself as
# a "DEFAULT run" while carrying an unrequested instrument.  That is a golden-gate hazard: the
# goldens are meant to be byte-identical to a probe-free build.  Opt IN with -MotionProbe instead.
foreach ($v in @('BRN_RC_PROBE','BRN_DIRECTOR_TRACE','BRN_FORCE_DIRECTOR_CAMERA','BRN_WORLD_CAMFREE','BRN_MOTION_PROBE','BRN_TRICACHE_PROBE','BRN_TRACTION_PROBE')) {
  Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}
if ($MotionProbe) {
  $env:BRN_MOTION_PROBE = "1"
  Write-Host "[flow] MOTION PROBE run: BRN_MOTION_PROBE=1 (opt-in). NOT a default run -- do not gate goldens off this."
}
# ⭐ [tricache] -- the world-collision triangle-cache trace (walls/worldcoll wave). CLEARED above for
# the same reason BRN_MOTION_PROBE is: a leftover env var from an earlier command in the same shell
# would ride into a run that then announces itself as DEFAULT while carrying an instrument.
if ($TriCacheProbe -gt 0) {
  $env:BRN_TRICACHE_PROBE = "$TriCacheProbe"
  Write-Host "[flow] TRICACHE PROBE run: BRN_TRICACHE_PROBE=$TriCacheProbe (opt-in, period in frames). NOT a default run -- do not gate goldens off this."
}
# ⭐ [traction] -- the per-wheel traction-line trace (worldcoll leg 3). Same opt-in discipline and
# the same CLEARED list as [tricache] above, for the same golden-gate reason.
if ($TractionProbe -gt 0) {
  $env:BRN_TRACTION_PROBE = "$TractionProbe"
  Write-Host "[flow] TRACTION PROBE run: BRN_TRACTION_PROBE=$TractionProbe (opt-in, period in frames). NOT a default run -- do not gate goldens off this."
}
if (-not $MotionProbe -and $TriCacheProbe -le 0 -and $TractionProbe -le 0) {
  Write-Host "[flow] DEFAULT run: BRN_WORLD_CAMFREE / FORCE_DIRECTOR_CAMERA / DIRECTOR_TRACE / RC_PROBE / MOTION_PROBE / TRICACHE_PROBE / TRACTION_PROBE all cleared."
}

# ⭐⭐ BRN_PROP_DIAG IS INHERITED, NOT MANAGED -- so it is RECORDED (2026-08-20, gateui r7).
#   It is deliberately NOT in the cleared list above: every prop/gate/UI brief asks for it, and a
#   run that silently turned it off would answer a different question than the one asked.  But it
#   is also not set here, so whether it is on depends entirely on the shell that invoked this
#   script -- and the [prop-diag] / [Q5-*] / [Q6-*] / [UI-gate] families exist or do not exist in
#   the log accordingly.  That is exactly how defect-B round 7 lost seven runs: they were compared
#   against dying runs whose shell had it set, so "same code, same harness" was not the same run at
#   all.  Two logs are only comparable when this line matches, so it is echoed AND written into
#   marks.txt next to the flow marks.  Same for the other inherited knobs a brief may set.
# ⭐⭐ -Teleport -- PUT THE CAR AT COORDINATES (2026-08-21, gateui r9 / billboards).
#   A boot-drive that can only start at the junkyard can only ever test what is within 275 s of
#   the junkyard.  That is how the SMASH flavour of the gate-UI ladder got proven and the
#   BILLBOARD flavour did not: all 120 type-12 regions are elsewhere in the city.
#   ⛔ THIS IS NOT A POSITION POKE.  The env var only ARMS the game's own
#   ActiveRaceCar::RequestPlaceOnTrack, which is answered by the same 100 m vertical line test
#   over the shipped world collision that places the car at boot, seated by the same
#   VehiclePhysics::SetTransformFromPositionOnRoad and re-seeded by the same VehiclePhysics::Reset.
#   The Y a teleport lands on is a vertex of the shipped collision mesh, never a number typed here
#   -- so pass the target's APPROXIMATE height and let the game find the ground.
#   ⚠️ It fires once the car has DRIVEN -TeleportArm metres (default 8), not on a timer: the car
#   reaches its live state at car select, tens of seconds before the flow reaches DRIVING, and
#   boot timing drifts run to run -- the same reason every mark in this script is anchored to a
#   flow state rather than a frame index.
#   ⚠️ THE STREAMER DOES NOT TELEPORT.  The car lands on collision that is resident whole, so it
#   never falls through the world, but the visible world and the breakable props around the
#   destination arrive over the next few seconds.  Give the car time to sit before asking it to
#   smash anything -- a -ThrottleScript that nudges, holds the handbrake, then accelerates is the
#   pattern (the nudge is what trips the arm distance).
#   It is RECORDED in marks.txt next to DIAGENV for the same reason DIAGENV is: two logs are only
#   comparable when the run carried the same instruments.
foreach ($v in @('BRN_CAR_TELEPORT','BRN_CAR_TELEPORT_ARM_DISTANCE')) {
  Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}
$teleportText = '(none)'
if ($Teleport -ne "") {
  $lParts = @($Teleport -split ',')
  if ($lParts.Count -lt 3 -or $lParts.Count -gt 4) {
    Write-Host "[flow] FAIL: -Teleport '$Teleport' is not `"x,y,z[,headingDeg]`"."
    exit 1
  }
  foreach ($lp in $lParts) {
    $lNum = 0.0
    if (-not [double]::TryParse($lp.Trim(), [Globalization.NumberStyles]::Float,
                                [Globalization.CultureInfo]::InvariantCulture, [ref]$lNum)) {
      Write-Host "[flow] FAIL: -Teleport component '$lp' is not a number."
      exit 1
    }
  }
  $env:BRN_CAR_TELEPORT = ($lParts | ForEach-Object { $_.Trim() }) -join ','
  $teleportText = $env:BRN_CAR_TELEPORT
  if ($TeleportArm -gt 0) {
    $env:BRN_CAR_TELEPORT_ARM_DISTANCE = ("{0}" -f $TeleportArm.ToString([Globalization.CultureInfo]::InvariantCulture))
    $teleportText += (" arm={0}m" -f $env:BRN_CAR_TELEPORT_ARM_DISTANCE)
  }
  Write-Host "[flow] TELEPORT armed: BRN_CAR_TELEPORT=$teleportText -- the player car is placed"
  Write-Host "       there ONCE, through the game's own place-on-track path. NOT a default run."
  if (-not $Drive) {
    Write-Host "[flow] NOTE: -Teleport without -Drive will never fire -- the arm waits for the car"
    Write-Host "       to have MOVED. Pass -Drive (and a -ThrottleScript if you want it to stop again)."
  }
}

$diagEnv = @()
foreach ($v in @('BRN_PROP_DIAG','BRN_HEAP_CHECK','BRN_RENDER_POSTFX','BRN_POSTFX_MASK_TEST')) {
  $val = [Environment]::GetEnvironmentVariable($v)
  if (-not [string]::IsNullOrEmpty($val)) { $diagEnv += ("{0}={1}" -f $v, $val) }
}
$diagEnvText = if ($diagEnv.Count -gt 0) { $diagEnv -join ' ' } else { '(none set)' }
Write-Host "[flow] INHERITED diag env: $diagEnvText"

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
  # ⭐ -FrameEvery: the dump PERIOD in presents (default 30 == the game's own default).
  #   30 presents is ~0.4 s on an uncapped boot, which is COARSER THAN A UI TRANSITION --
  #   a licence/menu animation that plays in ~1 s lands in two samples and reads as a pop.
  #   Judging "does this animate?" off a 30-present dump measures the SAMPLER, not the game.
  #   Use -FrameEvery 1 for a transition, and expect ~30x the frames (and disk).
  if ($FrameEvery -gt 0 -and $FrameEvery -ne 30) {
    $env:BRN_FRAME_DUMP_EVERY = "$FrameEvery"
  } else {
    Remove-Item Env:\BRN_FRAME_DUMP_EVERY -ErrorAction SilentlyContinue
  }
  $lEvery = if ($FrameEvery -gt 0) { $FrameEvery } else { 30 }
  Write-Host "[flow] BRN_FRAME_DUMP = $framesOut  (emptied; every ${lEvery}th present lands here)"
} else {
  Remove-Item Env:\BRN_FRAME_DUMP -ErrorAction SilentlyContinue
  Remove-Item Env:\BRN_FRAME_DUMP_EVERY -ErrorAction SilentlyContinue
}

function Newest-Frame {
  if (-not $framesOut) { return "-" }
  $f = @(Get-ChildItem $framesOut -Filter *.bmp -ErrorAction SilentlyContinue | Sort-Object Name)
  if ($f.Count -eq 0) { return "-" }
  return $f[-1].Name
}

$evAccept = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::AutoReset, "Local\BurnoutPC_Input_Accept")

# ⭐ THE DRIVING CHANNELS -- MANUAL-RESET (see the banner).  Created unconditionally so the game
#   always finds them; a channel that is never Set() is a control that is never pressed, which is
#   exactly the "resting car undisturbed" case.  Named after the EGameInputActions slot each one
#   fills, so the game side's switch and this list can be diffed by eye.
$evAccel = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::ManualReset, "Local\BurnoutPC_Input_Accelerate")
$evBrake = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::ManualReset, "Local\BurnoutPC_Input_Brake")
$evHandB = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::ManualReset, "Local\BurnoutPC_Input_HandBrake")
$evStrL  = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::ManualReset, "Local\BurnoutPC_Input_SteerLeft")
$evStrR  = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::ManualReset, "Local\BurnoutPC_Input_SteerRight")
foreach ($e in @($evAccel,$evBrake,$evHandB,$evStrL,$evStrR)) { $e.Reset() | Out-Null }

# ⭐ THE SCHEDULE PARSER (walls leg 5).  Parses "<sec>:<tok>[+<tok>],..." into a time-sorted list.
#   ⚠️ InvariantCulture ON PURPOSE: this box runs a comma-decimal locale, where [double]::Parse
#   turns "3.5" into 35 -- a schedule silently 10x too long, which reads as "the car never
#   turned" rather than as a parse bug.  A bad entry is a hard FAIL, never a silent skip: a
#   mistyped aim schedule that quietly degrades to "drive straight" would be scored as a wall
#   test that the car simply drove past.
function Parse-Schedule([string]$lSpec, [string[]]$lValid, [string]$lWhat) {
  $lOut = @()
  if ([string]::IsNullOrWhiteSpace($lSpec)) { return ,$lOut }
  foreach ($lPair in ($lSpec -split ',')) {
    $lTrim = $lPair.Trim()
    if ($lTrim -eq "") { continue }
    $lKV = $lTrim -split ':', 2
    if ($lKV.Count -ne 2) {
      Write-Host "[flow] FAIL: -$lWhat entry '$lTrim' is not <seconds>:<token>."; exit 1
    }
    $lSec = 0.0
    try { $lSec = [double]::Parse($lKV[0].Trim(), [Globalization.CultureInfo]::InvariantCulture) }
    catch { Write-Host "[flow] FAIL: -$lWhat entry '$lTrim' has a non-numeric time."; exit 1 }
    if ($lSec -lt 0) { Write-Host "[flow] FAIL: -$lWhat time '$lTrim' is negative."; exit 1 }
    $lTok = $lKV[1].Trim().ToLower()
    foreach ($lPiece in ($lTok -split '\+')) {
      if ($lValid -notcontains $lPiece) {
        Write-Host ("[flow] FAIL: -$lWhat token '{0}' unknown. Valid: {1}" -f $lPiece, ($lValid -join '|'))
        exit 1
      }
    }
    $lOut += ,([pscustomobject]@{ t = $lSec; tok = $lTok })
  }
  return ,@($lOut | Sort-Object t)
}
# The token in force at time $lT: the LAST entry whose time has passed. Before the first entry's
# time the schedule is not yet in force, so the caller's default (the fixed hold) still applies --
# reported as $null, never as "none", so "no entry yet" and "an entry saying none" stay distinct.
function Schedule-At($lSched, [double]$lT) {
  $lCur = $null
  foreach ($lE in $lSched) { if ($lT -ge $lE.t) { $lCur = $lE.tok } else { break } }
  return $lCur
}
$steerSched = Parse-Schedule $SteerScript    @('none','left','right')                 'SteerScript'
$throtSched = Parse-Schedule $ThrottleScript @('none','accel','brake','handbrake')    'ThrottleScript'

if ($Drive) {
  Write-Host ("[flow] DRIVE armed: throttle held from DRIVING+{0:f1}s, steer={1}, hold={2}" -f `
              $DriveDelay, $Steer, $(if ($DriveSeconds -gt 0) { ("{0:f0}s" -f $DriveSeconds) } else { "to end" }))
  if ($steerSched.Count -gt 0) {
    Write-Host ("[flow] AIM: SteerScript ({0} entries, t=0 at DRIVING+{1:f1}s) -- overrides -Steer {2}" -f `
                $steerSched.Count, $DriveDelay, $Steer)
    foreach ($e in $steerSched) { Write-Host ("[flow]   steer   t+{0,6:f2}s -> {1}" -f $e.t, $e.tok) }
  }
  if ($throtSched.Count -gt 0) {
    Write-Host ("[flow] AIM: ThrottleScript ({0} entries, t=0 at DRIVING+{1:f1}s)" -f `
                $throtSched.Count, $DriveDelay)
    foreach ($e in $throtSched) { Write-Host ("[flow]   pedal   t+{0,6:f2}s -> {1}" -f $e.t, $e.tok) }
  }
} else {
  Write-Host "[flow] DRIVE not armed: the five driving channels exist but are never signalled."
  if ($steerSched.Count -gt 0 -or $throtSched.Count -gt 0) {
    Write-Host "[flow] FAIL: -SteerScript/-ThrottleScript need -Drive (they schedule the drive channels)."
    exit 1
  }
}

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
#
# ⛔⛔ 2026-08-11 -- 'exitst' REMOVED, and the reason matters more than the cue did.
# It matched 'CarSelectManager::UpdateExitState', and the game NEVER logs that as a progress
# line -- the only occurrence in any log was as a frame INSIDE the callstack printed by the
# [ASSERT] lpProgressionData != NULL crash dump.  So `phase=DRIVING` was being derived from a
# stack trace: the flow only ever "reached DRIVING" *because* it was asserting.  Converting
# PROGRESSION.DAT to platform 4 retired that assert (3 asserts -> 0) and the mark stopped
# firing, which reads as a regression and is the exact opposite.
# The junkyard-exit signal is 'strfin', which fired at the IDENTICAL timestamp (81.8s) in the
# last pre-conversion run -- so promoting on it reproduces the old behaviour without depending
# on a crash.  See Read-CueText below for the general guard.
$cues = @(
  @('flyby',    '\[Intro\] state 9 -> 3'),
  @('carsel',   'Entering Car Select'),
  @('livery',   'CSL : Entering Car Select'),
  @('accept',   'CSM : SendStateEvent\( "ACCEPT" \)'),
  @('exitjy',   'action 4 -> ExitJunkyard'),
  @('strfin',   'signalling StreamingFinished')
)

# ⭐ Cue text with ASSERT CALLSTACK FRAMES STRIPPED.  A callstack frame is 4-space-indented and
# is a single bare token ("    BrnGameState::CarSelectManager::UpdateExitState", "    0xB16D2").
# Matching cues against those makes a crash look like progress -- which is exactly what happened
# above.  Any cue, not just the removed one, is vulnerable; strip once, centrally.
#
# ⚠️ SECOND SHAPE ADDED 2026-08-16.  CgsCrashHandlerPC's WriteReport now emits resolved frames as
# "    Name + 0xNNN    [rva 0xNNN]" so a player's report pins the statement, not just the function
# (see CgsMapFileReaderMinimalMemory.h's KI_MAX_STACK_RESULTS banner).  Those lines are NOT bare
# tokens, so the original pattern let them through -- reopening exactly the hole this function
# exists to close, and on the CRASH path specifically.  Both shapes are stripped now.
function Strip-CallstackFrames([string]$t) {
  if ($null -eq $t) { return $t }
  return ($t -split "`n" | Where-Object {
    $_ -notmatch '^\s{4}\S+\s*$' -and $_ -notmatch '^\s{4}\S.*\[rva 0x[0-9A-Fa-f]+\]\s*$'
  }) -join "`n"
}

$lastAccept = Get-Date
$seenAsserts = 0
$phase = 'BOOT'          # BOOT -> FLYBY (quiet) -> CARSELECT (pump again) -> DRIVING
$acceptGap = 2.0
$marks = @{}
$markFrame = @{}
$drivingAt = Get-Date    # set for real on the BOOT->...->DRIVING transition
$driveHeld = 'none/none' # "<pedal>/<steer>" currently asserted on the channels
$inputLog  = @()         # every input transition, for marks.txt -- what the car was ACTUALLY told

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

    $cueTxt = Strip-CallstackFrames $txt
    foreach ($m in $cues) {
      if (-not $marks.ContainsKey($m[0]) -and $cueTxt -match $m[1]) {
        $marks[$m[0]] = $elapsed
        $markFrame[$m[0]] = Newest-Frame
        Write-Host ("[flow] {0,-8} at {1,6:f1}s  frame={2}" -f $m[0], $elapsed, $markFrame[$m[0]])
      }
    }

    if ($phase -eq 'BOOT'      -and $marks.ContainsKey('flyby'))  { $phase = 'FLYBY' }
    if ($phase -eq 'FLYBY'     -and $marks.ContainsKey('carsel')) { $phase = 'CARSELECT'; $acceptGap = 3.0; $lastAccept = Get-Date }
    if ($phase -eq 'CARSELECT' -and $marks.ContainsKey('strfin')) { $phase = 'DRIVING'; $drivingAt = Get-Date }
  }

  $pump = ($phase -eq 'BOOT') -or (($phase -eq 'CARSELECT') -and (-not $HoldCarSelect))
  if ($pump -and ((Get-Date) - $lastAccept).TotalSeconds -ge $acceptGap) {
    $evAccept.Set() | Out-Null
    $lastAccept = Get-Date
  }

  # ---- the driving hold ------------------------------------------------------------------
  # Set()/Reset() on a MANUAL-RESET event is press-and-hold / release: the game observes the
  # channel as down on EVERY input update in between, which is the only way a throttle means
  # anything.  DriveDelay leaves the car settled on its springs first so the run measures
  # driving, not the tail of the spawn drop.
  if ($Drive -and $phase -eq 'DRIVING') {
    $sinceDriving = ((Get-Date) - $drivingAt).TotalSeconds
    $tIn  = $sinceDriving - $DriveDelay      # THE SCHEDULE TIME BASE: 0 == first input applied
    $want = ($tIn -ge 0) -and (($DriveSeconds -le 0) -or ($tIn -lt $DriveSeconds))

    # What every channel group should be RIGHT NOW. The fixed holds are the defaults; a schedule
    # entry whose time has passed replaces its group. Resolving the whole desired state each poll
    # and applying only on CHANGE keeps the Set/Reset traffic identical in shape to the old
    # single-transition hold -- a manual-reset event that is re-Set() every 250 ms would still
    # read as held, but the log would be unreadable and a missed Reset() would be invisible.
    $curSteer = 'none'; $curPedal = 'none'
    if ($want) {
      $curSteer = $Steer; $curPedal = 'accel'
      $lS = Schedule-At $steerSched $tIn; if ($null -ne $lS) { $curSteer = $lS }
      $lP = Schedule-At $throtSched $tIn; if ($null -ne $lP) { $curPedal = $lP }
    }

    $state = "$curPedal/$curSteer"
    if ($state -ne $driveHeld) {
      $driveHeld = $state
      $pedals = @($curPedal -split '\+')
      if ($pedals -contains 'accel')     { $evAccel.Set() | Out-Null } else { $evAccel.Reset() | Out-Null }
      if ($pedals -contains 'brake')     { $evBrake.Set() | Out-Null } else { $evBrake.Reset() | Out-Null }
      if ($pedals -contains 'handbrake') { $evHandB.Set() | Out-Null } else { $evHandB.Reset() | Out-Null }
      if ($curSteer -eq 'left')  { $evStrL.Set() | Out-Null } else { $evStrL.Reset() | Out-Null }
      if ($curSteer -eq 'right') { $evStrR.Set() | Out-Null } else { $evStrR.Reset() | Out-Null }
      Write-Host ("[flow] input {0,-20} at {1,6:f1}s (DRIVING+{2:f1}s, t+{3:f2}s)" -f `
                  $state, $elapsed, $sinceDriving, $tIn)
      $inputLog += ("input {0,-20} run={1,6:f1}s t+{2,6:f2}s" -f $state, $elapsed, $tIn)
    }
  }
  Start-Sleep -Milliseconds 250
}
foreach ($e in @($evAccel,$evBrake,$evHandB,$evStrL,$evStrR)) { $e.Reset() | Out-Null }

$endFrame = Newest-Frame
$endElapsed = ((Get-Date) - $t0).TotalSeconds

# ⭐⭐ THE PROCESS EXIT CODE (added 2026-08-20, gateui r7 / defect B).  It must be read BEFORE
#   Stop-Process, because Stop-Process overwrites it with the kill code and the one thing worth
#   knowing is then gone.  This is the ONLY signal that identifies the deaths BrnGame.log cannot
#   log, because they never run a handler:
#     0          the game asked to quit (or was killed by the line below -- read the flag)
#     0xC0000005 access violation      -- and no [EXCEPTION] block means the filter could not run
#     0xC00000FD stack overflow
#     0xC0000409 __fastfail: /GS stack-cookie failure or a CRT invalid argument
#     0xC0000374 heap corruption
#     3          abort()/_exit(3)
#   ⚠️ WER is DISABLED on this machine (HKLM ... \Windows Error Reporting\Disabled = 1), so
#   "no Application event 1000" proves NOTHING about a run.  This does.
$exitedOnOwn = $p.HasExited
$exitCode    = $null
if ($exitedOnOwn) {
  try { $exitCode = $p.ExitCode } catch { $exitCode = $null }
  if ($null -ne $exitCode) {
    Write-Host ("[flow] game exited on its own: exit code {0} (0x{1:X8})" -f $exitCode, ([uint32]($exitCode -band 0xFFFFFFFFL)))
  } else {
    Write-Host "[flow] game exited on its own: exit code unavailable"
  }
}

Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
Remove-Item Env:\BRN_FRAME_DUMP -ErrorAction SilentlyContinue
Remove-Item Env:\BRN_FRAME_DUMP_EVERY -ErrorAction SilentlyContinue
Copy-Item $log (Join-Path $OutDir "BrnGame.log") -ErrorAction SilentlyContinue

# --- marks.txt.  RUNSTART FIRST: it is what the gates use to reject stale dumps. ----------
$summary = @()
$summary += ("RUNSTART {0}" -f $t0.ToString('o'))
$summary += ("FRAMEDIR {0}" -f $(if ($framesOut) { $framesOut } else { "-" }))
foreach ($k in @('flyby','carsel','livery','accept','exitjy','strfin')) {
  if ($marks.ContainsKey($k)) { $summary += ("{0,-8} {1,6:f1}s  frame={2}" -f $k, $marks[$k], $markFrame[$k]) }
  else                        { $summary += ("{0,-8} (never)" -f $k) }
}
$summary += ("END      {0,6:f1}s  frame={1}" -f $endElapsed, $endFrame)
$summary += ("asserts={0} phase={1}" -f $seenAsserts, $phase)
# DIAGENV: the inherited probe knobs this run actually carried. Two runs are comparable only
# when this line matches -- see the banner where it is collected.
$summary += ("DIAGENV  {0}" -f $diagEnvText)
# TELEPORT: the -Teleport spec this run carried, for the same comparability reason as DIAGENV --
# a log whose car started 250 m from the junkyard is not comparable with one that did not.
$summary += ("TELEPORT {0}" -f $teleportText)
# EXIT: how the process left. "harness-stop" = it was still alive and this script killed it;
# anything else is the game's own exit code, decoded in the banner next to the read above.
if ($exitedOnOwn) {
  if ($null -ne $exitCode) {
    $summary += ("EXIT     self  code={0} (0x{1:X8})" -f $exitCode, ([uint32]($exitCode -band 0xFFFFFFFFL)))
  } else {
    $summary += "EXIT     self  code=unavailable"
  }
} else {
  $summary += "EXIT     harness-stop (process was still alive)"
}
$summary += ("drive={0} steer={1} delay={2:f1}s hold={3}" -f `
             [bool]$Drive, $Steer, $DriveDelay, $(if ($DriveSeconds -gt 0) { ("{0:f0}s" -f $DriveSeconds) } else { "to-end" }))
if ($SteerScript    -ne "") { $summary += ("steerscript    {0}" -f $SteerScript) }
if ($ThrottleScript -ne "") { $summary += ("throttlescript {0}" -f $ThrottleScript) }
# ⭐ The transitions that ACTUALLY fired, not the ones requested: an aim schedule whose last leg
#   never ran (short run, early exit) would otherwise be indistinguishable from one that did.
$summary += $inputLog
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
