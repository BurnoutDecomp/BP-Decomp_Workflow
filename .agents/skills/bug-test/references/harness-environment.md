# Harness environment

What reaches the game's environment on a harness run, and the game-side variables the harness
relies on. Sources: the environment block of `tools/diagnostics/flow_run.ps1`,
`tools/diagnostics/_box_lock.ps1`, `b5-decomp/src/GameShared/GameClasses/System/CgsHarnessSlot.h`,
`CgsAssertManager.cpp` and `CgsInputPadsPC.cpp` in the b5-decomp tree.

## The wipe, and how to get a variable through it

flow_run makes every run a default run before it adds anything:

1. A fixed list of known `BRN_*` names is cleared, then a **catch-all** clears every other `BRN_*`
   variable in the environment. Each one that was set prints
   `[flow] NOTE: <name> was set in the environment and has been CLEARED`.
2. Kept by design: `BRN_INPUT_ALLOW_BACKGROUND`, `BRN_AUDIO_MUTE`, `BRN_HARNESS_SLOT` (flow_run
   sets them); `BRN_PROP_DIAG`, `BRN_HEAP_CHECK`, `BRN_RENDER_POSTFX`, `BRN_POSTFX_MASK_TEST` (inherited
   from the shell and recorded: `[flow] INHERITED diag env` and the `DIAGENV` line in `marks.txt`);
   `BRN_DEBUG_UI_TRACE`, `BRN_EASYDRIVE_TRACE`, `BRN_STREET_UI_TRACE` (exported by the b5-decomp UI
   runners for the flow_run they launch).
