# HANDOFF — §6 Real Menu Drive / Delete `BrnAptRuntimeBringUp`

> Self-contained handoff for a fresh agent (no prior memory). Everything you need to
> resume is here. Written 2026-07-07. Repo root: `E:\Reverse_Engineering\Burnout\BP-Decomp_Workflow`.
> Read `AGENTS.md` + `STRATEGY.md` + `ONE_TO_ONE_REMAINING.md` §6 first for house rules.

---

## 0. THE GOAL

Make the Burnout Paradise **menu drive itself through the real console component system**,
byte/behaviour-exact vs the Xbox One 64-bit reference, and then **delete
`b5-decomp/src/GameSource/Gui/BrnAptRuntimeBringUp.cpp`** (a hand-written bring-up *shim*
that currently fakes the menu). No shims, everything exact. This is genuinely multi-session.

The X360 reference DBs live in `IDA Files/` (use `Burnout_External_Xbox_One.exe.i64` for x64
parity; the reconstruction is cross-checked vs `BURNOUT_X360_ARTIST.XEX.i64` and the PS3 ELF).
Use the curated dossier, **not** raw JSON exports: `python tools/work/work.py show <TU> --full [--asm]`
(TU ids are namespaced, e.g. `class:AptActionInterpreter`, `class:CgsGui::AptCommunicator`,
`class:AptScriptFunction2`).

---

## 1. TL;DR — THE ONE REMAINING BUG

Everything downstream is already real and homed. The **single functional blocker** is that
**no menu component registers** (`AddNewAptComponent` fires 0×). Registration flows:

```
onLoad()  →  BuildName()  →  RegisterComponent(name, this)
          →  gAptCommunicator.SendAptEvent(E_APT_EVENT_ONLOAD, uid, name, clip)
          →  AptCommunicator::AddNewAptComponent(clip, name)     ← never reached
```

A boot with `KB_CLASS_BINDING=true` + a probe proved: onLoad **dispatches 67×** and reaches
`sMethod_SendAptEvent` every time with `ev=ONLOAD, uid=defined`, **but `name=undefined` and
`clip='_global'` (a StringValue)** on all 67 → the `lbNameOk` guard rejects → 0 registrations.

An opcode trace armed at the exact onLoad execution point showed the wrong values are pushed
by the **compiled AS bytecode of a nested function (RegisterComponent), invoked by onLoad**.
The bug is at the **bytecode/interpreter level in that nested call** — NOT in the C++
communicator, NOT in onLoad dispatch, NOT in PERSISTENTAPT loading.

**NEXT STEP (do this first):** dump + disassemble the *nested* RegisterComponent function's
bytecode (§7), find why it pushes `'_global'`/undefined instead of the real name + clip, and
fix the one faithful defect. Then: un-gate the SendAptEvent asserts, delete the shim, delete
`BrnAptRuntimeBringUp`, validate vs the i64.

---

## 2. CURRENT COMMITTED STATE (b5-decomp HEAD = `cf1379c5`)

The submodule `b5-decomp` is at `cf1379c5`. Working tree is clean. The committed code:

- **Loads BOTH `MAIN` (level 0) and `PERSISTENTAPT` (level 2)** resident (commit `23bbf0a7`).
  `BrnAptRuntimeBringUp.cpp` `EnsureFrameworkMovie()` (~line 1407) loads MAIN into
  `s_FrameworkSlot` and PERSISTENTAPT into a new `s_PersistentSlot`.
  - Pool sizing: `KU_FRAMEWORK_POOL_BYTES = 12 MiB`, `muMaxResources = 128`,
    `KU_MAX_IMPORT_BUNDLES = 16` (PERSISTENTAPT is 11.5 MB / 101 resources / 13 imports).
- **`KB_CLASS_BINDING = false`** (`AptDisplayList.cpp:1274`) — the class-binding path is OFF so
  the **working shim menu is preserved**. Flip to `true` to exercise the real component binding
  (needed for all the diagnostics below; it currently renders the menu wrong until the bug is fixed).
