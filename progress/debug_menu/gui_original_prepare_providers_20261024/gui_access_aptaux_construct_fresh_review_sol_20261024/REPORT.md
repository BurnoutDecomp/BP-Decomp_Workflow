# Fresh source review: common Construct Aux binding

VERDICT: pass

CANONICAL_SOURCE_VERDICT: pass

SOURCE_COMPOSITION_VERDICT: pass

COMMON_CONSTRUCT_CHANGES_WHEN_COMPOSED: true

ORIGINAL_PREPARE_UPDATE_ACTIVATION: not_approved

The one typed pointer store passes this bounded source review. It restores the target's binding to the actual contained Aux after the common Construct has constructed its View/Aux owner. No source defect was found. This change will execute in the selected common Construct when composed; it is not an entirely dormant new entry. It establishes an object identity, without establishing APT preparation or runtime readiness.

## Exact binding

| Input | Identity |
| --- | --- |
| Source base | `36ae3ffed6e8fb3ea89ca91947647aa9465c8658` |
| Prepare overlay author seal | `1bd837d613dc24e6fed9d51fd14d88a4e3de3e6ce16f3c37c221850cdc04674f` |
| Independent Prepare review seal | `8a0bd0890b05a154a091e20e59a6174485bfa4d2c4b723c0dbffb8d22b4f1f90` |
| New author seal SHA256 | `16714abbdf362cd764d92e60cbd30a1b6a293257d1420ab3b3673fcc0302edde` |
| New manifest SHA256 | `b6bba91de38a6c4e1d48cadf0eac1bb1022903037deaf95f96e8ac670d158410` |
| New author bindings SHA256 | `fc31ddbf73359c6d98fa31485c342e7eb07de1f84cb66ff1afd840122e39cfba` |
| Patch SHA256 | `91cdba37c38a3c4e4373bc3153ae9307f57140ae66c5e0ce7330ffc62258d5e4` |
| Full module preimage SHA256 | `654c9880c4be21a8cc977e3644c490c20bcdefca6c6bfee355daa0dc6455da72` |
| Full module postimage SHA256 | `e08112c074a8fcf85f1d1a5461342b4a3b28490804549e3e1d182ffd2abac2fb` |
| Module postimage Git blob | `83d116ccfd63a2b2046937330c5647dd231ce32a` |
| Hypothetical final composed tree | `9292eaf03f741790150782d2f8a0b6e80ce4d953` |

The preimage is byte-identical to the just-reviewed complete-Prepare postimage. The resulting tree includes that overlay's unchanged header and Sku getter, plus this module postimage. Tree hashing was performed in reviewer memory from read-only Git tree bytes; no Git objects, refs, index or checkout were written. [BINDINGS.json](BINDINGS.json) contains the exact final three path blobs and all 42 captured inputs.

## Primary store and declaration shape

ARTIST `BrnGui::GuiModule::Construct` forms the access bundle at module+`0xF5714` (`82518C50/58`) and the pointed-to owner at module+`3*65536-0x1B70` (`82518C54/5C`). It clears all eight pointer fields at `82518C70..98`, then writes that owner's address to the first field at `82518C9C`. The proposed store follows `mGuiAccessPointers.Construct()` immediately, before the existing language/FLAPT/cache bindings, at postimage `BrnGuiModule.cpp:1075`.

This address is the actual contained View/Aux identity, not an offset-based host projection:

- The original View seat is module+`2*65536+0x480` =132224 (`82518490/9C`). The original caller constructs it before the access-bundle stores and passes it to shared GUI Construct at `825184DC/E4`.
- Shared View Construct forms its contained Aux at View+`65536-0x1FF0` =57360 (`82860610/2C`) and calls its actual Construct at `82860658`.
- 132224+57360=189584, exactly the address stored by `82518C9C`.
- The existing shared View header's public `GetAptAux()` returns `&mAptAux` at lines188–191; `mAptAux` is a by-value member at245. The derived Brn View publicly inherits that View and declares no shadow Aux/getter.
- Existing `GuiAccessPointers::mpAptAux` is `CgsGui::AptAux*` in the current header41 and DecFIGS `CgsGuiShared.h:125` (retained dump15/173). The getter returns that exact pointer type. No declaration, vtable, data field, cast or layout adjustment is added.

