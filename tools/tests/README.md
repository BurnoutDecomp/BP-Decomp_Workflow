# tools/tests -- bug tests for the running game

A **bug test** is one scenario run through the game plus a list of checks over the evidence
that run leaves behind (the log, the flow marks, dumped frames). It is the runtime-side
counterpart of the per-TU compile gate: the gate says the code builds, a case says the game
*behaves*.

```
powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case baseline_boot_drive
powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case props_hit_speed -ExpectFail   # RED
powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case props_hit_speed -NoRun -RunDir scratch\bugtest\runs\props_hit_speed\20260906_101500
powershell -ExecutionPolicy Bypass -File tools\tests\run_all.ps1 -Filter 'traffic_*'
powershell -ExecutionPolicy Bypass -File tools\tests\run_all.ps1 -Parallel 3          # 3 games at once
powershell -ExecutionPolicy Bypass -File tools\tests\build_exe_locked.ps1 -Label mylane
```

| file | role |
|---|---|
| `run_case.ps1` | run one case: `flow_run.ps1` with the case's scenario, then evaluate its checks; writes `result.json` + `REPORT.md` |
| `_checks.ps1` | the check kinds (`NewAsserts`, `LogCount`, `LogMatch`, `LogValue`, `Mark`, `Frame`, `FrameRatio`, `Script`) |
| `frame_stats.py` | one number about one region of one dumped frame (luminance, saturation, dark fraction ...) |
| `build_exe_locked.ps1` | rebuild the exe under the same box lock the runs use -- one build at a time, never during a run |
| `run_all.ps1` | every case (or a filter), one table; `-Parallel k` runs k of them at once |
| `slots.ps1` | build / refresh / list the per-slot launch folders the parallel runs use |
| `cases/*.ps1` | the cases. One file, returns one hashtable |

## Several games at once -- SLOTS

The box used to run **one** game, so a sixteen-case sweep was half an hour and every other lane
queued behind all of it. A **slot** is a second, third, ... instance of the same build:

```
powershell -ExecutionPolicy Bypass -File tools\tests\slots.ps1 -Make 3     # build/refresh slots 1..3
powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case baseline_boot_drive -Slot 2
powershell -ExecutionPolicy Bypass -File tools\tests\run_all.ps1 -Parallel 3
```

* **Slot 0 is `build\game` and is unchanged, byte for byte.** A plain `run_case.ps1 -Case x`, every
  other script in `tools\diagnostics`, and every golden still take exactly the path they always did.
