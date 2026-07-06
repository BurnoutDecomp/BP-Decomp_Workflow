# The real 1:1 APT / ActionScript flow — everything left to do

Scope: the entire **EATech Apt runtime** — the ActionScript-driven Flash-UI engine that
renders every menu/HUD. This is what must become byte-faithful to the Xbox i64 for the
menu (and every other Apt screen) to be truly 1:1. Grounded in the repo's own tracked
faithfulness debt (`progress/faithfulness_baseline.json`), the scaffold headers, and the
stub files — not estimates. 2026-07-05.

> **What "done" means, precisely.** The counts below track *invention-smells* caught by
> `tools/work/faithfulness_lint.py` — a mechanical detector of four fake-code patterns
> (underscore shims, trivial stub bodies, raw `*(T*)(p+N)` offset pokes, home-grown-format
> vocabulary). Driving them to **0 is necessary but NOT sufficient** for 1:1: the lint is
> blind to a fully-written body that still *diverges* from the Xbox binary, and it cannot see
> a function that is missing from the tree entirely (no code ⇒ no smell). The authoritative
> 1:1 gate is the one in "How each item is proven 1:1" below — compile + DecFIGS dwarfdump
> named-member conformance + behavioral parity vs `Burnout_External_Xbox_One.exe`. Read the
> smell count as a *floor to clear*, not the definition of finished.

---

## The pipeline (so the gaps below have context)

```
boot → AptInit (orchestration) → AptLoader async-load bundle → Fixup/resolve64 (relocate
serialized offsets → live structs) → compose display list → per-frame tick:
   doFrameControls (place/remove clips) → runStream (execute ActionScript) →
   clip events (onLoad/enterFrame) → AptCommunicator drive → render-tree walk → draw
```

The **VM (runStream + opcodes)** is largely reconstructed and works. The **orchestration**,
the **render path**, big parts of the **Fixup/load** path, and the **menu-drive** are still
scaffold / stub / shim / offset-poke.

---

## Grounded state: 341 tracked invention-smells in the Apt system

Repo-wide the baseline carries **858** smells; the Apt/ActionScript slice of that is **341**.
The remaining 517 are non-Apt (sound state-managers, network, debug UI, physics, RenderWare) —
out of scope here, though some sit in the boot/render path the menu transitively touches.

| Category | Apt slice | Repo-wide | What it means |
|---|---|---|---|
| `apt_shim` | 180 | 180 | Apt function faked as an `Apt<Class>_<verb>` free function, not the real `Class::method` |
| `offset_hack` | 81 | 525 | raw `*(ptr+0xNN)` poke instead of a reconstructed struct member |
| `engine_stub` | 43 | 105 | trivial/empty body that calls itself a stub, not reconstructed |
| `format_vocab` | 36 | 47 | runtime format-guessing / accommodation the original never did |
| `pack_accom` | 1 | 1 | `#pragma pack(4)` bent to a mis-emitted bundle layout |
| **Total** | **341** | **858** | the Apt slice must reach **0** (necessary, not sufficient — see top) |

**Caveat on the 180 `apt_shim`:** 42 of them live in `*_embed_check.cpp` test-harness files
(scaffold, not shipped engine code). The real shipped-engine invention count is **299**
(`138 apt_shim + 43 engine_stub + 81 offset_hack + 36 format_vocab + 1 pack_accom`); the other
42 are harness shims to retire alongside. The full per-file breakdown is the appendix at the
bottom — that table, not this prose, is the source of truth.

**Scope / reproduction.** "Apt slice" = every baseline fingerprint whose path is under
`src/SDKs/EATech/` (excluding the non-Apt infra dirs `eajobs/ rwcore/ rwcollision/ rwmath/
coreallocator/`) **or** contains `AptInterface`, `CgsAptDataHeaderType`, or
`BrnAptRuntimeBringUp`. Regenerate the baseline with
`python tools/work/faithfulness_lint.py --baseline` (only after deliberately paying debt down),
then re-derive this slice with that predicate.

---

## 1. Orchestration layer — retire the `BrnAptRuntimeBringUp` facade

