# AEMS/RWAC/Splicer X360 rodata recovery

## Scope and extraction rule

Source image: `IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex`.

Every image read below uses:

```text
file_offset = 0x3000 + (vaddr - 0x82000000)
```

Multi-byte integers and IEEE-754 values are decoded big-endian. Descriptor dumps are
exactly `0x34` bytes (13 words), which covers the full console descriptor size stated
by the checked-in vendor header. Pointer-target data previews are 32 bytes unless the
target is a NUL-terminated name string, in which case the dump ends at and includes the
terminating NUL.

## Descriptor layout used

The checked-in vendor header does **not** expose a fully named `PlugInDescRunTime`
definition: it deliberately leaves the first `0x24` bytes opaque. This is the exact
definition at
`b5-decomp/vendor/renderware/include/rw/audio/core/PlugIn.h:168-187`:

```cpp
class PlugInDescRunTime
{
public:
    // Only the fields the bodied registry walks touch are modelled by name; the
    // gap before +0x24 is the (un-homed) object header / per-type hooks and is
    // preserved as opaque storage so offsets stay exact.
    char mHeader[0x24]; // +0x00 .. +0x23 -- opaque object header (un-homed here)
    // FLAG (rwaudio PDB reconcile -- ProStreet08Milestone.pdb): PDB struct
    // rw::audio::core::PlugInDescRunTime [sizeof=52] names the +0x00..+0x23 prefix this
    // recon left opaque: +0x00 char* name; +0x04 GetSize(PlugInConfig*); +0x08
    // CreateInstance(PlugIn*,void*); +0x0C pPreProcess; +0x10 pProcess; +0x14 pChannelMaps;
    // +0x18 pParameterDescRunTime; +0x1C pEventDescRunTime; +0x20 pPlugInDescToolSide; then
    // +0x24 listNode (== mpNext), +0x28 guid (== muId), +0x2C plugInType, +0x2D
    // numConstructorParameters, +0x2E numAttributes... Kept opaque here (the registry walk
    // only touches +0x24/+0x28); expand when a TU needs the descriptor body.
    void *mpNext;       // +0x24 -- intrusive next link (PDB listNode)
    u32 muId;           // +0x28 -- registration id (PDB guid)
    char mPad2C[0x32 - 0x2C]; // +0x2C .. +0x31 -- opaque (PDB plugInType/numCtorParams/numAttributes..)
    char mbSeq;         // +0x32 -- registry sequence snapshot
};
```

No separate `PlugInRegistry.h` or more fully expanded descriptor declaration is present
in the current checked-in `b5-decomp/vendor/renderware/include/rw/audio/core/` directory;
the `PlugIn.h` class and its PDB-reconcile comment above are therefore the closest
same-directory definition. The closest fully named declaration is the DecFIGS outline
of the original SDK header,
`references/DecFIGS/dwarfdump/SDKs/EATech/include/rw/audio/core/plugin.h:175-230`:

```cpp
struct rw::audio::core::PlugInDescRunTime {
    char * name;
    unsigned int (*)(rw::audio::core::PlugInConfig *) GetSize;
    bool (*)(rw::audio::core::PlugIn *, void *) CreateInstance;
    unsigned char * pSpuElf;
    unsigned int spuElfSize;
    ChannelMapPair * pChannelMaps;
    ParameterDescRunTime * pParameterDescRunTime;
    EventDescRunTime * pEventDescRunTime;
    PlugInDescToolSide * pPlugInDescToolSide;
    void * listNode;
    DecoderDesc::Guid guid;
    unsigned char plugInType;
    unsigned char numConstructorParameters;
    unsigned char numAttributes;
    unsigned char numEvents;
    unsigned char isVariableInputChannels;
    unsigned char isVariableOutputChannels;
    unsigned char registryIndex;
}
```

The deviation is platform-conditional: the PS3/DecFIGS declaration names `+0x0C` and
`+0x10` as `pSpuElf`/`spuElfSize`, while the X360-specific checked-in vendor header names
those same slots `pPreProcess`/`pProcess`. The ARTIST `Voice::CreateInstance` dossier also
loads descriptor `+0x0C` and `+0x10` into the voice stage's pre-process/process callback
slots, so the X360 names are used here. The resulting complete X360 field map is:

| Offset | Width | X360 field |
|---:|---:|---|
| `+0x00` | 4 | `name` pointer |
| `+0x04` | 4 | `GetSize` callback |
| `+0x08` | 4 | `CreateInstance` callback |
| `+0x0C` | 4 | `pPreProcess` callback |
| `+0x10` | 4 | `pProcess` callback |
| `+0x14` | 4 | `pChannelMaps` |
| `+0x18` | 4 | `pParameterDescRunTime` |
| `+0x1C` | 4 | `pEventDescRunTime` |
| `+0x20` | 4 | `pPlugInDescToolSide` |
| `+0x24` | 4 | `listNode` |
| `+0x28` | 4 | `guid` / plug-in id |
| `+0x2C` | 1 | `plugInType` |
| `+0x2D` | 1 | `numConstructorParameters` |
| `+0x2E` | 1 | `numAttributes` |
| `+0x2F` | 1 | `numEvents` |
| `+0x30` | 1 | `isVariableInputChannels` |
| `+0x31` | 1 | `isVariableOutputChannels` |
| `+0x32` | 1 | `registryIndex` |
| `+0x33` | 1 | alignment byte |

The descriptor stores a `GetSize` callback, not a literal instance-size field. No
callback result is inferred in this report.

## 1. Custom descriptors

### `off_82F2D094` — GinsuPlayer

Descriptor offset:
`0x3000 + (0x82F2D094 - 0x82000000) = 0x00F30094`.

Raw 52-byte dump:

```text
00F30094: 82 0A 91 F0 82 6A 40 B8 82 6C 34 18 82 68 C1 D8
00F300A4: 82 68 C1 E8 82 F2 D0 2C 82 F2 E1 58 82 FF B9 F8
00F300B4: 00 00 00 00 00 00 00 00 47 6E 73 30 00 01 05 02
00F300C4: 00 00 00 00
BE words: 820A91F0 826A40B8 826C3418 8268C1D8 8268C1E8 82F2D02C 82F2E158 82FFB9F8 00000000 00000000 476E7330 00010502 00000000
```

| Field | Raw bytes | Interpretation / followed target |
|---|---|---|
| `name` | `82 0A 91 F0` | `0x820A91F0`; file `0x000AC1F0`: `47 69 6E 73 75 50 6C 61 79 65 72 00` = `"GinsuPlayer\0"`. |
| `GetSize` | `82 6A 40 B8` | `0x826A40B8`; file `0x006A70B8`; dossier name `rw::audio::core::GinsuPlayer::GetSize`. |
| `CreateInstance` | `82 6C 34 18` | `0x826C3418`; file `0x006C6418`; dossier name `rw::audio::core::GinsuPlayer::CreateInstance`. |
| `pPreProcess` | `82 68 C1 D8` | `0x8268C1D8`; file `0x0068F1D8`; dossier name `rw::audio::core::GinsuPlayer::PreProcess`. |
| `pProcess` | `82 68 C1 E8` | `0x8268C1E8`; file `0x0068F1E8`; dossier name `rw::audio::core::GinsuPlayer::Process`. |
| `pChannelMaps` | `82 F2 D0 2C` | Data pointer `0x82F2D02C`; file `0x00F3002C`; followed below. |
| `pParameterDescRunTime` | `82 F2 E1 58` | Data pointer `0x82F2E158`; file `0x00F31158`; followed below. |
| `pEventDescRunTime` | `82 FF B9 F8` | Data pointer `0x82FFB9F8`; file `0x00FFE9F8`; followed below. |
| `pPlugInDescToolSide` | `00 00 00 00` | Null. |
| `listNode` | `00 00 00 00` | Null initial link. |
| `guid` | `47 6E 73 30` | `0x476E7330`, ASCII `Gns0`. |
| `+0x2C..+0x2F` | `00 01 05 02` | type `0`; constructor parameters `1`; attributes `5`; events `2`. |
| `+0x30..+0x33` | `00 00 00 00` | variable input `0`; variable output `0`; registry index `0`; alignment byte `0`. |

Non-code data-pointer follow dumps:

```text
pChannelMaps          VA 0x82F2D02C, file 0x00F3002C:
00 01 FF FF 82 0A 93 C0 82 0A 93 B4 82 0A 93 AC 82 0A 93 A0 82 01 F0 44 82 0A 93 90 82 0A 93 80

pParameterDescRunTime VA 0x82F2E158, file 0x00F31158:
00 00 00 00 00 00 00 04 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00

pEventDescRunTime     VA 0x82FFB9F8, file 0x00FFE9F8:
D3 3B 0F A4 DB DC 85 7C 9B A0 58 72 02 49 1A A7 71 4B 4D 6B 89 BA 41 27 98 23 1C 04 46 F2 B5 BB
```

The last target is reported exactly as stored; its image bytes do not resemble a
zero-filled static descriptor, so no subordinate interpretation is invented.

### `off_82F2E124` — SndPlayer1_CgsStreamMod

Descriptor offset:
`0x3000 + (0x82F2E124 - 0x82000000) = 0x00F31124`.

Raw 52-byte dump:

```text
00F31124: 82 0A 91 D8 82 6A 42 10 82 6E A5 08 82 68 CD 10
00F31134: 82 6A 46 B0 82 F2 D9 1C 82 F2 FA B0 82 F2 E6 38
00F31144: 00 00 00 00 00 00 00 00 4A 53 74 72 00 01 03 05
00F31154: 00 01 00 00
BE words: 820A91D8 826A4210 826EA508 8268CD10 826A46B0 82F2D91C 82F2FAB0 82F2E638 00000000 00000000 4A537472 00010305 00010000
```

| Field | Raw bytes | Interpretation / followed target |
|---|---|---|
| `name` | `82 0A 91 D8` | `0x820A91D8`; file `0x000AC1D8`: `53 6E 64 50 6C 61 79 65 72 31 5F 43 67 73 53 74 72 65 61 6D 4D 6F 64 00` = `"SndPlayer1_CgsStreamMod\0"`. |
| `GetSize` | `82 6A 42 10` | `0x826A4210`; file `0x006A7210`; dossier name `rw::audio::core::SndPlayer1_CgsStreamMod::GetSize`. |
| `CreateInstance` | `82 6E A5 08` | `0x826EA508`; file `0x006ED508`; dossier name `rw::audio::core::SndPlayer1_CgsStreamMod::CreateInstance`. |
| `pPreProcess` | `82 68 CD 10` | `0x8268CD10`; file `0x0068FD10`; dossier name `rw::audio::core::SndPlayer1_CgsStreamMod::PreProcess`. |
| `pProcess` | `82 6A 46 B0` | `0x826A46B0`; file `0x006A76B0`; dossier name `rw::audio::core::SndPlayer1_CgsStreamMod::Process`. |
| `pChannelMaps` | `82 F2 D9 1C` | Data pointer `0x82F2D91C`; file `0x00F3091C`; followed below. |
| `pParameterDescRunTime` | `82 F2 FA B0` | Data pointer `0x82F2FAB0`; file `0x00F32AB0`; followed below. |
| `pEventDescRunTime` | `82 F2 E6 38` | Data pointer `0x82F2E638`; file `0x00F31638`; followed below. |
| `pPlugInDescToolSide` | `00 00 00 00` | Null. |
| `listNode` | `00 00 00 00` | Null initial link. |
| `guid` | `4A 53 74 72` | `0x4A537472`, ASCII `JStr`. |
| `+0x2C..+0x2F` | `00 01 03 05` | type `0`; constructor parameters `1`; attributes `3`; events `5`. |
| `+0x30..+0x33` | `00 01 00 00` | variable input `0`; variable output `1`; registry index `0`; alignment byte `0`. |

Non-code data-pointer follow dumps:

```text
pChannelMaps          VA 0x82F2D91C, file 0x00F3091C:
00 FE FF FF 00 00 00 00 3B 49 32 0E 3B C9 32 0E 3C 16 BB 99 3C 49 08 1C 3C 7B 54 A0 3C 96 D0 91

pParameterDescRunTime VA 0x82F2FAB0, file 0x00F32AB0:
00 00 00 00 00 00 00 01 3F F0 00 00 00 00 00 00 40 6F E0 00 00 00 00 00 00 00 00 00 00 00 00 00

pEventDescRunTime     VA 0x82F2E638, file 0x00F31638:
00 00 00 07 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 02 00 00 00 00 00 00 00 03 00 00 00 00
```

