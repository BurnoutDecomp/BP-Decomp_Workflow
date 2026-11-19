# Case schema

A case is one `.ps1` under `tools/tests/cases/` that **returns one hashtable**. run_case resolves
`-Case <name>` to `tools\tests\cases\<name>.ps1` (or takes a path), runs it, and refuses with exit
2 if it does not return a hashtable or has no `Checks`. Sources: `tools/tests/run_case.ps1`,
`tools/tests/_checks.ps1`, `tools/tests/README.md`.

```powershell
@{
  Name    = 'props_hit_speed'          # defaults to the file name
  Area    = 'physics'
  Bug     = 'BurnoutDecomp/b5-decomp#2 -- props sent flying way too much at medium/high speed'
  Frames  = $false                     # $true -> frames into <run>\frames (Frame checks need it)
  ProfileFixture = ''                  # or FreshProfile = $true, never both
  Run     = @{ Drive = $true; MotionProbe = $true; MaxSeconds = 60; SkipIntro = $true
               AcceptGap = 1.0; Teleport = '2995,1.5,-1750,0'; ThrottleScript = '0:accel' }
  DiagEnv = 'BRN_PROP_DIAG=1'          # instruments, applied after flow_run's BRN_* wipe
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
    @{ Kind='Mark';       Name='reached DRIVING'; Phase='DRIVING' }
    @{ Kind='LogValue';   Name='prop speed <= clamp'; Pattern='\[Q6-world\].*\|linVel\|=(?<v>[\d.]+)'; Group='v'; Agg='max'; Max=10.5 }
  )
}
```

`tools/tests/cases/baseline_boot_drive.ps1` is the run every other case is a variation of; if it is
red, no other case's failure means anything yet.

## Case keys

