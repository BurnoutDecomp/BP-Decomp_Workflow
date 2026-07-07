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
3. ✅ **DONE (2026-07-06) — Clip-class instantiation + ctors + onLoad dispatch.** Was blocked by
   `<no-registry>`: the real cause was **registerClass never firing** because MAIN's tag-1
   AS-bootstrap stream (`new AptCommunicator` + registerClass table, @chunk+0x32e8) was straddled
   to `0x800000000` by the emitter and `queueFrameActions` dropped it. Data FIX = swap
   `GUIAPT_MaybeBroken/MAIN.bundle` (intact @0x32e8) + `apt8_fix_df2_argtab.py` +
   `apt8_align_df2_argtab.py` (8-align the argtab; fixes the arg[1] name high-dword truncation).
   Three ENGINE fixes made the ctor bodies run to completion (all committed on `l2-drive-clean`):
   - **DOGMA 8-byte allocation granularity** (`82bd5cd0`): the pool rounded requests to 4 bytes →
     every 4-mod-8 request misaligned subsequent vtbl'd AptValues on x64. Also cut title memory
     ~3400 → ~900 MB.
   - **`AptValue::Append_ToString` x64 offset** (`1c9c7ba1`): read the embedded `EAStringC` at the
     console `+8`; on x64 the AptValue base is 16 B so the string is at `+0x10` — the `+8` read
     `{mnValueData, pad}` as the buffer ptr (`0xBAADF00D…`) → the AS `+` use-after-free crash.
   - **onLoad tick-order** (`dbcd9964`): `AptCIH_AssociateInstToClass` ticked the node BEFORE
     `FindAndSetEvents` set the onLoad mask, so the fresh-bit clear raced `HasEvent(onLoad)`.
   RESULT (binding on): registerClass fires 24×, 9 title classes bind, **all 9 ctors run their
   bodies without crashing**, and **onLoad is dispatched + runs** (9× FUNCTION-drain of one shared
   handler; `AptCIH_queueClipEvents_RunMatched` deferred `__proto__` path resolves it via findChild).
4a. ✅ **DONE (2026-07-06, b5-decomp `cf4586e9`) — extension natives now dispatch.** The reason
   `onLoad`'s `SendAptEvent` was a silent no-op: **`AptExtObject` (the CAptCommunicator extension base,
   tag 29) never overrode `GetNativeHashVirtual()`** so it inherited `AptValue`'s `return 0`.
   `_FunctionAptActionCallMethod`'s Extension-receiver path resolves natives via
   `receiver->GetNativeHashVirtual()->Lookup(name)` — a null hash made EVERY extension native
   (SendAptEvent / SetCommunicationObject / GetCircleButtonAsSelect / SendAptSoundEvent) resolve to null
   → no-op. Console vtbl[2] returns `mpNativeHash` (+8); the override was dropped in the x64 recon. FIX =
   add `GetNativeHashVirtual`/`ContainsNativeHashVirtual` overrides. Also fixed `sMethod_SendAptEvent`'s
   two int-param guards (raw `& 0x7F` → `getVtblIndex()`; meValueType is bits 25-31 on x64, not the low
   7). Corrected mental model: (i) `SetCommunicationObject` was a RED HERRING — `mpAptInternalCommunicator`
   is write-only; (ii) "0 CallMethod" was a probe misread (it only logs violations); CallMethod fires;
   (iii) `obj.method()` compiles to fused GetMember `0xA5`/`0xAF` + fused call `0x5D/0x5E/0xB2/0xB3` (all
   route through CallMethod); (iv) onLoad DOES run (9× FUNCTION-drain of the shared `BurnoutComponent.onLoad`
   via the deferred `__proto__` path). BOOT-VERIFIED: SetCommunicationObject binds, SendAptEvent dispatches.
4b. ✅ **DONE — `_name` MovieClip property getter** (`fe0ad58f`). `AptCIH::objectMemberLookup` was a
   *deferred* console override; `_name` fell through `findChild` to undefined, so a class-bound clip's ctor
   `this.msName = this._name` stored undefined. Reconstructed the override for `_name` → `GetInstanceName()`
   (returns 0 for other names so `findChild` is unchanged). Boot-verified: `setVar msName` flips undefined
   → string. The full MovieClip property set (`_x/_y/_width/_visible/…`) is a follow-on.
