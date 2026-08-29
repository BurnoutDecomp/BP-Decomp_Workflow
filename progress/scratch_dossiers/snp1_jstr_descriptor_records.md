# The two deferred `PlugInDescRunTime` records, recovered from rodata (2026-08-29)

Registrations 21 (`SndPlayer1`, `off_82F901C4` 'SnP1') and 24
(`SndPlayer1_CgsStreamMod`, `off_82F2E124` 'JStr') are the last two of the RWAC pass's
25 that are still commented out. These are their console records, read straight out of
the decrypted XEX so that when the registrations are lit the host records are the real
recovered fields and not a reconstruction.

**Method.** `file_off = 0x3000 + vaddr - 0x82000000`, big-endian, from
`IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex`. Field names/offsets from
`rw::audio::core::PlugInDescRunTime` (`vendor/renderware/include/rw/audio/core/PlugIn.h`,
console sizeof 52 / 0x34, ProStreet-PDB-confirmed). Independent of the codex decode fleet
— deliberately, so it is a cross-check rather than an echo.

---

## `SndPlayer1` — `off_82F901C4` (file 0xF931C4)

```
821744E4 82BA0220 82BA6C80 82B9C2D8 82BA0568 82F90190 82F910E0 82F90194
00000000 00000000 536E5031 00010306 00010000
```

| off | field | value | note |
|---|---|---|---|
| +0x00 | `pName` | 0x821744E4 | -> `"SndPlayer1"` |
| +0x04 | `pGetSize` | 0x82BA0220 | ✅ bodied |
| +0x08 | `pCreateInstance` | 0x82BA6C80 | ✅ bodied |
| +0x0C | `pPreProcess` | 0x82B9C2D8 | ✅ bodied |
| +0x10 | `pProcess` | 0x82BA0568 | ⛔ FLAG-deferred (the streaming half) |
| +0x14 | `pChannelMaps` | 0x82F90190 | non-null on console |
| +0x18 | `pParameterDescRunTime` | 0x82F910E0 | non-null on console |
| +0x1C | `pEventDescRunTime` | 0x82F90194 | non-null on console |
| +0x20 | `pPlugInDescToolSide` | 0 | zero, as in all 25 |
| +0x24 | `mpNext` | 0 | link field, written by the registry |
| +0x28 | `muId` | 0x536E5031 | `'SnP1'` |
| +0x2C | `mu8PlugInType` | 0 | **<= 3, so this IS a source stage** (`@0x82B6EDD0`) |
| +0x2D | `mu8NumConstructorParameters` | 1 | the `f32 maxRequests` |
| +0x2E | `mu8NumAttributes` | 3 | matches `ATTRIBUTE_MAX` |
| +0x2F | `mu8NumEvents` | 6 | PLAY / STOP / ISREQUESTDONE / GETREQUESTBUFFERED / MODIFYSTARTTIME / PLAY1 |
| +0x30 | `mbVariableInputChannels` | 0 | |
| +0x31 | `mbVariableOutputChannels` | 1 | |
| +0x32 | `mbSeq` | 0 | registry sequence snapshot, written at register time |

The four callback slots are exactly the four addresses the host header already declares,
so the record needs no reinterpretation — but **only three of the four are bodied**. `pProcess`
is the deferral, which is precisely why registration 21 stays commented: a registered record
with a dead `pProcess` is the null-slot poison the deferral rule exists to prevent.

⭐ The plan predicted this record's tail as "0,1,3,6,0,1". **CONFIRMED, field for field.**

---

## `SndPlayer1_CgsStreamMod` — `off_82F2E124` (file 0xF31124)

```
820A91D8 826A4210 826EA508 8268CD10 826A46B0 82F2D91C 82F2FAB0 82F2E638
00000000 00000000 4A537472 00010305 00010000
```

| off | field | value | note |
|---|---|---|---|
| +0x00 | `pName` | 0x820A91D8 | -> `"SndPlayer1_CgsStreamMod"` |
| +0x04 | `pGetSize` | 0x826A4210 | |
| +0x08 | `pCreateInstance` | 0x826EA508 | |
| +0x0C | `pPreProcess` | 0x8268CD10 | |
| +0x10 | `pProcess` | 0x826A46B0 | |
| +0x14 | `pChannelMaps` | 0x82F2D91C | |
| +0x18 | `pParameterDescRunTime` | 0x82F2FAB0 | |
| +0x1C | `pEventDescRunTime` | 0x82F2E638 | |
| +0x20 | `pPlugInDescToolSide` | 0 | |
| +0x24 | `mpNext` | 0 | |
| +0x28 | `muId` | 0x4A537472 | `'JStr'` |
| +0x2C | `mu8PlugInType` | 0 | source stage, same as its parent |
| +0x2D | `mu8NumConstructorParameters` | 1 | |
| +0x2E | `mu8NumAttributes` | 3 | |
| +0x2F | `mu8NumEvents` | **5** | ⭐ **ONE FEWER THAN 'SnP1'** |
| +0x30 | `mbVariableInputChannels` | 0 | |
| +0x31 | `mbVariableOutputChannels` | 1 | |
| +0x32 | `mbSeq` | 0 | |

⭐ **The one structural divergence between the twins in this record: five events, not six.**
Everything else in the tail is identical. The game-side fork drops one of the parent's six
events. Do NOT copy 'SnP1's six across when the 'JStr' record is written — and when the
event surface is bodied, the event enum for this fork must have five entries, which is an
independent check on whichever event the decode finds missing.

This pairs with the already-established fact that the twins' feed records differ too: the
parent's `SndPlayer1FeedDesc` is console-0x10 with TWO pointers, the fork's is console-0x0C
and pointer-free (corrected from the DecFIGS DWARF in `75ad7f41`). The forks are genuinely
different types; nothing may be copied between them without re-attestation.

---

## Consequence for the host records

Both records' `pChannelMaps` / `pParameterDescRunTime` / `pEventDescRunTime` are non-null on
the console. The 23 live host records leave those three null by standing decision
(`PlugIn.h`: "UNPROVEN-consumer on X360 -- null on PC until a reader lands"), and these two
must follow the same rule rather than inventing pointees for them.

⚠️ `mpNext` (+0x24) is the intrusive link `RegisterPlugInRunTime` writes into. It sits about
40 bytes into the record, which is the measured source of the "never register a placeholder
descriptor" rule — a short/placeholder record gets its link write scribbled past its end.
Both records above are full-length, so both are safe to publish *once their callbacks are
real*.
