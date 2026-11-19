---
name: bug-test
description: >-
  Prove what the running game does through the tools/tests harness: write a case, see it fail
  RED on the current build (run_case.ps1 -ExpectFail), fix, rebuild under the box lock
  (build_exe_locked.ps1), see it pass GREEN, and report both REPORT.md paths. Covers run_case /
  run_all / run_pair / slots, the case schema and check kinds (NewAsserts, LogValue, Mark, Frame,
  Script), Setup, ProfileFixture / FreshProfile, flow_run.ps1 switches (-Drive, -Teleport,
  -MenuScript, -ShoulderAt, -DiagEnv), witness lines ([FLAG PC witness] behind a BRN_* variable),
  marks.txt verdicts (DRIVE, THROTTLE, POLL), frames and frame_stats.py, the box lock, and the
  b5-decomp/tests unit runners. Load it before you "run the game", write or run a "test case" or
  harness case, add a witness, read an [ASSERT] from a run, or claim that a fix works at runtime.
---

# bug-test

**What it is for.** Proving at runtime what the game does: that a bug reproduces, that a fix
holds, that a code path actually runs. A bug test is one scenario run through the game plus a
list of checks over the evidence the run leaves (the log, the flow marks, dumped frames). It is
the runtime counterpart of the per-TU compile gate: the gate says the code builds, a case says the
game *behaves*. Also covers the offline unit regressions in `b5-decomp/tests/`.

**Not for.** Deciding what the console does (`console-evidence`), classifying a behaviour
difference (`diagnose-parity-bug`), build or link failures (`build-and-link`), committing
(`land-change`). The menu-coverage, debug-menu and sound campaigns have their own skills and use
this one for every run.

## Before you spend box time

The box runs one game per slot and every lane shares it. Do the offline work first.

1. **Know the question.** Which number or log line does the bug move? Which code must be
   *dispatched* for the fix to matter, and which line proves it ran in this flow?
