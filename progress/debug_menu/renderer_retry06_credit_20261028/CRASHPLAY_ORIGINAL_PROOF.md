# Original-leftover disposition review — 15 sites

One site is **PROVED_ORIGINAL_INERT** in ARTIST; fourteen remain **PENDING** at specific reachable original bodies or virtual targets. No canonical disposition/count was changed. “Inert” means editing its registered storage has no engine effect; the original control and its ordinary UI read/write behavior remain present. This is static original/source evidence, with zero native credit.

Source pin: B5 `d1585cfbb9a99db4ee6aa8c6b2848f399cc01ad2`. `INVENTORY_ROWS.json` selects each ID directly from `progress/debug_menu/entries.json`; the source spelling `mfBoostExhaustCutOffSpeed` corresponds to the inventory's decompiler spelling `mfExhaustCutOffSpeed`. Its canonical ID is **SetupBoostMenu#0004**, not an OnActivate row. `DISPOSITIONS.json` contains the exact IDs, captions, storage, defaults, and per-site next edge. No ID is counted twice across the overlapping input packets.

| Exact canonical site | Storage | Disposition / bounded closure |
|---|---|---|
| `BrnEffects::EffectsDebugComponent::OnActivate#0015` | `mbGlassEnabled`, +0x14, true | PENDING — E below |
| `BrnEffects::EffectsDebugComponent::OnActivate#0016` | `mbPopcornEnabled`, +0x15, true | PENDING — E |
| `BrnEffects::EffectsDebugComponent::OnActivate#0019` | `mbEngineCrashEffectsEnabled`, +0x1A, false | PENDING — E |
| `BrnEffects::EffectsDebugComponent::OnActivate#0020` | `mbSparksDebugEnabled`, +0x1B, false | PENDING — E |
| `BrnEffects::EffectsDebugComponent::OnActivate#0022` | `mbForceFinishLineRendering`, +0x20, false | PENDING — E |
| `BrnEffects::EffectsDebugComponent::OnActivate#0023` | `mbForceNonPlayerEffects`, +0x22, false | PENDING — E |
| `BrnEffects::EffectsDebugComponent::SetupBoostMenu#0004` | `mfBoostExhaustCutOffSpeed`, +0x38, 20.0 | PENDING — E |
| `BrnWorld::CrashPlayDebugComponent::OnActivate#0001` | `mbDisplayCrashBreaker`, +0x10, false | **PROVED_ORIGINAL_INERT** — C |
| `BrnWorld::WorldDebugComponent::OnActivate#0007` | WorldModule +0x5E1B18, false | PENDING — W |
| `BrnWorld::WorldDebugComponent::OnActivate#0008` | WorldModule +0x5E1B14, 32 | PENDING — W |
| `CgsSceneManager::TriangleCollisionDebugComponent::OnActivate#0013` | `miNumListsSearched`, +0x144, no retained constructor store | PENDING — T |
| `CgsSceneManager::SceneManagerDebugComponent::OnActivate#0011` | `mbDrawNonCachedTriangles`, +0x56, false | PENDING — S |
| `CgsSceneManager::SceneManagerDebugComponent::OnActivate#0012` | `mbDrawNonCachedSpheres`, +0x57, false | PENDING — S |
| `BrnAI::ResetOnTrackDebugComponent::OnActivate#0008` | `mbUseHardcodedResetPosition`, +0x85D, false | PENDING — R |
| `BrnAI::ResetOnTrackDebugComponent::OnActivate#0009` | `mbIncrementResetSpeed`, +0x85E, false | PENDING — R |

## C — complete CrashPlay closure

This conclusion is stronger than the preceding direct-offset scan:

1. **Exact object and initialization.** RaceCarEntityModule embeds CrashPlayManager at +0x180F0 and its debug component at manager+0. In `RaceCarEntityModule::Construct`, `0x822FDA24` forms that owner, `0x822FDAF8` stores the self/manager pointer at component+0x0C, and `0x822FDAFC` stores false at +0x10. `OnActivate @0x822A8208` passes precisely `this+0x10` to `sub_8282D800` with “Display crashbreaker.” The following three registrations address separate manager +0x138/+0x14E/+0x14F cells; they do not alias the display byte.
2. **All engine entrypoints terminate without it.** The complete raw ARTIST `Update @0x822A81B0`, `RenderHUD @0x822A8168`, and `RenderWorld @0x822C3470` bodies only test manager+0x0C, emit the existing null assertion if needed, and return. There is no drawing call, flag load, forwarded component pointer, or side effect controlled by +0x10. `GetName @0x822A81F8` and `GetPath @0x82312480` return literals. These are all six named component methods including registration. The DecFIGS-only `DrawCrashBreaker` declaration is not reachable from any of those actual original entrypoints.
3. **Enclosing owner cannot consume it indirectly.** All sixteen original CrashPlayManager bodies are retained and enumerated in `CRASHPLAY_OWNER_CLOSURE.json`. The manager is nonvirtual apart from its embedded component. Its only whole-owner dynamic dispatch is `Update @0x82306530`, `0x823068CC..0x823068DC`: manager+0's component vptr, slot zero, with the same manager/component address. This reaches the assertion-only component Update. The other calls pass the owner to inspected manager methods, pass disjoint ring buffers/vectors (+0x20, +0x30, +0xC4), or pass separate cars, IO queues and event payloads. None publishes the display-byte address. The superficially relevant `OnEnterRoad` loads at +0x10 use `r30=r4`, the road-action object, whereas its manager is `r31=r3`; they are not reads of this byte.
4. **Enclosing module address formation is closed.** The complete named RaceCarEntityModule scope is retained. The +0x180F0/-0x7F10 materializations are constructor/destructor, Prepare registration, manager Activate/Update/event calls, and accesses to the manager's separate gameplay members in PostSceneUpdate, ProcessPlayerVehicleInput, HandleStopModeAction and UpdateCrashingPlayerContacts. They neither load component+0x10 nor pass that byte to another system. `ADDRESS_SCREENING.json` retains the materialization instructions; full original bodies, rather than the token list, determine the pointer roles.
5. **Escapes are only the known debug UI/manager.** Prepare `0x82304050..54` registers the embedded component. `DebugComponent::Register` and DebugManager registration retain it in the debug list and invoke normal virtual lifecycle hooks. `DebugManager::Update/RenderWorld/RenderHUD` access base list/active fields and dispatch the three entrypoints above. `FindComponentByName @0x82822400` has four original callers: DeactivateComponent, `sub_82832200`, ExecuteScriptComponent, and ScriptCommand_ActivateComponent. The retained bodies only activate/deactivate the component through base state; none interprets subclass storage. The bool adapter uses Variant tag 8 and the supplied cell pointer; VariableManager initializes its change-callback storage to null. CrashPlay OnActivate installs no change callback or function for the display cell. Thus menu editing preserves the cell but has no path into a drawing engine.

Current `BrnCrashPlayDebugComponent.cpp` preserves the original false default, live registration and all three assertion-only callbacks. The field is private, has no accessor, and the complete current source identifier search finds only its declaration/default/registration. No source fix is required for this site. The lack of a recovered `DrawCrashBreaker` body is not grounds to add one: the original reachable callbacks do not call it.

## E — actual Effects escape, unresolved virtual slot

The prior 77-export packets correctly resolve the direct owner readers and nearest glass/crash/spark/finish-line/boost bodies. They do not close every helper virtual target. `UpdateActiveRaceCars @0x8229DB30` computes component+0x2C330 at `0x8229DEDC..E4` and stores it into the stack helper at +0x10 (`0x8229DFC0`). The helper reaches `EffectsStateMachine::Tick @0x82280468`; that method passes it through determine/change/tick virtual calls. The Boost targets are exported and do not read the seven cells under review.

For the Jump path, `HandleJumpAndLandingEffects @0x82288068`, `0x8228807C..84`, loads helper+4 (ActiveRaceCarData), selects +0x100 and calls that same base Tick. `EffectsModule` C++ ctor `@0x827E35E0` stores `off_820CEBEC` at each ActiveRaceCarData+0x100 and `off_820CEBFC` at +0x13C, which the Boost Tick path selects. This dataflow plus DecFIGS shape supports the Jump/Boost roles despite the unrelated ICF destructor name used by an adjacent vector iterator.

