# ReplayDirector, Sound collision and float provider review

Perform one combined read-only review of `SOURCE_MANIFEST.json`'s fifteen
changed source paths and the single workflow mount. Return explicit
`VERDICT: pass` or `VERDICT: fail` with concrete findings. Do not edit, publish,
run the game, alter site/ledger state or spawn another reviewer.

Source base is the reviewed/pushed private checkpoint
`8d9a61cff337e01c39b1576c2c44e1f783ea7a2a`; workflow base is
`fb46504ff0145fbeb0be53997b4a346cfc7624ab`. The earlier two source manifests and
seals remain unchanged. `preimage/src/`, `postimage/src/` and
`combined_source.patch` bind the exact continuation. Six imported Director
provider files are byte-identical to the previous approved checkpoint and are
listed as unchanged, rather than counted again as changes.

## Typed ReplayDirector and active callers

Read `../director_runtime_v2/REVIEWER_PACKET.md`, SOURCE_MANIFEST.json,
ASSEMBLY_POSTMORTEM.md, evidence and controls. That sealed full fifteen-file
provider supersedes its earlier eight-file version; this composition carries
only its nine changes relative to the approved provider checkpoint.

The real ReplayDirector owner replaces the old padding/camera aliases. Its
three original methods are recovered, and DirectorModule invokes them through
the original replay/live branches. The field interpretation resolves earlier
decimal-versus-hex comments: final Camera at+0x430, selection at+0x29D0 and
first-frame at+0x29D4 belong to ReplayDirector. Named owners expose all recorded
camera/parameter/timer/vehicle/random/shared-info state. Input's original
all-streamed byte and two generated camera schemas have typed accessors.
External camera behavior's original clear and replay-store at+0xB61 now have
named storage, with the inferred name explicitly distinguished from evidence.

Independently verify the complete original constructor/member ownership,
FillInSharedInfo, PreSceneQueryUpdate, Update, camera-space and policy query /
results order, first-frame seeding/suppression, recorded/live camera selection,
cycle-after-select, previous flag roll and output publication. Inspect actual
ARTIST assembly; do not rely on source banners or the old shared-source
postmortem excerpt as the proposed implementation.

The exact Update-body fixture reports27 checks and eight failing behavioral
mutations with explicit adapters/spies; it does not execute the complete
owner, PreSceneQueryUpdate or FillInSharedInfo. The serialiser's previous51
real-provider checks and five mutations still bind byte-identical files.

## Sound collision, scrape and deformation replay

Read `../sound_collision_followon/SOUND_COLLISION_PACKET.md` and its exact raw
ARTIST/method evidence, manifest/seal and source-bound fixture receipts. Five
paths replace opaque collision/scrape spans with canonical OutputCollision[8],
ScrapeInfo[4] and Vector3[4], retaining their observed anchors and sizes.
Typed AddCollision/AddScrape feed those same members.

The consumer chain restores recorded traffic lookup, collision and scrape
capture/playback, original fatal START-to-ON handling and terminating-output
count, output-count assertion before sort, and deformation's recorded mfA24
target rather than its smoothed cache. Check actual control flow and captured
records, including explicit original missing-record branches and live/replay
selection. No whole-output reset or substituted live record is introduced.
The semantic positives report370 collision and41 deformation checks; eleven
compiled mutation controls fail. Full live audible parity remains untested.

## Base float stream methods

Read `../base_float_provider_followon/BASE_FLOAT_PACKET.md`, both raw ARTIST
functions, the one-file patch and actual-method fixture. Existing declarations
had no bodies. ReadFloat82650130 and WriteFloat8264FEE8 restore original aligned
cursor IO, byte count including padding, assertion order and mode behavior.

Check the non-obvious assembly details independently: capacity uses
miBufferSize for ReadFloat, comparisons are unsigned, assertions continue,
post-assert loads/cursor differences retain their original order, and only
exact recording mode2 commits while modes1/3 validate and return0. Stream
pointer arithmetic addresses an external byte buffer, not fabricated class
members. Real-method tests report6757 checks; eight semantic mutations fail.

## Source32-safe validation and mounts

The managed shipping checkout has legitimately advanced to a different source
checkpoint. Further gates never assume its HEAD is f1. Parent
`F1_DEPENDENCY_SNAPSHOT.json` points to6970 exact raw f1 Git blobs for src and
tracked vendor; GIT_OBJECTS.json hashes every file. `../immutable_gate.py`
uses that source tree and canonicalc9 flags, excludes mutable shipping src,
and checks every opened repository header's Git blob/vendor Gitlink identity.
External compiler/SDK/package headers are separately content-pinned.

Composed immutable actual-TU receipts are in `../immutable_gates/`:
v3_GameModule, v3_ReplayDirector, v3_DirectorModule, v3_ExternalBehavior,
v3_SoundCollision, v3_SoundSerialiser and v3_Deformation. Each passes with zero
repository-header drift. Basefloat's final immutable gate also passes. The
prior Sound collision dependency audit checked258 captured f1 headers with
zero drift, preserving its unchanged component gate evidence.

`workflow_source_mount.patch` adds only BrnReplayDirector.cpp; the Director
serialiser and three Sound TUs were already mounted by the predecessors. Check
direct provider closure rather than assuming compilation establishes a link.

Root owns whole private shipping link/native delivery. This review grants no
gameplay, recording/playback, pixels/audio or menu-site/count credit. Original
Replay state/open/job producers are not invented: a separate raw-IDB scan
found no attested ARTIST entry/setup counterpart to the PS3-only methods.
RaceCar/Traffic typed producer/codec/render recovery remains separately owned.
