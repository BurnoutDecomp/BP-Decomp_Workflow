# World to Director bridge and serialiser follow-on

Review the nine-file LF patch in `combined_source.patch` and the exact postimages named in `SOURCE_MANIFEST.json`. Base is published private b5 commit `f32c7d531d98c811a89f69a6f868fdc10b74716a`; workflow companion is `5a73986a22c5a4f5f3f242dfec678688e75bad13`. This packet supersedes the unfinished `world_director_bridge_followon` seven-file overlay, adding only original Director stack argument types and the requested score/combo IO surface. It does not change common GameModule.cpp or BrnGameModule.hpp.

Recovered behavior:

* BridgeWorldToDirector locks its persistent channel before the active-player check, captures live frames in modes 0/1/2/3, acknowledges real World streaming completion in modes 4/7, and republishes recorded vehicle/crash/boost/centre-of-mass data in modes 5/6. Debug-controller focus and unlock form the common tail, including the no-player branch.
* The five-byte WorldEntity StatusInterface now occupies original Director input +0x6AB0. IsAllStreamed reads its fifth byte, +0x6AB4. The live World bridge copies this entire interface. Preparing/playback acknowledgement reads the World output directly, matching the binary; it does not overwrite retained Director world status on those branches.
* DirectorBridgeSerialiser uses typed VehicleInfo, PlayerCrashInfo, CarScoreData, combo, boost and transforms. Its ten spans retain the original stream order and sizes; the action queue uses the original per-event serialisation afterwards. Frame size remains 24,320 bytes and the channel allocation remains 32,768 bytes.
* DirectorModule's first two arguments to PreSceneQueryUpdate/Update/PostGuiUpdate are IOBufferStack pointers, matching DecFIGS. ARTIST consumes the subsequent buffers in r6/r7/r8/r9 and ignores the two stack-pointer parameters in r4/r5. Existing integer return declarations/bodies are preserved in this bounded parameter correction.
* Director input CarScoreData +0x3110 and combo byte +0x3258 replace existing opaque storage without changing later offsets. The four named getter/setter declarations are the original DWARF surface. The common integrator owns the GameState bridge that uses them.

The concrete World producer already exists at the pinned source base. `InternalBaseStreamer::IsStreamComplete` matches every nonzero target by resource id and the full user id, then requires READY status. `WorldEntityModule::PostPhysicsUpdate` writes that result into StatusInterface byte 4, and WorldModule forwards the status interface from its postphysics output into the World update output. No new ready flag or substitute producer was introduced. See `ASSEMBLY_POSTMORTEM.md` and the retained original evidence.

Validation:

* Five full production translation units pass canonical shipping /c gates: DirectorModule, Director input, World bridge, bridge serialiser, World update output. Opened-header provenance and immutable source24 snapshot checks are in `immutable_gates/*/RESULT.json`. The complete 38-file Git delta overlay supplies published V3 changes over that snapshot; `PUBLISHED_BASE_OVERLAY.json` binds those bytes. No mutable shipping source include root is permitted.
* Exact LF patch check and application reproduce all nine postimages byte for byte. `PATCH_CHECK.json` records this. Apply with `git -c core.autocrlf=false apply` to preserve those bytes.
* `FixturePositive04`: 41 checks, zero failures, zero original assertions. It executes the complete production bridge serialiser TU, original BaseSerialiser/queue/IOBuffer bodies, exact input setter/getter bodies and the original streaming predicate/search. It uses real frame and input layouts. Only the assert sink and inert logging globals are fixture adapters; private visibility is opened for test setup. Supporting CarScoreData, RaceCarState, string and StrStream bodies are frozen production bodies.
* Four behavioral mutations all compile and fail at execution: omit boost transfer (9 failed checks), omit queue transfer (9), copy only four status bytes (1), force completion through missing/loading/user-id mismatches (3). `CONTROLS_RESULTS.json` distinguishes compiler and executable exits. All have zero opened-header drift.
* Faithfulness scan records preimage and postimage findings in `FAITHFULNESS_RECEIPT.json`; shared baseline was not changed.

Limits: the fixture does not execute the full GameModule World bridge, WorldEntity postphysics body, common frame scheduler, full shipping link or native replay. It proves the bounded serialiser/status/predicate behavior and detects the named regressions. Common frame lifetime and startup construction changes belong to the separate common packet. Earlier sealed Director/ReplayDirector bodies were reused without repeating their completed behavior audits.

Please return an explicit `VERDICT: pass` or `VERDICT: fail` for this nine-file leaf packet.
