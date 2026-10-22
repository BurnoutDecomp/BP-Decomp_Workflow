# Replay bridge constructor and assertion repair review

VERDICT: pass

This one combined independent **delta review** accepts the exact three repaired postimages in `reviewed_packet/`. The repair resolves **both prior blockers**, F1/P1 (PostSim construction) and F2/P2 (wrapper pointer assertions), from the retained b9ec full review. No new defect was found in this delta. The earlier `b9ec871d56cf0ffe3c5d39f975cc414132d3c659` full **FAIL** report remains unchanged and remains the verdict for that unrepaired checkpoint.

The review is based on the exact pre/postimages, all six attached ARTIST pseudocode/assembly records, both DecFIGS declaration records, and the bound helper/type source. Author conclusions were checked against those artifacts; this report supplies the independent verdict. No production edit, compilation, build, fixture, test, CI, native game, input, IDA, or further subagent operation was performed.

## P1 — resolved: PostSim construction

[BrnReplayModuleIO.h:169](reviewed_packet/postimage/b5-decomp/src/GameSource/Replays/BrnReplayModuleIO.h:169) declares the canonical `InputBuffer_PostSim::Construct`. [BrnReplayModuleIO.cpp:177](reviewed_packet/postimage/b5-decomp/src/GameSource/Replays/BrnReplayModuleIO.cpp:177) defines it in the existing IO owner.

The order matches ARTIST `0x82652FE0`: `IOBuffer::Construct()` first clears the status flags and sets the constructed bit; then exactly eleven named `mRequestInterface.mapSerialisers` pointer slots become null; then `mGuiEventQueue.Construct()` initializes the named 4096-byte GUI queue. `KI_MAX_SERIALISERS` is 11 in the bound canonical interface, matching `li r10,0xB` and the eleven-store ARTIST loop. The older DecFIGS five-pointer declaration does not override that X360 count. The existing GUI wrapper's 4096 constructor forwards to `VariableEventQueue<4096,16>::Construct`.

The caller is also attested: ARTIST `CreateIOBuffer<InputBuffer_PostSim> @0x823AFD20` calls this constructor after successful allocation at `0x823AFDD4`. The current generic template statically invokes `(*lpOutBuffer)->Construct()`, so the new declaration/body replaces the inherited base-only call which caused F1. Default initialization and stack reuse no longer leave these PostSim request slots and queue metadata stale. Null pointer stores use native pointer width. The delta introduces no offset cast, bulk byte-span clearing, fallback, zero-fill dependency, or destructor work; existing destruction is preserved.

## P2 — resolved: all sixteen boundary assertions

Every added block is an explicit null check followed by BeginAssert/FireAssert/EndAssert. None returns, skips, or conditionally encloses its subsequent lock operation. Every `FireAssert` passes the exact original literal P4 path and its original line. `CHECKS.json` records each of the sixteen conditions, labels, paths, line numbers, source locations, and comparison with the attached ARTIST record.

| Boundary | Postimage assertion start | Original assertion labels, in order | Original lines | Helper operation order retained |
| --- | --- | --- | --- | --- |
| PreSim lock | .cpp:1547 | lpInputBuffer, lpOutputBuffer0 | 259, 260 | Replay write, GameState read |
| PreSim unlock | .cpp:1569 | lpInputBuffer, lpOutputBuffer0 | 272, 273 | GameState read unlock, Replay write unlock |
| PostSim lock | .cpp:1622 | lpInputBuffer, lpOutputBuffer0, lpOutputBuffer1, lpOutputBuffer2, lpOutputBuffer3, lpOutputBuffer4 | 403–408 | Replay write, then world/effects/sound/director/GUI reads |
| PostSim unlock | .cpp:1692 | lpInputBuffer, lpOutputBuffer0, lpOutputBuffer1, lpOutputBuffer2, lpOutputBuffer3, lpOutputBuffer4 | 428–433 | GUI/director/sound/effects/world read unlocks, then Replay write unlock |

The PostSim label mapping is destination=Replay input, source0=world, source1=effects, source2=sound, source3=director, source4=GUI. Assertion order remains forward even before the reverse unlock operations, as in `sub_823B7760`. All assertions at each boundary occur before any lock/unlock in its helper. The literal path is `d:\p4\b5_main\burnout\main\code\gameshared\gameclasses\module\CgsModuleUtils.h`. The four original helper addresses are `0x823B6FE0`, `0x823B7060`, `0x823B7620`, and `0x823B7760`.

## Exact scope and bindings

The complete source delta is only the PostSim Construct declaration/body, its heading comment, and the four added assertion sequences in the two frame wrappers. Recomputing the unified diff directly from all three complete pre/postimages reproduces `PATCH.diff` exactly. It changes no shared `CgsModuleUtils.h` template, unrelated caller, ReplayModule virtual body, GameMain wiring, destructor, or build source selection.

All three preimages are byte-identical at both `b9ec871d56cf0ffe3c5d39f975cc414132d3c659` and private checkpoint `20c1d8723951d70a349604c8a7a2ceec7cb28569`. Their only intervening repository change is the separate FileSystem.cpp addition, which is outside this review. The normal checkout was clean at `91a0ed564f9c9e3dec915bfb416c0467650084ef`. This review accepts proposed file contents and does not claim that they were applied or committed.

| Exact postimage | Git blob computed from reviewed bytes | SHA-256 |
| --- | --- | --- |
| src/GameSource/Replays/BrnReplayModuleIO.h | 68610261e5316f279cb7239dd31b0b298ad0bb0d | 8cff2f2e0fac7bcd050006b6380eafbe2325e66e45e4349818804993f84153fe |
| src/GameSource/Replays/BrnReplayModuleIO.cpp | 94b74d5c4836d61f5fc0bcac4a606284df09e891 | ba865d5f3a8b03ba6f997a5aa7a20c4e9d34ae56633e6a992cd1bcedb475bc16 |
| src/GameSource/Game/BrnGameModule.cpp | f2d73de31159f56c0f2ea498b96ce73d6eb2f73d | 4b0d29208323919933f7638cc82734b378df6f798d5eae83efefc7adb15a1d6b |

All packet manifest hashes, preimage Git blobs, evidence hashes, and document hashes match. `BINDINGS.json` binds the two source checkpoints, all three exact pre/postimages, every copied input, the supporting Git source objects, and the unchanged prior failed-review seal. `INTEGRITY.sha256` covers this report, CHECKS.json, BINDINGS.json, and every frozen snapshot. `SEAL.json` records the integrity inventory hash and report/bindings hashes without circular self-hashing.

## Acceptance boundary

**F1 and F2 are resolved in these exact postimages.** This pass does not replace the old checkpoint's FAIL record, re-review the separate ReplayModule full recovery/assertion repair, or review the intervening FileSystem change. PreSim/PostSim remain uncalled by active GameMain, and this repair changes no active frame integration. Start/open policy, serialise-job production, concrete build/link source closure, dispatch/runtime validation, and overall Replay operation receive no new acceptance or runtime credit here.
