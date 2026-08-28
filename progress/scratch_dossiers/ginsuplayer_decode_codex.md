# `rw::audio::core::GinsuPlayer` — X360 ARTIST decode dossier

Status: complete assembly-grounded research/decode; no source implementation was changed.

Target image: `BURNOUT_X360_ARTIST.XEX` (big-endian PowerPC).  All virtual and callback
signatures below were checked at their dispatch sites, not inferred from Hex-Rays prototypes.
The per-function JSON `assembly` fields are the behavioral authority.  Where the exporter has
no JSON (`CycleToSample` and `StopHandler`), the instructions were decoded directly from
`IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex` with
`file_off = 0x3000 + VA - 0x82000000` in big-endian PPC mode.

Inclusive instruction ranges are used throughout.  Adjacent rows meet at the next four-byte
address, and non-code words are called out as padding.  Consequently the range tables cover
every instruction (and every exported padding word) in each decoded body; they are not selected
snippets.

## Result in one paragraph

`GinsuPlayer` is a source-stage, mono granular engine-sound synthesizer.  A play event binds a
`Gnsu2` blob, copies its two interpolation tables into allocation-tail storage, and points at a
19-byte-per-32-sample predictive-coded stream.  `Process` maps requested engine frequency to a
source position, periodically chooses a deterministic random cycle within an attribute-controlled
window, phase-corrects that choice, crossfades over 0.5 ms, and otherwise streams in chunks whose
input length is capped at 64 samples.  `DecodeBlock` expands each 19-byte record to 32 floats using
one of four two-tap predictors and one of thirteen signed-nibble scale rows.  `GetSamples` converts
the decoded 16-bit-scale values to `[-1,1)` floats and linearly resamples with 16.16 fixed-point
phase.  The final buffer becomes the Mixer's source by swapping `mpSrcBuffer`/`mpDstBuffer`.

## Existing reconstruction inventory

There is **no** existing `rw::audio::core::GinsuPlayer`, `GinsuSynthData`, or plug-in home under
`b5-decomp/src` or the RenderWare vendor audio sources.  The direct integration gap is already
recorded in
`GameShared/GameClasses/Sound/Playback/RWAC/CgsGenericRwacFactory.cpp`: its registration list marks
`GinsuPlayer` / `off_82F2D094` deferred.  The ARTIST factory body at `0x826C1984..0x826C1990`
loads that descriptor and passes it to `PlugInRegistry::RegisterPlugInRunTime` immediately after
the stock `SndPlayer1` registration.

What does exist:

* Game-side users: `BrnSingleGinsuEffect`, `BrnDualGinsuEffect`,
  `BrnDualGinsuExhaustEffect`, `BrnHybridEngineControl`, and `BrnHybridExhaustControl` under
  `GameSource/Sound/Vehicles/Engines`; other `grep -ri ginsu` hits are callers/state/control
  references, not the granular player.
* `CgsGenericRwacCommands.{h,cpp}` has command tag 10,
  `RwacCommandGinsuAttachDataParameters`, currently represented as an opaque `uintptr_t
  maOperand`; this is upstream game command plumbing, not the plug-in's deferred event record.
* `CgsGinsuWaveContentResourceType.{h,cpp}` exists and returns resource type ID `40993`; it does
  not decode or play the content.

## Descriptor and callback ABI

Raw descriptor `off_82F2D094`, file offset `0x00F30094`:

```
82 0A 91 F0  82 6A 40 B8  82 6C 34 18  82 68 C1 D8
82 68 C1 E8  82 F2 D0 2C  82 F2 E1 58  82 FF B9 F8
00 00 00 00  00 00 00 00  47 6E 73 30  00 01 05 02
00 00 00 00
```

This decodes as:

| `PlugInDescRunTime` offset | value | meaning |
|---:|---:|---|
| `+0x00` | `0x820A91F0` | `"GinsuPlayer"` |
| `+0x04` | `0x826A40B8` | `GetSize` |
| `+0x08` | `0x826C3418` | `CreateInstance` |
| `+0x0C` | `0x8268C1D8` | `PreProcess` |
| `+0x10` | `0x8268C1E8` | `Process` |
| `+0x14` | `0x82F2D02C` | channel map bytes `00 01 FF FF` (one `0 -> 1` map, terminator) |
| `+0x18` | `0x82F2E158` | five attribute runtime records |
| `+0x1C` | `0x82FFB9F8` | two event runtime records (runtime-mutated storage; see BLOCKED note) |
| `+0x20,+0x24` | `0` | no toolside descriptor, no next descriptor |
| `+0x28` | `47 6E 73 30` | fourcc/GUID `'Gns0'` = `1198420784` |
| `+0x2C..+0x31` | `0,1,5,2,0,0` | `plugInType=SOURCE`, one constructor parameter, five attributes, two events, fixed input/output |
| `+0x32,+0x33` | `0,0` | sequence/pad |

The callback signatures, proven at the generic dispatch sites, are:

```cpp
static unsigned GinsuPlayer::GetSize(const VoiceStageConfig* config);
// Voice::CreateInstance: r3 = &VoiceStageConfig, indirect call through desc+4.

static bool GinsuPlayer::CreateInstance(GinsuPlayer* storage,
                                        const PlayParams* constructorParams);
// PlugIn::CreateInstance: r3 = allocated PlugIn storage, r4 = config->pConstructorParams.

static int GinsuPlayer::PreProcess(GinsuPlayer* self, Mixer* mixer,
                                   bool isLastInput, int requestedSamples);
// Mixer::ProcessInputPlugIns: r3=self, r4=Mixer, r5=bool, r6=request count.

static BufferStatus GinsuPlayer::Process(GinsuPlayer* self, Mixer* mixer,
                                         bool isLastInput);
// r3=self, r4=Mixer, r5=bool.  Return 0=UNAVAILABLE, 1=AVAILABLE.
```

`VoiceStageConfig` is the vendor `PlugInConfig`: on X360
`{ PlayParams* +0x00; PlugInHandle +0x04; u8 outputChannels +0x08; }`.  Only the first field is
read by `GetSize`; `CreateInstance` receives that first field, not the config object.

## Exact console object/data layout

These offsets are evidence labels for the 32-bit console image.  They must not be frozen as a
host packed layout.

### `GinsuPlayer` (`sizeof == 0x1D0` on X360)

| X360 offset | width | faithful name / evidence |
|---:|---:|---|
| `+0x00` | 4 | vptr installed as `off_820AE168` |
| `+0x04` | 4 | `PlugIn::mpSystem` |
| `+0x08` | 4 | `PlugIn::mpVoice` |
| `+0x0C` | 4 | `PlugIn::mpAttribute`; set to `self+0x28` |
| `+0x10..+0x21` | base | descriptor/latency/decay/ticks/input/output-channel fields; output channel is byte `+0x21` |
| `+0x28` | 4 | `mAttribute[0].value`: requested frequency, default `1000.0f` |
| `+0x30` | 4 | `mAttribute[1].value`: random jump-span in cycles, default `0` |
| `+0x38` | 4 | `mAttribute[2].value`: bound source sample rate (readback), initially `0` |
| `+0x40` | 4 | `mAttribute[3].value`: bound minimum frequency (readback), initially `0` |
| `+0x48` | 4 | `mAttribute[4].value`: bound maximum frequency (readback), initially `0` |
| `+0x50` | 1 | `mPlaying` |
| `+0x54` | 4 | `mOutputSamplesRequested` — a full word, unlike `SndPlayer1 +0x1C0` halfword |
| `+0x58` | `0x154` | `mSynthData` |
| `+0x1AC` | 4 | `pGinFile` |
| `+0x1B0` | 4 | `mSampleRate` |
| `+0x1B4` | 4 | `mPrevSampleRate` |
| `+0x1B8` | 4 | `mNoJumpSize = int(sampleRate * 0.011f)`; initialized but not read by this ARTIST `Process` |
| `+0x1BC` | 4 | `mOverlapSize = int(sampleRate * 0.0005f)` |
| `+0x1C0` | 4 | `mPlaybackPos` (decoded-input sample index) |
| `+0x1C4` | 4 | `mRandomSeed`, initialized `0x12345678` |
| `+0x1C8` | 8 | `mNextJumpTime` |

### `GinsuSynthData` relative to `player+0x58`

