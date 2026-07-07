# APT Menu 1:1 Handoff - Current Next Step

This is the authoritative handoff for the real Burnout Paradise Apt/ActionScript
menu flow as of 2026-07-07. It deliberately supersedes the older running notes in
`ONE_TO_ONE_REMAINING.md` section 6, which contains useful history but also many
corrected hypotheses.

## Goal

Make the menu drive through the real console Apt component system, then retire the
host-only `BrnAptRuntimeBringUp` shim path. The target is behavioral parity with
the Xbox One 64-bit Apt reference plus the normal repo gates:

- compile gate for touched TUs
- no new faithfulness-lint debt
- boot behavior matches the reference path
- no quiet stubs, raw offset accommodations, or fake Apt free-function shims

Do not delete `BrnAptRuntimeBringUp` yet. It is still the working-menu fallback and
also contains the current diagnostic hooks.

## Current Workspace State

Parent repo:

- branch: `main`
- dirty: `b5-decomp`, `tools/volatility`, and local `scratchpad_*` files

Submodule `b5-decomp`:

- branch: `l2-drive-clean`
- HEAD: `cf1379c5`
- ahead of `origin/l2-drive-clean` by 4 commits
- dirty diagnostic files:
  - `src/GameSource/Gui/BrnAptRuntimeBringUp.cpp`
  - `src/SDKs/EATech/include/Apt/AptActionInterpreterInterpHelpers.cpp`
  - `src/SDKs/EATech/include/Apt/AptAnimationTarget.cpp`
  - `src/SDKs/EATech/include/Apt/AptDisplayList.cpp`

Important: committed `cf1379c5` has `KB_CLASS_BINDING=false`. The dirty diagnostic
tree currently flips it to `true` to exercise the real binding path. Before any
real commit, restore `KB_CLASS_BINDING=false` unless the commit is explicitly a
diagnostic-only checkpoint.

Do not commit `progress/status.json`, the parent repo submodule pointer, or
`scratchpad_*` files as part of this work.

## Proven Current Symptom

With class binding enabled, the framework now gets far enough that the onLoad path
reaches `AptCommunicator::sMethod_SendAptEvent`, but registration still fails:

```text
[AptRT] framework: 'MAIN' up ... level 0
[AptRT] persist: 'PERSISTENTAPT' up ... level 2
[AptRT] SendAptEvent#N np=4: ev(id=1) uid=1 | p2Vft=-1 p2='<undef>' | p3Vft=1 p3CIH=0 p3='_global'
AddNewAptComponent / REGISTERED: 0
```

That is the current blocker. Treat it as an observed failure, not proof that every
downstream piece is finished.

The likely failing chain is:

```text
onLoad()
  -> BuildName()
  -> RegisterComponent(name, this)
  -> gAptCommunicator.SendAptEvent(E_APT_EVENT_ONLOAD, uid, name, clip)
  -> AddNewAptComponent(clip, name)
```

The current bad call reaches `SendAptEvent` with `name=undefined` and
`clip='_global'` as a string value instead of a CIH clip. The next job is to find
where those two arguments are produced.

## What Not To Chase Next

These were useful historical leads, but they are not the next actionable path:

- "PERSISTENTAPT is never loaded" is superseded. The current code loads and
  instantiates `MAIN` plus `PERSISTENTAPT`.
- The `MAIN frame0.cmdCount=90 (want 13)` line is not a valid root cause. That
  expectation came from a stale probe for a different movie.
- Do not delete the shim or ungate the hard `SendAptEvent` asserts until
  registration is actually working.
- Do not patch core AS interpreter behavior from a hunch. A wrong VM change breaks
  the working shim menu, MAIN bootstrap, and all future Apt screens.

## Next Step: One Diagnostic Boot

The dirty tree has already started the needed diagnostic:

- `BrnAptRuntimeBringUp.cpp` has `AptOpTraceArmDrain`, `AptOpTraceIsArmed`, and
  `AptFnDumpProbe`.
- `AptActionInterpreterInterpHelpers.cpp` dumps script-function bytecode while the
  op trace is armed.
