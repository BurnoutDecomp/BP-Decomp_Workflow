# APT Menu 1:1 Handoff - Current Next Step

This is the authoritative handoff for the active Burnout Paradise Apt/menu-flow
work as of 2026-07-07. It supersedes the older notes that said registration was
still blocked by `RegisterComponent` arguments or by `PERSISTENTAPT` not loading.

## Goal

Drive the title/menu path through the real console GUI/Apt flow, then retire the
host-only `BrnAptRuntimeBringUp` fallback once the real path owns the menu.

The target is behavioral parity with the Xbox One 64-bit Apt reference plus the
normal repo gates:

- compile gate for touched TUs
- no new faithfulness-lint debt
- boot/menu behavior proven by the real window, screenshots, key input, and log
- no quiet stubs, raw offset accommodations, or fake Apt free-function shims

Do not delete `BrnAptRuntimeBringUp` yet. It is still the runnable bridge and it
contains useful diagnostic hooks.

## Verified Runtime Result

The current build was driven with scripted window automation, not just a timed
launch. The script:

- launched `build/game/Burnout_PC.exe`
- captured the Burnout window by process `MainWindowHandle`
- saved screenshots under `scratchpad_screens/`
- sent `Enter`, `Down`, and `Enter` with `keybd_event`
- stopped the process cleanly after the run

Fresh evidence from `build/game/BrnGame.log`:

```text
[AptRT] framework: 'MAIN' up (loaded=1 instantiated=1 level=0).
[AptRT] persist: 'PERSISTENTAPT' up (loaded=1 instantiated=1 level=2).
[AptRT] flow: LoadAnimation('Title_Screen02', ...)
[AptRT] findChild hash    name='BuildName' -> ... (35/1)
[AptRT] findChild special name='_parent'   -> ... (12/1)
[AptRT] findChild hash    name='IsBurnoutComponent' -> ... (34/1)
[AptRT] findChild hash    name='msName' -> ... (1/1)
[AptRT] findChild hash    name='RegisterComponent' -> ... (35/1)
[AptRT] SendAptEvent#N np=4: ev(id=1) ...
[AptRT] kv: 'MenuItem_0' apt_labeltxt='$TITLESCREEN_MENU_NORMAL'
[AptRT] kv: 'MenuItem_1' apt_labeltxt='$TITLESCREEN_MENU_BEATTHETEAM'
[BootLegal] stage 7 -> 8
[GuiModule] key vk=0x28 -> event 6/41 (AddEvent=1)
[GuiModule] key vk=0x0D -> event 6/45 (AddEvent=1)
[AptRT] viewstate: 'BackgroundAnimatorComponent' -> 'BeatTheTeam' ... (APPLIED)
[BootLegal] stage 8 -> 9
```

Screenshots from the same scripted run:

- `scratchpad_screens/burnout_20_title_initial.png` - EA splash
- `scratchpad_screens/burnout_22_stage8_menu.png` - title screen at menu stage
- `scratchpad_screens/burnout_23_after_stage8_enter.png` - transition strip after accept attempt
- `scratchpad_screens/burnout_24_after_down_enter.png` - after `Down`, `Enter`, stage 9 reached

## Current Diagnosis

The previous registration diagnosis is superseded. In the current runtime:

- `MAIN` loads and instantiates.
- `PERSISTENTAPT` loads and instantiates.
- `BuildName`, `_parent`, `IsBurnoutComponent`, `msName`, `gAptCommunicator`, and
  `RegisterComponent` resolve.
- `SendAptEvent` fires repeatedly.
- The title selection menu receives component key/value and view-state updates.
- Scripted input can move selection to Beat The Team and accept it.
- `BootLegal` advances from menu-active stage 8 to accepted stage 9.

The current hard stop is later:

```text
[GuiModule] BF_LEGAL command 70 (accepted) -> OnLeave + park
           (frontend flow un-reconstructed; FLAG follow-on).
[AptRT] StopMovie: BF_LEGAL left -- FLOW slot tick+render parked ...
```

That log comes from `b5-decomp/src/GameSource/Gui/BrnGuiModule.cpp`. On command 70,
the current PC bridge calls `BootLegal::OnLeave()`, stops the flow Apt movie, stops
menu music, sets `miBootPhase = 3`, and then phase 3 immediately returns forever.

So the next real implementation target is not another speculative AS VM patch. It
is reconstructing the post-`BF_LEGAL` GuiFsmController transition instead of
parking.

## 2026-07-07 Codex Pass: Concrete Remaining Menu Work

This pass cleaned the local temporary Apt diagnostics from the `b5-decomp`
worktree, then checked the real FSM bundles and the controller/state dossiers.
The important result is that there is not enough faithful code in the current
source tree to just "load the next menu" after command 70.