| synth offset | player offset | width | faithful name |
|---:|---:|---:|---|
| `+0x00` | `+0x58` | 152 | `mOldDataBlock[8 * 19]` |
| `+0x98` | `+0xF0` | 4 | `mOldDataBlockIndex` |
| `+0x9C` | `+0xF4` | 4 | `mTempStoreBlockIndex` |
| `+0xA0` | `+0xF8` | 4 | `mpTempStore` |
| `+0xA4` | `+0xFC` | 4 | `mLastInputSample` |
| `+0xA8` | `+0x100` | 4 | `mCycleCount` |
| `+0xAC` | `+0x104` | 4 | `mMinFrequency` |
| `+0xB0` | `+0x108` | 4 | `mMaxFrequency` |
| `+0xB4` | `+0x10C` | 4 | `mSegCount` |
| `+0xB8` | `+0x110` | 4 | `mSampleCount` |
| `+0xBC` | `+0x114` | 4 | `mSampleRate` |
| `+0xC0` | `+0x118` | 4 | `mFreqOffset` — relative offset from this synth object, not a serialized pointer |
| `+0xC4` | `+0x11C` | 4 | `mCycleOffset` — relative offset from this synth object |
| `+0xC8` | `+0x120` | 4 | `mSampleData` pointer into the bound blob |
| `+0xCC` | `+0x124` | 4 | `mMinPeriod` (minimum adjacent cycle-table delta, stored as float) |
| `+0xD0` | `+0x128` | 4 | `mCurrentBlock` |
| `+0xD4` | `+0x12C` | 128 | `mSample[32]` decoded block |

The serialized `Gnsu2` header is 32 bytes:

```cpp
struct GinsuDataLayoutOnDisk {
    char id[4];             // +0x00 "Gnsu"
    char version[2];        // +0x04 begins with '2'
    uint16_t endianDone;    // +0x06
    float minFrequency;     // +0x08
    float maxFrequency;     // +0x0C
    int32_t segCount;       // +0x10
    int32_t cycleCount;     // +0x14
    int32_t sampleCount;    // +0x18
    int32_t sampleRate;     // +0x1C
    // int32_t frequencySamples[segCount + 1];
    // int32_t cycleSamples[cycleCount + 1];
    // uint8_t encodedSamples[]; // 19 bytes per 32 samples
};
```

No C++ `#pragma pack` is warranted: this is an explicit serialized-byte layout.  Decode fields at
fixed serialized offsets, then store native host fields.

## Raw constants and tables

Every non-address rodata load used by the decoded functions is listed here.  Offsets are
recomputed with the user's formula, and bytes are raw big-endian image bytes.

| VA | file offset | bytes | value / users |
|---:|---:|---|---|
| `82001C98` | `00004C98` | `3F 80 00 00` | `1.0f`; `Process` fades |
| `82001CA8` | `00004CA8` | `00 00 00 00 00 00 00 00` | `0.0` double; `PlayHandler` |
| `82001CC0` | `00004CC0` | `00 00 00 00` | `0.0f`; ctor/bind/math/helpers |
| `82001D9C` | `00004D9C` | `40 00 00 00` | `2.0f`; `Process` jump-window centering |
| `82001DA0` | `00004DA0` | `3F 00 00 00` | `0.5f`; interpolation/rounding |
| `82004A28` | `00007A28` | `42 F0 00 00` | `120.0f`; cycles/minute conversion |
| `82009E10` | `0000CE10` | `44 7A 00 00` | `1000.0f`; default requested frequency |
| `82020A7C` | `00023A7C` | `42 80 00 00` | `64.0f`; steady-state input cap |
| `8207ACF0` | `0007DCF0` | `37 80 00 00` | `1/65536.0f`; 16.16 resample fraction |
| `820AA7BC` | `000AD7BC` | `3C 34 39 58` | `0.01099999994f`; no-jump sample count |
| `820AA808` | `000AD808` | `47 3B 80 00` | `48000.0f`; initial/previous rate |
| `820ADB88` | `000B0B88` | `30 00 00 00` | `2^-31`; random residue normalization |
| `820ADBE8` | `000B0BE8` | `38 00 00 00` | `1/32768.0f`; decoded sample scale |
| `820ADBF0` | `000B0BF0` | `3F 84 7A E1 40 00 00 00` | double `0.0099999997764825821`; jump timer step |
| `820ADBF8` | `000B0BF8` | `3A 03 12 6F` | `0.00050000002374872565f`; overlap duration |

Addressed byte/string data:

| VA | file offset | raw bytes / meaning |
|---:|---:|---|
| `820A91F0` | `000AC1F0` | `47 69 6E 73 75 50 6C 61 79 65 72 00` = `"GinsuPlayer"` |
| `820ADB90` | `000B0B90` | NUL-terminated `"GinsuSynthData::GetSamples FAILED! Startsample=%d numInputSamples=%d mSampleCount=%d\n"` |
| `820AE168` | `000B1168` | vtable words `8284CB38 826C3498 827E2F38 826AA938` |
| `820AA810` | `000AD810` | base-vtable words used by destructor: `8284CB38 8284CB38 827E2F38 82680418` |

Predictor tables used only by `DecodeBlock`:

| VA | file offset | raw BE words | float values |
|---:|---:|---|---|
| `82F2E218` | `00F31218` | `00000000 3F700000 3FE60000 3FC40000` | `{0, 0.9375, 1.796875, 1.53125}` (`coef0`) |
| `82F2E228` | `00F31228` | `00000000 00000000 BF500000 BF5C0000` | `{0, 0, -0.8125, -0.859375}` (`coef1`) |

The 256-float nibble codebook begins at VA `82F2E238`, file offset `00F31238`, and occupies
`0x400` bytes.  The complete value rule, confirmed against every raw word, is:

```text
codebook[shift][nibble] = signed4(nibble) * 2^(12-shift), shift 0..12
codebook[shift][nibble] = 0,                         shift 13..15
signed4(n) = n for n<8, otherwise n-16
address = 82F2E238 + 4*(16*shift+n)
file_off = 00F31238 + 4*(16*shift+n)
```

For byte-exact reproducibility, the 16 BE words in each row are:

```text
s00 00000000 45800000 46000000 46400000 46800000 46A00000 46C00000 46E00000 C7000000 C6E00000 C6C00000 C6A00000 C6800000 C6400000 C6000000 C5800000
s01 00000000 45000000 45800000 45C00000 46000000 46200000 46400000 46600000 C6800000 C6600000 C6400000 C6200000 C6000000 C5C00000 C5800000 C5000000
s02 00000000 44800000 45000000 45400000 45800000 45A00000 45C00000 45E00000 C6000000 C5E00000 C5C00000 C5A00000 C5800000 C5400000 C5000000 C4800000
s03 00000000 44000000 44800000 44C00000 45000000 45200000 45400000 45600000 C5800000 C5600000 C5400000 C5200000 C5000000 C4C00000 C4800000 C4000000
s04 00000000 43800000 44000000 44400000 44800000 44A00000 44C00000 44E00000 C5000000 C4E00000 C4C00000 C4A00000 C4800000 C4400000 C4000000 C3800000
s05 00000000 43000000 43800000 43C00000 44000000 44200000 44400000 44600000 C4800000 C4600000 C4400000 C4200000 C4000000 C3C00000 C3800000 C3000000
s06 00000000 42800000 43000000 43400000 43800000 43A00000 43C00000 43E00000 C4000000 C3E00000 C3C00000 C3A00000 C3800000 C3400000 C3000000 C2800000
s07 00000000 42000000 42800000 42C00000 43000000 43200000 43400000 43600000 C3800000 C3600000 C3400000 C3200000 C3000000 C2C00000 C2800000 C2000000
s08 00000000 41800000 42000000 42400000 42800000 42A00000 42C00000 42E00000 C3000000 C2E00000 C2C00000 C2A00000 C2800000 C2400000 C2000000 C1800000
s09 00000000 41000000 41800000 41C00000 42000000 42200000 42400000 42600000 C2800000 C2600000 C2400000 C2200000 C2000000 C1C00000 C1800000 C1000000
s10 00000000 40800000 41000000 41400000 41800000 41A00000 41C00000 41E00000 C2000000 C1E00000 C1C00000 C1A00000 C1800000 C1400000 C1000000 C0800000
s11 00000000 40000000 40800000 40C00000 41000000 41200000 41400000 41600000 C1800000 C1600000 C1400000 C1200000 C1000000 C0C00000 C0800000 C0000000
s12 00000000 3F800000 40000000 40400000 40800000 40A00000 40C00000 40E00000 C1000000 C0E00000 C0C00000 C0A00000 C0800000 C0400000 C0000000 BF800000
s13 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
s14 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
s15 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
```

Immediate (non-rodata) algorithm constants include record size `19`, decoded block size `32`, old
cache size `8*19=152`, fixed-point unit `0x10000`, RNG xor `0x1D872B41`, modulus
`0x7FFFFFFF`, seed `0x12345678`, and steady input cap `64`.

## Installed vtable and events

### Vtable `off_820AE168`

The raw four-word run is followed immediately by a different vtable, so there are exactly four
slots.  DecFIGS supplies the base virtual names; the ARTIST slot bodies supply behavior.

| slot | target | exact signature | body / instruction coverage | member data | rodata |
|---:|---:|---|---|---|---|
| 0 | `8284CB38` | `void ReleaseEvent()` | `8284CB38` `blr`; `8284CB3C` zero padding | none | none |
| 1 | `826C3498` | `void EventEvent(int event, void* params)` | full dispatch below | `+4` System | handler addresses |
| 2 | `827E2F38` | `unsigned GetPpuTicksEvent() const` | `827E2F38` `li r3,0`; `827E2F3C` `blr` | none | none |
| 3 | `826AA938` | vector deleting destructor (`~GinsuPlayer()` source-level) | full body below | vptr | base vtable `820AA810` |