| key | meaning |
|---|---|
| `Name` | defaults to the file's base name; names the run folder |
| `Area`, `Bug` | free text; `Bug` (issue reference plus the reporter's words) heads `REPORT.md` |
| `Run` | hashtable splatted onto `tools/diagnostics/flow_run.ps1` verbatim: every flow_run switch is a scenario primitive ([flow-run-switches.md](flow-run-switches.md)) |
| `Frames` | `$true` passes `-Frames -FrameDir <run>\frames`. Set it here, not in `Run`: `Run.Frames` alone dumps into `<run>\flow\frames`, where the checks do not look |
| `DiagEnv` | `"A=1,B=2"` (commas or spaces separate; a bare name means `=1`). Names must match `^BRN_[A-Z0-9_]+$`; a value containing `=` or whitespace fails the run (the list did not split) |
| `FreshProfile` | `$true` parks this slot's `Profile.sav` beside the run so the game takes the first-boot path; restored afterwards |
| `ProfileFixture` | a `.sav` (absolute, repo-relative, or a bare name under `tools/tests/fixtures/`) copied over this slot's save for the run; the original is parked and restored, the post-run save is kept as `Profile.sav.after` |
| `ProfileFixtureSha256` | optional pin of the fixture's SHA-256; a mismatch refuses the run (exit 2) |
| `Setup` | a stimulus that must run while the game is up (below) |
| `Checks` | the checks, evaluated after flow_run returns; required and non-empty |
| `Solo` | `$true`: `run_all -Parallel` holds it back and runs it alone on slot 0 after the batch (frame-rate, wall-clock or desktop-foreground measurements) |
| `Pair` | marks a pair descriptor ([pair-cases.md](pair-cases.md)); run_case refuses it |

**Run keys the runner owns** (do not set them in a case): `OutDir`, `FrameDir`, `LockTimeoutSec`,
`MaxConcurrentOtherGames`, `Slot`, `GameDir`, `WorkingDirectory`. run_case also reads
`Run.NoLock`, `Run.StrictGameOwnership`, `Run.AllowConcurrentGames` (Boolean) and
`Run.MaxConcurrentOtherGames` (1..100; above 1 needs `AllowConcurrentGames`), and re-reads
`Run.MenuScript` and `DiagEnv` after `Setup` so a Setup block can compose them.

The private staged mode (`GameDir` + `WorkingDirectory` as sibling `<stage>\slot` and
`<stage>\data` folders, a positive `-Slot`, `Run.StrictGameOwnership`) exists for strict
private runs; ordinary cases never need it.

## Setup: a stimulus that runs while the game is up

`Checks` run after flow_run returns, which is wrong for anything that must happen during the run.
`Setup` is an optional scriptblock run_case calls just before the boot (after taking the box lock)
with one context hashtable, and it returns nothing or a `System.Diagnostics.Process`:

```powershell
Setup = {
  param($ctx)   # Root, RunDir, Slot, Case, GameDir, WorkingDirectory, UsesPrivateStage,
                # SlotCommandRoot, GameLog (THIS slot's live BrnGame.log)
  Start-Process powershell -PassThru -ArgumentList ... `
    -RedirectStandardOutput (Join-Path $ctx.RunDir 'thing.log')
}
```

- A returned process that outlives the run is stopped, but only if its image path and start time
  still match what run_case recorded (never a PID-only kill).
- Write the stimulus's evidence into `$ctx.RunDir` and read it from a `Script` check there: a
  helper that writes into a shared scratch folder is one stale file away from scoring a run against
  somebody else's stimulus.
- Poll `$ctx.GameLog`, never `build\game\BrnGame.log`: slot n has its own log.
- Setup may set non-`BRN_*` environment for the game (the pair cases set `BP_LAN*` there); those
  pass flow_run's wipe by inheritance.
- Existing Setup helpers: `tools/tests/offline/quiet_background_keys.ps1` (real desktop keys while
  another window holds the foreground) and `tools/tests/tools/VW_DEFORM_debugkeys.ps1` (the in-game
  debug UI through the debug-key channels; see `debug-menu-campaign`).

## Check kinds (`_checks.ps1`)

Every check is a hashtable with `Kind` and `Name`; it returns `@{ Pass; Detail }`. A check that
cannot be evaluated, or that throws, FAILS with the reason in `Detail`.

| Kind | fields | passes when |
|---|---|---|
| `NewAsserts` | optional `Known` = path to a regex list (default `tools/tests/known_asserts.txt`) | every `[ASSERT n] <msg>` family (digits folded to N, `(file:line)` and `[repeat ...]` stripped) matches a listed regex. Detail names each new family with its count and file:line: the first thing to read on a red run |
| `LogCount` | `Pattern` (regex), `Min` and/or `Max` | the number of matching log lines is in range |
| `LogMatch` | `Pattern`, `Expect` (`$true` default = must appear, `$false` = must not) | presence matches `Expect` |
| `LogValue` | `Pattern` with a named group, `Group`, `Agg` (`max` default, `min`, `mean`, `first`, `last`, `any`, `all`), `Min`/`Max`, optional `After='<cue>'` | the aggregate is in range (`any`: one value in range; `all`: every value in range). No matching value FAILS: "the witness never fired" |
| `Mark` | `Phase` (the final phase), or `Cue` plus optional `Expect = $false` | the final phase matches, or the cue fired (did not fire) |
| `Frame` | `At` (cue name, `'last'`, or an integer frame index), `Offset` (frames from there), `Region`, `Stat`, `Min`/`Max` | the frame statistic is in range |
| `FrameRatio` | `At`, `Offset`, `RegionA`, `RegionB`, `Stat`, `Min`/`Max` | statA / statB is in range |
| `Script` | `Script = { param($ctx) ...; @{ Pass = ...; Detail = '...' } }` | it returns `Pass = $true`; returning nothing FAILS |

- `$ctx` for a `Script` check: `Log` (path), `LogLines`, `Marks` (cue -> `@{ Secs; Frame; Fired }`),
  `MarksText`, `Phase`, `Asserts`, `FrameDir`, `RunDir`, `Case`, `CueRegex`.
- `After='<cue>'` keeps the lines from the first line that matches that cue's regex. A cue name
  flow_run does not know is **silently ignored** (every line is used), so copy names from the cue
  table below.
- "The car moved": `Get-DriveSegment $ctx.LogLines` (needs `-MotionProbe`) returns `Known`,
  `Path`, `Net`, `Samples`, `FromSample`, `ToSample`, `Respawns`, `Wrecks`, `Teleported`. It measures
  from the teleport seat (no teleport: the last placement jump before the throttle) up to the first
  respawn; a >20 m step between samples is a placement, and wrecks are reported, not folded in.
- A check that normalises against the whole run changes meaning when the run's composition changes:
  `camera_shake_smash` divides by every other frame in the run, so it carries neither `SkipIntro`
  nor `AcceptGap` (its banner has the measurements).
- A `LogValue` on a rare witness needs the run's world time: some soak witnesses fire about once
  per tens of seconds of driving, so those cases keep their driving time and only lose the boot.

## Cue names

run_case reads the cue table out of `flow_run.ps1` itself (its `$cues` array), so `At`, `Cue` and
`After` cannot drift from it. Each cue is anchored to a log transition and records the newest
dumped frame at that instant.

| cue | fires on |
|---|---|
| `flyby` | the new-profile intro fly-by (`[Intro] state 9 -> 3`) |
| `newprof` | `isNewProfile=0`: this boot found a profile (the returning path discriminator) |
| `ingame` | `InGame: OnEnter -> GUI FSM stage 5` |
| `jystart` | the start-of-game junkyard entry completing (car select transition in) |
| `carsel`, `livery` | `Entering Car Select`, then the livery screen |
| `accept`, `exitjy` | the car-select ACCEPT, then `ExitJunkyard` |
| `strfin` | `signalling StreamingFinished`: the junkyard exit, CARSELECT -> DRIVING |
| `e-junc`, `e-case20`, `e-start`, `e-count`, `e-inprog` | the event-start ladder; `e-inprog` is a contract cue nothing prints yet, and the `[evt-flow]` rungs print only with `BRN_PROP_DIAG` |

Phases: BOOT -> FLYBY -> CARSELECT -> DRIVING. A returning boot may go straight from BOOT to
CARSELECT; with a profile and no junkyard entry, `newprof` + `ingame` held for 5 s promote to
DRIVING.

## Frames

- Dumped every 30 presents by default; `Run.FrameEvery = 1` for a transition (30 times the frames
  and disk). A UI animation judged off a 30-present dump measures the sampler, not the game.
- flow_run refuses to start a dump below `-MinFreeGB` (25 by default): a dump can reach 16 GB.
- Through `DiagEnv`: `BRN_FRAME_DUMP_MAX=<n>` caps the frame count; `BRN_FRAME_DUMP_ARM=<latch>`
  holds the dump until a game-side latch fires (`slomo`, `ram[:<speed>]`, `skid`, `dv`, `x15`,
  `spark`, `assert`; any other value is the swerve-camera latch).
- Regions are `x0,y0,x1,y1` in pixels, or fractions when every component is <= 1.0. Prefer
  fractions: the frame size follows the `config.ini` beside the exe. Never edit slot 0's
  `build\game\config.ini`; a case that needs another size writes a private slot's `config.ini` in
  Setup (`vw_bloom_moving_1440.ps1`).
- `py -3 tools/tests/frame_stats.py <frame.bmp> --stat <stat> [--region ...]` prints one number;
  `--all` prints every stat as JSON. Stats: `lum_mean`, `lum_std`, `dark_frac` (luma < 16),
  `bright_frac` (> 240), `r_mean`, `g_mean`, `b_mean`, `sat_mean`, `edge_mean`.
- Open the frames before writing any sentence that begins "it does not draw".

## known_asserts

- One regex per line (PowerShell `-match` against the message with the `[ASSERT n]` prefix and the
  trailing `(file:line)` / `[repeat ...]` stripped); `#` starts a comment.
