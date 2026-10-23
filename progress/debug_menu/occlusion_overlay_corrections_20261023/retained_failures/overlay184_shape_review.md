# Independent source review: GUI overlay director channel-40 batch

VERDICT: fail

The two call-site substitutions are narrowly scoped and correctly identify the original producers, but the event-184 record is not laid out as the ARTIST wire record on the host source types.

## Blocking finding — event 184 payload offset/size mismatch

In the composed [CrashNavSettings.cpp](../gui_debug_overlay_director_batch_20261023_codex02_9cbefd/composed_postimage/src/GameSource/Gui/Flow/Screen/States/BrnCrashNavSettings.cpp:198), `GuiOverlayRequestWire184` inherits `CgsGui::GuiEvent<184>` and immediately declares `GuiOverlayRequest mRequest`; it declares no field for bytes +0x0C..+0x0F. The packet's changed call at lines 517–521 queues `sizeof(lWire)` while the constructor writes payload offset 16.

The corresponding source types define an empty `CgsModule::Event` base (`CgsVariableEventQueue.h:38`) and a generic `GuiEvent<N>` with three `u32` header words (`CgsGuiEvent.h:31–46`), so that base occupies 12 bytes with 4-byte alignment. `GuiOverlayRequest` consists of 0x44-byte records and 4-byte fields through its 0x120-byte X360-pinned layout (`BrnGuiEventTypeDefs.h:621–713`); it has no 8-byte-aligned data member. Consequently the wrapper member starts at +12 and the wrapper is 300 bytes, not 304. The header still advertises `{288,184,16}`, so the queue has a 288-byte payload at +12 while the receiver will read 288 bytes at +16: the overlay-id payload is shifted, the final four bytes extend beyond the queued record, and the event is not faithful to the original record.

This matches the packet's own ARTIST binding: `0x82436BE0` (export SHA-256 `D6D4C880…D603E5AA5C`) copies 288 bytes to +16 and calls `AddEvent` on channel 40 with 304 bytes. Caller `0x824D90E8` (SHA-256 `4877069A…D199C735E`) constructs `PRONoSaveLd` and invokes that publisher at `0x824D92F0`. The helper must explicitly own/zero the +0x0C..+0x0F gap and assert its member offset and total size before this call can pass.

## Event 188 and composition

The event-188 site is source-consistent: `GuiOverlayWaitFinishWire` explicitly supplies `muPad0C`, places its 8-byte request at +16, and the proposed call queues 24 bytes (`BrnRaceMainHudState.cpp:140–149, 1802–1804`). The ARTIST caller export `0x824806E8` (SHA-256 `4420CAE9…EA85F719A8`) reaches this producer in the pre-event-overlay expiry path; publisher `0x82476E98` (SHA-256 `12BDFC48…47FD948`) specifies `{8,188,16}+8`, channel 40, size 24. This is a debug-override-only branch, as the source notes.

Both composed postimage hashes match the packet bindings: CrashNavSettings `526A7444…96D75F89`; RaceMainHudState `C7520FE1…99EFEBF`. The diff replaces each old generic post at the same site, so it does not add a duplicate event there. The already-present event-191 output in CrashNavSettings (lines 467–476) remains outside the changed hunk. No shared decoder or consumer is modified.

## Scope and limits

Review covered the supplied two-file patch/postimages, its source-site and binding records, and the four bound ARTIST exports. The packet identifies the existing channel-40 decoder and overlay loopback as the delivery path; the composed snapshots do not include those receiver files, so I did not independently bind their current contents to commit `9cbefd`. The local generic event/type declarations cited above are static layout evidence, not a compiler-produced layout check. No build, runtime, native/game, Stage, Run, or input validation was performed; this review grants no behavior or site credit.