The no-op/zero bodies are ICF-folded and IDA labels them as unrelated users; the slot identity is
fixed by the `PlugIn` vtable shape, not by those incidental folded names.

Source-level sketches for slots 0 and 2 are exact:

```cpp
void GinsuPlayer::ReleaseEvent() {}
unsigned GinsuPlayer::GetPpuTicksEvent() const { return 0; }
```

### `EventEvent @ 0x826C3498`

Exact signature: `void GinsuPlayer::EventEvent(int event, void* parameterBlock)`.  Although IDA
prints `int`, the DecFIGS virtual and indirect call both make the return `void`; the final `r3`
value is incidental.

| inclusive instructions | complete effect |
|---|---|
| `826C3498..826C34A0` | load `System*` from `self+4`; compare `event` with zero |
| `826C34A4..826C34D0` | event 0: reserve 12 bytes at `system+0x20 + cursor`; cursor is word `system+0x10B8`; write `{PlayHandler, self, *(void**)parameterBlock}` |
| `826C34D4..826C34F8` | every nonzero event: reserve 8 bytes and write `{StopHandler, self}` |
| `826C34FC` | exported zero padding |

Parameter and deferred-record layouts are therefore exact:

```cpp
struct PlayParams   { void* pGinFile; };  // constructor parameter and event-0 block
struct PlayCommand  { int (*handler)(PlayCommand*); GinsuPlayer* player; void* pGinFile; };
struct StopCommand  { int (*handler)(StopCommand*); GinsuPlayer* player; };
// X360 sizes: 12 and 8.  Handler returns are those same sizes.
```

Implementation-grade host sketch (the ring API should perform wrapping/space management already
owned by `System`; this illustrates the exact bytes queued):

```cpp
void GinsuPlayer::EventEvent(int event, void* block)
{
    if (event == 0) {
        auto* c = mpSystem->AllocateDeferred<PlayCommand>();
        c->handler = &GinsuPlayer::PlayHandler;
        c->player = this;
        c->pGinFile = static_cast<PlayParams*>(block)->pGinFile;
    } else {
        auto* c = mpSystem->AllocateDeferred<StopCommand>();
        c->handler = &GinsuPlayer::StopHandler;
        c->player = this;
    }
}
```

There is deliberately no `event == 1` comparison: **all** nonzero IDs dispatch stop.

### `StopHandler @ 0x8268B1B8` (raw-XEX body)

Exact signature: `static int StopHandler(StopCommand* command)`.  The return is the ring-cursor
advance consumed by the deferred-command runner.

| inclusive instructions | complete effect |
|---|---|
| `8268B1B8..8268B1C8` | load `command->player` at `+4`, store byte zero at player `+0x50`, return `8` |
| `8268B1CC` | zero padding |

```cpp
int GinsuPlayer::StopHandler(StopCommand* c)
{
    c->player->mPlaying = false;
    return sizeof(StopCommand); // 8 X360; 16 with two host pointers
}
```

### `PlayHandler @ 0x826A4100`

Exact signature: `static int PlayHandler(PlayCommand* command)`.

| inclusive instructions | complete effect |
|---|---|
| `826A4100..826A4114` | save nonvolatiles; load player from command `+4`; set `mPlaying=1` |
| `826A4118..826A4130` | store command `+8` in `pGinFile`; call `GetTotalTableSize` (including its endian side effect) |
| `826A4134..826A4150` | compute allocation tail as `(player+0x1D7)&~7`; call `mSynthData.BindToData(file, tail)` |
| `826A4154..826A4178` | fetch bound rate; set previous rate `48000`; set current float rate; if integer rate is zero branch to failure |
| `826A417C..826A41A0` | publish attributes 2/3/4 = rate/min/max; old/temp indices `-1`; temp pointer zero |
| `826A41A4..826A41D4` | playback zero; compute no-jump and overlap sample counts; seed `0x12345678`; next-jump double zero |
| `826A41D8..826A41F4` | zero exactly 152 bytes of old-data cache; clear temp pointer; return record advance `12` |
| `826A41F8..826A4208` | zero-rate path returns `0`; common restore |

Rodata: `48000.0f @820AA808`, `0.011f @820AA7BC`, `0.0005f @820ADBF8`, and double zero
`@82001CA8`.  Player/synth offsets are in the layout tables above.

```cpp
int GinsuPlayer::PlayHandler(PlayCommand* c)
{
    GinsuPlayer& p = *c->player;
    p.mPlaying = true;
    p.pGinFile = c->pGinFile;
    (void)GinsuSynthData::GetTotalTableSize(p.pGinFile); // may endian-adjust in place
    auto* tail = AlignUp(reinterpret_cast<std::byte*>(&p) + sizeof(GinsuPlayer), 8);
    (void)p.mSynthData.BindToData(p.pGinFile,
                                  reinterpret_cast<uintptr_t>(tail));

    const int rate = p.mSynthData.mSampleRate;
    p.mPrevSampleRate = 48000.0f;
    p.mSampleRate = static_cast<float>(rate);
    if (rate == 0)
        return 0; // exact ARTIST behavior; cursor does not advance on malformed content

    p.mAttribute[2].value = p.mSampleRate;
    p.mAttribute[3].value = p.mSynthData.mMinFrequency;
    p.mAttribute[4].value = p.mSynthData.mMaxFrequency;
    p.mSynthData.mOldDataBlockIndex = -1;
    p.mSynthData.mTempStoreBlockIndex = -1;
    p.mSynthData.mpTempStore = nullptr;
    p.mPlaybackPos = 0;
    p.mNoJumpSize = static_cast<int>(p.mSampleRate * 0.011f);
    p.mRandomSeed = 0x12345678;
    p.mNextJumpTime = 0.0;
    p.mOverlapSize = static_cast<int>(p.mSampleRate * 0.0005f);
    std::memset(p.mSynthData.mOldDataBlock, 0, 152);
    return sizeof(PlayCommand); // 12 X360; host pointer-width size on PC
}
```

### Vector deleting destructor `@ 0x826AA938`

The source-level destructor has no owned-resource teardown.  The compiler helper returns `this`
and frees it only when bit 0 of the flags word is set.

| inclusive instructions | complete effect |
|---|---|
| `826AA938..826AA950` | prologue; save `this` and flags; install base `PlugIn` vtable `off_820AA810` |
| `826AA954..826AA968` | test flags bit 0; optionally call `operator delete(this)` |
| `826AA96C..826AA97C` | return original `this`; restore/return |

```cpp
GinsuPlayer::~GinsuPlayer() = default;
// compiler-generated deleting thunk: if (flags & 1) operator delete(this)
```

## Four descriptor callbacks

### `GetSize @ 0x826A40B8`

Exact signature: `static unsigned GetSize(const VoiceStageConfig* config)`.

| inclusive instructions | complete effect |
|---|---|
| `826A40B8..826A40C0` | save LR and allocate frame |
| `826A40C4..826A40CC` | load `config->pConstructorParams`; branch if null |
| `826A40D0..826A40D8` | load `PlayParams::pGinFile`; call `GetTotalTableSize`; add console object size `0x1D0` |
| `826A40DC..826A40E8` | success epilogue/return |
| `826A40EC..826A40FC` | null-params default: return `0x11D0 = 0x1D0 + 4096`; epilogue |

No rodata loads.  Member/config accesses: config `+0` -> `PlayParams*`, params `+0` -> blob pointer.

```cpp
unsigned GinsuPlayer::GetSize(const VoiceStageConfig* cfg)
{
    const PlayParams* p = static_cast<const PlayParams*>(cfg->pConstructorParams);
    const size_t tableBytes = p ? GinsuSynthData::GetTotalTableSize(p->pGinFile) : 4096u;
    return static_cast<unsigned>(AlignUp(sizeof(GinsuPlayer), 8) + tableBytes);
}
```

The host formula is mandatory: returning X360 literals `0x1D0/0x11D0` would under-allocate the
widened object.

### `CreateInstance @ 0x826C3418`

Exact signature: `static bool CreateInstance(GinsuPlayer* storage, const PlayParams*)`.  The second
argument is unused.  The apparent null check covers only the early vptr/synth stores; subsequent
unconditional writes dereference `storage`, so null is not a supported input.

| inclusive instructions | complete effect |
|---|---|
| `826C3418..826C342C` | prepare zeros; preserve `storage`; test for null |
| `826C3430..826C3454` | if nonnull, install `off_820AE168`; initialize synth last-input, cycle count, min/max, segment/sample/rate fields to zero |
| `826C3458..826C3478` | zero attributes 1..4; clear `mPlaying`; set current/previous rates to `48000` |
| `826C347C..826C3494` | set `PlugIn::mpAttribute=self+0x28`; set attribute 0 to `1000`; return true |

