# Renderer registration: actual owner and earliest boundary

There is **no currently complete registration boundary** in the edca consumer or its current continuation `d3ec7d2dd65a37b489d1dbf61a53b9ce030385ee`. The original supported boundary is `BrnGameModule::Prepare` stage RENDERMODULE, after successful GameData Prepare has published the genuine member allocator list and before hardware-memory/thread startup. The recovered WIP supplies that five-argument body, but its GameData Construct/resource/global-allocator prerequisites remain incomplete. Calling its renderer stage directly today would reallocate existing native buffers, prepare sky geometry a second time, and finally dereference an unbound graphics allocator in MemoryUsage.

A smaller **PC platform integration remains possible**, but it must complete a real renderer preparation owner that reconciles existing allocations. A convenience registration call or a forced Prepare-stage value is insufficient. The concrete minimum and its remaining dependencies are in `MINIMAL_PC_INTEGRATION.md`. No integration source or activation is proposed in this analysis packet.

## Exact versions and positive runtime evidence

The packet freezes witnessed consumer `edca934dc502f71f64ad873cdd386afe5e3eeeb2`, current WIP `02c63ea7ed5dfb3b43dbaeb959a2d23f3861db6b`, and the original ARTIST functions independently. The corresponding shipping build owners are parent `1daa6ce58c9bebc56762deaf72385b2a55be476b` for the edca fixture and parent `749a1980ff01f762201c3836f61a0830104282f8` for the WIP. Current consumer d3ec is bound to parent `c154d46d2280f653246147405e550e02fea1edc2`. All32 inspected lifecycle-provider files, including the GameModule CPP, are byte-identical to edca. Root's six GUI posts are outside these inspected files. `CURRENT_CONSUMER_CONTINUITY.json` binds that distinction; it does not claim a native run of d3ec. WIP definitions must not be represented as active consumer code.

The existing edca execution binding records exe SHA256 `0c55f39a7a5c4295981996a9924e36350da026f50e1ceb5f665a7f82916c77bf`. Its retained BrnGame.log records:

| Existing log line | Observation | Supported implication |
|---|---|---|
| 27 | both root addresses below4GB | actual native GameData arenas were created |
| 246 | created24 of24: raw1, linear7, heap8, RW linear4, RW general4 | all four general rows passed their allocation-success branches and were installed by the native producer |
| 1022 | sky dome constructed + prepared | the current sky owner completed its preparation call before the failed lookup |
| 6401 | Component not found | no renderer component was discoverable at that point |
| 6403 | exception | the later whole-registry SAVE attempt was invalid; no control change or verification credit |

The fourth general row in the exact source map is bank31, `2D Immediate Heap`, size0x3FC000. The native producer installs its actual `s_aRWGeneralAllocators[3]` pointer in the **GameData-owned** list; this is not the separate renderer WorldDispatch allocator. The count plus the source branches is an inference supporting producer completion, not an address readback of the eventual renderer call argument. A later integration witness must still compare that argument with the real published member list.

No new run was performed. This analysis does not upgrade the invalid occlusion attempt, and its whole-registry SAVE must not be repeated. The existing original unnamed DLC feature slot remains unrelated to renderer registration.

## Current actual instance and lifetime chain

`BrnMain.cpp` owns one static `gGameModule`; `GetMainGameModule` and `GetMainGameDataModule` return that object and its real member. The game embeds `mRenderModule`, `mGameDataModule` and `mDebugManager` by value. In edca EnginePrepare starts the D3D9 device at285, then calls `gGameModule.Construct()` at293. Game Construct builds DebugManager at328, then renderer at405 and GameData at406. Comments claiming that the current renderer Construct precedes device creation are stale for this host path.

Renderer Construct builds all eight immediate buffers, dispatch frames and the actual `mDebugComponent.Construct(this)` at1416. Component construction only initializes the base/list state, renderer pointer and local brightness controls. It does not register. The actual GetName/Path are `RendererModule` / `Renderer`; the target lookup string is valid.

Original Register acquires the current DebugManager, inserts this same component pointer into the component list, and registers a UI callback carrying that pointer. OnActivate registers pointers to this same renderer's named fields. DebugManager was constructed with the process-wide GlobalDebug allocator wrapper; its UI/metadata pools and these embedded member addresses outlive individual GameData IO buffers and native frame transitions. No temporary list, stack component or guessed allocator is needed for registration. Reconstructing DebugManager would clear its list, and constructing the component again would reset its link; neither belongs in a frame-level registration retry.

## Original renderer completion is larger than a state transition

ARTIST82409C20 stages0..4 run base Prepare and the two empty blobby/corona transitions. A completed stage sets release START, then **every successful invocation, including entry at Done**, obtains bank31 and calls seven buffer Prepares, sky Prepare, DebugComponent::Register and MemoryUsage. Original registration is82409F64, after sky82409F58 and before MemoryUsage82409F6C.

Current `ImRenderBuffer<V>::Prepare` is not idempotent: it overwrites capacities, calls DoAllocate four times, overwrites bank pointers and rewinds both banks. It has no existing-prepared early return. Its `IsPreparedPC` is an existing typed check of both bank pointers plus write/dispatch pointers, and can support a genuine native resource-adoption owner. It is not a substitute for completing the other original preconditions.

