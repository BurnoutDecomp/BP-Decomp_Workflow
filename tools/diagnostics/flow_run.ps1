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
#   flow_run.ps1 -Frames -Drive -PauseAt 25 -PauseTarget driver -ShoulderAt "30:R:2" -UnpauseAt 45
#                                     # pause on the DRIVER DETAILS screen, press RB (TOGGLE_RIGHT ->
#                                     # CN_SETTINGS), then try to back out -- the shoulder-button
#                                     # soft-lock test.
#   flow_run.ps1 -Frames -Drive -SteerScript "0:left,3.5:none"        # AIM, then run straight
#   flow_run.ps1 -Frames -Drive -ThrottleScript "0:accel,20:brake"    # ... and back off / reverse
#   flow_run.ps1 -Drive -Teleport "2958,12.5,-1764,90"                # PUT THE CAR THERE, then drive
#   flow_run.ps1 -Drive -Teleport "2641.5,1.3,-1723.8,169" -StartEvent
#                                     # stand in stunt junction 480897 and ARM the event start
#                                     # (BRN_START_EVENT=1; off by default -- see the banner below)
#   flow_run.ps1 -Frames -Drive -Teleport "2641.5,1.3,-1723.8,169" -ThrottleScript "0:accel,10:none" -SkipTrainingTip
#                                     # ... and let the START HINT show while the boot tutorial tip
#                                     # is still up (BRN_SKIP_TRAINING_TIP=1; off by default, needs
#                                     # $env:BRN_PROP_DIAG=1 to be visible in the log)
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
  [int]$CrashPlayer    = 0,      # opt IN to the deterministic player-crash trigger
                                 # (BRN_CRASH_PLAYER = the UpdateVehiclePhysics call to fire on;
                                 # 0 = off). ⭐ Crashes are STOCHASTIC (2 runs in 5), so a claim
                                 # about crash entry/recovery needs this, not a lucky collision.
  [string]$PauseAt     = "",     # opt IN: seconds after DRIVING to TAP the offline pause (action 46).
                                 #   Opens the main map, which IS the offline pause. "" == never.
                                 #   ⭐ A COMMA-SEPARATED LIST, so a run can pause and resume
                                 #   REPEATEDLY ("20,40,60") -- one tap per entry, each latched.
                                 #   A single number still works and means one cycle.
  [ValidateSet('map','driver')]
  [string]$PauseTarget = 'map',  # which offline pause -PauseAt taps: 'map' = action 46 GUI_BACK
                                 #   (CN_MAP_MAIN, whose base half is parked so nothing draws),
                                 #   'driver' = action 45 GUI_START (CN_D_DETAIL, the Driver
                                 #   Details screen -- the console's START-button pause).
  [string]$UnpauseAt   = "",     # opt IN: seconds after DRIVING to TAP Stop (action 50 GUI_CANCEL,
                                 #   i.e. Escape / pad-B) to come back out of the map. Same list
                                 #   form; entry i must be > PauseAt entry i, and repeated cycles
                                 #   need one entry per pause. ⛔ It taps Stop, NOT Accept -- the
                                 #   map's exit arm takes 45/50 only. See the $evStop banner.
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
  [double]$TeleportArm = 0,      # metres the car must have driven before the teleport fires
                                 # (0 = leave the game's own default of 8 m).
  [int]$DeformTrace    = 0,      # opt IN to the [deform-trace] PER-FRAME deformation witness
                                 # (BRN_DEFORM_TRACE = a sampling PERIOD in calls; 1 = every call).
                                 # ⭐ THE SERIES, not the one-shot. [deform-readback]'s "first
                                 # non-zero" line fires ONCE, at the junkyard 0.85 preset, and says
                                 # nothing whatever about whether a crash deforms anything. This
                                 # prints dispSq (the sim's summed sensor displacement) AND
                                 # maxVerlet (the constant-22 array that actually moves vertices)
                                 # on one line per change, tagged player/crashing/wrecked.
                                 # It also arms the [deform-upload] control at the upload site.
  [string]$Showtime    = "",     # opt IN to the SHOWTIME gesture: "<at>[:<holdSecs>]" seconds after
                                 #   the DRIVING mark, HOLD BOTH BUMPERS (rows 54+55 ->
                                 #   ControllerInput +0x42 mbCrashModePressed). Default hold 5 s.
                                 #   ⭐ THIS PRESSES THE REAL BUTTON through the ordinary input chain --
                                 #   it does not poke a game-state flag. It also sets
                                 #   BRN_START_SHOWTIME=1, which is now INERT -- the console's own
                                 #   ShouldStartShowtimeMode @0x82356B18 + the DetectModeStarts else
                                 #   arm landed 2026-08-27 and the harness hook was deleted with them.
                                 #   ⛔ NOT a default run: it can leave free burn.
  [string]$ShoulderAt  = "",     # opt IN: press ONE bumper. "<sec>:<L|R>[:<holdSec>]", comma-
                                 #   separated for repeats -- e.g. "24:R:1.5,44:L:1.5". Seconds are
                                 #   on the SAME DRIVING time base as -PauseAt, so a bumper press can
                                 #   be scheduled INSIDE a pause. Default hold 1.5 s.
                                 #   ⭐ WHY THIS EXISTS SEPARATELY FROM -Showtime: showtime is the
                                 #   BOTH-bumpers gesture and holds rows 54+55 together, so it cannot
                                 #   express LB alone or RB alone -- and on the pause screen the two
                                 #   are DIFFERENT transitions (54 -> TOGGLE_LEFT -> CN_MAP_MAIN,
                                 #   55 -> TOGGLE_RIGHT -> CN_SETTINGS). Mutually exclusive with
                                 #   -Showtime: they drive the same two channels.
  [switch]$StartEvent,           # opt IN to the EVENT-START hook (BRN_START_EVENT=1). OFF by
                                 # default and CLEARED every run -- it is a CAPABILITY, not an
                                 # instrument -- the same discipline -CrashEntry carried until that
                                 # flag was deleted on 2026-08-27. See the banner below.
  [switch]$ReleaseAsserts,       # opt IN to HOLDING the assert-release event open for the whole run,
                                 # instead of releasing one assert per detection (the default).
                                 # ⛔ NOT a default run: `asserts=` stops being comparable, because
                                 # every assert self-releases whether or not the poll loop saw it.
                                 # Use it ONLY for the open-world assert STORM -- four sites
                                 # (BrnSatNavRenderer.cpp:1306/:1307, BrnGuiCache_wH3b.cpp:84,
                                 # BrnGuiWorldDataController.cpp:374) fire once per frame while
                                 # driving, ~3,178 times each in 400 s, far faster than the ~1 Hz
                                 # poll can release them one at a time.
  [double]$MinFreeGB   = 25,     # refuse to START a frame dump below this much free space --
                                 # a dump can reach 16 GB and filling the volume mid-run breaks
                                 # far more than the run (see the guard below)
  [int]$MaxLogMB       = 128,    # abort if BrnGame.log exceeds this. A runaway assert cascade can
                                 # reach 474 MB, at which point the poll loop's whole-file re-read
                                 # stops progressing and the run holds the box lock forever.
  [int]$LockTimeoutSec = 1800,   # how long to WAIT for the box before giving up (see the lock below)
  [switch]$NoLock,               # ⛔ escape hatch only. Skips the box lock; two harnesses then kill
                                 # each other's runs. Do not use it to "get past" a busy box.
  [switch]$SkipTrainingTip,      # opt IN to the TRAINING-TIP BYPASS (BRN_SKIP_TRAINING_TIP=1). OFF
                                 # by default and CLEARED every run, on exactly the -StartEvent
                                 # grounds: it is a CAPABILITY (it changes what the game DOES at a
                                 # junction), not an instrument. See the banner below.
  [switch]$ShowtimeIgnoreProgression, # opt IN to BRN_SHOWTIME_IGNORE_PROGRESSION=1 -- stop the
                                 # console's OWN road-rules gate refusing the showtime gesture.
                                 # (Off by default, CLEARED every run: it changes what the game DOES.)
                                 # ShouldStartShowtimeMode @0x82356B18 refuses offline unless
                                 # AreRoadRulesAvailable @0x82311520 is true (>= 4 medals from the
                                 # start, or one ruled road). That is CORRECT console behaviour --
                                 # but NEITHER term is reachable on this build: medals come from
                                 # finishing an offline event (which does not complete yet) and the
                                 # two roads-ruled tallies have no writer at all. Without this, the
                                 # showtime SCORE half of item 6 cannot be observed at all.
                                 # The flag is scoped to that ONE decision -- it forges no
                                 # progression value, so completion %, the unlock predicates and the
                                 # save are untouched, and the nine gates below the road-rules test
                                 # still run. The game logs one line saying it was used.
                                 # DELETE-WHEN an offline event can award a medal.
  [switch]$EventFsm,             # opt IN to the EVENT-HUD FSM HOP (BRN_EVENT_FSM=1). While the
                                 # PRE_FLY_BY/RACE_MAIN bring-up is verified, the exe gates the
                                 # console's action-23 RunFsm("BRNEVENTFSM") post behind this env
                                 # var (GameBridgeGameStateToX_EventFlowGuiEvents.cpp, [FLAG PC
                                 # bring-up]); without it the HUD stays in FBURN_MAIN through an
                                 # event. CAPABILITY discipline: off by default, cleared every
                                 # run. DELETE-WHEN the exe-side gate is deleted (then the hop is
                                 # unconditional console behaviour and this switch dies with it).
  [string]$DiagEnv     = ""      # ⭐ PASS ENGINE DIAG VARS THROUGH THE CLEAR. "A=1,B=2" (or bare
                                 # "A,B", which means =1). The clearing loop below wipes ALL 49 BRN_*
                                 # engine variables on purpose, so exporting one in the parent shell
                                 # CANNOT reach the game -- measured 2026-08-29: a control run set
                                 # BRN_SHOWTIME_WATCH and BRN_TRAFFIC_DIAG and the game saw NEITHER,
                                 # which reads in the log EXACTLY like a dead probe. This applies them
                                 # AFTER the clear and ECHOES them, so a run carrying an instrument
                                 # still says so. INSTRUMENTS ONLY: a CAPABILITY (something that
                                 # changes what the game DOES) gets its own named switch, exactly as
                                 # -StartEvent / -Showtime / -EventFsm do.
)
$ErrorActionPreference = 'Stop'