Rodata: vtable `820AE168`, `0.0f @82001CC0`, `48000.0f @820AA808`, and
`1000.0f @82009E10`.  Offsets are enumerated in the player layout table.

```cpp
bool GinsuPlayer::CreateInstance(GinsuPlayer* p, const PlayParams*)
{
    // In source, placement construction should install the vptr; the assignments below are
    // the exact non-base state written by ARTIST.
    p->mSynthData.mLastInputSample = 0.0f;
    p->mSynthData.mCycleCount = 0;
    p->mSynthData.mMinFrequency = p->mSynthData.mMaxFrequency = 0.0f;
    p->mSynthData.mSegCount = p->mSynthData.mSampleCount = p->mSynthData.mSampleRate = 0;
    p->mAttribute[1].value = p->mAttribute[2].value = 0.0f;
    p->mAttribute[3].value = p->mAttribute[4].value = 0.0f;
    p->mPlaying = false;
    p->mSampleRate = p->mPrevSampleRate = 48000.0f;
    p->mpAttribute = p->mAttribute;
    p->mAttribute[0].value = 1000.0f;
    return true;
}
```

### `PreProcess @ 0x8268C1D8`

Exact signature: `static int PreProcess(GinsuPlayer*, Mixer*, bool, int requestedSamples)`.

| inclusive instructions | complete effect |
|---|---|
| `8268C1D8..8268C1E4` | preserve self in `r11`; return `0`; store **word** `r6` at player `+0x54`; `blr` |

No rodata.  `Mixer*` and the bool are unused.

```cpp
int GinsuPlayer::PreProcess(GinsuPlayer* p, Mixer*, bool, int requested)
{
    p->mOutputSamplesRequested = requested;
    return 0;
}
```

### `Process @ 0x8268C1E8`

Exact signature: `static BufferStatus Process(GinsuPlayer*, Mixer*, bool isLastInput)`.  The bool
in `r5` is unused.  This is the complete granular scheduler/render path.

| inclusive instructions | complete effect |
|---|---|
| `8268C1E8..8268C220` | save GPR/FPR state; bind `self`/`mixer`; if `!mPlaying`, return `BUFFER_UNAVAILABLE (0)` |
| `8268C224..8268C27C` | sample-rate-change handshake: if current != previous, write Mixer `mNumSamples=0`, `mbChannelCount=self->outputChannels`, `mfSampleRate=current`, latch previous=current, return `BUFFER_AVAILABLE (1)` |
| `8268C280..8268C2AC` | load jump span from attribute 1 and clamp only its upper side to `mCycleCount-1` |
| `8268C2B0..8268C338` | publish requested count/channels/rate to Mixer; get destination SampleBuffer and stride; derive output channel 0, crossfade channel 2, resample scratch channel 3; compute overlap samples; load stream/jump time |
| `8268C33C..8268C34C` | skip jump scheduling unless `mixer.mdStreamTime >= mNextJumpTime` and requested output >= overlap size |
| `8268C350..8268C3C8` | compute current cycle; map requested frequency (attribute 0) to target sample/cycle; center a jump-span window and clamp its start to `[0, cycleCount-jumpSpan-2]` |
| `8268C3CC..8268C440` | advance xorshift-like RNG; use **old** seed modulo `0x7FFFFFFF`, normalized by `2^-31`, to choose a cycle in that window; map it to a candidate sample |
| `8268C444..8268C4F8` | phase-safe candidate selection: map backward/forward choices onto the current cycle's integer phase; reject choices within the same phase period by retaining the old playback position |
| `8268C4FC..8268C514` | advance `mNextJumpTime` by double `0.0099999997764825821`; if candidate equals old position, skip crossfade |
| `8268C518..8268C5A4` | if old-data cache invalid, force overlap count zero; derive crossfade/resample buffers; compute old input count from cycle period; call `GetSamples(oldPos, oldInput, overlap, crossfade, scratch, true, System*)` |
| `8268C5A8..8268C6CC` | multiply old crossfade samples into output by `1 - i/N`, four-way unrolled plus scalar tail |
| `8268C6D0..8268C714` | set playback to candidate; compute new input count and call `GetSamples(candidate, newInput, N, crossfade, scratch, false, System*)` |
| `8268C718..8268C83C` | add new crossfade samples into output with gain `i/N`, four-way unrolled plus scalar tail |
| `8268C840..8268C858` | decrement requested output by overlap; advance playback by new input count; set produced output to overlap |
| `8268C85C..8268C93C` | steady rendering loop: compute input count from local cycle period; cap input to 64 and recompute output count when capped; `GetSamples` into output+produced; advance all counters until requested becomes zero |
| `8268C940..8268C960` | cache eight encoded blocks: `block=playback>>5`, set old-cache base index, copy 152 bytes from `mSampleData + 19*block` |
| `8268C964..8268C98C` | swap Mixer `mpSrcBuffer` and `mpDstBuffer`; restore FPR/GPR state; return `BUFFER_AVAILABLE (1)` |

Direct rodata loads are `1.0f @82001C98`, `0.0f @82001CC0`, `2.0f @82001D9C`,
`0.5f @82001DA0`, `120.0f @82004A28`, `64.0f @82020A7C`, `2^-31 @820ADB88`,
the `0.01` double at `820ADBF0`, and `0.0005f @820ADBF8`; exact bytes are in the constants table.
Immediate constants are `0x1D872B41`, `0x7FFFFFFF`, `19`, `32`, and `152`.

Mixer accesses are exact: `mdStreamTime +0x30000`, `mpSrcBuffer +0x3000C`,
`mpDstBuffer +0x30010`, `mNumSamples +0x30020`, `mfSampleRate +0x30024`, and
`mbChannelCount +0x3002C`.  Within the destination `SampleBuffer`, it reads `mpSamples +4` and
the unsigned-halfword `muStride +0x0E`.  It treats `mpSamples + 2*stride` as crossfade storage and
`mpSamples + 3*stride` as resampling scratch; channel 0 is final output.  Channel 1 is not touched
by this ARTIST body.

The following sketch retains the ARTIST arithmetic/order and all state transitions.  `TruncToInt`
means PPC `fctiwz` (toward zero), and failures from `GetSamples` are intentionally ignored, as in
the binary.