4c. **The full AS drive chain is DISASSEMBLED (runtime opcode+dict trace) and the remaining blocker is at
   the FRAMEWORK-MOVIE / stage-B level — ← CURRENT FRONTIER (§6.4).** The AS:
   ```
   onLoad()          = { this.BuildName(); gAptCommunicator.RegisterComponent(name, this); this.Initialize(); }
   BuildName()       = { this.msName = this._name;
                         reg = this._parent; while (reg && !reg.IsBurnoutComponent()) reg = reg._parent;
                         return reg.msName; }                     // ← the registration name
   RegisterComponent = { CAptCommunicator.SendAptEvent(KI_EVENT_ONLOAD, uid, name, clip); }
   Initialize()      = { this._visible = false; ... }             // ← why binding-on renders BLACK
   ```
   `BuildName` returns undefined because its `_parent`-walk overruns to `undefined`. A hierarchy trace
   DISPROVED an earlier "needs stage-B" guess: the menu items DO have bound ancestors **within the title**
   (`MenuItem_0 → SelectionMenu_mc(bound) → ''(bound) → root`), so NO framework-movie root is needed. The
   walk overruns because **`reg.IsBurnoutComponent()` does not resolve on the ancestor clips** (the opcode
   trace shows the `CallMethod` runs no body → returns undefined → the loop continues past every ancestor).
   `SelectionMenu_mc` is bound (has `__proto__`) yet `IsBurnoutComponent` (a `BurnoutComponent.prototype`
   method) isn't in its proto chain → its class is not `BurnoutComponent`-derived, OR its
   `Extends BurnoutComponent` (0x69) didn't run / wire the proto link during MAIN's class-def init streams.
   Per-clip primitives verified faithful: `AssociateInstToClass` Sets `__proto__` = class prototype (proven —
   onLoad runs); `Extends` correctly chains `B5X.prototype.__proto__ = BurnoutComponent.prototype`. NEXT
   (tractable, title-local — NOT stage-B): identify the container clips' bound classes and why the
   `IsBurnoutComponent` method doesn't resolve up their `__proto__` chain (likely an `Extends`/class-def
   coverage gap for the container component classes). Interim: `SendAptEvent`/`SendAptSoundEvent` carry
   FLAG'd graceful guards (no-op on bad args) so the shim menu stays working (0 asserts).
4d. ✅ **RESOLVED the (a)-vs-(b) fork via a fresh boot trace (2026-07-06).** Widened `AptRegisterClassProbe`
   (24→64) + logged the export name for `<no-class>` binds, `KB_CLASS_BINDING=true`, booted to title.
   FINDINGS: (1) MAIN registers **64** classes (the old probe truncated at 24!) incl. `B5MenuItem`,
   `Carousel_mc`/`CarouselItem_mc`, `Toggle_mc`/`ToggleItem_mc`, `ScrollableSelectionItem`, `TextField`,
   `ColourField`, `Ticker`, … but **NO `SelectionMenu`** class exists anywhere. (2) The bring-up loads
   **ONLY `MAIN` at level 0** — `PERSISTENTAPT` (the OTHER framework bundle, which "also has some" component
   classes) is NEVER loaded/bootstrapped, so any class it registers is missing. (3) The menu-container clip
   `SelectionMenu_mc` logs `<no-export-name>` — it is a plain timeline container with an INSTANCE name but
   **no LINKAGE/export name**, so it can NEVER bind to a class (`AssociateInstToClass` needs the export name
   to hit the registry). The `<no-class:…>` binds are all ART (`Bg`/`copyright2`/`ButtStart`/`MenuDirt`/…),
   confirming pm9(6). CONCLUSION (resolves the ambiguity): the menu items (`B5MenuItem`, which DO bind) have
   **NO within-title BurnoutComponent ancestor** — the container cannot be a class (no linkage name) and no
   `SelectionMenu` class exists — so `BuildName`'s `_parent`-walk correctly overruns. §6.4 is therefore
   **NOT** a per-clip primitive fix and **NOT** a title-local container class-link; it is at the
   **FRAMEWORK-COMPOSITION level**. The tractable next leads, in order: **(i)** load + bootstrap
   `PERSISTENTAPT.bundle` (add a second framework slot alongside MAIN) and re-trace — its registerClass may
   supply the menu-framework classes MAIN lacks; **(ii)** if still no component ancestor, the console composes
   the menu THROUGH the framework's component system (§6.5 `UpdateAll` dynamically builds/nests it) rather than
   from static title clips — wire `UpdateAll` and see whether the framework establishes the hierarchy; **(iii)**
   only if both fail, the title-under-framework NESTING (stage-B). Diagnostic reverted; KB_CLASS_BINDING=false,
   working menu rebuilt.
