# Original GUI replay and cache owners

This six-path prerequisite proposal is bound to source `b088fb295acc937c382a2c342cd1d2c7dd31bf20`, workflow `f0255e822018212f03e6a54f9c66ddee9554a569`. The complete pre/post images and hashes are in `BINDINGS.json`; physical checkout files are not source inputs. No original Update entry, callback, preparation stage or caller is selected by this packet.

The new original Update needs the real two-frame player-name storage and several real cache methods. The selected code already reserves the correct replay storage but calls it opaque “CarFlags”; it also narrows one original replay value to32 bits. This packet recovers those owners before the new caller uses them.

## Exact body and type recovery

ARTIST `82529984..825299A0` reads the current one-byte parity, chooses one of two arrays at layout2D0/350, and invokes `CgsNetwork::PlayerName::Construct` on the chosen sixteen-byte element. `8245B3A0` renders the preceding array and its original assertion names `maaGamertags`. The existing two byte arrays are promoted to `CgsNetwork::PlayerName maaGamertags[2][8]`. They occupy the same256 bytes and remain pointer-free. The replay block remains992 bytes, its parity remains at3D0, and its per-car eight-byte values remain unchanged at290.

The original Reset clears only the first character of every name in both arrays. SetupStartOfFrame toggles its parity with `1 - previous`, then clears only the first character in the selected array. The source retains those stores and the existing partial32-byte record clears. No string clear, parity clamp, second buffer or initialization flag was added. The sole selected AboveCar source consumer now obtains `GetPlayerName()` from the same previous-array element; the address, character bytes and surrounding rendering body are unchanged.

The whole64-bit replay value is load-bearing. Native Update `82529A48` executes `ld r5,0(r29)`. IncrementReplayPlayerActive `824EEEDC` saves that full r5 and `824EEF88` executes `stdx r26,r11,r9` into entry+10. The existing s32 parameter truncated it before storing an s64 member. The parameter and copied storage are now u64, preserving all64 bits. The value's higher-level identity is not guessed: the original operations here only copy it. The eight-byte source owner remains `mauCarRecordsC`; there is no invented two-word counter or host-endian extraction.

The existing Increment body still checks unsorted/nonempty, compares each name using the real DirtySDK provider, increments a matched entry, or constructs the first empty entry and copies its value. The change neither seeds a new entry nor returns successful work without performing it.

`GuiCache::GetOnlinePlayerInfo(EActiveRaceCarIndex) const` is the genuine DecFIGS h775 overload. ARTIST `82529948..82529980` inlines its eight-row search. The full body scans the actual retained `maPlayerInfo` owner, compares each real status record's active-race-car field, and returns its address or the original no-match null. It does not read another game's instance or use a placeholder record. The older s32 index overload remains byte-identical.

The DecFIGS wait-reason enum and `GetFriendsListWaitReason`/`SetFriendsListWaitReason` bind the existing cacheB868 owner, currently named `muFriendsPanelBranchMirror`. Event95's original clear and the friends-list uses attest that same word. `IsCameraConnected()` binds the already present camera-status word at13B58; the native Update training branch tests that word against zero. There is no new cache state or friendship.

## Real providers and callers

The selected PlayerName class and Construct body are bound from `BrnCgsPlayerName.h/.cpp`; ARTIST `8230E9C0` pins its16-byte width. The in-game status header provides the actual312-byte record, including name256 and active-race-car index276. `maPlayerInfo` retains the existing named storage used by the old index getter. No class offset is synthesized from a guest address.

The mounted `BrnGuiCache_wB_11.cpp` is the existing Increment owner. The real DirtySDK `vendor/dirtysdk/src/lobbyname.cpp` and its canonical vendor header are retained. Their existing high-bit-byte policy is unchanged and remains outside this delta; this packet does not assert whole-vendor parity. ReplayCredits reads the existing name/count, not the opaque64-bit value; its complete source is bound as an unchanged consumer.

All four modified C++ files already have literal mounts in the exact shipping build_game_exe.bat. The mounted compile_exe.py path is authoritative. No extra TU, CMake edit, second provider or build roster change is proposed.

The existing index-getter callers were audited before adding the enum overload. They pass s32/int row indices or the signed8-bit highlighted-index member, which promotes to int; they retain the old index selection. The bound SelectableGroup/MenuComponent/state headers establish that inherited member's type. The new original recorder will pass an explicit EActiveRaceCarIndex. `CALLER_AUDIT.json` retains the exact read-only source search and context for review. The original Update is absent from the postimages and has no current caller here.

## Postmortem and limits

The assembly ABI overrides the old pseudocode's32-bit third argument. The new u64 type preserves the register value and memory width without assigning an unproven role. Names are actual PlayerName objects at their original pointer-free strides. The selected render consumer is adapted by type, with no extra tick or resource lifetime change. Cache methods use original fields and declarations, not mirrors. All earlier b088 audio/pause providers remain intact.

Static inspection checks exact base/pre/post hashes, the unchanged old index getter, width and store closure, untouched replay value array, current/previous name selection, leading-byte reset rules, all existing shipping mounts and provider snapshots. No C++ was compiled, no fixture was imported or evaluated, and no tests, CI, game/input or IDB work occurred.

This is a prerequisite checkpoint, unreviewed and uncompiled. It does not make the complete Update ready. The original UI latch definitions82FB5924/25, native output/callback borrowing, existing PC controller/music record encodings and caller/temporary ownership reconciliation remain separate boundaries. No debug-control completion or runtime acceptance is claimed.