```cpp
BufferStatus GinsuPlayer::Process(GinsuPlayer* p, Mixer* m, bool /*last*/)
{
    if (!p->mPlaying)
        return BUFFER_UNAVAILABLE;

    if (p->mSampleRate != p->mPrevSampleRate) {
        m->mNumSamples = 0;
        m->mbChannelCount = p->mOutputChannels;
        m->mfSampleRate = p->mSampleRate;
        p->mPrevSampleRate = p->mSampleRate;
        return BUFFER_AVAILABLE;
    }

    float jumpSpan = p->mAttribute[1].value;
    const float maxSpan = float(p->mSynthData.mCycleCount - 1);
    if (jumpSpan > maxSpan)
        jumpSpan = maxSpan;                 // no lower clamp in ARTIST

    int remaining = p->mOutputSamplesRequested;
    m->mNumSamples = remaining;
    m->mbChannelCount = p->mOutputChannels;
    m->mfSampleRate = p->mSampleRate;

    SampleBuffer* dst = m->mpDstBuffer;
    float* output = dst->mpSamples;
    const unsigned stride = dst->muStride;
    float* crossfade = output + 2 * stride;
    float* scratch = output + 3 * stride;
    int overlap = TruncToInt(p->mSampleRate * 0.0005f);
    int produced = 0;

    if (m->mdStreamTime >= p->mNextJumpTime && remaining >= overlap) {
        const float currentCycle = p->mSynthData.SampleToCycle(p->mPlaybackPos);
        const int targetSample =
            p->mSynthData.FrequencyToSample(p->mAttribute[0].value);
        const float targetCycle = p->mSynthData.SampleToCycle(targetSample);
        float windowStart = targetCycle - jumpSpan * 0.5f;
        if (windowStart < 0.0f)
            windowStart = 0.0f;
        else {
            const float hi = float(p->mSynthData.mCycleCount) - jumpSpan - 2.0f;
            if (windowStart > hi)
                windowStart = hi;
        }

        const uint32_t oldSeed = p->mRandomSeed;
        const uint32_t x = oldSeed ^ 0x1D872B41u;
        const uint32_t y = x ^ (x >> 5);
        p->mRandomSeed = (y << 27) ^ y ^ x;
        const uint32_t residue = oldSeed % 0x7FFFFFFFu;
        const float randomCycle = windowStart +
            (float(residue) * jumpSpan) * 0x1p-31f;
        int candidate = p->mSynthData.CycleToSample(randomCycle);

        if (candidate < p->mPlaybackPos) {
            const int cyclesBack = TruncToInt(currentCycle - randomCycle);
            candidate = cyclesBack > 0
                ? p->mSynthData.CycleToSample(currentCycle - float(cyclesBack))
                : p->mPlaybackPos;
        } else {
            const int onePeriod = TruncToInt(p->mSynthData.CyclePeriod(currentCycle));
            if (candidate > p->mPlaybackPos + onePeriod) {
                const int cyclesForward = TruncToInt(randomCycle - currentCycle);
                candidate = p->mSynthData.CycleToSample(
                    currentCycle + float(cyclesForward));
            } else {
                candidate = p->mPlaybackPos;
            }
        }

        p->mNextJumpTime += 0.0099999997764825821;
        if (candidate != p->mPlaybackPos) {
            if (p->mSynthData.mOldDataBlockIndex == -1)
                overlap = 0;

            const float samplesPerCycle =
                (p->mSampleRate * 120.0f) / p->mAttribute[0].value;
            const float outputPerInput = 1.0f / samplesPerCycle;
            const int oldInput = TruncToInt(
                p->mSynthData.CyclePeriod(currentCycle) * float(overlap) * outputPerInput);
            (void)p->mSynthData.GetSamples(p->mPlaybackPos, oldInput, overlap,
                                          crossfade, scratch, true, p->mpSystem);
            for (int i = 0; i < overlap; ++i)
                output[i] = (1.0f - float(i) / float(overlap)) * crossfade[i];

            p->mPlaybackPos = candidate;
            const float newCycle = p->mSynthData.SampleToCycle(candidate);
            const int newInput = TruncToInt(
                p->mSynthData.CyclePeriod(newCycle) * float(overlap) * outputPerInput);
            (void)p->mSynthData.GetSamples(candidate, newInput, overlap,
                                          crossfade, scratch, false, p->mpSystem);
            for (int i = 0; i < overlap; ++i)
                output[i] += (float(i) / float(overlap)) * crossfade[i];

            produced = overlap;
            remaining -= overlap;
            p->mOutputSamplesRequested = remaining;
            p->mPlaybackPos += newInput;
        }
    }

    while (p->mOutputSamplesRequested > 0) {
        int outCount = p->mOutputSamplesRequested;
        const float cycle = p->mSynthData.SampleToCycle(p->mPlaybackPos);
        const float period = p->mSynthData.CyclePeriod(cycle);
        const float samplesPerCycle =
            (p->mSampleRate * 120.0f) / p->mAttribute[0].value;
        int inCount = TruncToInt((float(outCount) / samplesPerCycle) * period);
        if (inCount > 64) {
            inCount = 64;
            outCount = TruncToInt((samplesPerCycle / period) * 64.0f);
        }
        (void)p->mSynthData.GetSamples(p->mPlaybackPos, inCount, outCount,
                                      output + produced, scratch, false, p->mpSystem);
        produced += outCount;
        p->mPlaybackPos += inCount;
        p->mOutputSamplesRequested -= outCount;
    }

    const int block = p->mPlaybackPos >> 5;
    p->mSynthData.mOldDataBlockIndex = block;
    std::memcpy(p->mSynthData.mOldDataBlock,
                p->mSynthData.mSampleData + 19 * block, 152);
    std::swap(m->mpSrcBuffer, m->mpDstBuffer);
    return BUFFER_AVAILABLE;
}
```

`samplesPerCycle` is the requested-frequency period in output samples: sample rate times 120,
divided by requested frequency.  The source's local cycle-table period determines how many
encoded input samples correspond to that output duration.

## Synthesis helper closure

The complete non-runtime closure is:

```text
GetSize -> GetTotalTableSize -> AdjustEndianness
PlayHandler -> GetTotalTableSize, BindToData -> AdjustEndianness
Process -> FrequencyToSample -> FloorToInt
        -> CycleToSample [raw-XEX body]
        -> SampleToCycle
        -> CyclePeriod
        -> GetSamples -> DecodeBlock
```

Compiler save/restore thunks, `memcpy`, `memset`, and `printf` are standard runtime services and
not GinsuPlayer helpers.  No Decoder/TimerManager service is used: unlike `SndPlayer1`, Ginsu is a
self-contained custom decoder/synthesizer.

### `AdjustEndianness @ 0x8268B1D0`

IDA left this helper unnamed (`sub_8268B1D0`); DecFIGS calls the corresponding operation
`AdjustEndienness`.  Faithful signature:

```cpp
static GinsuDataLayoutOnDisk* AdjustEndianness(GinsuDataLayoutOnDisk* data);
```

| inclusive instructions | complete effect |
|---|---|
| `8268B1D0..8268B204` | byte-reverse dword at header `+0x08` |
| `8268B208..8268B224` | byte-reverse dword at `+0x0C` |
| `8268B228..8268B244` | byte-reverse dword at `+0x10` |
| `8268B248..8268B264` | byte-reverse dword at `+0x14` |
| `8268B268..8268B284` | byte-reverse dword at `+0x18` |
| `8268B288..8268B2A8` | byte-reverse dword at `+0x1C` |
| `8268B2AC..8268B2C0` | compute `cycleCount + segCount + 2`; skip table loop if nonpositive |
| `8268B2C4..8268B2F0` | byte-reverse that many dwords starting at blob `+0x20` |
| `8268B2F4..8268B300` | store halfword `1` at `+0x06`; return original blob pointer |

No rodata and no object members.  It mutates the caller-owned blob in place.

```cpp
GinsuDataLayoutOnDisk* AdjustEndianness(GinsuDataLayoutOnDisk* d)
{
    auto* b = reinterpret_cast<std::byte*>(d);
    for (size_t off = 8; off != 32; off += 4)
        ReverseFourBytesInPlace(b + off);
    const int words = ReadNativeI32(b + 0x14) + ReadNativeI32(b + 0x10) + 2;
    for (int i = 0; i < words; ++i)
        ReverseFourBytesInPlace(b + 0x20 + 4 * i);
    WriteNativeU16(b + 6, 1);
    return d;
}
```

### `GinsuSynthData::GetTotalTableSize @ 0x8268B308`

Exact signature from DecFIGS and call sites:
`static unsigned GetTotalTableSize(void* pGinFile)`.

| inclusive instructions | complete effect |
|---|---|
| `8268B308..8268B310` | prologue |
| `8268B314..8268B34C` | compare bytes `+0..+4` with `G n s u 2`; invalid magic branches to zero |
| `8268B350..8268B35C` | if halfword `+6` is zero, call `AdjustEndianness` and use returned blob |
| `8268B360..8268B370` | return `4 * (cycleCount + segCount + 2)` |
| `8268B374..8268B380` | success epilogue |
| `8268B384..8268B394` | invalid-magic return zero and epilogue |

No rodata: magic bytes and scale are immediates.  Serialized fields accessed are `+0..+6`,
`segCount +0x10`, and `cycleCount +0x14`.

```cpp
unsigned GinsuSynthData::GetTotalTableSize(void* file)
{
    auto* b = static_cast<std::byte*>(file);
    if (std::memcmp(b, "Gnsu2", 5) != 0)
        return 0;
    if (ReadNativeU16(b + 6) == 0)
        b = reinterpret_cast<std::byte*>(AdjustEndianness(
            reinterpret_cast<GinsuDataLayoutOnDisk*>(b)));
    return 4u * unsigned(ReadNativeI32(b + 0x14) + ReadNativeI32(b + 0x10) + 2);
}
```

### `GinsuSynthData::BindToData @ 0x8268B398`

Exact signature: `bool BindToData(void* pGinFile, uintptr_t tableStorage)`.

| inclusive instructions | complete effect |
|---|---|
| `8268B398..8268B3A0` | save GPRs |
| `8268B3A4..8268B3D0` | clear native min/max, segment/cycle/sample counts, and sample rate |
| `8268B3D4..8268B40C` | validate bytes `"Gnsu2"`; invalid branches to false |
| `8268B410..8268B420` | if header flag `+6` is zero, endian-adjust in place |
| `8268B424..8268B47C` | load min/max/counts/rate; compute `(segCount+1)*4`, `(cycleCount+1)*4`; store frequency-table relative offset `tableStorage-this` |
| `8268B480..8268B4A4` | copy frequency table; store cycle-table relative offset; copy cycle table |
| `8268B4A8..8268B4C8` | point `mSampleData` after both serialized tables; set `mCurrentBlock=-1` |
| `8268B4CC..8268B4F8` | initialize minimum period from `sampleCount`; scan all adjacent cycle-table differences and keep the minimum |
| `8268B4FC..8268B51C` | convert minimum period to float; store; return true; restore |
| `8268B520..8268B528` | invalid-magic return false; restore |

Rodata: `0.0f @82001CC0`.  All synth members touched appear in the offset table.

