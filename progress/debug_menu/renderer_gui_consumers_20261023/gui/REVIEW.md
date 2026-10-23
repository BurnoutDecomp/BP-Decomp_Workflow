# Fresh-eyes review: GUI channel-40 action publication batch

Review basis: `scratch/DEBUG_MENU_1011/gui_debug_event_publish_batch_20261023_codex01/`, source base `af18caf8a9e02428cfaa4705599e2b1ca9ea7377`, and comparison source commit `aa6b7ec4f9af54230bc2e04622b1d9c75c26700b`. The four edited-file blobs are identical at both commits. This is source-only review; no build, compile, test, CI, native, game, Stage, Run, or input validation was performed.

## Verdict

**VERDICT: pass** for the five bounded call-site publication changes. They emit the channel-40 records expected by the existing PC decoder and match the ARTIST wire records. This grants no runtime or verified-site credit.

## Exact source and ARTIST checks

All four edited source-file blobs match at both `af18caf8a9e02428cfaa4705599e2b1ca9ea7377` and `aa6b7ec4f9af54230bc2e04622b1d9c75c26700b`:

- `BrnOnlinePlay.cpp`: `38645be819a0d0240bc3d5e6f29e586225d98c44`
- `BrnCrashNavSettings.cpp`: `917be46e99e1ea95752c0e82f6e1af78636d6cad`
- `BrnCrashNavDriverDetails.cpp`: `e2526fdae21763f5108a9a0cb104722d1699ffaf`
- `BrnShowtimeInstantResults.cpp`: `635f46e3dbed07f5bdcabb49b7058123ab44bee0`

The shared event declarations, wrapper, channel-40 drain, and three consumer files also have identical blobs at both source commits. The proposal changes five calls across the four files above and leaves the shared publisher and decoder untouched.

The original ARTIST export hashes match the proposal bindings. `OutputGuiEvent<GuiEventActivateCrashNav>` at `0x82493938` writes header `{8,191,12}`, copies the two payload words, and queues channel 40 / 20 bytes. The existing `GuiEventActivateCrashNav` C++ object already contains exactly that 20-byte record, so direct `AddEvent(..., KI_CHANNEL_GUI_OUT, sizeof(lActivate))` matches the wire and avoids wrapping it twice. The three changed CrashNav calls preserve their `true` payload and the original order relative to `SendStateEvent("GO_BACK")`.

`OutputGuiEvent<GuiEventShowHideHud>` at `0x82493988` writes `{1,148,12}` plus the one-byte payload and queues channel 40 / 16 bytes. `GuiEventShowHideHud` is declared as a raw one-byte payload, so `GuiEventWrapper<GuiEventShowHideHud, 40>` is the correct single wrapper; the existing wrapper layout has payload offset 12 and its 4-byte alignment yields the expected 16-byte record. ARTIST `ShowtimeInstantResultsState::OnEnter` at `0x824C5D28` independently emits the same channel-40 record inline, and `Update` at `0x824DFB48` calls the named publisher. The two Showtime edits preserve the hide byte (0) and mirror those records.

The additional `GuiEventShowHideHud` occurrence in `ShowtimeInstantResultsState` is under `OutputInternalState` (channel 42), not channel 40, so leaving it unchanged is correct. The packet also correctly avoids a global `OutputGuiEvent<T>` rewrite: the existing type population mixes record-bearing `GuiEvent<N>` objects and raw payload structs, so one generic encoding would double-wrap some records or omit headers for others.

At aa6, `DrainFlowOutputQueue` has no direct queue-id arms for 148 or 191; the channel-40 case reads the record's size, inner event id, and payload offset, queues the unwrapped payload in `mGuiOutQueue`, and calls `RouteEventToFlow`. The exact recipient paths exist: `BrnGameModule.cpp` handles event 191 from the game bridge; `BrnRaceMainHudState.cpp` and `BrnFBurnMainHudState.cpp` handle event 148 as a one-byte value. The proposal feeds those existing paths without changing decoder behavior.

## Limits

The reviewed scope is only the five publication calls. Other `OutputGuiEvent<T>` callers and the full 66-instantiation audit were not re-reviewed here. The proposal remains uncompiled and unexecuted; source matching does not prove the decoder or recipients work at runtime.
