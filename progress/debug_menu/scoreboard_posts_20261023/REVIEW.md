# Independent source review — scoreboard channel 40

VERDICT: pass

Reviewed the proposal against its pinned `e306dbd2a266a53b77cfb8ccbc86e01726dc5395` source, ARTIST publisher and caller exports, DecFIGS declaration shape, and the exact PC receiver chain. The three touched base blobs match the bindings; the postimage SHA-256 values are `dce4dfa9861cc2636ee32fba13a7f3c9730ee2c87b48438c59f65b1ab7dd33cc` (`BrnOnlineScoreboards_wI_06.cpp`), `02d6368fcf5e0353043d3cfbb47157ac8a7dade60e81a6fe522ba7f4f4bfcdab` (`BrnOnlineScoreboards_wI_07.cpp`), and `aa7b9badd90dbade91334ea700c69564acff077400ae4a95086fc64278eb4753` (`BrnCrashNavMapMain.cpp`). These files remain byte-identical in published source `7e455d8854a32df1ca1934a54cc279c1e268a103`.

All five active call sites now enqueue their already-formed record on channel 40, with original record sizes and inner headers intact:

| Inner event | Record bytes | Payload | ARTIST header |
|---|---:|---:|---|
| 111 index | 16 | 4 bytes at +12 | `{4,111,12}` |
| 112 variation | 16 | 4 bytes at +12 | `{4,112,12}` |
| 113 table | 16 | 4 bytes at +12 | `{4,113,12}` |
| 120 gamercard (two UI call sites) | 28 | 16 bytes at +12 | `{16,120,12}` |

The ARTIST assembly pins those sizes, offsets, inner IDs, channel `0x28` (40), and the listed publisher-to-caller paths. The PC channel-40 drain decodes `{size,type,offset}` and forwards the payload to the matching `GameBridgeGUIToX` consumers. Direct-queueing IDs 111/112/113/120 through the generic helper bypasses that decoder, so this targeted channel correction addresses the evidenced mismatch without adding a second header. The existing channel-40 event-120 sibling producer is untouched; the five posts replace existing posts rather than duplicate them. Event 121 remains excluded because its source call is guarded by a constant false flag.

Scope is source-only: three files, five existing posts, no generic-template, decoder, receiver, or campaign-inventory changes. DecFIGS supports member names and shape; ARTIST supplies the X360 IDs and wire layout. No build or runtime validation was performed, and this verdict grants no site or runtime credit.