Observed facts from the repo:

- `FSM/BRNFLOADFSM.BUNDLE`, `BRNVIDEOFSM.BUNDLE`, `BRNLEGALFSM.BUNDLE`,
  `BRNBFPROFSM.BUNDLE`, `BRNCMPLDFSM.BUNDLE`, and `BRNBFPREFSM.BUNDLE` are
  single-state LuaCode bundles. They identify their own initial state but do not
  encode the boot-order edge out of `BF_LEGAL`.
- `GuiFsmController.cpp` is still not wired into the live PC boot bridge, but
  the core controller path is now substantially reconstructed: `Construct`,
  `Prepare`, `AddFlow`, `RunFsm`, `RunQueuedFsm`, `Update`,
  `HandleHudStateLoadComplete`, and `IsTransitionPending` are in source. The
  remaining controller-side gaps are the private debug/helper surface
  (`TriggerLoadUnload` as a standalone helper if required by a non-inlined
  caller, plus `DebugPrintResources`) and, more importantly, integration into
  `BrnGuiModule` instead of the `miBootPhase` bridge.
- DecFIGS names the HUD-flow slot after `BF_ATTR` as
  `PostTitleScreenLoad* mpStatePostTitleScreenLoad`. The current source instead
  has an inferred `BootCompoundLoad` shell for `BF_COMPLOAD`. Treat that as a
  known transition-stage mismatch, not as proved original code.
- `PostTitleScreenLoad.cpp` now implements the real dossier bodies for
  `OnEnter`, `OnLeave`, and `HandleIncomingEvents` in addition to the
  `GetResourcesToLoad` assert tripwire. Its `Update` body is still not safely
  reconstructed from an ARTIST packet, so it should not be wired as the live
  post-title state until that pass is complete.
- `BootProfile.cpp/.h` has a real dossier for the profile prompt flow
  (`Construct`, `OnEnter`, `Update`, `OnLeave`, controller input, profile task
  result, and the `ProfileMessageComponent` helper), but the checked-in source is
  only a small resource-accessor slice. Jumping directly into `BF_PROFILE` from
  the current runtime will hit incomplete source.
- `BrnHudFlow::Prepare` currently constructs `BF_PROFILE` through the two-arg
  `State::Construct`; the X360 body calls BootProfile's wider
  `Construct(id, fsm, ProfileManager*)` vtable slot. That is required before the
  real profile screen can be 1:1.

Concrete remaining list to make the menu flow 1:1 and retire
`BrnAptRuntimeBringUp`:

1. Wire the reconstructed `GuiFsmController` into the live GUI module path:
   module construction must `Prepare` it, `AddFlow` the screen/HUD/overlay
   flows, feed it ModelIO input/output buffers every tick, and route `RunFsm`
   events through it. This is the real controller that should replace
   `miBootPhase` hand sequencing.
2. Replace the inferred `BootCompoundLoad` HUD slot with the DecFIGS/X360
   `PostTitleScreenLoad` slot where appropriate, preserving the `BF_COMPLOAD`
   state id only if the X360 `BrnHudFlow::Prepare` call proves that id belongs to
   `PostTitleScreenLoad`.
3. Finish `PostTitleScreenLoad`: `OnEnter`, `OnLeave`, and
   `HandleIncomingEvents` are now bodied and compile, but `Update` still needs a
   source-truth pass before the state can drive the live post-title transition.
4. Body `BootProfile` for real, including the
   `ProfileTaskResultHandler` base, `ProfileMessageComponent`, the 3-arg
   `Construct(id, fsm, ProfileManager*)`, `OnEnter`, `Update`, `OnLeave`,
   controller input, and profile task-result handling. Until this exists,
   `BF_PROFILE` cannot be a faithful next screen.
5. Wire the post-legal event through the real controller path:
   `BootLegal` command 70 -> controller queues/runs the next FSM -> current FSM
   unload/load notifications -> `BrnBaseFlow::PrepareLua` for the next state.
   Do not keep using the `miBootPhase = 3` park.
6. Move Apt movie ownership out of `BrnAptRuntimeBringUp` into the normal GUI
   StateInterface/View/Resource flow: `PlayAptMovie`, `StopAptMovie`, persistent
   Apt, language/font resources, and component expected-list checks must be
   handled by the original model/view/cache path.
7. Continue the Apt engine cleanup required for 64-bit Xbox i64 parity:
   remove `Apt*_<verb>` free-function shims, raw offset reads, signature scans,
   format accommodations, and engine stubs by replacing them with real x64 Apt
   classes/methods and libapt2-correct `1:7:8` data.
