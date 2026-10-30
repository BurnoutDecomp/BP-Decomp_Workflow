# Combined Replay frame and provider source review

Read-only fresh review. Return `VERDICT: pass` or `VERDICT: fail`, with concrete
findings and exact source locations. Do not edit files, run the game, change
ledger/status, publish refs, or spawn another reviewer.

Review the sixteen exact proposed files in `SOURCE_MANIFEST.json` and the
`combined_source.patch`. Their before objects are immutable b5-decomp source24
`f1d1a5ebce785cfe2dc5315b2b3292d95983e6b8`; the manifest binds every after file.
The manifest explicitly distinguishes thirteen frame/Replay/Sound/World files
from three Resource dependency imports. All changes remain in private overlays.

The original frame discrepancy is recorded at:
`../swarm_replays_debug_controls_01_08_recovery_20261029/frame_bridge_followon_20261029/REVIEWER_PACKET.md`
and `DOWNSTREAM_BRIDGE_GAPS.md`. That packet is immutable. Its seal manifest is
`510cc77121a818d54c650ab1353745b7ce3fc33f83693aed60a011aedfcaa064`.

## Frame integration to review

`postimage/b5-decomp/src/GameSource/Game/BrnGameModule.cpp` and `.hpp` restore the
selected PC host route, whose console `DoUpdate` entry remains an explicitly
identified host scheduling leaf. The existing native phase bodies are called
with their original typed IO participants. Check all of the following against
the raw assembly, independently of the source contract checker:

1. Initial FSM update set is used by Network PreSim, GameState PreWorld and
   Replay PreSim. Replay PreSim is between GameState PreWorld and GUI PreWorld.
2. GUI PreWorld and Sound PreUpdate precede the late `ConstructUpdateSet`.
   This late result includes the produced Replay status and is retained through
   World, Director, GUI, Effects, Sound, Replay PostSim, PostWorld and Network.
   The World flow-state adapter reads that captured set from the frame owner.
3. Replay PreSim reaches World, Effects, Sound and GUI through their actual typed
   status/queue accessors. Read locks select const getter overloads. The old
   Effects empty-audio-queue fallback and optional source skips are removed from
   the selected full frame helpers now that their producers are supplied.
4. PostSim merges World, Effects, Sound, Director and GUI requests; its output
   reaches GameState PostWorld after Sound. The manual Effects-only
   `StoreSerialisers` bypass is removed.
5. Sound RootOutput and both standalone Replay phase outputs remain live through
   PostSim, PostWorld, Network, timers and the Sound/Replay resource tail. The
   same frame owner frees outputs in reverse order for catch-up substeps and
   the final render boundary. Zero-substep frames do not destroy absent outputs.
6. Resource debug input is published immediately before DebugManagerRender; the
   separate Resource provider below supplies the actual RenderDebug body.

The host retains the pre-existing static GUI/Director/World output ownership
needed by rendering. Its conditional output order is Network, Sound Root,
Replay PreSim, Replay PostSim, Effects, Sound PreUpdate; teardown reverses it.
The original standalone Replay buffers are not the aggregate ReplayIO_Buffer.

Raw ARTIST authorities in `evidence/ARTIST/`:

- `0x823F0AF8.json` and `DoUpdate.asm.txt`: full original frame allocation,
  initial/late set production, calls, resources and teardown.
- `0x823DD2A0.json`, `0x823DD408.json`: Replay phase wrappers.
- `0x823E8BD0.json`, `0x823DD0A8.json`, `0x823DCEC0.json`: World, Effects, Sound.
- `0x823F0758.json`, `0x823E7210.json`, `0x823E92A8.json`: GUI, Replay-to-GUI,
  GameState PostWorld.

Declaration shape is in canonical read-only
`references/DecFIGS/dwarfdump/GameSource/Game/BrnGameModule.h` and
`BrnGameModuleUpdateFunctions.cpp`. ARTIST assembly wins for register/stack
arguments, update-set lifetime, pointer identity and behavior.