- It is not a licence to ignore asserts: a listed family still counts in `asserts=`, and a lane
  whose bug is one of them checks it explicitly with `LogCount`. Keep the list short and dated;
  remove a line the day its family stops firing on a baseline run.
- Lane lists (`known_asserts_hud.txt`, `known_asserts_net_race.txt`) are named with
  `Known = (Join-Path $PSScriptRoot '..\known_asserts_<x>.txt')`, never an absolute path.

## Outputs

| file | content |
|---|---|
| `result.json` | `case`, `bug`, `area`, `label`, `when`, `run_dir`, `slot`, `verdict`, `expected`, `as_expected`, `phase`, `asserts`, `flow_exit`, `checks`, `provenance` (`exe_mtime`, `exe_size`, `exe_sha`, `exe_b5`, `b5_head`, `parent_head`, `b5_dirty`) |
| `REPORT.md` | the same for people, plus `marks.txt` |
| `..\latest.json` | the newest run of this case |
| `Profile.sav.aside`, `Profile.sav.after` | the parked save and the game's save (FreshProfile / ProfileFixture) |
| `flow-terminal.json`, `flow\terminal-status.json` | strict runs only: the terminal receipt `-NoRun` re-reads |

The exe stamp is taken again after flow_run returns, because a queued run can wait out somebody's
build; flow_run's `[flow] exe <sha> b5=<head>` line, printed under the lock, is the identity.