4e. ✅ **DEFINITIVE (2026-07-06, trace 2) — §6.4 root cause PINNED, and it IS §4.** The title's expected component
   classes (`SelectionMenu`, `SelectionMenuAnimatorComponent`, `BackgroundAnimatorComponent`,
   `StartMessageAnimatorComponent`) exist ONLY in TITLE_SCREEN02.bundle (the title defines its own). Uncapping the
   registerClass probe (24→200) confirmed **200+ classes register**, incl. the title's own `TransitionComponent`/
   `ControllerButtons`/`StaticHelpItem` (which bind). BUT the menu-container clip still logs **`<no-export-name>`** —
   its char has NO entry in the title's export table, so `AssociateInstToClass` fails at the export-NAME step (before
   the registry lookup). So §6.4 is NOT a missing class and NOT framework nesting; it is the **container's EXPORT/
   LINKAGE resolution**. The container is one of the title's type-5 IMPORTED sprite containers (content in the 5
   import bundles); its export-name link arrives via the **DEFERRED import-export resolution == §4 "Faithful
   import-export resolution (Fixup pass-3) — AptMovie::resolve + AptLoader::Load, PS3-ext @0x80E9E4"** (the un-homed
   import `.apt` load, AptDisplayList.cpp:~626). **⇒ §6.4 (menu drive) and §4 (import-export) are the SAME blocker.**
   The class-linked clips that DO bind resolve via the title's OWN export table; the container resolves via an import
   → deferred → no export name → no class → no component ancestor → BuildName overruns. **THE fix for §6.4 is to
   complete §4's import-export resolution** so an imported container char resolves its export name (+ its
   `SelectionMenuAnimatorComponent` class). Then: §6.5 `UpdateAll` (already wired) drives → §6.6 delete shim → §6.7
   validate. This makes §4 the critical-path dependency for the whole menu-drive/shim-deletion chain.
   **TRACE 3 (exact mechanism, 2026-07-06):** a diagnostic in `AssociateInstToClass` counting the char's ROOT-movie
   (`pChar->mpFixupLink`) exports showed the `<no-export>` container clips resolve to a movie with **expCount=625,
   menuish=0** — the container's `mpFixupLink` points to the **IMPORT bundle's root** (625 exports, none the
   menu/Selection/Animator classes), NOT the title root where `SelectionMenuAnimatorComponent` is defined. So
   `AssociateInstToClass` walks the WRONG export table. FIX SHAPE: for an imported clip, resolve the class via the
   **PLACING (title) movie's export/import table** (title import-slot → title export entry → class name), not via
   `pChar->mpFixupLink` (the import root). Title-defined clips (TransitionComponent/B5MenuItem) keep working because
   THEIR `mpFixupLink` IS the title root. This is precisely the console import-export resolution (Fixup pass-3, §4).
   **TRACE 4 (the CORE missing piece — IMPLEMENTED an export-walk fallback, then found the real blocker):** added a
   fallback in `AssociateInstToClass` that, when the char's own root movie misses, walks pNode up to the display root
   and tries the PLACING (title) movie's export table. It compiled + ran but the container STILL logged
   `<no-export-name>`. Reason: the title's export table DOES hold the `SelectionMenuAnimatorComponent` entry
   (charId→name), but `title_charTable[that charId]` is **NULL** — the imported char was never linked into it — so the
   match `charTable[id] == pChar` fails against the title too. ⇒ **§4's CORE missing piece is the import LINK**: the
   deferred `AptCharacterAnimation::Link` / `AptFile::FindExport` must land the referenced import export char into the
   PARENT (title) movie's `charTable[importId]` (the "leaf imports 3→4 Link → the referenced export char lands in the
   parent's charTable[importId]" chain from the §4 notes). ONCE that runs, the title's export walk (or the export-walk
   fallback) matches and the container binds. Fallback reverted (unverified vs console asm + non-functional without the
   Link); the concrete §4 task is now: home the import-bundle load (`AptLoader_StartAsyncLoad`/`LoadImportBundle`
   exist in the bring-up) + the `AptCharacterAnimation::Link` charTable-population so `title_charTable[importId]` is
   filled. Diagnostic reverted; KB_CLASS_BINDING=false; working menu rebuilt.