$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$exe  = Join-Path $root "build\game\Burnout_PC.exe"
$log  = Join-Path $root "build\game\BrnGame.log"
if ($OutDir   -eq "") { $OutDir   = Join-Path $root ("scratch\flow_run\" + (Get-Date).ToString('yyyyMMdd_HHmmss')) }
# ⛔ PER-RUN BY DEFAULT (2026-08-29). This used to default to a SHARED scratch\flow_frames,
# which the block further down EMPTIES at the start of every run -- so each run destroyed the
# previous run's evidence. Measured: a wave produced 420 frames proving a slow-motion result and
# the next run wiped them; only the two artefacts it had copied out by hand survived, and it had
# to say so in its own report.
# ⭐ The emptying itself is CORRECT and stays: a stale bitmap outranks a fresh one by name, and a
# mixed directory once let a frame gate score four stale frames out of six. The fix is not to stop
# clearing, it is to stop SHARING -- a fresh per-run directory is empty by construction, so both
# properties hold at once, and the frames land beside that run's own log, summary and marks.
# Disk stays bounded because dumping is opt-in (-Frames): a default run writes none.
if ($FrameDir -eq "") { $FrameDir = Join-Path $OutDir "frames" }

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

# ⛔⛔ SERIALIZE THE BOX -- ONE HARNESS AT A TIME (traffic-verify wave, 2026-08-27).
# Taken BEFORE the kill sweep below, because the kill is the destructive act: this script ends
# every Burnout_PC on the box and deletes BrnGame.log, so a concurrent harness's run is not merely
# slowed, it is destroyed -- and the victim reads the damage as a crash in the build under test.
# ⭐ Same lesson as the stale-instance block below, one level up: there the hazard is leftovers of
# THIS script, here it is one of the other eight scripts in this directory that touch the game.
# The measured history, and the release-on-exit semantics, live in _box_lock.ps1.
. "$PSScriptRoot\_box_lock.ps1"
Enter-BoxLock -TimeoutSec $LockTimeoutSec -NoLock:$NoLock -Label "flow_run"

# ⛔⛔ KILL STALE INSTANCES **AND VERIFY THE KILL** (pauseresume wave, 2026-08-27).
# This used to be a single fire-and-forget `Stop-Process -Force`, and it silently FAILS on this
# process often enough to matter: every run ends `EXIT harness-stop (process was still alive)`,
# so a survivor is not an edge case, it is the normal exit path. Two runs of this wave were
# thrown away to it -- with two and then three game instances sharing the box the flow never
# reached the flyby inside 275 s, and the summary reported `phase=BOOT` with `asserts=0`, which
# reads exactly like a boot REGRESSION in the build under test. ⭐ A measurement harness that
# can be starved by its own leftovers reports the starvation as a property of the game. Escalate
# to `taskkill /T` and REFUSE TO RUN rather than produce a quietly incomparable run.
$staleTries = 0
while ($true) {
  $stale = @(Get-Process Burnout_PC -ErrorAction SilentlyContinue)
  if ($stale.Count -eq 0) { break }
  $staleTries++
  if ($staleTries -gt 5) {
    Write-Host "[flow] FAIL: $($stale.Count) stale Burnout_PC process(es) survived 5 kill attempts."
    Write-Host "[flow]       Refusing to run: a second instance starves the flow and the summary"
    Write-Host "[flow]       would blame the build. Kill them by hand and re-run."
    exit 1
  }
  Write-Host "[flow] killing $($stale.Count) stale Burnout_PC process(es) (attempt $staleTries)"
  foreach ($sp in $stale) {
    Stop-Process -Id $sp.Id -Force -ErrorAction SilentlyContinue
    if ($staleTries -ge 2) { & taskkill /PID $sp.Id /F /T *>$null }
  }
  Start-Sleep -Seconds 2
}
Start-Sleep -Seconds 1
# ⭐ EXE PROVENANCE (2026-08-28). `build/game/Burnout_PC.exe` is a CONTESTED path: waves build in
# isolated shadow roots and stage their exe here, so the binary at this path is routinely SOMEONE
# ELSE'S TREE. That bit three times in one day -- a wave found no exe at all and staged its own, two
# other waves then measured against it, and a third had its exe replaced mid-session. A measurement
# taken against the wrong binary is the worst kind: reproducible and NOT attributable.
# compile_exe.py now stamps <exe>.provenance.json at link time; print it so every run says, in its
# own log, which build produced the numbers. No stamp = an exe nobody can vouch for -- say so rather
# than staying silent about it.
$provPath = "$exe.provenance.json"
if (Test-Path $provPath) {
  try {
    $prov = Get-Content $provPath -Raw | ConvertFrom-Json
    Write-Host ("[flow] exe {0}  b5={1}{2}  root={3}" -f `
      $prov.exe_sha256.Substring(0,12), $prov.b5_head.Substring(0,8),
      $(if ($prov.b5_dirty) { "+dirty" } else { "" }), $prov.built_from_root)
    if ($prov.built_from_root -ne $root) {
      Write-Host "[flow] ⚠ THIS EXE WAS BUILT IN ANOTHER TREE -- your numbers are not attributable to this checkout."
    }
  } catch { Write-Host "[flow] exe provenance unreadable: $provPath" }
} else {
  Write-Host "[flow] ⚠ exe has NO provenance stamp -- it predates stamping or was staged by hand."
  Write-Host "[flow]   Rebuild before trusting any measurement from this run."
}

if (Test-Path $log) { Remove-Item $log -Force }

# --- environment: a DEFAULT run, with every override explicitly cleared -------------------
$env:BRN_INPUT_ALLOW_BACKGROUND = "1"

# ⛔⛔ THE ASSERT RELEASE HAS TO BE AN EVENT, NOT A KEYSTROKE (traffic-verify wave, 2026-08-27).
# The poll loop below already TRIES to dismiss every assert, by tapping END three times. That tap
# goes through keybd_event, which delivers to the FOCUSED window -- so on an unattended box, where
# the game may not hold focus, the harness's own dismissal silently does nothing. The run then
# freezes: process alive, log frozen at the assert, and the summary blames the build.
# It cost three runs across two waves on 2026-08-27, all at the junkyard->driving handover
# (BrnGuiCache_wH3b.cpp:84 via GuiCache::GetProfileEventDisplayInfo <- SatNavRenderer::RecvEvent).
#
# CgsAssertManager.cpp:288-303 provides the supported way out: with BRN_INPUT_ALLOW_BACKGROUND set
# (it is, one line above), the assert screen also releases on the named event
# "Local\BurnoutPC_Assert_Release". The game OPENS that event -- it never creates it -- so it must
# exist BEFORE launch, and the handle must stay alive for the whole run or the GC closes it.
#
# ⭐ DEFAULT IS AutoReset AND ONE SET PER DETECTED ASSERT, deliberately. That mirrors the existing
# END-tap intent exactly (dismiss the asserts we saw) and so KEEPS `asserts=` a real measurement.
# -ReleaseAsserts switches to ManualReset + a single Set, which leaves the gate permanently open:
# necessary for the open-world storm, but it releases asserts the loop never counted, which is why
# it is opt-in and why the summary marks the run.
$assertEventMode = if ($ReleaseAsserts) { [System.Threading.EventResetMode]::ManualReset }
                   else                 { [System.Threading.EventResetMode]::AutoReset }
$evAssertRelease = New-Object System.Threading.EventWaitHandle(
                     $false, $assertEventMode, "Local\BurnoutPC_Assert_Release")
if ($ReleaseAsserts) {
  $evAssertRelease.Set() | Out-Null
  Write-Host "[flow] ⚠️ -ReleaseAsserts: assert gate held OPEN for the whole run -- 'asserts=' is NOT comparable with a default run"
}
# ⚠️ BRN_MOTION_PROBE IS IN THIS LIST DELIBERATELY (added 2026-08-15, walls leg 7).  It was the one
# probe env var this script neither set nor cleared, so a leftover `$env:BRN_MOTION_PROBE` from an
# earlier command in the same shell rode into the next run -- and that run then announced itself as
# a "DEFAULT run" while carrying an unrequested instrument.  That is a golden-gate hazard: the
# goldens are meant to be byte-identical to a probe-free build.  Opt IN with -MotionProbe instead.
# ✅ BRN_ENABLE_CRASH_ENTRY WAS IN THIS LIST FROM 2026-08-25 AND IS **DELETED** (2026-08-27).
# It was never an instrument, it was a CAPABILITY -- with it clear the game could not enter the
# crash state at all. Its last surviving reason (a crash cost the player their HUD for the
# session, because BrnGui::CrashedHudState was a hollow shell that never sent END_CRASH) fell
# with the endcrash wave, so crash entry is now unconditional in the exe and there is nothing
# left here to set or clear. -CrashEntry is gone with it; a script still passing it will fail
# loudly on the unknown parameter rather than silently produce a run that is not what it says.
# ⛔ BRN_CRASH_PLAYER JOINED THIS LIST 2026-08-26. It was the one crash-chain knob the script
# neither set nor cleared, so a leftover shell variable could make a run that calls itself DEFAULT
# fire a scripted player crash -- exactly the hazard the BRN_MOTION_PROBE note above describes, on
# the one variable whose consequence is a pinned car rather than an extra log family.
# ⛔⛔ BRN_START_EVENT IS IN THIS LIST FOR EXACTLY THE SAME REASON (2026-08-26, stunt-races wave D).
# It is the event-start hook: with it set the game calls GameStateModule::
# HarnessInjectEventStartBringUp (GameStateModule_gUI_00.cpp), which drives StartModeAtLights
# directly (mechanism SPIN_WHEELS_AT_LIGHTS, bypassing the 0.35 s gesture hold) -- i.e. it
# STARTS A GAME MODE -- as soon as the player car is standing in a traffic-light region.  A run
# carrying it is not a free-burn run at all, so a leftover shell variable would make a run that
# calls itself DEFAULT start a stunt race on its own, and every golden and every phase mark in this
# script describes free burn.  That is the SEVEN-NON-COMPARABLE-RUNS failure again (the DIAGENV
# banner below), only louder, because this one changes what the game DOES rather than what it says.
# Opt IN with -StartEvent.
# ⭐ BRN_DEFORM_TRACE JOINED THIS LIST 2026-08-27 (crashdeform wave), on the ordinary instrument
# grounds: it is a log family, it is opt-in, and a leftover shell variable must never ride into a
# run that then calls itself DEFAULT. Opt IN with -DeformTrace <period>.
# ⛔⛔ BRN_SKIP_TRAINING_TIP IS IN THIS LIST FOR THE BRN_START_EVENT REASON, NOT THE INSTRUMENT ONE.
# It makes the junction canEnter gate ignore a blocking training tip (GameStateModule_gSR_00.cpp's
# IsBlockingTrainingTipActiveForCanEnterGate), so with it set the "hold both triggers" start hint
# appears at a junction where the console would have suppressed it -- i.e. it changes what the game
# DOES and what the GUI SHOWS, not merely what the log says. A leftover shell variable would make a
# run that calls itself DEFAULT diverge from the console at every junction it visits, and no golden
# may be banked or gated through it. Opt IN with -SkipTrainingTip.
# ⛔⛔ BRN_EVENT_FSM is here for the same reason: it arms the event-HUD FSM hop (a CAPABILITY).
# ⛔⛔ THE DEFAULT-RUN GUARANTEE ONLY COVERS WHAT IS LISTED HERE (audited 2026-08-29).
# Measured: the engine reads 45 BRN_* variables and this list covered 14 of them -- so THIRTY-THREE
# instruments and capability switches could ride in from an earlier command in the same shell while
# the run announced itself as DEFAULT. Two of them change behaviour outright:
#   BRN_TRAFFIC_FAKE_SHOWTIME  -- silently makes a default run a SHOWTIME run (traffic ~95 -> ~167)
#   BRN_TRAFFIC_NO_JAM_NUKE    -- disables the jam relief valve
# and BRN_ASSERT_NO_SUPPRESS / BRN_CULL_OFF / BRN_IOBUF_ZERO / the shadow knobs all alter what is
# rendered or asserted. Goldens are meant to be byte-identical to a probe-free build, so a leftover
# here is a golden-gate hazard, not a nuisance -- the same reason BRN_MOTION_PROBE was added.
# ⚠️ BRN_INPUT_ALLOW_BACKGROUND is deliberately NOT cleared: this script sets it.
# ⭐ If you add a getenv("BRN_...") to the engine, add it here in the same change.
foreach ($v in @('BRN_RC_PROBE','BRN_DIRECTOR_TRACE','BRN_FORCE_DIRECTOR_CAMERA','BRN_WORLD_CAMFREE','BRN_MOTION_PROBE','BRN_TRICACHE_PROBE','BRN_TRACTION_PROBE','BRN_CRASH_PLAYER','BRN_START_EVENT','BRN_START_SHOWTIME','BRN_SHOWTIME_WATCH','BRN_DEFORM_TRACE','BRN_SKIP_TRAINING_TIP','BRN_EVENT_FSM','BRN_APT_LIFE','BRN_ASSERT_NO_SUPPRESS','BRN_CRASHCAM_DIAG','BRN_CULL_OFF','BRN_DOF_TRACE','BRN_DRIVETHRU_DIAG','BRN_ENGINE_PROBE','BRN_ENVMAP_DEBUG','BRN_GESTURE_DIAG','BRN_ICE_TIMESCALE_DIAG','BRN_ICE_TRACE','BRN_IOBUF_ZERO','BRN_JUNCTION_DIAG','BRN_MODEMGR_DIAG','BRN_POSTFX_CALIBRATION_TEST','BRN_POSTFX_CALIB_SCREEN_TEST','BRN_QUEUE_WATERMARK','BRN_SHADOW_BIAS','BRN_SHADOW_CULL','BRN_SHADOW_FALLBACKVS','BRN_SHADOW_FORCECWE','BRN_SHADOW_SLOPEBIAS','BRN_SHADOW_ZALWAYS','BRN_SLOMO_DIAG','BRN_SLOMO_LATCH_SKIP','BRN_TRAFFIC_DIAG','BRN_TRAFFIC_FAKE_SHOWTIME','BRN_TRAFFIC_NO_JAM_NUKE','BRN_SHOWTIME_IGNORE_PROGRESSION','BRN_TYRE_PROBE','BRN_WALL_PROBE','BRN_WHEEL_DIAG','BRN_WHEEL_ZALWAYS','BRN_FRAME_DUMP_ARM','BRN_FRAME_DUMP_MAX')) {
  # ⚠️ SAY SO when we discard something the caller deliberately set. Wiping is right -- it is what
  # makes a DEFAULT run default -- but doing it SILENTLY turns a deliberate `$env:BRN_X=1` into a
  # measurement of nothing. That cost a wave its first instrumented run: it exported BRN_MODEMGR_DIAG
  # in the shell, the wipe ate it, and the run produced no rungs with no explanation.
  if (Test-Path "Env:\$v") {
    Write-Host "[flow] NOTE: $v was set in the environment and has been CLEARED (this is a DEFAULT run)."
    Write-Host "[flow]       To pass an engine diagnostic THROUGH the wipe, use:  -DiagEnv $v=1"
  }
  Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}

# ⭐ -DiagEnv: re-apply the caller's INSTRUMENT variables AFTER the wipe above (see the
# parameter's banner for why exporting them in the parent shell cannot work). Parsed strictly so a
# typo FAILS the run instead of silently measuring nothing -- an unset probe variable and a broken
# probe are indistinguishable in the log, which is the whole failure this switch exists to stop.
$diagEnvApplied = @()
if (-not [string]::IsNullOrWhiteSpace($DiagEnv)) {
  foreach ($lsPart in $DiagEnv.Split(',')) {
    $lsTrim = $lsPart.Trim()
    if ($lsTrim -eq "") { continue }
    $lsName = $lsTrim
    $lsValue = "1"
    $liEq = $lsTrim.IndexOf('=')
    if ($liEq -ge 0) {
      $lsName  = $lsTrim.Substring(0, $liEq).Trim()
      $lsValue = $lsTrim.Substring($liEq + 1).Trim()
    }
    if ($lsName -notmatch '^BRN_[A-Z0-9_]+$') {
      Write-Host "[flow] FAIL: -DiagEnv name '$lsName' is not a BRN_* engine variable."
      exit 1
    }
    Set-Item -Path ("Env:\" + $lsName) -Value $lsValue
    $diagEnvApplied += ("{0}={1}" -f $lsName, $lsValue)
  }
  Write-Host ("[flow] DIAG ENV applied after the clear: {0} -- NOT a default run." -f ($diagEnvApplied -join ' '))
}
if ($CrashPlayer -gt 0) {
  $env:BRN_CRASH_PLAYER = "$CrashPlayer"
  Write-Host "[flow] CRASH PLAYER armed: BRN_CRASH_PLAYER=$CrashPlayer (opt-in, an UpdateVehiclePhysics call index). NOT a default run -- the player car is crashed ONCE, deterministically."
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
# ⭐ [deform-trace] -- the per-frame deformation witness (crashdeform wave). Same opt-in discipline
# and the same CLEARED list as [tricache]/[traction] above, for the same golden-gate reason.
if ($DeformTrace -gt 0) {
  $env:BRN_DEFORM_TRACE = "$DeformTrace"
  Write-Host "[flow] DEFORM TRACE run: BRN_DEFORM_TRACE=$DeformTrace (opt-in, period in calls). NOT a default run -- do not gate goldens off this."
}
if (-not $MotionProbe -and $TriCacheProbe -le 0 -and $TractionProbe -le 0 -and $CrashPlayer -le 0 -and $DeformTrace -le 0 -and -not $StartEvent -and $Showtime -eq "" -and -not $SkipTrainingTip -and -not $EventFsm -and -not $ShowtimeIgnoreProgression) {
  Write-Host "[flow] DEFAULT run: BRN_WORLD_CAMFREE / FORCE_DIRECTOR_CAMERA / DIRECTOR_TRACE / RC_PROBE / MOTION_PROBE / TRICACHE_PROBE / TRACTION_PROBE / CRASH_PLAYER / DEFORM_TRACE / START_EVENT / START_SHOWTIME / SKIP_TRAINING_TIP / EVENT_FSM all cleared."
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
# ⚠️ Whether the LADDER below can see anything at all hangs on this one inherited variable -- see
# the ladder banner. Captured here, next to the collection that already records it.
$ladderDiag = (-not [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable('BRN_PROP_DIAG')))

# ⭐⭐ -StartEvent -- ARM THE EVENT-START HOOK (2026-08-26, stunt-races wave D).
#   `BRN_START_EVENT=1` is the game-side bring-up hook (NOT this script's -- it is
#   GameStateModule::HarnessInjectEventStartBringUp in GameStateModule_gUI_00.cpp, which drives
#   StartModeAtLights directly with mechanism SPIN_WHEELS_AT_LIGHTS, bypassing the 0.35 s
#   accel+brake hold; it fires only while the player car is inside a traffic-light region).
#   Standing in a junction is what -Teleport is for; this is what turns standing there
#   into a STARTED EVENT without a pad.
#   ⛔ IT IS A CAPABILITY, NOT AN INSTRUMENT, and it is in the CLEARED list above for that reason
#   (see the banner there). A run carrying it can leave free burn entirely, so it is never a
#   default run and no golden may be banked or gated through it.
#   ⚠️ IT IS NOT A SUBSTITUTE FOR STANDING IN A JUNCTION. The hook is gated on the light region,
#   so -StartEvent on a car parked at the junkyard does nothing at all and is indistinguishable in
#   the log from a broken hook. Pair it with -Drive -Teleport onto a junction (the usage line at
#   the top puts the car in stunt junction 480897) or the run answers no question.
# ⭐⭐⭐ -Showtime -- PRESS BOTH BUMPERS, FOR REAL (showtime S7b-a, 2026-08-27).
#   Two halves, and they are different things:
#     (a) the GESTURE. At DRIVING+<at> this script Set()s both shoulder channels for <holdSecs>.
#         That travels the ORDINARY input chain -- ConsumeHarnessAction rows 54/55 -> maActionInfo
#         -> GameStateModuleIO computes ControllerInput::mbCrashModePressed (+0x42) as the AND of
#         their held bits, exactly as it does for a pad. Nothing here writes a game-state flag.
#     (b) the GAME-SIDE STAND-IN. BRN_START_SHOWTIME=1 arms
#         GameStateModule::HarnessInjectShowtimeBringUp.
#         ✅ THAT HOOK IS GONE (showtime S7b-b, 2026-08-27). ShouldStartShowtimeMode @0x82356B18
#         and the DetectModeStarts else arm both landed, so the gesture now drives the CONSOLE's
#         own gate stack and BRN_START_SHOWTIME is INERT -- nothing reads it. It is still set and
#         still cleared below so an old run's summary line stays comparable; delete both when the
#         next person touches this block.
#   ⛔ A -Showtime RUN CAN STILL LEAVE FREE BURN (that is now the game working, not a hook), so
#   it is still not a default run and no golden may be banked or gated through it.
#   ⭐ WHAT THE CONSOLE GATE NOW WANTS, in refusal order (ShouldStartShowtimeMode):
#     road rules available (Profile medal count >= 4, or one ruled road) | no 2 s post-mode lockout
#     | no sim-timer request this frame | both bumpers | player car active | sim not paused | no
#     junkyard flow | any running mode is IN_PROGRESS | meShowtimeBehaviour != OFF | not already
#     in showtime -- then a 10 ms hold, then >= 10 m/s (or already crashing), then a 0.5 s intro
#     window that must end with the car having touched the ground.
#   A refused press prints ONE line: "[showtime] BOTH BUMPERS held, but ShouldStartShowtimeMode
#   @0x82356B18 refused: <reason>". Read it before concluding anything about the input path.
#   ⚠ A -Showtime run with no -Drive parks a stationary car; the console gate this stands in for
#   has a speed term, so pair it with -Drive if the question is about a moving entry.
$showtimeAt = -1.0; $showtimeHold = 5.0; $shouldersHeld = $false
if ($Showtime -ne "") {
  $parts = $Showtime -split ':'
  $showtimeAt = [double]::Parse($parts[0], [System.Globalization.CultureInfo]::InvariantCulture)
  if ($parts.Count -gt 1) { $showtimeHold = [double]::Parse($parts[1], [System.Globalization.CultureInfo]::InvariantCulture) }
  $env:BRN_START_SHOWTIME = "1"
  # The witness that answers "did the P6 bounce chain execute" -- gated on the REAL
  # mbPlayerCarInShowtime, so it cannot print unless the console chain put the car there.
  $env:BRN_SHOWTIME_WATCH = "1"
  Write-Host ("[flow] SHOWTIME armed: BOTH BUMPERS held from DRIVING+{0:f1}s for {1:f1}s, and" -f $showtimeAt, $showtimeHold)
  Write-Host "       BRN_START_SHOWTIME=1 (opt-in). NOT a default run -- the game may leave free burn."
  if (-not $Drive) {
    Write-Host "[flow] NOTE: -Showtime without -Drive -- the car will be stationary when the gesture"
    Write-Host "       fires. The console gate this stands in for has a speed term; pair with -Drive."
  }
}
if ($ShowtimeIgnoreProgression) {
  $env:BRN_SHOWTIME_IGNORE_PROGRESSION = "1"
  Write-Host "[flow] SHOWTIME PROGRESSION GATE IGNORED: BRN_SHOWTIME_IGNORE_PROGRESSION=1 (opt-in)."
  Write-Host "       The console's own AreRoadRulesAvailable @0x82311520 refusal is skipped for that"
  Write-Host "       ONE decision only -- no progression value is forged and the save is untouched."
  Write-Host "       NOT a default run and NOT comparable with one. Do not bank or gate goldens off it."
  if ($Showtime -eq "") {
    Write-Host "[flow] NOTE: -ShowtimeIgnoreProgression without -Showtime does nothing observable --"
    Write-Host "       the gate it opens is only reached while BOTH BUMPERS are held."
  }
}
if ($StartEvent) {
  $env:BRN_START_EVENT = "1"
  Write-Host "[flow] START EVENT armed: BRN_START_EVENT=1 (opt-in). NOT a default run -- the game"
  Write-Host "       may leave free burn and start a mode. Do not bank or gate goldens off this."
  if ($Teleport -eq "") {
    Write-Host "[flow] NOTE: -StartEvent without -Teleport -- the hook only fires inside a traffic-light"
    Write-Host "       region, and the drive start (junkyard exit, 2960.9/1.9/-1658.5) is 326 m from the"
    Write-Host "       nearest one. Nothing will fire unless the car is driven into a junction."
  }
  if (-not $ladderDiag) {
    Write-Host "[flow] WARNING: BRN_PROP_DIAG is NOT set, so the [evt-flow] ladder rungs cannot print"
    Write-Host "       (their producer is gated on it). The run still happens; the LADDER line will"
    Write-Host "       read BLIND, and an empty ladder proves NOTHING about the chain. Set it first:"
    Write-Host "       `$env:BRN_PROP_DIAG=1"
  }
}
$startEventText = '(not armed)'
if ($StartEvent) { $startEventText = 'BRN_START_EVENT=1' }

# ⭐⭐ -SkipTrainingTip -- IGNORE A BLOCKING TRAINING TIP AT THE JUNCTION canEnter GATE.
#   `BRN_SKIP_TRAINING_TIP=1` is a game-side bring-up flag (NOT this script's -- it is
#   IsBlockingTrainingTipActiveForCanEnterGate in GameStateModule_gSR_00.cpp, wrapping the tip
#   term of the TWO canEnter computations inside CheckIfPlayerIsAtJunctionWithAnEvent).
#   The boot tutorial tip ("Find an Auto-Repair shop...") is a MODAL type, so the console's gate
#   holds mbCanEnterEvent at 0 for minutes -- most of a 275 s run -- and the junction start-hint
#   glyphs ("hold both triggers") never appear even when the car is standing in the right place.
#   With this armed the hint chain can be exercised on the harness's own timescale.
#   ⛔ IT IS A CAPABILITY, NOT AN INSTRUMENT, and it is in the CLEARED list above for that reason
#   (see the banner there). It changes what the GUI SHOWS at every junction the run visits, so it
#   is never a default run and no golden may be banked or gated through it.
#   ⚠️ IT DOES NOT START ANYTHING. Only canEnter is bypassed; ShouldStartSnapRaceMode's own
#   blocking-tip pre-gate is deliberately untouched, so the 0.35 s accel+brake hold still refuses
#   while a tip is up. Starting an event out of a tip-blocked state is -StartEvent's job.
#   ⚠️ IT IS NOT A SUBSTITUTE FOR STANDING IN A JUNCTION -- same as -StartEvent: pair it with
#   -Drive -Teleport onto a junction or the run answers no question.
if ($SkipTrainingTip) {
  $env:BRN_SKIP_TRAINING_TIP = "1"
  Write-Host "[flow] SKIP TRAINING TIP armed: BRN_SKIP_TRAINING_TIP=1 (opt-in). NOT a default run --"
  Write-Host "       the junction canEnter gate ignores a blocking tip, so the start hint can show"
  Write-Host "       where the console would suppress it. Do not bank or gate goldens off this."
  if ($Teleport -eq "") {
    Write-Host "[flow] NOTE: -SkipTrainingTip without -Teleport -- the gate it unblocks is only reached"
    Write-Host "       inside a traffic-light region, and the drive start (junkyard exit) is 326 m from"
    Write-Host "       the nearest one. Nothing will change unless the car is driven into a junction."
  }
  if (-not $ladderDiag) {
    Write-Host "[flow] WARNING: BRN_PROP_DIAG is NOT set, so neither the [snap] junction rungs nor the"
    Write-Host "       one-shot '[snap] BRN_SKIP_TRAINING_TIP ... IGNORED' line can print (their"
    Write-Host "       producer is gated on it). The run still happens, but the log will not show"
    Write-Host "       whether the flag suppressed anything. Set it first: `$env:BRN_PROP_DIAG=1"
  }
}
$skipTipText = '(not armed)'
if ($SkipTrainingTip) { $skipTipText = 'BRN_SKIP_TRAINING_TIP=1' }

# ⭐⭐ -EventFsm (2026-08-27, stunt-race UI wave). Arms the console's event-HUD FSM hop: on game
#   action 23 the bridge posts RunFsm("BRNEVENTFSM") and the HUD flow leaves FBURN_MAIN for
#   PRE_FLY_BY -> (BF_PROCEED) -> RACE_MAIN. The exe gates that post behind BRN_EVENT_FSM while
#   the two destination states are being brought up; without this switch an event runs under the
#   freeburn HUD. CAPABILITY discipline: cleared list above, never a default run.
#   DELETE-WHEN the exe-side gate dies (EventFlowGuiEvents.cpp [FLAG PC bring-up]).
if ($EventFsm) {
  $env:BRN_EVENT_FSM = "1"
  Write-Host "[flow] EVENT-HUD FSM armed: BRN_EVENT_FSM=1 (opt-in). NOT a default run -- on mode"
  Write-Host "       start the HUD flow hops FBURN_MAIN -> PRE_FLY_BY -> RACE_MAIN. Watch for"
  Write-Host "       [HudFlow] lines; a LogUnreconstructedState hit here is a REGRESSION now."
}
$eventFsmText = '(not armed)'
if ($EventFsm) { $eventFsmText = 'BRN_EVENT_FSM=1' }

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
  # ⛔⛔ FREE-SPACE GUARD (2026-08-29). A frame dump can be ENORMOUS: every-2-presents for 130 s
  # measured 16 GB, and a wave had to prune 5.2 GB after D: hit 100% mid-session. This box runs at
  # ~1% free with 1.8 TB of the owner's own content on it, so a dump can fill the volume DURING a
  # measurement -- which does not just lose the run, it can break every other wave's build and the
  # shared repo's working tree at the same time.
  # ⭐ Refuse up front instead: a run that declines to start is recoverable, a full disk mid-write is
  # not. -MinFreeGB overrides for a deliberately large capture.
  $drv = (Get-Item $FrameDir -ErrorAction SilentlyContinue)
  $root = if ($drv) { $drv.PSDrive.Name } else { (Split-Path -Qualifier $FrameDir).TrimEnd(':') }
  $free = try { (Get-PSDrive $root -ErrorAction Stop).Free / 1GB } catch { $null }
  if ($free -ne $null -and $free -lt $MinFreeGB) {
    Write-Host ("[flow] FAIL: only {0:f1} GB free on {1}: -- refusing to start a FRAME DUMP." -f $free, $root)
    Write-Host  "[flow]       A dump can reach 16 GB; filling the volume mid-run can break other"
    Write-Host  "[flow]       waves' builds and the shared working tree, not just this measurement."
    Write-Host ("[flow]       Free some space, or pass -MinFreeGB below {0:f0} if you accept the risk." -f $free)
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

# The offline-pause channel (action 46 == KI_ACTION_PAUSE_MAIN_MAP). AUTO-RESET, like the four
# menu channels: this is a TAP, not a hold. Created unconditionally so the game always finds it;
# a channel never Set() is a key never pressed.
$evPauseMap = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::AutoReset, "Local\BurnoutPC_Input_PauseMap")

# ⛔⛔ THE RESUME CHANNEL IS *Stop*, NOT *Accept* -- and it was Accept until 2026-08-28, which is
# why -UnpauseAt silently stopped working and every -PauseAt run since the input-vocabulary
# repair has been a ONE-WAY pause that ran to the harness timeout still frozen.
#   The map's own exit arm is CrashNavMapMain::HandleCrashNavInputPressed @0x824CCAE8, whose two
#   cases are 0x2D (45 GUI_START) and 0x32 (50 GUI_CANCEL) -- it deliberately does NOT take
#   49 GUI_SELECT, because on the map screen A/Select PICKS AN ICON. That arm is faithful and is
#   not the bug.
#   The bug was on this side: b5-decomp d91d7949 ("input vocabulary repair") moved the harness's
#   Accept channel from action 45 to its correct 49 GUI_SELECT, and this block kept tapping
#   Accept. So the resume tap became a 49 the map is written to ignore. The channel lookup in
#   CgsInputPadsPC is BY ACTION ID, so the fix is to tap the channel that carries 50 -- Stop
#   (Escape / pad-B), the canonical back-out. Tapping Start (45) exits too; Accept (49) never will.
# ⭐ THE LESSON, again: a vocabulary repair is a repair of a SHARED table. Grep every consumer of
#   the old id -- this exit arm was written three days before the repair and nothing re-ran it.
$evStop = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::AutoReset, "Local\BurnoutPC_Input_Stop")

# ⭐ THE OTHER OFFLINE PAUSE. The console has TWO, and they are different screens:
#   action 46 GUI_BACK  -> InGame::PauseGame(true, FALSE) -> OpenMainMap()       -> CN_MAP_MAIN
#   action 45 GUI_START -> InGame::PauseGame(true, TRUE)  -> OpenDriverDetails() -> CN_D_DETAIL
# Both post the same deactivate pair, so both stop the sim; only the screen differs.
# -PauseTarget picks which one -PauseAt taps. 'driver' is the START button, i.e. what a
# player actually presses to pause, and the screen that DRAWS (CN_MAP_MAIN's base half is
# still parked).
$evStart = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::AutoReset, "Local\BurnoutPC_Input_Start")

# ⭐ THE PAUSE/RESUME SCHEDULES. -PauseAt / -UnpauseAt are COMMA-SEPARATED second marks on the
# DRIVING time base, so one run can exercise the pause REPEATEDLY -- which is the only way to
# show a resume is durable rather than lucky once. Entries are sorted and each fires once.
function Parse-TapSchedule([string]$lsSpec, [string]$lsName) {
  if ([string]::IsNullOrWhiteSpace($lsSpec)) { return @() }
  $lResult = @()
  foreach ($lsPart in $lsSpec.Split(',')) {
    $lsTrim = $lsPart.Trim()
    if ($lsTrim -eq "") { continue }
    $lfValue = 0.0
    if (-not [double]::TryParse($lsTrim, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$lfValue)) {
      Write-Host "[flow] FAIL: -$lsName entry '$lsTrim' is not a number."; exit 1
    }
    if ($lfValue -lt 0) { continue }
    $lResult += $lfValue
  }
  return @($lResult | Sort-Object)
}

# ⭐ THE SINGLE-BUMPER SCHEDULE. Entries are "<sec>:<L|R>[:<holdSec>]" on the DRIVING time base.
# Parsed here (not in the poll loop) so a typo fails the run at once instead of silently never
# pressing anything -- a channel that is never Set() is indistinguishable in the log from a dead
# game-side hook, which is the exact failure mode the pause campaign kept hitting.
function Parse-ShoulderSchedule([string]$lsSpec) {
  if ([string]::IsNullOrWhiteSpace($lsSpec)) { return @() }
  $lResult = @()
  foreach ($lsPart in $lsSpec.Split(',')) {
    $lsTrim = $lsPart.Trim()
    if ($lsTrim -eq "") { continue }
    $laFields = $lsTrim.Split(':')
    if ($laFields.Count -lt 2 -or $laFields.Count -gt 3) {
      Write-Host "[flow] FAIL: -ShoulderAt entry '$lsTrim' is not <sec>:<L|R>[:<holdSec>]."; exit 1
    }
    $lfAt = 0.0
    if (-not [double]::TryParse($laFields[0].Trim(), [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$lfAt)) {
      Write-Host "[flow] FAIL: -ShoulderAt time '$($laFields[0])' is not a number."; exit 1
    }
    $lsSide = $laFields[1].Trim().ToUpperInvariant()
    if ($lsSide -ne 'L' -and $lsSide -ne 'R') {
      Write-Host "[flow] FAIL: -ShoulderAt side '$($laFields[1])' is not L or R."; exit 1
    }
    $lfHold = 1.5
    if ($laFields.Count -eq 3 -and
        -not [double]::TryParse($laFields[2].Trim(), [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$lfHold)) {
      Write-Host "[flow] FAIL: -ShoulderAt hold '$($laFields[2])' is not a number."; exit 1
    }
    $lResult += [pscustomobject]@{ At = $lfAt; Side = $lsSide; Hold = $lfHold }
  }
  return @($lResult | Sort-Object At)
}
$script:shoulderTaps = Parse-ShoulderSchedule $ShoulderAt
$script:shoulderDown = ''            # '' | 'L' | 'R' -- which single bumper is currently HELD
if ($script:shoulderTaps.Count -gt 0) {
  if ($Showtime -ne "") {
    Write-Host "[flow] FAIL: -ShoulderAt and -Showtime both drive rows 54/55. Use one or the other."; exit 1
  }
  Write-Host ("[flow] BUMPER schedule: {0} press(es) -- {1}" -f $script:shoulderTaps.Count,
              (($script:shoulderTaps | ForEach-Object { "{0}B@DRIVING+{1:f1}s for {2:f1}s" -f $_.Side, $_.At, $_.Hold }) -join ', '))
}
$script:pauseTimes   = Parse-TapSchedule $PauseAt   'PauseAt'
$script:unpauseTimes = Parse-TapSchedule $UnpauseAt 'UnpauseAt'
$script:pauseNext    = 0
$script:unpauseNext  = 0
if ($script:pauseTimes.Count -gt 0) {
  Write-Host ("[flow] PAUSE schedule: {0} tap(s) at DRIVING+[{1}]s; UNPAUSE: {2} tap(s) at DRIVING+[{3}]s" -f `
    $script:pauseTimes.Count, ($script:pauseTimes -join ','), $script:unpauseTimes.Count, ($script:unpauseTimes -join ','))
}

# ⭐ THE DRIVING CHANNELS -- MANUAL-RESET (see the banner).  Created unconditionally so the game
#   always finds them; a channel that is never Set() is a control that is never pressed, which is
#   exactly the "resting car undisturbed" case.  Named after the EGameInputActions slot each one
#   fills, so the game side's switch and this list can be diffed by eye.
$evAccel = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::ManualReset, "Local\BurnoutPC_Input_Accelerate")
$evBrake = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::ManualReset, "Local\BurnoutPC_Input_Brake")
$evHandB = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::ManualReset, "Local\BurnoutPC_Input_HandBrake")
$evStrL  = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::ManualReset, "Local\BurnoutPC_Input_SteerLeft")
$evStrR  = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::ManualReset, "Local\BurnoutPC_Input_SteerRight")
# ⭐⭐ THE TWO SHOULDER CHANNELS (showtime S7b-a, 2026-08-27).  MANUAL-RESET, i.e. a HOLD, because
#   ControllerInput::mbCrashModePressed (+0x42) is `(row 54 HELD) && (row 55 HELD)` -- the game samples
#   BOTH at once, so a tap channel cannot express the gesture.  Created unconditionally, like the five
#   above; never Set() unless -Showtime asks for it.
$evShldL = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::ManualReset, "Local\BurnoutPC_Input_ShoulderL")
$evShldR = New-Object System.Threading.EventWaitHandle($false, [System.Threading.EventResetMode]::ManualReset, "Local\BurnoutPC_Input_ShoulderR")
foreach ($e in @($evAccel,$evBrake,$evHandB,$evStrL,$evStrR,$evShldL,$evShldR)) { $e.Reset() | Out-Null }

# ⛔⛔ RELEASE THE HOLDS ON A FAILURE PATH TOO (showtime cross-run hazard, 2026-08-29).
#   These seven are SESSION-GLOBAL manual-reset events: signalled IS a hold, and it survives this
#   process. The normal path clears them after the poll loop, but $ErrorActionPreference is 'Stop',
#   so ANY terminating error between a Set() and that line would leave a button held down for the
#   next harness -- and LB+RB held tips the pause screen into CN_SETTINGS, an empty state shell
#   that soft-locks and looks exactly like the game dying (measured by the pause wave, which is
#   how this was found). A `trap` runs on the way out of a terminating error, which is precisely
#   the gap; the box lock's own release covers the kill/Ctrl+C case for the NEXT run.
trap {
  foreach ($e in @($evAccel,$evBrake,$evHandB,$evStrL,$evStrR,$evShldL,$evShldR)) {
    try { $e.Reset() | Out-Null } catch { }
  }
  Write-Host "[flow] terminating error -- all seven input holds released before rethrow."
  break
}

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
  @('strfin',   'signalling StreamingFinished'),
  # ⛔⛔ THE RETURNING-PLAYER PATH (2026-08-28). Profile saving landed on 2026-08-27, and the
  #   moment a Profile.sav exists the game takes a DIFFERENT boot path.
  #   ⛔ CORRECTED 2026-08-28: an earlier version of this note said the junkyard flow is "skipped
  #   by design". IT IS NOT -- that is the DEFECT, measured. The returning path ENTERS the junkyard
  #   and never LEAVES it: the entry's completion gate is IsNewProfileIntroActive(), a
  #   new-profile-only signal a returning boot never raises, so the exit reset never runs and
  #   RaceCarEntityModule::mbInCarSelectScreen stays TRUE all run. That blocks BOTH ignition arms
  #   of UpdateEngineState @0x822A4F50 (the console's own "the podium never cranks" rule), so the
  #   engine never starts and no throttle can move the car. The owner's description of what they
  #   saw -- "as if we controlled the car, but inside the junkyard, never moving" -- was LITERALLY
  #   accurate. The cues below are still correct and still needed; only the explanation was wrong.
  #   MEASURED: on that path 'Entering Car Select' and 'signalling StreamingFinished' fire ZERO
  #   times, so the CARSELECT->DRIVING promotion below could never happen -- and because the
  #   throttle is gated on `$phase -eq 'DRIVING'`, **-Drive silently did nothing and the car sat
  #   in the junkyard for the whole run.** A landed FEATURE broke the harness, and the harness
  #   reported it as an ordinary quiet run.
  #   ⭐ 'newprof' is the DISCRIMINATOR, not a milestone: the game prints isNewProfile=1/0 before
  #   either path diverges (line ~963 fresh, ~850 returning, vs the gameplay cue at ~1024/1045).
  #   ⚠️ 'ingame' MUST NOT promote on the fresh path: measured, it fires at line 1045 there --
  #   BEFORE car select at 4458 -- so promoting on it unconditionally would hold the throttle
  #   down during boot and car select. It is only the gameplay entry when there is no car select.
  @('newprof',  'isNewProfile=0'),
  @('ingame',   'InGame: OnEnter -> GUI FSM stage 5'),
  # ⭐⭐ 2026-08-28 (returning-player wave). The START-OF-GAME JUNKYARD ENTRY actually
  #   COMPLETING. Before this wave it could only complete on a NEW profile, so a returning boot
  #   never reached car select and the 'newprof'+'ingame' fallback above was the only way to
  #   DRIVING. With the entry fixed, a returning boot goes junkyard -> car select -> accept ->
  #   exit, exactly like a fresh one -- and the fallback would then FIRE FIRST (at 'ingame',
  #   ~3500 log lines before car select), stop the Accept pump, and park the run at car select
  #   for ever with the throttle held. This cue is what tells the two apart: it is printed by
  #   CarSelectManager::StartTransitionInState, i.e. the moment the entry completes.
  @('jystart',  '=== CarSelectManager: Transition In \[Start\]')
)

# ⭐⭐ THE EVENT-START LADDER (2026-08-26, stunt-races wave D).  Five RUNGS between "the car is
#   standing in a junction" and "the event is running", each one a line the game prints when it
#   gets that far.  The whole point is that a run summary answers HOW FAR THE CHAIN GOT rather
#   than pass/fail: the chain has five independent producers and any of them can be the hole.
#   Rungs are ordinary cues, so each one is timestamped and frame-anchored like every flow mark --
#   `e-junc 214.3s frame=bb_000642.bmp` names the bitmap to open to SEE the junction banner.
#
#   ⚠️ 'grounded' vs 'contract' IS THE HONEST PART, and it exists because of this file's oldest
#   lesson (the 'exitst' banner above): a cue that matches nothing because NOTHING EVER PRINTS IT
#   reads exactly like a chain that stalled, and that misread is a reported regression.  So:
#     grounded  the emitter is IN THE TREE, IN THE BUILD, and REACHED.  Checked all three, not
#               just the first: a log line in an unmounted TU, or in a mounted one nothing calls,
#               is exactly as silent as a line that does not exist.
#     contract  NO producer prints this yet -- it is the text the producer is ASKED to print.
#               A '(never)' on one of these is NOT evidence about the game.  It is marked as such
#               in marks.txt rather than left to be misread.
#   Grounded rungs, all from GameBridgeGameStateToX_EventFlowGuiEvents.cpp (the action -> GUI
#   translation seam): action 201 -> gui 311 (:454), action 23 -> gui 93 (:607), action 47 ->
#   gui 234 (:631).  That TU is mounted (build_game_exe.bat:4282) and reached -- the `default:`
#   arm of TranslateGameActionsToGuiEvents calls into it
#   (GameBridgeGameStateToX_StuntGuiEvents.cpp:404).  Re-check those three facts, not just the
#   text, if a rung ever goes quiet.
#   Contract rungs, and the exact text asked for:
#     e-case20  "[start] event 20 ..."  -- the case-20 arm's OWN lines in
#               GameStateModule_gUI_00.cpp: "[start] event 20 -> StartGameMode mode=" (:917) on
#               fire and "[start] event 20 IGNORED -- mpCurrentGameMode is live" (:854) on the
#               reject twin; both gated on gpDebugPrint only, so they print even without
#               BRN_PROP_DIAG. (The BRN_START_EVENT hook itself bypasses this arm -- it drives
#               StartModeAtLights directly -- so this rung fires on the GESTURE/event path.)
#     e-inprog  "... E_GMS_IN_PROGRESS"  -- the enum name spelled out.  No log line in the tree
#               contains that token today, so it cannot false-positive; nothing else prints it.
#
#   ⛔⛔ THE LADDER IS BLIND WITHOUT BRN_PROP_DIAG.  Every [evt-flow] line is guarded by
#   `static const bool sbDiag = (getenv("BRN_PROP_DIAG") != 0)`
#   (GameBridgeGameStateToX_EventFlowGuiEvents.cpp:395), and this script deliberately does NOT set
#   that variable -- it INHERITS and RECORDS it (see the DIAGENV banner).  So on a shell without
#   it, three of the five rungs physically cannot print no matter how far the chain got.  That is
#   detected, announced at arm time, and stamped BLIND on the LADDER line; it is never silent.
#   ⚠️ And the same guard carries a 24-LINE BUDGET shared across ALL the [evt-flow] arms
#   (siDiagLinesLeft, :396).  Action 201 posts on junction entry/exit, so a run that drives past
#   several junctions can burn the budget before it reaches the one it was aimed at, and the later
#   rungs then go quiet mid-run.  Teleport ONTO the target junction rather than driving across town.
$eventLadder = @(
  @('e-junc',   '\[evt-flow\] action 201 -> gui 311',            'grounded'),
  @('e-case20', '\[start\] event 20 ',                            'grounded'),
  @('e-start',  '\[evt-flow\] action 23 -> gui 93',              'grounded'),
  @('e-count',  '\[evt-flow\] action 47 -> gui 234',             'grounded'),
  @('e-inprog', 'E_GMS_IN_PROGRESS',                             'contract')
)
foreach ($r in $eventLadder) { $cues += ,@($r[0], $r[1]) }

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
$runawayLog = $false
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

  # ⛔⛔ RUNAWAY-LOG GUARD (2026-08-28). This loop re-reads the WHOLE log every poll. An assert
  # cascade can grow BrnGame.log without bound -- measured: one overflow clobbered a component
  # counter with ASCII text and produced 2,168,776 `Invalid Component Index` lines, a **474 MB**
  # log. At that size Get-Content -Raw stops making progress, the loop never advances, and the run
  # HOLDS THE BOX LOCK INDEFINITELY -- stranding every other wave behind a harness that looks busy.
  # Two harnesses had to be killed by hand for exactly this.
  # ⭐ A measurement harness must not be destroyable by the thing it is measuring. Fail LOUDLY and
  # release the lock instead of hanging: an assert cascade is a real finding, and a run that dies
  # saying so is far more useful than one that wedges the machine.
  $logLen = 0
  try { $logLen = (Get-Item $log -ErrorAction SilentlyContinue).Length } catch { $logLen = 0 }
  if ($logLen -gt $MaxLogMB * 1MB) {
    Write-Host ("[flow] FAIL: BrnGame.log hit {0:f0} MB (limit {1} MB) at {2:f1}s -- runaway output," -f ($logLen/1MB), $MaxLogMB, $elapsed)
    Write-Host  "[flow]       almost certainly an ASSERT CASCADE. Aborting so the box lock is released."
    Write-Host  "[flow]       The log tail names the repeating line; that IS the finding. Raise -MaxLogMB"
    Write-Host  "[flow]       only if you genuinely expect an enormous log."
    $runawayLog = $true
    break
  }

  $txt = Get-Content $log -Raw -ErrorAction SilentlyContinue
  if ($null -ne $txt) {
    $n = ([regex]::Matches($txt, '\[ASSERT \d+\]')).Count
    if ($n -gt $seenAsserts) {
      # Release the event once per NEWLY SEEN assert (AutoReset consumes exactly one wait per Set),
      # THEN fall back to the END tap. Order matters: the event works whether or not the game holds
      # focus, the keystroke only works if it does. With -ReleaseAsserts the gate is already open
      # and these Sets are harmless no-ops.
      $newAsserts = $n - $seenAsserts
      $seenAsserts = $n
      for ($k = 0; $k -lt $newAsserts; $k++) { $evAssertRelease.Set() | Out-Null; Start-Sleep -Milliseconds 30 }
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
    # ⭐ 2026-08-28: BOOT may go straight to CARSELECT. The fresh path is unaffected -- 'flyby'
    #   fires thousands of lines before 'carsel' there, so BOOT has always become FLYBY first --
    #   but a RETURNING boot has no new-profile intro and therefore no flyby, while (since the
    #   junkyard-entry fix) it does reach car select. Without this arm its car-select screen
    #   would never promote and the Accept pump would never switch to the 3 s cadence.
    if (($phase -eq 'BOOT' -or $phase -eq 'FLYBY') -and $marks.ContainsKey('carsel')) { $phase = 'CARSELECT'; $acceptGap = 3.0; $lastAccept = Get-Date }
    if ($phase -eq 'CARSELECT' -and $marks.ContainsKey('strfin')) { $phase = 'DRIVING'; $drivingAt = Get-Date }
    # Returning-player promotion -- now a FALLBACK, not the normal path. Gated on 'newprof' (this
    # boot found a profile) and 'ingame', so the fresh path's behaviour -- and every golden banked
    # against it -- is bit-for-bit unchanged.
    # ⛔⛔ AND ON 'jystart' BEING ABSENT (2026-08-28). Once the start-of-game junkyard entry
    #   completes on a returning boot, the run owes the game an ACCEPT at car select, and the
    #   Accept pump only runs in BOOT/CARSELECT -- so promoting to DRIVING at 'ingame' (which is
    #   ~3500 log lines earlier) would silently park the run at car select with the throttle held,
    #   the exact class of silent-no-op this block was added to fix in the first place.
    # ⚠️ THE 5 s DWELL IS THE RACE GUARD, not politeness: 'ingame' and 'jystart' land ~20 log
    #   lines apart, so a single poll can see the first and not yet the second. Waiting until
    #   'ingame' is 5 s old before honouring the fallback makes the absence of 'jystart' mean
    #   "the entry is not coming" rather than "the poll was early".
    if ($phase -ne 'DRIVING' -and $marks.ContainsKey('newprof') -and $marks.ContainsKey('ingame') -and
        (-not $marks.ContainsKey('jystart')) -and (($elapsed - $marks['ingame']) -ge 5.0)) {
      $phase = 'DRIVING'; $drivingAt = Get-Date
      Write-Host "[flow] DRIVING via the RETURNING-PLAYER FALLBACK (profile found; no junkyard entry)"
    }
  }

  $pump = ($phase -eq 'BOOT') -or (($phase -eq 'CARSELECT') -and (-not $HoldCarSelect))
  if ($pump -and ((Get-Date) - $lastAccept).TotalSeconds -ge $acceptGap) {
    $evAccept.Set() | Out-Null
    $lastAccept = Get-Date
  }

  # ---- the offline-pause taps (opt-in) -----------------------------------------------------
  # One TAP each, latched, on the same DRIVING time base the throttle uses. Pause opens the main
  # map (CrashNavMapMain::OnEnter -> GuiEventActivateCrashNav(false) -> ... -> mbSimPaused = 1);
  # unpause taps STOP (50 GUI_CANCEL == Escape / pad-B), which the map's Update turns into
  # GO_BACK. ⛔ NOT Accept -- see the $evStop banner: Accept is 49 GUI_SELECT since d91d7949 and
  # the map's exit arm takes only 45/50, so tapping Accept resumes NOTHING.
  if ($phase -eq 'DRIVING') {
    $sinceDrivingP = ((Get-Date) - $drivingAt).TotalSeconds
    while ($script:pauseNext -lt $script:pauseTimes.Count -and
           $sinceDrivingP -ge $script:pauseTimes[$script:pauseNext]) {
      $script:pauseNext++
      if ($PauseTarget -eq 'driver') { $evStart.Set()    | Out-Null }
      else                           { $evPauseMap.Set() | Out-Null }
      Write-Host ("[flow] PAUSE tap #{0} ({1}) at DRIVING+{2:f1}s" -f $script:pauseNext,
                  $(if ($PauseTarget -eq 'driver') { "action 45 GUI_START -> CN_D_DETAIL" }
                    else                           { "action 46 GUI_BACK -> CN_MAP_MAIN" }),
                  $sinceDrivingP)
    }
    while ($script:unpauseNext -lt $script:unpauseTimes.Count -and
           $sinceDrivingP -ge $script:unpauseTimes[$script:unpauseNext]) {
      $script:unpauseNext++
      $evStop.Set() | Out-Null
      Write-Host ("[flow] UNPAUSE tap #{0} (action 50 GUI_CANCEL / Stop) at DRIVING+{1:f1}s" -f $script:unpauseNext, $sinceDrivingP)
    }
  }

  # ---- the SINGLE-bumper presses (-ShoulderAt) -------------------------------------------
  # Resolved every poll and applied only on CHANGE, exactly like the showtime pair below. The
  # channels are MANUAL-RESET, so Set() is press-and-hold and Reset() is release; the desired
  # state is "the newest entry whose window covers now", which makes overlapping entries
  # well-defined instead of leaving a button stuck down.
  if ($phase -eq 'DRIVING' -and $script:shoulderTaps.Count -gt 0) {
    $sinceDrivingS = ((Get-Date) - $drivingAt).TotalSeconds
    $lsWant = ''
    foreach ($lTap in $script:shoulderTaps) {
      if ($sinceDrivingS -ge $lTap.At -and $sinceDrivingS -lt ($lTap.At + $lTap.Hold)) { $lsWant = $lTap.Side }
    }
    if ($lsWant -ne $script:shoulderDown) {
      $script:shoulderDown = $lsWant
      $evShldL.Reset() | Out-Null; $evShldR.Reset() | Out-Null
      if     ($lsWant -eq 'L') { $evShldL.Set() | Out-Null }
      elseif ($lsWant -eq 'R') { $evShldR.Set() | Out-Null }
      $lsState = $(if ($lsWant -eq '') { 'BOTH UP' } else { "$($lsWant)B DOWN" })
      Write-Host ("[flow] BUMPER {0,-8} at {1,6:f1}s (DRIVING+{2:f1}s)" -f $lsState, $elapsed, $sinceDrivingS)
      $inputLog += ("bumper {0,-8} run={1,6:f1}s DRIVING+{2:f1}s" -f $lsState, $elapsed, $sinceDrivingS)
    }
  }

  # ---- the bumper hold (showtime) --------------------------------------------------------
  # ⚠⚠ DELIBERATELY OUTSIDE THE -Drive GATE. The first cut of this block sat INSIDE it, which
  # would have made `-Showtime` with no `-Drive` a SILENT NO-OP -- indistinguishable in the log
  # from a dead input channel or a broken game-side hook. -Showtime is its own opt-in and must
  # press the buttons whether or not the throttle is held; the "pair it with -Drive" note in the
  # arming banner is ADVICE about the console gate, not a precondition of the gesture.
  # Resolved every poll and applied only on CHANGE, like the pedals below. Both channels move
  # together because the byte the game computes from them is their AND.
  if ($phase -eq 'DRIVING' -and $showtimeAt -ge 0) {
    $sinceDrivingB = ((Get-Date) - $drivingAt).TotalSeconds
    $wantShoulders = ($sinceDrivingB -ge $showtimeAt) -and ($sinceDrivingB -lt ($showtimeAt + $showtimeHold))
    if ($wantShoulders -ne $shouldersHeld) {
      $shouldersHeld = $wantShoulders
      if ($wantShoulders) { $evShldL.Set()   | Out-Null; $evShldR.Set()   | Out-Null }
      else                { $evShldL.Reset() | Out-Null; $evShldR.Reset() | Out-Null }
      $bstate = $(if ($wantShoulders) { "DOWN" } else { "UP" })
      Write-Host ("[flow] BOTH BUMPERS {0,-5} at {1,6:f1}s (DRIVING+{2:f1}s)" -f $bstate, $elapsed, $sinceDrivingB)
      $inputLog += ("bumpers {0,-5} run={1,6:f1}s DRIVING+{2:f1}s" -f $bstate, $elapsed, $sinceDrivingB)
    }
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
foreach ($e in @($evAccel,$evBrake,$evHandB,$evStrL,$evStrR,$evShldL,$evShldR)) { $e.Reset() | Out-Null }

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

# --- the LADDER's final sweep ------------------------------------------------------------
# The poll loop reads the log at the TOP of an iteration and the elapsed check is above that, so
# the iteration that ends the run never reads -- and the game keeps writing right up to the
# Stop-Process above.  The last second or so of a run is therefore invisible to the loop.  For the
# flow marks that has always been harmless (they all fire in the first ninety seconds); for the
# LADDER it is not, because the rungs this wave cares about are exactly the ones that fire LAST.
# Sweep the finished, copied log once more -- LADDER RUNGS ONLY.  This can only ADD a rung the
# game genuinely printed; it can never invent one, and it does not touch a single flow mark, so
# the gates downstream see the marks.txt they have always seen.
$ladderLate = @{}
$finalLog = Join-Path $OutDir "BrnGame.log"
if (-not (Test-Path $finalLog)) { $finalLog = $log }
$finalTxt = Get-Content $finalLog -Raw -ErrorAction SilentlyContinue
if ($null -ne $finalTxt) {
  $finalCue = Strip-CallstackFrames $finalTxt
  foreach ($r in $eventLadder) {
    if ((-not $marks.ContainsKey($r[0])) -and ($finalCue -match $r[1])) {
      $marks[$r[0]]      = $endElapsed
      $markFrame[$r[0]]  = $endFrame
      $ladderLate[$r[0]] = $true
      Write-Host ("[flow] {0,-8} at {1,6:f1}s  frame={2}  (final sweep)" -f $r[0], $endElapsed, $endFrame)
    }
  }
}

# --- marks.txt.  RUNSTART FIRST: it is what the gates use to reject stale dumps. ----------
$summary = @()
$summary += ("RUNSTART {0}" -f $t0.ToString('o'))
$summary += ("FRAMEDIR {0}" -f $(if ($framesOut) { $framesOut } else { "-" }))
foreach ($k in @('flyby','newprof','ingame','jystart','carsel','livery','accept','exitjy','strfin')) {
  if ($marks.ContainsKey($k)) { $summary += ("{0,-8} {1,6:f1}s  frame={2}" -f $k, $marks[$k], $markFrame[$k]) }
  else                        { $summary += ("{0,-8} (never)" -f $k) }
}
$summary += ("END      {0,6:f1}s  frame={1}" -f $endElapsed, $endFrame)
if ($runawayLog) { $summary += "RUNAWAY LOG -- aborted on size; this run is NOT comparable" }
$summary += ("asserts={0} phase={1}{2}" -f $seenAsserts, $phase,
             $(if ($ReleaseAsserts) { "  [ASSERT GATE HELD OPEN -- asserts= NOT comparable]" } else { "" }))
# DIAGENV: the inherited probe knobs this run actually carried. Two runs are comparable only
# when this line matches -- see the banner where it is collected.
# ⚠ -DiagEnv variables are recorded HERE TOO. They are applied AFTER the wipe, so they do
# not appear in $diagEnvText -- and a run whose instruments are invisible in marks.txt is
# exactly the non-comparable log this line exists to prevent.
$summary += ("DIAGENV  {0}{1}" -f $diagEnvText,
             $(if ($diagEnvApplied.Count -gt 0) { "  [-DiagEnv " + ($diagEnvApplied -join ' ') + "]" } else { "" }))
# TELEPORT: the -Teleport spec this run carried, for the same comparability reason as DIAGENV --
# a log whose car started 250 m from the junkyard is not comparable with one that did not.
$summary += ("TELEPORT {0}" -f $teleportText)
# STARTEVT: whether this run carried the event-start hook. Same comparability reason as DIAGENV and
# TELEPORT, and a stronger one: a run carrying it may not have been in free burn at all.
$summary += ("STARTEVT {0}" -f $startEventText)
# SHOWTIME: whether this run pressed the bumpers, and whether the game-side stand-in was armed.
# Same comparability reason as STARTEVT: a run that entered showtime is not comparable with a
# free-burn run, and the summary must say so on its face.
$showtimeText = 'not armed'
if ($Showtime -ne "") { $showtimeText = ("BOTH BUMPERS at DRIVING+{0:f1}s for {1:f1}s (console gate; BRN_START_SHOWTIME inert)" -f $showtimeAt, $showtimeHold) }
if ($ShowtimeIgnoreProgression) { $showtimeText += "  +PROGRESSION-GATE-IGNORED (BRN_SHOWTIME_IGNORE_PROGRESSION=1)" }
$summary += ("SHOWTIME {0}" -f $showtimeText)
# SKIPTIP: whether this run carried the training-tip bypass. Same comparability reason as STARTEVT
# -- a run whose junction canEnter gate ignored a blocking tip showed a hint the console would not.
$summary += ("SKIPTIP  {0}" -f $skipTipText)
# EVENTFSM: whether the event-HUD FSM hop was armed -- a run that carried it left FBURN_MAIN on
# mode start (PRE_FLY_BY/RACE_MAIN), so its HUD pixels are not comparable to a default run's.
$summary += ("EVENTFSM {0}" -f $eventFsmText)
# --- LADDER: how far the event-start chain got.  Rung meanings and the grounded/contract split
#     are in the banner above the $eventLadder table.
$ladderDepth = 0
$ladderIdx   = 0
foreach ($r in $eventLadder) {
  $ladderIdx++
  if ($marks.ContainsKey($r[0])) {
    $ladderDepth = $ladderIdx
    $lLate = ""
    if ($ladderLate.ContainsKey($r[0])) { $lLate = "  (final sweep)" }
    $summary += ("{0,-8} {1,6:f1}s  frame={2}{3}" -f $r[0], $marks[$r[0]], $markFrame[$r[0]], $lLate)
  } elseif ($r[2] -eq 'contract') {
    $summary += ("{0,-8} (never) CUE UNVERIFIED -- nothing in the tree prints this text yet, so this" -f $r[0])
    $summary += ("         line says nothing about the game. See the ladder banner.")
  } else {
    $summary += ("{0,-8} (never)" -f $r[0])
  }
}
$ladderReached = 'none'
if ($ladderDepth -gt 0) { $ladderReached = $eventLadder[$ladderDepth - 1][0] }
$ladderBlind = ""
if (-not $ladderDiag) {
  $ladderBlind = "  BLIND(BRN_PROP_DIAG unset -- the [evt-flow] rungs cannot print)"
}
$summary += ("LADDER   {0}/{1} deepest={2} startevent={3}{4}" -f `
             $ladderDepth, $eventLadder.Count, $ladderReached, [bool]$StartEvent, $ladderBlind)
# CRASHARM: the deterministic crash trigger this run carried, for the same comparability reason.
$summary += ("CRASHARM crashEntry=always(flag deleted 2026-08-27) crashPlayer={0} deformTrace={1}" -f $CrashPlayer, $DeformTrace)
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