- A **SendAptEvent registration probe** is committed in
  `CgsAptCommunicator.cpp` `sMethod_SendAptEvent` (~line 831, behind a 150-hit cap) — it logs
  each registration attempt's params; use it to verify the fix (`fixed ⇒ name defined, clip=CIH,
  AddNewAptComponent>0`).
- An **ancestor-chain probe** is committed in `AptCIH::AssociateInstToClass`
  (`AptDisplayList.cpp`, before the `pNode->tick()`), inert while binding is off.

Session commit trail (newest first): `cf1379c5`, `7da8cc6f`, `23bbf0a7`, `6682ba04`, `f88ac1df`.
(`6682ba04` loaded PERSISTENTAPT *instead of* MAIN and was superseded by `23bbf0a7` which loads both.)

**Rule:** only commit/push the `b5-decomp` submodule source + parent-repo `.md` docs. Do NOT
commit `progress/status.json`, the submodule pointer, or `scratchpad_*.json` (CI reconciles).

---

## 3. ARCHITECTURE — WHAT'S REAL vs SHIM (verified via 4 dossier agents)

**Already REAL/homed — do NOT rebuild:** the whole Apt engine + component drive.
- `AptAux::InitializeApt` / `UpdateComponents` (`CgsAptAux.cpp`).
- `AptCommunicator::Initialize` / `sMethod_SendAptEvent` (`CgsAptCommunicator.cpp:809`,
  X360 `0x8285C360`) / `AddNewAptComponent` (`:278`, X360 `0x82849B88`) / `UpdateComponent`
  (`:474`) / `UpdateAllComponents` (`:423`, X360 `0x828499D0`) + the `AptCallFunctionOpti("UpdateAll")`
  bridge (`:64-125`).
- `AptDataHandler::AddAptData`/`FindAptData`; `AptCallbackFile::LoadAnimation`→CompleteLoad/
  Resolve/Fixup; `AptGetAnimationAtLevel`; the import machinery (`AptLoader::Update`/
  `AllImportsAvailable`/`Link`/`FindExport`); the render-callback family + `AptRender`.
- The AS interpreter: `runStream`, `callFunction`→`CallFunctionDispatch`→`ExecuteScriptFunction`,
  `getVariable`, `findChild`+`AptApt_ResolveSpecialName`, `AptScriptFunction2` preload, etc.

**SKELETONS (ctors + a few accessors only) — the shim fakes their orchestration:**
`CgsGui::GuiModule` / `ViewModule` / `GuiResourceModule`. Reconstructing these is Phase C
(delete-the-shim), NOT the current blocker.

**Only true link dep of the shim:** `AptLoader_StartAsyncLoad` (`BrnAptRuntimeBringUp.cpp:3033`) —
a PC-platform leaf (`AptLoader::Update` at `AptLoader.cpp:516` calls it). Re-home it, don't drop it.

**PERSISTENTAPT.bundle** (`build/game/GUIAPT/PERSISTENTAPT.bundle`) = the component library:
11.5 MB, **101 resources** (~61 embedded `type=0x1E` AptData movies + ~40 textures). Defines the
AS `BurnoutComponent` base + `IsBurnoutComponent`/`BuildName`/`RegisterComponent` + the menu
component classes. **MAIN.bundle** (236 KB, 0 imports) = the AS core: its frame-0 DoAction runs
`new AptCommunicator` + the 24-class `registerClass` bootstrap. They are **independent — the
console keeps BOTH resident** (this is why the code loads both).

---

## 4. THE FULL DIAGNOSTIC CHAIN (what's proven, 9 rule-outs)

Boot with `KB_CLASS_BINDING=true` + probes established, in order:
1. **onLoad DOES dispatch** — 67× (an earlier "onLoad doesn't fire" was a capture artifact of
   arming around the binding tick, which only *queues* onLoad; it drains later).
2. **The C++ SendAptEvent→AddNewAptComponent chain is fine** — event id, uid, clip all reach it.
3. **`BuildName` returns an undefined name** — the guard at `CgsAptCommunicator.cpp:837`
   (`lbNameOk` false) no-ops instead of registering. THIS is the blocker.
4. The clip param (param3) is a **StringValue `'_global'`** (vft 1), not a CIH (vft 12). Both the
   undefined name AND the `'_global'` clip come from **onLoad's compiled bytecode passing wrong args**.

Refuted candidates (each checked, reverted, no effect — do NOT re-try blindly):
- **findChild special-name path** — probe in `AptApt_ResolveSpecialName` case-16 (`_parent`)
  fired 0×; special names never reach findChild via this path.
- **`AptCIH::objectMemberLookup` `_parent`/`_root` getters** — no effect.
- **DF2 preload ORDER** (this→super→arguments→root→parent→global) — dossier-confirmed the
  reconstruction already matches the X360 (`class:AptScriptFunction2` asm ~`0x82B025E0`).
- **Preload flag BIT VALUES** (`KU_PRELOAD_*` in `AptScriptFunction2.h:104`) — dossier-confirmed
  (args=0x10, root=0x40, parent=0x80, global=0x100 match the console masks).
- **`muPreloadFlags` OFFSET** (`AptScriptFunction2.h:91`, `+0x0E`) — correct native-8 offset
  (console `+0x0A` + 4 for the name qword growing 4→8 bytes; see the struct comment `:81-98`).
- **Receiver-push ORDER** (`ExecuteScriptFunction`, `AptActionInterpreterInterpHelpers.cpp:861-868`)
  — pushes `pScope` onto the CIH stack BEFORE the preload, so `this`=CurrentTargetCIH() is correct.
- **Run-scope `this`** (`runStream`, `AptActionRun.cpp:90`) — a probe showed it resolves to a
  valid CIH on the onLoad runs (fired non-CIH only once, on an unrelated Object-scope run).
- **Constant-pool LOOKUP** — `stackPushIndirect` (`AptActionInterpreter.cpp:146-171`) resolves
  Lookup(tag8)→`mpConstantPool[idx]`, but the `'_global'` push probe showed `raw=1` = already a
  StringValue literal, NOT a Lookup. So `'_global'` is a literal operand, not a pool-index read.

⇒ Every structural hypothesis at the onLoad level is refuted. The defect is in the **nested
function's bytecode** (RegisterComponent), see §5-6.

---

## 5. onLoad BYTECODE — DECODED (the key new finding)

Dumped the drained onLoad handler (via a probe at `AptAnimationTarget::RunActions` `callFunction`,
line ~1501 — the deferred FUNCTION-slot drain). It is **98 bytes, pool count 17**:

```
0x59  Push[str]  0xA2 0x06  0x52  Push[str]  0xB5 0x02  Push[str]  0x88 [ptr]
0xAF 0x07  0xB2 0x08  0x59  Push[str]  0xB2 0x09
```

= **4 string pushes + 2 CallMethods (op 0xB2)**. The native-8 `Push` (op 0x96) operand is 3
qwords: `{flags=0, type=1(StringValue), absolute-ptr-to-string}`; the string pointers ARE
relocated correctly (resolve to real strings). **This onLoad has NO register pushes and NO
`'_global'`** — so the `'_global'`/`SendAptEvent(0xB2)` I traced earlier is inside a **nested
call (RegisterComponent)**, invoked by one of onLoad's two `0xB2` CallMethods. I dumped the
wrong level. **You must dump the nested RegisterComponent function.**

Note: the dumped `pool[0..16]` all printed as the same garbage (`'8..;..'`) — this is most
likely a probe artifact (`mppEntries` hold relocated *pointers* printed as `%s`), because the
Push uses direct string pointers not pool indices. BUT verify the constant pool of the *nested*
RegisterComponent is valid: if IT reads a value via pool index (`op 0x96 type 8/9` → Lookup) and
the pool is genuinely corrupt/unpatched, that is a strong `'_global'` candidate. The pool is
patched at DefineFunction2 time from the interpreter's two constant-pool registers
(`AptScriptFunction2.h` fields `mppConstantPool@+0x20`/`mnConstantPoolCount@+0x28`, sig slots
`0x98765432`/`0x12345678` before patching).

Known assumed AS (from an earlier partial trace — TREAT AS UNVERIFIED, it may be wrong):
```
onLoad()          = { this.BuildName(); gAptCommunicator.RegisterComponent(name, this); this.Initialize(); }
BuildName()       = { this.msName = this._name;
                      reg = this._parent; while (reg && !reg.IsBurnoutComponent()) reg = reg._parent;
                      return reg.msName; }