4f. ⚠️ **CORRECTION (trace 6 — the import-Link conclusion was PREMATURE).** The existing `CgsApt_ImportProbe` shows the
   FLOW (title) movie has **importCount=5**, and the 5 imports are `B5MenuItem::MenuArrow`,
   `B5HelperComponents::TransitionComponent`, `B5MenuItem::B5MenuItem`, `B5ControllerButtons::Grunge_Buttons_Backing`,
   `B5HelpItem::StaticHelpItem` — all 5 load + resolve (import-load complete) and their clips BIND. The
   `SelectionMenu`/`SelectionMenuAnimatorComponent` container is **NOT among the 5 imports**, so it is NOT an imported
   clip and §6.4 is NOT the import path. Its `mpFixupLink → a 625-export movie (menuish=0)` is therefore a **WRONG/garbage
   back-link** — the known "deep-nested container's back-link may not reach a charTable-bearing root (garbage
   mpCharacterTable/mnCharacterCount)" issue (`AptMovie::PlaceCommand` guards it with `bAnimSane`). **REAL §6.4 blocker =
   the title's nested SelectionMenu/Animator container clips get the WRONG `mpFixupLink` (charTable[0] back-link) from
   Fixup**, so `AssociateInstToClass` walks a bogus export table instead of the title's (which HAS the
   `SelectionMenuAnimatorComponent` export). The import path (§4, the 5 imports) works. NEXT: instrument
   `AssociateInstToClass` to compare the container's `pChar->mpFixupLink` vs the title root char, find why nested-container
   back-links diverge, and fix Fixup's `mpFixupLink` population for nested title clips. §6.5-6.7 remain gated on this
   (a nested-container Fixup back-link fix, precisely localized), NOT on import-export resolution.
4g. ✅✅ **DEFINITIVE root cause — disassembly-verified engine + OFFLINE bundle dump (2026-07-07). SUPERSEDES traces
   3-6 above (all had a wrong sub-hypothesis).** (a) Read the XB1 Fixup `sub_1408378E0` + X360 `AssociateInstToClass`
   @0x82B073B8 — the ENGINE IS FAITHFUL (back-link `char[+8]=charTable[0]`; export walk over `char->mpFixupLink`'s
   table). The `625` export count for the 41-char title is REAL (Flash exports many nested named symbols), not a bad
   offset. (b) Hard measurement (a `[AptRT] REGISTERED` probe at `AptCommunicator::AddNewAptComponent`): only the 4
   IMPORT clips bind; the title's `*AnimatorComponent` clips do NOT bind; **`AddNewAptComponent` fires ZERO times — NO
   component registers.** (c) OFFLINE bundle dump (`/tmp/find_ref.py` reusing the apt8_fix_frametables parser):
   `SelectionMenuAnimatorComponent` appears in TITLE_SCREEN02.bundle **exactly once, at chunk+0x7010 with charId=-1, and
   is NOT in the 625-entry export table** (0x170..0x2880). ⇒ **the title's OWN component clips have NO static char→class
   export linkage** — they are meant to be instantiated/bound by the title's ActionScript FRAMEWORK at runtime
   (`Object.registerClass(...)` + the init-action attach stream at chunk+0x7010), NOT statically via `AssociateInstToClass`.
   The 4 imports bind only because their SEPARATE bundles carry static linkage. **So §6.4 == running the title's AS
   init-action framework component-drive** (the long-noted "MAIN/framework movie drives the menu" thread, now PROVEN from
   the bundle bytes). And even the imports don't register because `BuildName` needs a bound-component ancestor that only
   the framework-instantiated components would provide. **This is a substantial reconstruction (the init-action VM
   component-instantiation), not a static-data or offset fix — genuinely multi-session.** §6.5 (UpdateAll) → §6.6 (delete
   shim) → §6.7 (validate) → deleting `BrnAptRuntimeBringUp` all sit behind it. NEXT: trace/execute the title frame-0
   init-action stream (the chunk+0x7010 registerClass+attach) so the framework creates+binds its components.