### `off_82F2E664` — GainArray

Descriptor offset:
`0x3000 + (0x82F2E664 - 0x82000000) = 0x00F31664`.

Raw 52-byte dump:

```text
00F31664: 82 0A 91 CC 82 68 9E 08 82 6C 3A 10 00 00 00 00
00F31674: 82 68 CD B0 82 F2 E6 60 82 F2 E6 98 00 00 00 00
00F31684: 00 00 00 00 00 00 00 00 4A 47 41 30 04 00 06 00
00F31694: 00 00 00 00
BE words: 820A91CC 82689E08 826C3A10 00000000 8268CDB0 82F2E660 82F2E698 00000000 00000000 00000000 4A474130 04000600 00000000
```

| Field | Raw bytes | Interpretation / followed target |
|---|---|---|
| `name` | `82 0A 91 CC` | `0x820A91CC`; file `0x000AC1CC`: `47 61 69 6E 41 72 72 61 79 00` = `"GainArray\0"`. |
| `GetSize` | `82 68 9E 08` | `0x82689E08`; file `0x0068CE08`; dossier name `CgsSound::Playback::Plugins::GainArray::GetSize`. |
| `CreateInstance` | `82 6C 3A 10` | `0x826C3A10`; file `0x006C6A10`; dossier name `CgsSound::Playback::Plugins::GainArray::CreateInstance`. |
| `pPreProcess` | `00 00 00 00` | Null. |
| `pProcess` | `82 68 CD B0` | `0x8268CDB0`; file `0x0068FDB0`; dossier name `CgsSound::Playback::Plugins::GainArray::Process`. |
| `pChannelMaps` | `82 F2 E6 60` | Data pointer `0x82F2E660`; file `0x00F31660`; followed below. |
| `pParameterDescRunTime` | `82 F2 E6 98` | Data pointer `0x82F2E698`; file `0x00F31698`; followed below. |
| `pEventDescRunTime` | `00 00 00 00` | Null. |
| `pPlugInDescToolSide` | `00 00 00 00` | Null. |
| `listNode` | `00 00 00 00` | Null initial link. |
| `guid` | `4A 47 41 30` | `0x4A474130`, ASCII `JGA0`. |
| `+0x2C..+0x2F` | `04 00 06 00` | type `4`; constructor parameters `0`; attributes `6`; events `0`. |
| `+0x30..+0x33` | `00 00 00 00` | variable input `0`; variable output `0`; registry index `0`; alignment byte `0`. |

Non-code data-pointer follow dumps:

```text
pChannelMaps          VA 0x82F2E660, file 0x00F31660:
FD FC FF FF 82 0A 91 CC 82 68 9E 08 82 6C 3A 10 00 00 00 00 82 68 CD B0 82 F2 E6 60 82 F2 E6 98

pParameterDescRunTime VA 0x82F2E698, file 0x00F31698:
00 00 00 00 00 00 00 01 C0 F8 6A 00 00 00 00 00 40 F8 6A 00 00 00 00 00 00 00 00 00 00 00 00 00
```

## 2. Vendor descriptors returned by standard getters

### `off_82F8C7A8` — Dac

Descriptor offset:
`0x3000 + (0x82F8C7A8 - 0x82000000) = 0x00F8F7A8`.

Raw 52-byte dump:

```text
00F8F7A8: 82 15 D0 80 82 B9 6C B0 82 BA 24 A0 00 00 00 00
00F8F7B8: 82 B9 72 50 82 F8 C6 7C 82 F8 C6 80 82 F8 C7 80
00F8F7C8: 00 00 00 00 00 00 00 00 44 61 63 30 04 00 03 05
00F8F7D8: 00 00 00 00
BE words: 8215D080 82B96CB0 82BA24A0 00000000 82B97250 82F8C67C 82F8C680 82F8C780 00000000 00000000 44616330 04000305 00000000
```