```cpp
bool GinsuSynthData::BindToData(void* file, uintptr_t storageAddress)
{
    mMinFrequency = mMaxFrequency = 0.0f;
    mSegCount = mCycleCount = mSampleCount = mSampleRate = 0;
    auto* b = static_cast<std::byte*>(file);
    if (std::memcmp(b, "Gnsu2", 5) != 0)
        return false;
    if (ReadNativeU16(b + 6) == 0)
        b = reinterpret_cast<std::byte*>(AdjustEndianness(
            reinterpret_cast<GinsuDataLayoutOnDisk*>(b)));

    mMinFrequency = ReadNativeF32(b + 8);
    mMaxFrequency = ReadNativeF32(b + 12);
    mSegCount = ReadNativeI32(b + 16);
    mCycleCount = ReadNativeI32(b + 20);
    mSampleCount = ReadNativeI32(b + 24);
    mSampleRate = ReadNativeI32(b + 28);
    const size_t freqBytes = 4u * size_t(mSegCount + 1);
    const size_t cycleBytes = 4u * size_t(mCycleCount + 1);
    auto* storage = reinterpret_cast<std::byte*>(storageAddress);
    mFreqOffset = uintptr_t(storage - reinterpret_cast<std::byte*>(this));
    std::memcpy(storage, b + 32, freqBytes);
    mCycleOffset = uintptr_t(storage + freqBytes - reinterpret_cast<std::byte*>(this));
    std::memcpy(storage + freqBytes, b + 32 + freqBytes, cycleBytes);
    mSampleData = reinterpret_cast<uint8_t*>(b + 32 + freqBytes + cycleBytes);
    mCurrentBlock = -1;

    const int* cycle = CycleTable();
    int minPeriod = mSampleCount;
    for (int i = 0; i < mCycleCount; ++i)
        if (cycle[i + 1] - cycle[i] < minPeriod)
            minPeriod = cycle[i + 1] - cycle[i];
    mMinPeriod = float(minPeriod);
    return true;
}
```

### `FloorToInt @ 0x8268B530`

Unnamed local helper, exact effective signature `static int FloorToInt(float x)` (`x` in `f1`).

| inclusive instructions | complete effect |
|---|---|
| `8268B530..8268B544` | compare with `0.0f`; nonnegative path converts toward zero and returns |
| `8268B548..8268B574` | negative path converts toward zero, converts the integer back, and decrements if the input was nonintegral |
| `8268B578..8268B580` | common return |

Rodata: `0.0f @82001CC0`.  No member accesses.

```cpp
static int FloorToInt(float x)
{
    const int t = TruncToInt(x);
    return (x < 0.0f && float(t) != x) ? t - 1 : t;
}
```

### `GinsuSynthData::DecodeBlock @ 0x8268B588`

Exact signature: `void DecodeBlock(int block, bool useOldData, System* system)`.  Call-site
registers prove the third argument; ARTIST does not read it.

| inclusive instructions | complete effect |
|---|---|
| `8268B588..8268B594` | set `mCurrentBlock=block`; test `useOldData` |
| `8268B598..8268B5BC` | choose record: old cache `mOldDataBlock + 19*(block-mOldDataBlockIndex)` or live `mSampleData + 19*block` |
| `8268B5C0..8268B604` | decode initial sample 0; select predictor coefficients from low nibble of byte 0; set nibble-scale row from low nibble of byte 2 |
| `8268B608..8268B634` | decode initial sample 1; initialize destination/payload loop state |
| `8268B638..8268B654` | load coefficient/codebook bases and three-iteration loop count |
| `8268B658..8268B7AC` | three unrolled iterations, each consuming five bytes / ten signed nibbles and emitting ten predicted samples |
| `8268B7B0..8268B7B4` | restore frame; return |

Rodata is exactly the two four-float predictor arrays and the 256-float codebook documented above.
Members read/written: old cache/index, sample-data pointer, current block, and `mSample[32]`.

The record is exactly 19 bytes: bytes 0..3 carry two 12-bit initial samples plus predictor/shift
nibbles; bytes 4..18 hold 30 residual nibbles.  There is no sign extension for the two initial
samples; the recurrence operates in float.

```cpp
void GinsuSynthData::DecodeBlock(int block, bool old, System* /*system*/)
{
    mCurrentBlock = block;
    const uint8_t* r = old
        ? mOldDataBlock + 19 * (block - mOldDataBlockIndex)
        : mSampleData + 19 * block;

    mSample[0] = float((unsigned(r[1]) << 8) | (r[0] & 0xF0));
    mSample[1] = float((unsigned(r[3]) << 8) | (r[2] & 0xF0));
    const unsigned predictor = r[0] & 0x0F;
    const unsigned shift = r[2] & 0x0F;
    const float a = kCoef0[predictor];
    const float b = kCoef1[predictor];
    int out = 2;
    for (int byte = 4; byte < 19; ++byte) {
        const unsigned codes[2] = { unsigned(r[byte] >> 4), unsigned(r[byte] & 0x0F) };
        for (unsigned code : codes) {
            mSample[out] = mSample[out - 1] * a + mSample[out - 2] * b
                         + kCodebook[shift][code];
            ++out;
        }
    }
}
```

The X360 unrolling groups five bytes at a time but is algebraically identical to the loop above;
the load/add/multiply order shown in the recurrence is preserved.

### `GinsuSynthData::FrequencyToSample @ 0x8268B7B8`

Exact signature: `int FrequencyToSample(float frequency) const`.

| inclusive instructions | complete effect |
|---|---|
| `8268B7B8..8268B7E0` | load `mSegCount`; if `<1`, return zero |
| `8268B7E4..8268B808` | resolve frequency-table pointer; if frequency <= min, return entry 0 |
| `8268B80C..8268B82C` | if frequency >= max, return entry `segCount` |
| `8268B830..8268B858` | normalize frequency to segment coordinate and call `FloorToInt` |
| `8268B85C..8268B8B4` | linearly interpolate adjacent frequency-table sample indices |
| `8268B8B8..8268B8E4` | round interpolated result: add `0.5` if positive, subtract `0.5` otherwise, then truncate |
| `8268B8E8..8268B8F4` | return/epilogue |

Rodata: `0.0f @82001CC0`, `0.5f @82001DA0`.  Members: segment count, min/max frequency,
and frequency-table relative offset.

```cpp
int GinsuSynthData::FrequencyToSample(float f) const
{
    if (mSegCount < 1) return 0;
    const int* t = FrequencyTable();
    if (f <= mMinFrequency) return t[0];
    if (f >= mMaxFrequency) return t[mSegCount];
    const float x = (f - mMinFrequency) * float(mSegCount)
                  / (mMaxFrequency - mMinFrequency);
    const int i = FloorToInt(x);
    const float sample = float(t[i]) + float(t[i + 1] - t[i]) * (x - float(i));
    return TruncToInt(sample + (sample > 0.0f ? 0.5f : -0.5f));
}
```

### `GinsuSynthData::CycleToSample @ 0x8268B8F8`

The per-function JSON is absent, but this body is fully recovered from raw XEX file offset
`0x0068E8F8`; `0x8268BA1C` is zero padding and `CyclePeriod` begins at `0x8268BA20`.
DecFIGS and Process call sites fix the signature: `int CycleToSample(float cycle) const`.

| inclusive raw instructions | complete effect |
|---|---|
| `8268B8F8..8268B920` | frame/count setup; if `mCycleCount<1`, return zero |
| `8268B924..8268B94C` | resolve cycle table; if cycle <= 0, return entry 0 |
| `8268B950..8268B980` | if cycle >= count, return entry `cycleCount` |
| `8268B984..8268B9E0` | compute floor(cycle), resolve adjacent entries, and linearly interpolate |
| `8268B9E4..8268BA08` | signed nearest-integer rounding via `+/-0.5` then truncation |
| `8268BA0C..8268BA18` | epilogue and `blr` |
| `8268BA1C` | zero padding, raw bytes `00 00 00 00` |

Rodata: `0.0f @82001CC0`, `0.5f @82001DA0`.  Members: cycle count and cycle-table
relative offset.

```cpp
int GinsuSynthData::CycleToSample(float x) const
{
    if (mCycleCount < 1) return 0;
    const int* t = CycleTable();
    if (x <= 0.0f) return t[0];
    if (x >= float(mCycleCount)) return t[mCycleCount];
    const int i = FloorToInt(x);
    const float sample = float(t[i]) + float(t[i + 1] - t[i]) * (x - float(i));
    return TruncToInt(sample + (sample > 0.0f ? 0.5f : -0.5f));
}
```

### `GinsuSynthData::CyclePeriod @ 0x8268BA20`

Exact signature: `float CyclePeriod(float cycle) const`.

Let `T[i]` be the cycle table and `P[i]=T[i+1]-T[i]`.  ARTIST interpolates *centered* local
periods: at interior integer `i`, the left endpoint is `(P[i-1]+P[i])/2` and the right endpoint
is `(P[i]+P[i+1])/2`.  At the boundaries it interpolates `P[0] -> (P[0]+P[1])/2` and
`(P[n-2]+P[n-1])/2 -> P[n-1]`.  Inputs below zero clamp to zero; inputs at/above `n` clamp to `n`.