`src/GameSource/Gui/BrnAptRuntimeBringUp.cpp` is **not in the original game**; its header says
it *is* the stand-in for the un-reconstructed X360 orchestration. Debt here: **16 offset_hack
+ 16 format_vocab + 3 apt_shim = 35**. Reconstruct and delete the facade:
- `AptInit` / `AptCommonInitialize`
- `AptAllocatorInitialize`
- `AptUpdateInitialize` (a hardcoded default-config block in `AptInit.cpp`; not smell-flagged,
  so it will not show in the count — verify against the X360 body regardless)
- `AptRenderInitialize`
- `AptCreateTargetInstance` / `AptChangeTargetInstance`
- `AptUpdate` (the real per-frame driver; today `AptRuntimeUpdate` in the facade)
- `AptRuntimePlayMovie` + the async `.apt` streamer (`aptloader_startasyncload` shim)
- `AptThreadIdLock` acquire/release (`AptInit.cpp`, **2 apt_shim** — these are the two tracked
  smells in that file, not `AptUpdateInitialize`)

## 2. Render path — the single biggest gap

**`AptRenderLinkStubs.cpp` carries 64 tracked smells** (24 `apt_shim` + 37 `engine_stub` +
3 `format_vocab`) — the render-tree walk and draw calls that link but do nothing, "homed as the
render path hits each." The `apt_shim`+`engine_stub` pair (61) are the empty link-stub bodies.
Plus:
- `AptRenderItem.cpp` (6 apt_shim), `AptRenderTreeManager.cpp` (4 apt_shim),
  `AptRenderHooks.cpp` (3 apt_shim), `AptRenderWalk.cpp` (1 engine_stub),
  `CgsAptCallbackRender.cpp` (1 apt_shim + 2 engine_stub), plus the render-item
  `*_embed_check.cpp` harness shims.
- **Retire the `CgsGraphics::Im2d` swap** — the scaffold renders Apt through the immediate-mode
  Im2d renderer instead of the faithful `ImRenderBuffer` / `gAptFuncs.pfnDrawRenderingUnit`
  render-tree walk (the original "AV'd on first use", so it was bypassed). Reconstruct the real
  walk and drop Im2d for this path.

The render cluster (~89 tracked smells, dominated by `AptRenderLinkStubs`' 64) is the largest
single body of work; 1:1 requires reconstructing each to its X360/XB1 body.

## 3. The ActionScript VM (interpreter) — the deep leaves

The dispatch loop works, but many leaves are still shim/offset-poke stubs:
- `AptActionInterpreterInterpHelpers.cpp` — **19 apt_shim + 1 offset_hack**: `getVariable`'s
  deep resolvers (`getContext` path parser, `AptInterp_LookupScopeChain`,
  `AptInterp_LookupGlobalFallback`), `HasMember`, the dictionary fetch.
- `AptCIHBehaviour.cpp` — **13 apt_shim + 1 format_vocab**: `FindAndSetEvents` leaves, the
  clip-event dispatcher, `HasEventMember` proto-chain.
- `AptCIHNativeFunctionHelper.cpp` — **8 apt_shim**: native AS methods (localToGlobal, etc.).
- `AptActionInterpreterStackOps.cpp` — **5 apt_shim + 1 offset_hack + 1 format_vocab**:
  `CallMethod` tail (apply/call spread, this-binding walk, super-call).
- `AptArray.cpp` (3 apt_shim), `AptActionDispatch.cpp` (1 engine_stub),
  `AptActionInterpreterParseStream.cpp` (**9 offset_hack** — the const-record / stream reads),
  `AptActionTryCatchFinallyBlock.cpp` (3 offset_hack), `AptAnimationTarget.cpp`
  (6 apt_shim + 1 engine_stub + 3 offset_hack), `AptActionInterpreter.cpp` (2 apt_shim).

## 4. The load / Fixup pipeline — offset-pokes → real structs

- `AptMovie.cpp` — **21 offset_hack + 3 format_vocab + 2 apt_shim** (`placeCommand`/`removeCommand`):
  `doFrameControls`, place/remove commands, the `CmdPayloadI32` dual-format read (+4/+8),
  `queueFrameActions`.
- `AptCharacterAnimation.cpp` — **15 offset_hack + 1 apt_shim** (`Link`): `Fixup` / `resolve64`
  (the serialized→live relocation — where the DF2 argtab, const-table, import-table are walked).
- `AptDisplayList.cpp` — **8 apt_shim**: `AssociateInstToClass`, `instantiateCharacter`, place.
- `AptLoader.cpp` (4 format_vocab), `AptLoader.h` (2 format_vocab),
  `AptLoader_embed_check.cpp` (2 apt_shim): async load, `CompleteLoad`, import availability.
- `AptCharacterHelper.cpp` (3 offset_hack), `AptCIHText.cpp` (4 offset_hack),
  `CgsAptDataHeaderType.cpp` (3 offset_hack), `AptCharacterSpriteInstBase.h`
  (**1 pack_accom + 1 format_vocab** — the `CmdPayloadI32` belt-and-suspenders that only exists
  because of the emitter quirk).
- **Faithful import-export resolution (Fixup pass-3)** — `AptMovie::resolve` + `AptLoader::Load`
  (PS3-ext `@0x80E9E4`): real bundles keep imports as import-table entries; needed so
  class-linked clips (TransitionComponent, B5MenuItem…) resolve their AS classes.

## 5. The bundle data pipeline (fan-tool artifacts → faithful)

`build/game/GUIAPT` is **JeBobs' fan-made native-8 bundles** + `apt8_fix_frametables.py` data
patches for the emitter's alignment bugs. None of this is original. (These bundle artifacts are
not source files, so they are **not** counted in the 341 — but they are load-bearing invention.)
Sub-items:
- **DF2 argtab layout is mis-emitted** (name at +4; Xbox i64 authoritative layout is name at +8,
  stride 16 — confirmed via `sub_14084A920` case 142). Repair it like the other emitter bugs.