* A slot is a **launch folder**, not a copy of the game: `build\game_slots\<n>\` holds the exe, its
  DLLs, its `.cgsmap` and its provenance stamp, and **the working directory stays `build\game`**, so
  all 5.9 GB of data is shared live and can never go stale in a slot.
* Everything a second instance would fight over is suffixed from `BRN_HARNESS_SLOT`
  (b5-decomp `CgsHarnessSlot.h`): the game's **single-instance mutex** (without which a second copy
  just quits), the harness **input channels**, the **assert-release** event, the **Memcard**
  directory, this harness's **box lock**, and the **kill sweep**, which becomes a match on the
  process's image path instead of its name.
* `build_exe_locked.ps1` takes slot 0's box lock plus a narrow `BurnoutPC_ExeStage` mutex that
  `slots.ps1` also takes around its copy, so a slot can never boot a half-linked exe. A slot run
  started before a build keeps the exe it started with; its provenance stamp says which.
* **Measured cost (2026-09-06, 3 slots, identical scenario):** boot-to-DRIVING 16.1/16.1/16.2 s
  against 16.2 s solo, all three drove 316 m with the GAS witness hot, and steady-state
  `producerFps` 54.5-57.5 against 57.0 solo. Log lines and pixels do not move with contention --
  but a check that is ever a **frame rate or a wall-clock duration** must be scored on its own slot.

## Silence, and whose keyboard the game reads

* **Every harness run is MUTED by default** (2026-09-06, lane quiet). `flow_run.ps1` sets
  `BRN_AUDIO_MUTE=1`, and the PC audio leaf answers it with **one `SetVolume(0)` on the XAudio2
  mastering voice** -- the last gain in the graph, so nothing reaches the box's speakers. It is
  **not** "skip audio init": the device is really opened, every fill still runs, and the decoders,
  AEMS programs and engine-note state machines behave exactly as before. Verified by diffing a
  muted run against a `-Audio` one: the `[Audio]`/`[MovieAudio]` line sequence is **identical**
  (same 7 device opens, same 2 XMA decodes, same frame and sample counts) and only the number in
  `master volume=` moves, 0.000 vs 1.000. The game prints that number, read back out of the
  engine, on every open, so "this run was silent" is a check and not a claim.
  `Run = @{ Audio = $true }` turns the sound back on for a case that needs to be heard.
  Launching `Burnout_PC.exe` by hand stays audible -- only the harness sets the variable.
* **The game reads the keyboard only while its own window has the focus.** Before this the focus
  gate returned "foreground" unconditionally whenever `BRN_INPUT_ALLOW_BACKGROUND` was set, i.e.
  on every harness run, so typing anywhere on the box drove the test car. Measured, and it is
  `tools\tests\cases\quiet_focus_input.ps1`: with the game's window present and NOT foreground for
  117 of 117 samples and W+A physically held, the pre-fix build's `gas` reached 1.000 and the car
  drove 20.85 m; the post-fix build stays at 0.000 and 0.16 m. The **XInput pad is unchanged** --
  a pad is a device somebody picked up, not a window -- and the harness's named-event channels are
  untouched. The game logs `[input] focus=<0|1> kbd=<n>` once per focus change.

## `Setup` -- a stimulus that must run WHILE the game is up

Every `Checks` entry runs after `flow_run` returns, which is wrong for anything that has to happen
*during* the run. A case may carry an optional `Setup` scriptblock; `run_case.ps1` calls it just
before the boot with one context hashtable and **kills whatever process it returns** if that
outlives the run.

```powershell
Setup = {
  param($ctx)          # Root, RunDir, Slot, Case, GameLog (THIS SLOT's live BrnGame.log)
  Start-Process powershell -PassThru -ArgumentList ... `
    -RedirectStandardOutput (Join-Path $ctx.RunDir 'thing.log')
}
```

Write its evidence **into `$ctx.RunDir`** and have a `Script` check read it from there: a helper
that drops its output in a shared scratch directory is one stale file away from scoring a run
against somebody else's stimulus. A case with no `Setup` key behaves exactly as before.

## Keeping a case short

* `SkipIntro` in a case's `Run` block passes the console's own **`-skipvideos`** command-line latch
  (`BrnMain.cpp` -> `BootVideos::Update`'s soft-reboot exit), so the EA-Franchise and Criterion VP6
  logos are not played. Not for a case that is *about* the boot UI.
* `AcceptGap` is the harness's Accept-pump period. It was a fixed 3.0 s at car select and the
  junkyard leg was measurably two consecutive pump periods long -- that is the harness waiting, not
  the game.
* Together: **boot-to-DRIVING 23.0 s -> 16.2 s**, so ~7 s comes off every case for free.
* ⚠️ A check that normalises against *the whole run* changes meaning when the run's composition
  changes. `camera_shake_smash` divides its shaking frames by every other frame in the run, and
  deleting the (very calm) boot movies raised that denominator 37 % and took the ratio from 4.07 to
  2.98 against a threshold of 3 -- with a bit-identical numerator. It therefore carries neither
  knob; its banner has the three measurements.
* ⚠️ A `LogValue` whose witness never fires **fails**, on purpose. Some soak witnesses are rare and
  their rate is per unit of *world* time (`traffic_soak_ram`'s `[T3-demote]` fires about once per
  40 s of driving), so those cases keep their world time and only lose the boot.

Everything a run produces lands in `scratch\bugtest\runs\<case>\<timestamp>\` (see the
banner in `run_case.ps1`); `scratch\bugtest\runs\<case>\latest.json` points at the newest.

## RED -> GREEN, or it is not a test

1. **Write the case first**, against the bug as reported. Decide what number or line the
   bug changes and check *that* -- not "no asserts" alone, unless the bug *is* an assert.
2. **Run it RED** on the current build: `run_case.ps1 -Case <x> -ExpectFail` must exit 0,
   i.e. the checks FAIL and the failure detail shows the bug's signature. If it passes, the
   case does not measure the bug; fix the case, not the game.
3. **Fix the game**, rebuild with `build_exe_locked.ps1`, run the case again without
   `-ExpectFail`: GREEN.
4. Keep the RED run's `REPORT.md` path and the GREEN run's in your report. Both are the proof.

A case that was never seen RED proves nothing about the fix; a check that cannot be evaluated
(no frame, no witness line) FAILS rather than passes, on purpose.

## Writing a case

```powershell
@{
  Name    = 'props_hit_speed'                 # defaults to the file name
  Area    = 'physics'
  Bug     = 'BurnoutDecomp/b5-decomp#2 -- props sent flying way too much at medium/high speed'
  Frames  = $false                            # $true -> BRN_FRAME_DUMP into <run>\frames (needed by Frame checks)
  FreshProfile = $false                       # $true -> park Memcard\Profile.sav for this run (first-boot path)
  Run     = @{ Drive = $true; MaxSeconds = 150; Teleport = '3389.2,0.2,-1620.0,180'; ThrottleScript = '0:accel' }
  DiagEnv = 'BRN_PROP_DIAG=1'                 # engine instruments, "A=1,B=2" (flow_run clears every BRN_* first)
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }         # known noise: tools/tests/known_asserts.txt
    @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
    @{ Kind='Mark';     Name='reached DRIVING'; Phase='DRIVING' }
    @{ Kind='LogValue'; Name='prop speed after hit <= clamp'; Pattern='\[Q6-world\].*\|linVel\|=(?<v>[\d.]+)'; Group='v'; Agg='max'; Max=10.5 }
    @{ Kind='Frame';    Name='HUD corner not vignetted'; At='ingame'; Region='0,0,0.15,0.15'; Stat='lum_mean'; Min=40 }
    @{ Kind='FrameRatio'; Name='corner/centre'; At='last'; RegionA='0,0,0.1,0.1'; RegionB='0.45,0.45,0.55,0.55'; Stat='lum_mean'; Min=0.8 }
    @{ Kind='Script';   Name='anything'; Script={ param($ctx) @{ Pass=$true; Detail='...' } } }
  )
}
```

* `Run` is splatted onto `tools\diagnostics\flow_run.ps1` verbatim -- every switch it has
  (`-Teleport`, `-StartEvent`, `-EventFsm`, `-SkipTrainingTip`, `-CrashPlayer`, `-PauseAt`,
  `-ShoulderAt`, `-Boost`, `-Showtime`, `-SteerScript`, `-ThrottleScript`, ...) is a scenario
  primitive. Read its `param()` block; it is the vocabulary.
* `At` in a frame check is a **cue name from marks.txt** (`ingame`, `carsel`, `strfin`,
  `e-inprog`, ...), `last`, or a frame index; `Offset` walks frames from there. Frames are
  dumped every 30 presents by default (`Run.FrameEvery = 1` for a transition).
* Regions are pixels or fractions; the frame is 1280x720.
* `LogValue` extracts a **named group** from every matching line and aggregates
  (`max|min|mean|first|last|any|all`); `After='<cue>'` restricts to lines after that cue.
* `Script` gets `$ctx` (`LogLines`, `Marks`, `MarksText`, `Phase`, `FrameDir`, `RunDir`) and
  returns `@{ Pass; Detail }`.

## Witness lines: the log is the oracle

Most bugs are not visible as an assert. The case needs a **witness**: a log line the game
prints with the number the bug moves. If none exists, add one in the code you are fixing --
named `[FLAG PC witness]`, tagged `[<lane>]`, first-N or once, **never per-frame unbounded**
(a 6-car witness flooded 733k lines once and the harness aborted at 128 MB). Instruments are
opt-in behind a `BRN_*` env var and reach the game only through the case's `DiagEnv`
(`flow_run` clears every `BRN_*` variable first, by design).

## The box

One game **per slot**. `flow_run.ps1` and `build_exe_locked.ps1` share `_box_lock.ps1`, whose mutex
is now per slot (`Local\BurnoutPC_FlowRun[_<n>]`); a queued lane waits (up to 2 h by default here)
and says so. Keep `MaxSeconds` as short as the scenario allows -- boot to DRIVING is ~16 s on the
returning-player path with `SkipIntro`+`AcceptGap` (~23 s without, ~64 s fresh) -- and do the
offline work (image reads, asm, dumps) before you spend box time.