Console offsets identify the target owners only. The host assignment uses the real C++ getter and naturally sized pointer; no Apt record/pointer-layout or serialized-data change is proposed.

## Actual initialization, callers and lifetime

The current common Construct reaches `mViewModule.Construct(...)` at module source896 before the new store1075. Derived `BrnGuiViewModule.cpp:62,67` forwards to the actual shared View Construct. The shared body at `CgsGuiViewModule.cpp:98,117` constructs its own Aux; the C++ View constructor also owns that same by-value member. Exact36ae `CgsAptAux.cpp:114,140,144,151` constructs its render handler, publishes `this` as the existing singleton and installs the callback table. ARTIST `8285FFF0/82860198` independently confirms that singleton points to the same Aux receiver.

The object therefore exists and its current explicit Construct call has returned before the new pointer is published into the bundle. It is a borrowed pointer into the module's contained View, not a stack record, new allocation, second singleton or replacement owner. The actual GameModule contains its GUI module by value (`BrnGameModule.hpp:1115`) and directly calls this common Construct (`BrnGameModule.cpp:448`). The common Construct changes when Root composes this source, even while the new original Prepare/Update entries remain unselected.

Object identity is distinct from readiness. Existing Aux Construct explicitly leaves its target pointer null; the same provider still contains deferred data-handler work. The new store neither prepares a target nor closes that broader engine work. The current PC `PrepareAptRuntime()` obtains `s_pViewModule->GetAptAux()` and checks equality with the singleton at module source695–696; it does not create another Aux there. The later PC Prepare assignment to the singleton at postimage1521 remains intact. Its explanatory comment is now stale but introduces no code change; under the existing one-Aux ownership contract the late assignment names the same contained object.

The new assignment has no dereference, preparation call, registration or cleanup action. Existing teardown bodies are byte-identical; shared View Destruct clears the singleton (`CgsGuiViewModule.cpp:237,241`). This patch adds no permission to use the bundle after its owner's logical teardown or outside the containing module's lifetime, and does not claim teardown/callback safety beyond the existing contract.

## Preservation and acceptance limits

Stripping comments/whitespace and removing the one new assignment reproduces every preimage code token. All bytes outside the common Construct function are identical. In particular the complete original Prepare, old no-argument Prepare, zero/two-argument Update, PC runtime helper, destructor, late reassignment and callers are byte-identical. The delta contains only the new store and its adjacent explanation. No field, allocation, readiness flag, new Prepare call, mount or original registration is added.

This closes the specific missing common-Construct Aux identity binding identified in the prior Prepare review. It does not activate the original Prepare/Update lifecycle or approve replacing the current PC entry. The remaining campaign still requires genuine GameData/GameTalk initialization, the target's ten-argument Update including its replay byte, caller-owned IO stacks/locks/retries, the real borrowed GUI output/callback lifetime and exactly-once migration of current manual consumers. Earlier packets, maps, verdicts and their exclusions remain retained. This packet's ten-argument description agrees with the prior review's primary ABI correction.

Compilation, linking, initialization success, resource readiness, control/registration behavior, raw big-endian PC schema, native/gameplay, online, Xenos and delivery acceptance are outside this verdict. In particular no runtime result from the unchanged delivered36ae executable is attributed to this proposal.

## Method

[STATIC_CHECKS.json](STATIC_CHECKS.json) contains 89 reviewer-owned static checks, all passing: the 18-file manifest/seal, copied and original primary exports, exact36ae source providers, exact Prepare overlay/review binding, full-body preservation, pointer type/containment, clear/store order, owner arithmetic, current caller and existing PC runtime behavior. The retained 42 inputs also include the full provider/header bodies used above.

Only reviewer-owned read/hash/text/tree calculations ran. No author script, imported fixture/provider, compiler, build/test, CI, game/input or IDB action ran. No source, Git state, earlier packet/report, normal build/configuration/profile/log or ledger was modified. A read of a nonexistent optional POSTMORTEM file was discarded; the report, patch and direct evidence supplied the review. Root remains the sole integration/publication/launch owner.
