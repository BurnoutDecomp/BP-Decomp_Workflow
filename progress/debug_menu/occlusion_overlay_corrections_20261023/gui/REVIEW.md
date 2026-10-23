# Independent source review: GUI overlay wire-fix delta

VERDICT: pass

The correction fixes the event-184 record and routes all three affected producers through the ARTIST channel-40 shapes. The actual 9cbefd receiver chain is hash-bound and consumes the corrected payload at the expected offset.

## Wire and producer checks

- `CrashNavSettings.cpp` now adds and zeros `muPad0C` between the 12-byte `GuiEvent<184>` header and the 288-byte `GuiOverlayRequest`. Its assertions pin header size 12, request size 288, request offset 16, and total size 304. That matches ARTIST publisher `0x82436BE0`: `{288,184,16}+288`, channel 40, 304 bytes.
- The helper is shared by the existing `OnInputSponsorProductCode` no-match producer (`0x824CD030`) and the new signed-out Profile producer (`0x824D90E8`). Both now send the same 304-byte event-184 wire. The sponsor export hash matches the packet (`B36202FF…E476B4C7`); the other bound caller/publisher hashes also match.
- The debug-gated event-188 producer still uses its explicit pad and 24-byte `GuiOverlayWaitFinishWire`, matching ARTIST `0x82476E98` `{8,188,16}+8`. Its caller stays in the pre-event-overlay expiry branch. The patch replaces the old direct post instead of adding a second event.
- The previously committed event-191 output remains outside the patch hunks. No shared publisher, decoder, or overlay consumer is changed.

## Receiver chain pinned to 9cbefd

I used `git show` and `git rev-parse` against B5 `9cbefd173085312ebaee5bab4875b8492fc292cb`, not the physical checkout. The five packet base blob IDs match that commit exactly: `CgsGuiStateInterface.h` `118bbf75…`, `BrnGuiModule.cpp` `d3c6e8f3…`, `BrnGuiOverlaysDirector.cpp` `bdd2426d…`, and both producer sources. In the bound source:

1. `StateInterface::OutputGuiEvent<T>` queues the bare object as `(GetEventType(), sizeof(T))` (header lines 219–222), explaining why direct IDs 184/188 miss the channel-40 arm.
2. `GuiModule::DrainFlowOutputQueue` channel 40 reads wrapper words 0/1/2 as payload size, inner event type, and payload offset, then queues `base + offset` under the inner ID in `mGuiOutQueue` (around line 3303 onward).
3. The existing bridge copies IDs 184/188 once into `mOverlayLoopBackQueue` (around line 4676), appends that queue to the GUI input before `mOverlaysDirector.Update` (around lines 4259–4263), and the director’s cases 184/188 call `HandleOverlayRequest` / `HandleWaitFinishRequest` (around lines 301/309). I found no duplicate post added by this delta.

The two composed postimage hashes match `bindings.json`; the exact 9cbefd base blobs for all five receiver/source files match as well.

## Limits

This is a source-only pass. No compile, test, CI, native/game, Stage, Run, or input validation was performed. The channel-40 drain trusts the header offset/size; this delta supplies the ARTIST-sized 304-byte record required by that decoder. No behavior or debug-menu site credit is claimed.
