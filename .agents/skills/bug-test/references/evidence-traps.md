# Evidence traps

Why each **Never** line in `SKILL.md` exists, and the check that catches it. Every one of these
cost real runs; none of them is a defect in game code. The general rule under all of them: a
harness and its diagnostics are code, exactly as likely to be wrong as the code they watch, and
trusted far more because their output reads like an observation.

## A green run can validate nothing

A fix to a function that never runs in the scenario passes every check, because the old code did
not run either. Recorded case (2026-09-16): a corrected virtual `Detach` on an effect owned by the
sound GlobalState shipped as "verified" after a run with only the usual known assert; nothing in
the tree ever detaches that state, so the code could not execute.

- Before a run can confirm a change, answer: what dispatches this code, and did that dispatcher
  fire in this flow? For a virtual, grep the call expression (`->Detach()`), not the qualified name,
  and separate an override's upward base call from a real entry point.
- Point at a log line that only the changed path prints (an existing witness, or a bounded one you
  add). If the code is unreachable in the scenario, say so in the report and the commit.

## See it fail first

- A case is RED on the unfixed build first (`-ExpectFail` exits 0 and the detail shows the bug's
  signature), then GREEN after the fix. A case that passes before the fix measures nothing.
- The same holds for any guard or verdict you add to the harness: build a control that makes it fail
  on purpose (inject one bogus value, run the old exe, revert only the one change). A verification
  you have not seen fail is not a verification. A new verdict can itself be the liar: the first cut
  of flow_run's `SIMPAUSE` line declared VOID a run that drove 403 m, and had to be narrowed.

## The harness can answer the wrong question

A check that answers a question adjacent to the one it claims to answer is worse than no check:
it gives a confident answer and nobody re-examines a green light. Recorded instances:

| the check | claimed to answer | actually answered |
|---|---|---|
| `-UnpauseAt` | does resume work? | does the button I tap work? Its action id had moved (Accept became 49, the map exits on 45/50) |
| the poll loop | what did the run log? | nothing once the log was hundreds of MB: it re-read the whole file each poll and held the box lock |
| the exe path | which build produced this number? | nothing: waves measured another tree's exe until the provenance stamp existed |
| a shared frame folder | where is my evidence? | a folder every run wiped: one run destroyed 420 proof frames (now per-run) |
| a `[move-probe]` line | how fast is the player? | race car 0, parked at the junkyard, while the player was car 2 |

Ask of every green light: what question does this actually answer, and is it the one I need?

## Asserts pause the game; the log tail lies

- The first occurrence of each assert site halts the game until released (see
  [harness-environment.md](harness-environment.md)). The process stays alive, so waiting for an
  exception or for the log to grow can wait forever.
- What a reporter means by "it stops" is the first assert on screen, not the last line of the log.
  Read the first `[ASSERT` forward (`grep -n "ASSERT" BrnGame.log | head`), and compare against the
  previous run's log before calling it new ground.
- `press END to continue` in the log means paused, not dead. Outside the harness, look at the game
  window (asserts are drawn there); in a harness run, open the frames.
- An assert right after a newly passing gate is the next suspect: once a gate opens, the code behind
  it runs for the first time.

## Which car drove

The junkyard flow accepts the default car (the Cavalry) unless the case moves the carousel or
swaps the car. A measurement taken on the default car says nothing about any other: one campaign
verified an engine-sound fix only on the one car whose engine already worked. Say in the report
which car drove; to choose one, see "Car select and which car drives" in
[menu-driving.md](menu-driving.md).

## An input you did not see armed

An opt-in input that never fires leaves a log identical to a dead game-side handler. Grep
`flow_run.console.log` for its arming line before reading anything else. Recorded case
(2026-09-16): a one-entry `-ShoulderAt` returned a bare object under Windows PowerShell 5.1, whose
`.Count` is `$null`, so the bumper was never pressed and two pause-ring runs were lost. flow_run now
wraps the object-returning schedule parses (`-ShoulderAt`, `-CamButtonAt`) in `@()` at the call
site; any new schedule switch that returns objects must do the same.

## One harness per slot

- Every harness kills or launches the game, so two at once destroy each other's runs, and the victim
  reads a vanished process and a truncated log as a crash in the build under test. `_box_lock.ps1`
  serialises them per slot; `-NoLock` turns that off and is never the way past a busy box.
- flow_run's kill sweep is scoped to its own slot's exe path, but the older diagnostics harnesses
  (`boot_test.ps1`, the `hud_*.ps1` scripts, `popup_capture.ps1`, `profile_test.ps1`,
  `saveicon_capture.ps1`) take only slot 0's lock and then kill every `Burnout_PC` by name: running
  one during a parallel sweep or a pair run kills those slots' games. `boot_test.ps1` also forces the
  game to the foreground and sends real keystrokes, so it takes over the desktop. In
  `b5-decomp/tests/`, `run_hardware_init_live.ps1` launches the exe with no box lock at all.
- If you stop a run (a tool timeout, a cancel), stop the powershell harness process you started, not
  only the game: the box stays locked until that process exits (recorded: the next run waited out the
  full 1800 s lock timeout). Never kill a harness or a game you did not start; that is somebody's live
  measurement. `PROOF_boxfree.ps1` and `PROOF_waitbox.ps1` probe the lock without taking it.

## A crowded box changes the measurement

- Parallel slots share one GPU and CPU, and so do other agents' builds. The engine's sim is
  frame-coupled, so a starved box can change physics (settling, tunnelling, contact resolution), not
  just frame rate; a wave can "reproduce" its blocker on a starved box with the fix already correct.
- Keep concurrent runs few; run frame-rate, wall-clock and per-frame-count checks alone (`Solo`).
  Prefer load-robust quantities: positions at rest, contact counts, whether a line fired at all.