4h. ⚠️ **CORRECTION of 4g (the "no static linkage / framework-attach" claim was WRONG — the components DO bind).**
   Decoded the chunk+0x7010 record: it is a **PlaceObject** (flags=0xa6 HasChar+Matrix+Name+ClipActions, depth=29,
   **charId=30**, instance-name="SelectionMenuAnimatorComponent", matrix tx=1368.7/ty=406.1; the `-1` I first read is
   the clipDepth @+0x38, not charId). So the AnimatorComponent clip PLACES import char 30 (a B5HelperComponents symbol)
   and its INSTANCE name is the class-name string. Class-binding uses the placed CHAR's export name (via the char's
   `mpFixupLink` = the import bundle's root), NOT the instance name. Confirmed by dumping B5HelperComponents' export table
   (root+0x68 IS the real class-export table): exports `TwizzleComponent`@2, `TransitionComponent`@4,
   `B5ScaleAndTintInterpolatorInst`@6. ⇒ the AnimatorComponent clips DO bind (under their char's class, e.g.
   TransitionComponent — which is exactly what appears in the bind list); I was conflating instance-name vs class-name.
   **The ONE fact consistent across every careful trace: components BIND + onLoad RUNS, but `AddNewAptComponent` fires
   ZERO times — registration fails at `BuildName` (no bound-component ANCESTOR in the display tree).** THAT is the real,
   stable §6.4 core (same as pm9). The session's import-Link / Fixup-back-link / no-linkage sub-hypotheses were all
   wrong detours (lesson: [[read-disasm-before-boot-tracing]]). REAL NEXT: why does `BuildName`'s `_parent`-walk find no
   BurnoutComponent ancestor — i.e. which display node SHOULD be the menu items' component ancestor, and does it bind?
   (Trace the bound clips' display-parent chain + each parent's bound class.) §6.5-6.7 gate on giving the components an
   ancestor so BuildName resolves → registration.
