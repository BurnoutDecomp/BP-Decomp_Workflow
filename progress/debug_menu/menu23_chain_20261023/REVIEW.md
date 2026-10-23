VERDICT: pass

Scope and bindings

Reviewed the source-only delta pinned to `7e455d8854a32df1ca1934a54cc279c1e268a103`. The patch changes four menu-music producer calls in `BrnCredits.cpp` and `BrnOfflineInstantResults.cpp`, plus `SoundLogicModule::ProcessGuiEvents` case 23. Preimage blobs match the pinned commit; source postimage SHA-256 values and ARTIST/evidence hashes match `bindings.json`. Patch SHA-256: `8BF1206258E92FF1C7698E2175457D7E30D562AE2249E8302A2613C15E58A752`.

The producer wire is correct. The current `GuiEventPlayMusicOnMenuStream` constructor bakes header `{8,23,12}` into its 20-byte object. ARTIST `OutputGuiEvent<GuiEventPlayMusicOnMenuStream>` at `0x82476C00` writes the same three header words and 8 payload bytes, then calls `AddEvent` with channel 40 and size 20. Posting the existing complete object directly to channel 40 therefore matches the original bytes without adding a second wrapper. The current generic source helper instead queues that object under its inner type 23; these four targeted direct posts fix that channel mismatch while leaving the shared template alone.

The four values and call sites also match ARTIST: Credits::OnLeave posts the empty-name hash with both flags clear; Credits::UpdateLoadResources posts the `Credits` stream with both clear; InstantResultsState::WillShowCredits posts the credits stream with flag A set and B clear; TriggerExitResults posts the empty-name hash with A set and B clear. The producer call remains at its existing point in each function, and each replacement emits one queue record, so the delta adds no duplicate notification or extra frame of staging.

The receiver handles both payload shapes correctly. ARTIST `ProcessGuiEvents` case 23 (`0x826ED6C8`) reads hash and flags at payload offsets 0, 4 and 5. The channel-40 drain unwraps `{8,23,12}+8` to the 8-byte body before SoundLogic receives it; `GetGuiPayload` leaves that raw body at offset 0, and also strips a full type-23 record if one reaches this case. The separate channel-155 module translation rekeys its full `{0,155,12}+8` record to type 23 without stripping the header. Since `GetGuiPayload` only strips a matching header id, the new guarded branch recognizes that 20-byte type-155 record and reads offsets 12, 16 and 17. It preserves the existing boot/title compatibility flow and leaves events 508/509 untouched.

`0x82476C00` has two additional ARTIST callers, BootLegal and PostTitleScreenLoad. In the pinned PC source those paths deliberately emit full event-155 records through the unchanged channel-155 translator; they are not omitted channel-40 producer edits, and the new receiver branch retains them. The other three generic ARTIST callers plus Credits::OnLeave’s inlined post correspond to the four changed source sites.

Limits

This is a static source pass only. No compilation, audio runtime check, or game run was performed; no verified-site or audible-result credit is granted.