8. Verify each frontier with the real window, not just compile: scripted launch,
   screenshot before/after `Enter`, send menu/navigation keys, capture
   `BrnGame.log`, and prove the next state renders visible buttons/prompt text.

The current "blank after Enter" is therefore expected for this transition state:
the source accepts `BF_LEGAL`, stops/parks the title movie, and has no real next
controller/state path wired yet. A temporary visual hold would hide the symptom,
but it would not be closer to 1:1 than reconstructing the controller and
post-title/profile states above.

## What Not To Chase Next

- Do not keep treating `PERSISTENTAPT is never loaded` as current. It is loaded now.
- Do not treat `MAIN frame0.cmdCount=90 (want 13)` as a root cause. That old
  expectation was from a stale probe for a different movie.
- Do not assume the DF2 arg-table/register mismatch remains the active blocker.
  The current run proves the menu path reaches selection and stage 9.
- Do not delete the Apt bridge/shim yet. The real post-legal flow is still missing.
- Do not patch core AS interpreter behavior from a hunch.

## Next Step

Implement the real transition after `BF_LEGAL` command 70 by wiring the
controller and finishing the post-title/profile state bodies, not by adding
another `BrnAptRuntimeBringUp` phase.

1. Integrate `GuiFsmController` into `BrnGuiModule` enough that `RunFsm` and
   `Update` own the same load/unload/PrepareLua sequence the X360 uses.

2. Fix the HUD boot-state ownership mismatch:
   `PostTitleScreenLoad` is the DecFIGS-named slot after `BF_ATTR`; the current
   `BootCompoundLoad` shell is only an inferred placeholder.

3. Finish `PostTitleScreenLoad::Update` and body `BootProfile` sufficiently for
   the next controller transition to reach live state code instead of
   blank/stub behavior.

## 2026-07-07 Follow-up: PostTitleScreenLoad Event Bodies

`b5-decomp/src/GameSource/Gui/Flow/HUD/States/BrnPostTitleScreenLoad.cpp` now
bodies the three reviewed ARTIST functions in the TU:

- `OnEnter`: clears `mpGuiCache`, registers events `{6, 64, 510}`, and enters
  `E_IDLE`.
- `OnLeave`: unregisters the same event set.
- `HandleIncomingEvents`: consumes the state input queue, latches the
  `GuiCache*` from event `64`, sets `mbVideoFinished` on event `510`, and emits
  `GuiEventStopVideo` for event `6` while in `E_PLAYING_VIDEO`.

Validation run:

```text
work faithfulness --files BrnPostTitleScreenLoad.cpp/.h -> PASS, no new invention smells
direct verify.compile_gate([...BrnPostTitleScreenLoad.cpp]) -> pass
work parity GameSource/Gui/Flow/HUD/States/BrnPostTitleScreenLoad.cpp -> RED advisory
```

The parity red is not ignored, but it is not the current blocker: the count-based
checker sees the original assert string-building helpers and a decompiler-typed
stack temporary that the source now represents as `CGS_ASSERT` and
`GuiEventStopVideo`. Before wiring this state live, run a proper postmortem on
`PostTitleScreenLoad::Update` and re-check event `6` against assembly.

## 2026-07-07 Follow-up: GuiFsmController Queue Slice

`b5-decomp/src/GameSource/Gui/BrnGuiFsmController.cpp` now bodies the reviewed
controller queue slice:

- `Construct`: resets the three flow slots to unloaded, clears pending/waiting
  flags, clears load/unload notifications, and seeds queued/current FSM records
  with blank ids, `E_GUI_HUD_NUMSFSMS`, and `E_GUIFLOW_COUNT`.
- `RunFsm`: validates `meFlowToUse`, sets transition-pending and
  mode-manager-waiting flags, copies the requested FSM, runs it immediately if
  the flow is unloaded, or moves a running flow to `FSMSHUTDOWN`.
- `RunQueuedFsm`: moves the queued FSM into the active load fields, converts the
  FSM id to the 13-byte load name, strips at the first space like ARTIST, clears
  the transition-pending flag, snapshots the current FSM, and resets the queued
  request to blank/default.

Supporting type work:

- `GuiEventRunFsm` is now homed in `BrnGuiEventTypeDefs.h` as the 24-byte flat
  controller payload proven by ARTIST (`mFsmId`, `mInitialStateId`,
  `meFsmToRun`, `meFlowToUse`). DecFIGS lists the fields in a misleading order;
  controller assembly reads `meFlowToUse` at payload `+0x14`, so the binary
  order wins.
- `GuiEventUnloadNotification` and `GuiEventUnloadRequestNotification` are now
  homed as flat 12-byte records in `CgsGuiResourceModuleIO.h`, matching the
  resource output buffer's queue sizes.

Validation run:

```text
work faithfulness --files BrnGuiFsmController.cpp/.h BrnGuiEventTypeDefs.h CgsGuiResourceModuleIO.h -> PASS
direct verify.compile_gate([BrnGuiFsmController.cpp, BrnHudFlow.cpp, BrnGuiCache.cpp, BrnPostTitleScreenLoad.cpp]) -> pass
work parity GameSource/Gui/BrnGuiFsmController.cpp -> RED advisory
```

The controller parity red was expected while `Update` and
`HandleHudStateLoadComplete` were still missing from the source. `Update`
remains the large missing controller body. A wider compile including
`BrnGuiModule.cpp` still fails on pre-existing EAThread/Win32 declaration
conflicts, not on this controller slice.

## 2026-07-07 Follow-up: HandleHudStateLoadComplete

`GuiFsmController::HandleHudStateLoadComplete` is now bodied from ARTIST:

- pending flow transitions force the corresponding flow load state to
  `E_FLOWLOADSTAGE_FSMSHUTDOWN`;
- mode-manager waiting flags are cleared when no transition is pending for that
  flow;
- the function returns true only when a waiting response was cleared and no
  transition is still pending.

Validation run:

```text
work faithfulness --files BrnGuiFsmController.cpp/.h -> PASS
direct verify.compile_gate([BrnGuiFsmController.cpp, BrnHudFlow.cpp, BrnGuiCache.cpp, BrnPostTitleScreenLoad.cpp]) -> pass
```

## 2026-07-07 Follow-up: GuiFsmController Update + x64 Queue Payloads

`GuiFsmController` now has the setup/update surface needed for real module
integration:

- `Prepare`: stages the controller by storing the `CgsGui::ModelModule*` and
  FSM heap allocator, then advances to `E_PREPARESTAGE_DONE`.
- `AddFlow`: installs the screen/HUD/overlay flow pointer into the indexed flow
  table and preserves the original duplicate-flow assert text.
- `Update`: consumes ModelIO load/unload notifications, maps request ids
  `{13,14,15}` to screen/HUD/overlay, queues the next FSM bundle request, calls
  `BrnBaseFlow::PrepareLua` when the LuaCode resource arrives, releases old FSMs,
  and drains queued transitions through `RunQueuedFsm`.

Supporting queue-type work:

- `GuiEventLoadRequest` moved out of the old opaque placeholder and is now the
  named resource request record (`request type`, `load/unload`, file-name
  pointer, request id, resource id) at the resource-module IO home.
- Pointer-bearing request/load-notification queue copies now use the widened
  PC/x64 payload sizes (`sizeof(GuiEventLoadRequest)` and
  `sizeof(GuiEventLoadNotification)`) instead of truncating the 64-bit file-name
  pointer or `ResourceHandle`.

Validation run:

```text
direct verify.compile_gate([
  BrnGuiFsmController.cpp,
  CgsModelModuleIO_InputBuffer.cpp,
  CgsModelModuleIO_OutputBuffer.cpp,
  CgsGuiResourceModuleIO_InputBuffer.cpp,
  CgsGuiResourceModuleIO_OutputBuffer.cpp,
  BrnHudFlow.cpp,
  BrnBaseFlow.cpp
]) -> pass
work faithfulness --files touched controller/GUI IO files -> PASS
work parity GameSource/Gui/BrnGuiFsmController.cpp -> RED advisory
```

The controller parity red is still count-based advisory noise: branch/loop
counts are now close, while call/return counts differ because assertions and
small helpers are represented differently. It does not replace the compile gate,
faithfulness gate, or the required later runtime proof.

After those pieces are ready, replace the phase-3 park in `BrnGuiModule.cpp`
only when the real next state can load, enter, tick, and render. Then rebuild the
runnable exe and verify by scripted window driving:

```powershell
& cmd.exe /c "tools\build\build_game_exe.bat"
# launch, screenshot the Burnout window, send Enter/Down/Enter, read BrnGame.log
```

Success for this frontier is:

```text
[BootLegal] stage 8 -> 9
[GuiModule] BF_LEGAL command 70 ...
<real next FSM/state entered; no miBootPhase=3 park>
```

After the post-legal flow is real, return to the remaining visual issues from the
same screenshots: stage 8 still mostly shows the title/transition strip rather than
a polished selectable menu. Treat that as a render/component-drive follow-up after
the flow no longer parks.

## Diagnostic State

The temporary dirty Apt diagnostics from the previous local pass were removed
from the `b5-decomp` worktree in this pass. Keep future runtime probes short-lived
unless a commit is explicitly a diagnostic checkpoint. Keep the scripted
screenshot/key-driving validation path.

Do not commit `progress/status.json`, parent repo submodule-pointer churn, or
`scratchpad_*` artifacts as part of the handoff.
