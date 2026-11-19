# flow_run.ps1 switches

Every parameter of `tools/diagnostics/flow_run.ps1`, one line each, checked against its `param()`
block and the code behind it. In a case, the `Run` hashtable is splatted onto these verbatim
(`Run = @{ Drive = $true; Teleport = '...' }`). Defaults are in parentheses. The script's own
banners carry the measurements behind each switch; read them before changing one.

Rules that hold for every switch:

- A typo fails the run instead of being skipped: an unknown token, a non-number, a missing
  companion switch. Numbers are parsed with InvariantCulture, so write `3.5`, never `3,5`.
- An opt-in switch prints an arming line (`DRIVE armed`, `TELEPORT armed`, `BUMPER schedule`,
  `MENU-TAP schedule`, `PAUSE schedule`, `MENUSCRIPT armed`, `DIAG ENV applied` ...) in
  `flow_run.console.log` and most are recorded in `marks.txt`. No arming line, no input.
- A capability (something that changes what the game does) has its own switch and is never a
  default run; an instrument (something that only prints) goes through `-DiagEnv`.
- Exit code: 0 = the run completed and any requested gates passed; 1 = anything failed (an assert
  stop, a foreign game, a runaway log, a failed gate, a refused argument).

## Time bases

| what | t = 0 |
|---|---|
| `-SteerScript`, `-ThrottleScript`, the `-Drive` hold | the DRIVING mark + `-DriveDelay` |
| `-PauseAt`, `-UnpauseAt`, `-ShoulderAt`, `-CamButtonAt`, `-MenuTapAt`, `-Boost`, `-Showtime` | the DRIVING mark |
| `-MenuScript` | starts at the DRIVING mark; each step waits on the game (a log line, a file), not the clock |
| `-TitleStart`, `-CarSelectTaps`, the Accept pump | before DRIVING (BOOT, CARSELECT) |
| `-DebugFinishAt`, `-WinTeleport` | the running mode's own time, counted by the game |
| `-CrashSweep*` cadence | sim frames, so it replays identically whatever the host frame rate |

The poll loop sleeps 250 ms per pass, so a scheduled input lands up to one pass late; the `POLL`
line in `marks.txt` reports the worst gap and `THROTTLE` how late the first input really was.

## Boot and flow

- `-SkipIntro`: launch with `-skipvideos`, the console's own boot-video latch; the EA and Criterion logos are skipped, the legal/title screen and the junkyard still run. Not for a case about the boot UI. Recorded as `SKIPINTRO`.
- `-TitleStart`: one Start tap after a fresh `[BootLegal] stage ... -> 7`, before the BOOT Accept pump, so player 0 is bound through action 8 (the plain Accept pump signs no profile in). Recorded as `TITLESTART`.
- `-AcceptGap <s>` (0 = the historical 2.0 s while booting, 3.0 s at car select): the Accept-pump period; harness latency, not a game gate. Recorded as `ACCEPTGAP`.
- `-HoldCarSelect`: stop pumping Accept once car select is up (park there for a capture).
- `-CarSelectTaps "<Channel>:<count>"`: at car select, spend the first pump slots tapping that channel, then accept as usual. The carousel recipe is in [menu-driving.md](menu-driving.md).

## Driving