- The existing frame-table / command-record repairs (`apt8_fix_frametables.py`) are themselves
  non-original data patches over a fan tool.
- **True 1:1** = the faithful in-engine Fixup consuming the console `1:7:4` data directly (or an
  authoritative X360→PC bundle port), retiring the fan-tool + patch-script dependency entirely.

## 6. The menu-drive path — "Layer 2"

Today the menu is driven by the **shim** `AptRuntimeSetComponentKeyValue` + the
`AptRuntimeSetComponentViewState` pair-map. Replace with the real chain and delete the shim:
1. ✅ **DONE (2026-07-06) — Repair the DF2 argtab** in the bundles. Was the live crash
   (`AptScriptFunction2::SetArgument` AV when class binding ran an arg-bearing method). ROOT
   CAUSE: JeBobs' emitter writes DF2 arg records as {reg u32@0, name-offset u32@4} stride 16;
   the engine + XB1 arbiter (`sub_14084A920` case 142: relocate name at `argtable+16*i+8`) read
   the name as a u64 pointer @+8. The ENGINE is XB1-faithful (parse case 0x8E: nStride=16
   nNameOff=8); the BUNDLE is non-conformant. FIX = `tools/assets/bundles/apt8_fix_df2_argtab.py`
   (in-place: name +4→u64@+8, zero +4; MAIN 16 args + TOGGLE 2 args). Verified with
   `KB_CLASS_BINDING=true`: class binding runs 98× with **no SetArgument crash** (was the AV).
2. **Re-apply the 3 genuine engine fixes** cleanly (no probes/guards): the `prototype` key, the
   clip-event mask table `gAptMemberIndexToEventBit` (extracted from X360 rodata), the
   `CallMethod` `GetHasClass` vtable-slot fix. *(saved on branch `l2-drive-clean` @ `def36a39`)*
3. **Clip-class instantiation** — PARTLY LANDED (2026-07-06). Was blocked by `<no-registry>` (empty
   registry): the real cause was **registerClass never firing** because MAIN's tag-1 AS-bootstrap
   stream (`new AptCommunicator` + registerClass table, @chunk+0x32e8) was straddled to `0x800000000`
   by the emitter (same misaligned-tag-1 bug) and `queueFrameActions` dropped it. FIX = swap
   `GUIAPT_MaybeBroken/MAIN.bundle` (intact @0x32e8) + re-apply `apt8_fix_df2_argtab`. NOW
   (binding on): registerClass fires 24×, **9 title classes bind** (TransitionComponent, B5MenuItem×2,
   StaticHelpItem, ControllerButtons), **ctors run**, SetArgument invoked. **← CURRENT FRONTIER:**
   SetArgument arg-name relocation truncation — a 2-arg fn gets arg[0] name full ptr but arg[1] name
   high-dword-zeroed (32-bit relocation). DF2 repair verified correct offline; the truncation is an
   engine resolve64/SetArgument bug on the 2nd+ arg (argtab is 4-mod-8, not 8-aligned). Needs cdb.
   THEN `onLoad` → `SendAptEvent(ONLOAD)` → `AddNewAptComponent`.
