# Independent source-only review: Replay PostSim consumer prerequisite

VERDICT: pass

I found no blocking defect in this three-file source prerequisite. The change recovers the typed PostSim game-event queue accessor and adds the guarded consumer to GameState PostWorld. It remains dormant in c1 GameMain and provides no active replay playback or recording.

The packet maps the exact preimages to c1 commit c1b0e7ef6a181c3cc92f45ac9481a9cbaaeb01db, parent 20c1d8723951d70a349604c8a7a2ceec7cb28569. I verified all changed preimage blobs and the two audit-only preimages against the c1 tree and Git object IDs; the manifest's copied preimage/postimage byte counts and SHA-256 hashes also match. I verified all packet and ARTIST/DecFIGS evidence hashes.

| Changed c1 source | c1 blob | Preimage SHA-256 | Postimage SHA-256 |
|---|---|---|---|
| src/GameSource/Replays/BrnReplayModuleIO.h | 68610261e5316f279cb7239dd31b0b298ad0bb0d | 8cff2f2e0fac7bcd050006b6380eafbe2325e66e45e4349818804993f84153fe | d9b594cbfa8b88f035a94ed91eb32372c2a11a7972dc002011cf20ca311c8bfa |
| src/GameSource/Replays/BrnReplayModuleIO.cpp | 94b74d5c4836d61f5fc0bcac4a606284df09e891 | ba865d5f3a8b03ba6f997a5aa7a20c4e9d34ae56633e6a992cd1bcedb475bc16 | 250f886c0feef423971f1d063588a5352e649e4e2dadbe17f5a761e04da3c3ea |
| src/GameSource/Game/BrnGameModule.cpp | f2d73de31159f56c0f2ea498b96ce73d6eb2f73d | 4b0d29208323919933f7638cc82734b378df6f798d5eae83efefc7adb15a1d6b | 2bd06339b1d539f03f55ca82aa296ac5b6f715bfad2ae2af99dc081a9fd0391d |

DecFIGS declares OutputBuffer_PostSim::GetGameEventQueue() const as returning const GameEventQueue*. The ARTIST body at 0x823BB478 checks the IOBuffer read-lock bit and returns this+4. ARTIST xrefs that shared body from DoUpdate_GameStatePostWorld at 0x823E93D0; its assembly then appends the returned queue into the PostWorld input queue. The added C++ method matches the typed DecFIGS shape, checks IsBufferLockedForReading(), and returns the embedded queue.

The new PostWorld append is inside the existing PostWorld-input write-lock and optional PostSim-output read-lock bracket. It follows BridgeWorldToGameState and runs before the remaining PostWorld work; the non-null guard prevents calling the accessor without a supplied Replay output. This matches the bounded consumer seat. ARTIST orders director event 43 before the Replay append and controller event 10 after it; both producers remain absent in c1. When event 43 is recovered, it must remain before this append. This packet does not implement either event producer.

The active c1 GameMain caller still passes null for the PostSim output, does not create Replay PreSim/PostSim buffers, and does not call DoUpdate_ReplaysPreSim or DoUpdate_ReplaysPostSim. The added queue append therefore does not execute through the current active caller. The ARTIST per-frame sequence also includes Replay PreSim before GUI PreWorld and a later ConstructUpdateSet before World; the current c1 path still lacks the active GUI PreWorld call and the closed late update set. DoUpdate_GuiPreWorld exists as a helper but is not called in the shown GameMain path. The included ARTIST PreWorld and GUI validation exports remain recovery evidence, not proof that the c1 producer is reconstructed.

The Replay PreSim status interface is still not staged into the World input, and the Replay PreSim GameDataRequestInterface has no active c1 consumer in this increment. Keep that resource-request path separate. The packet leaves these blockers explicit and does not claim complete Replay output payload wiring.

The ARTIST frame order places Replay PostSim after Effects/Sound and before GameState PostWorld, then Network PostSim. This patch does not alter that caller order or add Replay dispatch. No C++ build, CI, harness, fixture, native game, or IDA operation was run. No production source was edited; this is source review only, with no runtime or behavior credit.

An integration note (non-blocking for this bounded prerequisite): the source comment identifies the append as the seat after director event 43, but c1 has no event 43 implementation. Keep any future event 43 append before this block to preserve the ARTIST order.

REVIEWED_INPUTS.json records the source, evidence, and manifest bindings and is SHA-256 626340bef5a9c67f3c3854fde8cea37d1e31d692eeeecfd0591bc2175cfba680. INTEGRITY.sha256 hashes this report and the reviewed-input inventory; its detached SHA-256 seal is stored in INTEGRITY.sha256.sha256.
