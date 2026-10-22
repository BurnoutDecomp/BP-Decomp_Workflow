# Combined independent source review — exact five-path batch

VERDICT: fail

Increment 1 — gui_validation_cast_and_satnav_colour_repairs_20261023 — VERDICT: pass

Increment 2 — world_collision_completion_source_delta01_20261023 — VERDICT: fail

These verdicts apply to the frozen source increments against B5 `840d83b3c3390d1786ed571b3bf87e3947b89a9e`. There is one remaining source-parity defect, F1. Four individual changed paths pass this source-increment review; the exact proposed `GameBridgeWorldToGui.cpp` does not. No compilation, linking, active wiring, runtime or behaviour approval is given.

## F1 — P2: preserve the collision publisher's explicit input-pointer assertion

Location: `world_collision_completion_source_delta01_20261023/postimage/src/GameSource/Game/GameBridgeWorldToGui.cpp:773–774`.

The new tail calls `lpGuiInputBuffer->GetGuiEvents()->AddEvent(...)` directly. ARTIST `BridgeWorldToGui` calls the specialised GUI 493 publisher at `823EDE08`. That publisher saves its GUI input argument from r5 into r28 (`823DA23C`), tests it for null (`823DA244–248`), and on null executes BeginAssert / FireAssert / EndAssert (`823DA24C–2C0`) with **"Input hasn't been locked for write"**, before calling the write queue getter (`823DA2C8`). The proposal retains the getter and queue write but drops this diagnostic branch and its side effects.

`GetGuiEvents()` does not replace this check: exact-base `CgsGuiModuleIO.cpp:45–48` tests `IsBufferLockedForWriting()` on the buffer itself and returns the named queue. The earlier traffic sub-bridge has a different non-gating `lpGuiInput` assertion; it does not preserve the publisher's later, specific null-input diagnostic if execution continues after an ignored assertion. This finding concerns the original failure contract, not a claimed normal-input gameplay failure.

Required repair: preserve the explicit null-pointer assertion immediately before this queue access, or use the inherited pointer overload, e.g. `mGuiModule.AddGuiEvent(&lEvent, lpGuiInputBuffer)`. Exact-base `CgsGuiModule_AddGuiEvent_Inst.cpp:38–46` retains the assertion and posts the complete `sizeof(T)` payload; its line 147 explicitly instantiates GUI 493. `BrnGui::GuiModule` publicly inherits `CgsGui::GuiModule` and adds no hiding `AddGuiEvent` declaration. The reference overload's 12-byte header subtraction is a separate overload and must not be used for this flat event.

The null assertion must be restored without adding a return or changing the original non-gating flow. Leave this packet and its retained evidence unchanged; review any repair as a new exact increment.

## Checks that passed

**Increment 1, typed resource responses.** The complete diff changes only `static_cast` to `reinterpret_cast` at `BrnGuiModule.cpp:2163` and `2196`. The queue returns an opaque `CgsModule::Event*` to copied payload bytes. Both resource responses instead derive from `CgsResource::Events::Event` through `PoolEvent`; these are unrelated C++ bases. The repaired cast preserves the payload address without pretending there is an inheritance conversion. It introduces no raw member-offset access, layout change, size change, branch or store.

The surrounding six-state car-pool machine, reply-type checks (7 / 8), traffic-pool selector 15, queue clear order, invalidate result retry, three-argument `SetCarPoolValid`, and validate-to-fill fallthrough are unchanged. The exact queue `Clear()` only resets its bookkeeping and does not erase the retained response storage. ARTIST `8251445C–470` passes this / false / resource / descriptor in r3–r6 to `SetCarPoolValid`; `824EAF78–AFD0` consumes those registers, sets the valid/invalid state and copies both resource records. DecFIGS confirms the bool plus two const-reference parameters. The retained C2660 arity diagnostic is downstream of the invalid cast; reducing the method's argument list would be wrong.

**Increment 1, SatNav colour.** ARTIST `824F7FD8` is `lis r8,-1`, producing `0xFFFF0000`. At `8281C990`, the scalar DrawFrame entry saves r8 as the colour, then supplies it through r4 to each of four DrawBox calls. f1–f4 contain the rectangle coordinates and f5 the border. The existing C++ overload takes four f32 coordinates, a u32 colour and f32 border. Replacing only `0xFFFFFFFFu` with `0xFFFF0000u` and correcting the false uninitialised-register comment is supported. Toggle gating, rectangle coordinates, virtual scaling and border are unchanged. No claim is made about the resulting displayed colour, frame placement, alpha convention or safe-area parity.

**Increment 2, status-to-completion branch.** After the unchanged VehicleData → RouteInformation → TrafficAndPropData → ImpactInformation calls, the proposal retains the exact sequential short-circuit loads in ARTIST `823EDD98–EDDE4`: first invalid byte; if nonzero, invalidating byte; if zero, invalid byte again; if zero, validating byte. The first accepted arm posts VALIDATED (3), including the original invalidating → VALIDATED condition. The second accepted arm posts INVALIDATED (2); the last unsuccessful condition returns. Repeated getter calls are retained rather than collapsing the reads. The status member names and const getter shapes agree with DecFIGS and the five named bools in the bound dependency. ARTIST `823B6548` confirms the const output-buffer status getter's read-lock assertion and member access.