4. **Per-frame `UpdateAll`** drives the clips through the real communicator path.
5. **Delete the shim** — the `AddOutputAptViewState` FLAG fallback + the viewstate pair-map.
6. **Validate** — menu text / states / navigation byte-identical to the Xbox i64.

## 7. Init / globals / GC leftovers

`AptStringPool.cpp` (1 apt_shim, `aptstringpool_initialize`), `AptValueGCPoolManager.cpp`
(2 apt_shim), `AptGC.cpp` (**1 apt_shim + 1 format_vocab** — the deferred-release drain),
`CgsAptAux.cpp` init config (**2 offset_hack + 4 format_vocab**).

---

## Priority order (dependency-first)

1. ✅ §5 DF2 argtab repair DONE (§6.1) → next is §6.2 (re-apply the 3 engine fixes) + §6.3.
2. §4 faithful Fixup / import-export → §6.3–6.4 (clips instantiate + drive). **Current frontier:
   export-name → class-registry binding at placement (clips resolve `<no-registry>`).**
3. §6.5–6.6 delete shim + validate vs Xbox i64 ← **the menu drives faithfully.**
4. §2 render path (the ~89-smell cluster + Im2d retirement) — the biggest single body of work.
5. §1 orchestration (retire the facade), §3 VM leaves, §7 init/GC, and the 42 `_embed_check`
   harness shims.
6. §5 retire the fan-tool bundle pipeline for the faithful in-engine path.
7. Drive the **341** Apt invention-smells to **0** (offset_hack → engine_stub → format_vocab →
   apt_shim → pack_accom); re-run `faithfulness_lint.py` to confirm the baseline shrinks and
   never regrows. **This clears the floor; it does not by itself prove 1:1** — every touched TU
   must still pass the gate below.

## How each item is proven 1:1

- **Per function:** compile gate + DecFIGS dwarfdump named-member conformance + fresh-eyes review.
- **Behavioral:** boot-test, compare observable behavior against `Burnout_External_Xbox_One.exe`
  (menu text/states/nav/timing identical). A shim that "looks right" but diverges does not pass.
- **Debt ratchet:** the Apt slice of `faithfulness_lint.py` must go 341 → 0 and never regrow —
  a *necessary floor*, not the finish line. Faithfulness = the dwarfdump + behavioral gate above.
- **Completeness caveat:** the lint only sees code that exists. Any Apt function still entirely
  missing from the tree contributes no smell, so "341 → 0" does not certify coverage — only that
  what *is* present carries no detectable invention.

---

## Appendix — full per-file smell table (source of truth, 341 across 79 files)

Generated from `progress/faithfulness_baseline.json`. `*_embed_check.cpp` rows are test-harness
scaffold (42 apt_shim total), not shipped engine bodies.