| inclusive instructions | complete effect |
|---|---|
| `8268BA20..8268BA34` | if `mCycleCount<1`, return `0.0f` |
| `8268BA38..8268BA7C` | resolve table and compute floor(cycle), including negative noninteger correction |
| `8268BA80..8268BADC` | left-edge case (`i<1`): clamp negative input/index; form `P0` and half of `P0+P1` |
| `8268BAE0..8268BB0C` | select interior vs right edge; clamp input >= count to exactly count/index `count-1` |
| `8268BB10..8268BB6C` | right edge: form half of last two periods and final period |
| `8268BB70..8268BBCC` | interior: form the half-sums on each side of integer cycle `i` |
| `8268BBD0..8268BBF0` | common fractional interpolation and return |
| `8268BBF4` | exported zero padding |

Rodata: `0.0f @82001CC0`, `0.5f @82001DA0`.  Members: cycle count/table.

```cpp
float GinsuSynthData::CyclePeriod(float x) const
{
    const int n = mCycleCount;
    if (n < 1) return 0.0f;
    const int* t = CycleTable();
    int i = FloorToInt(x);
    float left, right;
    if (i < 1) {
        if (i < 0) { i = 0; x = 0.0f; }
        const float p0 = float(t[1] - t[0]);
        const float p1 = float(t[2] - t[1]);
        left = p0;
        right = 0.5f * (p0 + p1);
    } else if (i >= n - 1) {
        if (i >= n) { i = n - 1; x = float(n); }
        const float pPrev = float(t[n - 1] - t[n - 2]);
        const float pLast = float(t[n] - t[n - 1]);
        left = 0.5f * (pPrev + pLast);
        right = pLast;
    } else {
        const float pPrev = float(t[i] - t[i - 1]);
        const float pHere = float(t[i + 1] - t[i]);
        const float pNext = float(t[i + 2] - t[i + 1]);
        left = 0.5f * (pPrev + pHere);
        right = 0.5f * (pHere + pNext);
    }
    const float frac = x - float(i);
    return left + frac * (right - left);
}
```

The left-edge code accesses `T[2]`; valid content therefore has at least two cycles.  ARTIST has no
defensive special case for `mCycleCount==1`.

### `GinsuSynthData::SampleToCycle @ 0x8268BBF8`

Exact signature: `float SampleToCycle(int sample) const`.

This is the monotone inverse of `CycleToSample`.  It uses interpolation search, then bounds each
next search interval using `ceil(distance/mMinPeriod)`.  Once `T[i] <= sample < T[i+1]`, it returns
`i + (sample-T[i])/(T[i+1]-T[i])`.

| inclusive instructions | complete effect |
|---|---|
| `8268BBF8..8268BC0C` | load cycle count; count `<1` returns `0.0f` |
| `8268BC10..8268BC48` | resolve table; clamp sample <= `T[0]` to 0 and sample >= `T[n]` to float(n) |
| `8268BC4C..8268BC64` | initialize lower=0, upper=n interpolation-search interval |
| `8268BC68..8268BD24` | estimate candidate index from relative sample position; floor estimate; load `T[candidate]` |
| `8268BD28..8268BDBC` | sample below candidate: upper=candidate; raise lower by the min-period-derived bound |
| `8268BDC0..8268BE5C` | sample at/above next entry: lower=candidate+1; lower the upper bound using `mMinPeriod` |
| `8268BE60..8268BED0` | enclosing pair found; compute fractional cycle and return |
| `8268BED4` | exported zero padding |

Rodata: `0.0f @82001CC0`.  Members: cycle count/table and `mMinPeriod`.

```cpp
float GinsuSynthData::SampleToCycle(int sample) const
{
    const int n = mCycleCount;
    if (n < 1) return 0.0f;
    const int* t = CycleTable();
    if (sample <= t[0]) return 0.0f;
    if (sample >= t[n]) return float(n);

    int lo = 0, hi = n;
    for (;;) {
        const int span = hi - lo;
        const float estimate = float(sample - t[lo]) * float(span)
                             / float(t[hi] - t[lo]);
        const int i = lo + FloorToInt(estimate);
        if (sample < t[i]) {
            const int step = CeilToInt(float(t[i] - sample) / mMinPeriod);
            hi = i;
            lo = std::max(lo, i - step);
        } else if (sample >= t[i + 1]) {
            const int step = CeilToInt(float(sample - t[i]) / mMinPeriod);
            lo = i + 1;
            hi = std::min(hi, i + 1 + step);
        } else {
            return float(i) + float(sample - t[i]) / float(t[i + 1] - t[i]);
        }
    }
}
```

`FloorToInt`/`CeilToInt` in this sketch spell out PPC conversion semantics; the ARTIST function
inlines both rather than calling the local floor helper.

### `GinsuSynthData::GetSamples @ 0x8268BED8`

Exact signature, verified from all Process call register assignments and DecFIGS:

```cpp
bool GetSamples(int startSample, int numInputSamples, int numOutputSamples,
                float* output, float* resampleBuffer, bool useOldData, System* system);
```

| inclusive instructions | complete effect |
|---|---|
| `8268BED8..8268BF00` | save registers; bind all seven explicit arguments |
| `8268BF04..8268BF1C` | reject `start<0` or `start+numInput-1 >= mSampleCount` |
| `8268BF20..8268BF38` | if `(start>>5) != mCurrentBlock`, call `DecodeBlock(block,useOldData,system)` |
| `8268BF3C..8268BF50` | direct output when input count equals output count; otherwise set `resampleBuffer[0]=mLastInputSample` and decode into `resampleBuffer+1` |
| `8268BF54..8268BFC4` | copy `numInput` decoded values times `1/32768`; cross 32-sample blocks by calling `DecodeBlock(current+1,...)`; retain last decoded float |
| `8268BFC8..8268BFFC` | if resampling, compute signed 16.16 step `(numInput<<16)/numOutput`; initialize phase to one step; emit PPC divide traps for invalid divisor/overflow |
| `8268C000..8268C128` | four-way-unrolled linear interpolation for output indices `0..numOutput-2`; integer index=`phase>>16`, fraction=`(phase&0xFFFF)/65536` |
| `8268C12C..8268C188` | scalar interpolation tail through output index `numOutput-2` |
| `8268C18C..8268C19C` | force final output sample to `resampleBuffer[numInput]` exactly |
| `8268C1A0..8268C1AC` | store last decoded input in `mLastInputSample`; return true |
| `8268C1B0..8268C1C4` | invalid-range path: `printf` exact diagnostic with start/input/sampleCount |
| `8268C1C8..8268C1D0` | return false |

Rodata: `0.0f @82001CC0`, `1/32768 @820ADBE8`, `1/65536 @8207ACF0`, and diagnostic
string `@820ADB90`.  Members: sample count/current block/decoded block/last input;
`DecodeBlock` reaches encoded/cache members.

```cpp
bool GinsuSynthData::GetSamples(int start, int inCount, int outCount,
                                float* out, float* work, bool old, System* system)
{
    if (start < 0 || start + inCount - 1 >= mSampleCount) {
        std::printf("GinsuSynthData::GetSamples FAILED! Startsample=%d "
                    "numInputSamples=%d mSampleCount=%d\n",
                    start, inCount, mSampleCount);
        return false;
    }
    if ((start >> 5) != mCurrentBlock)
        DecodeBlock(start >> 5, old, system);

    float* decoded = out;
    if (inCount != outCount) {
        work[0] = mLastInputSample;
        decoded = work + 1;
    }
    int within = start & 31;
    float last = 0.0f;
    for (int i = 0; i < inCount; ++i) {
        last = mSample[within] * (1.0f / 32768.0f);
        decoded[i] = last;
        if (++within == 32) {
            DecodeBlock(mCurrentBlock + 1, old, system);
            within = 0;
        }
    }

    if (inCount != outCount) {
        const int32_t step = (inCount << 16) / outCount;
        uint32_t phase = uint32_t(step);
        for (int i = 0; i < outCount - 1; ++i) {
            const unsigned index = phase >> 16;
            const float frac = float(phase & 0xFFFFu) * (1.0f / 65536.0f);
            out[i] = work[index] + frac * (work[index + 1] - work[index]);
            phase += uint32_t(step);
        }
        out[outCount - 1] = work[inCount];
    }
    mLastInputSample = last;
    return true;
}
```

The scratch prefix deliberately supplies continuity from the previous call: interpolation phase
starts at one step, so `work[0]` is the prior input and `work[1]` is the first newly decoded input.
The explicit final assignment avoids fixed-point accumulation leaving the last output shy of the
last input.

## Host/x64 port hazards

1. **Compute allocation size from the host object.**  X360 `GetSize` returns
   `0x1D0 + tableBytes` or `0x11D0`; neither literal is valid on x64.  Use
   `AlignUp(sizeof(GinsuPlayer), 8) + tableBytes`, and derive the tail pointer with the same host
   expression.  The object-tail table storage is part of the allocation contract.