- `-CrashSweep` is bit-deterministic (placement at a speed, cadence in sim frames): repeats of a cell
  carry no information, so spend runs on distinct cells. `-Teleport` + `-SteerScript` is wall-clock
  coupled and does spread run to run; name the recipe when quoting a spread.
- Lanes share one checkout, so a build can contain another lane's uncommitted code. Record the
  `[flow] exe` line and `git status` for every run you cite, and treat an unattributable exe's result
  as provisional.

## Environment that rides in, or does not

- `BRN_*` variables exported in your shell are wiped; only `DiagEnv` reaches the game. Recorded:
  a control run exported two probes and the game saw neither, which read exactly like dead probes.
- The four inherited knobs (`BRN_PROP_DIAG` and three render ones) do ride in from your shell: runs
  compared across shells with and without `BRN_PROP_DIAG` were not the same run (seven runs lost).
  Compare the `DIAGENV` lines.
- A capability through `DiagEnv` makes a run that calls itself an instrument run change what the
  game does; flow_run gives every capability a switch and a `marks.txt` line for that reason.

## A placed car is not an ordinary car

- `-Teleport` and `-CrashSweep` use the console's own place-on-track, which resets deformation
  into the invincible absorption set for 1.5 s: a car that hits something sooner cannot
  dent, by arithmetic, and banks no deformation momentum. Give it at least 1.5 s of travel
  (`crash_sweep_batch.ps1 -MinDamageableSeconds 1.6`) and read `[absorb]` beside any `[dent]`;
  `crash_sweep_report.py` drops such shots unless `--keep-invincible`.
- A re-placed car that recovered keeps the previous shot's dents, so shot k > 0 is a different
  experiment from shot 0; take one crash per boot for a frequency.
- A harness that uses the game's own entry point inherits that entry point's state machine:
  determinism is not representativeness.

## Results that are not wins

`-DebugFinishPos` ends the event through the console's debug finish position and `-WinTeleport`
places the car into each checkpoint. Nothing is forged downstream, but a medal earned either way
was not earned by driving: never report one as a genuine win, and run such cases on a
`ProfileFixture` so the box's save comes back unchanged.

## Saves and shared files

- The box's `Profile.sav` decides the boot path. A missing slot profile boots the first-boot path;
  run_case's `FreshProfile` park is protected from re-seeding (`slots.ps1 -NoProfileSeed`, measured
  after a first-boot case silently booted as a returning player and read as a game regression).
- Use `ProfileFixture` or `FreshProfile`; never copy a save over the profile by hand, never delete
  it, and know that `PROOF_run.ps1` overwrites it with its `-Pinned` file.
- `build\game\config.ini` (slot 0) is shared by every lane; a case that needs another resolution
  writes a private slot's `config.ini` in Setup.

## Goldens

`frame_gate.ps1` and `carselect_frame_gate.ps1` refuse to score without `-Marks` or `-NotBefore`,
because frames left by an earlier run once passed a gate at correlation 1.000. Re-bank a golden
(`-WriteGoldens`) only after looking at the frame, and only from a default run: a world-render
regression once hid for a day behind shots taken through a camera override.

## Somebody else's red build

`build_exe_locked.ps1` neither kills a running game nor fixes compile errors. If the failing file
is not yours, do not edit it: report it and retry later (`build-and-link` covers link failures).
Compile-check your own TUs with `tools/work/selfcheck.py` before you queue for the lock.

## Only the decomp runs

Run only the decomp's own exe (`build\game\Burnout_PC.exe` and its slot copies). Other builds of
the game are byte oracles: read their files (`console-evidence`), never launch them. The
behavioural oracle is people playing this build.

## Instruments that lie

Before believing a number, read what it actually measures, and on which object:

- **Which instance?** A probe can truthfully report the wrong car, the wrong slot, the wrong FSM.
- **Sample period against the event's lifetime.** A 30-frame sampler cannot see a 24-frame event; a
  flat series can be the probe, not the system. Go per-frame while the event is live.
- **Budgets and caps.** A witness that spent its line budget early prints nothing for the event you
  wanted, and its silence looks like data. Check capacity against the volume before believing an
  absence.
- **The first frame is a catch-up.** The game's first frame runs a multi-second sim step, so an arm
  that latches on a cumulative count fires during boot.
- **A max cannot show a stall.** Prefer a histogram plus a distinct-value count.
- **A saturated ratio is as suspicious as a frozen max.** "124/124 applies were impulse-limited"
  was true by arithmetic on an invincible car. Before quoting a ratio, ask whether its condition
  could have gone the other way at all.
- **Provenance.** `[flow] exe <sha>` comes from the link-time stamp: a hand-staged exe is named
  wrongly, so verify by a string only that build prints. `Copy-Item` keeps the source file's mtime,
  so a hand-placed source can be older than its objects and the "before" build comes out byte
  identical (an A/A test): assert it is newer than its objects.
- **Measurement rules.** `drive_quality.py` still measures from the last >20 m placement jump, so a
  wreck and respawn truncates its path; `Get-DriveSegment` (and `marks.txt`'s `DRIVE`) measure from
  the teleport seat to the first respawn.
- **Locale.** The harness parses every number with InvariantCulture. A script that declares a list
  parameter `[double[]]` and is called through `powershell -File` receives `"12,20"` as one string
  that the box's locale can read as 1220 (measured by `roll_batch.ps1`, which now takes strings).
  `crash_sweep_batch.ps1` still declares `-Headings` / `-Speeds` as `[double[]]`: call it from a
  PowerShell session with `&`, not through `powershell -File`. New list parameters take strings and
  parse them invariantly.
- **A capture is not evidence until someone looks at it.** Five runs once reported a results screen
  that "does not draw" while their own frames showed it on screen.