| Field | Raw bytes | Interpretation / followed target |
|---|---|---|
| `name` | `82 15 D0 80` | `0x8215D080`; file `0x00160080`: `44 61 63 00` = `"Dac\0"`. |
| `GetSize` | `82 B9 6C B0` | `0x82B96CB0`; file `0x00B99CB0`; dossier name `rw::audio::core::Dac::GetSize`. |
| `CreateInstance` | `82 BA 24 A0` | `0x82BA24A0`; file `0x00BA54A0`; dossier name `rw::audio::core::Dac::CreateInstance`. |
| `pPreProcess` | `00 00 00 00` | Null. |
| `pProcess` | `82 B9 72 50` | `0x82B97250`; file `0x00B9A250`; dossier name `rw::audio::core::Dac::Process`. |
| `pChannelMaps` | `82 F8 C6 7C` | Data pointer `0x82F8C67C`; file `0x00F8F67C`; followed below. |
| `pParameterDescRunTime` | `82 F8 C6 80` | Data pointer `0x82F8C680`; file `0x00F8F680`; followed below. |
| `pEventDescRunTime` | `82 F8 C7 80` | Data pointer `0x82F8C780`; file `0x00F8F780`; followed below. |
| `pPlugInDescToolSide` | `00 00 00 00` | Null. |
| `listNode` | `00 00 00 00` | Null initial link. |
| `guid` | `44 61 63 30` | `0x44616330`, ASCII `Dac0`. |
| `+0x2C..+0x2F` | `04 00 03 05` | type `4`; constructor parameters `0`; attributes `3`; events `5`. |
| `+0x30..+0x33` | `00 00 00 00` | variable input `0`; variable output `0`; registry index `0`; alignment byte `0`. |

Non-code data-pointer follow dumps:

```text
pChannelMaps          VA 0x82F8C67C, file 0x00F8F67C:
06 00 FF FF 00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 40 14 00 00 00 00 00 00 00 00 00 00

pParameterDescRunTime VA 0x82F8C680, file 0x00F8F680:
00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 40 14 00 00 00 00 00 00 00 00 00 00 00 00 00 00

pEventDescRunTime     VA 0x82F8C780, file 0x00F8F780:
00 00 00 03 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00
```

### `off_82F901C4` — SndPlayer1

Descriptor offset:
`0x3000 + (0x82F901C4 - 0x82000000) = 0x00F931C4`.

Raw 52-byte dump:

```text
00F931C4: 82 17 44 E4 82 BA 02 20 82 BA 6C 80 82 B9 C2 D8
00F931D4: 82 BA 05 68 82 F9 01 90 82 F9 10 E0 82 F9 01 94
00F931E4: 00 00 00 00 00 00 00 00 53 6E 50 31 00 01 03 06
00F931F4: 00 01 00 00
BE words: 821744E4 82BA0220 82BA6C80 82B9C2D8 82BA0568 82F90190 82F910E0 82F90194 00000000 00000000 536E5031 00010306 00010000
```

| Field | Raw bytes | Interpretation / followed target |
|---|---|---|
| `name` | `82 17 44 E4` | `0x821744E4`; file `0x001774E4`: `53 6E 64 50 6C 61 79 65 72 31 00` = `"SndPlayer1\0"`. |
| `GetSize` | `82 BA 02 20` | `0x82BA0220`; file `0x00BA3220`; dossier name `rw::audio::core::SndPlayer1::GetSize`. |
| `CreateInstance` | `82 BA 6C 80` | `0x82BA6C80`; file `0x00BA9C80`; dossier name `rw::audio::core::SndPlayer1::CreateInstance`. |
| `pPreProcess` | `82 B9 C2 D8` | `0x82B9C2D8`; file `0x00B9F2D8`; **no dossier entry found** at `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B9C2D8.json`. |
| `pProcess` | `82 BA 05 68` | `0x82BA0568`; file `0x00BA3568`; dossier name `rw::audio::core::SndPlayer1::Process`. |
| `pChannelMaps` | `82 F9 01 90` | Data pointer `0x82F90190`; file `0x00F93190`; followed below. |
| `pParameterDescRunTime` | `82 F9 10 E0` | Data pointer `0x82F910E0`; file `0x00F940E0`; followed below. |
| `pEventDescRunTime` | `82 F9 01 94` | Data pointer `0x82F90194`; file `0x00F93194`; followed below. |
| `pPlugInDescToolSide` | `00 00 00 00` | Null. |
| `listNode` | `00 00 00 00` | Null initial link. |
| `guid` | `53 6E 50 31` | `0x536E5031`, ASCII `SnP1`. |
| `+0x2C..+0x2F` | `00 01 03 06` | type `0`; constructor parameters `1`; attributes `3`; events `6`. |
| `+0x30..+0x33` | `00 01 00 00` | variable input `0`; variable output `1`; registry index `0`; alignment byte `0`. |