2. **Widen every native pointer member.**  Console `PlugIn` vptr/System/Voice/attribute/descriptor
   pointers, `GinsuSynthData::mpTempStore`, `GinsuSynthData::mSampleData`, and
   `GinsuPlayer::pGinFile` are all 32-bit at the offsets shown.  They must be normal host pointers,
   not `uint32_t` compatibility fields.  `mFreqOffset` and `mCycleOffset` are relative offsets, but
   DecFIGS types them `uintptr_t`; store the host-width difference or replace them with native
   table pointers consistently.  Do not truncate a host address to preserve console offsets.

3. **Deferred records widen, and their handler return values must widen with them.**  X360
   `PlayCommand`/`StopCommand` are 12/8 bytes.  Natural x64 forms are 24/16 bytes (three/two
   pointers).  `EventEvent` must reserve the host `sizeof(record)`, and `PlayHandler`/
   `StopHandler` must return those same host sizes because the consumer advances its ring cursor by
   the handler return.  Retaining returns `12`/`8` on x64 would desynchronize the command ring.

4. **Constructor/event parameter blocks contain native pointers.**  `PlayParams` is four bytes on
   X360 and eight on x64.  `VoiceStageConfig::pConstructorParams` and the event-0 block must be read
   as host pointers.  There is no assembly evidence for storing a pointer into a narrow integer
   field anywhere in Ginsu; doing so would be an invented hazard.

5. **Serialized widths and granular strides do not widen.**  The `Gnsu2` header remains 32 bytes;
   its floats/integers and both copied tables remain 32-bit.  Encoded records remain **19 bytes**,
   decoded blocks remain 32 floats, and the old cache remains `8*19 == 152` bytes.  `19*block` and
   the 152-byte copy must not become `sizeof` of a host struct.  Parse the header by byte offset so
   host padding cannot alter it.

6. **The descriptor and vtable must be native C++ objects, not copied X360 word arrays.**  Callback,
   string, table, and vtable pointers widen.  Preserve the semantic fields (`'Gns0'`, type/count
   tail, callbacks, maps/attributes/events) through native initializers.

7. **Mixer/SampleBuffer pointers already widen in the vendor host types.**  Use named fields and
   float-pointer arithmetic.  The `muStride` itself remains a 16-bit count; the code computes
   channel bases in float elements (`2*stride`, `3*stride`), not byte-offset hacks.

8. **Endianness is an asset-format decision, not an object-layout accommodation.**  ARTIST checks
   halfword `+6`, swaps the six header dwords and the two table arrays in place when it is zero,
   then writes `1`.  A host implementation must reproduce the equivalent transition for the
   actual PC asset byte order.  It must not swap the 19-byte encoded records or widen/repack the
   serialized file.

9. **Preserve integer conversion semantics.**  PPC uses truncation-toward-zero plus explicit
   corrections for floor/ceil, and signed nearest rounding in table mapping.  Default C++ casts
   provide the truncation part; `std::round`, platform SIMD conversions, or unsigned arithmetic can
   differ at negative values and half points.

10. **Do not silently add guards that change scheduling.**  ARTIST ignores `BindToData` and
    `GetSamples` boolean results in the deferred/render paths, increments next-jump time from its
    prior value rather than from current stream time, uses the old RNG seed for the random residue,
    and has no explicit wraparound at end-of-stream.  Integration may validate assets before play,
    but the synthesizer body should remain behaviorally faithful.

## Proposed native declaration shape

This is a declaration/ownership guide, not a fixed-offset host replica:

```cpp
class GinsuPlayer final : public PlugIn {
public:
    struct PlayParams { void* pGinFile; };
    struct PlayCommand;
    struct StopCommand;

    static unsigned GetSize(const VoiceStageConfig*);
    static bool CreateInstance(GinsuPlayer*, const PlayParams*);
    static int PreProcess(GinsuPlayer*, Mixer*, bool, int);
    static BufferStatus Process(GinsuPlayer*, Mixer*, bool);

    void ReleaseEvent() override;
    void EventEvent(int, void*) override;
    unsigned GetPpuTicksEvent() const override;
    ~GinsuPlayer() override;

private:
    static int PlayHandler(PlayCommand*);
    static int StopHandler(StopCommand*);

    Attribute_t mAttribute[5];
    bool mPlaying;
    int mOutputSamplesRequested;
    GinsuSynthData mSynthData;
    void* pGinFile;
    float mSampleRate;
    float mPrevSampleRate;
    int mNoJumpSize;
    int mOverlapSize;
    int mPlaybackPos;
    uint32_t mRandomSeed;
    double mNextJumpTime;
};
```

`GinsuSynthData` should own its fixed cache/decoded arrays and native metadata in the DecFIGS order,
with `FrequencyTable()`/`CycleTable()` resolving either host-width relative offsets or direct native
pointers.  The table tail remains allocated after `GinsuPlayer`, matching the callback contract.

## Verification and closure audit

### Assembly/export checks

* Callback JSON bodies and counts: GetSize `826A40B8..40FC` (18 exported lines), CreateInstance
  `826C3418..3494` (32), PreProcess `8268C1D8..C1E4` (4), and Process
  `8268C1E8..C98C` (490).  Every range is covered above.
* Event/vtable bodies: EventEvent `826C3498..34FC` (26 including padding), PlayHandler
  `826A4100..4208` (67), deleting destructor `826AA938..A97C` (18), and raw StopHandler
  `8268B1B8..B1CC`.  Raw vtable at `820AE168` contains exactly the four targets documented.
* Helper JSON bodies: GetTotal `8268B308..B394` (36), Bind `8268B398..B528` (101), DecodeBlock
  `8268B588..B7B4` (140), FrequencyToSample `8268B7B8..B8F4` (80), CyclePeriod
  `8268BA20..BBF4` (118 including padding), SampleToCycle `8268BBF8..BED4` (184 including
  padding), and GetSamples `8268BED8..C1D0` (191).  Raw helper bodies AdjustEndianness,
  FloorToInt, and CycleToSample are also covered address-contiguously.
* `xrefs_from` closure was walked from all four callbacks and then recursively through Ginsu
  helpers.  The only omitted outbound targets are compiler register-save/restore thunks and the
  standard `memcpy`, `memset`, `printf`, and `operator delete` runtime routines.
* Callback signatures were checked at `Voice::CreateInstance`, `PlugIn::CreateInstance`, and
  `Mixer::ProcessInputPlugIns`; vtable signatures were checked against the DecFIGS `PlugIn` shape.
* All rodata bytes in this dossier were reread from the uncompressed raw XEX using the supplied
  formula and interpreted big-endian.  `CycleToSample` and StopHandler were decoded from the same
  raw image because their per-function JSON dossiers are absent.

### Semantic invariants suitable for tests

* `GetSize(null constructor params) == AlignUp(sizeof(host GinsuPlayer),8)+4096`; with content it
  adds `4*(segCount+cycleCount+2)` after endian adjustment.
* `PreProcess` preserves values above 65535 because it stores a word, not a halfword.
* Create defaults are `{frequency=1000, jumpSpan=0, rate/min/max=0}`, player rates `48000`, and
  stopped state.
* `FrequencyToSample(min/max)` returns frequency-table endpoints;
  `CycleToSample(0/count)` returns cycle-table endpoints; `SampleToCycle` round-trips table entries
  to their integer cycle indices.
* A 19-byte decode record produces two header samples plus 30 residual-predicted samples.  Shift
  rows 13..15 yield zero residuals.
* Equal input/output counts bypass resampling.  Resampling uses prior-call continuity, 16.16 phase,
  and forces the last output to the last new input.
* Event 0 queues play; every nonzero event queues stop.  On X360 their handlers return 12/8; on
  x64 they must return native record sizes.
* A playing rate change yields one available zero-sample buffer and latches the rate before normal
  synthesis resumes.
* A normal render ends by caching eight encoded blocks at `playback>>5` and swapping Mixer source
  and destination buffers.

## BLOCKED / evidence limits

* **Attribute/event display names and tool metadata are BLOCKED.**  The five runtime attribute
  records and two runtime event records are pointed to by the descriptor, but the raw event area at
  `0x82FFB9F8` is runtime/BSS-like data rather than stable serialized descriptor bytes.  Assembly
  proves the five value roles and proves event 0 versus nonzero dispatch, but not human-facing
  labels, units strings, ranges, or a symbolic name for event 1.  Proposed names in this dossier
  (`frequency`, `jumpSpan`, `sampleRate`, `minFrequency`, `maxFrequency`, `play`, `stop`) are faithful
  behavioral names, not claimed original strings.
* **The PC asset endian flag's producer-side contract is BLOCKED.**  ARTIST behavior is fully
  recovered, but these inputs do not establish whether the eventual PC content pipeline presents
  little-endian native header/tables with flag 1, or preserves a swap-required representation with
  flag 0.  Resolve this at asset integration; do not alter the decoded record format or object
  layout to guess around it.
* **No behavior is blocked.**  The two missing JSON dossiers were recoverable from authoritative
  raw XEX bytes.  All four descriptor callbacks, every installed vtable slot, both event handlers,
  and the complete reachable Ginsu synthesis helper set are decoded above.