3. `-DiagEnv` (a case's `DiagEnv`) is applied after the wipe and echoed as
   `[flow] DIAG ENV applied after the clear: ... -- NOT a default run`.

So exporting `$env:BRN_X=1` in your shell cannot reach the game, and it fails silently in a way
that reads exactly like a dead probe. The inherited four do ride in from your shell: two runs are
comparable only when their `DIAGENV` lines match.

`DiagEnv` grammar: entries separated by commas or spaces; `NAME=value` or a bare `NAME` (= 1).
A name must match `^BRN_[A-Z0-9_]+$`; a value containing `=` or whitespace fails the run, because
it means the list did not split. A new engine variable needs no edit to flow_run to be safe: pass
it with `DiagEnv`.

**Instruments in `DiagEnv`, capabilities on switches.** Anything that changes what the game does
(starts a mode, ends an event, skips a gate, drives the car) has its own flow_run switch, recorded
on its own `marks.txt` line: `-StartEvent`, `-EventFsm`, `-SkipTrainingTip`, `-Showtime`,
`-ShowtimeIgnoreProgression`, `-DebugFinishPos`, `-WinTeleport`, `-AIDrive`, `-Teleport`,
`-CrashSweep`, `-CrashPlayer`. The probes with switches (`-MotionProbe`, `-TriCacheProbe`,
`-TractionProbe`, `-DeformTrace`, `-Frames`) are switches so the run banner names them.

Arming `BRN_DENT_PROBE` also arms `BRN_CRASH_RESPONSE_DIAG` (the "DENT GUARD"): a `[dent]` depth
is unreadable without the `[absorb]` line for the same frames.

Variables that are not `BRN_*` pass by inheritance: the pair variables (`BP_PAIR_*`), the LAN
transport (`BP_LAN`, `BP_LAN_NAME`, set in a case's `Setup`), and `BPH_KEEP_SLOT_EXE=1`, which keeps
the exe already staged in a slot instead of refreshing it from `build\game` (a frozen build for a
regression sweep; the `[flow] exe` line still names the exe that ran).

## What flow_run sets

| variable | effect |
|---|---|
| `BRN_INPUT_ALLOW_BACKGROUND=1` | the harness channels and the assert-release event work without window focus; the host keyboard is refused (announced once), the XInput pad is not |
| `BRN_AUDIO_MUTE=1` (cleared by `-Audio`) | one `SetVolume(0)` on the mastering voice; the device opens and every fill runs. The game prints `master volume=` on each open, so "this run was silent" is checkable |
| `BRN_HARNESS_SLOT=<n>` (slot n > 0; removed for slot 0) | suffixes the single-instance mutex, the input channels, the assert-release event and the `Memcard` folder with `_<n>` |
| `BRN_FRAME_DUMP=<absolute dir>`, `BRN_FRAME_DUMP_EVERY` | `-Frames`, `-FrameDir`, `-FrameEvery` |
| `BRN_MOTION_PROBE`, `BRN_TRICACHE_PROBE`, `BRN_TRACTION_PROBE`, `BRN_DEFORM_TRACE`, `BRN_CRASH_PLAYER` | the probe and crash switches |
| `BRN_CAR_TELEPORT[_ARM_DISTANCE]`, `BRN_CRASH_SWEEP[_SHOTS,_SETTLE,_MAX,_ARM_DISTANCE]` | `-Teleport`, `-CrashSweep`, `-Jump` |
| `BRN_START_EVENT`, `BRN_EVENT_FSM`, `BRN_SKIP_TRAINING_TIP`, `BRN_AI_DRIVES_PLAYER`, `BRN_DEBUG_FINISH_POS` / `_AT`, `BRN_WIN_TELEPORT[_GAP,_SPEED,_LEAD]`, `BRN_SHOWTIME_IGNORE_PROGRESSION`, `BRN_START_SHOWTIME` (inert) + `BRN_SHOWTIME_WATCH` | the capability switches |

`BRN_INPUT_KEEP_KEYBOARD=1` (through `DiagEnv`) gives a harness run the keyboard back, read only
while the game's own window has the focus; `quiet_focus_input` uses it to test exactly that rule.

## Game-side levers worth knowing (pass them with `DiagEnv`)

| variable | effect |
|---|---|
| `BRN_SCREEN_DIAG=1` | `[screen] ENTER` / `[screen] MISSING STATE` for every scripted screen transition ([menu-driving.md](menu-driving.md)) |
| `BRN_CARSEL_TAPSTEP=1` | lets a harness tap step the car-select carousel |
| `BRN_DEBUG_PLAYER_CAR=<id or name>` | swap the player car once, after the junkyard (harness path, not the player's) |
| `BRN_FRAME_DUMP_MAX=<n>` | cap the number of dumped frames |
| `BRN_FRAME_DUMP_ARM=<latch>` | hold the dump until a game-side latch fires (`slomo`, `ram[:<speed>]`, `skid`, `dv`, `x15`, `spark`, `assert`; anything else is the swerve-camera latch) |
| `BRN_ASSERT_NO_SUPPRESS=1` | every repeat of an assert halts again, not only the first per site |
| `BRN_NET_*` | the PC LAN harness roles ([pair-cases.md](pair-cases.md)) |

## Asserts

- The first time each assert site (file, line) fires, the game resolves the call stack, logs it and
  **halts** until released. Repeats of that site are counted and logged (`[ASSERT n]`, so
  `asserts=N` and greps still work) but do not halt, unless `BRN_ASSERT_NO_SUPPRESS=1`.
- Released by END while the game's window has the focus, or (with `BRN_INPUT_ALLOW_BACKGROUND`) by
  the slot's named event `Local\BurnoutPC_Assert_Release[_<n>]`, which the game opens but never
  creates. flow_run creates it before launch and releases one assert per assert it sees in the
  log, at most 8 per poll with the rest carried as debt. The log says `press END to continue` on a
  halted assert: paused, not dead.
- `-ReleaseAsserts` holds the event open for the whole run (an assert storm only; `asserts=` stops
  being comparable). `-NoAssertRelease` never releases and stops the run at the first assert.
- An assert storm can starve the run without ending it (2026-08-29: a per-frame assert let a 1 Hz
  input schedule deliver one press instead of ninety). Check the assert count and the `POLL` /
  `THROTTLE` lines before believing an input- or timing-sensitive result.

## The box lock

`Enter-BoxLock` in `_box_lock.ps1` takes the named mutex `Local\BurnoutPC_FlowRun` (slot n:
`Local\BurnoutPC_FlowRun_<n>`). run_case takes it before any side effect (profile park, Setup,
the exe check) and flow_run takes it again on the same thread (a mutex is re-entrant for its
owner). `build_exe_locked.ps1` takes slot 0's lock plus the narrower `Local\BurnoutPC_ExeStage`
mutex that `slots.ps1` also takes around its exe copy, so a slot never boots a half-linked exe; a
slot run started before a build keeps the exe it started with. The lock is released when the
owning process exits, including on a crash or Ctrl+C, so nothing wedges the box permanently, but a
harness process that is still alive keeps it. On acquisition the lock clears the seven held input
channels a killed run may have stranded.