Non-code data-pointer follow dumps:

```text
pChannelMaps          VA 0x82F90190, file 0x00F93190:
00 FE FF FF 00 00 00 07 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 02 00 00 00 00 00 00 00 03

pParameterDescRunTime VA 0x82F910E0, file 0x00F940E0:
00 00 00 00 00 00 00 01 3F F0 00 00 00 00 00 00 40 6F E0 00 00 00 00 00 00 00 00 00 00 00 00 00

pEventDescRunTime     VA 0x82F90194, file 0x00F93194:
00 00 00 07 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 02 00 00 00 00 00 00 00 03 00 00 00 00
```

### `off_82F902E0` — SubMix

Descriptor offset:
`0x3000 + (0x82F902E0 - 0x82000000) = 0x00F932E0`.

Raw 52-byte dump:

```text
00F932E0: 82 17 B0 90 82 B9 82 F0 82 BA 46 80 00 00 00 00
00F932F0: 82 B9 C4 80 82 F9 02 BC 82 F9 02 C0 00 00 00 00
00F93300: 00 00 00 00 00 00 00 00 53 75 62 30 04 01 00 00
00F93310: 00 00 00 00
BE words: 8217B090 82B982F0 82BA4680 00000000 82B9C480 82F902BC 82F902C0 00000000 00000000 00000000 53756230 04010000 00000000
```

| Field | Raw bytes | Interpretation / followed target |
|---|---|---|
| `name` | `82 17 B0 90` | `0x8217B090`; file `0x0017E090`: `53 75 62 4D 69 78 00` = `"SubMix\0"`. |
| `GetSize` | `82 B9 82 F0` | `0x82B982F0`; file `0x00B9B2F0`; dossier name `rw::audio::core::SubMix::GetSize`. |
| `CreateInstance` | `82 BA 46 80` | `0x82BA4680`; file `0x00BA7680`; **no dossier entry found** at `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82BA4680.json`. |
| `pPreProcess` | `00 00 00 00` | Null. |
| `pProcess` | `82 B9 C4 80` | `0x82B9C480`; file `0x00B9F480`; dossier name `rw::audio::core::SubMix::Process`. |
| `pChannelMaps` | `82 F9 02 BC` | Data pointer `0x82F902BC`; file `0x00F932BC`; followed below. |
| `pParameterDescRunTime` | `82 F9 02 C0` | Data pointer `0x82F902C0`; file `0x00F932C0`; followed below. |
| `pEventDescRunTime` | `00 00 00 00` | Null. |
| `pPlugInDescToolSide` | `00 00 00 00` | Null. |
| `listNode` | `00 00 00 00` | Null initial link. |
| `guid` | `53 75 62 30` | `0x53756230`, ASCII `Sub0`. |
| `+0x2C..+0x2F` | `04 01 00 00` | type `4`; constructor parameters `1`; attributes `0`; events `0`. |
| `+0x30..+0x33` | `00 00 00 00` | variable input `0`; variable output `0`; registry index `0`; alignment byte `0`. |

Non-code data-pointer follow dumps:

```text
pChannelMaps          VA 0x82F902BC, file 0x00F932BC:
00 FD FF FF 00 00 00 00 00 00 00 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00

pParameterDescRunTime VA 0x82F902C0, file 0x00F932C0:
00 00 00 00 00 00 00 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
```

## 3. Float constants

Each conversion was independently made from the four bytes at the computed file
offset as a big-endian IEEE-754 binary32.