5. ✅ **DONE / WIRED (verified 2026-07-07) — Per-frame `UpdateAll` drive through the real communicator
   path.** The chain is homed to its console addresses and runs every frame:
   `AptAux::UpdateComponents` (CgsAptAux.cpp:241, X360 `0x82850570`) → `mpAptCommunicator->UpdateAllComponents()`
   → `AptCommunicator::UpdateAllComponents` (CgsAptCommunicator.cpp:423, X360 `0x828499D0`; collects each
   dirty component's bound ref into a temp array + clears the per-frame dirty flags) →
   `AptCallFunctionOpti("UpdateAll", 0, "gAptCommunicator", 1, lpArray)`. It currently **no-ops only because
   `muNumActivecomponents == 0`** (§6.4 registers nothing) — the drive itself is faithful and complete. (It
   is presently *triggered* from the `BrnAptRuntimeBringUp` tick @2404, standing in for the console
   `AptAux::Update` @0x82853B20 per-frame call; that trigger site moves onto `AptAux::Update` when the facade
   is retired in item 6.)
6. **Delete the shim** — the `AddOutputAptViewState` FLAG fallback + `AptRuntimeSetComponentKeyValue`
   / the `AptRuntimeSetComponentViewState` pair-map (single driver). ⛔ **HARD-GATED on §6.4:** the shim is
   what currently drives the *working* menu; because §6.4 registers 0 components, the real `UpdateAll` path
   (item 5) drives nothing, so deleting the shim now makes the menu go **dead/blank**. It can only be removed
   once §6.4 gives the menu items a bound-`BurnoutComponent` ancestor → `BuildName` resolves → `SendAptEvent`
   → `AddNewAptComponent` registers → `UpdateAllComponents` has components to drive.
7. **Validate** — menu text / states / navigation byte-identical to the Xbox i64. ⛔ Gated on §6.4 + item 6
   (needs the real drive producing the menu before a byte-diff is meaningful).

### §6.4 — EXECUTION PLAN (start a DEDICATED boot-loop session here; distilled from traces 4a–4h)
**Confirmed root cause:** the title's own component clips (`SelectionMenu` / `*AnimatorComponent`) are
PLACED by init-actions (PlaceObject @chunk+0x7010, charId from an import) but are NOT statically
class-bound; the menu items (`B5MenuItem`) DO bind + onLoad runs, but `BuildName`'s `_parent`-walk finds
no `BurnoutComponent` ancestor → `SendAptEvent` gets an undefined name → `AddNewAptComponent` fires **0×**
(measured). The framework that should instantiate + nest the component hierarchy is not composing it. Every
engine primitive is faithful (AssociateInstToClass, Extends, GetNativeHashVirtual, `_name`, onLoad
dispatch); the gap is COMPOSITION, and every step below needs the build+boot+read-log loop.

1. **READ FIRST (per [[read-disasm-before-boot-tracing]]).** ✅ **Partly done offline (2026-07-07):** an AS-symbol
   grep of the bundles shows the BurnoutComponent FRAMEWORK AS is ENTIRELY in `MAIN.bundle` (`BuildName`×2,
   `RegisterComponent`×2, `IsBurnoutComponent`, `onLoad`, `registerClass`, `Initialize`×59, `prototype`×88) —
   `TITLE_SCREEN02.bundle` has ZERO AS-method strings (pure placements/art). And NEITHER bundle contains
   `attachMovie` / `createEmptyMovieClip` / `__proto__` / `Extends` strings, so the framework does NOT create
   the menu clips via attachMovie and does NOT set `__proto__` by name — component binding is registerClass
   (export-name → class) + AssociateInstToClass at placement, which the container can't use (no export name).
   ⇒ the OPEN question is HOW MAIN's framework AS makes the menu items' container a `BurnoutComponent` (it must,
   for `BuildName` to resolve) without an export name or attachMovie. **OFFLINE DISASM EXHAUSTED (2026-07-07):**
   ran `disasm_apt.py` over MAIN's 286 DF2 bodies (30k lines) — the framework uses DICT-based member access
   (`DictByteGetMember`, shows as `dict[N]`), and the dict is load-relocated so it's UNRESOLVABLE offline (0
   framework-method names resolved). So the composition can only be read via the RUNTIME opcode+dict trace
   (a boot) — the `BuildName` decode in [[title-flow-bringup-status]] (pm9-3) IS that trace's output. **NEXT (a
   dedicated boot session, single targeted trace per [[read-disasm-before-boot-tracing]] — NOT a loop):** gate
   `AptOpTraceProbe` + `AptDictFetchProbe` on the framework-init window (not just onLoad) and trace what runs
   BETWEEN registerClass and the menu items' onLoad — i.e. whether a MAIN frame-action composes the container as
   a component (and whether that action is dropped/straddled like the pm2 tag-1 bootstrap was, which WOULD then
   be a data fix), or whether it lives in the unloaded PERSISTENTAPT (Lead A). That single trace disambiguates
   data-fix-vs-VM-reconstruction and is the true unblock.
   **OFFLINE HYPOTHESIS SPACE NOW FULLY CLOSED (2026-07-07):** also ruled out the pm2-style dropped/straddled
   frame-action — `apt8_fix_frametables.py` on the active MAIN reports 0 repairs / no straddle warnings, and the
   active MAIN has the SAME 286 DF2 records as the intact `GUIAPT_MaybeBroken` copy (no framework function or
   frame-action was lost by the emitter). So NO data fix exists: §6.4 is unambiguously RUNTIME. Only two leads
   remain, both boot-loop: **(A)** the composition lives in the un-loaded `PERSISTENTAPT` (⇒ the fix is §4 import
   resolution + loading it), or **(B)** it IS in MAIN's intact framework but the runtime result doesn't nest the
   items under a component (⇒ a VM/composition reconstruction). The single targeted framework-init trace decides
   A vs B. Everything decidable offline is decided; the next move REQUIRES a boot.
   **⭐ CONCRETE BLOCKER IDENTIFIED (2026-07-07) — the framework composition is ALREADY WIRED:**
   `BrnAptRuntimeBringUp.cpp:EnsureFrameworkMovie()` loads the AS framework movie at display level 0 with
   `KB_LOAD_FRAMEWORK_MOVIE = true` — this IS the stage-B "compose the framework beneath the flow movie" path
   that would give the menu items a framework-level component ancestor. It loads **MAIN**, and its own FLAG
   (2026-07-05) says **MAIN's load AVs inside `LoadAnimation`'s `CompleteLoad/Resolve/Fixup`** — a char-record
   shape among MAIN's 89 chars the relocation walk has not met — handled gracefully (one-shot, logged, not
   retried), so the title boots but the framework never composes ⇒ no component ancestor ⇒ 0 registrations.
   Neither MAIN nor PERSISTENTAPT (present, 11.5 MB, NOT loaded) has a `SelectionMenu` CLASS string (both carry
   `BurnoutComponent`/`B5MenuItem`/`B5MenuToggle`), so the ancestor is the FRAMEWORK ROOT (stage-B), not a
   container class-bind. **⇒ the real §6.4 unblock is: (i) re-verify / fix the MAIN framework-movie Fixup AV (a
   bounded relocation-walk shape, §4-adjacent; many Fixup fixes have landed since 07-05) so `EnsureFrameworkMovie`
   composes MAIN at level 0; (ii) boot-verify the menu items then gain a component ancestor → BuildName resolves
   → registration.** This is FAR more bounded than "reconstruct the framework AS."
   **⭐⭐ BOOT LOG READ (2026-07-07, exe 03:06) — the AV is FIXED and the blocker is now a bounded FRAME-0
   COMPOSITION REGRESSION:** the framework movie MAIN now LOADS + INSTANTIATES at level 0 (`Fixup COMPLETED
   charCount=89`, `INSTANTIATED ... bound to root CIH @level 0`, `'MAIN' up loaded=1 instantiated=1`). BUT the
   log shows `frame0.cmdCount=90 (want 13)` and the framework ticks with **`childNodes=0`**, whereas the code
   comment (BrnAptRuntimeBringUp.cpp:2132/2143) records it was PROVEN at `frame0.cmdCount=13 → childNodes=7`.
   So MAIN's frame-0 PLACE-commands that composed its 7 framework children NO LONGER RUN (0 children) — the
   framework instantiates but is empty, so it provides no component ancestor. ⇒ **the §6.4 unblock is now a
   specific, bounded bug: MAIN's frame-0 command table reads 90 vs the expected 13 → 0 children placed. Fix
   the frame-0 command-count/placement regression (compare active `GUIAPT/MAIN.bundle` [236416 B, cmdCount 90]
   vs the `childNodes=7`-era bundle; likely a frame-table relocation or a wrong MAIN bundle revision) so the 7
   framework children compose → then the menu items nest under a framework component → BuildName resolves.**
   This is a concrete frame-table/data debug, NOT an AS reconstruction — the single most actionable §6.4 state
   reached. NEXT: dump the active MAIN frame-0 command list, find why cmdCount=90 not 13, restore the 7-child
   composition, re-boot, confirm `[AptRT] REGISTERED` fires.
   **⭐⭐⭐ ROOT CAUSE PINNED (2026-07-07, offline `dump_frames.py`):** MAIN's root frame-0 command array is
   CORRUPT — `cnt=90 = t5, t1(stream=0x32e8 **BAD**), + 88× t8` (garbage; no real frame has 88 identical
   tag-8s). The tag-1 bootstrap stream at chunk+0x32e8 reads BAD = the **pm2 straddled-tag-1 bug** (the emitter
   4-mod-8 misalignment → the stream ptr straddles to `0x2_00000000`), and it corrupts the rest of the frame-0
   command array so the ~11 PlaceObject commands for the 7 framework children are replaced by garbage t8s ⇒ 0
   children compose. BOTH `GUIAPT/MAIN.bundle` AND `GUIAPT_MaybeBroken/MAIN.bundle` show it (the pm2 swap
   regressed or the intact rev is elsewhere), and `apt8_fix_frametables.py` reports "0 repaired" (it does NOT
   detect/repair this frame-0 corruption). **⇒ §6.4 fix (bounded, DATA): obtain/repair a MAIN.bundle whose root
   frame-0 parses to the real ~13 commands with a VALID tag-1 @0x32e8 — check the pristine GUIAPT
   ([[guiapt-widening-pipeline]]: `Downloads/…907389d186ed/GUIAPT/MAIN.bundle`) first; if it too is straddled,
   extend `apt8_fix_frametables` to repair the frame-0 command-array (not just the frame-table offsets). Then
   the 7 framework children compose → the menu items nest under a framework component → BuildName resolves →
   registration → item 5 drives → item 6 delete shim → item 7 validate.** §6.4 is now a frame-table data
   repair, fully localized — no AS reconstruction needed.
   **REFINED (2026-07-07): it is NOT a bundle-swap fix — it's the frame-table RELOCATION producing 90 vs 13.**
   ALL FIVE MAIN.bundle revisions show the IDENTICAL raw frame-0 (`cnt=90 t5 t1(BAD) + 88× t8`): active,
   MaybeBroken, AND the three pristine JeBobs sets (`Downloads/burnout-paradise-{907389d186ed,7fda84314f0e,
   f794573e2e48}/GUIAPT/MAIN.bundle`). So no clean bundle exists to swap in — 90 is the raw count in every rev.
   Yet the runtime log says `STEP5 frame-table: relocated=YES frame0.cmdCount=90 (want 13)` and BringUp.cpp:2132
   records it was VERIFIED at 13 (→ childNodes=7). ⇒ the RELOCATION/processing that used to reduce the raw frame-0
   to the 13 real commands (filtering the t8 padding + fixing the straddled t1) now emits 90 → the ~11 PlaceObjects
   never run. **So the fix is in the frame-table relocation code/data pipeline, not a bundle swap:** compare the
   relocated frame-table `apt8_fix_frametables.py` appends (the STEP5 `mpFrames`) against the working-era output —
   the relocation is emitting the raw 90-entry array (with the t8 padding + BAD t1) instead of the repaired
   13-command array. Find why the frame-0 command-array repair regressed (the fixer's append/patch, or the runtime
   STEP5 read), restore cmdCount=13/childNodes=7, re-boot, confirm `[AptRT] REGISTERED`.
