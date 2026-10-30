# Common replay scheduling and GameState bridge

Read-only contribution to the single combined batch review. Return findings to
Root; do not edit, publish, run the game, change ledger/site state or spawn a
reviewer. Inspect the exact two private files in SOURCE_MANIFEST.json and the
common_source.patch against the copied raw ARTIST evidence, plus the original
frame assembly in ../evidence/ARTIST/DoUpdate.asm.txt. FROZEN_SOURCE_SEAL.json
binds source, patch and raw function evidence. This is an additive continuation
of private b5 f32c7d531d98c811a89f69a6f868fdc10b74716a and workflow
5a73986a22c5a4f5f3f242dfec678688e75bad13. The published prefix is retained.

The Director dependency is ../world_director_resume_20261029. It owns the real
DirectorIO score/combo fields and typed accessors, five-byte World status,
DirectorBridgeSerialiser provider and IOBufferStack parameter declarations.
Those files are outside this two-file delta and belong in the same review.

Verify the original frame-owned Director input: ARTIST823F0C5C allocates one
typed input, BridgeTimers823F0DE4 fills it, both Director call sites consume
the same local at823F1630 and823F1828, and823F21E4 destroys it. The host now
retains that input with its existing substep buffers, constructs it once and
destroys it in reverse input-stack order. It removes the old phase allocation,
memset and second Construct, preserving data through PostGuiUpdate. Both host
call sites run only in the full cascade that owns this input. Scene-query
temporary allocations remain nested above the frame input. Zero-substep and
catch-up behavior must still obey the existing frame lifecycle.

DoUpdate_Director823E8DE0 reads DirectorBridgeSerialiser at823E8E80 in modes
4/5/6 before controller/world/GameState bridges, then writes at823E8F64 in modes
1/2/3 after the SimPaused store. The host recovers that wrapper order and
forwards the captured late update set's0x100 bit to PreSceneQueryUpdate.
Its original first two arguments are typed buffer stacks; the provider does
not read them. The existing host camera diagnostics remain outside this
reconstruction's behavior claims.

BridgeGameStateToDirector823CD170 now retains its full original state split.
GetStaticLayout precedes Lock. Modes0/1/2/3 run the live/capture arm, including
last-matching takedown, explicit false/-1 capture when there is no match,
capture-queue Construct before append, player team, typed score and combo
copy, score/combo capture, eliminated/expired flags and all eight teams.
The mode1 live arm precedes the later readiness check, as in the assembly.
Mode4 and7 set both ready/restored. Mode5 with a static layout restores only
takedown, action queue and score. Mode6 or absent playback layout writes no
input fields; playback does not copy team/combo/end-event fields. Assertions
continue, including invalid killer, source-interface and enum loop assertions.
The original signed player-slot indexing has no added bounds fallback.

The previous source comment claiming missing game-owned serialiser storage
was stale: both Construct calls and the GameModuleSerialiser timer stream were
already present in V3 and are unchanged. No new recording-state, file-open,
job-entry, or PS3-only producer is introduced.

Validation files are additive and may arrive after this frozen source seal:
CONTRACT_RECEIPT.json verifies selected call/dataflow and per-stack lifetime,
rejecting V3 and four compiling-source omissions; FIXTURE_RECEIPT.json and
SOURCE_BOUND_FIXTURE.cpp execute the exact changed GameState bridge method
with explicit adapters/spies across all eight modes, null/present static
layouts, all eight valid player slots and positive/zero/negative/NaN timers,
and reject six semantic mutations. These are CPU controls, not engine replay.
The actual whole GameModule TU gate must compile with immutable f1 source
plus the named V3 and Director layers and prove no repository-header drift.
AUDIT_RECEIPT.json compares both changed functions against raw original
features. POSTMORTEM_ORIGINAL_PACKET.md is the work CLI dossier whose source
excerpt is the shared preimage; review the frozen private postimage instead.

Root owns whole linking, private candidate creation and native runtime
evidence. No normal install, global input, native playback, pixels/audio or
menu-site/count credit is claimed by these source and CPU checks.
