---
name: menu-coverage
description: >-
  User-invoked only: the menu coverage campaign, making every menu that shows in the
  original game show in the decomp. The coverage-map method (each flow's registered state
  pool against the console's FSM Lua in build/game/FSM/*.BUNDLE, bodies per screen, hollow
  shells), the BRN_SCREEN_DIAG witness ([screen] ENTER, [screen] MISSING STATE), the rule that
  the vtable outranks the DWARF for whether an override is real
  (tools/re/vtable_override_audit.py), the usual reasons a screen does not show (an
  apt-component gate that never passes, an assert parking the game, a gate flag raised but
  never dropped, a consumer missing its case, a payload cast, an unmaterialised GUI bank, a
  missing mount), and driving menus in the harness (bug-test). Load only when the user
  explicitly asks for the menu coverage campaign.
disable-model-invocation: true
---

Stop unless the user explicitly asked, in their own words, for the menu coverage campaign. A single broken screen met in passing is `diagnose-parity-bug`.

# Menu coverage

**Goal:** every menu that shows up in the original game shows up in the decomp. Scope: the
offline path exhaustively; online screens get a status table, because they also need a live
online service that code alone cannot show or verify. **Proof:** a runtime witness plus
frames for every screen (`bug-test`), never "the file exists".

Not for: a single screen bug (`diagnose-parity-bug`); writing or running cases (`bug-test`);
reconstructing a TU (`reconstruct-tu`); the debug menu (`debug-menu-campaign`).

## 1. Build the coverage map

1. **The pools.** Each GUI flow registers its states with `Construct(CgsIDCompress("..."))`:
   the screen flow in `b5-decomp/src/GameSource/Gui/Flow/Screen/BrnScreenFlow.cpp`, the HUD
   flow in `b5-decomp/src/GameSource/Gui/Flow/HUD/BrnHudFlow.cpp`, the overlay flow in
   `b5-decomp/src/GameSource/Gui/Flow/Overlay/BrnOverlayFlow.cpp`.
2. **The console's FSMs.** `build/game/FSM/*.BUNDLE` (produced by `build data`) are bnd2
   containers holding plain Lua: a `stateNames` table (`["<id>"] = "<NAME>"`) and one
   `NextState_<id><NAME>( eventId )` function per state. `BRNSCREENFSM.BUNDLE` is the screen
   flow only; the HUD flow switches between several bundles over a session (the boot,
   free-burn, event and crash FSMs among them: grep the `RunFsm` posts for which runs
   where), and `BRNOVERLAY.BUNDLE` is the overlay's.