2. **One instrumented boot:** probe `AddNewAptComponent` (`[AptRT] REGISTERED <name>`) + `BuildName`'s walk
   (log each `_parent` + its `IsBurnoutComponent()` result). Read `build/game/BrnGame.log`: which node is the
   menu items' `_parent`, and why is it not a bound `BurnoutComponent`? (Target: REGISTERED count 0 → N.)
3. **Lead A — framework composition:** the bring-up loads MAIN at level 0 but NOT `PERSISTENTAPT`
   (BrnAptRuntimeBringUp.cpp:~1427; deliberate — PERSISTENTAPT imports MAIN and depends on the still-deferred
   §4 import resolution). Bringing PERSISTENTAPT up may supply the menu-framework component classes MAIN
   lacks → gives the items a component ancestor. This overlaps §4 (import-export resolution).
4. **Lead B — the nesting.** ✅ **RESOLVED OFFLINE (2026-07-07, no boot):** grep of
   `build/game/GUIAPT/TITLE_SCREEN02.bundle` — the export/import table is at bundle `0x170..0x2880`
   (`B5MenuItem` lives there @592/672/688: the imported, binding menu-item class), but `SelectionMenu_mc`
   (@0x43176/0x44408), `SelectionMenuAnimatorComponent` (@0x43128) and `MenuItem_0` (@0x43376) are all in
   the PLACEMENT/frame-command region as INSTANCE names — NOT export entries — and there is NO `SelectionMenu`
   (or `BurnoutComponent`) class string at all. So the container's char has no export name ⇒ no static class
   can bind to it (`AssociateInstToClass` needs the export name). **Option (a) "restore a lost linkage" is
   RULED OUT** — the console data has no linkage for it either. §6.4 is therefore definitively (b): the
   title's AS FRAMEWORK must CREATE the `SelectionMenu` component at runtime (attachMovie/`new` +
   registerClass) and nest `MenuItem_0/1` under it — so the reconstruction target is the frame-0
   init-action component-instantiation VM path (step 1), NOT a bundle/data fix. Re-verify offline with the
   export-table parser (apt8_fix_frametables format: chunk `Apt Data:1:7:8`, type-9 root `0x09876543`,
   exports stride-16 `{name-off, charId}`).