- `-Drive`: hold Accelerate from DRIVING + `-DriveDelay` through the game's ordinary input chain (nothing writes a velocity or a physics field). `-SteerScript` / `-ThrottleScript` refuse to run without it, and `-Teleport` / `-CrashSweep` never fire without it (they arm on distance driven).
- `-DriveDelay <s>` (6.0): seconds after the DRIVING mark before any input, so the car settles first.
- `-DriveSeconds <s>` (0 = to the end): length of the drive window.
- `-Steer <token>` (`none`): a fixed steering hold: `none`, `left`, `right`, or `left25` / `left50` / `left75` / `right25` / `right50` / `right75` (that fraction of full lock; full lock under throttle is a spin, not a lane change).
- `-SteerScript "<s>:<token>,..."`: a steering schedule with the same tokens; replaces `-Steer`. The newest entry whose time has passed wins.
- `-ThrottleScript "<s>:<token>[+<token>],..."`: a pedal schedule: `none`, `accel`, `brake`, `handbrake`, combined with `+`; replaces the plain hold.
- `-AIDrive`: `BRN_AI_DRIVES_PLAYER=1`, the console's "AI drives player" debug toggle applied from the harness; pad switches go inert. Proof: `[ai-drive] ***** HARNESS-ONLY` in the log. Recorded as `AIDRIVE`.
- `-Teleport "x,y,z[,headingDeg]"`: place the car once through the game's own `RequestPlaceOnTrack` (pass an approximate Y; the game finds the ground). Fires after the car has driven `-TeleportArm` metres. The streamer does not teleport: give the world and its props a few seconds before asking the car to hit anything. Recorded as `TELEPORT`.
- `-TeleportArm <m>` (0 = the game's 8 m): distance driven before the teleport fires.
- `-Boost "<sec>[:<periodSec>[:<holdSec>]]"` (period 1.0, hold 0.4): pulse the boost button from DRIVING + sec. It must pulse: the bounce reads the pressed-this-frame bit, so a hold is one press; the hold must be shorter than the period.

## Crash

- `-CrashPlayer <n>` (0 = off): crash the player car once, deterministically, on `UpdateVehiclePhysics` call n (`BRN_CRASH_PLAYER`). Recorded on the `CRASHARM` line.
- `-CrashSweep "x,y,z"`: the deterministic crash sweep's launch point; each shot is one `RequestPlaceOnTrack(pos, heading, speed)`, so impact speed and angle are inputs. Needs `-Drive` and `-CrashSweepShots`; refuses `-Teleport`. Recorded as `SWEEP`.
- `-CrashSweepShots "h:s,..."`: heading (degrees clockwise from +Z) and speed (m/s) per shot, or `x/y/z/h:s` to aim each shot from its own launch point; up to 48 shots per boot.
- `-CrashSweepSettle <frames>` (0 = the game's 150): sim frames between shots; the next shot also waits for the crash to end.
- `-CrashSweepMax <frames>` (0 = 900): sim frames after which a shot fires anyway.
- `-CrashSweepArm <m>` (0 = 8 m): metres driven before shot 0.
- `-Jump`: a preset over `-CrashSweep`: a measured ramp, a rising speed ladder with two repeats as the control, settle 420 frames. Anything passed explicitly wins. Needs `-Drive`.
- `-JumpSpeeds "20,26,..."`: override the `-Jump` speed ladder (m/s).

A placed car starts in the console's 1.5 s invincible absorption set, and a re-placed car that did
not wreck keeps the previous shot's dents: only shot 0 of a boot is a pristine, damageable car once
it has travelled 1.5 s (`crash_sweep_batch.ps1` takes one shot per boot for that reason).

## Camera and menus

- `-CamButtonAt "<sec>:<V|B>[:<holdSec>]"` (hold 2.0): hold LOOKBACK (`V`, game action 6) or CHANGEVIEW (`B`, action 5); the director's camera actions, not the GUI bumper rows.
- `-ShoulderAt "<sec>:<L|R>[:<holdSec>]"` (hold 1.5): hold one bumper (GUI actions 54/55: the pause-screen tab toggles). Refuses `-Showtime` (same two channels).
- `-MenuTapAt "<sec>:<Channel>,..."`: one auto-reset tap per entry. Channels: `DPadUp` `DPadDown` `DPadLeft` `DPadRight` `Next` `Prev` `OptionNext` `OptionPrev` `Accept` `Stop` `Start` `EventDetails` `Option0`.
- `-MenuScript "<step>;<step>;..."`: cue-gated steps (`wait:` `waitpeer:` `waitfile:` `signal:` `tap:` `tapuntil:` `hold:` `sleep:` `gap:` `timeout:` `mark:`); full grammar in [menu-driving.md](menu-driving.md).
- `-MenuScriptGap <s>` (0.35): spacing after each `-MenuScript` tap.
- `-PauseAt "<s>[,<s>...]"`: tap the offline pause, one tap per entry, so a run can pause and resume repeatedly.
- `-PauseTarget map|driver` (`map`): `map` taps action 46 (CN_MAP_MAIN); `driver` taps action 45, the START pause (CN_D_DETAIL, the screen that draws).
- `-UnpauseAt "<s>[,<s>...]"`: tap Stop (action 50) to come back out; one entry per pause, each later than its pause. Accept never resumes: the map's exit arm takes 45 and 50 only.

## Events

- `-StartEvent`: `BRN_START_EVENT=1`; the game-side hook starts a mode while the player car stands in a traffic-light region. Pair it with `-Drive -Teleport` onto a junction, or nothing fires. Recorded as `STARTEVT`.
- `-EventFsm`: `BRN_EVENT_FSM=1`; arms the event-HUD FSM hop (FBURN_MAIN -> PRE_FLY_BY -> RACE_MAIN) that the exe still gates. Recorded as `EVENTFSM`.
- `-SkipTrainingTip`: `BRN_SKIP_TRAINING_TIP=1`; the junction canEnter gate ignores a blocking training tip so the start hint can show. It starts nothing. Recorded as `SKIPTIP`.
- `-Showtime "<at>[:<holdSecs>]"` (hold 5): hold both bumpers from DRIVING + at through the ordinary input chain; the console's own gate decides, and a refused press prints `[showtime] BOTH BUMPERS held, but ... refused: <reason>`. Also arms the `BRN_SHOWTIME_WATCH` witness. Can leave free burn. Recorded as `SHOWTIME`.
- `-ShowtimeIgnoreProgression`: `BRN_SHOWTIME_IGNORE_PROGRESSION=1`; skips the road-rules progression refusal for that one decision and forges nothing. Does nothing without `-Showtime`.
- `-DebugFinishPos <n>` (0 = off): end the running mode with finish position n through the console's own debug member (1 = first place, the medal path). Needs a running mode (`-StartEvent`), banks into the profile, and is never a genuine win. Recorded as `DBGFINISH`.
- `-DebugFinishAt <s>` (20): seconds of mode time before `-DebugFinishPos` fires.
- `-WinTeleport <s>` (-1 = off): after s of in-progress time, place the car into each remaining landmark box; the game's own landmark chain scores the finish, but the car did not drive the route. Needs `-StartEvent`. Recorded as `WINTELE`.
- `-WinTeleportGap <ticks>` (0 = the game's 90): pre-world ticks between hops.
- `-WinTeleportSpeed <m/s>` (-1 = the game's 0): forward speed handed to each placement.
- `-WinTeleportLead <m>` (-1 = the game's 30; 0 = no stage): offline race only, metres outside the finish box the car is staged before the finish hop.

## Diagnostics

- `-DiagEnv "A=1,B=2"`: engine instruments applied after the `BRN_*` wipe and echoed; recorded on the `DIAGENV` line. Rules in [harness-environment.md](harness-environment.md).
- `-MotionProbe`: `BRN_MOTION_PROBE=1`, the `[motion]` pose / velocity / gas trace that the `DRIVE` and `GAS` lines and `Get-DriveSegment` read.
- `-TriCacheProbe <period>` (0 = off): `[tricache]` world-collision cache trace; the value is a sampling period in frames (1 = the game's default 60).
- `-TractionProbe <period>` (0 = off): `[traction]` per-wheel trace; a period in frames.
- `-DeformTrace <period>` (0 = off): `[deform-trace]` deformation witness; a period in calls (1 = every call).
- `-Frames`: dump frames (`BRN_FRAME_DUMP`) into `-FrameDir`. run_case passes it from the case's `Frames` key.
- `-FrameDir <absolute path>` (`<OutDir>\frames`): must be absolute; emptied at the start.
- `-FrameEvery <n>` (30): dump period in presents; 1 = every present.
- `-MinFreeGB <n>` (25): refuse to start a frame dump with less free space than this.
- `-Gates`: score the run with `frame_gate.ps1` and `carselect_frame_gate.ps1` against their goldens; needs `-Frames`.
- `-WriteGoldens`: re-bank both goldens instead of checking them. Look at the frames first; bank on a default run only.

## Process control

- `-OutDir <dir>` (`scratch\flow_run\<timestamp>`; run_case passes `<run>\flow`): emptied at the start.
- `-MaxSeconds <s>` (275): wall-clock budget from launch; then the game is stopped (`EXIT harness-stop`).
- `-LogWaitSeconds <s>` (90): fail when the game writes no log of its own in that time; a log older than the launch is never read.
- `-MaxLogMB <n>` (128): abort on a runaway log (almost always an assert cascade) so the box lock is released; the run is marked not comparable.
- `-LockTimeoutSec <s>` (1800; run_case passes 7200): how long to wait for the box.
- `-NoLock`: escape hatch that skips the box lock; two harnesses then kill each other's runs. Never use it to get past a busy box.
- `-Slot <n>` (0): run slot n's copy of the exe from `build\game_slots\<n>\` with slot-suffixed names and its own lock.
- `-GameDir <dir>`, `-WorkingDirectory <dir>`: a private staged pair (`<stage>\slot`, `<stage>\data`); both, with a positive `-Slot` and `-StrictGameOwnership`.
- `-StrictGameOwnership`: refuse to start while any Burnout or TUB game runs, stop only this run's own process, and write `terminal-status.json`.
- `-AllowConcurrentGames`: in a strict private run, permit other games with distinct image paths.
- `-MaxConcurrentOtherGames <n>` (1): how many other games `-AllowConcurrentGames` permits; above 1 requires it.
- `-BelowNormal`: set the owned game to BelowNormal priority right after launch.
- `-ReleaseAsserts`: hold the assert-release event open for the whole run; only for an assert storm, and `asserts=` stops being comparable.
- `-NoAssertRelease`: never release an assert; stop at the first one observed (`ASSERT_STOP` in `marks.txt`). Refuses `-ReleaseAsserts`.
- `-Audio`: let the run make noise. By default every run is muted (`BRN_AUDIO_MUTE=1`, one `SetVolume(0)` on the mastering voice; the audio simulation is unchanged and the log prints `master volume=`).
