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
powershell -ExecutionPolicy Bypass -File tools\tests\build_exe_locked.ps1 -Label mylane
```

| file | role |
|---|---|
| `run_case.ps1` | run one case: `flow_run.ps1` with the case's scenario, then evaluate its checks; writes `result.json` + `REPORT.md` |
| `_checks.ps1` | the check kinds (`NewAsserts`, `LogCount`, `LogMatch`, `LogValue`, `Mark`, `Frame`, `FrameRatio`, `Script`) |
| `frame_stats.py` | one number about one region of one dumped frame (luminance, saturation, dark fraction ...) |
| `build_exe_locked.ps1` | rebuild the exe under the same box lock the runs use -- one build at a time, never during a run |
| `run_all.ps1` | every case (or a filter), one table |
| `cases/*.ps1` | the cases. One file, returns one hashtable |

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

One game at a time. `flow_run.ps1` and `build_exe_locked.ps1` share `_box_lock.ps1`; a
queued lane waits (up to 2 h by default here) and says so. Keep `MaxSeconds` as short as the
scenario allows -- boot to DRIVING is ~25 s on the returning-player path, ~80 s fresh -- and do
the offline work (image reads, asm, dumps) before you spend box time.