3. **Intersect.**
   - In a pool but in no FSM: unreachable in the original too. "Fixing" it would be a
     divergence, not a fix.
   - In an FSM but in no pool: a genuinely missing state; the game will print
     `[screen] MISSING STATE` when the script asks for it.
   - Absent from `BRNSCREENFSM.BUNDLE` is not unreachable: check the other flows' FSMs
     (`PAUSED`, for one, lives in the HUD flow's).
4. **Per reachable screen:** the console's functions against our bodies
   (`python tools/re/hasbody.py <Class::Method>`, `work show <tu>`, `work audit <tu>`). A
   header-only shell inherits the do-nothing `CgsGui::State` base and registers for no
   events, so nothing on it works; a state only receives the GUI ids it registers for.
5. **Overrides: the vtable outranks the DWARF.** The DWARF declares methods that the
   console's vtable fills with a shared ICF-folded empty body, so a declared override is
   real only if the console's slot holds a distinct body. Check with
   `python tools/re/vtable_override_audit.py --table <vtable address>`; the generated report
   is `progress/VTABLE_OVERRIDE_AUDIT.md`. Detail and traps: [references/coverage-map.md](references/coverage-map.md).
6. **Witness it.** Run with `BRN_SCREEN_DIAG=1` in `DiagEnv`: every scripted transition
   passes `ScriptedFsm::SetState`
   (`b5-decomp/src/GameShared/GameClasses/Fsm/CgsScriptedFsm.cpp`), which prints
   `[screen] ENTER '<to>' (from '<from>') seq N`, and `[screen] MISSING STATE '<id>'` when the
   pool lacks the requested state. Frames prove it drew.
7. **Record the map** in a tracked report under `progress/` (one row per state: flow,
   reachable per the FSM, bodied, witnessed, frame), so the next agent starts from it.

## 2. Why a screen does not show

One line each; the method behind each is in [references/triage.md](references/triage.md).

- **A gate that never passes** hides the whole screen: `GuiCache::AreAllAptComponentsInitialised`
  waits on every expected apt component. With `BRN_SATNAV_DIAG=1` the cache prints
  `[cnav-diag] expect ...`, `[cnav-diag] ONLOAD ...` and the still-unloaded hashes for the
  screen flow: diff expected against loaded.
- **An assert parks the game** until released, so a menu that ignores every tap is often
  sitting on one: read the run log's `[ASSERT n]` lines first, especially right after a
  gate starts passing.
- **A gate flag with a raise and no drop**: a state that waits for X re-runs the wait on
  every re-entry (pause, unpause), so the flag's drop must exist too.
- **One producer, many consumers**: for each game action or GUI event, every consumer's
  `case N:` must exist; reaching one consumer is not being consumed.
- **An entry without its exit**: a state machine whose entry is reconstructed but whose
  exit arms are gated is a trap, not a partial.
- **A payload cast**: a queue record's layout is whatever its producer posted
  (`b5-decomp/src/GameShared/GameClasses/Gui/CgsGuiModule.h`); casting it to the wrong
  struct shifts every field.
- **An unmaterialised GUI bank**: a request to a bank the PC resource servicer does not
  materialise "completes without IO" and asserts at first use; grep the log for
  `not materialised on PC`.
- **A stalled resource handler**: grep the log for `request handler DEFERRED:`.
- **A caption left unrecovered** in a pointer table is usually one `.rdata` read
  (`tools/re/x360rd.py`).
- **Not in the exe**: a reconstructed screen whose `.cpp` is not mounted in
  `tools/build/build_game_exe.bat` is not built (`progress/linked_files.json` lists what the
  compiler opened; `build-and-link`).

## 3. Driving menus

The harness switches are documented in `bug-test` and in the `param()` block of
`tools/diagnostics/flow_run.ps1`. For menus:

- Most front-end menus are reached in the world (pause, Easy Drive), so plan the route from
  the FSM Lua, not from the screen list: a menu row can lead through an intermediate state.
- `-PauseAt` opens the pause menu; `-MenuTapAt "<sec>:<Channel>"` taps menu channels, and
  there is no `Back` channel (`Stop` is action 50, `GUI_CANCEL`, the B button); the tab
  toggles (actions 54/55) need `-ShoulderAt`, never a new `-MenuTapAt` channel;
  `-MenuScript` waits on log lines instead of the clock.
- Count rows from the screen's own source: disabled rows are skipped by `Next`, so walk to
  high rows with `Prev` when the menu wraps.

## Never

- Never "fix" a state the console's FSM cannot reach.
- Never claim a screen shows without a witness line and a frame.
- Never trust the DWARF over the console's vtable for whether an override exists.
- Never add a harness channel that changes how an existing named input event behaves.
- Never take an online screen's absence as a defect without the online service it needs.

## Tools

- `BRN_SCREEN_DIAG=1`, `BRN_SATNAV_DIAG=1` (diagnostic variables, through `DiagEnv`).
- `python tools/re/hasbody.py <Class::Method> [--status]`; `work show <tu>`; `work audit <tu>`.
- `python tools/re/vtable_override_audit.py --table <addr>` (read-only for one table; run
  without arguments it regenerates the report: leave that to its owner).
- `tools/re/ppcdis.py <hexaddr>`, `tools/re/x360rd.py <hexaddr> [nbytes]`.
- `tools/diagnostics/flow_run.ps1` through `tools/tests/run_case.ps1` (`bug-test`).

## Read next

- [references/coverage-map.md](references/coverage-map.md): FSM bundles, vtable checks,
  ICF traps, the status table for online screens.
- [references/triage.md](references/triage.md): how each "does not show" cause is found in
  one run.
- Skills: `bug-test`, `diagnose-parity-bug`, `console-evidence`, `build-and-link`,
  `reconstruct-tu`.
