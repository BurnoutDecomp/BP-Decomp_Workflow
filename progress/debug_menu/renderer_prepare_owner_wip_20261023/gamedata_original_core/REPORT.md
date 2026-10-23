# Original four-argument GameData caller

This separate WIP proposal recovers the complete ARTIST `GameDataModule::Prepare` caller at `0x82673F38`, including the previously omitted GameTalk and LiveUpdate stages, plus its original scoped status-copy helper. It does **not** claim that the original helper/core callees are all available or that initialization/native integration is ready.

The ten-path diff is `source/gamedata_original_core.patch`; full pre/post files and hashes are in `SOURCE_MANIFEST.json`. The composition base is source WIP `53961615f5f9105568fa37a329f79758451c922d`. It is independent of the six-path AutoTest continuation. No active source/worktree, index/refs, build, tests, CI, executable, game/input, or inventory was changed.

The current two-argument Prepare method remains byte-identical, and its native DONE value remains7. Original stage names are added as distinct enum aliases with ARTIST's actual values. In particular, original GameTalk=7 and DONE=19; the shortened host path's DONE=7 is not relabeled as the original state machine. These lifecycles must not be mixed.

## Recovered caller

The method constructs its filesystem-status accumulator on every entry. It preserves the original stage order: base1, resource2, banks3, pools4, allocators5, DLC16/17/18, Attrib6, GameTalk7, LiveUpdate8, data lists9–14, done19. Case15 remains invalid; DecFIGS's older test-stream stage does not override ARTIST.

DLC17 submits at most one patch request through a real input-stack IOHelper, retaining the GameData receiver pointer, saved package ID, path/version read order, queue clear, unlock, resource pump and scope pop. DLC18 pumps once when no reply is available. When a reply is present, it increments the index; if another package remains, it selects17 and yields through the false/status tail before any next submission. This retains the repaired ARTIST yield boundary from the older stage18 audit without reusing that packet's remaining omissions.

Attrib6 fetches heap allocators21/20/19 and linear22 in the original evaluation order, prepares with max-vaults80, carves the Attrib input on the original input stack, calls the exact three-argument schema helper, and destroys the carve on either helper result. It calls the original two-stack data-list helper signatures rather than the native zero-argument shortcuts. After the challenge list succeeds, it resets the ICE-list prepare counter before stage11.

GameTalk7 calls Prepare(10.0f,1/60.0f), checks its result, then checks DebugGameTalkInterface Prepare with the original assert. LiveUpdate8 invokes its module Prepare. Completion resets prepare to1 and release to0, publishes the actual member allocator list under the output write lock, and returns true. Every false/default route publishes the current filesystem-status accumulator under the same write lock, with no fabricated null-output guard.

`UpdateResourceModule` preserves the original enum result and caller stack ownership. It creates ResourceOutput on the output stack, invokes the original four-argument resource core, read-locks and copies its filesystem status into the GameData member, unlocks, then pops the scoped output. ResourceOutput Destruct is recovered from the exact DestroyIOBuffer instantiation's shared thunk to IOBuffer::Destruct.

## Required typed corrections

- `AddPatchRequest`'s first field is the receiver pointer supplied in r4, not a signed32-bit integer. The existing canonical event is corrected in place to retain the native pointer, event ID, 256-byte path and package version. No receiver truncation/cast is introduced; queue bytes use sizeof the actual host record.
- `GameTalk::Prepare` returns true in ARTIST (`li r3,1` at8283952C), and GameData checks that return at82674328. Its current void declaration/body is corrected to bool/true without changing the original side effects.
- GameTalk's embedded debug component is its existing derived GameTalkDebugComponent type, identified by the GameData constructor's vtable stores and the named GetName/GetPath/OnActivate bodies. The prior base-typed member could not dispatch those overrides. No duplicate component/type is created.
- The new GameData members use their canonical GameTalk, DebugGameTalkInterface, LiveUpdateModule and filesystem-status types. ARTIST identifies the X360-only objects through constructor/vtable targets, prepare calls and assert text. DecFIGS does not list these platform members; it supplies the remaining API/member declaration shape.
- GameData's direct read of its owned DLC manager's package count is expressed by bounded friendship, matching the actual private typed owner rather than a raw-offset helper.

## Availability boundary

Ten original stack-backed GameData helper overloads are declared without quiet/adaptor/trap definitions: CreateBanks, CreatePools, CreateAllocators, schema prepare, and the six data-list prepares. The existing shortened native implementations are retained separately. The original four-argument ResourceModule::Update is likewise declared without a substitute body. `MISSING_LINK_SYMBOLS.json` lists these exact eleven targets.

GameData's existing Construct does not yet construct the newly recovered GameTalk/LiveUpdate/debug-interface members. Their original construction order, transport prerequisites, shipping mounts and full lifecycle need a separate recovery. The new fields alone do not initialize their engine state. DLC content discovery remains an actual backend dependency; no empty enumeration or synthesized patch reply is supplied.

`INITIALIZATION_BOUNDARIES.md` records another prerequisite found during tracing: the renderer's missing new-module seed and the unresolved game/LiveUpdate legacy IO factory ownership. This packet does not alter the base module, bypass its readiness, activate renderer Prepare, or change native buffer/sky-dome allocation policy.

No source/link/runtime/site credit is granted here. All 1355 registration-site counts remain unchanged. Root owns WIP publication, source review, composition and any subsequent build/native validation.
