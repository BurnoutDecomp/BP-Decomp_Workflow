# Source, ABI, and receiver evidence

## Original output records

The 66-entry ARTIST audit binds these original `OutputGuiEvent<T>` instantiations to channel 40:

- `GuiEventScoreboardRequestIndexEvent`: publisher `0x82493FF8`, `{4,111,12}+4`, 16 bytes.
- `GuiEventScoreboardRequestVariationEvent`: publisher `0x82494048`, `{4,112,12}+4`, 16 bytes.
- `GuiEventScoreboardRequestTableEvent`: publisher `0x82494098`, `{4,113,12}+4`, 16 bytes.
- `GuiEventScoreboardRequestGamercardEvent`: publisher `0x82493D38`, `{16,120,12}+16`, 28 bytes.

The first three publishers load record size `0x10`, channel `0x28`, payload offset `0x0C`, payload size `4`, and inner ids `0x6F`, `0x70`, and `0x71`. The gamercard publisher loads payload size `0x10`, offset `0x0C`, record size `0x1C`, channel `0x28`, and inner id `0x78`. The complete per-export hashes and xrefs are in [artist_scoreboard_wires.tsv](artist_scoreboard_wires.tsv) and [bindings.json](bindings.json).

The ARTIST callers are:

- `OnlineScoreboards::HandleLeaderboardRequestState` (`0x8249F458`): callsites `0x8249F534` (111), `0x8249F594` (112), and `0x8249F614` (113).
- `OnlineScoreboards::HandleControllerInputPressedUsingTable` (`0x824A9B78`): callsite `0x824A9DB4` (120).
- `CrashNavMapMain::HandleCrashNavInputPressed` (`0x824CCAE8`): callsite `0x824CCD84` (120).

## Current source shape and correction

In B5 `e306dbd2`, each affected event type already derives from `CgsGui::GuiEvent<id>`, whose three words plus payload form the complete output record. The index, variation, and table types are 16 bytes with `{4,id,12}`; the gamercard type is 28 bytes with `{16,120,12}`. The source constructors initialize these header words, and the gamercard member is a 16-byte `CgsNetwork::PlayerName`.

The source definitions pin this existing-record layout: `BrnGuiDemangledEventTypes.h:1196-1214` constructs ids 111/112/113 with `{4,id,12}` and one word; `:1187-1192` constructs id120 with `{16,120,12}` followed by the 16-byte player name. The full object is the ARTIST output record, so the source adjustment keeps `sizeof(T)` unchanged and changes only the AddEvent channel.

The current generic `StateInterface::OutputGuiEvent<T>` at `CgsGuiStateInterface.h:219-222` direct-passes the object on the queue channel `GetEventType()`. That keys the four cases by 111/112/113/120 instead of 40. `DrainFlowOutputQueue` has a channel-40 decoder that extracts the inner type and payload; unrelated direct IDs fall through its default. The patch keeps the already-built record bytes and changes only the queue channel to 40. Wrapping again would add a second header and violate ARTIST’s sizes and offsets.

The receiving `GameBridgeGUIToX` cases show the consumers:

- Case 111 reads the category and asks `NetworkInSelectScoreboardEvent` for indexes.
- Case 112 reads the index and asks for its variations.
- Case 113 reads the variation and asks for the selected scoreboard table.
- Case 120 copies the `PlayerName` into the network gamercard request.

A sibling producer, `OnlineGameRoomPlayerInfo::PostGamercardRequest`, already adds the 28-byte event-120 record on channel 40 and remains untouched. The event-121 score-target call in `BrnOnlineScoreboards_wI_07.cpp` is under `const bool lbEvScoreTargetEnabled = false`; it is not an active post in this source and is excluded from the five-call count. These five are actual UI/action posts; no debug registration sites are counted.

The additional event-120 xref `0x824A5130` is the already-correct `OnlineGameRoomPlayerInfo::PostGamercardRequest` path: source lines 192-200 construct the player name and AddEvent the complete record on channel 40. The two event-120 sites changed here are the table gamercard action (`0x824A9DB4`) and CrashNav friend gamercard action (`0x824CCD84`).

## DecFIGS declaration shape

DecFIGS names the payload members: `miCategory`, `miIndex`, `miVariation`, and `PlayerName mPlayerName`. Its PS3 template ids are 112/113/114 and 121, respectively. ARTIST X360 owns the target IDs 111/112/113 and 120 and the wire dimensions above; the patch follows ARTIST for behavior and uses DecFIGS only for member names and declaration shape.