| file (under `b5-decomp/src/`) | smells |
|---|---|
| `SDKs/EATech/AptRenderLinkStubs.cpp` | 64 — 24 apt_shim, 37 engine_stub, 3 format_vocab |
| `GameSource/Gui/BrnAptRuntimeBringUp.cpp` | 35 — 3 apt_shim, 16 offset_hack, 16 format_vocab |
| `SDKs/EATech/include/Apt/AptMovie.cpp` | 26 — 2 apt_shim, 21 offset_hack, 3 format_vocab |
| `SDKs/EATech/include/Apt/AptActionInterpreterInterpHelpers.cpp` | 20 — 19 apt_shim, 1 offset_hack |
| `SDKs/EATech/include/Apt/AptCharacterAnimation.cpp` | 16 — 1 apt_shim, 15 offset_hack |
| `SDKs/EATech/include/Apt/AptCIHBehaviour.cpp` | 14 — 13 apt_shim, 1 format_vocab |
| `SDKs/EATech/include/Apt/AptAnimationTarget.cpp` | 10 — 6 apt_shim, 1 engine_stub, 3 offset_hack |
| `SDKs/EATech/include/Apt/AptActionInterpreterParseStream.cpp` | 9 — 9 offset_hack |
| `SDKs/EATech/include/Apt/AptCIHNativeFunctionHelper.cpp` | 8 — 8 apt_shim |
| `SDKs/EATech/include/Apt/AptDisplayList.cpp` | 8 — 8 apt_shim |
| `SDKs/EATech/include/Apt/AptActionInterpreterStackOps.cpp` | 7 — 5 apt_shim, 1 offset_hack, 1 format_vocab |
| `GameShared/GameClasses/Gui/View/AptInterface/CgsAptAux.cpp` | 6 — 2 offset_hack, 4 format_vocab |
| `SDKs/EATech/include/Apt/AptRenderItem.cpp` | 6 — 6 apt_shim |
| `SDKs/EATech/include/Apt/AptCIHText.cpp` | 4 — 4 offset_hack |
| `SDKs/EATech/include/Apt/AptLoader.cpp` | 4 — 4 format_vocab |
| `SDKs/EATech/include/Apt/AptRenderTreeManager.cpp` | 4 — 4 apt_shim |
| `GameShared/GameClasses/Gui/Model/Resources/CgsAptDataHeaderType.cpp` | 3 — 3 offset_hack |
| `GameShared/GameClasses/Gui/View/AptInterface/CgsAptCallbackRender.cpp` | 3 — 1 apt_shim, 2 engine_stub |
| `SDKs/EATech/Apt/AptActionTryCatchFinallyBlock.cpp` | 3 — 3 offset_hack |
| `SDKs/EATech/include/Apt/AptArray.cpp` | 3 — 3 apt_shim |
| `SDKs/EATech/include/Apt/AptCharacterHelper.cpp` | 3 — 3 offset_hack |
| `SDKs/EATech/include/Apt/AptRenderHooks.cpp` | 3 — 3 apt_shim |
| `SDKs/EATech/Apt/AptInit.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/Apt/AptValueGCPoolManager.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptActionInterpreter.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptArray_embed_check.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptCIH_embed_check.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptCharacterAnimation_embed_check.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptCharacterInst_embed_check.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptCharacterSpriteInstBase.h` | 2 — 1 format_vocab, 1 pack_accom |
| `SDKs/EATech/include/Apt/AptCharacter_embed_check.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptFile.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptFile_embed_check.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptFrameStack.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptGC.cpp` | 2 — 1 apt_shim, 1 format_vocab |
| `SDKs/EATech/include/Apt/AptIntervalTimer.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptLoader.h` | 2 — 2 format_vocab |
| `SDKs/EATech/include/Apt/AptLoader_embed_check.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptNativeHash_embed_check.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptObject_embed_check.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptRenderItemCustomControl.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptRenderItem_embed_check.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptSharedPtr_embed_check.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptTarget.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptTextFormat.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptValue/AptValue.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/include/Apt/AptValueWithHash_embed_check.cpp` | 2 — 2 apt_shim |
| `SDKs/EATech/Apt/AptStringPool.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptActionDispatch.cpp` | 1 — 1 engine_stub |
| `SDKs/EATech/include/Apt/AptActionInterpreterContext.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptActionInterpreterSpecialOps.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptActionInterpreter_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptAnimationTarget_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptCIH.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptCharacterAnimationInst.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptCharacterLevelInst_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptCharacterMorphInst_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptCharacterShapeInst_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptCharacterSpriteInst_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptCharacterStaticTextInst_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptDisplayListState_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptLinker.cpp` | 1 — 1 engine_stub |
| `SDKs/EATech/include/Apt/AptMovie_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptRenderItemDynamicText_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptRenderItemShape_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptRenderItemSprite_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptRenderTreeManager_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptRenderWalk.cpp` | 1 — 1 engine_stub |
| `SDKs/EATech/include/Apt/AptScriptFunctionBase.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptSharedPtr.h` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptTarget_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptTextFormat_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptValue/AptExtern.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptValue/AptString.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptValue/AptStringObject_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptValue/AptString_embed_check.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptValue/AptValueConvert.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptValue/AptValueFindChild.cpp` | 1 — 1 apt_shim |
| `SDKs/EATech/include/Apt/AptValue/AptValue_embed_check.cpp` | 1 — 1 apt_shim |