| Symbol | Offset calculation | Raw bytes / word | Exact f32 value |
|---|---|---|---|
| `flt_82001C98` | `0x3000 + (0x82001C98 - 0x82000000) = 0x00004C98` | `3F 80 00 00` / `0x3F800000` | `1.0` |
| `flt_82001D9C` | `0x3000 + (0x82001D9C - 0x82000000) = 0x00004D9C` | `40 00 00 00` / `0x40000000` | `2.0` |
| `flt_82001CC0` | `0x3000 + (0x82001CC0 - 0x82000000) = 0x00004CC0` | `00 00 00 00` / `0x00000000` | `+0.0` |
| `flt_82F2E758` | `0x3000 + (0x82F2E758 - 0x82000000) = 0x00F31758` | `7F 7F FF FF` / `0x7F7FFFFF` | `340282346638528859811704183484516925440` (`3.4028234663852886e+38`, maximum finite f32) |

Thus the SpliceManager stage-0 values are mono `1.0` and stereo `2.0`. The
RootInputBuffer default stamps are `+0.0` and maximum finite f32.

## 4. Constructor plug-in-id FourCCs

The task text calls these “four” ids but lists five; all five are covered. For each,
the four big-endian bytes were also located as a unique contiguous occurrence in the
XEX, making the decode directly traceable to an image offset.

| Value | XEX file offset containing bytes | Raw bytes | ASCII | Matching header symbol |
|---|---:|---|---|---|
| `0x53656E30` | `0x00F92F88` (VA `0x82F8FF88`) | `53 65 6E 30` | `Sen0` | Send plug-in `GUID`: DecFIGS `plugins/send.h:25` gives `GUID = 1399156272`; the current checked-in `Send.cpp` also identifies the value, but no current checked-in vendor **header** defines a named constant. |
| `0x53756230` | `0x00F93308` (VA `0x82F90308`) | `53 75 62 30` | `Sub0` | SubMix plug-in `GUID`: DecFIGS `plugins/submix.h:31` gives `GUID = 1400201776`; no matching named constant was found in the current checked-in vendor headers. |
| `0x536E5031` | `0x00F931EC` (VA `0x82F901EC`) | `53 6E 50 31` | `SnP1` | SndPlayer1 plug-in `GUID`: DecFIGS `plugins/sndplayer1.h:109` gives `GUID = 1399738417`; no matching named constant was found in the current checked-in vendor headers. |
| `0x52737030` | `0x00F92908` (VA `0x82F8F908`) | `52 73 70 30` | `Rsp0` | Resample plug-in `GUID`: DecFIGS `plugins/resample.h:5` gives `GUID = 1383297072`; no matching named constant was found in the current checked-in vendor headers. |
| `0x506E3231` | `0x00F92168` (VA `0x82F8F168`) | `50 6E 32 31` | `Pn21` | `rw::audio::core::Pan2D1::KU_GUID`, defined as `1349399089u` in `b5-decomp/vendor/renderware/include/rw/audio/core/plugins/Pan2D1.h:75-80`; DecFIGS `plugins/pan2d1.h:2` names the original generic `GUID`. |

The ASCII conversion is byte-for-byte: `53 65 6E 30` → `S e n 0`,
`53 75 62 30` → `S u b 0`, `53 6E 50 31` → `S n P 1`,
`52 73 70 30` → `R s p 0`, and `50 6E 32 31` → `P n 2 1`.

## Verification checklist

- Re-dumped every descriptor as 13 big-endian words = 52 bytes = the vendor-header
  `sizeof=52`; each dump runs through offset `+0x33`.
- Re-read every non-null name pointer from the XEX through its terminating NUL.
- Looked up every non-null callback address only by its exact
  `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x<ADDR>.json` path. Two exact files are absent
  and are explicitly reported as “no dossier entry found.”
- Followed every non-null non-code descriptor pointer to its computed image offset and
  recorded a raw target preview; no subordinate record semantics were guessed.
- Re-read every float's four bytes and converted each independently as big-endian f32.
- Re-derived every listed FourCC from its four bytes and confirmed each byte sequence
  occurs uniquely in the XEX at the reported file offset.
