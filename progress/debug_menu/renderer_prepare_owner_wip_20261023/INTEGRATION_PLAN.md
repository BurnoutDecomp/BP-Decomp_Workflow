# PC integration boundary

The original owner is source recovered. **Do not activate it in the current playable host yet.** This plan separates a future integration from the frozen owner proposal.

## Actual existing allocator provenance

The current private GamePrepare obtains the shared GameData input/output pair from `GetScriptedLoadGameDataInput/Output`. It calls the two-argument `mGameDataModule.Prepare(0,0)` before its global-load state machine. That shortened Prepare drives CreateAllocators; the current CreateAllocators fills the GameData member `mAllocatorList` and maps RW-general bank 31 to the `2D Immediate Heap` row, whose current capacity is `0x3FC000`. No separate renderer list is needed or justified.

On later incomplete GamePrepare passes, the existing tail schedules/calls `GameDataModule::Update(sharedInput, sharedOutput)`. Update publishes **the address of that GameData member** with `SetAllocatorList(&mAllocatorList)` under the output write lock. `GetAllocatorList()` reads the pointer under a read-lock assertion. This establishes the actual source provenance of the host's list. It does not prove a successful runtime allocation: current CreateAllocators can log allocation failure and still report success.

The first source branch after two-argument Prepare succeeds can still see an unpublished/null output list: initial publication currently occurs in the later GamePrepare tail. Returning before that tail merely to wait for a list could deadlock this host. A future adapter must restore the original success-publication point or deliberately drive the existing producer without changing its resource ownership; it must not fabricate a list or reach into an unrelated allocator registry.

## Existing allocation owners

Current renderer Construct has already prepared the seven immediate buffers through `sWorldDispatchAllocator`, plus the native modal assert buffer and dispatch storage. ImRenderBuffer::Prepare allocates four banks and overwrites the stored pointers; it does not release earlier banks. Entering the original renderer Prepare afterward would replace live allocations and leak their previous ownership.

It would also change host capacities:

| Buffer | Existing native command bytes | Original Prepare command bytes |
| --- | ---: | ---: |
| Main 2D | 524288 | 110592 |
| Debug 2D | 163840 | 81920 |

The main 2D vertex capacity would change from 524288 to 393216. Other original 3D sizes currently agree, but agreement does not make a second allocation safe. The owner proposal does not edit renderer allocation policy or these capacities.

`EnsureSkyDomeBringUp` also owns the native sky-dome renderer Construct, program readiness, manager Construct, and both geometry meshes. It uses the same native dispatch allocator and `mbSkyDomeTried/Ready` latches. Original renderer Prepare unconditionally calls SkyDome Prepare, whose CreateGeometry replaces four buffer pointers. An integration must retain the already-owned meshes and program readiness or move the one initialization before use; it cannot prepare geometry twice and leave the latches inconsistent.

Renderer Construct currently initializes the two by-value blobby banks and internal/external indices. ARTIST renderer Prepare's blobby/corona cases contain only stage transitions. The outer Prepare omission does not explain or excuse any separate manager capacity/Construct defect.

## Two valid future integration scopes

The full original path requires the complete original GameData/resource dependencies, main-owned five-stack lifetime, persistent IO-pair handoff to all current consumers, and retirement of duplicated Construct/BeginFramesPC placement. Its success/failure status publication must precede the renderer allocator read exactly as the recovered owner requires. The XContent discovery backend remains a real dependency; an empty-success enumeration is not a substitute.

A bounded native adapter may instead reconcile the current preallocation owner explicitly. It must:

1. Operate on the actual game module and GameData-owned output list after its real readiness/publication point, before the first consumer that needs renderer completion.
2. Reuse the live native banks, host capacities, sky-dome geometry, and program state with concrete ownership/readiness evidence. A boolean that merely suppresses original allocation without establishing those resources is insufficient.
3. Enter the original renderer completion path and its registration at the original successful lifecycle point. It must not call Register directly or invent an alternate debug component.
4. Mark only the native ownership reconciliation with `FLAG PC-platform leaf`, retain the original retry/order semantics, and keep a per-module lifecycle state so it cannot re-enter original Prepare during driving.
5. Be a separate exact pre/post proposal and fresh review before Root composes, builds, or runs it.

## Duplicate current callers

Current GamePrepare calls two-argument GameData Prepare on every preparation pass. LoadingScriptedState's stage 8 actually prepares Replay, then still calls `GetMainGameDataModule()->Prepare(0,0)` before advancing. Its comments call the latter harmless because the shortened PC core parks at DONE 7.

ARTIST GameData Prepare's success tail resets its prepare stage to 1. Replacing the old two-argument body or forwarding those callers into the original four-argument core can therefore replay initialization. Both callers and their lifecycle roles must be reconciled when the original owner is activated. The integration must also avoid a second ThreadLayout Begin: the host currently starts it in BeginFramesPC and can restart it during overlap changes.

## Root-controlled completion evidence

After a fresh source review and composition, Root should compile/link the affected source set and use its normal attributable native harness. The distinguishing witnesses are one original owner completion, one renderer registration for the actual instance, unchanged native buffer capacities/ownership, the real GameData list and bank-31 pointer, and successful RendererModule component lookup before targeted alias/occlusion readbacks. A component lookup alone does not certify renderer behavior or the pending debug sites. The current playable b330 executable remains the control until Root deliberately stages a reviewed successor.