**Exact next edge for all seven IDs:** read the Jump table's +8 cell at **0x820CEBF4**, resolve its function and inspect that original body. The current Jump OnTick is empty and comments call it an ICF-folded empty slot; no table bytes or original target body in the retained packet proves that statement. Since that dispatch receives a helper carrying the debug-component pointer, this is a real bounded capability to read the seven cells, not an arbitrary demand to disprove every possible function in the image. The other inspected original readers remain correct, including the fixed 13.4112 exhaust speed threshold; no debug-field substitution is justified.

## W — World render escape remains open

The two module offsets, defaults, exact menu pointers and unused per-frame dump gap in `WorldModule::Update @0x827D63E8` are established. `WorldModule::WorldModule @0x827E5998` installs `off_820CE69C` at the embedded WorldDebugComponent, module+0x5E1B30. `DebugManager::RenderWorld @0x8282E030` invokes component vtable+4. **Read 0x820CE6A0 and inspect that WorldDebugComponent::RenderWorld target**; no standalone named original body exists in the 30,084 retained exports. Its receiver has `mpWorldModule` at +0x0C and can reach either target field. The current RenderWorld/DrawTarget source only draws the vehicle cannon, but current source cannot prove what the missing original callback did. The closed update path and absence of a dumper call do not close that separate path.

## T — TriangleCollision has reachable missing bodies

Registration @0x828AAA68 exposes +0x144 as a read-only s32; the map-owned result count at +0x64 is different storage. The current constructor and retained original constructor do not establish an initial assignment to +0x144.

Two actual incoming edges prevent an original-unused conclusion: **RenderWorld @0x828CAE88 -> BuildSpacialMap @0x828AAD50**, and **DrawPolySoups @0x828C09D8 -> DrawPolySoupPoly @0x828B3B98**. Both callees lack standalone original exports and receive the component; inspect their stores and pointer forwarding for +0x144. The DecFIGS-only DrawSpacialMapQuery/DoSpacialMapQuery/TestPolySoupLineCollision declarations are not themselves evidence of a live path and are not used as blockers here. No count producer should be invented from a nearby counter or this menu caption.

## S — SceneManager's named-method scan omits two live callees

The two defaults/registration addresses +0x56/+0x57 are exact, and RenderWorld @0x828D04E8 directly tests only +0x54/+0x55/+0x10/+0x11. However it **calls DrawTriangleTest @0x828C2E70 with the component**, and DrawPrimitives @0x828CB9A0 **calls DebugRenderCollisionVolume @0x828ABB28 with the component**. Neither target has a standalone export. These are the exact remaining bodies to inspect; “all named component exports have no loads” does not cover them. Current recovered bodies omit the noncached flags, which must be preserved pending their original bodies, not augmented based on captions.

## R — ResetOnTrack has an open render target and history writer

Construct @0x82791A48 and OnActivate @0x82790E00 establish the two false-default cells +0x85D/+0x85E. Update @0x827867E8 uses the distinct continuous-reset and skip cells +0x85C/+0x860. The menu adds no change callbacks for these two flags.

`AIModule::AIModule @0x827E3780` installs **off_820CF9B4** at ResetOnTrackManager+0x540 (`0x827E387C`); resolve **0x820CF9B8**, the RenderWorld slot reached by DebugManager's render dispatch. That original callback is not in the retained named exports. Independently, **ProcessResetOnTrackRequest @0x82799D38 -> PushResetInfo @0x82778B30** passes the component pointer to a missing original history-writer body. Inspect these two actual edges before declaring the cells unused. Current RenderWorld and PushResetInfo source do not reference the two flags, but that is source evidence only.

## Pins and limits

`evidence/ARTIST/` retains the inspected owner/framework exports; `OWNER_SCOPE.json` and `EXPORT_INDEX.json` pin scope and all 30,084 export identities/hashes. `MISSING_REACHABLE_BODIES.json` records the exact missing direct-call targets. `source/`, `SOURCE_PINS.json`, and `SOURCE_IDENTIFIER_REFERENCES.json` retain current-source evidence. The previous twelve packets were read without edits; their reports are navigation/context, not independent proof of their conclusions. An IDA session check returned zero sessions; no database was opened or changed, and prior failed-open receipts were not retried.

No source/build/game/ref/status/count changes, no native run, no fabricated reader, and no arbitrary whole-program-negative requirement. `SEAL.json` hashes every local review artifact except itself; `REPORT.sha256` pins this report.