| Resource | Native Construct ownership/budget | Original Prepare request |
|---|---|---|
| main2D | WorldDispatch;512KiB commands /512KiB vertices | bank31;110592 /393216 |
| debug2D | WorldDispatch;160KiB /2MiB | GlobalDebug;81920 /2MiB |
| assert2D | WorldDispatch; native modal buffer,160KiB /2MiB | separate PC addition |
| textured3D | WorldDispatch;1024 /32768 | bank31;same sizes |
| untextured3D | WorldDispatch;16384 /524288 | bank31;same sizes |
| debug3D | WorldDispatch;1MiB /1MiB | GlobalDebug;same sizes |
| race positions | WorldDispatch;128KiB /128KiB | bank31;same sizes |
| menus/HUD | WorldDispatch;512 /4 | bank31;same sizes |

The native WorldDispatch allocator is an actual static `rw::LinearResourceAllocator` adopting one operator-new block. Dispatch frames, the immediate banks and sky use that retained block. Re-running original Prepare would overwrite ownership, reduce the two native2D budgets and lose current bank contents. Merely setting renderer stage Done avoids none of this.

Sky is independently owned by `EnsureSkyDomeBringUp`: ready returns without work; tried-but-failed returns false; otherwise device/arena availability precedes program creation, actual sky Construct and Prepare. Its shader pair is embedded `gauSkyDomeVertexProgramPC` / `gauSkyDomePixelProgramPC`, so `shaders.bndl` is not a direct prerequisite for this pair. The original geometry method always allocates both dome meshes; it cannot be called again just because the outer state is Done. Existing world rendering later calls the same Ensure helper and must retain the same prepared object.

## Further concrete renderer prerequisites

1. The original new-module classification is absent in edca/d3ec; packet13 restores its genuine final Construct store in WIP02c. Renderer base Construct itself is also absent from the current native Construct body, while ARTIST's first operation calls it. The current first lifetime uses the static object's zero-initialized base stage. A complete native preparation owner should restore that genuine base initialization, rather than seed base stages or invent factories.
2. `MemoryUsage` is a real definition in `BrnRendererModule_wBT_01.cpp`, and dereferences `mpGraphicsAllocator` **before** the message-filter check. Both exact edca/d3ec and02c initialize that typed `BrnResource::LinearResourceAllocator*` to0 and never bind it in the actual Construct owner. The original allocator-wrapper initialization/binding is a missing prerequisite for using this unchanged tail.
3. The existing native `Allocators::GetGlobalGraphicsAllocator` returns an anonymous **rw** LinearResourceAllocator over a separate256KiB arena. That object is not a `BrnResource::LinearResourceAllocator` wrapper. Assigning/casting it into `mpGraphicsAllocator`, or assuming the pointer names the WorldDispatch arena, is invalid. Recover the genuine wrapper/global producer and typed binding, or separately review a PC memory-report leaf against the real retained native owner. No such cast, guessed global or silent MemoryUsage omission is proposed.

## Caller and thread order

The original outer Prepare stage3 consumes the four-argument GameData Prepare. On true, GameData publishes `&mAllocatorList` under the output write lock; the outer stage4 reads it under a read lock and calls renderer Prepare. Original ThreadLayout::Begin is later, at stage6. The original main loop supplies five stacks; the WIP body correctly requires them.

Active edca EnginePrepare only constructs. EngineUpdate calls BeginFramesPC once before entering frame updates. Native UpdateThread then drives the distinct `GamePrepare()` helper, whose first operation is the two-argument native GameData Prepare. Global bundles/acquires follow, and it calls PrepareAgain, not the original renderer Prepare. Native ThreadLayout begins serially and later switches to parallel only after MAIN+in-game. Calling the original five-argument owner from this already-running path would introduce another thread Begin and different resource/IO ownership.

The native GameData output does not publish its allocator-list pointer merely because the two-argument Prepare returned true. Publication is in GameData::Update. GamePrepare's pending tail requests that update; ResourceUpdateThread services it after the frame. A newly inserted wait before the tail that returns without requesting a pump can therefore wait forever on its own unpublished list. An explicit startup owner must either run the existing native Update on the actual pair before the first read, or schedule the existing request owner and wait without holding IO locks.

The native two-argument completion parks at stage7; original four-argument completion resets its stage to1. LoadingScriptedState case8 calls the native Prepare again. Changing that call to original Prepare, or driving both owners on one state word, can repeat original page registration and allocator/audio work. The bounded PC route must retain the two-argument path and its stage semantics until the full original caller conversion is reviewed.

## Corrected scope of an initially suspected IO hazard

Comparing edca's old members-only OutputBuffer Construct with WIP's recovered IO-base Construct initially suggested a lock-clobber regression. Reading the complete exact WIP caller resolves it: 02c GameData Update2772..80 already resets only a local FileSystemStatusInterface and copies it under the held lock; the scripted IO owner calls canonical Construct before any lock. Both repairs were already present at d458 and are frozen here at current02c. No additional correction is required for those call sites. Earlier immutable packets stay unchanged.

All work here is read-only source/assembly/log inspection plus private immutable evidence. There are no source checkout/Git/inventory changes, C++ builds/tests, CI calls, game input or activation. Counts remain50 verified /7 no-ops /1298 pending of1355.
