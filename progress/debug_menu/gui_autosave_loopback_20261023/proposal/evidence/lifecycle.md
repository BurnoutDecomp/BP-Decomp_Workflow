# Source and lifecycle proof

Candidate source is `b5-decomp` commit `9af6a868959578f4eafa9af0d69ccd27081667a0`; the physical worktree was at `91a0ed564f9c9e3dec915bfb416c0467650084ef` and was not edited. The candidate C++ source blob is `eee391b23fc3e4b0c0e1406394489d2db596e1cc`. The complete exact candidate and proposed file are in `../source/BrnGuiModule.cpp.before.cpp` and `../source/BrnGuiModule.cpp.after.cpp`; `../source/BrnGuiModule.patch` is the complete diff.

## Original sequence

- `OnlineGameOptionsSummary::HandleControllerInputSaveOptions` at ARTIST `0x824A8D94` saves the online-game options, writes a one-byte request payload of zero (`r27` initialized to zero at `0x824A8C6C`, stored at `0x824A8DA0`), posts event 356, and then shows the options summary. See `artist_assembly.md`.
- `StateInterface::OutputGuiEvent<GuiAutosaveRequestEvent>` at `0x824937E0` builds channel 40 with `{payload size 1, type 356, payload offset 12, payload}` and adds it to the observer output queue.
- `EventInterpreterModule::ProcessOutEvents` at `0x8285E568..0x8285E57C` unwraps the wrapper into an event keyed by its inner type and forwards it to the module out-event queue.
- `CgsGui::GuiModule::Update` at `0x82860568..0x82860578` appends that queue to the module-owned queue at offset `+111644`; BrnGui's normal next-update input walk handles event 356 at `0x82529054`.
- The ARTIST case 356 ORs the request byte into the per-update force byte and writes the pending byte. The autosave tail later checks pending, combines force with the 60-second throttle, then clears pending when it starts the save.

## Candidate PC lifecycle

- `BrnGuiModule.cpp:2484` begins `DispatchInboundGuiEvents`; its event-356 arm at `:2779` already has the exact two native effects. `Update` checks pending at `:4000` and resets the force byte at `:4073` after the tail.
- The flows update at `:4330`; their channel-40 output is drained later at `:4368`. `DrainFlowOutputQueue` handles channel 40 at `:3303`: unwraps the record, appends it to `mGuiOutQueue`, then sends the unwrapped event to the custom-renderer and subscribed flows. There is no 356 module-latch consumer in this late path.
- `BrnGameModule.cpp:4876-4893` sets the current `mpGuiInputBuffer` and calls the GUI update. `CreateStaticIOBuffers` at `:5289` constructs that input buffer for a simulation step; `DestroyStaticIOBuffers` at `:5337` destroys it, including the final-step teardown at `:5176` and intermediate-step teardown at `:5129`. A late append to that step's GUI input queue would be retired before the next update.
- The autosave pending/force fields are module members (`BrnGuiModule.h:613-621`). The late observer drain occurs after the current tail has already cleared the force byte, so setting the same two latches there naturally leaves them for the next update's tail. A payload of zero remains non-forcing and observes the original 60-second throttle; a nonzero payload retains the original force behavior.
- `mOverlayLoopBackQueue` is a different PC seam: it only admits 184/186/188/189/190/279/322 at `BrnGuiModule.cpp:4660-4670` and feeds the overlays director after module inbound dispatch. Adding 356 there would not restore the module consumer.

## Proposed one-site change

At the channel-40 drain, after extracting `luEventType` and `lpRawEvent`, apply only the existing event-356 latch operations. Do not break or add a second event: the existing `mGuiOutQueue.AddEvent`, renderer delivery, and flow routing remain untouched and each runs once.

## Verification scope

No C++ compilation, test, game launch, Stage/Run/input operation, CI action, or Git mutation was performed for this proposal. The only files created are under this scratch proposal directory. A native fixed-build acceptance should repeat the same route/save case, observe event 356 at the late drain, and then observe one save after `lastAutosave + 60s` for the natural zero payload. Check a force-byte path separately (the native route producer above is explicitly zero) to confirm the existing bypass still works; do not convert the route event into a forced save.