RegisterComponent = { CAptCommunicator.SendAptEvent(KI_EVENT_ONLOAD, uid, name, clip); }
```
The real bytecode may differ — the whole point of §7 is to read the ACTUAL RegisterComponent
bytecode rather than trust this model.

---

## 6. THE TWO LIVE HYPOTHESES FOR THE `'_global'` DEFECT

After dumping RegisterComponent (§7), you're testing between:
- **(a) The AS genuinely references `_global`** (e.g. `_global.gAptCommunicator.SendAptEvent(...)`),
  and a `GetVariable` (op that resolves the pushed `'_global'` string → the `_global` object) is
  either missing from the trace or not consuming the string, so `'_global'` stays on the operand
  stack and becomes an arg. → the fix is in the GetVariable/GetMember/CallMethod stack handling.
- **(b) The ActionPush operand DECODING / `_parseStream` native-8 widening** for that stream is
  subtly wrong, so a Push reads a literal `'_global'` where the real operand is a Register/Lookup.
  → the fix is in the operand decode (or the bundle's native-8 conversion of that DF2).

To distinguish you MUST see RegisterComponent's real opcode+operand stream. Both fixes are
verified the same way: re-boot with `KB_CLASS_BINDING=true` + the SendAptEvent probe and confirm
`name` is a real string, `clip` is a CIH (`clipCIH=1`), and `AddNewAptComponent > 0`.

---

## 7. IMMEDIATE NEXT STEPS (concrete, in order)

### Step A — dump the NESTED RegisterComponent bytecode
Move the bytecode-dump probe from the drain to **every script-function call**, so nested calls
are captured. Add this probe to `BrnAptRuntimeBringUp.cpp` (near the other `[AptOp]` probes ~L226):

```cpp
extern "C" void AptFnDumpProbe(const void* pBase, int nSize,
                               const char* const* ppPool, int nPoolCount)
{
    static int s_iFnDump = 0;
    if (s_iFnDump >= 12 || pBase == nullptr || nSize <= 0 || nSize > 8192) return;
    ++s_iFnDump;
    char lac[128];
    std::snprintf(lac, sizeof(lac), "[AptFn] #%d size=%d poolN=%d\n", s_iFnDump, nSize, nPoolCount);
    CgsDev::Log::WriteToLog(lac);
    const unsigned char* const p = static_cast<const unsigned char*>(pBase);
    char line[220];
    for (int i = 0; i < nSize; i += 40) {
        int n = std::snprintf(line, sizeof(line), "[AptFn]  ");
        for (int j = 0; j < 40 && (i+j) < nSize; ++j) n += std::snprintf(line+n, sizeof(line)-n, "%02X", p[i+j]);
        std::snprintf(line+n, sizeof(line)-n, "\n"); CgsDev::Log::WriteToLog(line);
    }
    // (optional) dump pool strings if you trust them; they printed as pointers last time.
}
```

Call it in `AptActionInterpreter::ExecuteScriptFunction`
(`AptActionInterpreterInterpHelpers.cpp` ~L909, right before `runStream`), gated so it only
fires while `KB_CLASS_BINDING` binding is active (or cap it and correlate with the SendAptEvent
probe). `extern "C" void AptFnDumpProbe(...)` declare it in that TU. Use the accessors:
`pFunc->GetByteCodeBase()`, `pFunc->GetByteCodeSize()`, `pFunc->GetConstantPool()` (returns
`AptConstantPool{ const char** mppEntries; int32_t mnCount; }`, `AptScriptFunctionBase.h:77`).

Also (best signal) **re-arm the opcode trace over the same window** so you get per-push resolved
values. The op-trace infra is in `BrnAptRuntimeBringUp.cpp`: `AptOpTraceProbe` (~L226, logs each
opcode when `s_iOpTraceArmed`), `AptPushIndirectProbe` (~L246, logs each Push's resolved
type/text), `AptOpTraceArmForClass` (~L203, filters `"TransitionComponent"`). Add a generic arm:

```cpp
extern "C" void AptOpTraceArmDrain(int nOn) {   // in BrnAptRuntimeBringUp.cpp
    static int s_iD = 0;
    if (nOn) { if (s_iD >= 6) return; s_iOpTraceArmed = 1; s_pOpTraceBase = 0;
               CgsDev::Log::WriteToLog("[AptRT] optrace ARM (drain)\n"); }
    else if (s_iOpTraceArmed) { s_iOpTraceArmed = 0; ++s_iD; CgsDev::Log::WriteToLog("[AptRT] optrace DISARM\n"); }
}
```
Also set `s_iOpEarlyBudget = 0` and bump the `s_iOpHits >= 1400` cap (~L232) to `6000`, and wrap
the nested `callFunction`/`runStream` for RegisterComponent with `AptOpTraceArmDrain(1/0)`.

### Step B — build the operand-aware EATech-AS2 disassembler (the real missing tool)
The opcode operand shapes are the console's `_parseStream` 0x42-entry jump table
(`word_82145280`; see `AptActionInterpreter::_parseStream`/`ResolveTranscode` — the table is
binary data flagged deferred in the reconstruction). Recover that table (from the XEX rodata via
the DecFIGS technique, or from the reconstruction's parse dispatch) to know each opcode's operand
size. Standard SWF opcodes present: `0x96` Push, `0x1C` GetVariable, `0x4E` GetMember,
`0x52`/`0xB2` CallMethod, `0x88` ConstantPool, `0x87` StoreRegister, `0x8E` DefineFunction2,
`0x99` Jump, `0x9D` If. EATech ADDS extended opcodes `0xA2/0xAF/0xB5/0xB2/0xAE/0x69/...` whose
operand sizes you need from the table. `disasm_apt.py` (see §9) is a partial start but does NOT
resolve `dict[N]` (op 0x88) or find DF2 records in PERSISTENTAPT (multi-resource pkg).

### Step C — fix + verify
Apply the ONE faithful fix (hypothesis a or b), rebuild, boot with `KB_CLASS_BINDING=true`, and
check the SendAptEvent probe shows a real name + CIH clip + `AddNewAptComponent > 0`.

### Steps D-F (after registration works — see `ONE_TO_ONE_REMAINING.md` §6.5-6.7)
- D: restore the CGS_ASSERTs at `CgsAptCommunicator.cpp:830-838` / `:950-956` (un-gate SendAptEvent),
  confirm `UpdateAllComponents` (item 5, already wired) drives the real menu.
- E: **delete the menu shim** — `AptRuntimeSetComponentKeyValue`/`AptRuntimeSetComponentViewState`/
  the `AptRuntime*` clip-effect cluster (`BrnAptRuntimeBringUp.cpp:2565-end`) + its call site
  `CgsGuiComponent.cpp:54` (`GuiComponent::AddOutputAptViewState`) + `BrnBootLegalBoundary.cpp:85`.
- F: reconstruct `GuiResourceModule::Prepare/Update` + `ViewModule::Construct/Prepare` +
  `GuiModule::Update`/`AptAux::Update`; re-home `AptLoader_StartAsyncLoad` + the
  `gpfnApt*TextRenderData` hooks; then **delete `BrnAptRuntimeBringUp.cpp` + `.h`** and re-point
  its callers (`BrnGuiModule.cpp:194/195/361/682/645`, `BrnRendererModule.cpp:118`,
  `BrnBootLegalBoundary.cpp:85`). Free to delete: `AptRuntimeIsReady` (no caller) + all 25
  `[AptRT]` probe sinks (weak `*Default` no-ops absorb them).
- G: validate byte/behaviour-exact vs `IDA Files/Burnout_External_Xbox_One.exe.i64`.

---

## 8. BUILD / BOOT / TEST LOOP

- **Build** (~4 min): `& cmd.exe /c "tools\build\build_game_exe.bat"` (from repo root, PowerShell).
  Emits `build/game/Burnout_PC.exe`. Run in background; exit code 0 = success.
- **Boot:** `Start-Process build/game/Burnout_PC.exe -WorkingDirectory build/game`. Kill any prior
  instance first (`Get-Process Burnout_PC | Stop-Process -Force`) — it locks the exe/log. Let it
  run ~35 s to reach the title (onLoad drains a few frames after binding).
- **Log:** `build/game/BrnGame.log`. Clear it BEFORE each boot with `Clear-Content` (NOT
  `Remove-Item` — the process holds a handle). Grep for `[AptRT]`, `[AptOp]`, `[AptFn]`,
  `SendAptEvent#`, `registerClass`, `class-bind`.