- `AptAnimationTarget.cpp` arms the trace around the deferred onLoad function drain.
- `AptDisplayList.cpp` currently has `KB_CLASS_BINDING=true`.

Do one controlled rebuild and boot, then read the log. Do not make a semantic fix
until this boot tells us whether the bad arguments come from bytecode decoding,
stack/CallMethod handling, or an untraced nested call.

Commands from repo root:

```powershell
git -C b5-decomp status --short --branch
& cmd.exe /c "tools\build\build_game_exe.bat"
if (Test-Path build/game/BrnGame.log) { Clear-Content build/game/BrnGame.log }
Get-Process Burnout_PC -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process build/game/Burnout_PC.exe -WorkingDirectory build/game
Start-Sleep -Seconds 40
Get-Process Burnout_PC -ErrorAction SilentlyContinue | Stop-Process -Force
Select-String build/game/BrnGame.log -Pattern "\[AptFn\]|\[AptOp\]|SendAptEvent|REGISTERED|optrace ARM|optrace DISARM|framework:|persist:" |
  Set-Content scratchpad_menu_apt_diag_log.txt
```

## How To Read The Diagnostic

First check whether the current dump captures only the 98-byte onLoad body or also
captures a nested script function around the `SendAptEvent` calls.

If the log only repeats the same 98-byte function body:

- The current dump window is not seeing the nested `RegisterComponent` execution.
- Do not infer the fix from the outer onLoad bytecode.
- Instrument `CallMethod` / `CallFunctionDispatch` next to log:
  - member name or dictionary key being called
  - receiver value type/vtable
  - resolved callee value type/vtable
  - script-function bytecode pointer and size if the callee is script-backed
  - parameter count and top stack values before dispatch

If a distinct nested function body is captured:

- Disassemble that body with operand sizes from the Apt parse table, not generic SWF
  assumptions.
- Confirm whether `_global` is a literal operand that should be consumed by
  `GetVariable`/`GetMember`, or whether a native-8 Push/constant-pool decode is
  producing the wrong value.
- Compare the relevant implementation against the dossiers before editing:

```powershell
python tools/work/work.py show class:AptActionInterpreter --full --asm -o scratchpad_AptActionInterpreter.md
python tools/work/work.py show class:AptActionInterpreterStackOps --full --asm -o scratchpad_AptActionInterpreterStackOps.md
python tools/work/work.py show class:AptScriptFunction2 --full --asm -o scratchpad_AptScriptFunction2.md
```

Only after that comparison should you touch VM behavior.

## Success Criteria For This Frontier

With `KB_CLASS_BINDING=true`, a successful fix must produce:

```text
SendAptEvent#N ... p2='<real component name>' ... p3CIH=1
[AptComm] component registered: '<name>' (count=N)
AddNewAptComponent / REGISTERED > 0
```

Then and only then:

1. Restore the hard `SendAptEvent` argument asserts.
2. Verify `AptCommunicator::UpdateAllComponents` has registered components to drive.
3. Remove the menu-state shim (`AptRuntimeSetComponentKeyValue`,
   `AptRuntimeSetComponentViewState`, and the `CgsGuiComponent.cpp` fallback) only
   after the real `UpdateAll` path visibly drives the menu.
4. Re-home the remaining integration pieces:
   - `AptLoader_StartAsyncLoad`
   - `GuiResourceModule::Prepare/Update`
   - `ViewModule::Construct/Prepare`
   - `GuiModule::Update` / `AptAux::Update`
   - `gpfnApt*TextRenderData` hooks
5. Delete `BrnAptRuntimeBringUp.cpp/.h` only after those callers are real.

## Commit Hygiene

Before committing real work:

- restore `KB_CLASS_BINDING=false` unless the commit is deliberately diagnostic
- remove or gate noisy `[AptFn]` / `[AptOp]` probes
- keep the working shim menu bootable until the real path is proven
- run at least the touched-TU compile gate
- run `python tools/work/faithfulness_lint.py --all` and make sure no new Apt debt
  appears

The handoff is intentionally narrow: make the registration call faithful first. The
rest of the 1:1 Apt debt remains real, but it should not be mixed into this frontier.
