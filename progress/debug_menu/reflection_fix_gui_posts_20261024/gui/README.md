# GUI channel-40 network and scoreboard publisher repair proposal

Base: committed B5 source `ea5ce572baedd4ad8918f6d5bfcdfd756250d411` (parent `b9c0e692bc9d8f232b9986923acf07aff26c0639`). Proposal is source-only and binds each touched source preimage to its exact Git blob and SHA-256 in `bindings.json`.

## What this repairs

Four active producer sites across three source files currently call the generic `StateInterface::OutputGuiEvent`, whose implementation queues `GetEventType()` as the outer queue id and passes `sizeof(T)` unchanged. The ARTIST instantiations instead queue a channel-40 record with an inner event id and payload offset. In the current PC flow drain, channel 40 is the recognized GUI-out channel; it unwraps words 0–2 and rekeys the resulting payload by inner id before forwarding. The four raw outer ids are not handled by that channel-40 arm, so these posts do not reach their existing consumers.

The proposal preserves the generic template. It fixes each actual producer according to its existing source representation:

- Events 246 and 264 are local **8-byte payload-only** structs. ARTIST writes `(8, <built-in function id>, 12)` plus those eight bytes, total 20, on channel 40. The proposal wraps each payload in `GuiEventWrapper<Payload, 40>` and queues the wrapper. It asserts payload size, wrapper size, and `mOutEvent` offset.
- Event 323 is already a **32-byte complete record**: `(20, 323, 12)` plus a 20-byte payload. ARTIST writes the same record. The proposal queues the existing record directly on channel 40 and asserts its base header, payload offsets, and total size. It does not add a second wrapper.
- Event 266 is already a **16-byte complete record**: `(4, 266, 12)` plus the selector word. ARTIST writes that record on channel 40. The proposal queues the existing record directly on channel 40 and asserts event id, base header, selector offset, and total size. The earlier correct channel-40 post in `CrashNavSettings::OnLeave` remains as source context; only the raw `Update` post is changed.

## Site and consumer counts

The patch changes four actual producer call sites in three owned files: one event 246, one event 264, one event 323, and one event 266. These are producer/support-system counts, not debug registrations. Their current receivers are concrete: `BrnNetworkStateManager::ProcessGuiEvents` consumes 246 (player-option dispatch), 264 (camera/mugshot output), and 266 (news/TOS request/release); `GameBridgeGUIToX` consumes 323 and copies its 20-byte telemetry payload into `NetworkInTelemetryEvent`. The event 121 site is explicitly excluded: its current constant-false entitlement gate remains unresolved and has its own correction addendum at `gui_event121_gate_classification_addendum_20261024_ea5ce572/`.

## Evidence boundary

Full ARTIST X360 JSON exports for all four publisher instantiations and their actual caller functions are in `evidence/ARTIST/`; `site_map.tsv` gives each call address. The ARTIST publisher records pin payload size, id, offset, channel 40, and total bytes. The current receiver and decoder snippets are exact-base source excerpts in `evidence/current/`. DecFIGS `0x4D8A7C` corroborates the `CrashNavAccountManagement::HandleNewsAndTOSEvent(const GuiEventNetworkNewsAndTOS*)` receiver type; ARTIST remains the authority for event 266's X360 id and wire bytes. The 246/264 current payload fields are checked against the exact current demangled consumer declarations and ARTIST publisher/caller assembly; no unsupported DecFIGS layout inference is used.

The proposal does not modify `CgsGuiStateInterface.h`, `BrnGuiModule.cpp`, or other decoder/consumer code. The existing decoder is sufficient once producers publish the original channel-40 shape. `patch.diff`, complete preimages/postimages, source maps, and hashes are included. No production source, Git ref/index, build, CI, game, or input state was changed or tested.