- **Toggle binding:** `KB_CLASS_BINDING` at `AptDisplayList.cpp:1274`. `false` = working shim menu
  (leave it here when you commit). `true` = exercise real binding (needed for all diagnostics;
  currently renders wrong until fixed — do NOT commit `true`).
- **compile-gate a few TUs without a full build:**
  `python -c "import sys;sys.path.insert(0,'tools/work');import verify;print(verify.compile_gate(['<file1>','<file2>'])[0])"`
- **Faithfulness lint:** `python tools/work/faithfulness_lint.py --all` (ratchets vs
  `progress/faithfulness_baseline.json`; don't blind-regen it).

---

## 9. KEY FILES / TOOLS / ADDRESSES

Interpreter / bytecode:
- `b5-decomp/src/SDKs/EATech/include/Apt/AptActionRun.cpp` — `runStream` (dispatch loop; opcode
  trace probe at L132; run-scope `this` at L90).
- `.../AptActionInterpreterInterpHelpers.cpp` — `CallFunctionDispatch` (L735), `ExecuteScriptFunction`
  (L815; installs constant pool L829, runs body L909), `getVariable` callers.
- `.../AptActionInterpreterVariable.cpp` — `getVariable` (X360 `0x82B03430`).
- `.../AptActionInterpreter.cpp` — `stackPushIndirect` (L146; Push resolve + `AptPushIndirectProbe`
  at L164), `_FunctionAptActionGetVariable` (X360 `0x82B038A0`).
- `.../AptValue/AptValueFindChild.cpp` — `AptValue::findChild` (X360 `0x82B01298`) +
  `AptApt_ResolveSpecialName` (case 16 `_parent`, case 19 `_global`, case 2 `this`);
  `ObjectIndex::in_word_set` is in `.../Apt/AptObjectIndex.{h,cpp}` (wordlist IS filled).
- `.../AptScriptFunction2.{h,cpp}` — the DF2 preload (`SetupBeforeExecution`, cpp L190-250),
  `KU_PRELOAD_*` flags (h L104), `AptScriptFunction2ByteCode` struct (h L86).
- `.../AptScriptFunctionByteCodeBlock.{h,cpp}` — tag-36 fn (`GetConstantPool` @X360 `0x82AF1620`).

Drive / dispatch:
- `.../AptCIHBehaviour.cpp` — `AptCIH_queueClipEvents_RunMatched` (L1439; queues onLoad as a
  FUNCTION slot at L1610 `AddFunctionBack`).
- `.../AptAnimationTarget.cpp` — `RunActions` (L1336; the FUNCTION-slot drain `callFunction` at
  L1501 — arm/dump here for onLoad).
- `.../AptDisplayList.cpp` — `AptCIH::AssociateInstToClass` (L1276; `KB_CLASS_BINDING` L1274;
  the binding tail sets `__proto__`, runs the ctor, `FindAndSetEvents`, `tick()` which fires onLoad).

C++ communicator (all REAL):
- `b5-decomp/src/GameShared/GameClasses/Gui/View/AptInterface/CgsAptCommunicator.cpp` —
  `sMethod_SendAptEvent` (L809, guard L837, the SendAptEvent probe), `AddNewAptComponent` (L278),
  `UpdateAllComponents` (L423).
- `.../CgsAptAux.cpp` — `AptAux::UpdateComponents` (L241), `InitializeApt` (L181), `ConstructApt`.

Shim / integration:
- `b5-decomp/src/GameSource/Gui/BrnAptRuntimeBringUp.cpp` — `EnsureFrameworkMovie` (L1407, loads
  MAIN+PERSISTENTAPT), `AptLoadMovieSlot` (L1268), `DriveFaithfulLoad` (L1632, `AddAptData` L1720),
  op-trace probes (L200-256), the menu-drive shim cluster (L2565-end),
  `AptLoader_StartAsyncLoad` (L3033).
- `BrnGuiModule.cpp` / `BrnRendererModule.cpp` / `BrnBootLegalBoundary.cpp` — the shim's callers.

Bundles (native-8 GUIAPT set; `build/game/GUIAPT/`): `PERSISTENTAPT.bundle`, `MAIN.bundle`,
`TITLE_SCREEN02.bundle`, the `B5*.bundle` component set. Do NOT re-widen from `GUIAPT_Unmodified`
— the `GUIAPT/` set is JeBobs' pristine native-8 drive set.

Tools:
- `tools/work/work.py show <TU> --full [--asm]` — the curated dossier (use this, not raw JSON).
- `tools/assets/bundles/dump_frames.py <bundle>` — frame/command-tag dumper (t3=PlaceObject,
  t1=DoAction, t5=background, t8=morph).
- A hierarchy/PlaceObject dumper + a partial AS2 disassembler (`disasm_apt.py`, resolves inline
  string operands, NOT dict[N]) were written in the session scratchpad — recreate if needed.
- `IDA Files/*.i64` — the reference DBs (Xbox One = the x64 parity target).

---

## 10. HARD-WON GOTCHAS (don't relearn these)

- **The compile gate is x64** (vendored EASTL, `vcvars64`, 8-byte pointers). Reconstruct with
  named logical members, NOT guest 32-bit byte offsets. Native-8 struct offsets legitimately
  differ from console (a leading pointer field grows 4→8).
- **Hex-Rays pseudocode misattributes stack-spill stores as member writes** — trust `--asm`.
- **onLoad is DEFERRED**: the binding `tick()` only QUEUES it (`queueClipEvents`→`AddFunctionBack`);
  it EXECUTES later in `RunActions` (`AptAnimationTarget.cpp:1501`). Arm traces THERE, not at the tick.
- **`AddNewAptComponent`/registration is the ONLY blocker** — everything downstream (`UpdateAll`,
  render) is real and no-ops only because 0 components register.
- **Do NOT patch the core AS interpreter on a hunch** — 7 candidates already refuted; a wrong
  change regresses every AS path (breaks the working menu + the framework `registerClass`).
- **Preserve the working menu**: keep `KB_CLASS_BINDING=false` in any commit; the shim menu must
  keep booting green.
- The `§6.4` diagnosis in `ONE_TO_ONE_REMAINING.md` (entries 4a-4j) contains SUPERSEDED
  sub-hypotheses — trust §1-7 of THIS doc + entry 4j + the commit messages over the older 4a-4i.

---

## 11. SANITY BASELINE (what a correct fix boot looks like)

With `KB_CLASS_BINDING=true` today you get (the BUG state):
```
[AptRT] framework: 'MAIN' up ... @level 0     ; registerClass 24× (RivalShutdown/Ticker/B5MenuItem/...)
[AptRT] persist: 'PERSISTENTAPT' up ... @level 2  ; its components bind (ScrollableSelectionItem/ControllerButtons/...)
[AptRT] SendAptEvent#N np=4: ev(id=1) uid=1 | p2Vft=-1 p2='<undef>' | p3Vft=1 p3CIH=0 p3='_global'   (×67)
AddNewAptComponent / REGISTERED : 0
```
A CORRECT fix boot: `p2` = a real component name string, `p3CIH=1` (a CIH clip), and
`AddNewAptComponent` fires > 0. That is the green light to proceed to Steps D-G.
