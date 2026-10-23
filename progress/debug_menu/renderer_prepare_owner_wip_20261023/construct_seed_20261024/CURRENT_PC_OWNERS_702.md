# Concrete initialization and PC ownership at source702

This is a source-bound integration plan, not a runtime readiness result. All paths below refer to exact WIP source702d242bd0e99a8510ef09bbc42b0a316956ac9b. The physical b330 executable remains the control; this packet neither stages nor activates anything.

## Actual GameData Construct order

Primary82671B90 first constructs ModuleSingleBuffered, resets its owned stage/counter/event-slot state and binds both receiver queues. It then calls, in order:

1. mAudioStreamAllocator.Construct.
2. Original ConstructResourceModule8266D570.
3. mAttribSysModule.Construct at61698.
4. mGameTalk.Construct(false) at61908.
5. mDebugGameTalkInterface.Construct(&mGameTalk) at65940.
6. mLiveUpdateModule.Construct(&mGameTalk) at58500, through its real Construct slot.
7. VehicleList, WheelList, HUD-message controller and ChallengeList Construct.
8. The remaining allocator-map/texture/debug/DLC stores and constructors.

The exact native Construct differs. It constructs AttribSys and the list controllers before its retained native Resource allocation block, and never constructs the three newly recovered GameTalk/interface/LiveUpdate members. Thus adding those calls beside its early AttribSys call would still violate original resource-before-AttribSys ordering. Recovering a complete original Construct must retain its actual dependency chain; selecting it in the native path is a separate integration.

Original ConstructResourceModule includes the genuine type-construction/registration producer and texture callback, not the current singleton registry bridge. Prior recovery packets that left those as explicit traps are evidence of an unresolved dependency, not complete provider code to reuse. Original audio buffer creation also belongs there after LinearMalloc::Construct; the native CreateAllocators later resets its audio allocator. Mixing those lifetimes can erase the adopted audio buffer.

## Current native allocations and list publication

Native GameData Construct still owns160MiB main and224MiB graphics roots through the existing low-address allocator. Its strings remain GameDataRoot0/GameDataRoot1, but actual option writes are maResourceSets[0] and[2]. Both native and original category ids are now0/2; the older initial-plan0/1 description is superseded. Host budgets and block sizing still differ from original and must be preserved until reviewed.

The actual allocator list is the embedded GameData mAllocatorList. Native two-argument Prepare drives its native allocation helpers; Update publishes the address through the real shared output under the output write lock. An initial successful native Prepare can precede that later publication. Waiting before the producer tail merely because the list pointer is null can prevent the publication itself. The integration must establish the actual producer/readiness point, not create another list or read an unrelated registry.

## Existing renderer owner

EnsureWorldDispatchAllocator owns one rw::LinearResourceAllocator over its retained operator-new block. Renderer Construct prepares the seven original immediate buffers plus the native modal-assert buffer and dispatch storage through that actual allocator. Its capacity expression also reserves the current sky-dome/corona/header/matrix needs.

| Buffer | Native command bytes | Original Prepare command bytes | Native vertex bytes | Original vertex bytes |
|---|---:|---:|---:|---:|
| Main2D | 524288 | 110592 | 524288 | 393216 |
| Debug2D | 163840 | 81920 | 2097152 | 2097152 |

Original Prepare would allocate into those same objects through the actual GameData bank31/debug allocators. Their existing Prepare operations replace stored allocations. The restored new-module classification does not reconcile those owners, free old banks, preserve capacity or prove either allocator ready. Do not call original Prepare over these live buffers merely because that classification is now correct.

EnsureSkyDomeBringUp owns native program construction and the main/environment geometry via mbSkyDomeTried/Ready. It uses the same native allocator. Original SkyDome Prepare would create geometry again. Integration must preserve the actual program and mesh ownership or move its one initialization before use; a skip flag without ownership evidence is insufficient.

GamePrepare's repeated native Prepare calls, LoadingScriptedState stage8's extra GameData Prepare after Replay, and BeginFramesPC's existing ThreadLayout Begin/restart remain concrete duplicate-lifecycle hazards. Original GameData success resets its main Prepare stage to1; LiveUpdate's own completed Prepare resets update state too. Neither method is a safe per-frame readiness probe.

## Game legacy factories

The actual game vtable has the six template hooks, including creators returning owned input/output storage. Current ModuleSingleBufferedTemplate already has separate typed member buffers; it does not alias the base DataBuffers. Current BrnGameModule derives the direct base instead, and its IO header misattributes the destroy-input template hook827E3100 as an InputBuffer method. A faithful typed-template/base correction is needed, with the actual output request-interface member and original constructor flag lifetime. No numeric offset cast or fabricated ready buffer is acceptable.

Root should review each source packet, resolve original constructor/provider/mount boundaries, then separately review an explicitly marked PC ownership reconciliation. Required native witnesses remain one owner completion, actual GameData list/bank provenance, one renderer registration for the actual object, unchanged retained native capacities/ownership and targeted debug alias behavior. No source flag or component lookup alone supplies those witnesses.
