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

## What Not To Chase Next

- Do not keep treating `PERSISTENTAPT is never loaded` as current. It is loaded now.
- Do not treat `MAIN frame0.cmdCount=90 (want 13)` as a root cause. That old
  expectation was from a stale probe for a different movie.
- Do not assume the DF2 arg-table/register mismatch remains the active blocker.
  The current run proves the menu path reaches selection and stage 9.
- Do not delete the Apt bridge/shim yet. The real post-legal flow is still missing.
- Do not patch core AS interpreter behavior from a hunch.

## Next Step

Implement the real transition after `BF_LEGAL` command 70.

1. Confirm the exact post-legal target from source-of-truth evidence before coding.
   Use the real FSM/assets and dossiers, not a guess. Likely evidence surfaces:
   `build/game/FSM/BRNLEGALFSM.BUNDLE`, `build/game/FSM/BRNHUD.BUNDLE`,
   `BrnGui::BrnHudFlow`, `BrnGuiModule::Update`, and the X360
   GuiFsmController/ModelIO path.

2. Determine whether command 70 should enter another HUD boot state such as
   `BF_PROFILE`, `BF_ATTR`, or `BF_COMPLOAD`, or whether it should switch into a
   separate frontend/screen flow. `BrnHudFlow` already constructs these boot states:
   `BF_PRELOAD`, `BF_VIDEOS`, `BF_LEGAL`, `BF_ATTR`, `BF_COMPLOAD`, `BF_PROFILE`,
   and `BF_LOADING`.

3. Replace the phase-3 park in `BrnGuiModule.cpp` with the faithful controller
   transition pattern. Reuse the existing BF_LOADING -> BF_VIDEOS -> BF_LEGAL
   sequencing style only if the source evidence confirms the next state and event.

4. Rebuild the runnable exe and verify by scripted window driving:

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

The current submodule checkout is diagnostic-heavy:

- `KB_CLASS_BINDING` is `true` in `AptDisplayList.cpp` at current `HEAD`
  (`88994eb9`), not merely an unstaged local change.
- Dirty diagnostic files currently include:
  - `src/GameSource/Gui/BrnAptRuntimeBringUp.cpp`
  - `src/SDKs/EATech/include/Apt/AptActionInterpreterInterpHelpers.cpp`
  - `src/SDKs/EATech/include/Apt/AptActionInterpreterVariable.cpp`
  - `src/SDKs/EATech/include/Apt/AptScriptFunction2.cpp`
  - `src/SDKs/EATech/include/Apt/AptValue/AptValueFindChild.cpp`

Before a clean production commit, gate or remove noisy `[AptRT] var`,
`[AptRT] findChild`, `[AptRT] bind`, and `[AptRT] f2` probes unless the commit is
explicitly a diagnostic checkpoint. Keep the scripted screenshot/key-driving
validation path.

Do not commit `progress/status.json`, parent repo submodule-pointer churn, or
`scratchpad_*` artifacts as part of the handoff.