## Provider leaves in the same batch

- `replay_io_leaf/`: the two exact Replay IO postimages, original constructor/
  factory/getter evidence and controls. Verify PostSim standalone allocation
  size1556 from ARTIST823AE5D0 and queue Construct82653010; the outer aggregate
  owns the separate four-byte gap so its PreSim getter still reaches+0x61C.
  Check the new const PreSim resource-request getter at823BB128, including its
  read-lock contract. The shared IOBuffer-only Destruct must remain exact.
- `sound_root_leaf/SOUND_REVIEW_PACKET.md`: six postimages recovering the
  persistent channel9 SoundSerialiser, Construct8264C9F8, owner initialization
  in SoundLogic Construct826C9330, original Update827029D0 replay/readiness/
  registration branches, action218 mirror, and canonical typed status copy.
  The original skipModuleSerialise1 constant is deliberate. Review its actual
  source, raw ARTIST files, and all branch/queue behavior, not just its fixture.
- `../swarm_replays_frame_bridge_recovery_revision02_20261029/`: three postimages
  for active InGame/stage8 World consumers and original Prop request transfer.
  Check GUI-to-World before Replay status, no duplicate Sound PreUpdate, captured
  late set at both full World call sites, and actual const Prop queue append.
- `../swarm_resource_texture_provider_20261029/REVIEW_PACKET.md`: three imported
  Resource source files supplying TextureRenderCallback and RenderDebug. Check
  the required common GameModule call in this composition. Its provider source
  has independent production compile and CPU writer/negative-control evidence;
  it is part of this fresh combined source review to avoid relying on an
  inherited-context reviewer as independent approval.

## Verification already performed

- `gates/GameModule_attempt03_resource_exact/RESULT.json`: actual whole
  GameModule TU with canonical shipping flags, immutable source24 include tree,
  named overlay headers first and all private source hashes stable during
  compilation. This is the current final header revision.
- `CONTRACT_RECEIPT.json`: source24 baseline plus six mutation controls rejected;
  selected source call/dataflow and reverse lifetime contract passes. This
  structural source check is not a runtime witness.
- `AUDIT_RECEIPT.json`: exact before/after evidence audit of five native bridge
  wrappers has no new high-signal findings. Existing partial-name warnings
  (`GetStatu`, `GetReplayR`, etc.) are truncated IDA names; queue/posting enum
  and IOHelper assertion bodies are outside that narrow source index.
- The new frame source has zero faithfulness-lint hits. Provider manifests and
  gate/fixture receipts are in their own packets.
- Sound leaf: four actual TU gates pass, real canonical provider26/26 and
  extracted exact Update protocol1488/1488; six semantic mutation controls fail.
- World leaf: before and after actual TU gates pass for all three source paths.
- Replay IO leaf: actual TU and both typed factory uses compile; real
  Construct/queue/locking witness passes and type/lock/constructor controls fail.

## Explicit open original behavior

This batch does not assert that recording, playback, the eight Replay controls,
all Sound playback, or any menu site is operational. Root owns native delivery
and the overall debug behavior goal; no gameplay, screen/pixel or audible
runtime witness has run for this batch.

Separate original recovery is still required for Replay state-entry/open-file/
serialise-job producer paths; RaceCar/Traffic serialiser producers and their
World transfer; Sound traffic/skid/in-air/collision/deformation replay consumers.
The exact Sound list is in its packet. The callback request-byte scan remains
scoped source evidence; it does not authorize inventing consumers. These open
modules are not replaced by fake buffers, empty channel interfaces, invented
recording backends, or added null guards in this batch.

Review the sixteen-file change for correctness in its bounded scope and report
any concrete prerequisite that prevents the selected frame route from being
safe or faithful. Do not certify the complete Replay feature from compile or
CPU fixture results.