**Increment 2, event payload and ownership.** The original `823DA2CC–2D8` posts id 493 with size 4. The moved class is token-identical after comments/whitespace are excluded: one enum member, the original five enum constants 0–4 and `GetEventType() == 493`. The new size assertion pins four bytes. There is exactly one definition across the combined overlaid headers. The original aggregate now includes the named owner, retaining old include users. `GameBridgeWorldToGui.cpp` already includes that owner. DecFIGS names the owner and enum/member shape; its historical `GuiEvent<483>` base/id does not override the X360's flat four-byte payload and id 493.

The direct queue call has the correct address, id and size; F1 is its lost assertion. Existing typed output and input consumers keep the same event identity. A read-only quoted-include inspection resolved 78 base files and 86 proposal files, added eight header dependencies, found no new include recursion and no additional same-name class/struct definition conflict within those resolved closures after removing the old event definition. This is source inspection, not a substitute for the hosted compiler. No C++ compiler, preprocessor, fixture or linking check was executed.

## Exact bindings and limits

Both packet manifests cover all 17 files in their respective frozen payloads, with no missing, extra or mismatching files. All five preimages match their exact Git blobs at the stated base byte-for-byte. All five frozen unified diffs match the complete pre/post differences. The six supplied dependency snapshots also match that exact base. All seven supplied ARTIST JSONs match the original `.ida-exports/BURNOUT_X360_ARTIST.XEX` files byte-for-byte. `INPUTS.json` records the full raw SHA-256 and byte length for every packet file, original evidence file, consulted DecFIGS file, additional exact-base dependency and quoted-include input; `CHECKS.json` records the verification results and Git blob identities.

Packet 1 integrity-manifest SHA-256: `42ceffff79643c8d2563bef8a05242fa18e6e7c541cfbfd3dba08d96bef9e95b`.

Packet 2 integrity-manifest SHA-256: `325412ccbc16b49594e74a831380883e93cc94905d84eb7b8f42d0ef12629017`.

| B5 source path | Base bytes | Exact base SHA-256 | Post bytes | Exact reviewed postimage SHA-256 | Source disposition |
| --- | ---: | --- | ---: | --- | --- |
| src/GameSource/Gui/BrnGuiModule.cpp | 284816 | `1ef0d714afef53e9d478faeac33fac43f656c999885c07f21df7a007707dc2ca` | 284826 | `0466a386fc98cf672c85b62aa5589b986a7cd2af311931c075013f3de89ff5e0` | pass for this source increment |
| src/GameSource/Gui/BrnGuiSatNavDebugComponent.cpp | 15676 | `f161a3d874e9185ea517fc737b3fbe79a39f94f721fd992a0de51ee4b2ef8e0c` | 15708 | `b40b11913e4c8b214aab61ea9648a21721a665a2d7d8b3a50c3231ac89d8ab8a` | pass for this source increment |
| src/GameSource/Gui/BrnGuiDemangledEventTypes.h | 98124 | `2908bf4f6d55bdaf95bfec0b12d02021b982c9ae795d4261a3a12a15e8afe4ae` | 97636 | `ff1cf6023db573b5cb63ed47753c490240755ff70f42c373f3312dbec7ccb7c3` | pass for this source increment |
| src/GameSource/Gui/BrnGuiEventTypeDefs.h | 189219 | `5ce6c86484e7ff07793d4690d0fabd16d3e143ae431ff0048502f0633b315a7e` | 189964 | `597605770de1b809644be80dd3018024e7ff8ffbb2d45d585162c270a81c7e49` | pass for this source increment |
| src/GameSource/Game/GameBridgeWorldToGui.cpp | 62196 | `d7b5c3a1f9d9029f341c6d9c5b75fdb301d995e825380d0444ffdd3f158ac342` | 63189 | `3930dd05c94f914ce252797417d76efd7458604f9c17d519da5ae9e06fde76ea` | fail (F1) |

The earlier hosted build remains **FAIL**: retained run 39870493775 requested the exact 840d83b base, records `validated: false`, `exit_code: 1` and no outputs. Its log identifies the two unrelated-base casts; this source repair does not retroactively change the result. No new build was started, and no retained fixture result is repurposed as validation of these proposals.

The original white-outline native visibility evidence and its prior sealed review remain unchanged. SatNav site 0006 remains withheld from final campaign/parity credit pending native checking of the repaired colour and outstanding visual parity. No native image was newly captured or credited by this review.

This collision completion tail is a source prerequisite. It does not establish a complete collision-world validation round trip, active GUI PreWorld/late-update wiring, replay activation, resource-policy correctness, asynchronous completion or removal of PC profile stand-ins. The unchanged bodies and legacy accommodations in these large source files are not newly certified as complete original behaviour.

Only a new sibling review directory was written. No build, game, Stage/Run/harness/watchdog, fixture, CI, IDA, source/index mutation, commit or subagent was used. Packet files, production source, original failed runs and earlier reports were left unchanged. `INTEGRITY.sha256` seals REPORT.md, INPUTS.json and CHECKS.json; `SEAL.sha256` holds the detached SHA-256 of that integrity manifest.