2. **Read before you run.** The console's code for the path (`console-evidence`), the witness
   you will need, and the evidence earlier runs already left under `scratch\bugtest\runs\` (a local
   input): a capture is not evidence until someone opens it.
3. **Re-score without booting.** `run_case.ps1 -Case <name> -NoRun -RunDir <existing run dir>`
   evaluates the checks against a run on disk: no boot, no lock. Iterate on checks this way.
4. **Check the box.** `tools/tests/tools/PROOF_boxfree.ps1` prints FREE or BUSY for slot 0 and
   touches nothing else. BUSY is somebody's live measurement.

## The procedure: RED -> GREEN, or it is not a test

1. **Write the case first**, against the bug as reported (`tools/tests/cases/`, one `.ps1` that
   returns one hashtable; schema in [case-schema.md](references/case-schema.md)). Check the number
   or line the bug changes, not "no asserts" alone, unless the bug *is* an assert.
2. **No line carries that number?** Add a witness in the code you are fixing (rules below), build,
   then write the check against it.
3. **Run it RED** on the current build: `run_case.ps1 -Case <name> -ExpectFail -Label pre-fix`
   must exit 0, i.e. the checks FAIL, and the failure detail must show the bug's signature. If it
   passes, the case does not measure the bug: fix the case, not the game.
4. **Fix the game.** Compile-check your own files (`python tools/work/selfcheck.py <file.cpp>`),
   then rebuild with `build_exe_locked.ps1 -Label <lane>`: one build at a time, never during a run.
5. **Run it GREEN**: the same command without `-ExpectFail`, `-Label post-fix`.
6. **Prove dispatch.** Point at the line in the GREEN log that says your changed code ran. If the
   code cannot be reached in this flow, say so; never let `asserts=N` imply it was exercised.
7. **Report** the RED and the GREEN `REPORT.md` paths, each run's `[flow] exe <sha> b5=<head>`
   line, and whether `REPORT.md` says the b5 tree had uncommitted changes. Both runs are the proof.

A case never seen RED proves nothing about the fix. A check that cannot be evaluated (no frame,
no witness line, unknown cue) FAILS rather than passes, on purpose: never weaken it to go green.

## Running

```
powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case <name> [-ExpectFail] [-Label <txt>] [-Slot <n>]
powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case <name> -NoRun -RunDir <run dir>
powershell -ExecutionPolicy Bypass -File tools\tests\run_all.ps1 [-Filter 'traffic_*'] [-Parallel <k>] [-ExpectFail] [-Label <txt>]
powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case <pair case> [-SlotA 1 -SlotB 2]
powershell -ExecutionPolicy Bypass -File tools\tests\slots.ps1 -Make <k> | -Slot <n> | -List | -Clean
powershell -ExecutionPolicy Bypass -File tools\tests\build_exe_locked.ps1 -Label <lane>
```

- Exit codes (run_case, run_pair): 0 = verdict as expected (PASS, or FAIL under `-ExpectFail`),
  1 = not, 2 = the runner could not run the case (bad case file, no exe, flow_run refused).
- Run them with `powershell` (Windows PowerShell 5.1) as shown: it is the host the scripts spawn
  for their own children.
- A queued run waits for the box (`[box] waiting for the box` is not a hang); run_case waits up to
  `-LockTimeoutSec 7200`. Start it where your tool will not kill it mid-wait (a background job),
  or lower the timeout and come back.
- **Slots.** `-Slot n` runs a copy of the exe from `build\game_slots\<n>\` with its own log, input
  channels, lock and `Memcard_<n>` profile; the data is shared live from `build\game`. Slot 0 is
  `build\game` itself. `run_all -Parallel k` deals cases onto slots 1..k and never uses slot 0;
  pairs never use slot 0. Stage slots with `slots.ps1 -Make <k>`.
- Parallel runs share one GPU and CPU. A check on a frame rate, a wall-clock duration or anything
  counted per frame must run alone: mark the case `Solo = $true` and run_all runs it after the
  batch, on slot 0.
- Before a parallel sweep, run `baseline_boot_drive` alone: sixteen failures blaming one missing
  exe is a slow way to learn one fact.
- Keep `MaxSeconds` as short as the scenario allows (flow_run's default is 275 s). Read your own
  boot-to-DRIVING from `marks.txt` and add the scenario's tail; `SkipIntro` + `AcceptGap` cut the
  boot (returning player about 16 s instead of 23 s, measured 2026-09-06).
- Direct `flow_run.ps1` runs (no case) land in `scratch\flow_run\<timestamp>\`; prefer a case.
  Every switch, one line each: [flow-run-switches.md](references/flow-run-switches.md).

## Reading a run

Everything lands in `scratch\bugtest\runs\<case>\<timestamp>\`; `latest.json` beside the
timestamped folders points at the newest. In each run folder:

| file | what |
|---|---|
| `flow\BrnGame.log` | the game's log for this run |
| `flow\marks.txt` | flow_run's summary: cues, phase, asserts, the run's recipe, the verdict lines |
| `frames\bb_NNNNNN.bmp` | dumped frames, only when the case sets `Frames = $true` |
| `flow_run.console.log` | everything flow_run printed: schedule lines, the `[flow] exe` line |
| `result.json`, `REPORT.md` | the verdict, every check's detail, exe and commit provenance |

Read these `marks.txt` lines before any conclusion:

- `asserts=N phase=P`: P is BOOT, FLYBY, CARSELECT or DRIVING. A cue line gives the seconds and
  the frame dumped at that instant; `(never)` means the cue did not fire.
- `DIAGENV`, `TELEPORT`, `SWEEP`, `SLOT`, `SKIPINTRO`, `ACCEPTGAP`, `AUDIO`, `STARTEVT` ...: the
  run's recipe. Two runs are comparable only when these match.
- `EXIT`: `harness-stop` is the normal end; `self code=0x...` is the game dying on its own
  (0xC0000005 access violation, 0xC00000FD stack overflow, 0xC0000409 fast-fail, 0xC0000374 heap
  corruption).
- `DRIVE` (needs `-MotionProbe`), `POLL`, `THROTTLE`, `SIMPAUSE`, `GAS`: did the car move, was the
  harness loop starved, was the stimulus applied on time, was the world frozen, did the press reach
  the car. A run whose THROTTLE line says VOID measured nothing.
- `MENUSCRIPT done=k/n state=...`, one line per step, each ending `(log line <n>)`.
- `LADDER`: the event-start rungs; `BLIND` means `BRN_PROP_DIAG` was not set.

`[flow] exe <sha> b5=<head>` comes from the exe's link-time provenance stamp. "THIS EXE WAS
BUILT IN ANOTHER TREE" or "NO provenance stamp" means the numbers are not attributable to your
checkout; a hand-staged exe is named wrongly. The shared checkout also means an exe can contain
another lane's uncommitted code: record `git status` with every run you will cite.

## Witness lines: the log is the oracle

Most bugs are not visible as an assert. The case needs a **witness**: a log line the game prints
with the number the bug moves. If none exists, add one in the code you are fixing:

- named `[FLAG PC witness]`, tagged `[<lane>]`;
- first-N or once, **never per-frame unbounded** (a 6-car witness once flooded 733k lines and the
  harness aborted at its 128 MB log limit);
- opt-in behind a `BRN_*` variable read once, which reaches the game **only through the case's
  `DiagEnv`**: flow_run wipes every `BRN_*` variable before launch, by design (a short kept list
  aside), and applies `DiagEnv` after the wipe;
- when its budget runs out it prints that it truncated, so its silence cannot read as absence.

Before believing any witness's zero, read its filter, its budget and its sample period: a probe
can be structurally unable to print what you are looking for. Prefer load-robust quantities
(positions at rest, counts, whether a line fired at all) over per-frame or wall-clock numbers.
The variables the harness itself manages: [harness-environment.md](references/harness-environment.md).

## Profiles

- `build\game\Memcard\Profile.sav` (slot n: `build\game\Memcard_<n>\Profile.sav`) is the box's
  shared test profile. Whether it exists decides the boot path: returning player or first boot.
- A known progression state: `ProfileFixture = '<file>.sav'` (a bare name under
  `tools/tests/fixtures/`, or a path). run_case copies the fixture over the slot's save, parks the
  original beside the run, puts it back afterwards and keeps the game's save as
  `Profile.sav.after`. The first-boot path: `FreshProfile = $true`. Never both.
- A case that can bank progress (an event finish, a medal, a discovery, a win) runs on a fixture so
  the box's save comes back unchanged.
- Never copy a save over the box's profile by hand and never delete it. `PROOF_run.ps1` copies its
  `-Pinned` file over `build\game\Memcard\Profile.sav` before and after the run and keeps no copy of
  what was there; its default `-Pinned` is a wave-local scratch file. Use it only when you mean it.

## Unit regressions (b5-decomp/tests)

- Most `run_<name>.py` files in `b5-decomp/tests/` compile a small fixture with the project's MSVC
  flags and run it. Offline: no box, no lock. Example: `python b5-decomp/tests/run_air_ram.py`.
- If the environment sets `NoDefaultCurrentDirectoryInExePath` (Claude Code's shells do; check
  `env | grep -i NoDefaultCurrent` or `$env:NoDefaultCurrentDirectoryInExePath`), cmd.exe will not
  start the freshly built `regression.exe` from the current directory and the runners fail with
  "is not recognized". Unset it for the run: in Bash
  `env -u NoDefaultCurrentDirectoryInExePath python b5-decomp/tests/run_air_ram.py`, in
  PowerShell `Remove-Item Env:\NoDefaultCurrentDirectoryInExePath` first. A verdict taken with it
  set is void.
- Some of them boot the game, which is box time: the `*Live.ps1` files are run_case cases
  (`run_case.ps1 -Case b5-decomp/tests/BootOrderLive.ps1`), and `run_rival_organic.py`,
  `run_debug_menu.ps1`, `run_easydrive.ps1`, `run_street_ui.ps1`, `run_junkyard_customization.ps1`
  run the harness themselves. `run_hardware_init_live.ps1` launches the exe with no box lock (it
  only refuses when a game is already running) and changes this logon session's accessibility
  settings: run it only on an idle box.

## Never

Each line has its reason and its check in [evidence-traps.md](references/evidence-traps.md).

- Never treat a green run as proof that your change ran: name its dispatcher and the line showing it fired.
- Never accept a case you have not seen RED on the unfixed build, or a check you have not seen fail.
- Never trust a check before asking what question it actually answers; an adjacent question is worse than none.
- Never read the log's last line as where the game stopped: an assert halts it; read the first `[ASSERT` forward and look at the window or the frames.
- Never assume which car drove: the junkyard flow accepts the default car (the Cavalry) unless the case moves the carousel or swaps the car.
- Never trust an opt-in input you did not see armed: grep `flow_run.console.log` for its schedule line (a one-entry `-ShoulderAt` once never pressed under Windows PowerShell 5.1).
- Never pass `-NoLock`, and never launch a game beside a harness: the two kill each other's runs.
- Never run boot_test, the `hud_*` scripts, popup_capture, profile_test or saveicon_capture while any slot or pair runs: they kill every Burnout_PC by name.
- Never abandon a run with its harness alive: stop the powershell process you started, or the box stays locked; never kill a harness or game you did not start.
- Never take a timing, frame-rate or physics-sensitive number on a crowded box: the sim is frame-coupled.
- Never export a `BRN_*` variable in your shell for the game: use `DiagEnv`; and never compare runs whose `DIAGENV` lines differ.
- Never put a capability in `DiagEnv` when flow_run has a switch for it (`-StartEvent`, `-Showtime`, `-EventFsm` ...).
- Never treat a placed car (`-Teleport`, `-CrashSweep`) as an ordinary one: placement resets it into a 1.5 s invincible absorption set.
- Never report a result taken through `-DebugFinishPos` or `-WinTeleport` as a genuine win.
- Never overwrite or delete a save by hand, and never edit slot 0's `build\game\config.ini`.
- Never re-bank a golden (`-WriteGoldens`) without looking at the frame, or through a non-default run.
- Never edit another lane's file to get `build_exe_locked.ps1` through: report the error and retry later.
- Never run any game build other than the decomp's own exe: other builds are byte oracles to read, never to launch (a Xenia trace for a goal is the maintainer's to capture: `goal-scoping`).

## Tools

| path | role |
|---|---|
| `tools/tests/run_case.ps1` | one case: flow_run with the case's scenario, then the checks; writes `result.json` + `REPORT.md` |
| `tools/tests/run_all.ps1` | every case (or `-Filter`), one table; `-Parallel k` on slots 1..k; skips pair cases |
| `tools/tests/run_pair.ps1` | a pair case on two slots, one verdict ([pair-cases.md](references/pair-cases.md)) |
| `tools/tests/slots.ps1` | build / refresh / list / clean the per-slot launch folders |
| `tools/tests/build_exe_locked.ps1` | rebuild the exe under the box lock (`-Label`, `-Jobs`, `-CpuLimit`, `-TimeoutSec`, `-LogDir`) |
| `tools/tests/_checks.ps1` | the check kinds and `Get-DriveSegment` |
| `tools/tests/frame_stats.py` | one number about one region of one dumped frame |
| `tools/tests/known_asserts.txt` | assert families that are another lane's noise (lane lists: `_hud`, `_net_race`) |
| `tools/tests/fixtures/` | pinned `.sav` files for `ProfileFixture` |
| `tools/tests/tools/PROOF_run.ps1` | a case under the box lock with a pinned save copied in before and after (`-Repeat`, `-Pinned`) |
| `tools/tests/tools/PROOF_batch.ps1` | a list of cases through PROOF_run into a progress file |
| `tools/tests/tools/PROOF_boxfree.ps1` | slot-0 lock FREE or BUSY, right now |
| `tools/tests/tools/PROOF_waitbox.ps1` | poll until the slot-0 lock is free (`-MaxSec`) |
| `tools/tests/tools/PROOF_waitexe.ps1` | poll until `build\game\Burnout_PC.exe` changes, or a `-Claims` file grows (`-MaxSec`) |
| `tools/tests/tools/PROOF_waitfile.ps1` | poll until a file gains a line matching `-Pattern` |
| `tools/diagnostics/flow_run.ps1` | boots the game, drives the flow, writes `marks.txt`; every case runs through it |
| `tools/diagnostics/_box_lock.ps1` | the per-slot box mutex every game-launching harness takes |
| `tools/diagnostics/frame_gate.ps1` | provenance-checked score of the post-handover chase frame against its golden |
| `tools/diagnostics/carselect_frame_gate.ps1` | the same for the car-select screen (`-BySignature` when marks are missing) |
| `tools/diagnostics/boot_test.ps1` | older boot/menu loop: real keystrokes and desktop captures into the foreground window |
| `tools/diagnostics/crash_sweep_batch.ps1` | one placed crash per boot over a heading x speed grid (`-MinDamageableSeconds 1.6` clears invincibility) |
| `tools/diagnostics/crash_sweep_report.py` | segments a `-CrashSweep` log into shots and scores each; drops invincible shots |
| `tools/diagnostics/crash_episode_compare.py` | two crash_sweep_batch tags, cell by cell; marks pre-damaged boots VOID |
| `tools/diagnostics/crash_roll_census.py` | counts tumble events per crash (time inverted, half rolls) |
| `tools/diagnostics/crash_impulse_ledger.py` | where a crash's impulse went (`contacts` / `ledger` / `corpus`) |
| `tools/diagnostics/roll_batch.ps1` | one crash per boot over four crash kinds (`-Kind wall/jump/showtime/carcar`) |
| `tools/diagnostics/takedown_metrics.py` | takedown-victim metrics from the rival-damage witnesses |
| `tools/diagnostics/drive_quality.py` | path, speed and turning from `[motion]`; measures after the last >20 m jump |

## Read next

- [case-schema.md](references/case-schema.md): case keys, check kinds, Setup, cues, frames, outputs.
- [flow-run-switches.md](references/flow-run-switches.md): every flow_run switch, one line each.
- [menu-driving.md](references/menu-driving.md): menu taps, `-MenuScript`, the pause ring, car select, screen diagnostics.
- [pair-cases.md](references/pair-cases.md): two instances online.
- [harness-environment.md](references/harness-environment.md): the `BRN_*` wipe, inherited and game-side harness variables, asserts.
- [evidence-traps.md](references/evidence-traps.md): why each Never line exists and how to catch it.
- `tools/tests/README.md` and the banners of `run_case.ps1`, `flow_run.ps1` and `_box_lock.ps1`.
- Skills: `console-evidence`, `diagnose-parity-bug`, `build-and-link`, `land-change`, `menu-coverage`,
  `debug-menu-campaign`, `sound-pass`, `campaign-lane`.