5. **Then the chain falls:** a bound-component ancestor → `BuildName` resolves → `SendAptEvent` →
   `AddNewAptComponent` registers → item 5's `UpdateAll` drives the real menu → item 6 (delete the
   `AptRuntimeSetComponentKeyValue`/`AptRuntimeSetComponentViewState` + `AddOutputAptViewState` shim,
   single-driver) → item 7 (byte-diff vs `Burnout_External_Xbox_One.exe`).
Reusable diagnostics live in [[title-flow-bringup-status]] (uncapped `AptRegisterClassProbe`, the
`<no-export:NAME>` probe, the offline bundle parsers). KB_CLASS_BINDING stays false until §6.4 lands.

## 7. Init / globals / GC leftovers

`AptStringPool.cpp` (1 apt_shim, `aptstringpool_initialize`), `AptValueGCPoolManager.cpp`
(2 apt_shim), `AptGC.cpp` (**1 apt_shim + 1 format_vocab** — the deferred-release drain),
`CgsAptAux.cpp` init config (**2 offset_hack + 4 format_vocab**).

---

## Priority order (dependency-first)

1. ✅ §6.1 DF2 argtab repair + §6.2 engine fixes + §6.3 clip-class instantiation/ctors/onLoad DONE.
2. **← CURRENT FRONTIER: §6.4** — onLoad runs but stops before `SendAptEvent`, so no component
   registers. Opcode-trace the onLoad handler past `KI_EVENT_ONLOAD` → fix → registration lands.
3. §6.5 per-frame `UpdateAll` drive → §6.6 delete shim + §6.7 validate vs Xbox i64 ←
   **the menu drives faithfully** (deletes `AptRuntimeSetComponentKeyValue`/ViewState).
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
