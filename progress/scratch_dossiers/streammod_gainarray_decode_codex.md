# StreamMod and GainArray X360 decode

## 1. Summary

This report decodes both game-side plug-ins registered by
`CgsSound::Playback::GenericRwacFactory` in the ARTIST X360 build.  Assembly in the
named per-function JSON dossiers is the behavioural authority.  Raw data was read from
`IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex` with
`file_off = 0x3000 + vaddr - 0x82000000`, big-endian.

Decoded for `SndPlayer1_CgsStreamMod`: all four descriptor callbacks, all four vtable
slots, the complete five-event dispatch, and every class-local helper reachable from
those callbacks (`UnpackHeader`, `WaitForStartTime`, `Declick`,
`AdvanceCurrentRequest`, `FeedCleanup`, `GetFeedSlot`, `PlayHandler`,
`ModifyStartTimeHandler`, `RemoveRequest`, `RequestCleanup`, `StreamLostCallback`,
`StopHandler`, `SubmitChunk`, `StreamNextChunk`, `HandleLoopStart`,
`HandleSampleEnd`, `StartRequest`, and `RwacTimerClient`).  Calls into already-separate
engine/platform services (`System`, `Decoder`, `BitGetter`, `IStreamProvider`,
`CgsFileSystem`, assertions, allocation, and `XMem*`) are closed at their exact call
signatures; recursively decoding those independent subsystems would be an unbounded
closure and is not treated as a StreamMod helper.

Decoded for `GainArray`: all three descriptor callbacks and all four vtable slots (the
first two share one no-op body).  No requested body is BLOCKED.

High-value corrections/gaps:

- The supplied approximate addresses are call sites, not starts.  Exact starts are:
  `UnpackHeader 0x8268C990` (`0x8268C9D4` is its first `BitGetter::GetBits` call),
  `PlayHandler 0x826A43A0` (`0x826A4518` is `XMemCpy`), `SubmitChunk 0x826C3928`
  (`0x826C39E8` is `Decoder::Feed`), `StartRequest 0x826DBD40`
  (`0x826DBD78` is `System::Lock`), and `RemoveRequest 0x826A45E8`
  (`0x826A46A4` is `Voice::ExpelAfterDecay`).  The corresponding callee dossiers'
  `xrefs_to` point back to the containing helper, and the containing helpers'
  `xrefs_from` name those exact callees.
- Contrary to the committed `sndplayer1shared.h`, StreamMod has **20 feed records of
  12 console bytes**, not 15 records of 16 bytes.  `GetFeedSlot` wraps at 20
  (`0x826A437C`), `CreateInstance` and `FeedCleanup` each iterate 20 records with a
  `+0x0C` stride (`0x826EA750..0x826EA778`, `0x826A425C..0x826A433C`), and DecFIGS
  names `SndPlayer1FeedDesc[20]` with no pointer members.
- StreamMod has a 32-byte console `RequestInternal`, a `0x88` console
  `RequestExternal`, six chunk buffers per external request, a fixed declick tail at
  `+0x188`, and embedded float request-handle counter at `+0x160`.  The ordinary
  `SndPlayer1` has a 48-byte internal request, `0x50` external request, 16-byte feed
  records, declick tail `+0x1D8`, and a separately allocated request-handle counter.
- The game `IStreamProvider` hookup is fully live on the current PC side:
  `Module::Prepare` publishes `static_cast<IStreamProvider*>(this)` to
  `off_82FFBA0C`.  StreamMod itself remains mostly unimplemented and its descriptor is
  not registered.
- The existing GainArray TU has bodies for `GetSize`, `CreateInstance`, `Process`, and
  a destructor plus the recovered `1/64` ramp constant.  It lacks a real public header,
  descriptor home/getter, vtable definitions, and factory registration.  Its current
  `Process` also advances `f32*` channel pointers by `4 * stride * channel`, four times
  the assembly's byte-scaled displacement; the faithful typed expression is
  `mpSamples + stride * channel`.

### Descriptor and vtable raw data

| Datum | Recomputed file offset | Raw big-endian bytes | Decode |
|---|---:|---|---|
| StreamMod descriptor `0x82F2E124` | `0x00F31124` | `82 0A 91 D8 82 6A 42 10 82 6E A5 08 82 68 CD 10 82 6A 46 B0 82 F2 D9 1C 82 F2 FA B0 82 F2 E6 38 00 00 00 00 00 00 00 00 4A 53 74 72 00 01 03 05 00 01 00 00` | name, four callbacks, metadata, null tool-side/link, `JStr`, tail `0,1,3,5,0,1,0,0` |
| StreamMod name `0x820A91D8` | `0x000AC1D8` | `53 6E 64 50 6C 61 79 65 72 31 5F 43 67 73 53 74 72 65 61 6D 4D 6F 64 00` | `"SndPlayer1_CgsStreamMod"` |
| StreamMod vtable `0x820AE178` | `0x000B1178` | `82 6C 37 E8 82 6D B5 88 82 68 FE 88 82 6A A9 80` | Release, Event, ticks, deleting destructor |
| GainArray descriptor `0x82F2E664` | `0x00F31664` | `82 0A 91 CC 82 68 9E 08 82 6C 3A 10 00 00 00 00 82 68 CD B0 82 F2 E6 60 82 F2 E6 98 00 00 00 00 00 00 00 00 00 00 00 00 4A 47 41 30 04 00 06 00 00 00 00 00` | name, GetSize/Create/null-Pre/Process, metadata, null tool-side/link, `JGA0`, tail `4,0,6,0,0,0,0,0` |
| GainArray name `0x820A91CC` | `0x000AC1CC` | `47 61 69 6E 41 72 72 61 79 00` | `"GainArray"` |
| GainArray vtable `0x820AE188` | `0x000B1188` | `82 84 CB 38 82 84 CB 38 82 7E 2F 38 82 6A A9 E0` | no-op Release, no-op Event, zero ticks, deleting destructor |

## 2. TARGET 1 - SndPlayer1_CgsStreamMod

ABI convention for every subsection (a): the register list given there is exhaustive
for values consumed by the body, and there are no caller-supplied stack arguments in
any decoded StreamMod body.  All signatures use the X360 PowerPC register ABI (the
exporter's `__fastcall` spelling): integer/pointer arguments in `r3` onward, floating
arguments in the named FPR, and results in `r3`/`f1` as stated.  Stack-frame slots
visible in the tables are locals/save areas.  Registers explicitly described as merely
live at an indirect dispatch are not additional semantic parameters.

### Console record vocabulary used by the sketches

These names come from
`references/DecFIGS/dwarfdump/GameShared/GameClasses/Sound/Playback/Plugins/Streaming/internal/sndplayer1.h`;
the offsets/counts below are independently attested by ARTIST assembly.

```cpp
enum RequestState : u8 { FREE=0, QUEUED=1, FEEDING=2, FEEDCOMPLETE=3, COMPLETE=4 };
enum StreamState : u32 { READ_HEADER=0, READ_CHUNK=1, SUBMIT_CHUNK=2 };

struct RequestInternalX360 {                 // stride 0x20
    f64 startTime;                            // +00
    Decoder* pDecoder;                        // +08
    f32 requestHandle;                        // +0C
    f32 sampleRate;                           // +10
    s32 numSamples;                           // +14
    s32 loopStart;                            // +18
    u16 decoderInstanceSize;                  // +1C
    u8 state;                                 // +1E
    u8 numChannels;                           // +1F
};
struct FeedDescX360 {                         // stride 0x0C, count 20
    bool streamed; u8 pad01[3];               // +00
    s32 chunkSamplesPlayed;                   // +04
    u8 decoderRequestHandle;                  // +08
    u8 feedState;                             // +09
    u8 requestIndex; u8 pad0B;                // +0A
};
struct ChunkX360 { u32 size; u8* buf; };      // stride 8
struct RequestExternalX360 {                  // stride 0x88
    f64 streamFileOffset;                     // +00
    u8* pSampleData;                          // +08
    s32 loopStartStreamOffset;                // +0C
    s32 gigaSamplesInRam;                     // +10
    s32 numSamplesFed;                        // +14
    s32 numBytesFed;                          // +18
    char* pStreamLoopFileName;                 // +1C
    CgsFileSystem::ReadStream* pReadStream;    // +20
    StreamState streamState;                  // +24
    u8* pStreamBuffer;                        // +28
    ChunkX360 chunks[6];                      // +2C..+5B
    u32 readBufferSelect;                     // +5C
    u32 writeBufferSelect;                    // +60
    u32 unlockBufferSelect;                   // +64
    u32 readSize;                             // +68
    u32 readPointer;                          // +6C
    u32 queuedChunks;                         // +70
    u32 lockedChunks;                         // +74
    u8 codec, playType, latestFeedSlot, expelMode; // +78..+7B
    u8* pNextChunk;                           // +7C
    u8* pLoopStartChunk;                      // +80
};
```

### `GetSize` — `0x826A4210`

#### (a) Exact signature / dispatch ABI

Descriptor callback invoked by `Voice::CreateInstance` with `r3 = const
VoiceStageConfig*`; return is `u32` in `r3`.  `config+0` is the constructor-parameter
pointer and `config+8` supplies the output-channel byte.  Faithful semantic signature:
`static u32 GetSize(const VoiceStageConfig* config)`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826A4210.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826A4210` | `lwz r11, 0(r3)` | Load from r11, 0(r3). |
| `0x826A4214` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4218` | `beq cr6, loc_826A4234` | Conditional branch to cr6, loc_826A4234 according to the named CR/CTR condition. |
| `0x826A421C` | `addi r10, r1, back_chain` | Integer/address arithmetic: r10, r1, back_chain. |
| `0x826A4220` | `lfs f0, 0(r11)` | Load from f0, 0(r11). |
| `0x826A4224` | `fctidz f0, f0` | Execute the exact PPC operation shown: f0, f0. |
| `0x826A4228` | `stfiwx f0, 0, r10` | Store the source value to f0, 0, r10. |
| `0x826A422C` | `lwz r11, back_chain(r1)` | Load from r11, back_chain(r1). |
| `0x826A4230` | `b loc_826A4238` | Branch unconditionally to loc_826A4238. |
| `0x826A4234` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826A4238` | `lbz r9, 8(r3)` | Load from r9, 8(r3). |
| `0x826A423C` | `slwi r10, r11, 5` | Shift/rotate/mask or width-normalize: r10, r11, 5. |
| `0x826A4240` | `rotlwi r11, r9, 2` | Shift/rotate/mask or width-normalize: r11, r9, 2. |
| `0x826A4244` | `addi r11, r11, 0x18F` | Integer/address arithmetic: r11, r11, 0x18F. |
| `0x826A4248` | `clrrwi r11, r11, 3` | Shift/rotate/mask or width-normalize: r11, r11, 3. |
| `0x826A424C` | `add r3, r11, r10` | Integer/address arithmetic: r3, r11, r10. |
| `0x826A4250` | `blr` | Return to the caller through LR. |
| `0x826A4254` | `.long 0` | Adjacent exported data/alignment word: 0. |

#### (c) Rodata constants

None.  `1`, `5-bit request stride`, `0x18F`, and the alignment mask are immediates.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| config `+0x00` | optional pointer, first `f32` converted to integer | `VoiceStageConfig::mpContext` -> `maxRequests` |
| config `+0x08` | `lbz` | low byte of `mFlagAndField8`, output channels |
| result fixed `+0x188` | implicit in formula | first byte of variable declick array |
| result dynamic | `+0x20 * maxRequests` | inline `RequestInternal[]` |

#### (e) Implementation-grade C++ sketch

```cpp
static u32 GetSize(const VoiceStageConfig* c)
{
    const s32 requests = c->mpContext
        ? static_cast<s32>(*static_cast<const f32*>(c->mpContext)) : 1;
    const u32 requestOffset = AlignUp(0x188u + 4u * LowByte(c->mFlagAndField8), 8u);
    return requestOffset + 0x20u * requests;
}
```

X64 hazards: pointer members in the object and `RequestInternal::pDecoder` widen;
console stride `0x20` and fixed extent `0x188` therefore do not survive.  No deferred
command is involved and no pointer is intentionally narrow.  **GetSize must call one
host layout computation shared with CreateInstance**, using host `sizeof`/alignment and
checking the retained 16-bit relative offsets; transliterating the console return is
wrong.

### `CreateInstance` — `0x826EA508`

#### (a) Exact signature / dispatch ABI

Descriptor callback call site supplies `r3 = PlugIn*` (already base-initialized by
`PlugIn::CreateInstance`) and `r4 = VoiceStageConfig::mpContext`; `r5` still contains
the descriptor, `r6` the `VoiceStageConfig*`, and `r7` the input-channel flag at the
indirect call `0x82B6A864..0x82B6A870`.  This body consumes only `r3/r4`; result bool
is in `r3`.  The callback consumes the first context value as `f32 maxRequests`,
defaulting to one:
`static bool CreateInstance(PlugIn* instance, void* constructorParams)`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826EA508.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826EA508` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826EA50C` | `bl __savegprlr_19` | Call __savegprlr_19; place the return address in LR. |
| `0x826EA510` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826EA514` | `mr r31, r3` | Copy register value: r31, r3. |
| `0x826EA518` | `cmplwi cr6, r4, 0` | Compare cr6, r4, 0 and update the specified condition register. |
| `0x826EA51C` | `beq cr6, loc_826EA538` | Conditional branch to cr6, loc_826EA538 according to the named CR/CTR condition. |
| `0x826EA520` | `addi r11, r1, 0xD0+var_80` | Integer/address arithmetic: r11, r1, 0xD0+var_80. |
| `0x826EA524` | `lfs f0, 0(r4)` | Load from f0, 0(r4). |
| `0x826EA528` | `fctidz f0, f0` | Execute the exact PPC operation shown: f0, f0. |
| `0x826EA52C` | `stfiwx f0, 0, r11` | Store the source value to f0, 0, r11. |
| `0x826EA530` | `lwz r28, 0xD0+var_80(r1)` | Load from r28, 0xD0+var_80(r1). |
| `0x826EA534` | `b loc_826EA53C` | Branch unconditionally to loc_826EA53C. |
| `0x826EA538` | `li r28, 1` | Materialize immediate/address component: r28, 1. |
| `0x826EA53C` | `cmplwi cr6, r31, 0` | Compare cr6, r31, 0 and update the specified condition register. |
| `0x826EA540` | `beq cr6, loc_826EA558` | Conditional branch to cr6, loc_826EA558 according to the named CR/CTR condition. |
| `0x826EA544` | `lis r11, off_820AE178@ha` | Materialize immediate/address component: r11, off_820AE178@ha. |
| `0x826EA548` | `addi r3, r31, 0x40 # '@'` | Integer/address arithmetic: r3, r31, 0x40 # '@'. |
| `0x826EA54C` | `addi r11, r11, off_820AE178@l` | Integer/address arithmetic: r11, r11, off_820AE178@l. |
| `0x826EA550` | `stw r11, 0(r31)` | Store the source value to r11, 0(r31). |
| `0x826EA554` | `bl rw__audio__core__TimerHandle__TimerHandle` | Call rw__audio__core__TimerHandle__TimerHandle; place the return address in LR. |
| `0x826EA558` | `lbz r10, 0x21(r31)` | Load from r10, 0x21(r31). |
| `0x826EA55C` | `addi r11, r31, 0x18F` | Integer/address arithmetic: r11, r31, 0x18F. |
| `0x826EA560` | `addi r19, r31, 0x28 # '('` | Integer/address arithmetic: r19, r31, 0x28 # '('. |
| `0x826EA564` | `lwz r3, 4(r31)` | Load from r3, 4(r31). |
| `0x826EA568` | `rotlwi r10, r10, 2` | Shift/rotate/mask or width-normalize: r10, r10, 2. |
| `0x826EA56C` | `clrrwi r11, r11, 3` | Shift/rotate/mask or width-normalize: r11, r11, 3. |
| `0x826EA570` | `li r30, 0` | Materialize immediate/address component: r30, 0. |
| `0x826EA574` | `add r10, r10, r11` | Integer/address arithmetic: r10, r10, r11. |
| `0x826EA578` | `subf r11, r31, r11` | Integer/address arithmetic: r11, r31, r11. |
| `0x826EA57C` | `stw r19, 0xC(r31)` | Store the source value to r19, 0xC(r31). |
| `0x826EA580` | `addi r10, r10, 7` | Integer/address arithmetic: r10, r10, 7. |
| `0x826EA584` | `lis r9, aSndplayer1Cgss_2@ha` | Materialize immediate/address component: r9, aSndplayer1Cgss_2@ha. |
| `0x826EA588` | `rlwinm r10, r10, 0,16,28` | Shift/rotate/mask or width-normalize: r10, r10, 0,16,28. |
| `0x826EA58C` | `stb r30, 0x187(r31)` | Store the source value to r30, 0x187(r31). |
| `0x826EA590` | `addi r5, r9, aSndplayer1Cgss_2@l# "SndPlayer1_CgsStreamMod RequestExternal"...` | Integer/address arithmetic: r5, r9, aSndplayer1Cgss_2@l# "SndPlayer1_CgsStreamMod RequestExternal".... |
| `0x826EA594` | `subf r10, r31, r10` | Integer/address arithmetic: r10, r31, r10. |
| `0x826EA598` | `sth r11, 0x17A(r31)` | Store the source value to r11, 0x17A(r31). |
| `0x826EA59C` | `li r7, 0` | Materialize immediate/address component: r7, 0. |
| `0x826EA5A0` | `li r6, 0x10` | Materialize immediate/address component: r6, 0x10. |
| `0x826EA5A4` | `mulli r4, r28, 0x88` | Integer/address arithmetic: r4, r28, 0x88. |
| `0x826EA5A8` | `sth r10, 0x17C(r31)` | Store the source value to r10, 0x17C(r31). |
| `0x826EA5AC` | `bl rw__audio__core__System__Alloc` | Call rw__audio__core__System__Alloc; place the return address in LR. |
| `0x826EA5B0` | `stw r3, 0x58(r31)` | Store the source value to r3, 0x58(r31). |
| `0x826EA5B4` | `cmplwi cr6, r3, 0` | Compare cr6, r3, 0 and update the specified condition register. |
| `0x826EA5B8` | `beq cr6, loc_826EA7B4` | Conditional branch to cr6, loc_826EA7B4 according to the named CR/CTR condition. |
| `0x826EA5BC` | `cmplwi cr6, r28, 0` | Compare cr6, r28, 0 and update the specified condition register. |
| `0x826EA5C0` | `stb r28, 0x182(r31)` | Store the source value to r28, 0x182(r31). |
| `0x826EA5C4` | `beq cr6, loc_826EA6F4` | Conditional branch to cr6, loc_826EA6F4 according to the named CR/CTR condition. |
| `0x826EA5C8` | `lis r11, aPthisMprequest@ha` | Materialize immediate/address component: r11, aPthisMprequest@ha. |
| `0x826EA5CC` | `mr r29, r30` | Copy register value: r29, r30. |
| `0x826EA5D0` | `addi r22, r11, aPthisMprequest@l# "pThis->mpRequestExternal[i].maChunk[j]."...` | Integer/address arithmetic: r22, r11, aPthisMprequest@l# "pThis->mpRequestExternal[i].maChunk[j].".... |
| `0x826EA5D4` | `lis r11, aGamesharedGame_104@ha` | Materialize immediate/address component: r11, aGamesharedGame_104@ha. |
| `0x826EA5D8` | `mr r26, r30` | Copy register value: r26, r30. |
| `0x826EA5DC` | `addi r21, r11, aGamesharedGame_104@l# "..\\..\\..\\GameShared\\GameClasses\\So"...` | Integer/address arithmetic: r21, r11, aGamesharedGame_104@l# "..\\..\\..\\GameShared\\GameClasses\\So".... |
| `0x826EA5E0` | `lis r11, aSndplayer1Cgss_1@ha` | Materialize immediate/address component: r11, aSndplayer1Cgss_1@ha. |
| `0x826EA5E4` | `mr r20, r28` | Copy register value: r20, r28. |
| `0x826EA5E8` | `addi r24, r11, aSndplayer1Cgss_1@l# "SndPlayer1_CgsStreamMod Chunk"` | Integer/address arithmetic: r24, r11, aSndplayer1Cgss_1@l# "SndPlayer1_CgsStreamMod Chunk". |
| `0x826EA5EC` | `li r25, 4` | Materialize immediate/address component: r25, 4. |
| `0x826EA5F0` | `li r23, 0x1964` | Materialize immediate/address component: r23, 0x1964. |
| `0x826EA5F4` | `lhz r11, 0x17C(r31)` | Load from r11, 0x17C(r31). |
| `0x826EA5F8` | `addi r28, r29, 0x30 # '0'` | Integer/address arithmetic: r28, r29, 0x30 # '0'. |
| `0x826EA5FC` | `li r27, 6` | Materialize immediate/address component: r27, 6. |
| `0x826EA600` | `add r11, r11, r26` | Integer/address arithmetic: r11, r11, r26. |
| `0x826EA604` | `add r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x826EA608` | `stb r30, 0x1E(r11)` | Store the source value to r30, 0x1E(r11). |
| `0x826EA60C` | `lwz r11, 0x58(r31)` | Load from r11, 0x58(r31). |
| `0x826EA610` | `add r11, r29, r11` | Integer/address arithmetic: r11, r29, r11. |
| `0x826EA614` | `stw r30, 0x20(r11)` | Store the source value to r30, 0x20(r11). |
| `0x826EA618` | `lwz r11, 0x58(r31)` | Load from r11, 0x58(r31). |
| `0x826EA61C` | `add r11, r29, r11` | Integer/address arithmetic: r11, r29, r11. |
| `0x826EA620` | `stw r25, 0x68(r11)` | Store the source value to r25, 0x68(r11). |
| `0x826EA624` | `lwz r11, 0x58(r31)` | Load from r11, 0x58(r31). |
| `0x826EA628` | `add r11, r29, r11` | Integer/address arithmetic: r11, r29, r11. |
| `0x826EA62C` | `stw r30, 0x6C(r11)` | Store the source value to r30, 0x6C(r11). |
| `0x826EA630` | `lwz r11, 0x58(r31)` | Load from r11, 0x58(r31). |
| `0x826EA634` | `add r11, r29, r11` | Integer/address arithmetic: r11, r29, r11. |
| `0x826EA638` | `stw r30, 0x5C(r11)` | Store the source value to r30, 0x5C(r11). |
| `0x826EA63C` | `lwz r11, 0x58(r31)` | Load from r11, 0x58(r31). |
| `0x826EA640` | `add r11, r29, r11` | Integer/address arithmetic: r11, r29, r11. |
| `0x826EA644` | `stw r30, 0x60(r11)` | Store the source value to r30, 0x60(r11). |
| `0x826EA648` | `lwz r11, 0x58(r31)` | Load from r11, 0x58(r31). |
| `0x826EA64C` | `add r11, r29, r11` | Integer/address arithmetic: r11, r29, r11. |
| `0x826EA650` | `stw r30, 0x64(r11)` | Store the source value to r30, 0x64(r11). |
| `0x826EA654` | `lwz r11, 0x58(r31)` | Load from r11, 0x58(r31). |
| `0x826EA658` | `add r11, r29, r11` | Integer/address arithmetic: r11, r29, r11. |
| `0x826EA65C` | `stw r30, 0x70(r11)` | Store the source value to r30, 0x70(r11). |
| `0x826EA660` | `lwz r11, 0x58(r31)` | Load from r11, 0x58(r31). |
| `0x826EA664` | `add r11, r29, r11` | Integer/address arithmetic: r11, r29, r11. |
| `0x826EA668` | `stw r30, 0x74(r11)` | Store the source value to r30, 0x74(r11). |
| `0x826EA66C` | `lwz r11, 0x58(r31)` | Load from r11, 0x58(r31). |
| `0x826EA670` | `add r11, r29, r11` | Integer/address arithmetic: r11, r29, r11. |
| `0x826EA674` | `stw r30, 0x24(r11)` | Store the source value to r30, 0x24(r11). |
| `0x826EA678` | `stw r30, 0x170(r31)` | Store the source value to r30, 0x170(r31). |
| `0x826EA67C` | `lwz r11, 0x58(r31)` | Load from r11, 0x58(r31). |
| `0x826EA680` | `li r7, 0` | Materialize immediate/address component: r7, 0. |
| `0x826EA684` | `li r6, 0x10` | Materialize immediate/address component: r6, 0x10. |
| `0x826EA688` | `add r11, r28, r11` | Integer/address arithmetic: r11, r28, r11. |
| `0x826EA68C` | `mr r5, r24` | Copy register value: r5, r24. |
| `0x826EA690` | `li r4, 0x1964` | Materialize immediate/address component: r4, 0x1964. |
| `0x826EA694` | `stw r23, -4(r11)` | Store the source value to r23, -4(r11). |
| `0x826EA698` | `lwz r3, 4(r31)` | Load from r3, 4(r31). |
| `0x826EA69C` | `bl rw__audio__core__System__Alloc` | Call rw__audio__core__System__Alloc; place the return address in LR. |
| `0x826EA6A0` | `lwz r11, 0x58(r31)` | Load from r11, 0x58(r31). |
| `0x826EA6A4` | `stwx r3, r28, r11` | Store the source value to r3, r28, r11. |
| `0x826EA6A8` | `lwz r11, 0x58(r31)` | Load from r11, 0x58(r31). |
| `0x826EA6AC` | `lwzx r11, r28, r11` | Load from r11, r28, r11. |
| `0x826EA6B0` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA6B4` | `bne cr6, loc_826EA6D0` | Conditional branch to cr6, loc_826EA6D0 according to the named CR/CTR condition. |
| `0x826EA6B8` | `bl CgsDev__Assert__BeginAssert` | Call CgsDev__Assert__BeginAssert; place the return address in LR. |
| `0x826EA6BC` | `li r5, 0x45C` | Materialize immediate/address component: r5, 0x45C. |
| `0x826EA6C0` | `mr r4, r21` | Copy register value: r4, r21. |
| `0x826EA6C4` | `mr r3, r22` | Copy register value: r3, r22. |
| `0x826EA6C8` | `bl CgsDev__Assert__FireAssert` | Call CgsDev__Assert__FireAssert; place the return address in LR. |
| `0x826EA6CC` | `bl CgsDev__Assert__EndAssert` | Call CgsDev__Assert__EndAssert; place the return address in LR. |
| `0x826EA6D0` | `addi r27, r27, -1` | Integer/address arithmetic: r27, r27, -1. |
| `0x826EA6D4` | `addi r28, r28, 8` | Integer/address arithmetic: r28, r28, 8. |
| `0x826EA6D8` | `cmplwi cr6, r27, 0` | Compare cr6, r27, 0 and update the specified condition register. |
| `0x826EA6DC` | `bne cr6, loc_826EA67C` | Conditional branch to cr6, loc_826EA67C according to the named CR/CTR condition. |
| `0x826EA6E0` | `addi r20, r20, -1` | Integer/address arithmetic: r20, r20, -1. |
| `0x826EA6E4` | `addi r26, r26, 0x20 # ' '` | Integer/address arithmetic: r26, r26, 0x20 # ' '. |
| `0x826EA6E8` | `addi r29, r29, 0x88` | Integer/address arithmetic: r29, r29, 0x88. |
| `0x826EA6EC` | `cmplwi cr6, r20, 0` | Compare cr6, r20, 0 and update the specified condition register. |
| `0x826EA6F0` | `bne cr6, loc_826EA5F4` | Conditional branch to cr6, loc_826EA5F4 according to the named CR/CTR condition. |
| `0x826EA6F4` | `lis r11, flt_82001CC0@ha` | Materialize immediate/address component: r11, flt_82001CC0@ha. |
| `0x826EA6F8` | `lbz r10, 0x21(r31)` | Load from r10, 0x21(r31). |
| `0x826EA6FC` | `stb r30, 0x181(r31)` | Store the source value to r30, 0x181(r31). |
| `0x826EA700` | `stb r30, 0x180(r31)` | Store the source value to r30, 0x180(r31). |
| `0x826EA704` | `stb r30, 0x17F(r31)` | Store the source value to r30, 0x17F(r31). |
| `0x826EA708` | `stw r30, 0x158(r31)` | Store the source value to r30, 0x158(r31). |
| `0x826EA70C` | `lfs f0, flt_82001CC0@l(r11)` | Load from f0, flt_82001CC0@l(r11). |
| `0x826EA710` | `lis r11, dbl_82001CA8@ha` | Materialize immediate/address component: r11, dbl_82001CA8@ha. |
| `0x826EA714` | `stb r10, 0x17E(r31)` | Store the source value to r10, 0x17E(r31). |
| `0x826EA718` | `stfs f0, 0(r19)` | Store the source value to f0, 0(r19). |
| `0x826EA71C` | `stfs f0, 0x160(r31)` | Store the source value to f0, 0x160(r31). |
| `0x826EA720` | `stw r30, 0x15C(r31)` | Store the source value to r30, 0x15C(r31). |
| `0x826EA724` | `stfs f0, 0x164(r31)` | Store the source value to f0, 0x164(r31). |
| `0x826EA728` | `stb r30, 0x184(r31)` | Store the source value to r30, 0x184(r31). |
| `0x826EA72C` | `stfs f0, 0x168(r31)` | Store the source value to f0, 0x168(r31). |
| `0x826EA730` | `stb r30, 0x183(r31)` | Store the source value to r30, 0x183(r31). |
| `0x826EA734` | `lfd f13, dbl_82001CA8@l(r11)` | Load from f13, dbl_82001CA8@l(r11). |
| `0x826EA738` | `lis r11, flt_820AA808@ha` | Materialize immediate/address component: r11, flt_820AA808@ha. |
| `0x826EA73C` | `stfd f13, 0x38(r31)` | Store the source value to f13, 0x38(r31). |
| `0x826EA740` | `stb r30, 0x185(r31)` | Store the source value to r30, 0x185(r31). |
| `0x826EA744` | `stfd f13, 0x30(r31)` | Store the source value to f13, 0x30(r31). |
| `0x826EA748` | `stb r30, 0x186(r31)` | Store the source value to r30, 0x186(r31). |
| `0x826EA74C` | `stfs f0, 0x150(r31)` | Store the source value to f0, 0x150(r31). |
| `0x826EA750` | `li r10, 0x14` | Materialize immediate/address component: r10, 0x14. |
| `0x826EA754` | `lfs f12, flt_820AA808@l(r11)` | Load from f12, flt_820AA808@l(r11). |
| `0x826EA758` | `addi r11, r31, 0x5C # '\'` | Integer/address arithmetic: r11, r31, 0x5C # '\'. |
| `0x826EA75C` | `stfs f12, 0x154(r31)` | Store the source value to f12, 0x154(r31). |
| `0x826EA760` | `stfs f12, 0x16C(r31)` | Store the source value to f12, 0x16C(r31). |
| `0x826EA764` | `addi r10, r10, -1` | Integer/address arithmetic: r10, r10, -1. |
| `0x826EA768` | `stb r30, 9(r11)` | Store the source value to r30, 9(r11). |
| `0x826EA76C` | `stb r30, 0(r11)` | Store the source value to r30, 0(r11). |
| `0x826EA770` | `addi r11, r11, 0xC` | Integer/address arithmetic: r11, r11, 0xC. |
| `0x826EA774` | `cmplwi cr6, r10, 0` | Compare cr6, r10, 0 and update the specified condition register. |
| `0x826EA778` | `bne cr6, loc_826EA764` | Conditional branch to cr6, loc_826EA764 according to the named CR/CTR condition. |
| `0x826EA77C` | `lis r10, aSndplayer@ha` | Materialize immediate/address component: r10, aSndplayer@ha. |
| `0x826EA780` | `lwz r11, 4(r31)` | Load from r11, 4(r31). |
| `0x826EA784` | `li r9, 1` | Materialize immediate/address component: r9, 1. |
| `0x826EA788` | `addi r7, r10, aSndplayer@l# "SndPlayer"` | Integer/address arithmetic: r7, r10, aSndplayer@l# "SndPlayer". |
| `0x826EA78C` | `lis r10, rw__audio__core__SndPlayer1_CgsStreamMod__RwacTimerClient@ha` | Materialize immediate/address component: r10, rw__audio__core__SndPlayer1_CgsStreamMod__RwacTimerClient@ha. |
| `0x826EA790` | `li r8, 1` | Materialize immediate/address component: r8, 1. |
| `0x826EA794` | `mr r6, r31` | Copy register value: r6, r31. |
| `0x826EA798` | `addi r5, r10, rw__audio__core__SndPlayer1_CgsStreamMod__RwacTimerClient@l` | Integer/address arithmetic: r5, r10, rw__audio__core__SndPlayer1_CgsStreamMod__RwacTimerClient@l. |
| `0x826EA79C` | `addi r4, r31, 0x40 # '@'` | Integer/address arithmetic: r4, r31, 0x40 # '@'. |
| `0x826EA7A0` | `addi r3, r11, 0x60 # '\`'` | Integer/address arithmetic: r3, r11, 0x60 # '\`'. |
| `0x826EA7A4` | `bl rw__audio__core__TimerManager__AddTimer` | Call rw__audio__core__TimerManager__AddTimer; place the return address in LR. |
| `0x826EA7A8` | `clrlwi r11, r3, 24` | Shift/rotate/mask or width-normalize: r11, r3, 24. |
| `0x826EA7AC` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA7B0` | `beq cr6, loc_826EA7C0` | Conditional branch to cr6, loc_826EA7C0 according to the named CR/CTR condition. |
| `0x826EA7B4` | `li r3, 0` | Materialize immediate/address component: r3, 0. |
| `0x826EA7B8` | `addi r1, r1, 0xD0` | Integer/address arithmetic: r1, r1, 0xD0. |
| `0x826EA7BC` | `b __restgprlr_19` | Branch unconditionally to __restgprlr_19. |
| `0x826EA7C0` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826EA7C4` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x826EA7C8` | `stb r11, 0x187(r31)` | Store the source value to r11, 0x187(r31). |
| `0x826EA7CC` | `addi r1, r1, 0xD0` | Integer/address arithmetic: r1, r1, 0xD0. |
| `0x826EA7D0` | `b __restgprlr_19` | Branch unconditionally to __restgprlr_19. |

#### (c) Rodata constants

| VA | file_off | Raw bytes | Decode/use |
|---:|---:|---|---|
| `0x820AE178` | `0x000B1178` | `82 6C 37 E8 82 6D B5 88 82 68 FE 88 82 6A A9 80` | four-slot StreamMod vtable |
| `0x82001CC0` | `0x00004CC0` | `00 00 00 00` | `0.0f` |
| `0x82001CA8` | `0x00004CA8` | `00 00 00 00 00 00 00 00` | `0.0` |
| `0x820AA808` | `0x000AD808` | `47 3B 80 00` | `48000.0f` |
| `0x820B666C` | `0x000B966C` | `53 6E 64 50 6C 61 79 65 72 31 5F 43 67 73 53 74 72 65 61 6D 4D 6F 64 20 52 65 71 75 65 73 74 45 78 74 65 72 6E 61 6C 20 61 72 72 61 79 00` | allocation tag `"SndPlayer1_CgsStreamMod RequestExternal array"` |
| `0x820B64A0` | `0x000B94A0` | `53 6E 64 50 6C 61 79 65 72 31 5F 43 67 73 53 74 72 65 61 6D 4D 6F 64 20 43 68 75 6E 6B 00` | chunk allocation tag |
| `0x820B6640` | `0x000B9640` | `70 54 68 69 73 2D 3E 6D 70 52 65 71 75 65 73 74 45 78 74 65 72 6E 61 6C 5B 69 5D 2E 6D 61 43 68 75 6E 6B 5B 6A 5D 2E 62 75 66 00` | allocation assert expression |
| `0x820B65D8` | `0x000B95D8` | `2E 2E 5C 2E 2E 5C 2E 2E 5C 47 61 6D 65 53 68 61 72 65 64 5C 47 61 6D 65 43 6C 61 73 73 65 73 5C 53 6F 75 6E 64 2F 50 6C 61 79 62 61 63 6B 2F 50 6C 75 67 69 6E 73 2F 53 74 72 65 61 6D 69 6E 67 2F 69 6E 74 65 72 6E 61 6C 2F 73 6E 64 70 6C 61 79 65 72 31 2E 63 70 70 00` | assert source path |
| `0x820B6634` | `0x000B9634` | `53 6E 64 50 6C 61 79 65 72 00` | timer name `"SndPlayer"` |

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x00` | store `0x820AE178` | hidden vptr |
| `+0x04` | load | `PlugIn::mpSystemUseGetSystemAccessor` |
| `+0x0C` | store `this+0x28` | `PlugIn::mpAttribute` |
| `+0x21` | load | `PlugIn::mOutputChannels` |
| `+0x28/+0x30/+0x38` | zero float/doubles | three attributes: handle/progress/duration |
| `+0x40` | placement TimerHandle; AddTimer handle | `mTimerHandle` |
| `+0x58` | store allocation | `mpRequestExternal` |
| `+0x5C + 0x0C*i` | clear `+0` and `+9`, 20 records | `mFeedDesc[i].streamed/feedState` |
| `+0x150..+0x16C` | initialize current/cache/handle/rate fields | DecFIGS names shown in shared-layout audit below |
| `+0x170/+0x174` | `muDataReadForNewSize` cleared; byte array filled later | new-size header state |
| `+0x17A` | store `0x188` relative | `mDeclickBufferOffset` |
| `+0x17C` | store aligned dynamic offset | `mRequestInternalOffset` |
| `+0x17E..+0x187` | counts/cursors/flags | max channels; request/feed cursors; timer flag |
| external `+0x20/+0x24/+0x5C..+0x74` | initialized | read-stream state/ring counters |
| external `+0x2C+8*j` | `size=6500`, allocated buffer | six `Chunk` records |
| internal `+0x1E` | clear for each request | `RequestInternal::state=FREE` |

#### (e) Implementation-grade C++ sketch

```cpp
static bool CreateInstance(PlugIn* base, void* params)
{
    auto* self = static_cast<SndPlayer1_CgsStreamMod*>(base);
    const s32 n = params ? static_cast<s32>(*static_cast<f32*>(params)) : 1;
    new (&self->mTimerHandle) TimerHandle;
    self->mpAttribute = self->mAttribute;
    const HostLayout l = ComputeHostLayout(self->mOutputChannels, n);
    self->mDeclickBufferOffset = CheckedU16(l.declickOffset);
    self->mRequestInternalOffset = CheckedU16(l.requestOffset);
    self->mTimerAdded = 0;

    self->mpRequestExternal = static_cast<RequestExternal*>(
        System::Alloc(self->mpSystemUseGetSystemAccessor,
                      sizeof(RequestExternal) * n,
                      "SndPlayer1_CgsStreamMod RequestExternal array", 16, nullptr));
    if (!self->mpRequestExternal) return false;
    self->mMaxRequests = static_cast<u8>(n);

    for (s32 i=0; i<n; ++i) {
        self->Request(i).state = FREE;
        RequestExternal& e = self->mpRequestExternal[i];
        e.pReadStream=nullptr; e.streamState=READ_HEADER;
        e.readBufferSelect=e.writeBufferSelect=e.unlockBufferSelect=0;
        e.readSize=4; e.readPointer=0; e.queuedChunks=e.lockedChunks=0;
        self->muDataReadForNewSize=0; // faithfully repeated by the console loop
        for (u32 j=0; j<6; ++j) {
            e.chunks[j].size=6500;
            e.chunks[j].buf=static_cast<u8*>(System::Alloc(self->mpSystemUseGetSystemAccessor,
                6500, "SndPlayer1_CgsStreamMod Chunk", 16, nullptr));
            CGS_ASSERT(e.chunks[j].buf, "pThis->mpRequestExternal[i].maChunk[j].buf");
        }
    }
    self->mCurrentRequest=self->mNextRequestToFree=self->mNextFreeRequest=0;
    self->mCurrentRequestSamplesPlayed=self->mCurrentRequestNumSamples=0;
    self->mMaxChannels=self->mOutputChannels;
    self->mAttribute[0].mfValue=self->mRequestHandle=self->mLastRequestHandleProcessed=
        self->mLastRequestHandleSuccessfullyProcessed=self->mCurrentRequestHandle=0.0f;
    self->mAttribute[1].mfValue=self->mAttribute[2].mfValue=0.0f;
    self->mDcOffsetsGathered=self->mNumDeclickSamples=0;
    self->mNextFeedSlotToFill=self->mNextFeedSlotToFree=0;
    self->mCurrentRequestSampleRate=self->mPreviousSampleRate=48000.0f;
    for (u32 i=0;i<20;++i) { self->mFeedDesc[i].feedState=0; self->mFeedDesc[i].streamed=false; }
    if (TimerManager::AddTimer(&self->mpSystemUseGetSystemAccessor->mTimerManager,
            &self->mTimerHandle, &RwacTimerClient, self, "SndPlayer", 1, 1) != 0)
        return false;
    self->mTimerAdded=1;
    return true;
}
```

X64 hazards: vptr/System/Voice/attribute/descriptor, decoder, external sample/path/read
stream/chunk pointers all widen.  Use host `sizeof(RequestExternal)` (console `0x88`),
host `sizeof(RequestInternal)` (console `0x20`), and typed six-element chunks (console
stride 8).  Feed records contain no pointers and remain a semantic count of 20.  The two
relative offsets are intentionally 16-bit, not pointer fields; range-check them.  No
deferred-command return applies.  GetSize/Create must share `ComputeHostLayout`.

### `PreProcess` — `0x8268CD10`

#### (a) Exact signature / dispatch ABI

Stage callback: `r3=PlugIn*`, `r4=Mixer*`, `r5=bool alreadyProcessed`,
`r6=int requestedSamples`; return count in `r3`.  Semantic signature:
`static int PreProcess(PlugIn*, Mixer*, bool, int)`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x8268CD10.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x8268CD10` | `mr r11, r3` | Copy register value: r11, r3. |
| `0x8268CD14` | `li r3, 0` | Materialize immediate/address component: r3, 0. |
| `0x8268CD18` | `sth r6, 0x178(r11)` | Store the source value to r6, 0x178(r11). |
| `0x8268CD1C` | `blr` | Return to the caller through LR. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `this+0x178` | `sth r6` | `mSamplesRequested` (low 16 bits) |

#### (e) Implementation-grade C++ sketch

```cpp
static int PreProcess(PlugIn* p, Mixer*, bool, int requested)
{
    static_cast<SndPlayer1_CgsStreamMod*>(p)->mSamplesRequested = static_cast<u16>(requested);
    return 0;
}
```

X64 hazards: no pointers or record strides are touched; the 16-bit sample count is
deliberate.  This is not a deferred handler.  No GetSize issue applies.

### `Process` — `0x826A46B0`

#### (a) Exact signature / dispatch ABI

Stage callback: `r3=SndPlayer1_CgsStreamMod*`, `r4=Mixer*`, `r5=bool` (unused),
return `BufferStatus` (`0` unavailable, `1` available) in `r3`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826A46B0.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826A46B0` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826A46B4` | `bl __savegprlr_17` | Call __savegprlr_17; place the return address in LR. |
| `0x826A46B8` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826A46BC` | `mr r31, r3` | Copy register value: r31, r3. |
| `0x826A46C0` | `mr r24, r4` | Copy register value: r24, r4. |
| `0x826A46C4` | `lbz r11, 0x184(r31)` | Load from r11, 0x184(r31). |
| `0x826A46C8` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A46CC` | `beq cr6, loc_826A46E8` | Conditional branch to cr6, loc_826A46E8 according to the named CR/CTR condition. |
| `0x826A46D0` | `lbz r11, 0x183(r31)` | Load from r11, 0x183(r31). |
| `0x826A46D4` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A46D8` | `beq cr6, loc_826A46E8` | Conditional branch to cr6, loc_826A46E8 according to the named CR/CTR condition. |
| `0x826A46DC` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__Declick` | Call rw__audio__core__SndPlayer1_CgsStreamMod__Declick; place the return address in LR. |
| `0x826A46E0` | `addi r1, r1, 0xE0` | Integer/address arithmetic: r1, r1, 0xE0. |
| `0x826A46E4` | `b __restgprlr_17` | Branch unconditionally to __restgprlr_17. |
| `0x826A46E8` | `lbz r11, 0x181(r31)` | Load from r11, 0x181(r31). |
| `0x826A46EC` | `li r20, 0` | Materialize immediate/address component: r20, 0. |
| `0x826A46F0` | `lhz r10, 0x17C(r31)` | Load from r10, 0x17C(r31). |
| `0x826A46F4` | `rotlwi r11, r11, 5` | Shift/rotate/mask or width-normalize: r11, r11, 5. |
| `0x826A46F8` | `mr r18, r20` | Copy register value: r18, r20. |
| `0x826A46FC` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826A4700` | `stw r20, 0x14C(r31)` | Store the source value to r20, 0x14C(r31). |
| `0x826A4704` | `mr r25, r20` | Copy register value: r25, r20. |
| `0x826A4708` | `add r30, r11, r31` | Integer/address arithmetic: r30, r11, r31. |
| `0x826A470C` | `mr r27, r20` | Copy register value: r27, r20. |
| `0x826A4710` | `lbz r11, 0x1E(r30)` | Load from r11, 0x1E(r30). |
| `0x826A4714` | `cmpwi cr6, r11, 4` | Compare cr6, r11, 4 and update the specified condition register. |
| `0x826A4718` | `beq cr6, loc_826A4728` | Conditional branch to cr6, loc_826A4728 according to the named CR/CTR condition. |
| `0x826A471C` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4720` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826A4724` | `bne cr6, loc_826A472C` | Conditional branch to cr6, loc_826A472C according to the named CR/CTR condition. |
| `0x826A4728` | `mr r11, r20` | Copy register value: r11, r20. |
| `0x826A472C` | `lis r10, 3` | Materialize immediate/address component: r10, 3. |
| `0x826A4730` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826A4734` | `ori r21, r10, 0xC # 0x3000C` | Bitwise operation: r21, r10, 0xC # 0x3000C. |
| `0x826A4738` | `lis r10, 3` | Materialize immediate/address component: r10, 3. |
| `0x826A473C` | `li r17, 2` | Materialize immediate/address component: r17, 2. |
| `0x826A4740` | `ori r19, r10, 0x20 # ' ' # 0x30020` | Bitwise operation: r19, r10, 0x20 # ' ' # 0x30020. |
| `0x826A4744` | `lis r10, 3` | Materialize immediate/address component: r10, 3. |
| `0x826A4748` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A474C` | `ori r22, r10, 0x2C # ',' # 0x3002C` | Bitwise operation: r22, r10, 0x2C # ',' # 0x3002C. |
| `0x826A4750` | `lis r10, 3` | Materialize immediate/address component: r10, 3. |
| `0x826A4754` | `ori r23, r10, 0x24 # '$' # 0x30024` | Bitwise operation: r23, r10, 0x24 # '$' # 0x30024. |
| `0x826A4758` | `beq cr6, loc_826A4C24` | Conditional branch to cr6, loc_826A4C24 according to the named CR/CTR condition. |
| `0x826A475C` | `lwz r11, 0x14(r30)` | Load from r11, 0x14(r30). |
| `0x826A4760` | `li r26, 4` | Materialize immediate/address component: r26, 4. |
| `0x826A4764` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4768` | `bne cr6, loc_826A4828` | Conditional branch to cr6, loc_826A4828 according to the named CR/CTR condition. |
| `0x826A476C` | `stb r26, 0x1E(r30)` | Store the source value to r26, 0x1E(r30). |
| `0x826A4770` | `lbz r11, 0x181(r31)` | Load from r11, 0x181(r31). |
| `0x826A4774` | `lbz r10, 0x182(r31)` | Load from r10, 0x182(r31). |
| `0x826A4778` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826A477C` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826A4780` | `mr r9, r11` | Copy register value: r9, r11. |
| `0x826A4784` | `cmplw cr6, r9, r10` | Compare cr6, r9, r10 and update the specified condition register. |
| `0x826A4788` | `stb r11, 0x181(r31)` | Store the source value to r11, 0x181(r31). |
| `0x826A478C` | `bne cr6, loc_826A4794` | Conditional branch to cr6, loc_826A4794 according to the named CR/CTR condition. |
| `0x826A4790` | `stb r20, 0x181(r31)` | Store the source value to r20, 0x181(r31). |
| `0x826A4794` | `lbz r11, 0x181(r31)` | Load from r11, 0x181(r31). |
| `0x826A4798` | `lhz r10, 0x17C(r31)` | Load from r10, 0x17C(r31). |
| `0x826A479C` | `rotlwi r11, r11, 5` | Shift/rotate/mask or width-normalize: r11, r11, 5. |
| `0x826A47A0` | `stw r20, 0x158(r31)` | Store the source value to r20, 0x158(r31). |
| `0x826A47A4` | `stw r20, 0x15C(r31)` | Store the source value to r20, 0x15C(r31). |
| `0x826A47A8` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826A47AC` | `add r30, r11, r31` | Integer/address arithmetic: r30, r11, r31. |
| `0x826A47B0` | `lbz r11, 0x1E(r30)` | Load from r11, 0x1E(r30). |
| `0x826A47B4` | `cmpwi cr6, r11, 4` | Compare cr6, r11, 4 and update the specified condition register. |
| `0x826A47B8` | `beq cr6, loc_826A47C8` | Conditional branch to cr6, loc_826A47C8 according to the named CR/CTR condition. |
| `0x826A47BC` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A47C0` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826A47C4` | `bne cr6, loc_826A47CC` | Conditional branch to cr6, loc_826A47CC according to the named CR/CTR condition. |
| `0x826A47C8` | `mr r11, r20` | Copy register value: r11, r20. |
| `0x826A47CC` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826A47D0` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A47D4` | `beq cr6, loc_826A47F4` | Conditional branch to cr6, loc_826A47F4 according to the named CR/CTR condition. |
| `0x826A47D8` | `stw r20, 0x158(r31)` | Store the source value to r20, 0x158(r31). |
| `0x826A47DC` | `lfs f0, 0xC(r30)` | Load from f0, 0xC(r30). |
| `0x826A47E0` | `stfs f0, 0x150(r31)` | Store the source value to f0, 0x150(r31). |
| `0x826A47E4` | `lfs f0, 0x10(r30)` | Load from f0, 0x10(r30). |
| `0x826A47E8` | `stfs f0, 0x154(r31)` | Store the source value to f0, 0x154(r31). |
| `0x826A47EC` | `lwz r11, 0x14(r30)` | Load from r11, 0x14(r30). |
| `0x826A47F0` | `stw r11, 0x15C(r31)` | Store the source value to r11, 0x15C(r31). |
| `0x826A47F4` | `lbz r11, 0x1E(r30)` | Load from r11, 0x1E(r30). |
| `0x826A47F8` | `cmpwi cr6, r11, 4` | Compare cr6, r11, 4 and update the specified condition register. |
| `0x826A47FC` | `beq cr6, loc_826A480C` | Conditional branch to cr6, loc_826A480C according to the named CR/CTR condition. |
| `0x826A4800` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4804` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826A4808` | `bne cr6, loc_826A4810` | Conditional branch to cr6, loc_826A4810 according to the named CR/CTR condition. |
| `0x826A480C` | `mr r11, r20` | Copy register value: r11, r20. |
| `0x826A4810` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826A4814` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4818` | `beq cr6, loc_826A4C24` | Conditional branch to cr6, loc_826A4C24 according to the named CR/CTR condition. |
| `0x826A481C` | `lwz r11, 0x14(r30)` | Load from r11, 0x14(r30). |
| `0x826A4820` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4824` | `beq cr6, loc_826A476C` | Conditional branch to cr6, loc_826A476C according to the named CR/CTR condition. |
| `0x826A4828` | `lfs f0, 0x10(r30)` | Load from f0, 0x10(r30). |
| `0x826A482C` | `lfs f13, 0x16C(r31)` | Load from f13, 0x16C(r31). |
| `0x826A4830` | `fcmpu cr6, f0, f13` | Compare cr6, f0, f13 and update the specified condition register. |
| `0x826A4834` | `bne cr6, loc_826A4DC0` | Conditional branch to cr6, loc_826A4DC0 according to the named CR/CTR condition. |
| `0x826A4838` | `lbz r11, 0x21(r31)` | Load from r11, 0x21(r31). |
| `0x826A483C` | `lbz r10, 0x1F(r30)` | Load from r10, 0x1F(r30). |
| `0x826A4840` | `cmplw cr6, r10, r11` | Compare cr6, r10, r11 and update the specified condition register. |
| `0x826A4844` | `bne cr6, loc_826A4DC0` | Conditional branch to cr6, loc_826A4DC0 according to the named CR/CTR condition. |
| `0x826A4848` | `lbz r11, 0x186(r31)` | Load from r11, 0x186(r31). |
| `0x826A484C` | `rotlwi r10, r11, 1` | Shift/rotate/mask or width-normalize: r10, r11, 1. |
| `0x826A4850` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826A4854` | `slwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826A4858` | `add r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x826A485C` | `lbz r11, 0x65(r11)` | Load from r11, 0x65(r11). |
| `0x826A4860` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4864` | `bne cr6, loc_826A48B8` | Conditional branch to cr6, loc_826A48B8 according to the named CR/CTR condition. |
| `0x826A4868` | `lbz r9, 0x185(r31)` | Load from r9, 0x185(r31). |
| `0x826A486C` | `lbz r11, 0x186(r31)` | Load from r11, 0x186(r31). |
| `0x826A4870` | `mr r10, r11` | Copy register value: r10, r11. |
| `0x826A4874` | `cmplw cr6, r10, r9` | Compare cr6, r10, r9 and update the specified condition register. |
| `0x826A4878` | `beq cr6, loc_826A48B8` | Conditional branch to cr6, loc_826A48B8 according to the named CR/CTR condition. |
| `0x826A487C` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826A4880` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826A4884` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826A4888` | `cmplwi cr6, r11, 0x14` | Compare cr6, r11, 0x14 and update the specified condition register. |
| `0x826A488C` | `bne cr6, loc_826A4894` | Conditional branch to cr6, loc_826A4894 according to the named CR/CTR condition. |
| `0x826A4890` | `mr r11, r20` | Copy register value: r11, r20. |
| `0x826A4894` | `stb r11, 0x186(r31)` | Store the source value to r11, 0x186(r31). |
| `0x826A4898` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826A489C` | `rotlwi r10, r11, 1` | Shift/rotate/mask or width-normalize: r10, r11, 1. |
| `0x826A48A0` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826A48A4` | `slwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826A48A8` | `add r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x826A48AC` | `lbz r11, 0x65(r11)` | Load from r11, 0x65(r11). |
| `0x826A48B0` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A48B4` | `beq cr6, loc_826A486C` | Conditional branch to cr6, loc_826A486C according to the named CR/CTR condition. |
| `0x826A48B8` | `lbz r11, 0x186(r31)` | Load from r11, 0x186(r31). |
| `0x826A48BC` | `rotlwi r10, r11, 1` | Shift/rotate/mask or width-normalize: r10, r11, 1. |
| `0x826A48C0` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826A48C4` | `slwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826A48C8` | `add r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x826A48CC` | `lbz r11, 0x65(r11)` | Load from r11, 0x65(r11). |
| `0x826A48D0` | `cmplwi cr6, r11, 1` | Compare cr6, r11, 1 and update the specified condition register. |
| `0x826A48D4` | `bne cr6, loc_826A4C24` | Conditional branch to cr6, loc_826A4C24 according to the named CR/CTR condition. |
| `0x826A48D8` | `lis r11, dbl_82001CA8@ha` | Materialize immediate/address component: r11, dbl_82001CA8@ha. |
| `0x826A48DC` | `lfd f1, 0(r30)` | Load from f1, 0(r30). |
| `0x826A48E0` | `lfd f12, dbl_82001CA8@l(r11)` | Load from f12, dbl_82001CA8@l(r11). |
| `0x826A48E4` | `fcmpu cr6, f1, f12` | Compare cr6, f1, f12 and update the specified condition register. |
| `0x826A48E8` | `beq cr6, loc_826A49D4` | Conditional branch to cr6, loc_826A49D4 according to the named CR/CTR condition. |
| `0x826A48EC` | `addi r6, r1, 0xE0+var_90` | Integer/address arithmetic: r6, r1, 0xE0+var_90. |
| `0x826A48F0` | `mr r4, r24` | Copy register value: r4, r24. |
| `0x826A48F4` | `mr r3, r31` | Copy register value: r3, r31. |
| `0x826A48F8` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__WaitForStartTime` | Call rw__audio__core__SndPlayer1_CgsStreamMod__WaitForStartTime; place the return address in LR. |
| `0x826A48FC` | `clrlwi r11, r3, 24` | Shift/rotate/mask or width-normalize: r11, r3, 24. |
| `0x826A4900` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4904` | `bne cr6, loc_826A4910` | Conditional branch to cr6, loc_826A4910 according to the named CR/CTR condition. |
| `0x826A4908` | `stw r20, 0x158(r31)` | Store the source value to r20, 0x158(r31). |
| `0x826A490C` | `b loc_826A4C24` | Branch unconditionally to loc_826A4C24. |
| `0x826A4910` | `lwz r25, 0xE0+var_90(r1)` | Load from r25, 0xE0+var_90(r1). |
| `0x826A4914` | `cmplwi cr6, r25, 0` | Compare cr6, r25, 0 and update the specified condition register. |
| `0x826A4918` | `beq cr6, loc_826A49D0` | Conditional branch to cr6, loc_826A49D0 according to the named CR/CTR condition. |
| `0x826A491C` | `lhz r11, 0x178(r31)` | Load from r11, 0x178(r31). |
| `0x826A4920` | `cmplw cr6, r25, r11` | Compare cr6, r25, r11 and update the specified condition register. |
| `0x826A4924` | `blt cr6, loc_826A492C` | Conditional branch to cr6, loc_826A492C according to the named CR/CTR condition. |
| `0x826A4928` | `mr r25, r11` | Copy register value: r25, r11. |
| `0x826A492C` | `addis r26, r24, 3` | Integer/address arithmetic: r26, r24, 3. |
| `0x826A4930` | `lbz r11, 0x1F(r30)` | Load from r11, 0x1F(r30). |
| `0x826A4934` | `slwi r27, r25, 2` | Shift/rotate/mask or width-normalize: r27, r25, 2. |
| `0x826A4938` | `addi r26, r26, 0x10` | Integer/address arithmetic: r26, r26, 0x10. |
| `0x826A493C` | `mr r29, r20` | Copy register value: r29, r20. |
| `0x826A4940` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4944` | `lwz r28, 0(r26)` | Load from r28, 0(r26). |
| `0x826A4948` | `beq cr6, loc_826A497C` | Conditional branch to cr6, loc_826A497C according to the named CR/CTR condition. |
| `0x826A494C` | `lhz r11, 0xE(r28)` | Load from r11, 0xE(r28). |
| `0x826A4950` | `mr r5, r27# count  ; count` | Copy register value: r5, r27# count  ; count. |
| `0x826A4954` | `lwz r10, 4(r28)` | Load from r10, 4(r28). |
| `0x826A4958` | `li r4, 0# c  ; c` | Materialize immediate/address component: r4, 0# c  ; c. |
| `0x826A495C` | `mullw r11, r11, r29` | Integer/address arithmetic: r11, r11, r29. |
| `0x826A4960` | `slwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826A4964` | `add r3, r11, r10# pDest  ; pDest` | Integer/address arithmetic: r3, r11, r10# pDest  ; pDest. |
| `0x826A4968` | `bl XMemSet` | Call XMemSet; place the return address in LR. |
| `0x826A496C` | `lbz r11, 0x1F(r30)` | Load from r11, 0x1F(r30). |
| `0x826A4970` | `addi r29, r29, 1` | Integer/address arithmetic: r29, r29, 1. |
| `0x826A4974` | `cmplw cr6, r29, r11` | Compare cr6, r29, r11 and update the specified condition register. |
| `0x826A4978` | `blt cr6, loc_826A494C` | Conditional branch to cr6, loc_826A494C according to the named CR/CTR condition. |
| `0x826A497C` | `lis r11, 3` | Materialize immediate/address component: r11, 3. |
| `0x826A4980` | `lwz r10, 0(r26)` | Load from r10, 0(r26). |
| `0x826A4984` | `lis r8, 3` | Materialize immediate/address component: r8, 3. |
| `0x826A4988` | `ori r9, r11, 0x20 # ' ' # 0x30020` | Bitwise operation: r9, r11, 0x20 # ' ' # 0x30020. |
| `0x826A498C` | `addis r11, r24, 3` | Integer/address arithmetic: r11, r24, 3. |
| `0x826A4990` | `lis r7, 3` | Materialize immediate/address component: r7, 3. |
| `0x826A4994` | `addi r11, r11, 0xC` | Integer/address arithmetic: r11, r11, 0xC. |
| `0x826A4998` | `ori r8, r8, 0x2C # ',' # 0x3002C` | Bitwise operation: r8, r8, 0x2C # ',' # 0x3002C. |
| `0x826A499C` | `stwx r25, r24, r9` | Store the source value to r25, r24, r9. |
| `0x826A49A0` | `ori r7, r7, 0x24 # '$' # 0x30024` | Bitwise operation: r7, r7, 0x24 # '$' # 0x30024. |
| `0x826A49A4` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x826A49A8` | `lwz r9, 0(r11)` | Load from r9, 0(r11). |
| `0x826A49AC` | `stw r10, 0(r11)` | Store the source value to r10, 0(r11). |
| `0x826A49B0` | `stw r9, 0(r26)` | Store the source value to r9, 0(r26). |
| `0x826A49B4` | `lbz r11, 0x1F(r30)` | Load from r11, 0x1F(r30). |
| `0x826A49B8` | `stbx r11, r24, r8` | Store the source value to r11, r24, r8. |
| `0x826A49BC` | `lfs f0, 0x10(r30)` | Load from f0, 0x10(r30). |
| `0x826A49C0` | `stfsx f0, r24, r7` | Store the source value to f0, r24, r7. |
| `0x826A49C4` | `stw r20, 0x158(r31)` | Store the source value to r20, 0x158(r31). |
| `0x826A49C8` | `addi r1, r1, 0xE0` | Integer/address arithmetic: r1, r1, 0xE0. |
| `0x826A49CC` | `b __restgprlr_17` | Branch unconditionally to __restgprlr_17. |
| `0x826A49D0` | `stfd f12, 0(r30)` | Store the source value to f12, 0(r30). |
| `0x826A49D4` | `lwz r10, 4(r31)` | Load from r10, 4(r31). |
| `0x826A49D8` | `lhz r11, 0x1C(r30)` | Load from r11, 0x1C(r30). |
| `0x826A49DC` | `addi r9, r11, 0x7F` | Integer/address arithmetic: r9, r11, 0x7F. |
| `0x826A49E0` | `lwz r11, 0(r10)` | Load from r11, 0(r10). |
| `0x826A49E4` | `clrrwi r9, r9, 7` | Shift/rotate/mask or width-normalize: r9, r9, 7. |
| `0x826A49E8` | `lwz r10, 0xC(r11)` | Load from r10, 0xC(r11). |
| `0x826A49EC` | `subf r9, r9, r10` | Integer/address arithmetic: r9, r9, r10. |
| `0x826A49F0` | `mr r25, r10` | Copy register value: r25, r10. |
| `0x826A49F4` | `mr r18, r9` | Copy register value: r18, r9. |
| `0x826A49F8` | `stw r9, 0xC(r11)` | Store the source value to r9, 0xC(r11). |
| `0x826A49FC` | `lbz r11, 0x186(r31)` | Load from r11, 0x186(r31). |
| `0x826A4A00` | `lwz r30, 8(r30)` | Load from r30, 8(r30). |
| `0x826A4A04` | `rotlwi r10, r11, 1` | Shift/rotate/mask or width-normalize: r10, r11, 1. |
| `0x826A4A08` | `mr r3, r30` | Copy register value: r3, r30. |
| `0x826A4A0C` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826A4A10` | `slwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826A4A14` | `stw r30, 0x14C(r31)` | Store the source value to r30, 0x14C(r31). |
| `0x826A4A18` | `add r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x826A4A1C` | `lbz r4, 0x64(r11)` | Load from r4, 0x64(r11). |
| `0x826A4A20` | `bl rw__audio__core__Decoder__GetSamplesRemaining` | Call rw__audio__core__Decoder__GetSamplesRemaining; place the return address in LR. |
| `0x826A4A24` | `lhz r11, 0x178(r31)` | Load from r11, 0x178(r31). |
| `0x826A4A28` | `mr r28, r3` | Copy register value: r28, r3. |
| `0x826A4A2C` | `cmpw cr6, r11, r28` | Compare cr6, r11, r28 and update the specified condition register. |
| `0x826A4A30` | `blt cr6, loc_826A4A38` | Conditional branch to cr6, loc_826A4A38 according to the named CR/CTR condition. |
| `0x826A4A34` | `mr r11, r28` | Copy register value: r11, r28. |
| `0x826A4A38` | `lbz r9, 0x181(r31)` | Load from r9, 0x181(r31). |
| `0x826A4A3C` | `addis r29, r24, 3` | Integer/address arithmetic: r29, r24, 3. |
| `0x826A4A40` | `mr r5, r11` | Copy register value: r5, r11. |
| `0x826A4A44` | `lhz r10, 0x17C(r31)` | Load from r10, 0x17C(r31). |
| `0x826A4A48` | `rotlwi r11, r9, 5` | Shift/rotate/mask or width-normalize: r11, r9, 5. |
| `0x826A4A4C` | `addi r29, r29, 0x10` | Integer/address arithmetic: r29, r29, 0x10. |
| `0x826A4A50` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826A4A54` | `mr r3, r30` | Copy register value: r3, r30. |
| `0x826A4A58` | `add r30, r11, r31` | Integer/address arithmetic: r30, r11, r31. |
| `0x826A4A5C` | `lwz r4, 0(r29)` | Load from r4, 0(r29). |
| `0x826A4A60` | `bl rw__audio__core__Decoder__Decode` | Call rw__audio__core__Decoder__Decode; place the return address in LR. |
| `0x826A4A64` | `add r11, r24, r21` | Integer/address arithmetic: r11, r24, r21. |
| `0x826A4A68` | `lwz r10, 0(r29)` | Load from r10, 0(r29). |
| `0x826A4A6C` | `mr r27, r3` | Copy register value: r27, r3. |
| `0x826A4A70` | `subf r7, r27, r28` | Integer/address arithmetic: r7, r27, r28. |
| `0x826A4A74` | `lwz r9, 0(r11)` | Load from r9, 0(r11). |
| `0x826A4A78` | `stw r10, 0(r11)` | Store the source value to r10, 0(r11). |
| `0x826A4A7C` | `stwx r27, r24, r19` | Store the source value to r27, r24, r19. |
| `0x826A4A80` | `stw r9, 0(r29)` | Store the source value to r9, 0(r29). |
| `0x826A4A84` | `lbz r11, 0x1F(r30)` | Load from r11, 0x1F(r30). |
| `0x826A4A88` | `stbx r11, r24, r22` | Store the source value to r11, r24, r22. |
| `0x826A4A8C` | `lfs f0, 0x10(r30)` | Load from f0, 0x10(r30). |
| `0x826A4A90` | `stfsx f0, r24, r23` | Store the source value to f0, r24, r23. |
| `0x826A4A94` | `lwz r10, 0x158(r31)` | Load from r10, 0x158(r31). |
| `0x826A4A98` | `lfs f0, 0xC(r30)` | Load from f0, 0xC(r30). |
| `0x826A4A9C` | `lbz r11, 0x186(r31)` | Load from r11, 0x186(r31). |
| `0x826A4AA0` | `add r10, r10, r27` | Integer/address arithmetic: r10, r10, r27. |
| `0x826A4AA4` | `stfs f0, 0x150(r31)` | Store the source value to f0, 0x150(r31). |
| `0x826A4AA8` | `addi r11, r11, 8` | Integer/address arithmetic: r11, r11, 8. |
| `0x826A4AAC` | `stw r10, 0x158(r31)` | Store the source value to r10, 0x158(r31). |
| `0x826A4AB0` | `lfs f0, 0x10(r30)` | Load from f0, 0x10(r30). |
| `0x826A4AB4` | `stfs f0, 0x154(r31)` | Store the source value to f0, 0x154(r31). |
| `0x826A4AB8` | `lwz r10, 0x14(r30)` | Load from r10, 0x14(r30). |
| `0x826A4ABC` | `stw r10, 0x15C(r31)` | Store the source value to r10, 0x15C(r31). |
| `0x826A4AC0` | `slwi r10, r11, 1` | Shift/rotate/mask or width-normalize: r10, r11, 1. |
| `0x826A4AC4` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826A4AC8` | `slwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826A4ACC` | `lwzx r10, r11, r31` | Load from r10, r11, r31. |
| `0x826A4AD0` | `add r10, r27, r10` | Integer/address arithmetic: r10, r27, r10. |
| `0x826A4AD4` | `stwx r10, r11, r31` | Store the source value to r10, r11, r31. |
| `0x826A4AD8` | `lwz r11, 0x158(r31)` | Load from r11, 0x158(r31). |
| `0x826A4ADC` | `lwz r10, 0x14(r30)` | Load from r10, 0x14(r30). |
| `0x826A4AE0` | `cmpw cr6, r11, r10` | Compare cr6, r11, r10 and update the specified condition register. |
| `0x826A4AE4` | `bne cr6, loc_826A4B9C` | Conditional branch to cr6, loc_826A4B9C according to the named CR/CTR condition. |
| `0x826A4AE8` | `lwz r11, 0x18(r30)` | Load from r11, 0x18(r30). |
| `0x826A4AEC` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4AF0` | `blt cr6, loc_826A4AFC` | Conditional branch to cr6, loc_826A4AFC according to the named CR/CTR condition. |
| `0x826A4AF4` | `stw r11, 0x158(r31)` | Store the source value to r11, 0x158(r31). |
| `0x826A4AF8` | `b loc_826A4B9C` | Branch unconditionally to loc_826A4B9C. |
| `0x826A4AFC` | `stb r26, 0x1E(r30)` | Store the source value to r26, 0x1E(r30). |
| `0x826A4B00` | `lwz r11, 0x14C(r31)` | Load from r11, 0x14C(r31). |
| `0x826A4B04` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4B08` | `beq cr6, loc_826A4B1C` | Conditional branch to cr6, loc_826A4B1C according to the named CR/CTR condition. |
| `0x826A4B0C` | `lwz r11, 4(r31)` | Load from r11, 4(r31). |
| `0x826A4B10` | `stw r20, 0x14C(r31)` | Store the source value to r20, 0x14C(r31). |
| `0x826A4B14` | `lwz r11, 0(r11)` | Load from r11, 0(r11). |
| `0x826A4B18` | `stw r25, 0xC(r11)` | Store the source value to r25, 0xC(r11). |
| `0x826A4B1C` | `mr r3, r31` | Copy register value: r3, r31. |
| `0x826A4B20` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__AdvanceCurrentRequest` | Call rw__audio__core__SndPlayer1_CgsStreamMod__AdvanceCurrentRequest; place the return address in LR. |
| `0x826A4B24` | `lbz r11, 0x181(r31)` | Load from r11, 0x181(r31). |
| `0x826A4B28` | `lhz r10, 0x17C(r31)` | Load from r10, 0x17C(r31). |
| `0x826A4B2C` | `rotlwi r11, r11, 5` | Shift/rotate/mask or width-normalize: r11, r11, 5. |
| `0x826A4B30` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826A4B34` | `add r8, r11, r31` | Integer/address arithmetic: r8, r11, r31. |
| `0x826A4B38` | `lbz r11, 0x1E(r8)` | Load from r11, 0x1E(r8). |
| `0x826A4B3C` | `cmpwi cr6, r11, 4` | Compare cr6, r11, 4 and update the specified condition register. |
| `0x826A4B40` | `beq cr6, loc_826A4B50` | Conditional branch to cr6, loc_826A4B50 according to the named CR/CTR condition. |
| `0x826A4B44` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4B48` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826A4B4C` | `bne cr6, loc_826A4B54` | Conditional branch to cr6, loc_826A4B54 according to the named CR/CTR condition. |
| `0x826A4B50` | `mr r11, r20` | Copy register value: r11, r20. |
| `0x826A4B54` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826A4B58` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4B5C` | `beq cr6, loc_826A4B9C` | Conditional branch to cr6, loc_826A4B9C according to the named CR/CTR condition. |
| `0x826A4B60` | `lwz r11, 8(r8)` | Load from r11, 8(r8). |
| `0x826A4B64` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4B68` | `beq cr6, loc_826A4B9C` | Conditional branch to cr6, loc_826A4B9C according to the named CR/CTR condition. |
| `0x826A4B6C` | `lwz r10, 4(r31)` | Load from r10, 4(r31). |
| `0x826A4B70` | `lhz r11, 0x1C(r8)` | Load from r11, 0x1C(r8). |
| `0x826A4B74` | `addi r9, r11, 0x7F` | Integer/address arithmetic: r9, r11, 0x7F. |
| `0x826A4B78` | `lwz r11, 0(r10)` | Load from r11, 0(r10). |
| `0x826A4B7C` | `clrrwi r9, r9, 7` | Shift/rotate/mask or width-normalize: r9, r9, 7. |
| `0x826A4B80` | `lwz r10, 0xC(r11)` | Load from r10, 0xC(r11). |
| `0x826A4B84` | `subf r9, r9, r10` | Integer/address arithmetic: r9, r9, r10. |
| `0x826A4B88` | `mr r25, r10` | Copy register value: r25, r10. |
| `0x826A4B8C` | `mr r18, r9` | Copy register value: r18, r9. |
| `0x826A4B90` | `stw r9, 0xC(r11)` | Store the source value to r9, 0xC(r11). |
| `0x826A4B94` | `lwz r11, 8(r8)` | Load from r11, 8(r8). |
| `0x826A4B98` | `stw r11, 0x14C(r31)` | Store the source value to r11, 0x14C(r31). |
| `0x826A4B9C` | `cmpwi cr6, r7, 0` | Compare cr6, r7, 0 and update the specified condition register. |
| `0x826A4BA0` | `bne cr6, loc_826A4C24` | Conditional branch to cr6, loc_826A4C24 according to the named CR/CTR condition. |
| `0x826A4BA4` | `lbz r11, 0x186(r31)` | Load from r11, 0x186(r31). |
| `0x826A4BA8` | `rotlwi r10, r11, 1` | Shift/rotate/mask or width-normalize: r10, r11, 1. |
| `0x826A4BAC` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826A4BB0` | `slwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826A4BB4` | `add r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x826A4BB8` | `lbz r10, 0x65(r11)` | Load from r10, 0x65(r11). |
| `0x826A4BBC` | `cmplwi cr6, r10, 1` | Compare cr6, r10, 1 and update the specified condition register. |
| `0x826A4BC0` | `bne cr6, loc_826A4C24` | Conditional branch to cr6, loc_826A4C24 according to the named CR/CTR condition. |
| `0x826A4BC4` | `stb r17, 0x65(r11)` | Store the source value to r17, 0x65(r11). |
| `0x826A4BC8` | `lbz r11, 0x186(r31)` | Load from r11, 0x186(r31). |
| `0x826A4BCC` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826A4BD0` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826A4BD4` | `cmplwi cr6, r11, 0x14` | Compare cr6, r11, 0x14 and update the specified condition register. |
| `0x826A4BD8` | `bne cr6, loc_826A4BE0` | Conditional branch to cr6, loc_826A4BE0 according to the named CR/CTR condition. |
| `0x826A4BDC` | `mr r11, r20` | Copy register value: r11, r20. |
| `0x826A4BE0` | `lwz r3, 0x14C(r31)` | Load from r3, 0x14C(r31). |
| `0x826A4BE4` | `stb r11, 0x186(r31)` | Store the source value to r11, 0x186(r31). |
| `0x826A4BE8` | `cmplwi cr6, r3, 0` | Compare cr6, r3, 0 and update the specified condition register. |
| `0x826A4BEC` | `beq cr6, loc_826A4C1C` | Conditional branch to cr6, loc_826A4C1C according to the named CR/CTR condition. |
| `0x826A4BF0` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826A4BF4` | `slwi r10, r11, 1` | Shift/rotate/mask or width-normalize: r10, r11, 1. |
| `0x826A4BF8` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826A4BFC` | `slwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826A4C00` | `add r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x826A4C04` | `lbz r10, 0x65(r11)` | Load from r10, 0x65(r11). |
| `0x826A4C08` | `cmplwi cr6, r10, 1` | Compare cr6, r10, 1 and update the specified condition register. |
| `0x826A4C0C` | `bne cr6, loc_826A4C1C` | Conditional branch to cr6, loc_826A4C1C according to the named CR/CTR condition. |
| `0x826A4C10` | `lbz r4, 0x64(r11)` | Load from r4, 0x64(r11). |
| `0x826A4C14` | `bl rw__audio__core__Decoder__GetSamplesRemaining` | Call rw__audio__core__Decoder__GetSamplesRemaining; place the return address in LR. |
| `0x826A4C18` | `mr r7, r3` | Copy register value: r7, r3. |
| `0x826A4C1C` | `cmpwi cr6, r7, 0` | Compare cr6, r7, 0 and update the specified condition register. |
| `0x826A4C20` | `beq cr6, loc_826A4BA4` | Conditional branch to cr6, loc_826A4BA4 according to the named CR/CTR condition. |
| `0x826A4C24` | `lwz r11, 0x14C(r31)` | Load from r11, 0x14C(r31). |
| `0x826A4C28` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4C2C` | `beq cr6, loc_826A4C48` | Conditional branch to cr6, loc_826A4C48 according to the named CR/CTR condition. |
| `0x826A4C30` | `cmplwi cr6, r18, 0` | Compare cr6, r18, 0 and update the specified condition register. |
| `0x826A4C34` | `stw r20, 0x14C(r31)` | Store the source value to r20, 0x14C(r31). |
| `0x826A4C38` | `beq cr6, loc_826A4C48` | Conditional branch to cr6, loc_826A4C48 according to the named CR/CTR condition. |
| `0x826A4C3C` | `lwz r11, 4(r31)` | Load from r11, 4(r31). |
| `0x826A4C40` | `lwz r11, 0(r11)` | Load from r11, 0(r11). |
| `0x826A4C44` | `stw r25, 0xC(r11)` | Store the source value to r25, 0xC(r11). |
| `0x826A4C48` | `lbz r10, 0x21(r31)` | Load from r10, 0x21(r31). |
| `0x826A4C4C` | `add r11, r24, r22` | Integer/address arithmetic: r11, r24, r22. |
| `0x826A4C50` | `cmpwi cr6, r27, 0` | Compare cr6, r27, 0 and update the specified condition register. |
| `0x826A4C54` | `stb r10, 0(r11)` | Store the source value to r10, 0(r11). |
| `0x826A4C58` | `lfs f0, 0x16C(r31)` | Load from f0, 0x16C(r31). |
| `0x826A4C5C` | `stfsx f0, r24, r23` | Store the source value to f0, r24, r23. |
| `0x826A4C60` | `bne cr6, loc_826A4C7C` | Conditional branch to cr6, loc_826A4C7C according to the named CR/CTR condition. |
| `0x826A4C64` | `lhz r11, 0x178(r31)` | Load from r11, 0x178(r31). |
| `0x826A4C68` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A4C6C` | `beq cr6, loc_826A4DB0` | Conditional branch to cr6, loc_826A4DB0 according to the named CR/CTR condition. |
| `0x826A4C70` | `li r3, 0` | Materialize immediate/address component: r3, 0. |
| `0x826A4C74` | `addi r1, r1, 0xE0` | Integer/address arithmetic: r1, r1, 0xE0. |
| `0x826A4C78` | `b __restgprlr_17` | Branch unconditionally to __restgprlr_17. |
| `0x826A4C7C` | `lbz r9, 0(r11)` | Load from r9, 0(r11). |
| `0x826A4C80` | `lbz r10, 0x17E(r31)` | Load from r10, 0x17E(r31). |
| `0x826A4C84` | `mr r7, r9` | Copy register value: r7, r9. |
| `0x826A4C88` | `lwzx r11, r24, r21` | Load from r11, r24, r21. |
| `0x826A4C8C` | `mr r8, r10` | Copy register value: r8, r10. |
| `0x826A4C90` | `cmplw cr6, r7, r8` | Compare cr6, r7, r8 and update the specified condition register. |
| `0x826A4C94` | `bge cr6, loc_826A4C9C` | Conditional branch to cr6, loc_826A4C9C according to the named CR/CTR condition. |
| `0x826A4C98` | `mr r10, r9` | Copy register value: r10, r9. |
| `0x826A4C9C` | `clrlwi r4, r10, 24` | Shift/rotate/mask or width-normalize: r4, r10, 24. |
| `0x826A4CA0` | `lhz r10, 0x17A(r31)` | Load from r10, 0x17A(r31). |
| `0x826A4CA4` | `mr r9, r20` | Copy register value: r9, r20. |
| `0x826A4CA8` | `add r3, r10, r31` | Integer/address arithmetic: r3, r10, r31. |
| `0x826A4CAC` | `cmpwi cr6, r4, 4` | Compare cr6, r4, 4 and update the specified condition register. |
| `0x826A4CB0` | `blt cr6, loc_826A4D5C` | Conditional branch to cr6, loc_826A4D5C according to the named CR/CTR condition. |
| `0x826A4CB4` | `addi r5, r4, -3` | Integer/address arithmetic: r5, r4, -3. |
| `0x826A4CB8` | `mr r8, r17` | Copy register value: r8, r17. |
| `0x826A4CBC` | `addi r10, r3, 8` | Integer/address arithmetic: r10, r3, 8. |
| `0x826A4CC0` | `lhz r7, 0xE(r11)` | Load from r7, 0xE(r11). |
| `0x826A4CC4` | `addi r30, r8, -1` | Integer/address arithmetic: r30, r8, -1. |
| `0x826A4CC8` | `lwz r6, 4(r11)` | Load from r6, 4(r11). |
| `0x826A4CCC` | `addi r29, r8, 1` | Integer/address arithmetic: r29, r8, 1. |
| `0x826A4CD0` | `mullw r7, r7, r9` | Integer/address arithmetic: r7, r7, r9. |
| `0x826A4CD4` | `add r7, r7, r27` | Integer/address arithmetic: r7, r7, r27. |
| `0x826A4CD8` | `addi r9, r9, 4` | Integer/address arithmetic: r9, r9, 4. |
| `0x826A4CDC` | `slwi r7, r7, 2` | Shift/rotate/mask or width-normalize: r7, r7, 2. |
| `0x826A4CE0` | `cmplw cr6, r9, r5` | Compare cr6, r9, r5 and update the specified condition register. |
| `0x826A4CE4` | `add r7, r7, r6` | Integer/address arithmetic: r7, r7, r6. |
| `0x826A4CE8` | `lfs f0, -4(r7)` | Load from f0, -4(r7). |
| `0x826A4CEC` | `stfs f0, -8(r10)` | Store the source value to f0, -8(r10). |
| `0x826A4CF0` | `lhz r7, 0xE(r11)` | Load from r7, 0xE(r11). |
| `0x826A4CF4` | `lwz r6, 4(r11)` | Load from r6, 4(r11). |
| `0x826A4CF8` | `mullw r7, r30, r7` | Integer/address arithmetic: r7, r30, r7. |
| `0x826A4CFC` | `add r7, r7, r27` | Integer/address arithmetic: r7, r7, r27. |
| `0x826A4D00` | `slwi r7, r7, 2` | Shift/rotate/mask or width-normalize: r7, r7, 2. |
| `0x826A4D04` | `add r7, r7, r6` | Integer/address arithmetic: r7, r7, r6. |
| `0x826A4D08` | `lfs f0, -4(r7)` | Load from f0, -4(r7). |
| `0x826A4D0C` | `stfs f0, -4(r10)` | Store the source value to f0, -4(r10). |
| `0x826A4D10` | `lhz r7, 0xE(r11)` | Load from r7, 0xE(r11). |
| `0x826A4D14` | `lwz r6, 4(r11)` | Load from r6, 4(r11). |
| `0x826A4D18` | `mullw r7, r7, r8` | Integer/address arithmetic: r7, r7, r8. |
| `0x826A4D1C` | `add r7, r7, r27` | Integer/address arithmetic: r7, r7, r27. |
| `0x826A4D20` | `addi r8, r8, 4` | Integer/address arithmetic: r8, r8, 4. |
| `0x826A4D24` | `slwi r7, r7, 2` | Shift/rotate/mask or width-normalize: r7, r7, 2. |
| `0x826A4D28` | `add r7, r7, r6` | Integer/address arithmetic: r7, r7, r6. |
| `0x826A4D2C` | `lfs f0, -4(r7)` | Load from f0, -4(r7). |
| `0x826A4D30` | `stfs f0, 0(r10)` | Store the source value to f0, 0(r10). |
| `0x826A4D34` | `lhz r7, 0xE(r11)` | Load from r7, 0xE(r11). |
| `0x826A4D38` | `lwz r6, 4(r11)` | Load from r6, 4(r11). |
| `0x826A4D3C` | `mullw r7, r29, r7` | Integer/address arithmetic: r7, r29, r7. |
| `0x826A4D40` | `add r7, r7, r27` | Integer/address arithmetic: r7, r7, r27. |
| `0x826A4D44` | `slwi r7, r7, 2` | Shift/rotate/mask or width-normalize: r7, r7, 2. |
| `0x826A4D48` | `add r7, r7, r6` | Integer/address arithmetic: r7, r7, r6. |
| `0x826A4D4C` | `lfs f0, -4(r7)` | Load from f0, -4(r7). |
| `0x826A4D50` | `stfs f0, 4(r10)` | Store the source value to f0, 4(r10). |
| `0x826A4D54` | `addi r10, r10, 0x10` | Integer/address arithmetic: r10, r10, 0x10. |
| `0x826A4D58` | `blt cr6, loc_826A4CC0` | Conditional branch to cr6, loc_826A4CC0 according to the named CR/CTR condition. |
| `0x826A4D5C` | `cmplw cr6, r9, r4` | Compare cr6, r9, r4 and update the specified condition register. |
| `0x826A4D60` | `bge cr6, loc_826A4D9C` | Conditional branch to cr6, loc_826A4D9C according to the named CR/CTR condition. |
| `0x826A4D64` | `slwi r10, r9, 2` | Shift/rotate/mask or width-normalize: r10, r9, 2. |
| `0x826A4D68` | `add r10, r10, r3` | Integer/address arithmetic: r10, r10, r3. |
| `0x826A4D6C` | `lhz r8, 0xE(r11)` | Load from r8, 0xE(r11). |
| `0x826A4D70` | `lwz r7, 4(r11)` | Load from r7, 4(r11). |
| `0x826A4D74` | `mullw r8, r8, r9` | Integer/address arithmetic: r8, r8, r9. |
| `0x826A4D78` | `add r8, r8, r27` | Integer/address arithmetic: r8, r8, r27. |
| `0x826A4D7C` | `addi r9, r9, 1` | Integer/address arithmetic: r9, r9, 1. |
| `0x826A4D80` | `slwi r8, r8, 2` | Shift/rotate/mask or width-normalize: r8, r8, 2. |
| `0x826A4D84` | `cmplw cr6, r9, r4` | Compare cr6, r9, r4 and update the specified condition register. |
| `0x826A4D88` | `add r8, r8, r7` | Integer/address arithmetic: r8, r8, r7. |
| `0x826A4D8C` | `lfs f0, -4(r8)` | Load from f0, -4(r8). |
| `0x826A4D90` | `stfs f0, 0(r10)` | Store the source value to f0, 0(r10). |
| `0x826A4D94` | `addi r10, r10, 4` | Integer/address arithmetic: r10, r10, 4. |
| `0x826A4D98` | `blt cr6, loc_826A4D6C` | Conditional branch to cr6, loc_826A4D6C according to the named CR/CTR condition. |
| `0x826A4D9C` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826A4DA0` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x826A4DA4` | `stb r11, 0x183(r31)` | Store the source value to r11, 0x183(r31). |
| `0x826A4DA8` | `addi r1, r1, 0xE0` | Integer/address arithmetic: r1, r1, 0xE0. |
| `0x826A4DAC` | `b __restgprlr_17` | Branch unconditionally to __restgprlr_17. |
| `0x826A4DB0` | `stwx r20, r24, r19` | Store the source value to r20, r24, r19. |
| `0x826A4DB4` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x826A4DB8` | `addi r1, r1, 0xE0` | Integer/address arithmetic: r1, r1, 0xE0. |
| `0x826A4DBC` | `b __restgprlr_17` | Branch unconditionally to __restgprlr_17. |
| `0x826A4DC0` | `lis r11, 3` | Materialize immediate/address component: r11, 3. |
| `0x826A4DC4` | `lis r10, 3` | Materialize immediate/address component: r10, 3. |
| `0x826A4DC8` | `ori r11, r11, 0x20 # ' ' # 0x30020` | Bitwise operation: r11, r11, 0x20 # ' ' # 0x30020. |
| `0x826A4DCC` | `lis r9, 3` | Materialize immediate/address component: r9, 3. |
| `0x826A4DD0` | `ori r10, r10, 0x2C # ',' # 0x3002C` | Bitwise operation: r10, r10, 0x2C # ',' # 0x3002C. |
| `0x826A4DD4` | `ori r9, r9, 0x24 # '$' # 0x30024` | Bitwise operation: r9, r9, 0x24 # '$' # 0x30024. |
| `0x826A4DD8` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x826A4DDC` | `stwx r20, r24, r11` | Store the source value to r20, r24, r11. |
| `0x826A4DE0` | `lbz r11, 0x1F(r30)` | Load from r11, 0x1F(r30). |
| `0x826A4DE4` | `stbx r11, r24, r10` | Store the source value to r11, r24, r10. |
| `0x826A4DE8` | `lfs f0, 0x10(r30)` | Load from f0, 0x10(r30). |
| `0x826A4DEC` | `stfsx f0, r24, r9` | Store the source value to f0, r24, r9. |
| `0x826A4DF0` | `lfs f0, 0x10(r30)` | Load from f0, 0x10(r30). |
| `0x826A4DF4` | `stfs f0, 0x16C(r31)` | Store the source value to f0, 0x16C(r31). |
| `0x826A4DF8` | `lbz r11, 0x1F(r30)` | Load from r11, 0x1F(r30). |
| `0x826A4DFC` | `stb r11, 0x21(r31)` | Store the source value to r11, 0x21(r31). |
| `0x826A4E00` | `addi r1, r1, 0xE0` | Integer/address arithmetic: r1, r1, 0xE0. |
| `0x826A4E04` | `b __restgprlr_17` | Branch unconditionally to __restgprlr_17. |

#### (c) Rodata constants

| VA | file_off | Raw bytes | Decode/use |
|---:|---:|---|---|
| `0x82001CA8` | `0x00004CA8` | `00 00 00 00 00 00 00 00` | `0.0`, start-time sentinel |

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x14C` | clear/store Decoder pointer while scratch is carved | `mpLoadedDecoder` |
| `+0x150..+0x15C` | publish request handle/rate/played/length | current-request cache |
| `+0x16C` | compare/store | `mPreviousSampleRate` |
| `+0x178` | requested decode count | `mSamplesRequested` |
| `+0x17A/+0x17C` | relative tail bases | declick/internal offsets |
| `+0x17E` | cap last-sample capture channels | `mMaxChannels` |
| `+0x181/+0x182` | current/max request | request ring |
| `+0x183/+0x184` | declick gathered/remaining | declick state |
| `+0x185/+0x186` | producer/consumer feed indices | feed ring |
| feed `+0x04/+0x08/+0x09` | sample counter, decoder handle, state | `FeedDesc` |
| internal `+0/+8/+0xC/+0x10/+0x14/+0x18/+0x1C/+0x1E/+0x1F` | all request fields | `RequestInternal` |
| Mixer `+0x3000C/+0x30010` | swap | `mpSrcBuffer/mpDstBuffer` |
| Mixer `+0x30020/+0x30024/+0x3002C` | publish | samples/rate/channels |
| SampleBuffer `+4/+0x0E` | sample base/stride | `mpSamples/muStride` |
| System->StackAllocator `+0x0C` | subtract/restore aligned decoder scratch | `mpTop` |

#### (e) Implementation-grade C++ sketch

```cpp
BufferStatus Process(SndPlayer1_CgsStreamMod* s, Mixer* m, bool)
{
    if (s->mNumDeclickSamples && s->mDcOffsetsGathered) return s->Declick(m);
    RequestInternal* r=&s->Request(s->mCurrentRequest);
    s->mpLoadedDecoder=nullptr;
    while (IsActive(r->state) && r->numSamples==0) {
        r->state=COMPLETE; s->AdvanceCurrentRequest(); r=&s->Request(s->mCurrentRequest);
    }
    u32 produced=0; u32 samplesRemainingAfter=0;
    u8* savedTop=nullptr; bool scratchCarved=false;
    if (!IsActive(r->state)) goto finish;
    if (r->sampleRate!=s->mPreviousSampleRate || r->numChannels!=s->mOutputChannels) {
        m->mNumSamples=0; m->mbChannelCount=r->numChannels; m->mfSampleRate=r->sampleRate;
        s->mPreviousSampleRate=r->sampleRate; s->mOutputChannels=r->numChannels; return BUFFER_AVAILABLE;
    }
    while (s->mFeedDesc[s->mNextFeedSlotToFree].feedState==0 &&
           s->mNextFeedSlotToFree!=s->mNextFeedSlotToFill)
        s->mNextFeedSlotToFree=(s->mNextFeedSlotToFree+1)%20;
    if (s->mFeedDesc[s->mNextFeedSlotToFree].feedState!=1) goto finish;
    if (r->startTime!=0.0) {
        u32 silence=0;
        if (!s->WaitForStartTime(m,r->startTime,&silence)) { s->mCurrentRequestSamplesPlayed=0; goto finish; }
        if (silence) {
            silence=Min<u32>(silence,s->mSamplesRequested);
            for (u32 c=0;c<r->numChannels;++c)
                memset(m->mpDstBuffer->mpSamples+c*m->mpDstBuffer->muStride,0,4*silence);
            m->mNumSamples=silence; Swap(m->mpSrcBuffer,m->mpDstBuffer);
            m->mbChannelCount=r->numChannels; m->mfSampleRate=r->sampleRate;
            s->mCurrentRequestSamplesPlayed=0; return BUFFER_AVAILABLE;
        }
        r->startTime=0.0;
    }
    {
        StackAllocator* stack=s->mpSystemUseGetSystemAccessor->mpStackAllocator;
        savedTop=stack->mpTop;
        stack->mpTop-=AlignUp(r->decoderInstanceSize,128); scratchCarved=true;
        Decoder* d=r->pDecoder; s->mpLoadedDecoder=d;
        FeedDesc& f=s->mFeedDesc[s->mNextFeedSlotToFree];
        u32 available=Decoder::GetSamplesRemaining(d,f.decoderRequestHandle);
        u32 ask=Min<u32>(s->mSamplesRequested,available);
        produced=Decoder::Decode(d,m->mpDstBuffer,ask);
        samplesRemainingAfter=available-produced;
        Swap(m->mpSrcBuffer,m->mpDstBuffer); m->mNumSamples=produced;
        m->mbChannelCount=r->numChannels; m->mfSampleRate=r->sampleRate;
        s->mCurrentRequestHandle=r->requestHandle;
        s->mCurrentRequestSampleRate=r->sampleRate;
        s->mCurrentRequestSamplesPlayed+=produced;
        s->mCurrentRequestNumSamples=r->numSamples;
        f.chunkSamplesPlayed+=produced;
        if (s->mCurrentRequestSamplesPlayed==r->numSamples) {
            if (r->loopStart>=0) s->mCurrentRequestSamplesPlayed=r->loopStart;
            else { r->state=COMPLETE; s->mpLoadedDecoder=nullptr; stack->mpTop=savedTop;
                   scratchCarved=false; s->AdvanceCurrentRequest();
                   r=&s->Request(s->mCurrentRequest);
                   if (IsActive(r->state)&&r->pDecoder) {
                       savedTop=stack->mpTop; stack->mpTop-=AlignUp(r->decoderInstanceSize,128);
                       scratchCarved=true; s->mpLoadedDecoder=r->pDecoder;
                   }}
        }
        while (samplesRemainingAfter==0 && s->mFeedDesc[s->mNextFeedSlotToFree].feedState==1) {
            s->mFeedDesc[s->mNextFeedSlotToFree].feedState=2;
            s->mNextFeedSlotToFree=(s->mNextFeedSlotToFree+1)%20;
            if (s->mpLoadedDecoder && s->mFeedDesc[s->mNextFeedSlotToFree].feedState==1)
                samplesRemainingAfter=Decoder::GetSamplesRemaining(s->mpLoadedDecoder,
                    s->mFeedDesc[s->mNextFeedSlotToFree].decoderRequestHandle);
        }
    }
finish:
    if (s->mpLoadedDecoder) { s->mpLoadedDecoder=nullptr; if (scratchCarved) s->mpSystemUseGetSystemAccessor->mpStackAllocator->mpTop=savedTop; }
    m->mbChannelCount=s->mOutputChannels; m->mfSampleRate=s->mPreviousSampleRate;
    if (!produced) {
        if (s->mSamplesRequested) return BUFFER_UNAVAILABLE;
        m->mNumSamples=0; return BUFFER_AVAILABLE;
    }
    const u32 channels=Min<u32>(m->mbChannelCount,s->mMaxChannels);
    for (u32 c=0;c<channels;++c)
        s->DeclickBuffer()[c]=m->mpSrcBuffer->mpSamples[c*m->mpSrcBuffer->muStride+produced-1];
    s->mDcOffsetsGathered=1;
    return BUFFER_AVAILABLE;
}
```

X64 hazards: Decoder/System/SampleBuffer pointers widen; internal stride is host
`sizeof(RequestInternal)`, not `0x20`; feed stride is typed `sizeof(FeedDesc)` and count
20; StackAllocator top is pointer-wide.  Decoder request handles remain intentionally
`u8`.  No deferred-handler return or GetSize body occurs here.

### `ReleaseEvent` (vtable slot 0) — `0x826C37E8`

#### (a) Exact signature / dispatch ABI

Virtual slot 0 receives `r3=this`; the DecFIGS declaration is `virtual void
ReleaseEvent()`.  Any value left in `r3` is incidental.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826C37E8.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826C37E8` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826C37EC` | `bl __savegprlr_27` | Call __savegprlr_27; place the return address in LR. |
| `0x826C37F0` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826C37F4` | `mr r30, r3` | Copy register value: r30, r3. |
| `0x826C37F8` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__StreamLostCallback` | Call rw__audio__core__SndPlayer1_CgsStreamMod__StreamLostCallback; place the return address in LR. |
| `0x826C37FC` | `lbz r11, 0x187(r30)` | Load from r11, 0x187(r30). |
| `0x826C3800` | `cmplwi cr6, r11, 1` | Compare cr6, r11, 1 and update the specified condition register. |
| `0x826C3804` | `bne cr6, loc_826C3814` | Conditional branch to cr6, loc_826C3814 according to the named CR/CTR condition. |
| `0x826C3808` | `addi r4, r30, 0x40 # '@'` | Integer/address arithmetic: r4, r30, 0x40 # '@'. |
| `0x826C380C` | `lwz r3, 4(r30)` | Load from r3, 4(r30). |
| `0x826C3810` | `bl rw__audio__core__System__RemoveTimer` | Call rw__audio__core__System__RemoveTimer; place the return address in LR. |
| `0x826C3814` | `lwz r11, 0x58(r30)` | Load from r11, 0x58(r30). |
| `0x826C3818` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826C381C` | `beq cr6, loc_826C388C` | Conditional branch to cr6, loc_826C388C according to the named CR/CTR condition. |
| `0x826C3820` | `lbz r11, 0x182(r30)` | Load from r11, 0x182(r30). |
| `0x826C3824` | `li r27, 0` | Materialize immediate/address component: r27, 0. |
| `0x826C3828` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826C382C` | `beq cr6, loc_826C387C` | Conditional branch to cr6, loc_826C387C according to the named CR/CTR condition. |
| `0x826C3830` | `li r28, 0x30 # '0'` | Materialize immediate/address component: r28, 0x30 # '0'. |
| `0x826C3834` | `mr r31, r28` | Copy register value: r31, r28. |
| `0x826C3838` | `li r29, 6` | Materialize immediate/address component: r29, 6. |
| `0x826C383C` | `lwz r11, 0x58(r30)` | Load from r11, 0x58(r30). |
| `0x826C3840` | `lwzx r4, r11, r31` | Load from r4, r11, r31. |
| `0x826C3844` | `cmplwi cr6, r4, 0` | Compare cr6, r4, 0 and update the specified condition register. |
| `0x826C3848` | `beq cr6, loc_826C3858` | Conditional branch to cr6, loc_826C3858 according to the named CR/CTR condition. |
| `0x826C384C` | `li r5, 0` | Materialize immediate/address component: r5, 0. |
| `0x826C3850` | `lwz r3, 4(r30)` | Load from r3, 4(r30). |
| `0x826C3854` | `bl rw__audio__core__System__Free` | Call rw__audio__core__System__Free; place the return address in LR. |
| `0x826C3858` | `addi r29, r29, -1` | Integer/address arithmetic: r29, r29, -1. |
| `0x826C385C` | `addi r31, r31, 8` | Integer/address arithmetic: r31, r31, 8. |
| `0x826C3860` | `cmplwi cr6, r29, 0` | Compare cr6, r29, 0 and update the specified condition register. |
| `0x826C3864` | `bne cr6, loc_826C383C` | Conditional branch to cr6, loc_826C383C according to the named CR/CTR condition. |
| `0x826C3868` | `lbz r11, 0x182(r30)` | Load from r11, 0x182(r30). |
| `0x826C386C` | `addi r27, r27, 1` | Integer/address arithmetic: r27, r27, 1. |
| `0x826C3870` | `addi r28, r28, 0x88` | Integer/address arithmetic: r28, r28, 0x88. |
| `0x826C3874` | `cmplw cr6, r27, r11` | Compare cr6, r27, r11 and update the specified condition register. |
| `0x826C3878` | `blt cr6, loc_826C3834` | Conditional branch to cr6, loc_826C3834 according to the named CR/CTR condition. |
| `0x826C387C` | `li r5, 0` | Materialize immediate/address component: r5, 0. |
| `0x826C3880` | `lwz r4, 0x58(r30)` | Load from r4, 0x58(r30). |
| `0x826C3884` | `lwz r3, 4(r30)` | Load from r3, 4(r30). |
| `0x826C3888` | `bl rw__audio__core__System__Free` | Call rw__audio__core__System__Free; place the return address in LR. |
| `0x826C388C` | `addi r1, r1, 0x80` | Integer/address arithmetic: r1, r1, 0x80. |
| `0x826C3890` | `b __restgprlr_27` | Branch unconditionally to __restgprlr_27. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x04` | System receiver for RemoveTimer/Free | `mpSystemUseGetSystemAccessor` |
| `+0x40` | address passed to RemoveTimer | `mTimerHandle` |
| `+0x58` | external-array base/free | `mpRequestExternal` |
| `+0x182` | request count | `mMaxRequests` |
| `+0x187` | timer removal guard | `mTimerAdded` |
| external `+0x30,+0x38,...,+0x58` | six chunk buffer pointers | `chunks[j].buf` |

#### (e) Implementation-grade C++ sketch

```cpp
void ReleaseEvent()
{
    StreamLostCallback(this);
    if (mTimerAdded==1) System::RemoveTimer(mpSystemUseGetSystemAccessor,&mTimerHandle);
    if (mpRequestExternal) {
        for (u32 i=0;i<mMaxRequests;++i)
            for (u32 j=0;j<6;++j)
                if (mpRequestExternal[i].chunks[j].buf)
                    System::Free(mpSystemUseGetSystemAccessor,
                                 mpRequestExternal[i].chunks[j].buf,nullptr);
        System::Free(mpSystemUseGetSystemAccessor,mpRequestExternal,nullptr);
    }
}
```

X64 hazards: System/external/chunk pointers widen and external/chunk console strides
`0x88/8` must become host `sizeof`.  No deferred return, narrow pointer, or GetSize issue.

### `EventEvent` (vtable slot 1) — `0x826DB588`

#### (a) Exact signature / dispatch ABI

Virtual dispatch supplies `r3=this`, `r4=s32 event`, `r5=void* parameters`.
DecFIGS declares `virtual void EventEvent(int, void*)`; the assembly's unchanged `r3`
on most paths is not a semantic return.  Event ids are PLAY=0, STOP=1,
IS_REQUEST_DONE=2, GET_REQUEST_BUFFERED=3, MODIFY_START_TIME=4.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826DB588.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826DB588` | `lwz r10, 4(r3)` | Load from r10, 4(r3). |
| `0x826DB58C` | `cmpwi cr6, r4, 0` | Compare cr6, r4, 0 and update the specified condition register. |
| `0x826DB590` | `bne cr6, loc_826DB704` | Conditional branch to cr6, loc_826DB704 according to the named CR/CTR condition. |
| `0x826DB594` | `lis r11, flt_82001C98@ha` | Materialize immediate/address component: r11, flt_82001C98@ha. |
| `0x826DB598` | `lfs f0, 0x160(r3)` | Load from f0, 0x160(r3). |
| `0x826DB59C` | `lfs f13, flt_82001C98@l(r11)` | Load from f13, flt_82001C98@l(r11). |
| `0x826DB5A0` | `lis r11, flt_820B56EC@ha` | Materialize immediate/address component: r11, flt_820B56EC@ha. |
| `0x826DB5A4` | `fadds f0, f0, f13` | Floating-point arithmetic/select/conversion: f0, f0, f13. |
| `0x826DB5A8` | `stfs f0, 0x160(r3)` | Store the source value to f0, 0x160(r3). |
| `0x826DB5AC` | `lfs f12, flt_820B56EC@l(r11)` | Load from f12, flt_820B56EC@l(r11). |
| `0x826DB5B0` | `fcmpu cr6, f0, f12` | Compare cr6, f0, f12 and update the specified condition register. |
| `0x826DB5B4` | `ble cr6, loc_826DB5BC` | Conditional branch to cr6, loc_826DB5BC according to the named CR/CTR condition. |
| `0x826DB5B8` | `stfs f13, 0x160(r3)` | Store the source value to f13, 0x160(r3). |
| `0x826DB5BC` | `lwz r11, 0x10(r5)` | Load from r11, 0x10(r5). |
| `0x826DB5C0` | `lfs f0, 0x160(r3)` | Load from f0, 0x160(r3). |
| `0x826DB5C4` | `stfs f0, 0x20(r5)` | Store the source value to f0, 0x20(r5). |
| `0x826DB5C8` | `lis r4, dword_82FFBA08@ha` | Materialize immediate/address component: r4, dword_82FFBA08@ha. |
| `0x826DB5CC` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DB5D0` | `beq cr6, loc_826DB624` | Conditional branch to cr6, loc_826DB624 according to the named CR/CTR condition. |
| `0x826DB5D4` | `lwz r9, dword_82FFBA08@l(r4)` | Load from r9, dword_82FFBA08@l(r4). |
| `0x826DB5D8` | `mr r8, r9` | Copy register value: r8, r9. |
| `0x826DB5DC` | `lbz r7, 0(r9)` | Load from r7, 0(r9). |
| `0x826DB5E0` | `addi r9, r9, 1` | Integer/address arithmetic: r9, r9, 1. |
| `0x826DB5E4` | `cmplwi cr6, r7, 0` | Compare cr6, r7, 0 and update the specified condition register. |
| `0x826DB5E8` | `bne cr6, loc_826DB5DC` | Conditional branch to cr6, loc_826DB5DC according to the named CR/CTR condition. |
| `0x826DB5EC` | `subf r9, r8, r9` | Integer/address arithmetic: r9, r8, r9. |
| `0x826DB5F0` | `mr r8, r11` | Copy register value: r8, r11. |
| `0x826DB5F4` | `addi r9, r9, -1` | Integer/address arithmetic: r9, r9, -1. |
| `0x826DB5F8` | `clrlwi r9, r9, 0` | Shift/rotate/mask or width-normalize: r9, r9, 0. |
| `0x826DB5FC` | `lbz r7, 0(r11)` | Load from r7, 0(r11). |
| `0x826DB600` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826DB604` | `cmplwi cr6, r7, 0` | Compare cr6, r7, 0 and update the specified condition register. |
| `0x826DB608` | `bne cr6, loc_826DB5FC` | Conditional branch to cr6, loc_826DB5FC according to the named CR/CTR condition. |
| `0x826DB60C` | `subf r11, r8, r11` | Integer/address arithmetic: r11, r8, r11. |
| `0x826DB610` | `addi r11, r11, -1` | Integer/address arithmetic: r11, r11, -1. |
| `0x826DB614` | `clrlwi r11, r11, 0` | Shift/rotate/mask or width-normalize: r11, r11, 0. |
| `0x826DB618` | `add r11, r11, r9` | Integer/address arithmetic: r11, r11, r9. |
| `0x826DB61C` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826DB620` | `b loc_826DB628` | Branch unconditionally to loc_826DB628. |
| `0x826DB624` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826DB628` | `addi r8, r11, 0x2B # '+'` | Integer/address arithmetic: r8, r11, 0x2B # '+'. |
| `0x826DB62C` | `lwz r9, 0x10B8(r10)` | Load from r9, 0x10B8(r10). |
| `0x826DB630` | `lwz r7, 0x20(r10)` | Load from r7, 0x20(r10). |
| `0x826DB634` | `lis r6, rw__audio__core__SndPlayer1_CgsStreamMod__PlayHandler@ha` | Materialize immediate/address component: r6, rw__audio__core__SndPlayer1_CgsStreamMod__PlayHandler@ha. |
| `0x826DB638` | `clrrwi r8, r8, 2` | Shift/rotate/mask or width-normalize: r8, r8, 2. |
| `0x826DB63C` | `cmplwi cr6, r11, 1` | Compare cr6, r11, 1 and update the specified condition register. |
| `0x826DB640` | `add r11, r7, r9` | Integer/address arithmetic: r11, r7, r9. |
| `0x826DB644` | `add r9, r9, r8` | Integer/address arithmetic: r9, r9, r8. |
| `0x826DB648` | `addi r6, r6, rw__audio__core__SndPlayer1_CgsStreamMod__PlayHandler@l` | Integer/address arithmetic: r6, r6, rw__audio__core__SndPlayer1_CgsStreamMod__PlayHandler@l. |
| `0x826DB64C` | `stw r9, 0x10B8(r10)` | Store the source value to r9, 0x10B8(r10). |
| `0x826DB650` | `stw r6, 0(r11)` | Store the source value to r6, 0(r11). |
| `0x826DB654` | `stw r3, 4(r11)` | Store the source value to r3, 4(r11). |
| `0x826DB658` | `lfs f0, 0x160(r3)` | Load from f0, 0x160(r3). |
| `0x826DB65C` | `stfs f0, 0x24(r11)` | Store the source value to f0, 0x24(r11). |
| `0x826DB660` | `lfd f0, 0(r5)` | Load from f0, 0(r5). |
| `0x826DB664` | `stfd f0, 8(r11)` | Store the source value to f0, 8(r11). |
| `0x826DB668` | `lfd f0, 8(r5)` | Load from f0, 8(r5). |
| `0x826DB66C` | `stfd f0, 0x10(r11)` | Store the source value to f0, 0x10(r11). |
| `0x826DB670` | `lwz r10, 0x14(r5)` | Load from r10, 0x14(r5). |
| `0x826DB674` | `stw r10, 0x1C(r11)` | Store the source value to r10, 0x1C(r11). |
| `0x826DB678` | `lwz r10, 0x18(r5)` | Load from r10, 0x18(r5). |
| `0x826DB67C` | `stw r10, 0x18(r11)` | Store the source value to r10, 0x18(r11). |
| `0x826DB680` | `lfs f0, 0x1C(r5)` | Load from f0, 0x1C(r5). |
| `0x826DB684` | `fctidz f0, f0` | Execute the exact PPC operation shown: f0, f0. |
| `0x826DB688` | `stfd f0, back_chain(r1)` | Store the source value to f0, back_chain(r1). |
| `0x826DB68C` | `sth r8, 0x20(r11)` | Store the source value to r8, 0x20(r11). |
| `0x826DB690` | `lbz r10, back_chain+7(r1)` | Load from r10, back_chain+7(r1). |
| `0x826DB694` | `stb r10, 0x22(r11)` | Store the source value to r10, 0x22(r11). |
| `0x826DB698` | `bne cr6, loc_826DB6A8` | Conditional branch to cr6, loc_826DB6A8 according to the named CR/CTR condition. |
| `0x826DB69C` | `li r10, 0` | Materialize immediate/address component: r10, 0. |
| `0x826DB6A0` | `stb r10, 0x28(r11)` | Store the source value to r10, 0x28(r11). |
| `0x826DB6A4` | `blr` | Return to the caller through LR. |
| `0x826DB6A8` | `addi r8, r11, 0x28 # '('` | Integer/address arithmetic: r8, r11, 0x28 # '('. |
| `0x826DB6AC` | `lwz r11, dword_82FFBA08@l(r4)` | Load from r11, dword_82FFBA08@l(r4). |
| `0x826DB6B0` | `mr r10, r8` | Copy register value: r10, r8. |
| `0x826DB6B4` | `lbz r9, 0(r11)` | Load from r9, 0(r11). |
| `0x826DB6B8` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826DB6BC` | `cmplwi cr6, r9, 0` | Compare cr6, r9, 0 and update the specified condition register. |
| `0x826DB6C0` | `stb r9, 0(r10)` | Store the source value to r9, 0(r10). |
| `0x826DB6C4` | `addi r10, r10, 1` | Integer/address arithmetic: r10, r10, 1. |
| `0x826DB6C8` | `bne cr6, loc_826DB6B4` | Conditional branch to cr6, loc_826DB6B4 according to the named CR/CTR condition. |
| `0x826DB6CC` | `lwz r9, 0x10(r5)` | Load from r9, 0x10(r5). |
| `0x826DB6D0` | `mr r11, r8` | Copy register value: r11, r8. |
| `0x826DB6D4` | `lbz r10, 0(r11)` | Load from r10, 0(r11). |
| `0x826DB6D8` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826DB6DC` | `cmplwi cr6, r10, 0` | Compare cr6, r10, 0 and update the specified condition register. |
| `0x826DB6E0` | `bne cr6, loc_826DB6D4` | Conditional branch to cr6, loc_826DB6D4 according to the named CR/CTR condition. |
| `0x826DB6E4` | `addi r11, r11, -1` | Integer/address arithmetic: r11, r11, -1. |
| `0x826DB6E8` | `lbz r10, 0(r9)` | Load from r10, 0(r9). |
| `0x826DB6EC` | `addi r9, r9, 1` | Integer/address arithmetic: r9, r9, 1. |
| `0x826DB6F0` | `cmplwi cr6, r10, 0` | Compare cr6, r10, 0 and update the specified condition register. |
| `0x826DB6F4` | `stb r10, 0(r11)` | Store the source value to r10, 0(r11). |
| `0x826DB6F8` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826DB6FC` | `bne cr6, loc_826DB6E8` | Conditional branch to cr6, loc_826DB6E8 according to the named CR/CTR condition. |
| `0x826DB700` | `blr` | Return to the caller through LR. |
| `0x826DB704` | `cmpwi cr6, r4, 1` | Compare cr6, r4, 1 and update the specified condition register. |
| `0x826DB708` | `bne cr6, loc_826DB734` | Conditional branch to cr6, loc_826DB734 according to the named CR/CTR condition. |
| `0x826DB70C` | `lwz r11, 0x10B8(r10)` | Load from r11, 0x10B8(r10). |
| `0x826DB710` | `lis r8, rw__audio__core__SndPlayer1_CgsStreamMod__StopHandler@ha` | Materialize immediate/address component: r8, rw__audio__core__SndPlayer1_CgsStreamMod__StopHandler@ha. |
| `0x826DB714` | `lwz r9, 0x20(r10)` | Load from r9, 0x20(r10). |
| `0x826DB718` | `addi r8, r8, rw__audio__core__SndPlayer1_CgsStreamMod__StopHandler@l` | Integer/address arithmetic: r8, r8, rw__audio__core__SndPlayer1_CgsStreamMod__StopHandler@l. |
| `0x826DB71C` | `add r9, r9, r11` | Integer/address arithmetic: r9, r9, r11. |
| `0x826DB720` | `addi r11, r11, 8` | Integer/address arithmetic: r11, r11, 8. |
| `0x826DB724` | `stw r11, 0x10B8(r10)` | Store the source value to r11, 0x10B8(r10). |
| `0x826DB728` | `stw r8, 0(r9)` | Store the source value to r8, 0(r9). |
| `0x826DB72C` | `stw r3, 4(r9)` | Store the source value to r3, 4(r9). |
| `0x826DB730` | `blr` | Return to the caller through LR. |
| `0x826DB734` | `cmpwi cr6, r4, 2` | Compare cr6, r4, 2 and update the specified condition register. |
| `0x826DB738` | `bne cr6, loc_826DB798` | Conditional branch to cr6, loc_826DB798 according to the named CR/CTR condition. |
| `0x826DB73C` | `lis r11, flt_82001CC0@ha` | Materialize immediate/address component: r11, flt_82001CC0@ha. |
| `0x826DB740` | `lfs f0, 0(r5)` | Load from f0, 0(r5). |
| `0x826DB744` | `lfs f13, 0x28(r3)` | Load from f13, 0x28(r3). |
| `0x826DB748` | `fcmpu cr6, f0, f13` | Compare cr6, f0, f13 and update the specified condition register. |
| `0x826DB74C` | `lfs f12, flt_82001CC0@l(r11)` | Load from f12, flt_82001CC0@l(r11). |
| `0x826DB750` | `blt cr6, loc_826DB788` | Conditional branch to cr6, loc_826DB788 according to the named CR/CTR condition. |
| `0x826DB754` | `fcmpu cr6, f0, f13` | Compare cr6, f0, f13 and update the specified condition register. |
| `0x826DB758` | `beq cr6, loc_826DB774` | Conditional branch to cr6, loc_826DB774 according to the named CR/CTR condition. |
| `0x826DB75C` | `lfs f13, 0x164(r3)` | Load from f13, 0x164(r3). |
| `0x826DB760` | `fcmpu cr6, f0, f13` | Compare cr6, f0, f13 and update the specified condition register. |
| `0x826DB764` | `bgt cr6, loc_826DB790` | Conditional branch to cr6, loc_826DB790 according to the named CR/CTR condition. |
| `0x826DB768` | `lfs f13, 0x168(r3)` | Load from f13, 0x168(r3). |
| `0x826DB76C` | `fcmpu cr6, f0, f13` | Compare cr6, f0, f13 and update the specified condition register. |
| `0x826DB770` | `ble cr6, loc_826DB790` | Conditional branch to cr6, loc_826DB790 according to the named CR/CTR condition. |
| `0x826DB774` | `lis r11, dbl_82001CA8@ha` | Materialize immediate/address component: r11, dbl_82001CA8@ha. |
| `0x826DB778` | `lfd f13, 0x38(r3)` | Load from f13, 0x38(r3). |
| `0x826DB77C` | `lfd f0, dbl_82001CA8@l(r11)` | Load from f0, dbl_82001CA8@l(r11). |
| `0x826DB780` | `fcmpu cr6, f13, f0` | Compare cr6, f13, f0 and update the specified condition register. |
| `0x826DB784` | `bne cr6, loc_826DB790` | Conditional branch to cr6, loc_826DB790 according to the named CR/CTR condition. |
| `0x826DB788` | `lis r11, flt_82001C98@ha` | Materialize immediate/address component: r11, flt_82001C98@ha. |
| `0x826DB78C` | `lfs f12, flt_82001C98@l(r11)` | Load from f12, flt_82001C98@l(r11). |
| `0x826DB790` | `stfs f12, 4(r5)` | Store the source value to f12, 4(r5). |
| `0x826DB794` | `blr` | Return to the caller through LR. |
| `0x826DB798` | `cmpwi cr6, r4, 3` | Compare cr6, r4, 3 and update the specified condition register. |
| `0x826DB79C` | `bne cr6, loc_826DB884` | Conditional branch to cr6, loc_826DB884 according to the named CR/CTR condition. |
| `0x826DB7A0` | `lbz r11, 0x182(r3)` | Load from r11, 0x182(r3). |
| `0x826DB7A4` | `li r7, 0` | Materialize immediate/address component: r7, 0. |
| `0x826DB7A8` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DB7AC` | `beqlr cr6` | Conditionally return through LR when beq is satisfied. |
| `0x826DB7B0` | `lis r11, flt_82001CC0@ha` | Materialize immediate/address component: r11, flt_82001CC0@ha. |
| `0x826DB7B4` | `lfs f13, 0(r5)` | Load from f13, 0(r5). |
| `0x826DB7B8` | `li r8, 0` | Materialize immediate/address component: r8, 0. |
| `0x826DB7BC` | `li r9, 0` | Materialize immediate/address component: r9, 0. |
| `0x826DB7C0` | `lfs f0, flt_82001CC0@l(r11)` | Load from f0, flt_82001CC0@l(r11). |
| `0x826DB7C4` | `lhz r11, 0x17C(r3)` | Load from r11, 0x17C(r3). |
| `0x826DB7C8` | `add r11, r11, r9` | Integer/address arithmetic: r11, r11, r9. |
| `0x826DB7CC` | `add r11, r11, r3` | Integer/address arithmetic: r11, r11, r3. |
| `0x826DB7D0` | `lfs f12, 0xC(r11)` | Load from f12, 0xC(r11). |
| `0x826DB7D4` | `fcmpu cr6, f12, f13` | Compare cr6, f12, f13 and update the specified condition register. |
| `0x826DB7D8` | `bne cr6, loc_826DB828` | Conditional branch to cr6, loc_826DB828 according to the named CR/CTR condition. |
| `0x826DB7DC` | `lbz r11, 0x1E(r11)` | Load from r11, 0x1E(r11). |
| `0x826DB7E0` | `cmpwi cr6, r11, 4` | Compare cr6, r11, 4 and update the specified condition register. |
| `0x826DB7E4` | `beq cr6, loc_826DB7F4` | Conditional branch to cr6, loc_826DB7F4 according to the named CR/CTR condition. |
| `0x826DB7E8` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DB7EC` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826DB7F0` | `bne cr6, loc_826DB7F8` | Conditional branch to cr6, loc_826DB7F8 according to the named CR/CTR condition. |
| `0x826DB7F4` | `li r11, 0` | Materialize immediate/address component: r11, 0. |
| `0x826DB7F8` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826DB7FC` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DB800` | `beq cr6, loc_826DB828` | Conditional branch to cr6, loc_826DB828 according to the named CR/CTR condition. |
| `0x826DB804` | `lwz r11, 0x58(r3)` | Load from r11, 0x58(r3). |
| `0x826DB808` | `add r10, r11, r8` | Integer/address arithmetic: r10, r11, r8. |
| `0x826DB80C` | `lbz r11, 0x79(r10)` | Load from r11, 0x79(r10). |
| `0x826DB810` | `cmplwi cr6, r11, 1` | Compare cr6, r11, 1 and update the specified condition register. |
| `0x826DB814` | `beq cr6, loc_826DB860` | Conditional branch to cr6, loc_826DB860 according to the named CR/CTR condition. |
| `0x826DB818` | `cmplwi cr6, r11, 2` | Compare cr6, r11, 2 and update the specified condition register. |
| `0x826DB81C` | `beq cr6, loc_826DB860` | Conditional branch to cr6, loc_826DB860 according to the named CR/CTR condition. |
| `0x826DB820` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DB824` | `beq cr6, loc_826DB84C` | Conditional branch to cr6, loc_826DB84C according to the named CR/CTR condition. |
| `0x826DB828` | `stfs f0, 4(r5)` | Store the source value to f0, 4(r5). |
| `0x826DB82C` | `addi r7, r7, 1` | Integer/address arithmetic: r7, r7, 1. |
| `0x826DB830` | `stfs f0, 8(r5)` | Store the source value to f0, 8(r5). |
| `0x826DB834` | `lbz r11, 0x182(r3)` | Load from r11, 0x182(r3). |
| `0x826DB838` | `addi r9, r9, 0x20 # ' '` | Integer/address arithmetic: r9, r9, 0x20 # ' '. |
| `0x826DB83C` | `addi r8, r8, 0x88` | Integer/address arithmetic: r8, r8, 0x88. |
| `0x826DB840` | `cmplw cr6, r7, r11` | Compare cr6, r7, r11 and update the specified condition register. |
| `0x826DB844` | `blt cr6, loc_826DB7C4` | Conditional branch to cr6, loc_826DB7C4 according to the named CR/CTR condition. |
| `0x826DB848` | `blr` | Return to the caller through LR. |
| `0x826DB84C` | `lis r11, flt_82001C98@ha` | Materialize immediate/address component: r11, flt_82001C98@ha. |
| `0x826DB850` | `stfs f0, 4(r5)` | Store the source value to f0, 4(r5). |
| `0x826DB854` | `lfs f13, flt_82001C98@l(r11)` | Load from f13, flt_82001C98@l(r11). |
| `0x826DB858` | `stfs f13, 8(r5)` | Store the source value to f13, 8(r5). |
| `0x826DB85C` | `blr` | Return to the caller through LR. |
| `0x826DB860` | `lwz r11, 0x18(r10)` | Load from r11, 0x18(r10). |
| `0x826DB864` | `stfs f0, 8(r5)` | Store the source value to f0, 8(r5). |
| `0x826DB868` | `extsw r11, r11` | Shift/rotate/mask or width-normalize: r11, r11. |
| `0x826DB86C` | `std r11, back_chain(r1)` | Store the source value to r11, back_chain(r1). |
| `0x826DB870` | `lfd f0, back_chain(r1)` | Load from f0, back_chain(r1). |
| `0x826DB874` | `fcfid f0, f0` | Floating-point arithmetic/select/conversion: f0, f0. |
| `0x826DB878` | `frsp f0, f0` | Floating-point arithmetic/select/conversion: f0, f0. |
| `0x826DB87C` | `stfs f0, 4(r5)` | Store the source value to f0, 4(r5). |
| `0x826DB880` | `blr` | Return to the caller through LR. |
| `0x826DB884` | `cmpwi cr6, r4, 4` | Compare cr6, r4, 4 and update the specified condition register. |
| `0x826DB888` | `bnelr cr6` | Conditionally return through LR when bne is satisfied. |
| `0x826DB88C` | `lwz r9, 0x10B8(r10)` | Load from r9, 0x10B8(r10). |
| `0x826DB890` | `lis r8, rw__audio__core__SndPlayer1_CgsStreamMod__ModifyStartTimeHandler@ha` | Materialize immediate/address component: r8, rw__audio__core__SndPlayer1_CgsStreamMod__ModifyStartTimeHandler@ha. |
| `0x826DB894` | `lwz r11, 0x20(r10)` | Load from r11, 0x20(r10). |
| `0x826DB898` | `addi r8, r8, rw__audio__core__SndPlayer1_CgsStreamMod__ModifyStartTimeHandler@l` | Integer/address arithmetic: r8, r8, rw__audio__core__SndPlayer1_CgsStreamMod__ModifyStartTimeHandler@l. |
| `0x826DB89C` | `add r11, r11, r9` | Integer/address arithmetic: r11, r11, r9. |
| `0x826DB8A0` | `addi r9, r9, 0x18` | Integer/address arithmetic: r9, r9, 0x18. |
| `0x826DB8A4` | `stw r9, 0x10B8(r10)` | Store the source value to r9, 0x10B8(r10). |
| `0x826DB8A8` | `stw r8, 0(r11)` | Store the source value to r8, 0(r11). |
| `0x826DB8AC` | `stw r3, 4(r11)` | Store the source value to r3, 4(r11). |
| `0x826DB8B0` | `lfd f0, 0(r5)` | Load from f0, 0(r5). |
| `0x826DB8B4` | `stfd f0, 8(r11)` | Store the source value to f0, 8(r11). |
| `0x826DB8B8` | `lfs f0, 8(r5)` | Load from f0, 8(r5). |
| `0x826DB8BC` | `stfs f0, 0x10(r11)` | Store the source value to f0, 0x10(r11). |
| `0x826DB8C0` | `blr` | Return to the caller through LR. |
| `0x826DB8C4` | `.long 0` | Adjacent exported data/alignment word: 0. |

#### (c) Rodata constants

| VA | file_off | Raw bytes | Decode/use |
|---:|---:|---|---|
| `0x82001C98` | `0x00004C98` | `3F 80 00 00` | `1.0f` |
| `0x82001CC0` | `0x00004CC0` | `00 00 00 00` | `0.0f` |
| `0x82001CA8` | `0x00004CA8` | `00 00 00 00 00 00 00 00` | `0.0` |
| `0x820B56EC` | `0x000B86EC` | `4A 80 00 00` | `4194304.0f`, handle wrap ceiling |

`dword_82FFBA08` is writable runtime state, not rodata; RootSoundModule seeds it to
`"SOUND\\STREAMS\\"` on both X360 and the current PC side.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x04` -> System `+0x20/+0x10B8` | append commands | deferred ring base/cursor |
| `+0x28/+0x38` | request-done tests | attribute handle / duration |
| `+0x160` | increment/wrap/store | `mRequestHandle` (embedded `f32`, not pointer) |
| `+0x164/+0x168` | request-done window | last processed / last successful |
| `+0x17C/+0x182` | request array/count | internal ring |
| external `+0x18/+0x79` | bytes fed/play type | buffered response |
| command `+0..` | handler/this/payload/path | Play/Stop/Modify command records |

#### (e) Implementation-grade C++ sketch

```cpp
void EventEvent(s32 event, void* pv)
{
    System* sys=mpSystemUseGetSystemAccessor;
    switch (event) {
    case 0: {
        auto& p=*static_cast<PlayParams*>(pv);
        mRequestHandle+=1.0f; if (mRequestHandle>4194304.0f) mRequestHandle=1.0f;
        p.requestHandle=mRequestHandle;
        const u32 pathBytes=p.pStreamFilePath
            ? u32(strlen(spPathPrefix)+strlen(p.pStreamFilePath)+1) : 1;
        const u32 bytes=AlignUp(0x28u+pathBytes,4u); // console fixed prefix
        PlayCommand* c=ReserveHostPlayCommand(sys,bytes,pathBytes);
        c->handler=&PlayHandler; c->self=this; c->startTime=p.startTime;
        c->streamFileOffset=p.streamFileOffset; c->streamPoolGuid=p.streamPoolGuid;
        c->pRamData=p.pRamData; c->sizeOfCommand=CheckedU16(HostPlayCommandBytes(pathBytes));
        c->expelMode=static_cast<u8>(static_cast<s32>(p.expelMode));
        c->requestHandle=mRequestHandle;
        if (pathBytes==1) c->path[0]=0;
        else { strcpy(c->path,spPathPrefix); strcat(c->path,p.pStreamFilePath); }
        break;
    }
    case 1: { auto* c=ReserveCommand<StopCommand>(sys); c->handler=&StopHandler; c->self=this; break; }
    case 2: {
        auto& p=*static_cast<IsRequestDoneParams*>(pv); p.isRequestDone=0.0f;
        if (p.requestHandle<mAttribute[0].mfValue ||
            ((p.requestHandle==mAttribute[0].mfValue ||
              (p.requestHandle<=mLastRequestHandleProcessed &&
               p.requestHandle>mLastRequestHandleSuccessfullyProcessed)) &&
             mAttribute[2].mfValue==0.0f)) p.isRequestDone=1.0f;
        break;
    }
    case 3: {
        auto& p=*static_cast<GetRequestBufferedParams*>(pv);
        for (u32 i=0;i<mMaxRequests;++i) {
            RequestInternal& r=Request(i);
            if (r.requestHandle==p.requestHandle && IsActive(r.state)) {
                RequestExternal& e=mpRequestExternal[i];
                if (e.playType==1 || e.playType==2) {
                    p.streamBytesBuffered=static_cast<f32>(e.numBytesFed);
                    p.isFullyBuffered=0.0f; return;
                }
                if (e.playType==0) { p.streamBytesBuffered=0.0f; p.isFullyBuffered=1.0f; return; }
            }
            p.streamBytesBuffered=0.0f; p.isFullyBuffered=0.0f;
        }
        break;
    }
    case 4: {
        auto& p=*static_cast<ModifyStartTimeParams*>(pv);
        auto* c=ReserveCommand<ModifyStartTimeCommand>(sys);
        c->handler=&ModifyStartTimeHandler; c->self=this;
        c->startTime=p.newStartTime; c->requestHandle=p.requestHandle; break;
    }
    }
}
```

X64 hazards: every command handler/self/path/RAM pointer widens; the producer cursor
must advance by the host record size (and the handler must return that same size), not
console `8/24` or fixed prefix `0x28`.  `mRequestHandle` is a float, not a pointer.
The command-size field is intentionally `u16`; range-check it.  Internal/external
strides are host `sizeof`.  No GetSize body occurs here.

### `GetPpuTicksEvent` (vtable slot 2) — `0x8268FE88`

#### (a) Exact signature / dispatch ABI

`r3=const this`, returns `u32` in `r3`: `virtual u32 GetPpuTicksEvent() const`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x8268FE88.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x8268FE88` | `lwz r3, 0x50(r3)` | Load from r3, 0x50(r3). |
| `0x8268FE8C` | `blr` | Return to the caller through LR. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x50` | `lwz` | `mTimerHandle.mCpuTicks` |

#### (e) Implementation-grade C++ sketch

```cpp
u32 GetPpuTicksEvent() const { return mTimerHandle.mCpuTicks; }
```

X64 hazards: none; this is a scalar field access, not a command handler or GetSize.

### scalar deleting destructor (vtable slot 3) — `0x826AA980`

#### (a) Exact signature / dispatch ABI

Compiler helper: `r3=this`, `r4=deleteFlags`, returns original `this` in `r3`.
There are no caller stack arguments; `r5` is not a parameter and is never read by the
body (the inaccurate export prototype's extra argument is spurious).

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826AA980.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826AA980` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826AA984` | `stw r12, var_8(r1)` | Store the source value to r12, var_8(r1). |
| `0x826AA988` | `std r30, var_18(r1)` | Store the source value to r30, var_18(r1). |
| `0x826AA98C` | `std r31, var_10(r1)` | Store the source value to r31, var_10(r1). |
| `0x826AA990` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826AA994` | `mr r31, r3` | Copy register value: r31, r3. |
| `0x826AA998` | `mr r30, r4` | Copy register value: r30, r4. |
| `0x826AA99C` | `addi r3, r31, 0x40 # '@'# a1  ; a1` | Integer/address arithmetic: r3, r31, 0x40 # '@'# a1  ; a1. |
| `0x826AA9A0` | `bl STUB` | Call STUB; place the return address in LR. |
| `0x826AA9A4` | `lis r11, off_820AA810@ha` | Materialize immediate/address component: r11, off_820AA810@ha. |
| `0x826AA9A8` | `clrlwi r10, r30, 31` | Shift/rotate/mask or width-normalize: r10, r30, 31. |
| `0x826AA9AC` | `addi r11, r11, off_820AA810@l` | Integer/address arithmetic: r11, r11, off_820AA810@l. |
| `0x826AA9B0` | `cmplwi cr6, r10, 0` | Compare cr6, r10, 0 and update the specified condition register. |
| `0x826AA9B4` | `mr r3, r31` | Copy register value: r3, r31. |
| `0x826AA9B8` | `stw r11, 0(r31)` | Store the source value to r11, 0(r31). |
| `0x826AA9BC` | `beq cr6, loc_826AA9C8` | Conditional branch to cr6, loc_826AA9C8 according to the named CR/CTR condition. |
| `0x826AA9C0` | `bl operator_delete` | Call operator_delete; place the return address in LR. |
| `0x826AA9C4` | `mr r3, r31` | Copy register value: r3, r31. |
| `0x826AA9C8` | `addi r1, r1, 0x70` | Integer/address arithmetic: r1, r1, 0x70. |
| `0x826AA9CC` | `lwz r12, var_8(r1)` | Load from r12, var_8(r1). |
| `0x826AA9D0` | `mtlr r12` | Restore/set LR from r12. |
| `0x826AA9D4` | `ld r30, var_18(r1)` | Load from r30, var_18(r1). |
| `0x826AA9D8` | `ld r31, var_10(r1)` | Load from r31, var_10(r1). |
| `0x826AA9DC` | `blr` | Return to the caller through LR. |

#### (c) Rodata constants

| VA | file_off | Raw bytes | Decode/use |
|---:|---:|---|---|
| `0x820AA810` | `0x000AD810` | `82 84 CB 38 82 84 CB 38 82 7E 2F 38 82 68 04 18` | base PlugIn destructing vtable sentinel |

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x40` | pass subobject to destructor thunk | `mTimerHandle` |
| `+0x00` | install base vptr | hidden vptr |

#### (e) Implementation-grade C++ sketch

```cpp
SndPlayer1_CgsStreamMod* ScalarDeletingDestructor(SndPlayer1_CgsStreamMod* self,u32 flags)
{
    self->mTimerHandle.~TimerHandle();
    // native destructor naturally installs the base vptr
    if (flags&1) ::operator delete(self);
    return self;
}
```

X64 hazards: the vptr widens and must be compiler-generated; do not store the console
vtable address.  No record stride, narrow pointer, deferred return, or GetSize issue.

### `UnpackHeader` — corrected start `0x8268C990`

#### (a) Exact signature / dispatch ABI

Member helper: `r3=this`, `r4=u32 requestIndex`, `r5=void* packedHeader`; incidental
last `BitGetter` result remains in `r3`.  Semantic declaration is `void
UnpackHeader(u32, void*)`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x8268C990.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x8268C990` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x8268C994` | `bl __savegprlr_26` | Call __savegprlr_26; place the return address in LR. |
| `0x8268C998` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x8268C99C` | `mr r11, r3` | Copy register value: r11, r3. |
| `0x8268C9A0` | `slwi r7, r4, 5` | Shift/rotate/mask or width-normalize: r7, r4, 5. |
| `0x8268C9A4` | `mr r28, r5` | Copy register value: r28, r5. |
| `0x8268C9A8` | `li r27, 0` | Materialize immediate/address component: r27, 0. |
| `0x8268C9AC` | `mulli r10, r4, 0x88` | Integer/address arithmetic: r10, r4, 0x88. |
| `0x8268C9B0` | `lhz r8, 0x17C(r11)` | Load from r8, 0x17C(r11). |
| `0x8268C9B4` | `lwz r9, 0x58(r11)` | Load from r9, 0x58(r11). |
| `0x8268C9B8` | `stw r28, 0xA0+var_50(r1)` | Store the source value to r28, 0xA0+var_50(r1). |
| `0x8268C9BC` | `stw r27, 0xA0+var_4C(r1)` | Store the source value to r27, 0xA0+var_4C(r1). |
| `0x8268C9C0` | `add r8, r8, r7` | Integer/address arithmetic: r8, r8, r7. |
| `0x8268C9C4` | `li r4, 4` | Materialize immediate/address component: r4, 4. |
| `0x8268C9C8` | `addi r3, r1, 0xA0+var_50` | Integer/address arithmetic: r3, r1, 0xA0+var_50. |
| `0x8268C9CC` | `add r31, r8, r11` | Integer/address arithmetic: r31, r8, r11. |
| `0x8268C9D0` | `add r30, r10, r9` | Integer/address arithmetic: r30, r10, r9. |
| `0x8268C9D4` | `bl rw__audio__core__BitGetter__GetBits` | Call rw__audio__core__BitGetter__GetBits; place the return address in LR. |
| `0x8268C9D8` | `li r4, 4` | Materialize immediate/address component: r4, 4. |
| `0x8268C9DC` | `addi r3, r1, 0xA0+var_50` | Integer/address arithmetic: r3, r1, 0xA0+var_50. |
| `0x8268C9E0` | `bl rw__audio__core__BitGetter__GetBits` | Call rw__audio__core__BitGetter__GetBits; place the return address in LR. |
| `0x8268C9E4` | `mr r11, r3` | Copy register value: r11, r3. |
| `0x8268C9E8` | `li r4, 6` | Materialize immediate/address component: r4, 6. |
| `0x8268C9EC` | `addi r3, r1, 0xA0+var_50` | Integer/address arithmetic: r3, r1, 0xA0+var_50. |
| `0x8268C9F0` | `stb r11, 0x78(r30)` | Store the source value to r11, 0x78(r30). |
| `0x8268C9F4` | `bl rw__audio__core__BitGetter__GetBits` | Call rw__audio__core__BitGetter__GetBits; place the return address in LR. |
| `0x8268C9F8` | `addi r11, r3, 1` | Integer/address arithmetic: r11, r3, 1. |
| `0x8268C9FC` | `li r4, 0x12` | Materialize immediate/address component: r4, 0x12. |
| `0x8268CA00` | `addi r3, r1, 0xA0+var_50` | Integer/address arithmetic: r3, r1, 0xA0+var_50. |
| `0x8268CA04` | `stb r11, 0x1F(r31)` | Store the source value to r11, 0x1F(r31). |
| `0x8268CA08` | `bl rw__audio__core__BitGetter__GetBits` | Call rw__audio__core__BitGetter__GetBits; place the return address in LR. |
| `0x8268CA0C` | `clrldi r11, r3, 32` | Shift/rotate/mask or width-normalize: r11, r3, 32. |
| `0x8268CA10` | `li r4, 2` | Materialize immediate/address component: r4, 2. |
| `0x8268CA14` | `addi r3, r1, 0xA0+var_50` | Integer/address arithmetic: r3, r1, 0xA0+var_50. |
| `0x8268CA18` | `std r11, 0xA0+var_48(r1)` | Store the source value to r11, 0xA0+var_48(r1). |
| `0x8268CA1C` | `lfd f0, 0xA0+var_48(r1)` | Load from f0, 0xA0+var_48(r1). |
| `0x8268CA20` | `fcfid f0, f0` | Floating-point arithmetic/select/conversion: f0, f0. |
| `0x8268CA24` | `frsp f0, f0` | Floating-point arithmetic/select/conversion: f0, f0. |
| `0x8268CA28` | `stfs f0, 0x10(r31)` | Store the source value to f0, 0x10(r31). |
| `0x8268CA2C` | `bl rw__audio__core__BitGetter__GetBits` | Call rw__audio__core__BitGetter__GetBits; place the return address in LR. |
| `0x8268CA30` | `mr r11, r3` | Copy register value: r11, r3. |
| `0x8268CA34` | `li r4, 1` | Materialize immediate/address component: r4, 1. |
| `0x8268CA38` | `addi r3, r1, 0xA0+var_50` | Integer/address arithmetic: r3, r1, 0xA0+var_50. |
| `0x8268CA3C` | `stb r11, 0x79(r30)` | Store the source value to r11, 0x79(r30). |
| `0x8268CA40` | `bl rw__audio__core__BitGetter__GetBits` | Call rw__audio__core__BitGetter__GetBits; place the return address in LR. |
| `0x8268CA44` | `mr r29, r3` | Copy register value: r29, r3. |
| `0x8268CA48` | `li r4, 0x1D` | Materialize immediate/address component: r4, 0x1D. |
| `0x8268CA4C` | `addi r3, r1, 0xA0+var_50` | Integer/address arithmetic: r3, r1, 0xA0+var_50. |
| `0x8268CA50` | `bl rw__audio__core__BitGetter__GetBits` | Call rw__audio__core__BitGetter__GetBits; place the return address in LR. |
| `0x8268CA54` | `clrlwi r29, r29, 24` | Shift/rotate/mask or width-normalize: r29, r29, 24. |
| `0x8268CA58` | `stw r3, 0x14(r31)` | Store the source value to r3, 0x14(r31). |
| `0x8268CA5C` | `cmplwi cr6, r29, 0` | Compare cr6, r29, 0 and update the specified condition register. |
| `0x8268CA60` | `beq cr6, loc_8268CA78` | Conditional branch to cr6, loc_8268CA78 according to the named CR/CTR condition. |
| `0x8268CA64` | `li r4, 0x20 # ' '` | Materialize immediate/address component: r4, 0x20 # ' '. |
| `0x8268CA68` | `addi r3, r1, 0xA0+var_50` | Integer/address arithmetic: r3, r1, 0xA0+var_50. |
| `0x8268CA6C` | `bl rw__audio__core__BitGetter__GetBits` | Call rw__audio__core__BitGetter__GetBits; place the return address in LR. |
| `0x8268CA70` | `stw r3, 0x18(r31)` | Store the source value to r3, 0x18(r31). |
| `0x8268CA74` | `b loc_8268CA80` | Branch unconditionally to loc_8268CA80. |
| `0x8268CA78` | `li r11, -1` | Materialize immediate/address component: r11, -1. |
| `0x8268CA7C` | `stw r11, 0x18(r31)` | Store the source value to r11, 0x18(r31). |
| `0x8268CA80` | `lbz r26, 0x79(r30)` | Load from r26, 0x79(r30). |
| `0x8268CA84` | `cmplwi cr6, r26, 2` | Compare cr6, r26, 2 and update the specified condition register. |
| `0x8268CA88` | `bne cr6, loc_8268CA9C` | Conditional branch to cr6, loc_8268CA9C according to the named CR/CTR condition. |
| `0x8268CA8C` | `li r4, 0x20 # ' '` | Materialize immediate/address component: r4, 0x20 # ' '. |
| `0x8268CA90` | `addi r3, r1, 0xA0+var_50` | Integer/address arithmetic: r3, r1, 0xA0+var_50. |
| `0x8268CA94` | `bl rw__audio__core__BitGetter__GetBits` | Call rw__audio__core__BitGetter__GetBits; place the return address in LR. |
| `0x8268CA98` | `stw r3, 0x10(r30)` | Store the source value to r3, 0x10(r30). |
| `0x8268CA9C` | `cmplwi cr6, r29, 0` | Compare cr6, r29, 0 and update the specified condition register. |
| `0x8268CAA0` | `beq cr6, loc_8268CADC` | Conditional branch to cr6, loc_8268CADC according to the named CR/CTR condition. |
| `0x8268CAA4` | `cmplwi cr6, r26, 1` | Compare cr6, r26, 1 and update the specified condition register. |
| `0x8268CAA8` | `beq cr6, loc_8268CACC` | Conditional branch to cr6, loc_8268CACC according to the named CR/CTR condition. |
| `0x8268CAAC` | `cmplwi cr6, r26, 2` | Compare cr6, r26, 2 and update the specified condition register. |
| `0x8268CAB0` | `bne cr6, loc_8268CAC4` | Conditional branch to cr6, loc_8268CAC4 according to the named CR/CTR condition. |
| `0x8268CAB4` | `lwz r11, 0x18(r31)` | Load from r11, 0x18(r31). |
| `0x8268CAB8` | `lwz r10, 0x10(r30)` | Load from r10, 0x10(r30). |
| `0x8268CABC` | `cmpw cr6, r11, r10` | Compare cr6, r11, r10 and update the specified condition register. |
| `0x8268CAC0` | `bge cr6, loc_8268CACC` | Conditional branch to cr6, loc_8268CACC according to the named CR/CTR condition. |
| `0x8268CAC4` | `stw r27, 0xC(r30)` | Store the source value to r27, 0xC(r30). |
| `0x8268CAC8` | `b loc_8268CADC` | Branch unconditionally to loc_8268CADC. |
| `0x8268CACC` | `li r4, 0x20 # ' '` | Materialize immediate/address component: r4, 0x20 # ' '. |
| `0x8268CAD0` | `addi r3, r1, 0xA0+var_50` | Integer/address arithmetic: r3, r1, 0xA0+var_50. |
| `0x8268CAD4` | `bl rw__audio__core__BitGetter__GetBits` | Call rw__audio__core__BitGetter__GetBits; place the return address in LR. |
| `0x8268CAD8` | `stw r3, 0xC(r30)` | Store the source value to r3, 0xC(r30). |
| `0x8268CADC` | `lwz r11, 0xA0+var_4C(r1)` | Load from r11, 0xA0+var_4C(r1). |
| `0x8268CAE0` | `srwi r11, r11, 3` | Shift/rotate/mask or width-normalize: r11, r11, 3. |
| `0x8268CAE4` | `add r11, r11, r28` | Integer/address arithmetic: r11, r11, r28. |
| `0x8268CAE8` | `stw r11, 8(r30)` | Store the source value to r11, 8(r30). |
| `0x8268CAEC` | `addi r1, r1, 0xA0` | Integer/address arithmetic: r1, r1, 0xA0. |
| `0x8268CAF0` | `b __restgprlr_26` | Branch unconditionally to __restgprlr_26. |

#### (c) Rodata constants

None; all bit widths are immediates.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x58`, ext stride `0x88` | find external record | `mpRequestExternal[index]` |
| `+0x17C`, internal stride `0x20` | find internal record | `Request(index)` |
| internal `+0x10/+0x14/+0x18/+0x1F` | sample rate/count/loop/channels | named fields |
| external `+0x08/+0x0C/+0x10/+0x78/+0x79` | payload, loop stream offset, RAM count, codec/play type | named fields |

#### (e) Implementation-grade C++ sketch

```cpp
void UnpackHeader(u32 i,void* packed)
{
    BitGetter b(packed); RequestInternal& r=Request(i); RequestExternal& e=mpRequestExternal[i];
    (void)b.GetBits(4); e.codec=static_cast<u8>(b.GetBits(4));
    r.numChannels=static_cast<u8>(b.GetBits(6)+1);
    r.sampleRate=static_cast<f32>(b.GetBits(18));
    e.playType=static_cast<u8>(b.GetBits(2));
    const bool loop=b.GetBits(1)!=0; r.numSamples=static_cast<s32>(b.GetBits(29));
    r.loopStart=loop?static_cast<s32>(b.GetBits(32)):-1;
    if (e.playType==2) e.gigaSamplesInRam=static_cast<s32>(b.GetBits(32));
    if (loop) {
        if (e.playType==1 || (e.playType==2 && r.loopStart>=e.gigaSamplesInRam))
            e.loopStartStreamOffset=static_cast<s32>(b.GetBits(32));
        else e.loopStartStreamOffset=0;
    }
    e.pSampleData=static_cast<u8*>(packed)+(b.BitPosition()>>3);
}
```

X64 hazards: `pSampleData` widens; use host external/internal strides.  The packed file
format remains bit-exact and does not use host pointer layout.  No deferred return or
GetSize issue.

### `WaitForStartTime` — `0x8268CAF8`

#### (a) Exact signature / dispatch ABI

Member helper lowering is `r3=this` (unused), `r4=Mixer*`, `f1=startTime`, and
`r6=u32* silenceSamples` (the double consumes its ABI argument slots).  Returns bool in
`r3`: `bool WaitForStartTime(Mixer*, double, u32*)`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x8268CAF8.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x8268CAF8` | `lis r11, 3` | Materialize immediate/address component: r11, 3. |
| `0x8268CAFC` | `lfdx f0, r4, r11` | Load from f0, r4, r11. |
| `0x8268CB00` | `lis r11, dbl_82001CA8@ha` | Materialize immediate/address component: r11, dbl_82001CA8@ha. |
| `0x8268CB04` | `fsub f0, f1, f0` | Floating-point arithmetic/select/conversion: f0, f1, f0. |
| `0x8268CB08` | `lfd f13, dbl_82001CA8@l(r11)` | Load from f13, dbl_82001CA8@l(r11). |
| `0x8268CB0C` | `fcmpu cr6, f0, f13` | Compare cr6, f0, f13 and update the specified condition register. |
| `0x8268CB10` | `ble cr6, loc_8268CB64` | Conditional branch to cr6, loc_8268CB64 according to the named CR/CTR condition. |
| `0x8268CB14` | `lis r11, 3` | Materialize immediate/address component: r11, 3. |
| `0x8268CB18` | `ori r11, r11, 0x18 # 0x30018` | Bitwise operation: r11, r11, 0x18 # 0x30018. |
| `0x8268CB1C` | `lwzx r11, r4, r11` | Load from r11, r4, r11. |
| `0x8268CB20` | `lfs f13, 0xC(r11)` | Load from f13, 0xC(r11). |
| `0x8268CB24` | `lis r11, flt_820ADBFC@ha` | Materialize immediate/address component: r11, flt_820ADBFC@ha. |
| `0x8268CB28` | `fmul f0, f13, f0` | Floating-point arithmetic/select/conversion: f0, f13, f0. |
| `0x8268CB2C` | `lfs f13, flt_820ADBFC@l(r11)` | Load from f13, flt_820ADBFC@l(r11). |
| `0x8268CB30` | `frsp f0, f0` | Floating-point arithmetic/select/conversion: f0, f0. |
| `0x8268CB34` | `fcmpu cr6, f0, f13` | Compare cr6, f0, f13 and update the specified condition register. |
| `0x8268CB38` | `blt cr6, loc_8268CB44` | Conditional branch to cr6, loc_8268CB44 according to the named CR/CTR condition. |
| `0x8268CB3C` | `li r3, 0` | Materialize immediate/address component: r3, 0. |
| `0x8268CB40` | `blr` | Return to the caller through LR. |
| `0x8268CB44` | `lis r11, 3` | Materialize immediate/address component: r11, 3. |
| `0x8268CB48` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x8268CB4C` | `ori r11, r11, 0x28 # '(' # 0x30028` | Bitwise operation: r11, r11, 0x28 # '(' # 0x30028. |
| `0x8268CB50` | `lfsx f13, r4, r11` | Load from f13, r4, r11. |
| `0x8268CB54` | `fmuls f0, f13, f0` | Floating-point arithmetic/select/conversion: f0, f13, f0. |
| `0x8268CB58` | `fctidz f0, f0` | Execute the exact PPC operation shown: f0, f0. |
| `0x8268CB5C` | `stfiwx f0, 0, r6` | Store the source value to f0, 0, r6. |
| `0x8268CB60` | `blr` | Return to the caller through LR. |
| `0x8268CB64` | `li r11, 0` | Materialize immediate/address component: r11, 0. |
| `0x8268CB68` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x8268CB6C` | `stw r11, 0(r6)` | Store the source value to r11, 0(r6). |
| `0x8268CB70` | `blr` | Return to the caller through LR. |
| `0x8268CB74` | `.long 0` | Adjacent exported data/alignment word: 0. |

#### (c) Rodata constants

| VA | file_off | Raw bytes | Decode/use |
|---:|---:|---|---|
| `0x82001CA8` | `0x00004CA8` | `00 00 00 00 00 00 00 00` | `0.0` |
| `0x820ADBFC` | `0x000B0BFC` | `43 80 00 00` | `256.0f` |

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| Mixer `+0x30000` | subtract | `mdStreamTime` |
| Mixer `+0x30018 -> +0x0C` | multiply delta | `mpFormat->mfSampleRate` |
| Mixer `+0x30028` | final scale before integer conversion | `mfResampleGain` |

#### (e) Implementation-grade C++ sketch

```cpp
bool WaitForStartTime(Mixer* m,double start,u32* out)
{
    const double dt=start-m->mdStreamTime;
    if (dt<=0.0) { *out=0; return true; }
    const f32 frames=static_cast<f32>(m->mpFormat->mfSampleRate*dt);
    if (frames>=256.0f) return false;
    *out=static_cast<u32>(m->mfResampleGain*frames); return true;
}
```

X64 hazards: Mixer format pointer widens; no console record stride, deferred return,
narrow pointer, or GetSize issue.

### `Declick` — `0x8268CB78`

#### (a) Exact signature / dispatch ABI

`r3=this`, `r4=Mixer*`, returns `BufferStatus=1` in `r3`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x8268CB78.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x8268CB78` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x8268CB7C` | `bl __savegprlr_28` | Call __savegprlr_28; place the return address in LR. |
| `0x8268CB80` | `mr r7, r3` | Copy register value: r7, r3. |
| `0x8268CB84` | `addis r29, r4, 3` | Integer/address arithmetic: r29, r4, 3. |
| `0x8268CB88` | `addi r29, r29, 0x10` | Integer/address arithmetic: r29, r29, 0x10. |
| `0x8268CB8C` | `lhz r11, 0x17A(r7)` | Load from r11, 0x17A(r7). |
| `0x8268CB90` | `lbz r28, 0x184(r7)` | Load from r28, 0x184(r7). |
| `0x8268CB94` | `add r8, r11, r7` | Integer/address arithmetic: r8, r11, r7. |
| `0x8268CB98` | `lhz r9, 0x178(r7)` | Load from r9, 0x178(r7). |
| `0x8268CB9C` | `mr r11, r28` | Copy register value: r11, r28. |
| `0x8268CBA0` | `lwz r10, 0(r29)` | Load from r10, 0(r29). |
| `0x8268CBA4` | `cmplw cr6, r11, r9` | Compare cr6, r11, r9 and update the specified condition register. |
| `0x8268CBA8` | `mr r6, r11` | Copy register value: r6, r11. |
| `0x8268CBAC` | `blt cr6, loc_8268CBB4` | Conditional branch to cr6, loc_8268CBB4 according to the named CR/CTR condition. |
| `0x8268CBB0` | `mr r6, r9` | Copy register value: r6, r9. |
| `0x8268CBB4` | `lbz r9, 0x21(r7)` | Load from r9, 0x21(r7). |
| `0x8268CBB8` | `cmplwi cr6, r9, 0` | Compare cr6, r9, 0 and update the specified condition register. |
| `0x8268CBBC` | `beq cr6, loc_8268CCA0` | Conditional branch to cr6, loc_8268CCA0 according to the named CR/CTR condition. |
| `0x8268CBC0` | `extsw r9, r11` | Shift/rotate/mask or width-normalize: r9, r11. |
| `0x8268CBC4` | `lwz r11, 4(r10)` | Load from r11, 4(r10). |
| `0x8268CBC8` | `lhz r10, 0xE(r10)` | Load from r10, 0xE(r10). |
| `0x8268CBCC` | `mr r5, r11` | Copy register value: r5, r11. |
| `0x8268CBD0` | `lbz r31, 0x21(r7)` | Load from r31, 0x21(r7). |
| `0x8268CBD4` | `addi r3, r11, 8` | Integer/address arithmetic: r3, r11, 8. |
| `0x8268CBD8` | `lis r11, flt_82001C98@ha` | Materialize immediate/address component: r11, flt_82001C98@ha. |
| `0x8268CBDC` | `std r9, back_chain(r1)` | Store the source value to r9, back_chain(r1). |
| `0x8268CBE0` | `rotlwi r30, r10, 2` | Shift/rotate/mask or width-normalize: r30, r10, 2. |
| `0x8268CBE4` | `lfd f0, back_chain(r1)` | Load from f0, back_chain(r1). |
| `0x8268CBE8` | `fcfid f0, f0` | Floating-point arithmetic/select/conversion: f0, f0. |
| `0x8268CBEC` | `frsp f13, f0` | Floating-point arithmetic/select/conversion: f13, f0. |
| `0x8268CBF0` | `lfs f0, flt_82001C98@l(r11)` | Load from f0, flt_82001C98@l(r11). |
| `0x8268CBF4` | `fdivs f11, f0, f13` | Floating-point arithmetic/select/conversion: f11, f0, f13. |
| `0x8268CBF8` | `lfs f13, 0(r8)` | Load from f13, 0(r8). |
| `0x8268CBFC` | `li r9, 0` | Materialize immediate/address component: r9, 0. |
| `0x8268CC00` | `cmpwi cr6, r6, 4` | Compare cr6, r6, 4 and update the specified condition register. |
| `0x8268CC04` | `fmuls f0, f13, f11` | Floating-point arithmetic/select/conversion: f0, f13, f11. |
| `0x8268CC08` | `blt cr6, loc_8268CC54` | Conditional branch to cr6, loc_8268CC54 according to the named CR/CTR condition. |
| `0x8268CC0C` | `addi r10, r6, -4` | Integer/address arithmetic: r10, r6, -4. |
| `0x8268CC10` | `mr r11, r3` | Copy register value: r11, r3. |
| `0x8268CC14` | `srwi r10, r10, 2` | Shift/rotate/mask or width-normalize: r10, r10, 2. |
| `0x8268CC18` | `addi r10, r10, 1` | Integer/address arithmetic: r10, r10, 1. |
| `0x8268CC1C` | `slwi r9, r10, 2` | Shift/rotate/mask or width-normalize: r9, r10, 2. |
| `0x8268CC20` | `fsubs f13, f13, f0` | Floating-point arithmetic/select/conversion: f13, f13, f0. |
| `0x8268CC24` | `stfs f13, -8(r11)` | Store the source value to f13, -8(r11). |
| `0x8268CC28` | `addi r10, r10, -1` | Integer/address arithmetic: r10, r10, -1. |
| `0x8268CC2C` | `cmplwi cr6, r10, 0` | Compare cr6, r10, 0 and update the specified condition register. |
| `0x8268CC30` | `fsubs f13, f13, f0` | Floating-point arithmetic/select/conversion: f13, f13, f0. |
| `0x8268CC34` | `stfs f13, -4(r11)` | Store the source value to f13, -4(r11). |
| `0x8268CC38` | `fsubs f12, f13, f0` | Floating-point arithmetic/select/conversion: f12, f13, f0. |
| `0x8268CC3C` | `stfs f12, 0(r11)` | Store the source value to f12, 0(r11). |
| `0x8268CC40` | `fsubs f13, f12, f0` | Floating-point arithmetic/select/conversion: f13, f12, f0. |
| `0x8268CC44` | `stfs f13, 4(r11)` | Store the source value to f13, 4(r11). |
| `0x8268CC48` | `addi r11, r11, 0x10` | Integer/address arithmetic: r11, r11, 0x10. |
| `0x8268CC4C` | `bne cr6, loc_8268CC20` | Conditional branch to cr6, loc_8268CC20 according to the named CR/CTR condition. |
| `0x8268CC50` | `stfs f13, 0(r8)` | Store the source value to f13, 0(r8). |
| `0x8268CC54` | `cmplw cr6, r9, r6` | Compare cr6, r9, r6 and update the specified condition register. |
| `0x8268CC58` | `bge cr6, loc_8268CC88` | Conditional branch to cr6, loc_8268CC88 according to the named CR/CTR condition. |
| `0x8268CC5C` | `slwi r10, r9, 2` | Shift/rotate/mask or width-normalize: r10, r9, 2. |
| `0x8268CC60` | `lfs f13, 0(r8)` | Load from f13, 0(r8). |
| `0x8268CC64` | `subf r11, r9, r6` | Integer/address arithmetic: r11, r9, r6. |
| `0x8268CC68` | `add r10, r10, r5` | Integer/address arithmetic: r10, r10, r5. |
| `0x8268CC6C` | `addi r11, r11, -1` | Integer/address arithmetic: r11, r11, -1. |
| `0x8268CC70` | `fsubs f13, f13, f0` | Floating-point arithmetic/select/conversion: f13, f13, f0. |
| `0x8268CC74` | `stfs f13, 0(r10)` | Store the source value to f13, 0(r10). |
| `0x8268CC78` | `addi r10, r10, 4` | Integer/address arithmetic: r10, r10, 4. |
| `0x8268CC7C` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x8268CC80` | `bne cr6, loc_8268CC6C` | Conditional branch to cr6, loc_8268CC6C according to the named CR/CTR condition. |
| `0x8268CC84` | `stfs f13, 0(r8)` | Store the source value to f13, 0(r8). |
| `0x8268CC88` | `addi r31, r31, -1` | Integer/address arithmetic: r31, r31, -1. |
| `0x8268CC8C` | `add r5, r30, r5` | Integer/address arithmetic: r5, r30, r5. |
| `0x8268CC90` | `add r3, r30, r3` | Integer/address arithmetic: r3, r30, r3. |
| `0x8268CC94` | `addi r8, r8, 4` | Integer/address arithmetic: r8, r8, 4. |
| `0x8268CC98` | `cmplwi cr6, r31, 0` | Compare cr6, r31, 0 and update the specified condition register. |
| `0x8268CC9C` | `bne cr6, loc_8268CBF8` | Conditional branch to cr6, loc_8268CBF8 according to the named CR/CTR condition. |
| `0x8268CCA0` | `clrlwi r11, r28, 24` | Shift/rotate/mask or width-normalize: r11, r28, 24. |
| `0x8268CCA4` | `lis r9, 3` | Materialize immediate/address component: r9, 3. |
| `0x8268CCA8` | `subf r10, r6, r11` | Integer/address arithmetic: r10, r6, r11. |
| `0x8268CCAC` | `addis r11, r4, 3` | Integer/address arithmetic: r11, r4, 3. |
| `0x8268CCB0` | `lis r8, 3` | Materialize immediate/address component: r8, 3. |
| `0x8268CCB4` | `addi r11, r11, 0xC` | Integer/address arithmetic: r11, r11, 0xC. |
| `0x8268CCB8` | `lis r5, 3` | Materialize immediate/address component: r5, 3. |
| `0x8268CCBC` | `stb r10, 0x184(r7)` | Store the source value to r10, 0x184(r7). |
| `0x8268CCC0` | `ori r9, r9, 0x2C # ',' # 0x3002C` | Bitwise operation: r9, r9, 0x2C # ',' # 0x3002C. |
| `0x8268CCC4` | `lwz r10, 0(r29)` | Load from r10, 0(r29). |
| `0x8268CCC8` | `ori r8, r8, 0x24 # '$' # 0x30024` | Bitwise operation: r8, r8, 0x24 # '$' # 0x30024. |
| `0x8268CCCC` | `ori r5, r5, 0x20 # ' ' # 0x30020` | Bitwise operation: r5, r5, 0x20 # ' ' # 0x30020. |
| `0x8268CCD0` | `lwz r3, 0(r11)` | Load from r3, 0(r11). |
| `0x8268CCD4` | `stw r10, 0(r11)` | Store the source value to r10, 0(r11). |
| `0x8268CCD8` | `stw r3, 0(r29)` | Store the source value to r3, 0(r29). |
| `0x8268CCDC` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x8268CCE0` | `lbz r11, 0x21(r7)` | Load from r11, 0x21(r7). |
| `0x8268CCE4` | `stbx r11, r4, r9` | Store the source value to r11, r4, r9. |
| `0x8268CCE8` | `lfs f0, 0x16C(r7)` | Load from f0, 0x16C(r7). |
| `0x8268CCEC` | `stfsx f0, r4, r8` | Store the source value to f0, r4, r8. |
| `0x8268CCF0` | `stwx r6, r4, r5` | Store the source value to r6, r4, r5. |
| `0x8268CCF4` | `lbz r11, 0x184(r7)` | Load from r11, 0x184(r7). |
| `0x8268CCF8` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x8268CCFC` | `bne cr6, loc_8268CD08` | Conditional branch to cr6, loc_8268CD08 according to the named CR/CTR condition. |
| `0x8268CD00` | `li r11, 0` | Materialize immediate/address component: r11, 0. |
| `0x8268CD04` | `stb r11, 0x183(r7)` | Store the source value to r11, 0x183(r7). |
| `0x8268CD08` | `b __restgprlr_28` | Branch unconditionally to __restgprlr_28. |

#### (c) Rodata constants

| VA | file_off | Raw bytes | Decode/use |
|---:|---:|---|---|
| `0x82001C98` | `0x00004C98` | `3F 80 00 00` | `1.0f`, reciprocal numerator |

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x17A` | tail base | `mDeclickBufferOffset` |
| `+0x178/+0x184` | min requested/remaining | `mSamplesRequested/mNumDeclickSamples` |
| `+0x183` | clear when drained | `mDcOffsetsGathered` |
| `+0x21/+0x16C` | output channels/rate | plugin format |
| Mixer `+0x3000C/+0x30010/+0x30020/+0x30024/+0x3002C` | swap/publish | named Mixer fields |
| dst SampleBuffer `+4/+0x0E` | channel writes | `mpSamples/muStride` |

#### (e) Implementation-grade C++ sketch

```cpp
BufferStatus Declick(Mixer* m)
{
    const u32 emit=Min<u32>(mNumDeclickSamples,mSamplesRequested);
    for (u32 c=0;c<mOutputChannels;++c) {
        f32& last=DeclickBuffer()[c]; const f32 step=last/f32(mNumDeclickSamples);
        f32* dst=m->mpDstBuffer->mpSamples+c*m->mpDstBuffer->muStride;
        for (u32 n=0;n<emit;++n) dst[n]=(last-=step);
    }
    mNumDeclickSamples=static_cast<u8>(mNumDeclickSamples-emit);
    Swap(m->mpSrcBuffer,m->mpDstBuffer); m->mNumSamples=emit;
    m->mfSampleRate=mPreviousSampleRate; m->mbChannelCount=mOutputChannels;
    if (!mNumDeclickSamples) mDcOffsetsGathered=0;
    return BUFFER_AVAILABLE;
}
```

X64 hazards: SampleBuffer pointers widen; declick base must come from host layout, not
console `+0x188`.  No deferred return, narrow pointer, or GetSize issue.

### `AdvanceCurrentRequest` — `0x8268CD20`

#### (a) Exact signature / dispatch ABI

`r3=this`; assembly returns the unchanged `this` in `r3`, while DecFIGS declares the
semantic helper `void AdvanceCurrentRequest()`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x8268CD20.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x8268CD20` | `lbz r11, 0x181(r3)` | Load from r11, 0x181(r3). |
| `0x8268CD24` | `lbz r10, 0x182(r3)` | Load from r10, 0x182(r3). |
| `0x8268CD28` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x8268CD2C` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x8268CD30` | `mr r9, r11` | Copy register value: r9, r11. |
| `0x8268CD34` | `cmplw cr6, r9, r10` | Compare cr6, r9, r10 and update the specified condition register. |
| `0x8268CD38` | `stb r11, 0x181(r3)` | Store the source value to r11, 0x181(r3). |
| `0x8268CD3C` | `li r10, 0` | Materialize immediate/address component: r10, 0. |
| `0x8268CD40` | `bne cr6, loc_8268CD48` | Conditional branch to cr6, loc_8268CD48 according to the named CR/CTR condition. |
| `0x8268CD44` | `stb r10, 0x181(r3)` | Store the source value to r10, 0x181(r3). |
| `0x8268CD48` | `lbz r9, 0x181(r3)` | Load from r9, 0x181(r3). |
| `0x8268CD4C` | `lhz r11, 0x17C(r3)` | Load from r11, 0x17C(r3). |
| `0x8268CD50` | `rotlwi r9, r9, 5` | Shift/rotate/mask or width-normalize: r9, r9, 5. |
| `0x8268CD54` | `stw r10, 0x158(r3)` | Store the source value to r10, 0x158(r3). |
| `0x8268CD58` | `stw r10, 0x15C(r3)` | Store the source value to r10, 0x15C(r3). |
| `0x8268CD5C` | `add r11, r11, r9` | Integer/address arithmetic: r11, r11, r9. |
| `0x8268CD60` | `add r11, r11, r3` | Integer/address arithmetic: r11, r11, r3. |
| `0x8268CD64` | `lbz r9, 0x1E(r11)` | Load from r9, 0x1E(r11). |
| `0x8268CD68` | `cmpwi cr6, r9, 4` | Compare cr6, r9, 4 and update the specified condition register. |
| `0x8268CD6C` | `beq cr6, loc_8268CD7C` | Conditional branch to cr6, loc_8268CD7C according to the named CR/CTR condition. |
| `0x8268CD70` | `cmpwi cr6, r9, 0` | Compare cr6, r9, 0 and update the specified condition register. |
| `0x8268CD74` | `li r9, 1` | Materialize immediate/address component: r9, 1. |
| `0x8268CD78` | `bne cr6, loc_8268CD80` | Conditional branch to cr6, loc_8268CD80 according to the named CR/CTR condition. |
| `0x8268CD7C` | `mr r9, r10` | Copy register value: r9, r10. |
| `0x8268CD80` | `clrlwi r9, r9, 24` | Shift/rotate/mask or width-normalize: r9, r9, 24. |
| `0x8268CD84` | `cmplwi cr6, r9, 0` | Compare cr6, r9, 0 and update the specified condition register. |
| `0x8268CD88` | `beqlr cr6` | Conditionally return through LR when beq is satisfied. |
| `0x8268CD8C` | `stw r10, 0x158(r3)` | Store the source value to r10, 0x158(r3). |
| `0x8268CD90` | `lfs f0, 0xC(r11)` | Load from f0, 0xC(r11). |
| `0x8268CD94` | `stfs f0, 0x150(r3)` | Store the source value to f0, 0x150(r3). |
| `0x8268CD98` | `lfs f0, 0x10(r11)` | Load from f0, 0x10(r11). |
| `0x8268CD9C` | `stfs f0, 0x154(r3)` | Store the source value to f0, 0x154(r3). |
| `0x8268CDA0` | `lwz r11, 0x14(r11)` | Load from r11, 0x14(r11). |
| `0x8268CDA4` | `stw r11, 0x15C(r3)` | Store the source value to r11, 0x15C(r3). |
| `0x8268CDA8` | `blr` | Return to the caller through LR. |
| `0x8268CDAC` | `.long 0` | Adjacent exported data/alignment word: 0. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x150/+0x154/+0x158/+0x15C` | cache next active request | current request fields |
| `+0x17C` | base | `mRequestInternalOffset` |
| `+0x181/+0x182` | increment/wrap | current/max requests |
| internal `+0x0C/+0x10/+0x14/+0x1E` | handle/rate/count/state | named fields |

#### (e) Implementation-grade C++ sketch

```cpp
void AdvanceCurrentRequest()
{
    mCurrentRequest=static_cast<u8>(mCurrentRequest+1);
    if (mCurrentRequest==mMaxRequests) mCurrentRequest=0;
    mCurrentRequestSamplesPlayed=mCurrentRequestNumSamples=0;
    RequestInternal& r=Request(mCurrentRequest);
    if (IsActive(r.state)) {
        mCurrentRequestSamplesPlayed=0; mCurrentRequestHandle=r.requestHandle;
        mCurrentRequestSampleRate=r.sampleRate; mCurrentRequestNumSamples=r.numSamples;
    }
}
```

X64 hazards: the internal record contains a widened Decoder pointer, so walk with host
`sizeof`, not rotate-by-5.  The relative base stays a checked `u16`.  No deferred return
or GetSize issue.

### `FeedCleanup` — `0x826A4258`

#### (a) Exact signature / dispatch ABI

`r3=this`; semantic `void FeedCleanup()`.  The unchanged/last value in `r3` is
incidental.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826A4258.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826A4258` | `std r31, back_chain(r1)` | Store the source value to r31, back_chain(r1). |
| `0x826A425C` | `addi r8, r3, 0x65 # 'e'` | Integer/address arithmetic: r8, r3, 0x65 # 'e'. |
| `0x826A4260` | `li r4, 0x14` | Materialize immediate/address component: r4, 0x14. |
| `0x826A4264` | `li r5, 0` | Materialize immediate/address component: r5, 0. |
| `0x826A4268` | `lbz r11, 0(r8)` | Load from r11, 0(r8). |
| `0x826A426C` | `cmplwi cr6, r11, 2` | Compare cr6, r11, 2 and update the specified condition register. |
| `0x826A4270` | `bne cr6, loc_826A4330` | Conditional branch to cr6, loc_826A4330 according to the named CR/CTR condition. |
| `0x826A4274` | `lbz r6, 1(r8)` | Load from r6, 1(r8). |
| `0x826A4278` | `lhz r9, 0x17C(r3)` | Load from r9, 0x17C(r3). |
| `0x826A427C` | `rotlwi r7, r6, 5` | Shift/rotate/mask or width-normalize: r7, r6, 5. |
| `0x826A4280` | `lbz r10, -1(r8)` | Load from r10, -1(r8). |
| `0x826A4284` | `add r11, r9, r7` | Integer/address arithmetic: r11, r9, r7. |
| `0x826A4288` | `rotlwi r9, r10, 2` | Shift/rotate/mask or width-normalize: r9, r10, 2. |
| `0x826A428C` | `add r11, r11, r3` | Integer/address arithmetic: r11, r11, r3. |
| `0x826A4290` | `add r9, r10, r9` | Integer/address arithmetic: r9, r10, r9. |
| `0x826A4294` | `slwi r9, r9, 2` | Shift/rotate/mask or width-normalize: r9, r9, 2. |
| `0x826A4298` | `lwz r11, 8(r11)` | Load from r11, 8(r11). |
| `0x826A429C` | `lwz r7, 0x24(r11)` | Load from r7, 0x24(r11). |
| `0x826A42A0` | `add r9, r9, r7` | Integer/address arithmetic: r9, r9, r7. |
| `0x826A42A4` | `add r7, r9, r11` | Integer/address arithmetic: r7, r9, r11. |
| `0x826A42A8` | `lwz r9, 0xC(r7)` | Load from r9, 0xC(r7). |
| `0x826A42AC` | `cmpwi cr6, r9, 0` | Compare cr6, r9, 0 and update the specified condition register. |
| `0x826A42B0` | `beq cr6, loc_826A42D8` | Conditional branch to cr6, loc_826A42D8 according to the named CR/CTR condition. |
| `0x826A42B4` | `lbz r31, 0x31(r11)` | Load from r31, 0x31(r11). |
| `0x826A42B8` | `cmplw cr6, r10, r31` | Compare cr6, r10, r31 and update the specified condition register. |
| `0x826A42BC` | `bne cr6, loc_826A42C8` | Conditional branch to cr6, loc_826A42C8 according to the named CR/CTR condition. |
| `0x826A42C0` | `lwz r11, 0x1C(r11)` | Load from r11, 0x1C(r11). |
| `0x826A42C4` | `b loc_826A42CC` | Branch unconditionally to loc_826A42CC. |
| `0x826A42C8` | `lwz r11, 8(r7)` | Load from r11, 8(r7). |
| `0x826A42CC` | `subf r11, r11, r9` | Integer/address arithmetic: r11, r11, r9. |
| `0x826A42D0` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A42D4` | `bne cr6, loc_826A4330` | Conditional branch to cr6, loc_826A4330 according to the named CR/CTR condition. |
| `0x826A42D8` | `stb r5, 0(r8)` | Store the source value to r5, 0(r8). |
| `0x826A42DC` | `mulli r11, r6, 0x88` | Integer/address arithmetic: r11, r6, 0x88. |
| `0x826A42E0` | `lbz r9, -9(r8)` | Load from r9, -9(r8). |
| `0x826A42E4` | `cmplwi cr6, r9, 0` | Compare cr6, r9, 0 and update the specified condition register. |
| `0x826A42E8` | `lwz r10, 0x58(r3)` | Load from r10, 0x58(r3). |
| `0x826A42EC` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826A42F0` | `beq cr6, loc_826A4330` | Conditional branch to cr6, loc_826A4330 according to the named CR/CTR condition. |
| `0x826A42F4` | `lwz r9, 0x74(r11)` | Load from r9, 0x74(r11). |
| `0x826A42F8` | `cmplwi cr6, r9, 0` | Compare cr6, r9, 0 and update the specified condition register. |
| `0x826A42FC` | `beq cr6, loc_826A432C` | Conditional branch to cr6, loc_826A432C according to the named CR/CTR condition. |
| `0x826A4300` | `lwz r10, 0x64(r11)` | Load from r10, 0x64(r11). |
| `0x826A4304` | `addi r10, r10, 1` | Integer/address arithmetic: r10, r10, 1. |
| `0x826A4308` | `cmplwi cr6, r10, 6` | Compare cr6, r10, 6 and update the specified condition register. |
| `0x826A430C` | `bne cr6, loc_826A4314` | Conditional branch to cr6, loc_826A4314 according to the named CR/CTR condition. |
| `0x826A4310` | `mr r10, r5` | Copy register value: r10, r5. |
| `0x826A4314` | `lwz r7, 0x60(r11)` | Load from r7, 0x60(r11). |
| `0x826A4318` | `cmplw cr6, r10, r7` | Compare cr6, r10, r7 and update the specified condition register. |
| `0x826A431C` | `beq cr6, loc_826A432C` | Conditional branch to cr6, loc_826A432C according to the named CR/CTR condition. |
| `0x826A4320` | `addi r9, r9, -1` | Integer/address arithmetic: r9, r9, -1. |
| `0x826A4324` | `stw r10, 0x64(r11)` | Store the source value to r10, 0x64(r11). |
| `0x826A4328` | `stw r9, 0x74(r11)` | Store the source value to r9, 0x74(r11). |
| `0x826A432C` | `stb r5, -9(r8)` | Store the source value to r5, -9(r8). |
| `0x826A4330` | `addi r4, r4, -1` | Integer/address arithmetic: r4, r4, -1. |
| `0x826A4334` | `addi r8, r8, 0xC` | Integer/address arithmetic: r8, r8, 0xC. |
| `0x826A4338` | `cmplwi cr6, r4, 0` | Compare cr6, r4, 0 and update the specified condition register. |
| `0x826A433C` | `bne cr6, loc_826A4268` | Conditional branch to cr6, loc_826A4268 according to the named CR/CTR condition. |
| `0x826A4340` | `ld r31, back_chain(r1)` | Load from r31, back_chain(r1). |
| `0x826A4344` | `blr` | Return to the caller through LR. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x58` + external `0x88*i` | request stream counters | `mpRequestExternal[i]` |
| `+0x17C` + internal `0x20*i` | decoder pointer | `Request(i).pDecoder` |
| feed `+0/+4/+8/+9/+0xA` | streamed flag, played, handle, state, request | all `FeedDesc` fields |
| Decoder `+0x1C/+0x24/+5*n` | total/current feed accounting | decoder-owned request data |
| external `+0x60/+0x64/+0x74` | write/unlock indices, locked count | chunk ring release |

#### (e) Implementation-grade C++ sketch

```cpp
void FeedCleanup()
{
    for (u32 i=0;i<20;++i) {
        FeedDesc& f=mFeedDesc[i]; if (f.feedState!=2) continue;
        RequestInternal& r=Request(f.requestIndex); Decoder* d=r.pDecoder;
        auto& dr=d->RequestAt(f.decoderRequestHandle); // decoder base +0x24, stride 20
        const s32 target=(f.decoderRequestHandle==d->mCurrentRequest)
            ? d->mCurrentSamples : dr.samples;
        if (dr.request==0 || dr.request==target) {
            f.feedState=0;
            RequestExternal& e=mpRequestExternal[f.requestIndex];
            if (f.streamed) {
                if (e.lockedChunks) {
                    u32 next=(e.unlockBufferSelect+1)%6;
                    if (next!=e.writeBufferSelect) { e.unlockBufferSelect=next; --e.lockedChunks; }
                }
                f.streamed=false;
            }
        }
    }
}
```

X64 hazards: Decoder/external pointers widen and decoder-private layout must be accessed
through its typed API; external stride becomes host `sizeof`.  Feed stride remains a
12-byte-shaped pointer-free type and count 20.  No deferred return or GetSize issue.

### `GetFeedSlot` — `0x826A4348`

#### (a) Exact signature / dispatch ABI

`r3=this`, `r4=s32* outSlot`, returns bool in `r3`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826A4348.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826A4348` | `mr r10, r3` | Copy register value: r10, r3. |
| `0x826A434C` | `lbz r11, 0x185(r10)` | Load from r11, 0x185(r10). |
| `0x826A4350` | `rotlwi r9, r11, 1` | Shift/rotate/mask or width-normalize: r9, r11, 1. |
| `0x826A4354` | `add r9, r11, r9` | Integer/address arithmetic: r9, r11, r9. |
| `0x826A4358` | `slwi r9, r9, 2` | Shift/rotate/mask or width-normalize: r9, r9, 2. |
| `0x826A435C` | `add r9, r9, r10` | Integer/address arithmetic: r9, r9, r10. |
| `0x826A4360` | `lbz r9, 0x65(r9)` | Load from r9, 0x65(r9). |
| `0x826A4364` | `cmplwi cr6, r9, 0` | Compare cr6, r9, 0 and update the specified condition register. |
| `0x826A4368` | `bne cr6, loc_826A4394` | Conditional branch to cr6, loc_826A4394 according to the named CR/CTR condition. |
| `0x826A436C` | `stw r11, 0(r4)` | Store the source value to r11, 0(r4). |
| `0x826A4370` | `lbz r11, 0x185(r10)` | Load from r11, 0x185(r10). |
| `0x826A4374` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826A4378` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826A437C` | `cmplwi cr6, r11, 0x14` | Compare cr6, r11, 0x14 and update the specified condition register. |
| `0x826A4380` | `bne cr6, loc_826A4388` | Conditional branch to cr6, loc_826A4388 according to the named CR/CTR condition. |
| `0x826A4384` | `li r11, 0` | Materialize immediate/address component: r11, 0. |
| `0x826A4388` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x826A438C` | `stb r11, 0x185(r10)` | Store the source value to r11, 0x185(r10). |
| `0x826A4390` | `blr` | Return to the caller through LR. |
| `0x826A4394` | `li r3, 0` | Materialize immediate/address component: r3, 0. |
| `0x826A4398` | `blr` | Return to the caller through LR. |
| `0x826A439C` | `.long 0` | Adjacent exported data/alignment word: 0. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x185` | read/increment/wrap at 20 | `mNextFeedSlotToFill` |
| `+0x5C + 0x0C*i + 9` | availability test | `mFeedDesc[i].feedState` |

#### (e) Implementation-grade C++ sketch

```cpp
bool GetFeedSlot(s32* out)
{
    if (mFeedDesc[mNextFeedSlotToFill].feedState) return false;
    *out=mNextFeedSlotToFill; mNextFeedSlotToFill=(mNextFeedSlotToFill+1)%20; return true;
}
```

X64 hazards: use typed feed indexing; there are exactly 20 pointer-free records.  No
deferred return, narrow pointer, or GetSize issue.

### `PlayHandler` — corrected start `0x826A43A0`

#### (a) Exact signature / dispatch ABI

Deferred command handler receives `r3=Command*`; returns the record's `u16
sizeOfCommand` in `r3` (console field `command+0x20`).  This return is the command-ring
cursor advance and is semantically mandatory.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826A43A0.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826A43A0` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826A43A4` | `bl __savegprlr_24` | Call __savegprlr_24; place the return address in LR. |
| `0x826A43A8` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826A43AC` | `mr r29, r3` | Copy register value: r29, r3. |
| `0x826A43B0` | `lwz r30, 4(r29)` | Load from r30, 4(r29). |
| `0x826A43B4` | `lfs f0, 0x24(r29)` | Load from f0, 0x24(r29). |
| `0x826A43B8` | `lbz r11, 0x17F(r30)` | Load from r11, 0x17F(r30). |
| `0x826A43BC` | `stfs f0, 0x164(r30)` | Store the source value to f0, 0x164(r30). |
| `0x826A43C0` | `lhz r10, 0x17C(r30)` | Load from r10, 0x17C(r30). |
| `0x826A43C4` | `rotlwi r9, r11, 5` | Shift/rotate/mask or width-normalize: r9, r11, 5. |
| `0x826A43C8` | `lwz r26, 4(r30)` | Load from r26, 4(r30). |
| `0x826A43CC` | `add r10, r10, r9` | Integer/address arithmetic: r10, r10, r9. |
| `0x826A43D0` | `add r28, r10, r30` | Integer/address arithmetic: r28, r10, r30. |
| `0x826A43D4` | `lbz r10, 0x1E(r28)` | Load from r10, 0x1E(r28). |
| `0x826A43D8` | `cmplwi cr6, r10, 0` | Compare cr6, r10, 0 and update the specified condition register. |
| `0x826A43DC` | `bne cr6, loc_826A4544` | Conditional branch to cr6, loc_826A4544 according to the named CR/CTR condition. |
| `0x826A43E0` | `li r27, 0` | Materialize immediate/address component: r27, 0. |
| `0x826A43E4` | `lwz r10, 0x58(r30)` | Load from r10, 0x58(r30). |
| `0x826A43E8` | `mulli r11, r11, 0x88` | Integer/address arithmetic: r11, r11, 0x88. |
| `0x826A43EC` | `lfs f0, 0x24(r29)` | Load from f0, 0x24(r29). |
| `0x826A43F0` | `stfs f0, 0xC(r28)` | Store the source value to f0, 0xC(r28). |
| `0x826A43F4` | `stw r27, 8(r28)` | Store the source value to r27, 8(r28). |
| `0x826A43F8` | `lfd f0, 8(r29)` | Load from f0, 8(r29). |
| `0x826A43FC` | `stfd f0, 0(r28)` | Store the source value to f0, 0(r28). |
| `0x826A4400` | `lfd f0, 0x10(r29)` | Load from f0, 0x10(r29). |
| `0x826A4404` | `add r31, r11, r10` | Integer/address arithmetic: r31, r11, r10. |
| `0x826A4408` | `li r24, 1` | Materialize immediate/address component: r24, 1. |
| `0x826A440C` | `mr r3, r30` | Copy register value: r3, r30. |
| `0x826A4410` | `stfd f0, 0(r31)` | Store the source value to f0, 0(r31). |
| `0x826A4414` | `lbz r11, 0x22(r29)` | Load from r11, 0x22(r29). |
| `0x826A4418` | `stb r11, 0x7B(r31)` | Store the source value to r11, 0x7B(r31). |
| `0x826A441C` | `stb r24, 0x1E(r28)` | Store the source value to r24, 0x1E(r28). |
| `0x826A4420` | `stw r27, 0x14(r31)` | Store the source value to r27, 0x14(r31). |
| `0x826A4424` | `stw r27, 0x18(r31)` | Store the source value to r27, 0x18(r31). |
| `0x826A4428` | `stw r27, 0x10(r31)` | Store the source value to r27, 0x10(r31). |
| `0x826A442C` | `stw r27, 0x1C(r31)` | Store the source value to r27, 0x1C(r31). |
| `0x826A4430` | `lfs f0, 0x24(r29)` | Load from f0, 0x24(r29). |
| `0x826A4434` | `stfs f0, 0x168(r30)` | Store the source value to f0, 0x168(r30). |
| `0x826A4438` | `lbz r4, 0x17F(r30)` | Load from r4, 0x17F(r30). |
| `0x826A443C` | `lwz r5, 0x1C(r29)` | Load from r5, 0x1C(r29). |
| `0x826A4440` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__UnpackHeader` | Call rw__audio__core__SndPlayer1_CgsStreamMod__UnpackHeader; place the return address in LR. |
| `0x826A4444` | `lbz r11, 0x79(r31)` | Load from r11, 0x79(r31). |
| `0x826A4448` | `cmplwi cr6, r11, 1` | Compare cr6, r11, 1 and update the specified condition register. |
| `0x826A444C` | `beq cr6, loc_826A4458` | Conditional branch to cr6, loc_826A4458 according to the named CR/CTR condition. |
| `0x826A4450` | `cmplwi cr6, r11, 2` | Compare cr6, r11, 2 and update the specified condition register. |
| `0x826A4454` | `bne cr6, loc_826A451C` | Conditional branch to cr6, loc_826A451C according to the named CR/CTR condition. |
| `0x826A4458` | `addi r11, r31, 0x28 # '('` | Integer/address arithmetic: r11, r31, 0x28 # '('. |
| `0x826A445C` | `stw r30, 0xB0+var_58(r1)` | Store the source value to r30, 0xB0+var_58(r1). |
| `0x826A4460` | `addi r25, r29, 0x28 # '('` | Integer/address arithmetic: r25, r29, 0x28 # '('. |
| `0x826A4464` | `stw r27, 0xB0+var_54(r1)` | Store the source value to r27, 0xB0+var_54(r1). |
| `0x826A4468` | `addi r4, r1, 0xB0+var_60` | Integer/address arithmetic: r4, r1, 0xB0+var_60. |
| `0x826A446C` | `stw r11, 0xB0+var_5C(r1)` | Store the source value to r11, 0xB0+var_5C(r1). |
| `0x826A4470` | `li r11, 0x32 # '2'` | Materialize immediate/address component: r11, 0x32 # '2'. |
| `0x826A4474` | `stw r25, 0xB0+var_60(r1)` | Store the source value to r25, 0xB0+var_60(r1). |
| `0x826A4478` | `stw r11, 0xB0+var_50(r1)` | Store the source value to r11, 0xB0+var_50(r1). |
| `0x826A447C` | `lis r11, off_82FFBA0C@ha` | Materialize immediate/address component: r11, off_82FFBA0C@ha. |
| `0x826A4480` | `lwz r3, off_82FFBA0C@l(r11)` | Load from r3, off_82FFBA0C@l(r11). |
| `0x826A4484` | `lwz r11, 0(r3)` | Load from r11, 0(r3). |
| `0x826A4488` | `lwz r11, 0(r11)` | Load from r11, 0(r11). |
| `0x826A448C` | `mtctr r11` | Load CTR from r11 for a counted loop or indirect call. |
| `0x826A4490` | `bctrl` | Call the function in CTR with the live ABI argument registers. |
| `0x826A4494` | `cmplwi cr6, r3, 0` | Compare cr6, r3, 0 and update the specified condition register. |
| `0x826A4498` | `stw r3, 0x20(r31)` | Store the source value to r3, 0x20(r31). |
| `0x826A449C` | `beq cr6, loc_826A4500` | Conditional branch to cr6, loc_826A4500 according to the named CR/CTR condition. |
| `0x826A44A0` | `lwz r11, 0x18(r28)` | Load from r11, 0x18(r28). |
| `0x826A44A4` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826A44A8` | `blt cr6, loc_826A451C` | Conditional branch to cr6, loc_826A451C according to the named CR/CTR condition. |
| `0x826A44AC` | `mr r11, r25` | Copy register value: r11, r25. |
| `0x826A44B0` | `mr r10, r11` | Copy register value: r10, r11. |
| `0x826A44B4` | `lbz r9, 0(r11)` | Load from r9, 0(r11). |
| `0x826A44B8` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826A44BC` | `cmplwi cr6, r9, 0` | Compare cr6, r9, 0 and update the specified condition register. |
| `0x826A44C0` | `bne cr6, loc_826A44B4` | Conditional branch to cr6, loc_826A44B4 according to the named CR/CTR condition. |
| `0x826A44C4` | `subf r11, r10, r11` | Integer/address arithmetic: r11, r10, r11. |
| `0x826A44C8` | `mr r3, r26` | Copy register value: r3, r26. |
| `0x826A44CC` | `addi r11, r11, -1` | Integer/address arithmetic: r11, r11, -1. |
| `0x826A44D0` | `lis r10, aSndplayer1Cgss@ha` | Materialize immediate/address component: r10, aSndplayer1Cgss@ha. |
| `0x826A44D4` | `clrlwi r11, r11, 0` | Shift/rotate/mask or width-normalize: r11, r11, 0. |
| `0x826A44D8` | `addi r5, r10, aSndplayer1Cgss@l# "SndPlayer1_CgsStreamMod StreamLoopFileN"...` | Integer/address arithmetic: r5, r10, aSndplayer1Cgss@l# "SndPlayer1_CgsStreamMod StreamLoopFileN".... |
| `0x826A44DC` | `addi r26, r11, 1` | Integer/address arithmetic: r26, r11, 1. |
| `0x826A44E0` | `li r7, 0` | Materialize immediate/address component: r7, 0. |
| `0x826A44E4` | `li r6, 0x10` | Materialize immediate/address component: r6, 0x10. |
| `0x826A44E8` | `mr r4, r26` | Copy register value: r4, r26. |
| `0x826A44EC` | `bl rw__audio__core__System__Alloc` | Call rw__audio__core__System__Alloc; place the return address in LR. |
| `0x826A44F0` | `cmplwi cr6, r3, 0` | Compare cr6, r3, 0 and update the specified condition register. |
| `0x826A44F4` | `stw r3, 0x1C(r31)` | Store the source value to r3, 0x1C(r31). |
| `0x826A44F8` | `bne cr6, loc_826A4510` | Conditional branch to cr6, loc_826A4510 according to the named CR/CTR condition. |
| `0x826A44FC` | `stw r27, 0x14(r28)` | Store the source value to r27, 0x14(r28). |
| `0x826A4500` | `stb r27, 0x1E(r28)` | Store the source value to r27, 0x1E(r28). |
| `0x826A4504` | `lhz r3, 0x20(r29)` | Load from r3, 0x20(r29). |
| `0x826A4508` | `addi r1, r1, 0xB0` | Integer/address arithmetic: r1, r1, 0xB0. |
| `0x826A450C` | `b __restgprlr_24` | Branch unconditionally to __restgprlr_24. |
| `0x826A4510` | `mr r5, r26# count  ; count` | Copy register value: r5, r26# count  ; count. |
| `0x826A4514` | `mr r4, r25# pSrc  ; pSrc` | Copy register value: r4, r25# pSrc  ; pSrc. |
| `0x826A4518` | `bl XMemCpy` | Call XMemCpy; place the return address in LR. |
| `0x826A451C` | `stb r24, 0x1E(r28)` | Store the source value to r24, 0x1E(r28). |
| `0x826A4520` | `lbz r11, 0x17F(r30)` | Load from r11, 0x17F(r30). |
| `0x826A4524` | `lbz r10, 0x182(r30)` | Load from r10, 0x182(r30). |
| `0x826A4528` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826A452C` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826A4530` | `mr r9, r11` | Copy register value: r9, r11. |
| `0x826A4534` | `cmplw cr6, r9, r10` | Compare cr6, r9, r10 and update the specified condition register. |
| `0x826A4538` | `bne cr6, loc_826A4540` | Conditional branch to cr6, loc_826A4540 according to the named CR/CTR condition. |
| `0x826A453C` | `mr r11, r27` | Copy register value: r11, r27. |
| `0x826A4540` | `stb r11, 0x17F(r30)` | Store the source value to r11, 0x17F(r30). |
| `0x826A4544` | `lhz r3, 0x20(r29)` | Load from r3, 0x20(r29). |
| `0x826A4548` | `addi r1, r1, 0xB0` | Integer/address arithmetic: r1, r1, 0xB0. |
| `0x826A454C` | `b __restgprlr_24` | Branch unconditionally to __restgprlr_24. |

#### (c) Rodata constants

| VA | file_off | Raw bytes | Decode/use |
|---:|---:|---|---|
| `0x820B0648` | `0x000B3648` | `53 6E 64 50 6C 61 79 65 72 31 5F 43 67 73 53 74 72 65 61 6D 4D 6F 64 20 53 74 72 65 61 6D 4C 6F 6F 70 46 69 6C 65 4E 61 6D 65 00` | loop-filename allocation tag |

`off_82FFBA0C` is writable provider state, not rodata.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| command `+4/+8/+0x10/+0x1C/+0x20/+0x22/+0x24/+0x28` | self/start/offset/RAM/size/expel/handle/path | `PlayCommand` |
| `+0x164/+0x168` | copy handle | last processed / last successful |
| `+0x17F/+0x182` | reserve/wrap request ring | next free/max requests |
| internal all fields | initialize queued request | `RequestInternal` |
| external `+0..+0x20/+0x7B` | initialize/open stream | `RequestExternal` |
| provider spec stack `+0..+0x10` | filename, buffer out, plugin, priorities 0/50 | `IStreamProvider::StreamSpec` |

#### (e) Implementation-grade C++ sketch

```cpp
u32 PlayHandler(Command* raw)
{
    auto* c=static_cast<PlayCommand*>(raw); auto* s=c->self;
    const u32 i=s->mNextFreeRequest; s->mLastRequestHandleProcessed=c->requestHandle;
    RequestInternal& r=s->Request(i);
    if (r.state!=FREE) return c->sizeOfCommand;
    RequestExternal& e=s->mpRequestExternal[i];
    r.requestHandle=c->requestHandle; r.pDecoder=nullptr; r.startTime=c->startTime;
    e.streamFileOffset=c->streamFileOffset; e.expelMode=c->expelMode;
    r.state=QUEUED; e.numSamplesFed=e.numBytesFed=e.gigaSamplesInRam=0;
    e.pStreamLoopFileName=nullptr; s->mLastRequestHandleSuccessfullyProcessed=c->requestHandle;
    s->UnpackHeader(i,c->pRamData);
    if (e.playType==1 || e.playType==2) {
        IStreamProvider::StreamSpec spec={c->path,&e.pStreamBuffer,s,0,50};
        e.pReadStream=spStreamProvider->DoOpenStream(spec);
        if (!e.pReadStream) { r.state=FREE; return c->sizeOfCommand; }
        if (r.loopStart>=0) {
            const u32 bytes=u32(strlen(c->path)+1);
            e.pStreamLoopFileName=static_cast<char*>(System::Alloc(
                s->mpSystemUseGetSystemAccessor,bytes,
                "SndPlayer1_CgsStreamMod StreamLoopFileName",16,nullptr));
            if (!e.pStreamLoopFileName) { r.numSamples=0; r.state=FREE; return c->sizeOfCommand; }
            memcpy(e.pStreamLoopFileName,c->path,bytes);
        }
    }
    r.state=QUEUED; s->mNextFreeRequest=(s->mNextFreeRequest+1)%s->mMaxRequests;
    return c->sizeOfCommand;
}
```

X64 hazards: command handler/self/RAM/path, System, stream provider, output buffer,
ReadStream and loop-filename pointers widen; provider spec and command fixed prefix must
be host structs.  Internal/external console strides become host `sizeof`.  The handler
return **is the ring cursor advance**; its producer and `sizeOfCommand` must use the same
host byte count.  The `u16 sizeOfCommand` is intentionally narrow and must be checked.

### `ModifyStartTimeHandler` — `0x826A4550`

#### (a) Exact signature / dispatch ABI

Deferred handler: `r3=ModifyStartTimeCommand*`; returns console `24` in `r3`, which is
the ring cursor advance.  Host code must return `sizeof(ModifyStartTimeCommand)`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826A4550.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826A4550` | `lwz r8, 4(r3)` | Load from r8, 4(r3). |
| `0x826A4554` | `li r9, 0` | Materialize immediate/address component: r9, 0. |
| `0x826A4558` | `lbz r7, 0x182(r8)` | Load from r7, 0x182(r8). |
| `0x826A455C` | `cmplwi cr6, r7, 0` | Compare cr6, r7, 0 and update the specified condition register. |
| `0x826A4560` | `beq cr6, loc_826A45DC` | Conditional branch to cr6, loc_826A45DC according to the named CR/CTR condition. |
| `0x826A4564` | `lhz r11, 0x17C(r8)` | Load from r11, 0x17C(r8). |
| `0x826A4568` | `lfs f0, 0x10(r3)` | Load from f0, 0x10(r3). |
| `0x826A456C` | `add r11, r11, r8` | Integer/address arithmetic: r11, r11, r8. |
| `0x826A4570` | `addi r11, r11, 0x1E` | Integer/address arithmetic: r11, r11, 0x1E. |
| `0x826A4574` | `lfs f13, -0x12(r11)` | Load from f13, -0x12(r11). |
| `0x826A4578` | `fcmpu cr6, f13, f0` | Compare cr6, f13, f0 and update the specified condition register. |
| `0x826A457C` | `bne cr6, loc_826A45A8` | Conditional branch to cr6, loc_826A45A8 according to the named CR/CTR condition. |
| `0x826A4580` | `lbz r10, 0(r11)` | Load from r10, 0(r11). |
| `0x826A4584` | `cmpwi cr6, r10, 4` | Compare cr6, r10, 4 and update the specified condition register. |
| `0x826A4588` | `beq cr6, loc_826A4598` | Conditional branch to cr6, loc_826A4598 according to the named CR/CTR condition. |
| `0x826A458C` | `cmpwi cr6, r10, 0` | Compare cr6, r10, 0 and update the specified condition register. |
| `0x826A4590` | `li r10, 1` | Materialize immediate/address component: r10, 1. |
| `0x826A4594` | `bne cr6, loc_826A459C` | Conditional branch to cr6, loc_826A459C according to the named CR/CTR condition. |
| `0x826A4598` | `li r10, 0` | Materialize immediate/address component: r10, 0. |
| `0x826A459C` | `clrlwi r10, r10, 24` | Shift/rotate/mask or width-normalize: r10, r10, 24. |
| `0x826A45A0` | `cmplwi cr6, r10, 0` | Compare cr6, r10, 0 and update the specified condition register. |
| `0x826A45A4` | `bne cr6, loc_826A45C0` | Conditional branch to cr6, loc_826A45C0 according to the named CR/CTR condition. |
| `0x826A45A8` | `addi r9, r9, 1` | Integer/address arithmetic: r9, r9, 1. |
| `0x826A45AC` | `addi r11, r11, 0x20 # ' '` | Integer/address arithmetic: r11, r11, 0x20 # ' '. |
| `0x826A45B0` | `cmplw cr6, r9, r7` | Compare cr6, r9, r7 and update the specified condition register. |
| `0x826A45B4` | `blt cr6, loc_826A4574` | Conditional branch to cr6, loc_826A4574 according to the named CR/CTR condition. |
| `0x826A45B8` | `li r3, 0x18` | Materialize immediate/address component: r3, 0x18. |
| `0x826A45BC` | `blr` | Return to the caller through LR. |
| `0x826A45C0` | `lwz r10, 4(r8)` | Load from r10, 4(r8). |
| `0x826A45C4` | `lfd f0, -0x1E(r11)` | Load from f0, -0x1E(r11). |
| `0x826A45C8` | `lfd f13, 8(r10)` | Load from f13, 8(r10). |
| `0x826A45CC` | `fcmpu cr6, f0, f13` | Compare cr6, f0, f13 and update the specified condition register. |
| `0x826A45D0` | `ble cr6, loc_826A45DC` | Conditional branch to cr6, loc_826A45DC according to the named CR/CTR condition. |
| `0x826A45D4` | `lfd f0, 8(r3)` | Load from f0, 8(r3). |
| `0x826A45D8` | `stfd f0, -0x1E(r11)` | Store the source value to f0, -0x1E(r11). |
| `0x826A45DC` | `li r3, 0x18` | Materialize immediate/address component: r3, 0x18. |
| `0x826A45E0` | `blr` | Return to the caller through LR. |
| `0x826A45E4` | `.long 0` | Adjacent exported data/alignment word: 0. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| command `+4/+8/+0x10` | this/new start/request handle | `ModifyStartTimeCommand` |
| System `+0x08` | lower time bound | `System::mfSystemTime` |
| `+0x17C/+0x182` | scan internal ring | request base/count |
| internal `+0/+0x0C/+0x1E` | conditionally update start | start/handle/state |

#### (e) Implementation-grade C++ sketch

```cpp
u32 ModifyStartTimeHandler(Command* raw)
{
    auto* c=static_cast<ModifyStartTimeCommand*>(raw); auto* s=c->self;
    for (u32 i=0;i<s->mMaxRequests;++i) {
        RequestInternal& r=s->Request(i);
        if (r.requestHandle==c->requestHandle && IsActive(r.state)) {
            if (r.startTime>s->mpSystemUseGetSystemAccessor->mfSystemTime) r.startTime=c->startTime;
            break;
        }
    }
    return sizeof(ModifyStartTimeCommand);
}
```

X64 hazards: handler/this pointers widen and internal stride becomes host `sizeof`.
The return **is the ring cursor advance** (console 24 is not portable).  No narrow
pointer or GetSize issue.

### `RemoveRequest` — corrected start `0x826A45E8`

#### (a) Exact signature / dispatch ABI

`r3=this`, `r4=u32 requestIndex`; semantic `void RemoveRequest(u32)`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826A45E8.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826A45E8` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826A45EC` | `bl __savegprlr_26` | Call __savegprlr_26; place the return address in LR. |
| `0x826A45F0` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826A45F4` | `mr r31, r3` | Copy register value: r31, r3. |
| `0x826A45F8` | `mr r30, r4` | Copy register value: r30, r4. |
| `0x826A45FC` | `li r27, 0` | Materialize immediate/address component: r27, 0. |
| `0x826A4600` | `slwi r8, r30, 5` | Shift/rotate/mask or width-normalize: r8, r30, 5. |
| `0x826A4604` | `mulli r10, r30, 0x88` | Integer/address arithmetic: r10, r30, 0x88. |
| `0x826A4608` | `lhz r11, 0x17C(r31)` | Load from r11, 0x17C(r31). |
| `0x826A460C` | `lwz r9, 0x58(r31)` | Load from r9, 0x58(r31). |
| `0x826A4610` | `lwz r26, 4(r31)` | Load from r26, 4(r31). |
| `0x826A4614` | `add r11, r11, r8` | Integer/address arithmetic: r11, r11, r8. |
| `0x826A4618` | `add r28, r10, r9` | Integer/address arithmetic: r28, r10, r9. |
| `0x826A461C` | `add r29, r11, r31` | Integer/address arithmetic: r29, r11, r31. |
| `0x826A4620` | `lwz r3, 8(r29)` | Load from r3, 8(r29). |
| `0x826A4624` | `cmplwi cr6, r3, 0` | Compare cr6, r3, 0 and update the specified condition register. |
| `0x826A4628` | `beq cr6, loc_826A4634` | Conditional branch to cr6, loc_826A4634 according to the named CR/CTR condition. |
| `0x826A462C` | `bl rw__audio__core__Decoder__Release` | Call rw__audio__core__Decoder__Release; place the return address in LR. |
| `0x826A4630` | `stw r27, 8(r29)` | Store the source value to r27, 8(r29). |
| `0x826A4634` | `addi r11, r31, 0x65 # 'e'` | Integer/address arithmetic: r11, r31, 0x65 # 'e'. |
| `0x826A4638` | `li r10, 0x14` | Materialize immediate/address component: r10, 0x14. |
| `0x826A463C` | `lbz r9, 1(r11)` | Load from r9, 1(r11). |
| `0x826A4640` | `cmplw cr6, r9, r30` | Compare cr6, r9, r30 and update the specified condition register. |
| `0x826A4644` | `bne cr6, loc_826A464C` | Conditional branch to cr6, loc_826A464C according to the named CR/CTR condition. |
| `0x826A4648` | `stb r27, 0(r11)` | Store the source value to r27, 0(r11). |
| `0x826A464C` | `addi r10, r10, -1` | Integer/address arithmetic: r10, r10, -1. |
| `0x826A4650` | `addi r11, r11, 0xC` | Integer/address arithmetic: r11, r11, 0xC. |
| `0x826A4654` | `cmplwi cr6, r10, 0` | Compare cr6, r10, 0 and update the specified condition register. |
| `0x826A4658` | `bne cr6, loc_826A463C` | Conditional branch to cr6, loc_826A463C according to the named CR/CTR condition. |
| `0x826A465C` | `lis r11, off_82FFBA0C@ha` | Materialize immediate/address component: r11, off_82FFBA0C@ha. |
| `0x826A4660` | `lwz r4, 0x20(r28)` | Load from r4, 0x20(r28). |
| `0x826A4664` | `lwz r3, off_82FFBA0C@l(r11)` | Load from r3, off_82FFBA0C@l(r11). |
| `0x826A4668` | `lwz r11, 0(r3)` | Load from r11, 0(r3). |
| `0x826A466C` | `lwz r11, 4(r11)` | Load from r11, 4(r11). |
| `0x826A4670` | `mtctr r11` | Load CTR from r11 for a counted loop or indirect call. |
| `0x826A4674` | `bctrl` | Call the function in CTR with the live ABI argument registers. |
| `0x826A4678` | `lwz r4, 0x1C(r28)` | Load from r4, 0x1C(r28). |
| `0x826A467C` | `cmplwi cr6, r4, 0` | Compare cr6, r4, 0 and update the specified condition register. |
| `0x826A4680` | `beq cr6, loc_826A4690` | Conditional branch to cr6, loc_826A4690 according to the named CR/CTR condition. |
| `0x826A4684` | `li r5, 0` | Materialize immediate/address component: r5, 0. |
| `0x826A4688` | `mr r3, r26` | Copy register value: r3, r26. |
| `0x826A468C` | `bl rw__audio__core__System__Free` | Call rw__audio__core__System__Free; place the return address in LR. |
| `0x826A4690` | `stb r27, 0x1E(r29)` | Store the source value to r27, 0x1E(r29). |
| `0x826A4694` | `lbz r11, 0x7B(r28)` | Load from r11, 0x7B(r28). |
| `0x826A4698` | `cmplwi cr6, r11, 1` | Compare cr6, r11, 1 and update the specified condition register. |
| `0x826A469C` | `bne cr6, loc_826A46A8` | Conditional branch to cr6, loc_826A46A8 according to the named CR/CTR condition. |
| `0x826A46A0` | `lwz r3, 8(r31)` | Load from r3, 8(r31). |
| `0x826A46A4` | `bl rw__audio__core__Voice__ExpelAfterDecay` | Call rw__audio__core__Voice__ExpelAfterDecay; place the return address in LR. |
| `0x826A46A8` | `addi r1, r1, 0x90` | Integer/address arithmetic: r1, r1, 0x90. |
| `0x826A46AC` | `b __restgprlr_26` | Branch unconditionally to __restgprlr_26. |

#### (c) Rodata constants

None. `off_82FFBA0C` is writable provider state.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x04/+0x08/+0x58/+0x17C` | System, Voice, external, internal | owning pointers/bases |
| all feed `requestIndex/feedState` | invalidate matching feeds | feed ring |
| internal `+8/+0x1E` | release Decoder; FREE | decoder/state |
| external `+0x1C/+0x20/+0x7B` | free loop name, close stream, expel mode | named fields |

#### (e) Implementation-grade C++ sketch

```cpp
void RemoveRequest(u32 i)
{
    RequestInternal& r=Request(i); RequestExternal& e=mpRequestExternal[i];
    if (r.pDecoder) { Decoder::Release(r.pDecoder); r.pDecoder=nullptr; }
    for (u32 f=0;f<20;++f) if (mFeedDesc[f].requestIndex==i) mFeedDesc[f].feedState=0;
    spStreamProvider->DoCloseStream(e.pReadStream);
    if (e.pStreamLoopFileName)
        System::Free(mpSystemUseGetSystemAccessor,e.pStreamLoopFileName,nullptr);
    r.state=FREE;
    if (e.expelMode==1) Voice::ExpelAfterDecay(mpVoice);
}
```

X64 hazards: Decoder/System/Voice/provider/ReadStream/loop-name/external pointers widen;
use host internal/external/feed indexing.  No pointer is intentionally stored narrow,
and no deferred return or GetSize issue applies.

### `RequestCleanup` — `0x826C36D8`

#### (a) Exact signature / dispatch ABI

`r3=this`; semantic `void RequestCleanup()`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826C36D8.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826C36D8` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826C36DC` | `stw r12, var_8(r1)` | Store the source value to r12, var_8(r1). |
| `0x826C36E0` | `std r31, var_10(r1)` | Store the source value to r31, var_10(r1). |
| `0x826C36E4` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826C36E8` | `mr r31, r3` | Copy register value: r31, r3. |
| `0x826C36EC` | `lbz r11, 0x180(r31)` | Load from r11, 0x180(r31). |
| `0x826C36F0` | `lhz r10, 0x17C(r31)` | Load from r10, 0x17C(r31). |
| `0x826C36F4` | `rotlwi r11, r11, 5` | Shift/rotate/mask or width-normalize: r11, r11, 5. |
| `0x826C36F8` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826C36FC` | `add r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x826C3700` | `lbz r11, 0x1E(r11)` | Load from r11, 0x1E(r11). |
| `0x826C3704` | `cmplwi cr6, r11, 4` | Compare cr6, r11, 4 and update the specified condition register. |
| `0x826C3708` | `bne cr6, loc_826C375C` | Conditional branch to cr6, loc_826C375C according to the named CR/CTR condition. |
| `0x826C370C` | `mr r3, r31` | Copy register value: r3, r31. |
| `0x826C3710` | `lbz r4, 0x180(r31)` | Load from r4, 0x180(r31). |
| `0x826C3714` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__RemoveRequest` | Call rw__audio__core__SndPlayer1_CgsStreamMod__RemoveRequest; place the return address in LR. |
| `0x826C3718` | `lbz r11, 0x180(r31)` | Load from r11, 0x180(r31). |
| `0x826C371C` | `lbz r10, 0x182(r31)` | Load from r10, 0x182(r31). |
| `0x826C3720` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826C3724` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826C3728` | `mr r9, r11` | Copy register value: r9, r11. |
| `0x826C372C` | `cmplw cr6, r9, r10` | Compare cr6, r9, r10 and update the specified condition register. |
| `0x826C3730` | `bne cr6, loc_826C3738` | Conditional branch to cr6, loc_826C3738 according to the named CR/CTR condition. |
| `0x826C3734` | `li r11, 0` | Materialize immediate/address component: r11, 0. |
| `0x826C3738` | `stb r11, 0x180(r31)` | Store the source value to r11, 0x180(r31). |
| `0x826C373C` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826C3740` | `lhz r10, 0x17C(r31)` | Load from r10, 0x17C(r31). |
| `0x826C3744` | `rotlwi r11, r11, 5` | Shift/rotate/mask or width-normalize: r11, r11, 5. |
| `0x826C3748` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826C374C` | `add r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x826C3750` | `lbz r11, 0x1E(r11)` | Load from r11, 0x1E(r11). |
| `0x826C3754` | `cmplwi cr6, r11, 4` | Compare cr6, r11, 4 and update the specified condition register. |
| `0x826C3758` | `beq cr6, loc_826C370C` | Conditional branch to cr6, loc_826C370C according to the named CR/CTR condition. |
| `0x826C375C` | `addi r1, r1, 0x60` | Integer/address arithmetic: r1, r1, 0x60. |
| `0x826C3760` | `lwz r12, var_8(r1)` | Load from r12, var_8(r1). |
| `0x826C3764` | `mtlr r12` | Restore/set LR from r12. |
| `0x826C3768` | `ld r31, var_10(r1)` | Load from r31, var_10(r1). |
| `0x826C376C` | `blr` | Return to the caller through LR. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x17C/+0x180/+0x182` | inspect/remove/advance/wrap | request base, next-to-free, max |
| internal `+0x1E` | loop while COMPLETE | state |

#### (e) Implementation-grade C++ sketch

```cpp
void RequestCleanup()
{
    while (Request(mNextRequestToFree).state==COMPLETE) {
        RemoveRequest(mNextRequestToFree);
        mNextRequestToFree=(mNextRequestToFree+1)%mMaxRequests;
    }
}
```

X64 hazards: use host internal stride; no deferred return, narrow pointer, or GetSize issue.

### `StreamLostCallback` — `0x826C3770`

#### (a) Exact signature / dispatch ABI

Callback/member lowering: `r3=void* context` which is the plugin; semantic `static void
StreamLostCallback(void*)`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826C3770.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826C3770` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826C3774` | `bl __savegprlr_28` | Call __savegprlr_28; place the return address in LR. |
| `0x826C3778` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826C377C` | `mr r31, r3` | Copy register value: r31, r3. |
| `0x826C3780` | `li r28, 0` | Materialize immediate/address component: r28, 0. |
| `0x826C3784` | `mr r29, r28` | Copy register value: r29, r28. |
| `0x826C3788` | `lbz r11, 0x182(r31)` | Load from r11, 0x182(r31). |
| `0x826C378C` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826C3790` | `beq cr6, loc_826C37D0` | Conditional branch to cr6, loc_826C37D0 according to the named CR/CTR condition. |
| `0x826C3794` | `mr r30, r28` | Copy register value: r30, r28. |
| `0x826C3798` | `lhz r11, 0x17C(r31)` | Load from r11, 0x17C(r31). |
| `0x826C379C` | `add r11, r11, r30` | Integer/address arithmetic: r11, r11, r30. |
| `0x826C37A0` | `add r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x826C37A4` | `lbz r11, 0x1E(r11)` | Load from r11, 0x1E(r11). |
| `0x826C37A8` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826C37AC` | `beq cr6, loc_826C37BC` | Conditional branch to cr6, loc_826C37BC according to the named CR/CTR condition. |
| `0x826C37B0` | `mr r4, r29` | Copy register value: r4, r29. |
| `0x826C37B4` | `mr r3, r31` | Copy register value: r3, r31. |
| `0x826C37B8` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__RemoveRequest` | Call rw__audio__core__SndPlayer1_CgsStreamMod__RemoveRequest; place the return address in LR. |
| `0x826C37BC` | `lbz r11, 0x182(r31)` | Load from r11, 0x182(r31). |
| `0x826C37C0` | `addi r29, r29, 1` | Integer/address arithmetic: r29, r29, 1. |
| `0x826C37C4` | `addi r30, r30, 0x20 # ' '` | Integer/address arithmetic: r30, r30, 0x20 # ' '. |
| `0x826C37C8` | `cmplw cr6, r29, r11` | Compare cr6, r29, r11 and update the specified condition register. |
| `0x826C37CC` | `blt cr6, loc_826C3798` | Conditional branch to cr6, loc_826C3798 according to the named CR/CTR condition. |
| `0x826C37D0` | `stb r28, 0x181(r31)` | Store the source value to r28, 0x181(r31). |
| `0x826C37D4` | `stb r28, 0x17F(r31)` | Store the source value to r28, 0x17F(r31). |
| `0x826C37D8` | `stb r28, 0x180(r31)` | Store the source value to r28, 0x180(r31). |
| `0x826C37DC` | `addi r1, r1, 0x80` | Integer/address arithmetic: r1, r1, 0x80. |
| `0x826C37E0` | `b __restgprlr_28` | Branch unconditionally to __restgprlr_28. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x17C/+0x182` | scan all requests | internal base/max |
| `+0x17F/+0x180/+0x181` | clear cursors | next free/free/current |
| internal `+0x1E` | remove any non-FREE | state |

#### (e) Implementation-grade C++ sketch

```cpp
void StreamLostCallback(void* p)
{
    auto* s=static_cast<SndPlayer1_CgsStreamMod*>(p);
    for (u32 i=0;i<s->mMaxRequests;++i) if (s->Request(i).state) s->RemoveRequest(i);
    s->mCurrentRequest=s->mNextFreeRequest=s->mNextRequestToFree=0;
}
```

X64 hazards: host internal stride and pointers inside RemoveRequest; no deferred return,
narrow pointer, or GetSize issue.

### `StopHandler` — `0x826C3898`

#### (a) Exact signature / dispatch ABI

Deferred handler: `r3=StopCommand*`; returns console `8`, the ring cursor advance.
Host code returns `sizeof(StopCommand)`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826C3898.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826C3898` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826C389C` | `bl __savegprlr_28` | Call __savegprlr_28; place the return address in LR. |
| `0x826C38A0` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826C38A4` | `lwz r31, 4(r3)` | Load from r31, 4(r3). |
| `0x826C38A8` | `li r28, 0` | Materialize immediate/address component: r28, 0. |
| `0x826C38AC` | `mr r29, r28` | Copy register value: r29, r28. |
| `0x826C38B0` | `lbz r11, 0x182(r31)` | Load from r11, 0x182(r31). |
| `0x826C38B4` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826C38B8` | `beq cr6, loc_826C38F8` | Conditional branch to cr6, loc_826C38F8 according to the named CR/CTR condition. |
| `0x826C38BC` | `mr r30, r28` | Copy register value: r30, r28. |
| `0x826C38C0` | `lhz r11, 0x17C(r31)` | Load from r11, 0x17C(r31). |
| `0x826C38C4` | `add r11, r11, r30` | Integer/address arithmetic: r11, r11, r30. |
| `0x826C38C8` | `add r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x826C38CC` | `lbz r11, 0x1E(r11)` | Load from r11, 0x1E(r11). |
| `0x826C38D0` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826C38D4` | `beq cr6, loc_826C38E4` | Conditional branch to cr6, loc_826C38E4 according to the named CR/CTR condition. |
| `0x826C38D8` | `mr r4, r29` | Copy register value: r4, r29. |
| `0x826C38DC` | `mr r3, r31` | Copy register value: r3, r31. |
| `0x826C38E0` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__RemoveRequest` | Call rw__audio__core__SndPlayer1_CgsStreamMod__RemoveRequest; place the return address in LR. |
| `0x826C38E4` | `lbz r11, 0x182(r31)` | Load from r11, 0x182(r31). |
| `0x826C38E8` | `addi r29, r29, 1` | Integer/address arithmetic: r29, r29, 1. |
| `0x826C38EC` | `addi r30, r30, 0x20 # ' '` | Integer/address arithmetic: r30, r30, 0x20 # ' '. |
| `0x826C38F0` | `cmplw cr6, r29, r11` | Compare cr6, r29, r11 and update the specified condition register. |
| `0x826C38F4` | `blt cr6, loc_826C38C0` | Conditional branch to cr6, loc_826C38C0 according to the named CR/CTR condition. |
| `0x826C38F8` | `li r11, 0x10` | Materialize immediate/address component: r11, 0x10. |
| `0x826C38FC` | `stb r28, 0x181(r31)` | Store the source value to r28, 0x181(r31). |
| `0x826C3900` | `stb r28, 0x17F(r31)` | Store the source value to r28, 0x17F(r31). |
| `0x826C3904` | `li r3, 8` | Materialize immediate/address component: r3, 8. |
| `0x826C3908` | `stb r28, 0x180(r31)` | Store the source value to r28, 0x180(r31). |
| `0x826C390C` | `stw r28, 0x158(r31)` | Store the source value to r28, 0x158(r31). |
| `0x826C3910` | `stw r28, 0x15C(r31)` | Store the source value to r28, 0x15C(r31). |
| `0x826C3914` | `stb r28, 0x185(r31)` | Store the source value to r28, 0x185(r31). |
| `0x826C3918` | `stb r28, 0x186(r31)` | Store the source value to r28, 0x186(r31). |
| `0x826C391C` | `stb r11, 0x184(r31)` | Store the source value to r11, 0x184(r31). |
| `0x826C3920` | `addi r1, r1, 0x80` | Integer/address arithmetic: r1, r1, 0x80. |
| `0x826C3924` | `b __restgprlr_28` | Branch unconditionally to __restgprlr_28. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| command `+4` | load target | `StopCommand::self` |
| `+0x158/+0x15C` | zero progress/length | current request cache |
| `+0x17F/+0x180/+0x181` | zero request cursors | request ring |
| `+0x184` | set 16 | `mNumDeclickSamples` |
| `+0x185/+0x186` | zero feed cursors | feed ring |

#### (e) Implementation-grade C++ sketch

```cpp
u32 StopHandler(Command* raw)
{
    auto* s=static_cast<StopCommand*>(raw)->self;
    for (u32 i=0;i<s->mMaxRequests;++i) if (s->Request(i).state) s->RemoveRequest(i);
    s->mCurrentRequest=s->mNextFreeRequest=s->mNextRequestToFree=0;
    s->mCurrentRequestSamplesPlayed=s->mCurrentRequestNumSamples=0;
    s->mNextFeedSlotToFill=s->mNextFeedSlotToFree=0; s->mNumDeclickSamples=16;
    return sizeof(StopCommand);
}
```

X64 hazards: command pointers widen and request indexing uses host stride.  The return
**is the ring cursor advance**; console 8 must become host `sizeof`.  No narrow pointer
or GetSize issue.

### `SubmitChunk` — corrected start `0x826C3928`

#### (a) Exact signature / dispatch ABI

`r3=this`, `r4=u8* chunk`, `r5=u32 requestIndex`, `r6=bool resetDecoder`; returns
`chunk + big_endian_u32(chunk+0)` in `r3`.  `Decoder::Feed` is called at the supplied
approximate `0x826C39E8` with `r3=decoder`, `r4=chunk+8`, `r5=big_endian_u32(chunk+4)`,
`r6=!resetDecoder`, `r7/r8/r9=0`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826C3928.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826C3928` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826C392C` | `bl __savegprlr_24` | Call __savegprlr_24; place the return address in LR. |
| `0x826C3930` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826C3934` | `mr r31, r4` | Copy register value: r31, r4. |
| `0x826C3938` | `lwz r10, 0x58(r3)` | Load from r10, 0x58(r3). |
| `0x826C393C` | `mulli r11, r5, 0x88` | Integer/address arithmetic: r11, r5, 0x88. |
| `0x826C3940` | `add r29, r11, r10` | Integer/address arithmetic: r29, r11, r10. |
| `0x826C3944` | `lbz r10, 0(r31)` | Load from r10, 0(r31). |
| `0x826C3948` | `slwi r30, r5, 5` | Shift/rotate/mask or width-normalize: r30, r5, 5. |
| `0x826C394C` | `lhz r11, 0x17C(r3)` | Load from r11, 0x17C(r3). |
| `0x826C3950` | `mr r25, r5` | Copy register value: r25, r5. |
| `0x826C3954` | `lbz r5, 4(r31)` | Load from r5, 4(r31). |
| `0x826C3958` | `li r27, 1` | Materialize immediate/address component: r27, 1. |
| `0x826C395C` | `li r26, 0` | Materialize immediate/address component: r26, 0. |
| `0x826C3960` | `li r9, 0` | Materialize immediate/address component: r9, 0. |
| `0x826C3964` | `stb r10, 0xB0+var_58(r1)` | Store the source value to r10, 0xB0+var_58(r1). |
| `0x826C3968` | `li r8, 0` | Materialize immediate/address component: r8, 0. |
| `0x826C396C` | `lbz r10, 1(r31)` | Load from r10, 1(r31). |
| `0x826C3970` | `li r7, 0` | Materialize immediate/address component: r7, 0. |
| `0x826C3974` | `stb r5, 0xB0+var_60(r1)` | Store the source value to r5, 0xB0+var_60(r1). |
| `0x826C3978` | `addi r4, r31, 8` | Integer/address arithmetic: r4, r31, 8. |
| `0x826C397C` | `lbz r5, 5(r31)` | Load from r5, 5(r31). |
| `0x826C3980` | `stb r10, 0xB0+var_58+1(r1)` | Store the source value to r10, 0xB0+var_58+1(r1). |
| `0x826C3984` | `lbz r10, 2(r31)` | Load from r10, 2(r31). |
| `0x826C3988` | `stb r5, 0xB0+var_60+1(r1)` | Store the source value to r5, 0xB0+var_60+1(r1). |
| `0x826C398C` | `stb r10, 0xB0+var_58+2(r1)` | Store the source value to r10, 0xB0+var_58+2(r1). |
| `0x826C3990` | `lbz r10, 3(r31)` | Load from r10, 3(r31). |
| `0x826C3994` | `stb r10, 0xB0+var_58+3(r1)` | Store the source value to r10, 0xB0+var_58+3(r1). |
| `0x826C3998` | `add r10, r11, r3` | Integer/address arithmetic: r10, r11, r3. |
| `0x826C399C` | `clrlwi r11, r6, 24` | Shift/rotate/mask or width-normalize: r11, r6, 24. |
| `0x826C39A0` | `add r24, r30, r10` | Integer/address arithmetic: r24, r30, r10. |
| `0x826C39A4` | `lbz r10, 6(r31)` | Load from r10, 6(r31). |
| `0x826C39A8` | `cntlzw r11, r11` | Shift/rotate/mask or width-normalize: r11, r11. |
| `0x826C39AC` | `extrwi r6, r11, 1,26` | Execute the exact PPC operation shown: r6, r11, 1,26. |
| `0x826C39B0` | `lbz r11, 0x7A(r29)` | Load from r11, 0x7A(r29). |
| `0x826C39B4` | `stb r10, 0xB0+var_60+2(r1)` | Store the source value to r10, 0xB0+var_60+2(r1). |
| `0x826C39B8` | `lbz r10, 7(r31)` | Load from r10, 7(r31). |
| `0x826C39BC` | `stb r10, 0xB0+var_60+3(r1)` | Store the source value to r10, 0xB0+var_60+3(r1). |
| `0x826C39C0` | `rotlwi r10, r11, 1` | Shift/rotate/mask or width-normalize: r10, r11, 1. |
| `0x826C39C4` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826C39C8` | `slwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826C39CC` | `add r30, r11, r3` | Integer/address arithmetic: r30, r11, r3. |
| `0x826C39D0` | `stb r27, 0x65(r30)` | Store the source value to r27, 0x65(r30). |
| `0x826C39D4` | `stw r26, 0x60(r30)` | Store the source value to r26, 0x60(r30). |
| `0x826C39D8` | `stb r25, 0x66(r30)` | Store the source value to r25, 0x66(r30). |
| `0x826C39DC` | `lwz r3, 8(r24)` | Load from r3, 8(r24). |
| `0x826C39E0` | `lwz r28, 0xB0+var_60(r1)` | Load from r28, 0xB0+var_60(r1). |
| `0x826C39E4` | `mr r5, r28` | Copy register value: r5, r28. |
| `0x826C39E8` | `bl rw__audio__core__Decoder__Feed` | Call rw__audio__core__Decoder__Feed; place the return address in LR. |
| `0x826C39EC` | `mr r10, r3` | Copy register value: r10, r3. |
| `0x826C39F0` | `lwz r11, 0xB0+var_58(r1)` | Load from r11, 0xB0+var_58(r1). |
| `0x826C39F4` | `add r3, r11, r31` | Integer/address arithmetic: r3, r11, r31. |
| `0x826C39F8` | `stb r10, 0x64(r30)` | Store the source value to r10, 0x64(r30). |
| `0x826C39FC` | `lwz r11, 0x14(r29)` | Load from r11, 0x14(r29). |
| `0x826C3A00` | `add r11, r11, r28` | Integer/address arithmetic: r11, r11, r28. |
| `0x826C3A04` | `stw r11, 0x14(r29)` | Store the source value to r11, 0x14(r29). |
| `0x826C3A08` | `addi r1, r1, 0xB0` | Integer/address arithmetic: r1, r1, 0xB0. |
| `0x826C3A0C` | `b __restgprlr_24` | Branch unconditionally to __restgprlr_24. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| external `+0x14/+0x7A` | add chunk samples/latest slot | `numSamplesFed/latestFeedSlot` |
| `+0x17C` + internal `+8` | decoder | request decoder |
| feed `+4/+8/+9/+0xA` | clear played, store handle/state/request | `FeedDesc` |
| chunk `+0/+4/+8` | next byte distance/sample count/payload | big-endian chunk record |

#### (e) Implementation-grade C++ sketch

```cpp
u8* SubmitChunk(u8* chunk,u32 requestIndex,bool resetDecoder)
{
    const u32 next=ReadBE32(chunk); const u32 samples=ReadBE32(chunk+4);
    RequestExternal& e=mpRequestExternal[requestIndex];
    FeedDesc& f=mFeedDesc[e.latestFeedSlot];
    f.feedState=1; f.chunkSamplesPlayed=0; f.requestIndex=static_cast<u8>(requestIndex);
    f.decoderRequestHandle=Decoder::Feed(Request(requestIndex).pDecoder,
        chunk+8,samples,!resetDecoder,0,0,0);
    e.numSamplesFed+=samples;
    return chunk+next;
}
```

X64 hazards: decoder/chunk pointers widen; external/internal/feed records use host typed
strides.  `decoderRequestHandle` and `requestIndex` are intentionally `u8`, not narrow
pointers.  The chunk's first two words remain big-endian file data.  No deferred return
or GetSize issue.

### `StreamNextChunk` — `0x826DB8C8`

#### (a) Exact signature / dispatch ABI

`r3=this`, `r4=u32 requestIndex`, `r5=bool resetDecoder`; returns bool in `r3`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826DB8C8.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826DB8C8` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826DB8CC` | `stw r12, var_8(r1)` | Store the source value to r12, var_8(r1). |
| `0x826DB8D0` | `std r30, var_18(r1)` | Store the source value to r30, var_18(r1). |
| `0x826DB8D4` | `std r31, var_10(r1)` | Store the source value to r31, var_10(r1). |
| `0x826DB8D8` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826DB8DC` | `mr r8, r3` | Copy register value: r8, r3. |
| `0x826DB8E0` | `mr r7, r4` | Copy register value: r7, r4. |
| `0x826DB8E4` | `mr r6, r5` | Copy register value: r6, r5. |
| `0x826DB8E8` | `slwi r4, r7, 5` | Shift/rotate/mask or width-normalize: r4, r7, 5. |
| `0x826DB8EC` | `mulli r10, r7, 0x88` | Integer/address arithmetic: r10, r7, 0x88. |
| `0x826DB8F0` | `lhz r11, 0x17C(r8)` | Load from r11, 0x17C(r8). |
| `0x826DB8F4` | `lwz r9, 0x58(r8)` | Load from r9, 0x58(r8). |
| `0x826DB8F8` | `add r11, r11, r4` | Integer/address arithmetic: r11, r11, r4. |
| `0x826DB8FC` | `add r31, r10, r9` | Integer/address arithmetic: r31, r10, r9. |
| `0x826DB900` | `add r11, r11, r8` | Integer/address arithmetic: r11, r11, r8. |
| `0x826DB904` | `lbz r11, 0x1E(r11)` | Load from r11, 0x1E(r11). |
| `0x826DB908` | `cmplwi cr6, r11, 1` | Compare cr6, r11, 1 and update the specified condition register. |
| `0x826DB90C` | `bne cr6, loc_826DB928` | Conditional branch to cr6, loc_826DB928 according to the named CR/CTR condition. |
| `0x826DB910` | `lwz r11, 0x20(r31)` | Load from r11, 0x20(r31). |
| `0x826DB914` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DB918` | `beq cr6, loc_826DB9E8` | Conditional branch to cr6, loc_826DB9E8 according to the named CR/CTR condition. |
| `0x826DB91C` | `lwz r11, 0(r11)` | Load from r11, 0(r11). |
| `0x826DB920` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DB924` | `beq cr6, loc_826DB9E8` | Conditional branch to cr6, loc_826DB9E8 according to the named CR/CTR condition. |
| `0x826DB928` | `lwz r11, 0x70(r31)` | Load from r11, 0x70(r31). |
| `0x826DB92C` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DB930` | `beq cr6, loc_826DB9E8` | Conditional branch to cr6, loc_826DB9E8 according to the named CR/CTR condition. |
| `0x826DB934` | `lbz r11, 0x185(r8)` | Load from r11, 0x185(r8). |
| `0x826DB938` | `rotlwi r10, r11, 1` | Shift/rotate/mask or width-normalize: r10, r11, 1. |
| `0x826DB93C` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826DB940` | `slwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826DB944` | `add r11, r11, r8` | Integer/address arithmetic: r11, r11, r8. |
| `0x826DB948` | `lbz r11, 0x65(r11)` | Load from r11, 0x65(r11). |
| `0x826DB94C` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DB950` | `bne cr6, loc_826DB9E8` | Conditional branch to cr6, loc_826DB9E8 according to the named CR/CTR condition. |
| `0x826DB954` | `addi r4, r1, 0x70+var_20` | Integer/address arithmetic: r4, r1, 0x70+var_20. |
| `0x826DB958` | `mr r3, r8` | Copy register value: r3, r8. |
| `0x826DB95C` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__GetFeedSlot` | Call rw__audio__core__SndPlayer1_CgsStreamMod__GetFeedSlot; place the return address in LR. |
| `0x826DB960` | `clrlwi r11, r3, 24` | Shift/rotate/mask or width-normalize: r11, r3, 24. |
| `0x826DB964` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DB968` | `beq cr6, loc_826DB9E8` | Conditional branch to cr6, loc_826DB9E8 according to the named CR/CTR condition. |
| `0x826DB96C` | `lwz r9, 0x18(r31)` | Load from r9, 0x18(r31). |
| `0x826DB970` | `li r30, 1` | Materialize immediate/address component: r30, 1. |
| `0x826DB974` | `lwz r10, 0x68(r31)` | Load from r10, 0x68(r31). |
| `0x826DB978` | `mr r5, r7` | Copy register value: r5, r7. |
| `0x826DB97C` | `lwz r11, 0x70+var_20(r1)` | Load from r11, 0x70+var_20(r1). |
| `0x826DB980` | `mr r3, r8` | Copy register value: r3, r8. |
| `0x826DB984` | `add r10, r10, r9` | Integer/address arithmetic: r10, r10, r9. |
| `0x826DB988` | `stb r11, 0x7A(r31)` | Store the source value to r11, 0x7A(r31). |
| `0x826DB98C` | `stw r10, 0x18(r31)` | Store the source value to r10, 0x18(r31). |
| `0x826DB990` | `slwi r10, r11, 1` | Shift/rotate/mask or width-normalize: r10, r11, 1. |
| `0x826DB994` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826DB998` | `slwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826DB99C` | `add r11, r11, r8` | Integer/address arithmetic: r11, r11, r8. |
| `0x826DB9A0` | `stb r30, 0x5C(r11)` | Store the source value to r30, 0x5C(r11). |
| `0x826DB9A4` | `lwz r11, 0x5C(r31)` | Load from r11, 0x5C(r31). |
| `0x826DB9A8` | `addi r11, r11, 6` | Integer/address arithmetic: r11, r11, 6. |
| `0x826DB9AC` | `slwi r11, r11, 3` | Shift/rotate/mask or width-normalize: r11, r11, 3. |
| `0x826DB9B0` | `lwzx r4, r11, r31` | Load from r4, r11, r31. |
| `0x826DB9B4` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__SubmitChunk` | Call rw__audio__core__SndPlayer1_CgsStreamMod__SubmitChunk; place the return address in LR. |
| `0x826DB9B8` | `lwz r11, 0x5C(r31)` | Load from r11, 0x5C(r31). |
| `0x826DB9BC` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826DB9C0` | `cmplwi cr6, r11, 6` | Compare cr6, r11, 6 and update the specified condition register. |
| `0x826DB9C4` | `stw r11, 0x5C(r31)` | Store the source value to r11, 0x5C(r31). |
| `0x826DB9C8` | `bne cr6, loc_826DB9D4` | Conditional branch to cr6, loc_826DB9D4 according to the named CR/CTR condition. |
| `0x826DB9CC` | `li r11, 0` | Materialize immediate/address component: r11, 0. |
| `0x826DB9D0` | `stw r11, 0x5C(r31)` | Store the source value to r11, 0x5C(r31). |
| `0x826DB9D4` | `lwz r11, 0x70(r31)` | Load from r11, 0x70(r31). |
| `0x826DB9D8` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x826DB9DC` | `addi r11, r11, -1` | Integer/address arithmetic: r11, r11, -1. |
| `0x826DB9E0` | `stw r11, 0x70(r31)` | Store the source value to r11, 0x70(r31). |
| `0x826DB9E4` | `b loc_826DB9EC` | Branch unconditionally to loc_826DB9EC. |
| `0x826DB9E8` | `li r3, 0` | Materialize immediate/address component: r3, 0. |
| `0x826DB9EC` | `addi r1, r1, 0x70` | Integer/address arithmetic: r1, r1, 0x70. |
| `0x826DB9F0` | `lwz r12, var_8(r1)` | Load from r12, var_8(r1). |
| `0x826DB9F4` | `mtlr r12` | Restore/set LR from r12. |
| `0x826DB9F8` | `ld r30, var_18(r1)` | Load from r30, var_18(r1). |
| `0x826DB9FC` | `ld r31, var_10(r1)` | Load from r31, var_10(r1). |
| `0x826DBA00` | `blr` | Return to the caller through LR. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x185` / feed `+9` | require/reserve free feed | fill cursor/feed state |
| internal `+0x1E` | QUEUED stream readiness check | state |
| external `+0x18/+0x5C/+0x68/+0x70/+0x7A` | bytes, read selector/size/queued/latest feed | stream ring |
| external chunks `+0x2C + 8*i` | selected chunk pointer | `chunks[readBufferSelect]` |

#### (e) Implementation-grade C++ sketch

```cpp
bool StreamNextChunk(u32 i,bool reset)
{
    RequestInternal& r=Request(i); RequestExternal& e=mpRequestExternal[i];
    if (r.state==QUEUED && (!e.pReadStream || !e.pReadStream->mDeviceStream)) return false;
    if (!e.queuedChunks || mFeedDesc[mNextFeedSlotToFill].feedState) return false;
    s32 slot; if (!GetFeedSlot(&slot)) return false;
    e.latestFeedSlot=static_cast<u8>(slot); e.numBytesFed+=e.readSize;
    mFeedDesc[slot].streamed=true;
    SubmitChunk(e.chunks[e.readBufferSelect].buf,i,reset);
    e.readBufferSelect=(e.readBufferSelect+1)%6; --e.queuedChunks; return true;
}
```

X64 hazards: read-stream/chunk pointers widen; use host external/chunk/feed strides.
Feed index remains `u8`.  No deferred return or GetSize issue.

### `HandleLoopStart` — `0x826DBA08`

#### (a) Exact signature / dispatch ABI

`r3=this`, `r4=u32 requestIndex`; returns bool in `r3`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826DBA08.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826DBA08` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826DBA0C` | `stw r12, var_8(r1)` | Store the source value to r12, var_8(r1). |
| `0x826DBA10` | `std r31, var_10(r1)` | Store the source value to r31, var_10(r1). |
| `0x826DBA14` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826DBA18` | `mr r8, r3` | Copy register value: r8, r3. |
| `0x826DBA1C` | `mr r7, r4` | Copy register value: r7, r4. |
| `0x826DBA20` | `mulli r11, r7, 0x88` | Integer/address arithmetic: r11, r7, 0x88. |
| `0x826DBA24` | `lwz r10, 0x58(r8)` | Load from r10, 0x58(r8). |
| `0x826DBA28` | `add r31, r11, r10` | Integer/address arithmetic: r31, r11, r10. |
| `0x826DBA2C` | `lhz r11, 0x17C(r8)` | Load from r11, 0x17C(r8). |
| `0x826DBA30` | `slwi r10, r7, 5` | Shift/rotate/mask or width-normalize: r10, r7, 5. |
| `0x826DBA34` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826DBA38` | `add r10, r11, r8` | Integer/address arithmetic: r10, r11, r8. |
| `0x826DBA3C` | `lbz r11, 0x79(r31)` | Load from r11, 0x79(r31). |
| `0x826DBA40` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DBA44` | `bne cr6, loc_826DBA94` | Conditional branch to cr6, loc_826DBA94 according to the named CR/CTR condition. |
| `0x826DBA48` | `lwz r11, 0x7C(r31)` | Load from r11, 0x7C(r31). |
| `0x826DBA4C` | `stw r11, 0x80(r31)` | Store the source value to r11, 0x80(r31). |
| `0x826DBA50` | `lbz r10, 0x185(r8)` | Load from r10, 0x185(r8). |
| `0x826DBA54` | `mr r11, r10` | Copy register value: r11, r10. |
| `0x826DBA58` | `slwi r9, r11, 1` | Shift/rotate/mask or width-normalize: r9, r11, 1. |
| `0x826DBA5C` | `add r9, r11, r9` | Integer/address arithmetic: r9, r11, r9. |
| `0x826DBA60` | `slwi r9, r9, 2` | Shift/rotate/mask or width-normalize: r9, r9, 2. |
| `0x826DBA64` | `add r9, r9, r8` | Integer/address arithmetic: r9, r9, r8. |
| `0x826DBA68` | `lbz r9, 0x65(r9)` | Load from r9, 0x65(r9). |
| `0x826DBA6C` | `cmplwi cr6, r9, 0` | Compare cr6, r9, 0 and update the specified condition register. |
| `0x826DBA70` | `bne cr6, loc_826DBAF0` | Conditional branch to cr6, loc_826DBAF0 according to the named CR/CTR condition. |
| `0x826DBA74` | `clrlwi r10, r10, 24` | Shift/rotate/mask or width-normalize: r10, r10, 24. |
| `0x826DBA78` | `addi r10, r10, 1` | Integer/address arithmetic: r10, r10, 1. |
| `0x826DBA7C` | `clrlwi r10, r10, 24` | Shift/rotate/mask or width-normalize: r10, r10, 24. |
| `0x826DBA80` | `cmplwi cr6, r10, 0x14` | Compare cr6, r10, 0x14 and update the specified condition register. |
| `0x826DBA84` | `bne cr6, loc_826DBA8C` | Conditional branch to cr6, loc_826DBA8C according to the named CR/CTR condition. |
| `0x826DBA88` | `li r10, 0` | Materialize immediate/address component: r10, 0. |
| `0x826DBA8C` | `stb r10, 0x185(r8)` | Store the source value to r10, 0x185(r8). |
| `0x826DBA90` | `b loc_826DBAF4` | Branch unconditionally to loc_826DBAF4. |
| `0x826DBA94` | `cmplwi cr6, r11, 1` | Compare cr6, r11, 1 and update the specified condition register. |
| `0x826DBA98` | `mr r3, r8` | Copy register value: r3, r8. |
| `0x826DBA9C` | `bne cr6, loc_826DBAD0` | Conditional branch to cr6, loc_826DBAD0 according to the named CR/CTR condition. |
| `0x826DBAA0` | `li r5, 1` | Materialize immediate/address component: r5, 1. |
| `0x826DBAA4` | `mr r4, r7` | Copy register value: r4, r7. |
| `0x826DBAA8` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__StreamNextChunk` | Call rw__audio__core__SndPlayer1_CgsStreamMod__StreamNextChunk; place the return address in LR. |
| `0x826DBAAC` | `clrlwi r11, r3, 24` | Shift/rotate/mask or width-normalize: r11, r3, 24. |
| `0x826DBAB0` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DBAB4` | `bne cr6, loc_826DBB30` | Conditional branch to cr6, loc_826DBB30 according to the named CR/CTR condition. |
| `0x826DBAB8` | `li r3, 0` | Materialize immediate/address component: r3, 0. |
| `0x826DBABC` | `addi r1, r1, 0x70` | Integer/address arithmetic: r1, r1, 0x70. |
| `0x826DBAC0` | `lwz r12, var_8(r1)` | Load from r12, var_8(r1). |
| `0x826DBAC4` | `mtlr r12` | Restore/set LR from r12. |
| `0x826DBAC8` | `ld r31, var_10(r1)` | Load from r31, var_10(r1). |
| `0x826DBACC` | `blr` | Return to the caller through LR. |
| `0x826DBAD0` | `lwz r11, 0x18(r10)` | Load from r11, 0x18(r10). |
| `0x826DBAD4` | `lwz r10, 0x10(r31)` | Load from r10, 0x10(r31). |
| `0x826DBAD8` | `cmpw cr6, r11, r10` | Compare cr6, r11, r10 and update the specified condition register. |
| `0x826DBADC` | `bge cr6, loc_826DBB14` | Conditional branch to cr6, loc_826DBB14 according to the named CR/CTR condition. |
| `0x826DBAE0` | `lwz r11, 0x7C(r31)` | Load from r11, 0x7C(r31). |
| `0x826DBAE4` | `addi r4, r1, 0x70+var_20` | Integer/address arithmetic: r4, r1, 0x70+var_20. |
| `0x826DBAE8` | `stw r11, 0x80(r31)` | Store the source value to r11, 0x80(r31). |
| `0x826DBAEC` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__GetFeedSlot` | Call rw__audio__core__SndPlayer1_CgsStreamMod__GetFeedSlot; place the return address in LR. |
| `0x826DBAF0` | `lwz r11, 0x70+var_20(r1)` | Load from r11, 0x70+var_20(r1). |
| `0x826DBAF4` | `li r6, 1` | Materialize immediate/address component: r6, 1. |
| `0x826DBAF8` | `lwz r4, 0x7C(r31)` | Load from r4, 0x7C(r31). |
| `0x826DBAFC` | `mr r5, r7` | Copy register value: r5, r7. |
| `0x826DBB00` | `stb r11, 0x7A(r31)` | Store the source value to r11, 0x7A(r31). |
| `0x826DBB04` | `mr r3, r8` | Copy register value: r3, r8. |
| `0x826DBB08` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__SubmitChunk` | Call rw__audio__core__SndPlayer1_CgsStreamMod__SubmitChunk; place the return address in LR. |
| `0x826DBB0C` | `stw r3, 0x7C(r31)` | Store the source value to r3, 0x7C(r31). |
| `0x826DBB10` | `b loc_826DBB30` | Branch unconditionally to loc_826DBB30. |
| `0x826DBB14` | `li r5, 1` | Materialize immediate/address component: r5, 1. |
| `0x826DBB18` | `mr r4, r7` | Copy register value: r4, r7. |
| `0x826DBB1C` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__StreamNextChunk` | Call rw__audio__core__SndPlayer1_CgsStreamMod__StreamNextChunk; place the return address in LR. |
| `0x826DBB20` | `clrlwi r11, r3, 24` | Shift/rotate/mask or width-normalize: r11, r3, 24. |
| `0x826DBB24` | `li r3, 0` | Materialize immediate/address component: r3, 0. |
| `0x826DBB28` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DBB2C` | `beq cr6, loc_826DBB34` | Conditional branch to cr6, loc_826DBB34 according to the named CR/CTR condition. |
| `0x826DBB30` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x826DBB34` | `addi r1, r1, 0x70` | Integer/address arithmetic: r1, r1, 0x70. |
| `0x826DBB38` | `lwz r12, var_8(r1)` | Load from r12, var_8(r1). |
| `0x826DBB3C` | `mtlr r12` | Restore/set LR from r12. |
| `0x826DBB40` | `ld r31, var_10(r1)` | Load from r31, var_10(r1). |
| `0x826DBB44` | `blr` | Return to the caller through LR. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| internal `+0x18` | compare loop start | `loopStart` |
| external `+0x10/+0x79/+0x7A/+0x7C/+0x80` | RAM split/play type/feed/next/loop pointers | loop source state |
| `+0x185`, feed `+9` | inline reserve or GetFeedSlot | feed producer |

#### (e) Implementation-grade C++ sketch

```cpp
bool HandleLoopStart(u32 i)
{
    RequestInternal& r=Request(i); RequestExternal& e=mpRequestExternal[i];
    if (e.playType==0) {
        e.pLoopStartChunk=e.pNextChunk; s32 slot; GetFeedSlot(&slot);
        e.latestFeedSlot=static_cast<u8>(slot);
        e.pNextChunk=SubmitChunk(e.pNextChunk,i,true); return true;
    }
    if (e.playType==1) return StreamNextChunk(i,true);
    if (r.loopStart>=e.gigaSamplesInRam) return StreamNextChunk(i,true);
    e.pLoopStartChunk=e.pNextChunk; s32 slot; GetFeedSlot(&slot);
    e.latestFeedSlot=static_cast<u8>(slot);
    e.pNextChunk=SubmitChunk(e.pNextChunk,i,true); return true;
}
```

X64 hazards: next/loop/chunk pointers widen and record strides become host `sizeof`.
Feed slot remains an integer.  No deferred return or GetSize issue.

### `HandleSampleEnd` — `0x826DBB48`

#### (a) Exact signature / dispatch ABI

`r3=this`, `r4=u32 requestIndex`, `r5=bool* requestCompleted`; returns bool in `r3`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826DBB48.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826DBB48` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826DBB4C` | `bl __savegprlr_28` | Call __savegprlr_28; place the return address in LR. |
| `0x826DBB50` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826DBB54` | `mr r30, r3` | Copy register value: r30, r3. |
| `0x826DBB58` | `mr r28, r4` | Copy register value: r28, r4. |
| `0x826DBB5C` | `slwi r8, r28, 5` | Shift/rotate/mask or width-normalize: r8, r28, 5. |
| `0x826DBB60` | `mulli r10, r28, 0x88` | Integer/address arithmetic: r10, r28, 0x88. |
| `0x826DBB64` | `lhz r11, 0x17C(r30)` | Load from r11, 0x17C(r30). |
| `0x826DBB68` | `lwz r9, 0x58(r30)` | Load from r9, 0x58(r30). |
| `0x826DBB6C` | `add r11, r11, r8` | Integer/address arithmetic: r11, r11, r8. |
| `0x826DBB70` | `add r31, r10, r9` | Integer/address arithmetic: r31, r10, r9. |
| `0x826DBB74` | `add r29, r11, r30` | Integer/address arithmetic: r29, r11, r30. |
| `0x826DBB78` | `lwz r11, 0x18(r29)` | Load from r11, 0x18(r29). |
| `0x826DBB7C` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DBB80` | `blt cr6, loc_826DBD28` | Conditional branch to cr6, loc_826DBD28 according to the named CR/CTR condition. |
| `0x826DBB84` | `li r11, 0` | Materialize immediate/address component: r11, 0. |
| `0x826DBB88` | `stb r11, 0(r5)` | Store the source value to r11, 0(r5). |
| `0x826DBB8C` | `lbz r11, 0x79(r31)` | Load from r11, 0x79(r31). |
| `0x826DBB90` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DBB94` | `bne cr6, loc_826DBBEC` | Conditional branch to cr6, loc_826DBBEC according to the named CR/CTR condition. |
| `0x826DBB98` | `lwz r11, 0x18(r29)` | Load from r11, 0x18(r29). |
| `0x826DBB9C` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DBBA0` | `bne cr6, loc_826DBBAC` | Conditional branch to cr6, loc_826DBBAC according to the named CR/CTR condition. |
| `0x826DBBA4` | `lwz r11, 8(r31)` | Load from r11, 8(r31). |
| `0x826DBBA8` | `stw r11, 0x80(r31)` | Store the source value to r11, 0x80(r31). |
| `0x826DBBAC` | `addi r4, r1, 0x80+var_30` | Integer/address arithmetic: r4, r1, 0x80+var_30. |
| `0x826DBBB0` | `mr r3, r30` | Copy register value: r3, r30. |
| `0x826DBBB4` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__GetFeedSlot` | Call rw__audio__core__SndPlayer1_CgsStreamMod__GetFeedSlot; place the return address in LR. |
| `0x826DBBB8` | `lwz r11, 0x80+var_30(r1)` | Load from r11, 0x80+var_30(r1). |
| `0x826DBBBC` | `li r6, 1` | Materialize immediate/address component: r6, 1. |
| `0x826DBBC0` | `lwz r4, 0x80(r31)` | Load from r4, 0x80(r31). |
| `0x826DBBC4` | `mr r5, r28` | Copy register value: r5, r28. |
| `0x826DBBC8` | `mr r3, r30` | Copy register value: r3, r30. |
| `0x826DBBCC` | `stb r11, 0x7A(r31)` | Store the source value to r11, 0x7A(r31). |
| `0x826DBBD0` | `lwz r11, 0x18(r29)` | Load from r11, 0x18(r29). |
| `0x826DBBD4` | `stw r11, 0x14(r31)` | Store the source value to r11, 0x14(r31). |
| `0x826DBBD8` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__SubmitChunk` | Call rw__audio__core__SndPlayer1_CgsStreamMod__SubmitChunk; place the return address in LR. |
| `0x826DBBDC` | `stw r3, 0x7C(r31)` | Store the source value to r3, 0x7C(r31). |
| `0x826DBBE0` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x826DBBE4` | `addi r1, r1, 0x80` | Integer/address arithmetic: r1, r1, 0x80. |
| `0x826DBBE8` | `b __restgprlr_28` | Branch unconditionally to __restgprlr_28. |
| `0x826DBBEC` | `cmplwi cr6, r11, 1` | Compare cr6, r11, 1 and update the specified condition register. |
| `0x826DBBF0` | `bne cr6, loc_826DBC4C` | Conditional branch to cr6, loc_826DBC4C according to the named CR/CTR condition. |
| `0x826DBBF4` | `lwz r10, 0x20(r31)` | Load from r10, 0x20(r31). |
| `0x826DBBF8` | `lfd f0, 0(r31)` | Load from f0, 0(r31). |
| `0x826DBBFC` | `lwz r11, 0xC(r31)` | Load from r11, 0xC(r31). |
| `0x826DBC00` | `fctidz f0, f0` | Execute the exact PPC operation shown: f0, f0. |
| `0x826DBC04` | `stfd f0, 0x80+var_30(r1)` | Store the source value to f0, 0x80+var_30(r1). |
| `0x826DBC08` | `extsw r11, r11` | Shift/rotate/mask or width-normalize: r11, r11. |
| `0x826DBC0C` | `lwz r3, 0(r10)` | Load from r3, 0(r10). |
| `0x826DBC10` | `ld r10, 0x80+var_30(r1)` | Load from r10, 0x80+var_30(r1). |
| `0x826DBC14` | `add r4, r11, r10` | Integer/address arithmetic: r4, r11, r10. |
| `0x826DBC18` | `bl CgsFileSystem__StreamDeviceDiskRead__Seek` | Call CgsFileSystem__StreamDeviceDiskRead__Seek; place the return address in LR. |
| `0x826DBC1C` | `lwz r11, 0x18(r29)` | Load from r11, 0x18(r29). |
| `0x826DBC20` | `li r5, 1` | Materialize immediate/address component: r5, 1. |
| `0x826DBC24` | `mr r4, r28` | Copy register value: r4, r28. |
| `0x826DBC28` | `mr r3, r30` | Copy register value: r3, r30. |
| `0x826DBC2C` | `stw r11, 0x14(r31)` | Store the source value to r11, 0x14(r31). |
| `0x826DBC30` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__StreamNextChunk` | Call rw__audio__core__SndPlayer1_CgsStreamMod__StreamNextChunk; place the return address in LR. |
| `0x826DBC34` | `clrlwi r11, r3, 24` | Shift/rotate/mask or width-normalize: r11, r3, 24. |
| `0x826DBC38` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DBC3C` | `bne cr6, loc_826DBD30` | Conditional branch to cr6, loc_826DBD30 according to the named CR/CTR condition. |
| `0x826DBC40` | `li r3, 0` | Materialize immediate/address component: r3, 0. |
| `0x826DBC44` | `addi r1, r1, 0x80` | Integer/address arithmetic: r1, r1, 0x80. |
| `0x826DBC48` | `b __restgprlr_28` | Branch unconditionally to __restgprlr_28. |
| `0x826DBC4C` | `lwz r11, 0x18(r29)` | Load from r11, 0x18(r29). |
| `0x826DBC50` | `lwz r10, 0x10(r31)` | Load from r10, 0x10(r31). |
| `0x826DBC54` | `stw r11, 0x14(r31)` | Store the source value to r11, 0x14(r31). |
| `0x826DBC58` | `lwz r11, 0x18(r29)` | Load from r11, 0x18(r29). |
| `0x826DBC5C` | `cmpw cr6, r11, r10` | Compare cr6, r11, r10 and update the specified condition register. |
| `0x826DBC60` | `bge cr6, loc_826DBCA4` | Conditional branch to cr6, loc_826DBCA4 according to the named CR/CTR condition. |
| `0x826DBC64` | `clrlwi r11, r11, 0` | Shift/rotate/mask or width-normalize: r11, r11, 0. |
| `0x826DBC68` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DBC6C` | `bne cr6, loc_826DBC78` | Conditional branch to cr6, loc_826DBC78 according to the named CR/CTR condition. |
| `0x826DBC70` | `lwz r11, 8(r31)` | Load from r11, 8(r31). |
| `0x826DBC74` | `stw r11, 0x80(r31)` | Store the source value to r11, 0x80(r31). |
| `0x826DBC78` | `addi r4, r1, 0x80+var_30` | Integer/address arithmetic: r4, r1, 0x80+var_30. |
| `0x826DBC7C` | `mr r3, r30` | Copy register value: r3, r30. |
| `0x826DBC80` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__GetFeedSlot` | Call rw__audio__core__SndPlayer1_CgsStreamMod__GetFeedSlot; place the return address in LR. |
| `0x826DBC84` | `lwz r11, 0x80+var_30(r1)` | Load from r11, 0x80+var_30(r1). |
| `0x826DBC88` | `li r6, 1` | Materialize immediate/address component: r6, 1. |
| `0x826DBC8C` | `lwz r4, 0x80(r31)` | Load from r4, 0x80(r31). |
| `0x826DBC90` | `mr r5, r28` | Copy register value: r5, r28. |
| `0x826DBC94` | `mr r3, r30` | Copy register value: r3, r30. |
| `0x826DBC98` | `stb r11, 0x7A(r31)` | Store the source value to r11, 0x7A(r31). |
| `0x826DBC9C` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__SubmitChunk` | Call rw__audio__core__SndPlayer1_CgsStreamMod__SubmitChunk; place the return address in LR. |
| `0x826DBCA0` | `stw r3, 0x7C(r31)` | Store the source value to r3, 0x7C(r31). |
| `0x826DBCA4` | `lwz r10, 0x10(r31)` | Load from r10, 0x10(r31). |
| `0x826DBCA8` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826DBCAC` | `lwz r9, 0x14(r29)` | Load from r9, 0x14(r29). |
| `0x826DBCB0` | `cmpw cr6, r10, r9` | Compare cr6, r10, r9 and update the specified condition register. |
| `0x826DBCB4` | `blt cr6, loc_826DBCBC` | Conditional branch to cr6, loc_826DBCBC according to the named CR/CTR condition. |
| `0x826DBCB8` | `li r11, 0` | Materialize immediate/address component: r11, 0. |
| `0x826DBCBC` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826DBCC0` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DBCC4` | `beq cr6, loc_826DBD30` | Conditional branch to cr6, loc_826DBD30 according to the named CR/CTR condition. |
| `0x826DBCC8` | `lwz r10, 0x20(r31)` | Load from r10, 0x20(r31). |
| `0x826DBCCC` | `lfd f0, 0(r31)` | Load from f0, 0(r31). |
| `0x826DBCD0` | `lwz r11, 0xC(r31)` | Load from r11, 0xC(r31). |
| `0x826DBCD4` | `fctidz f0, f0` | Execute the exact PPC operation shown: f0, f0. |
| `0x826DBCD8` | `stfd f0, 0x80+var_30(r1)` | Store the source value to f0, 0x80+var_30(r1). |
| `0x826DBCDC` | `extsw r11, r11` | Shift/rotate/mask or width-normalize: r11, r11. |
| `0x826DBCE0` | `lwz r3, 0(r10)` | Load from r3, 0(r10). |
| `0x826DBCE4` | `ld r10, 0x80+var_30(r1)` | Load from r10, 0x80+var_30(r1). |
| `0x826DBCE8` | `add r4, r11, r10` | Integer/address arithmetic: r4, r11, r10. |
| `0x826DBCEC` | `bl CgsFileSystem__StreamDeviceDiskRead__Seek` | Call CgsFileSystem__StreamDeviceDiskRead__Seek; place the return address in LR. |
| `0x826DBCF0` | `lwz r11, 0x18(r29)` | Load from r11, 0x18(r29). |
| `0x826DBCF4` | `lwz r10, 0x10(r31)` | Load from r10, 0x10(r31). |
| `0x826DBCF8` | `cmpw cr6, r11, r10` | Compare cr6, r11, r10 and update the specified condition register. |
| `0x826DBCFC` | `blt cr6, loc_826DBD30` | Conditional branch to cr6, loc_826DBD30 according to the named CR/CTR condition. |
| `0x826DBD00` | `li r5, 1` | Materialize immediate/address component: r5, 1. |
| `0x826DBD04` | `mr r4, r28` | Copy register value: r4, r28. |
| `0x826DBD08` | `mr r3, r30` | Copy register value: r3, r30. |
| `0x826DBD0C` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__StreamNextChunk` | Call rw__audio__core__SndPlayer1_CgsStreamMod__StreamNextChunk; place the return address in LR. |
| `0x826DBD10` | `clrlwi r11, r3, 24` | Shift/rotate/mask or width-normalize: r11, r3, 24. |
| `0x826DBD14` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DBD18` | `bne cr6, loc_826DBD30` | Conditional branch to cr6, loc_826DBD30 according to the named CR/CTR condition. |
| `0x826DBD1C` | `li r3, 0` | Materialize immediate/address component: r3, 0. |
| `0x826DBD20` | `addi r1, r1, 0x80` | Integer/address arithmetic: r1, r1, 0x80. |
| `0x826DBD24` | `b __restgprlr_28` | Branch unconditionally to __restgprlr_28. |
| `0x826DBD28` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826DBD2C` | `stb r11, 0(r5)` | Store the source value to r11, 0(r5). |
| `0x826DBD30` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x826DBD34` | `addi r1, r1, 0x80` | Integer/address arithmetic: r1, r1, 0x80. |
| `0x826DBD38` | `b __restgprlr_28` | Branch unconditionally to __restgprlr_28. |

#### (c) Rodata constants

None.

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| internal `+0x14/+0x18` | length/loop start | sample endpoints |
| external `+0/+8/+0x0C/+0x10/+0x14/+0x20/+0x79/+0x7A/+0x7C/+0x80` | all loop/seek/feed state | named external fields |
| `+0x185`, feed `+9` | reserve feed | feed ring |

#### (e) Implementation-grade C++ sketch

```cpp
bool HandleSampleEnd(u32 i,bool* completed)
{
    RequestInternal& r=Request(i); RequestExternal& e=mpRequestExternal[i];
    if (r.loopStart<0) { *completed=true; return true; }
    *completed=false;
    if (e.playType==0) {
        if (r.loopStart==0) e.pLoopStartChunk=e.pSampleData;
        s32 slot; GetFeedSlot(&slot); e.latestFeedSlot=static_cast<u8>(slot);
        e.numSamplesFed=r.loopStart;
        e.pNextChunk=SubmitChunk(e.pLoopStartChunk,i,true); return true;
    }
    if (e.playType==1) {
        e.pReadStream->Seek(static_cast<s64>(e.streamFileOffset)+e.loopStartStreamOffset);
        e.numSamplesFed=r.loopStart; return StreamNextChunk(i,true);
    }
    e.numSamplesFed=r.loopStart;
    if (r.loopStart<e.gigaSamplesInRam) {
        if (r.loopStart==0) e.pLoopStartChunk=e.pSampleData;
        s32 slot; GetFeedSlot(&slot); e.latestFeedSlot=static_cast<u8>(slot);
        e.pNextChunk=SubmitChunk(e.pLoopStartChunk,i,true);
    }
    if (e.gigaSamplesInRam<r.numSamples) {
        e.pReadStream->Seek(static_cast<s64>(e.streamFileOffset)+e.loopStartStreamOffset);
        if (r.loopStart>=e.gigaSamplesInRam && !StreamNextChunk(i,true)) return false;
    }
    return true;
}
```

X64 hazards: stream/sample/chunk pointers widen; external/internal/feed strides become
host `sizeof`.  The stream file offset remains double and is explicitly converted to
the seek integer as the assembly does.  No deferred return, narrow pointer, or GetSize issue.

### `StartRequest` — corrected start `0x826DBD40`

#### (a) Exact signature / dispatch ABI

`r3=this`, `r4=u32 requestIndex`; returns bool in `r3`.  Corrected xref chain:
`RwacTimerClient 0x826EA3B8 -> StartRequest 0x826DBD40`; the supplied
`0x826DBD78` is the first call (`System::Lock`) inside it.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826DBD40.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826DBD40` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826DBD44` | `bl __savegprlr_26` | Call __savegprlr_26; place the return address in LR. |
| `0x826DBD48` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826DBD4C` | `mr r31, r3` | Copy register value: r31, r3. |
| `0x826DBD50` | `mr r28, r4` | Copy register value: r28, r4. |
| `0x826DBD54` | `slwi r8, r28, 5` | Shift/rotate/mask or width-normalize: r8, r28, 5. |
| `0x826DBD58` | `mulli r10, r28, 0x88` | Integer/address arithmetic: r10, r28, 0x88. |
| `0x826DBD5C` | `lhz r11, 0x17C(r31)` | Load from r11, 0x17C(r31). |
| `0x826DBD60` | `lwz r26, 4(r31)` | Load from r26, 4(r31). |
| `0x826DBD64` | `lwz r9, 0x58(r31)` | Load from r9, 0x58(r31). |
| `0x826DBD68` | `add r11, r11, r8` | Integer/address arithmetic: r11, r11, r8. |
| `0x826DBD6C` | `mr r3, r26` | Copy register value: r3, r26. |
| `0x826DBD70` | `add r27, r10, r9` | Integer/address arithmetic: r27, r10, r9. |
| `0x826DBD74` | `add r30, r11, r31` | Integer/address arithmetic: r30, r11, r31. |
| `0x826DBD78` | `bl rw__audio__core__System__Lock` | Call rw__audio__core__System__Lock; place the return address in LR. |
| `0x826DBD7C` | `lwz r3, 4(r31)` | Load from r3, 4(r31). |
| `0x826DBD80` | `bl rw__audio__core__System__GetDecoderRegistry` | Call rw__audio__core__System__GetDecoderRegistry; place the return address in LR. |
| `0x826DBD84` | `lbz r11, 0x78(r27)` | Load from r11, 0x78(r27). |
| `0x826DBD88` | `lis r10, dword_820AA7C4@ha` | Materialize immediate/address component: r10, dword_820AA7C4@ha. |
| `0x826DBD8C` | `rotlwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826DBD90` | `addi r10, r10, dword_820AA7C4@l` | Integer/address arithmetic: r10, r10, dword_820AA7C4@l. |
| `0x826DBD94` | `mr r29, r3` | Copy register value: r29, r3. |
| `0x826DBD98` | `lwzx r4, r11, r10` | Load from r4, r11, r10. |
| `0x826DBD9C` | `bl rw__audio__core__DecoderRegistry__GetDecoderHandle` | Call rw__audio__core__DecoderRegistry__GetDecoderHandle; place the return address in LR. |
| `0x826DBDA0` | `mr r4, r3` | Copy register value: r4, r3. |
| `0x826DBDA4` | `lwz r7, 4(r31)` | Load from r7, 4(r31). |
| `0x826DBDA8` | `li r6, 0x14` | Materialize immediate/address component: r6, 0x14. |
| `0x826DBDAC` | `lbz r5, 0x1F(r30)` | Load from r5, 0x1F(r30). |
| `0x826DBDB0` | `mr r3, r29` | Copy register value: r3, r29. |
| `0x826DBDB4` | `bl rw__audio__core__DecoderRegistry__DecoderFactory` | Call rw__audio__core__DecoderRegistry__DecoderFactory; place the return address in LR. |
| `0x826DBDB8` | `cmplwi cr6, r3, 0` | Compare cr6, r3, 0 and update the specified condition register. |
| `0x826DBDBC` | `stw r3, 8(r30)` | Store the source value to r3, 8(r30). |
| `0x826DBDC0` | `beq cr6, loc_826DBE14` | Conditional branch to cr6, loc_826DBE14 according to the named CR/CTR condition. |
| `0x826DBDC4` | `lwz r11, 0x20(r3)` | Load from r11, 0x20(r3). |
| `0x826DBDC8` | `sth r11, 0x1C(r30)` | Store the source value to r11, 0x1C(r30). |
| `0x826DBDCC` | `lbz r11, 0x79(r27)` | Load from r11, 0x79(r27). |
| `0x826DBDD0` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DBDD4` | `beq cr6, loc_826DBE28` | Conditional branch to cr6, loc_826DBE28 according to the named CR/CTR condition. |
| `0x826DBDD8` | `cmplwi cr6, r11, 2` | Compare cr6, r11, 2 and update the specified condition register. |
| `0x826DBDDC` | `beq cr6, loc_826DBE28` | Conditional branch to cr6, loc_826DBE28 according to the named CR/CTR condition. |
| `0x826DBDE0` | `li r5, 1` | Materialize immediate/address component: r5, 1. |
| `0x826DBDE4` | `mr r4, r28` | Copy register value: r4, r28. |
| `0x826DBDE8` | `mr r3, r31` | Copy register value: r3, r31. |
| `0x826DBDEC` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__StreamNextChunk` | Call rw__audio__core__SndPlayer1_CgsStreamMod__StreamNextChunk; place the return address in LR. |
| `0x826DBDF0` | `clrlwi r11, r3, 24` | Shift/rotate/mask or width-normalize: r11, r3, 24. |
| `0x826DBDF4` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826DBDF8` | `bne cr6, loc_826DBE8C` | Conditional branch to cr6, loc_826DBE8C according to the named CR/CTR condition. |
| `0x826DBDFC` | `lwz r3, 8(r30)` | Load from r3, 8(r30). |
| `0x826DBE00` | `cmplwi cr6, r3, 0` | Compare cr6, r3, 0 and update the specified condition register. |
| `0x826DBE04` | `beq cr6, loc_826DBE14` | Conditional branch to cr6, loc_826DBE14 according to the named CR/CTR condition. |
| `0x826DBE08` | `bl rw__audio__core__Decoder__Release` | Call rw__audio__core__Decoder__Release; place the return address in LR. |
| `0x826DBE0C` | `li r11, 0` | Materialize immediate/address component: r11, 0. |
| `0x826DBE10` | `stw r11, 8(r30)` | Store the source value to r11, 8(r30). |
| `0x826DBE14` | `mr r3, r26` | Copy register value: r3, r26. |
| `0x826DBE18` | `bl rw__audio__core__System__Unlock` | Call rw__audio__core__System__Unlock; place the return address in LR. |
| `0x826DBE1C` | `li r3, 0` | Materialize immediate/address component: r3, 0. |
| `0x826DBE20` | `addi r1, r1, 0x90` | Integer/address arithmetic: r1, r1, 0x90. |
| `0x826DBE24` | `b __restgprlr_26` | Branch unconditionally to __restgprlr_26. |
| `0x826DBE28` | `lbz r10, 0x185(r31)` | Load from r10, 0x185(r31). |
| `0x826DBE2C` | `mr r11, r10` | Copy register value: r11, r10. |
| `0x826DBE30` | `slwi r9, r11, 1` | Shift/rotate/mask or width-normalize: r9, r11, 1. |
| `0x826DBE34` | `add r9, r11, r9` | Integer/address arithmetic: r9, r11, r9. |
| `0x826DBE38` | `slwi r9, r9, 2` | Shift/rotate/mask or width-normalize: r9, r9, 2. |
| `0x826DBE3C` | `add r9, r9, r31` | Integer/address arithmetic: r9, r9, r31. |
| `0x826DBE40` | `lbz r9, 0x65(r9)` | Load from r9, 0x65(r9). |
| `0x826DBE44` | `cmplwi cr6, r9, 0` | Compare cr6, r9, 0 and update the specified condition register. |
| `0x826DBE48` | `bne cr6, loc_826DBE6C` | Conditional branch to cr6, loc_826DBE6C according to the named CR/CTR condition. |
| `0x826DBE4C` | `clrlwi r10, r10, 24` | Shift/rotate/mask or width-normalize: r10, r10, 24. |
| `0x826DBE50` | `addi r10, r10, 1` | Integer/address arithmetic: r10, r10, 1. |
| `0x826DBE54` | `clrlwi r10, r10, 24` | Shift/rotate/mask or width-normalize: r10, r10, 24. |
| `0x826DBE58` | `cmplwi cr6, r10, 0x14` | Compare cr6, r10, 0x14 and update the specified condition register. |
| `0x826DBE5C` | `bne cr6, loc_826DBE64` | Conditional branch to cr6, loc_826DBE64 according to the named CR/CTR condition. |
| `0x826DBE60` | `li r10, 0` | Materialize immediate/address component: r10, 0. |
| `0x826DBE64` | `stb r10, 0x185(r31)` | Store the source value to r10, 0x185(r31). |
| `0x826DBE68` | `b loc_826DBE70` | Branch unconditionally to loc_826DBE70. |
| `0x826DBE6C` | `lwz r11, 0x90+var_40(r1)` | Load from r11, 0x90+var_40(r1). |
| `0x826DBE70` | `li r6, 1` | Materialize immediate/address component: r6, 1. |
| `0x826DBE74` | `lwz r4, 8(r27)` | Load from r4, 8(r27). |
| `0x826DBE78` | `mr r5, r28` | Copy register value: r5, r28. |
| `0x826DBE7C` | `stb r11, 0x7A(r27)` | Store the source value to r11, 0x7A(r27). |
| `0x826DBE80` | `mr r3, r31` | Copy register value: r3, r31. |
| `0x826DBE84` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__SubmitChunk` | Call rw__audio__core__SndPlayer1_CgsStreamMod__SubmitChunk; place the return address in LR. |
| `0x826DBE88` | `stw r3, 0x7C(r27)` | Store the source value to r3, 0x7C(r27). |
| `0x826DBE8C` | `mr r3, r26` | Copy register value: r3, r26. |
| `0x826DBE90` | `bl rw__audio__core__System__Unlock` | Call rw__audio__core__System__Unlock; place the return address in LR. |
| `0x826DBE94` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x826DBE98` | `addi r1, r1, 0x90` | Integer/address arithmetic: r1, r1, 0x90. |
| `0x826DBE9C` | `b __restgprlr_26` | Branch unconditionally to __restgprlr_26. |

#### (c) Rodata constants

| VA | file_off | Raw bytes | Decode/use |
|---:|---:|---|---|
| `0x820AA7C4` | `0x000AD7C4` | `58 61 73 30 45 4C 33 30 50 36 42 30 45 58 6D 30 58 61 73 31 45 4C 33 31` | six decoder GUIDs: `Xas0`, `EL30`, `P6B0`, `EXm0`, `Xas1`, `EL31` |

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| `+0x04/+0x58/+0x17C` | System/external/internal | core object links |
| internal `+8/+0x1C/+0x1F` | decoder/store instance size/channels | request decoder state |
| external `+8/+0x78/+0x79/+0x7A/+0x7C` | sample data/codec/type/feed/next | feed source |
| `+0x185`, feed `+9` | reserve first feed | feed ring |

#### (e) Implementation-grade C++ sketch

```cpp
bool StartRequest(u32 i)
{
    System* sys=mpSystemUseGetSystemAccessor; RequestInternal& r=Request(i);
    RequestExternal& e=mpRequestExternal[i]; System::Lock(sys);
    DecoderRegistry* reg=System::GetDecoderRegistry(sys);
    void* handle=reg->GetDecoderHandle(kDecoderGuids[e.codec]);
    r.pDecoder=reg->DecoderFactory(handle,r.numChannels,20,sys);
    if (!r.pDecoder) { System::Unlock(sys); return false; }
    r.decoderInstanceSize=static_cast<u16>(r.pDecoder->mInstanceSize);
    bool ok=true;
    if (e.playType==0 || e.playType==2) {
        s32 slot; GetFeedSlot(&slot); e.latestFeedSlot=static_cast<u8>(slot);
        e.pNextChunk=SubmitChunk(e.pSampleData,i,true);
    } else ok=StreamNextChunk(i,true);
    if (!ok) { Decoder::Release(r.pDecoder); r.pDecoder=nullptr; }
    System::Unlock(sys); return ok;
}
```

X64 hazards: System/registry/decoder/sample/chunk pointers widen and host record strides
apply.  `decoderInstanceSize` is intentionally `u16` and must be range-checked;
decoder/feed handles remain scalar.  No deferred return or GetSize issue.

### `RwacTimerClient` — `0x826E9EF8`

#### (a) Exact signature / dispatch ABI

Timer callback: `r3=void* context` (plugin), `f1=float timeToNextCall` (unused).
DecFIGS signature is `static void RwacTimerClient(void*, float)`; the assembly return
register is incidental.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826E9EF8.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826E9EF8` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826E9EFC` | `bl __savegprlr_14` | Call __savegprlr_14; place the return address in LR. |
| `0x826E9F00` | `stfd f30, var_A8(r1)` | Store the source value to f30, var_A8(r1). |
| `0x826E9F04` | `stfd f31, var_A0(r1)` | Store the source value to f31, var_A0(r1). |
| `0x826E9F08` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826E9F0C` | `mr r30, r3` | Copy register value: r30, r3. |
| `0x826E9F10` | `lwz r11, 8(r30)` | Load from r11, 8(r30). |
| `0x826E9F14` | `lbz r11, 0x47(r11)` | Load from r11, 0x47(r11). |
| `0x826E9F18` | `cmplwi cr6, r11, 2` | Compare cr6, r11, 2 and update the specified condition register. |
| `0x826E9F1C` | `beq cr6, loc_826EA458` | Conditional branch to cr6, loc_826EA458 according to the named CR/CTR condition. |
| `0x826E9F20` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__FeedCleanup` | Call rw__audio__core__SndPlayer1_CgsStreamMod__FeedCleanup; place the return address in LR. |
| `0x826E9F24` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__RequestCleanup` | Call rw__audio__core__SndPlayer1_CgsStreamMod__RequestCleanup; place the return address in LR. |
| `0x826E9F28` | `lbz r11, 0x181(r30)` | Load from r11, 0x181(r30). |
| `0x826E9F2C` | `lhz r8, 0x17C(r30)` | Load from r8, 0x17C(r30). |
| `0x826E9F30` | `mr r10, r11` | Copy register value: r10, r11. |
| `0x826E9F34` | `lwz r9, 0x58(r30)` | Load from r9, 0x58(r30). |
| `0x826E9F38` | `mr r14, r11` | Copy register value: r14, r11. |
| `0x826E9F3C` | `slwi r11, r10, 5` | Shift/rotate/mask or width-normalize: r11, r10, 5. |
| `0x826E9F40` | `mulli r10, r10, 0x88` | Integer/address arithmetic: r10, r10, 0x88. |
| `0x826E9F44` | `add r11, r11, r8` | Integer/address arithmetic: r11, r11, r8. |
| `0x826E9F48` | `add r31, r10, r9` | Integer/address arithmetic: r31, r10, r9. |
| `0x826E9F4C` | `add r17, r11, r30` | Integer/address arithmetic: r17, r11, r30. |
| `0x826E9F50` | `lbz r11, 0x1E(r17)` | Load from r11, 0x1E(r17). |
| `0x826E9F54` | `cmpwi cr6, r11, 4` | Compare cr6, r11, 4 and update the specified condition register. |
| `0x826E9F58` | `beq cr6, loc_826E9F68` | Conditional branch to cr6, loc_826E9F68 according to the named CR/CTR condition. |
| `0x826E9F5C` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826E9F60` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826E9F64` | `bne cr6, loc_826E9F6C` | Conditional branch to cr6, loc_826E9F6C according to the named CR/CTR condition. |
| `0x826E9F68` | `li r11, 0` | Materialize immediate/address component: r11, 0. |
| `0x826E9F6C` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826E9F70` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826E9F74` | `bne cr6, loc_826E9F98` | Conditional branch to cr6, loc_826E9F98 according to the named CR/CTR condition. |
| `0x826E9F78` | `lis r11, dbl_82001CA8@ha` | Materialize immediate/address component: r11, dbl_82001CA8@ha. |
| `0x826E9F7C` | `lfd f0, dbl_82001CA8@l(r11)` | Load from f0, dbl_82001CA8@l(r11). |
| `0x826E9F80` | `stfd f0, 0x38(r30)` | Store the source value to f0, 0x38(r30). |
| `0x826E9F84` | `stfd f0, 0x30(r30)` | Store the source value to f0, 0x30(r30). |
| `0x826E9F88` | `addi r1, r1, 0x110` | Integer/address arithmetic: r1, r1, 0x110. |
| `0x826E9F8C` | `lfd f30, var_A8(r1)` | Load from f30, var_A8(r1). |
| `0x826E9F90` | `lfd f31, var_A0(r1)` | Load from f31, var_A0(r1). |
| `0x826E9F94` | `b __restgprlr` | Branch unconditionally to __restgprlr. |
| `0x826E9F98` | `lwz r11, 0x15C(r30)` | Load from r11, 0x15C(r30). |
| `0x826E9F9C` | `lfs f13, 0x150(r30)` | Load from f13, 0x150(r30). |
| `0x826E9FA0` | `lwz r10, 0x158(r30)` | Load from r10, 0x158(r30). |
| `0x826E9FA4` | `stfs f13, 0x28(r30)` | Store the source value to f13, 0x28(r30). |
| `0x826E9FA8` | `extsw r11, r11` | Shift/rotate/mask or width-normalize: r11, r11. |
| `0x826E9FAC` | `lfs f0, 0x154(r30)` | Load from f0, 0x154(r30). |
| `0x826E9FB0` | `extsw r10, r10` | Shift/rotate/mask or width-normalize: r10, r10. |
| `0x826E9FB4` | `std r11, 0x110+var_B8(r1)` | Store the source value to r11, 0x110+var_B8(r1). |
| `0x826E9FB8` | `std r10, 0x110+var_B0(r1)` | Store the source value to r10, 0x110+var_B0(r1). |
| `0x826E9FBC` | `lfd f13, 0x110+var_B8(r1)` | Load from f13, 0x110+var_B8(r1). |
| `0x826E9FC0` | `lfd f12, 0x110+var_B0(r1)` | Load from f12, 0x110+var_B0(r1). |
| `0x826E9FC4` | `fcfid f13, f13` | Floating-point arithmetic/select/conversion: f13, f13. |
| `0x826E9FC8` | `fcfid f12, f12` | Floating-point arithmetic/select/conversion: f12, f12. |
| `0x826E9FCC` | `fdiv f13, f13, f0` | Floating-point arithmetic/select/conversion: f13, f13, f0. |
| `0x826E9FD0` | `stfd f13, 0x38(r30)` | Store the source value to f13, 0x38(r30). |
| `0x826E9FD4` | `fdiv f0, f12, f0` | Floating-point arithmetic/select/conversion: f0, f12, f0. |
| `0x826E9FD8` | `stfd f0, 0x30(r30)` | Store the source value to f0, 0x30(r30). |
| `0x826E9FDC` | `lwz r11, 0x14(r17)` | Load from r11, 0x14(r17). |
| `0x826E9FE0` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826E9FE4` | `bne cr6, loc_826EA04C` | Conditional branch to cr6, loc_826EA04C according to the named CR/CTR condition. |
| `0x826E9FE8` | `lbz r10, 0x182(r30)` | Load from r10, 0x182(r30). |
| `0x826E9FEC` | `clrlwi r11, r14, 24` | Shift/rotate/mask or width-normalize: r11, r14, 24. |
| `0x826E9FF0` | `li r14, 0` | Materialize immediate/address component: r14, 0. |
| `0x826E9FF4` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826E9FF8` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826E9FFC` | `mr r9, r11` | Copy register value: r9, r11. |
| `0x826EA000` | `cmplw cr6, r9, r10` | Compare cr6, r9, r10 and update the specified condition register. |
| `0x826EA004` | `beq cr6, loc_826EA00C` | Conditional branch to cr6, loc_826EA00C according to the named CR/CTR condition. |
| `0x826EA008` | `mr r14, r11` | Copy register value: r14, r11. |
| `0x826EA00C` | `clrlslwi r11, r14, 24,5` | Execute the exact PPC operation shown: r11, r14, 24,5. |
| `0x826EA010` | `add r11, r11, r8` | Integer/address arithmetic: r11, r11, r8. |
| `0x826EA014` | `add r17, r11, r30` | Integer/address arithmetic: r17, r11, r30. |
| `0x826EA018` | `lbz r11, 0x1E(r17)` | Load from r11, 0x1E(r17). |
| `0x826EA01C` | `cmpwi cr6, r11, 4` | Compare cr6, r11, 4 and update the specified condition register. |
| `0x826EA020` | `beq cr6, loc_826EA030` | Conditional branch to cr6, loc_826EA030 according to the named CR/CTR condition. |
| `0x826EA024` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA028` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826EA02C` | `bne cr6, loc_826EA034` | Conditional branch to cr6, loc_826EA034 according to the named CR/CTR condition. |
| `0x826EA030` | `li r11, 0` | Materialize immediate/address component: r11, 0. |
| `0x826EA034` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826EA038` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA03C` | `beq cr6, loc_826EA458` | Conditional branch to cr6, loc_826EA458 according to the named CR/CTR condition. |
| `0x826EA040` | `lwz r11, 0x14(r17)` | Load from r11, 0x14(r17). |
| `0x826EA044` | `cmpwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA048` | `beq cr6, loc_826E9FEC` | Conditional branch to cr6, loc_826E9FEC according to the named CR/CTR condition. |
| `0x826EA04C` | `lwz r11, 0x20(r31)` | Load from r11, 0x20(r31). |
| `0x826EA050` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA054` | `lis r11, aGamesharedGame_104@ha` | Materialize immediate/address component: r11, aGamesharedGame_104@ha. |
| `0x826EA058` | `addi r16, r11, aGamesharedGame_104@l# "..\\..\\..\\GameShared\\GameClasses\\So"...` | Integer/address arithmetic: r16, r11, aGamesharedGame_104@l# "..\\..\\..\\GameShared\\GameClasses\\So".... |
| `0x826EA05C` | `bne cr6, loc_826EA07C` | Conditional branch to cr6, loc_826EA07C according to the named CR/CTR condition. |
| `0x826EA060` | `bl CgsDev__Assert__BeginAssert` | Call CgsDev__Assert__BeginAssert; place the return address in LR. |
| `0x826EA064` | `lis r11, aPrequestextern_1@ha` | Materialize immediate/address component: r11, aPrequestextern_1@ha. |
| `0x826EA068` | `li r5, 0x2AC` | Materialize immediate/address component: r5, 0x2AC. |
| `0x826EA06C` | `addi r3, r11, aPrequestextern_1@l# "pRequestExternal->mpReadStream"` | Integer/address arithmetic: r3, r11, aPrequestextern_1@l# "pRequestExternal->mpReadStream". |
| `0x826EA070` | `mr r4, r16` | Copy register value: r4, r16. |
| `0x826EA074` | `bl CgsDev__Assert__FireAssert` | Call CgsDev__Assert__FireAssert; place the return address in LR. |
| `0x826EA078` | `bl CgsDev__Assert__EndAssert` | Call CgsDev__Assert__EndAssert; place the return address in LR. |
| `0x826EA07C` | `lis r11, aResultPrequest@ha` | Materialize immediate/address component: r11, aResultPrequest@ha. |
| `0x826EA080` | `li r15, 6` | Materialize immediate/address component: r15, 6. |
| `0x826EA084` | `addi r22, r11, aResultPrequest@l# "result <= pRequestExternal->mReadSize"` | Integer/address arithmetic: r22, r11, aResultPrequest@l# "result <= pRequestExternal->mReadSize". |
| `0x826EA088` | `lis r11, aPrequestextern_0@ha` | Materialize immediate/address component: r11, aPrequestextern_0@ha. |
| `0x826EA08C` | `lis r23, CgsDev__Log__gpDebugPrint@ha` | Materialize immediate/address component: r23, CgsDev__Log__gpDebugPrint@ha. |
| `0x826EA090` | `addi r21, r11, aPrequestextern_0@l# "pRequestExternal->mReadPointer + pReque"...` | Integer/address arithmetic: r21, r11, aPrequestextern_0@l# "pRequestExternal->mReadPointer + pReque".... |
| `0x826EA094` | `lis r11, aPrequestextern@ha` | Materialize immediate/address component: r11, aPrequestextern@ha. |
| `0x826EA098` | `lis r19, CgsDev__Message__gxMessageFilterFlags@ha` | Materialize immediate/address component: r19, CgsDev__Message__gxMessageFilterFlags@ha. |
| `0x826EA09C` | `addi r20, r11, aPrequestextern@l# "pRequestExternal->maChunk[pRequestExter"...` | Integer/address arithmetic: r20, r11, aPrequestextern@l# "pRequestExternal->maChunk[pRequestExter".... |
| `0x826EA0A0` | `lis r11, aSndplayer1Cgss_1@ha` | Materialize immediate/address component: r11, aSndplayer1Cgss_1@ha. |
| `0x826EA0A4` | `li r18, 4` | Materialize immediate/address component: r18, 4. |
| `0x826EA0A8` | `addi r27, r11, aSndplayer1Cgss_1@l# "SndPlayer1_CgsStreamMod Chunk"` | Integer/address arithmetic: r27, r11, aSndplayer1Cgss_1@l# "SndPlayer1_CgsStreamMod Chunk". |
| `0x826EA0AC` | `lis r11, asc_820B6498@ha` | Materialize immediate/address component: r11, asc_820B6498@ha. |
| `0x826EA0B0` | `addi r26, r11, asc_820B6498@l# " ****\n"` | Integer/address arithmetic: r26, r11, asc_820B6498@l# " ****\n". |
| `0x826EA0B4` | `lis r11, aTo_0@ha` | Materialize immediate/address component: r11, aTo_0@ha. |
| `0x826EA0B8` | `addi r25, r11, aTo_0@l# " to "` | Integer/address arithmetic: r25, r11, aTo_0@l# " to ". |
| `0x826EA0BC` | `lis r11, aStreamWarningR@ha` | Materialize immediate/address component: r11, aStreamWarningR@ha. |
| `0x826EA0C0` | `addi r24, r11, aStreamWarningR@l# "**** STREAM WARNING: reallocating Chunk"...` | Integer/address arithmetic: r24, r11, aStreamWarningR@l# "**** STREAM WARNING: reallocating Chunk".... |
| `0x826EA0C4` | `lwz r9, 0x20(r31)` | Load from r9, 0x20(r31). |
| `0x826EA0C8` | `lwz r11, 0(r9)` | Load from r11, 0(r9). |
| `0x826EA0CC` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA0D0` | `beq cr6, loc_826EA33C` | Conditional branch to cr6, loc_826EA33C according to the named CR/CTR condition. |
| `0x826EA0D4` | `lwz r11, 0x74(r31)` | Load from r11, 0x74(r31). |
| `0x826EA0D8` | `cmplwi cr6, r11, 6` | Compare cr6, r11, 6 and update the specified condition register. |
| `0x826EA0DC` | `bge cr6, loc_826EA33C` | Conditional branch to cr6, loc_826EA33C according to the named CR/CTR condition. |
| `0x826EA0E0` | `lwz r11, 0x24(r31)` | Load from r11, 0x24(r31). |
| `0x826EA0E4` | `addi r15, r15, -1` | Integer/address arithmetic: r15, r15, -1. |
| `0x826EA0E8` | `cmplwi cr6, r11, 1` | Compare cr6, r11, 1 and update the specified condition register. |
| `0x826EA0EC` | `blt cr6, loc_826EA200` | Conditional branch to cr6, loc_826EA200 according to the named CR/CTR condition. |
| `0x826EA0F0` | `beq cr6, loc_826EA148` | Conditional branch to cr6, loc_826EA148 according to the named CR/CTR condition. |
| `0x826EA0F4` | `cmplwi cr6, r11, 3` | Compare cr6, r11, 3 and update the specified condition register. |
| `0x826EA0F8` | `bge cr6, loc_826EA334` | Conditional branch to cr6, loc_826EA334 according to the named CR/CTR condition. |
| `0x826EA0FC` | `lwz r11, 0x60(r31)` | Load from r11, 0x60(r31). |
| `0x826EA100` | `addi r11, r11, 1` | Integer/address arithmetic: r11, r11, 1. |
| `0x826EA104` | `cmplwi cr6, r11, 6` | Compare cr6, r11, 6 and update the specified condition register. |
| `0x826EA108` | `bne cr6, loc_826EA110` | Conditional branch to cr6, loc_826EA110 according to the named CR/CTR condition. |
| `0x826EA10C` | `li r11, 0` | Materialize immediate/address component: r11, 0. |
| `0x826EA110` | `lwz r10, 0x64(r31)` | Load from r10, 0x64(r31). |
| `0x826EA114` | `cmplw cr6, r11, r10` | Compare cr6, r11, r10 and update the specified condition register. |
| `0x826EA118` | `beq cr6, loc_826EA334` | Conditional branch to cr6, loc_826EA334 according to the named CR/CTR condition. |
| `0x826EA11C` | `li r8, 0` | Materialize immediate/address component: r8, 0. |
| `0x826EA120` | `stw r8, 0x170(r30)` | Store the source value to r8, 0x170(r30). |
| `0x826EA124` | `lwz r9, 0x70(r31)` | Load from r9, 0x70(r31). |
| `0x826EA128` | `lwz r10, 0x74(r31)` | Load from r10, 0x74(r31). |
| `0x826EA12C` | `addi r9, r9, 1` | Integer/address arithmetic: r9, r9, 1. |
| `0x826EA130` | `stw r8, 0x24(r31)` | Store the source value to r8, 0x24(r31). |
| `0x826EA134` | `addi r10, r10, 1` | Integer/address arithmetic: r10, r10, 1. |
| `0x826EA138` | `stw r11, 0x60(r31)` | Store the source value to r11, 0x60(r31). |
| `0x826EA13C` | `stw r9, 0x70(r31)` | Store the source value to r9, 0x70(r31). |
| `0x826EA140` | `stw r10, 0x74(r31)` | Store the source value to r10, 0x74(r31). |
| `0x826EA144` | `b loc_826EA334` | Branch unconditionally to loc_826EA334. |
| `0x826EA148` | `lwz r10, 0x60(r31)` | Load from r10, 0x60(r31). |
| `0x826EA14C` | `lwz r11, 0x68(r31)` | Load from r11, 0x68(r31). |
| `0x826EA150` | `slwi r9, r10, 3` | Shift/rotate/mask or width-normalize: r9, r10, 3. |
| `0x826EA154` | `lwz r10, 0x6C(r31)` | Load from r10, 0x6C(r31). |
| `0x826EA158` | `add r9, r9, r31` | Integer/address arithmetic: r9, r9, r31. |
| `0x826EA15C` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826EA160` | `lwz r10, 0x2C(r9)` | Load from r10, 0x2C(r9). |
| `0x826EA164` | `cmplw cr6, r11, r10` | Compare cr6, r11, r10 and update the specified condition register. |
| `0x826EA168` | `ble cr6, loc_826EA184` | Conditional branch to cr6, loc_826EA184 according to the named CR/CTR condition. |
| `0x826EA16C` | `bl CgsDev__Assert__BeginAssert` | Call CgsDev__Assert__BeginAssert; place the return address in LR. |
| `0x826EA170` | `li r5, 0x2E4` | Materialize immediate/address component: r5, 0x2E4. |
| `0x826EA174` | `mr r4, r16` | Copy register value: r4, r16. |
| `0x826EA178` | `mr r3, r21` | Copy register value: r3, r21. |
| `0x826EA17C` | `bl CgsDev__Assert__FireAssert` | Call CgsDev__Assert__FireAssert; place the return address in LR. |
| `0x826EA180` | `bl CgsDev__Assert__EndAssert` | Call CgsDev__Assert__EndAssert; place the return address in LR. |
| `0x826EA184` | `lwz r11, 0x60(r31)` | Load from r11, 0x60(r31). |
| `0x826EA188` | `lwz r9, 0x6C(r31)` | Load from r9, 0x6C(r31). |
| `0x826EA18C` | `addi r10, r11, 6` | Integer/address arithmetic: r10, r11, 6. |
| `0x826EA190` | `lwz r11, 0x20(r31)` | Load from r11, 0x20(r31). |
| `0x826EA194` | `lwz r4, 0x68(r31)` | Load from r4, 0x68(r31). |
| `0x826EA198` | `slwi r10, r10, 3` | Shift/rotate/mask or width-normalize: r10, r10, 3. |
| `0x826EA19C` | `lwz r3, 0(r11)` | Load from r3, 0(r11). |
| `0x826EA1A0` | `lwzx r10, r10, r31` | Load from r10, r10, r31. |
| `0x826EA1A4` | `add r5, r10, r9` | Integer/address arithmetic: r5, r10, r9. |
| `0x826EA1A8` | `bl CgsFileSystem__StreamDeviceDiskRead__Read` | Call CgsFileSystem__StreamDeviceDiskRead__Read; place the return address in LR. |
| `0x826EA1AC` | `mr r29, r3` | Copy register value: r29, r3. |
| `0x826EA1B0` | `cmplwi cr6, r29, 0` | Compare cr6, r29, 0 and update the specified condition register. |
| `0x826EA1B4` | `beq cr6, loc_826EA334` | Conditional branch to cr6, loc_826EA334 according to the named CR/CTR condition. |
| `0x826EA1B8` | `lwz r11, 0x68(r31)` | Load from r11, 0x68(r31). |
| `0x826EA1BC` | `cmplw cr6, r29, r11` | Compare cr6, r29, r11 and update the specified condition register. |
| `0x826EA1C0` | `ble cr6, loc_826EA1DC` | Conditional branch to cr6, loc_826EA1DC according to the named CR/CTR condition. |
| `0x826EA1C4` | `bl CgsDev__Assert__BeginAssert` | Call CgsDev__Assert__BeginAssert; place the return address in LR. |
| `0x826EA1C8` | `li r5, 0x2EE` | Materialize immediate/address component: r5, 0x2EE. |
| `0x826EA1CC` | `mr r4, r16` | Copy register value: r4, r16. |
| `0x826EA1D0` | `mr r3, r22` | Copy register value: r3, r22. |
| `0x826EA1D4` | `bl CgsDev__Assert__FireAssert` | Call CgsDev__Assert__FireAssert; place the return address in LR. |
| `0x826EA1D8` | `bl CgsDev__Assert__EndAssert` | Call CgsDev__Assert__EndAssert; place the return address in LR. |
| `0x826EA1DC` | `lwz r11, 0x68(r31)` | Load from r11, 0x68(r31). |
| `0x826EA1E0` | `lwz r10, 0x6C(r31)` | Load from r10, 0x6C(r31). |
| `0x826EA1E4` | `subf. r11, r29, r11` | Integer/address arithmetic: r11, r29, r11. |
| `0x826EA1E8` | `add r10, r29, r10` | Integer/address arithmetic: r10, r29, r10. |
| `0x826EA1EC` | `stw r11, 0x68(r31)` | Store the source value to r11, 0x68(r31). |
| `0x826EA1F0` | `stw r10, 0x6C(r31)` | Store the source value to r10, 0x6C(r31). |
| `0x826EA1F4` | `bne loc_826EA334` | Conditional branch to loc_826EA334 according to the named CR/CTR condition. |
| `0x826EA1F8` | `li r11, 2` | Materialize immediate/address component: r11, 2. |
| `0x826EA1FC` | `b loc_826EA330` | Branch unconditionally to loc_826EA330. |
| `0x826EA200` | `lwz r11, 0x170(r30)` | Load from r11, 0x170(r30). |
| `0x826EA204` | `lwz r3, 0(r9)` | Load from r3, 0(r9). |
| `0x826EA208` | `add r10, r11, r30` | Integer/address arithmetic: r10, r11, r30. |
| `0x826EA20C` | `subfic r4, r11, 4` | Integer/address arithmetic: r4, r11, 4. |
| `0x826EA210` | `addi r5, r10, 0x174` | Integer/address arithmetic: r5, r10, 0x174. |
| `0x826EA214` | `bl CgsFileSystem__StreamDeviceDiskRead__Read` | Call CgsFileSystem__StreamDeviceDiskRead__Read; place the return address in LR. |
| `0x826EA218` | `lwz r11, 0x170(r30)` | Load from r11, 0x170(r30). |
| `0x826EA21C` | `add r11, r11, r3` | Integer/address arithmetic: r11, r11, r3. |
| `0x826EA220` | `cmplwi cr6, r11, 4` | Compare cr6, r11, 4 and update the specified condition register. |
| `0x826EA224` | `stw r11, 0x170(r30)` | Store the source value to r11, 0x170(r30). |
| `0x826EA228` | `bne cr6, loc_826EA334` | Conditional branch to cr6, loc_826EA334 according to the named CR/CTR condition. |
| `0x826EA22C` | `lwz r11, 0x60(r31)` | Load from r11, 0x60(r31). |
| `0x826EA230` | `lwz r10, 0x174(r30)` | Load from r10, 0x174(r30). |
| `0x826EA234` | `slwi r11, r11, 3` | Shift/rotate/mask or width-normalize: r11, r11, 3. |
| `0x826EA238` | `clrlwi r29, r10, 1` | Shift/rotate/mask or width-normalize: r29, r10, 1. |
| `0x826EA23C` | `add r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x826EA240` | `lwz r28, 0x2C(r11)` | Load from r28, 0x2C(r11). |
| `0x826EA244` | `cmplw cr6, r29, r28` | Compare cr6, r29, r28 and update the specified condition register. |
| `0x826EA248` | `ble cr6, loc_826EA30C` | Conditional branch to cr6, loc_826EA30C according to the named CR/CTR condition. |
| `0x826EA24C` | `ld r11, CgsDev__Message__gxMessageFilterFlags@l(r19)` | Load from r11, CgsDev__Message__gxMessageFilterFlags@l(r19). |
| `0x826EA250` | `clrldi r11, r11, 63` | Shift/rotate/mask or width-normalize: r11, r11, 63. |
| `0x826EA254` | `cmpldi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA258` | `beq cr6, loc_826EA288` | Conditional branch to cr6, loc_826EA288 according to the named CR/CTR condition. |
| `0x826EA25C` | `mr r4, r24` | Copy register value: r4, r24. |
| `0x826EA260` | `lwz r3, CgsDev__Log__gpDebugPrint@l(r23)# off_82F31918` | Load from r3, CgsDev__Log__gpDebugPrint@l(r23)# off_82F31918. |
| `0x826EA264` | `bl CgsDev__StrStreamBase__operator__` | Call CgsDev__StrStreamBase__operator__; place the return address in LR. |
| `0x826EA268` | `mr r4, r28` | Copy register value: r4, r28. |
| `0x826EA26C` | `bl sub_821F0EC8` | Call sub_821F0EC8; place the return address in LR. |
| `0x826EA270` | `mr r4, r25` | Copy register value: r4, r25. |
| `0x826EA274` | `bl CgsDev__StrStreamBase__operator__` | Call CgsDev__StrStreamBase__operator__; place the return address in LR. |
| `0x826EA278` | `mr r4, r29` | Copy register value: r4, r29. |
| `0x826EA27C` | `bl sub_821F0EC8` | Call sub_821F0EC8; place the return address in LR. |
| `0x826EA280` | `mr r4, r26` | Copy register value: r4, r26. |
| `0x826EA284` | `bl CgsDev__StrStreamBase__operator__` | Call CgsDev__StrStreamBase__operator__; place the return address in LR. |
| `0x826EA288` | `lwz r11, 0x60(r31)` | Load from r11, 0x60(r31). |
| `0x826EA28C` | `li r5, 0` | Materialize immediate/address component: r5, 0. |
| `0x826EA290` | `lwz r3, 4(r30)` | Load from r3, 4(r30). |
| `0x826EA294` | `addi r11, r11, 6` | Integer/address arithmetic: r11, r11, 6. |
| `0x826EA298` | `slwi r11, r11, 3` | Shift/rotate/mask or width-normalize: r11, r11, 3. |
| `0x826EA29C` | `lwzx r4, r11, r31` | Load from r4, r11, r31. |
| `0x826EA2A0` | `bl rw__audio__core__System__Free` | Call rw__audio__core__System__Free; place the return address in LR. |
| `0x826EA2A4` | `li r7, 0` | Materialize immediate/address component: r7, 0. |
| `0x826EA2A8` | `lwz r3, 4(r30)` | Load from r3, 4(r30). |
| `0x826EA2AC` | `li r6, 0x10` | Materialize immediate/address component: r6, 0x10. |
| `0x826EA2B0` | `mr r5, r27` | Copy register value: r5, r27. |
| `0x826EA2B4` | `mr r4, r29` | Copy register value: r4, r29. |
| `0x826EA2B8` | `bl rw__audio__core__System__Alloc` | Call rw__audio__core__System__Alloc; place the return address in LR. |
| `0x826EA2BC` | `lwz r11, 0x60(r31)` | Load from r11, 0x60(r31). |
| `0x826EA2C0` | `addi r11, r11, 6` | Integer/address arithmetic: r11, r11, 6. |
| `0x826EA2C4` | `slwi r11, r11, 3` | Shift/rotate/mask or width-normalize: r11, r11, 3. |
| `0x826EA2C8` | `stwx r3, r11, r31` | Store the source value to r3, r11, r31. |
| `0x826EA2CC` | `lwz r11, 0x60(r31)` | Load from r11, 0x60(r31). |
| `0x826EA2D0` | `addi r11, r11, 6` | Integer/address arithmetic: r11, r11, 6. |
| `0x826EA2D4` | `slwi r11, r11, 3` | Shift/rotate/mask or width-normalize: r11, r11, 3. |
| `0x826EA2D8` | `lwzx r11, r11, r31` | Load from r11, r11, r31. |
| `0x826EA2DC` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA2E0` | `bne cr6, loc_826EA2FC` | Conditional branch to cr6, loc_826EA2FC according to the named CR/CTR condition. |
| `0x826EA2E4` | `bl CgsDev__Assert__BeginAssert` | Call CgsDev__Assert__BeginAssert; place the return address in LR. |
| `0x826EA2E8` | `li r5, 0x2D1` | Materialize immediate/address component: r5, 0x2D1. |
| `0x826EA2EC` | `mr r4, r16` | Copy register value: r4, r16. |
| `0x826EA2F0` | `mr r3, r20` | Copy register value: r3, r20. |
| `0x826EA2F4` | `bl CgsDev__Assert__FireAssert` | Call CgsDev__Assert__FireAssert; place the return address in LR. |
| `0x826EA2F8` | `bl CgsDev__Assert__EndAssert` | Call CgsDev__Assert__EndAssert; place the return address in LR. |
| `0x826EA2FC` | `lwz r11, 0x60(r31)` | Load from r11, 0x60(r31). |
| `0x826EA300` | `slwi r11, r11, 3` | Shift/rotate/mask or width-normalize: r11, r11, 3. |
| `0x826EA304` | `add r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x826EA308` | `stw r29, 0x2C(r11)` | Store the source value to r29, 0x2C(r11). |
| `0x826EA30C` | `lwz r11, 0x60(r31)` | Load from r11, 0x60(r31). |
| `0x826EA310` | `addi r10, r29, -4` | Integer/address arithmetic: r10, r29, -4. |
| `0x826EA314` | `addi r11, r11, 6` | Integer/address arithmetic: r11, r11, 6. |
| `0x826EA318` | `slwi r11, r11, 3` | Shift/rotate/mask or width-normalize: r11, r11, 3. |
| `0x826EA31C` | `lwzx r11, r11, r31` | Load from r11, r11, r31. |
| `0x826EA320` | `stw r29, 0(r11)` | Store the source value to r29, 0(r11). |
| `0x826EA324` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826EA328` | `stw r10, 0x68(r31)` | Store the source value to r10, 0x68(r31). |
| `0x826EA32C` | `stw r18, 0x6C(r31)` | Store the source value to r18, 0x6C(r31). |
| `0x826EA330` | `stw r11, 0x24(r31)` | Store the source value to r11, 0x24(r31). |
| `0x826EA334` | `cmplwi cr6, r15, 0` | Compare cr6, r15, 0 and update the specified condition register. |
| `0x826EA338` | `bne cr6, loc_826EA0C4` | Conditional branch to cr6, loc_826EA0C4 according to the named CR/CTR condition. |
| `0x826EA33C` | `lis r10, dbl_820B6460@ha` | Materialize immediate/address component: r10, dbl_820B6460@ha. |
| `0x826EA340` | `lis r11, dbl_82001CA8@ha` | Materialize immediate/address component: r11, dbl_82001CA8@ha. |
| `0x826EA344` | `li r28, 3` | Materialize immediate/address component: r28, 3. |
| `0x826EA348` | `lfd f30, dbl_820B6460@l(r10)` | Load from f30, dbl_820B6460@l(r10). |
| `0x826EA34C` | `lfd f31, dbl_82001CA8@l(r11)` | Load from f31, dbl_82001CA8@l(r11). |
| `0x826EA350` | `lbz r9, 0x1E(r17)` | Load from r9, 0x1E(r17). |
| `0x826EA354` | `cmpwi cr6, r9, 4` | Compare cr6, r9, 4 and update the specified condition register. |
| `0x826EA358` | `beq cr6, loc_826EA368` | Conditional branch to cr6, loc_826EA368 according to the named CR/CTR condition. |
| `0x826EA35C` | `cmpwi cr6, r9, 0` | Compare cr6, r9, 0 and update the specified condition register. |
| `0x826EA360` | `li r11, 1` | Materialize immediate/address component: r11, 1. |
| `0x826EA364` | `bne cr6, loc_826EA36C` | Conditional branch to cr6, loc_826EA36C according to the named CR/CTR condition. |
| `0x826EA368` | `li r11, 0` | Materialize immediate/address component: r11, 0. |
| `0x826EA36C` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826EA370` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA374` | `beq cr6, loc_826EA458` | Conditional branch to cr6, loc_826EA458 according to the named CR/CTR condition. |
| `0x826EA378` | `lbz r11, 0x185(r30)` | Load from r11, 0x185(r30). |
| `0x826EA37C` | `rotlwi r10, r11, 1` | Shift/rotate/mask or width-normalize: r10, r11, 1. |
| `0x826EA380` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826EA384` | `slwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826EA388` | `add r11, r11, r30` | Integer/address arithmetic: r11, r11, r30. |
| `0x826EA38C` | `lbz r11, 0x65(r11)` | Load from r11, 0x65(r11). |
| `0x826EA390` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA394` | `bne cr6, loc_826EA458` | Conditional branch to cr6, loc_826EA458 according to the named CR/CTR condition. |
| `0x826EA398` | `clrlwi r31, r14, 24` | Shift/rotate/mask or width-normalize: r31, r14, 24. |
| `0x826EA39C` | `lwz r10, 0x58(r30)` | Load from r10, 0x58(r30). |
| `0x826EA3A0` | `cmplwi cr6, r9, 1` | Compare cr6, r9, 1 and update the specified condition register. |
| `0x826EA3A4` | `mulli r11, r31, 0x88` | Integer/address arithmetic: r11, r31, 0x88. |
| `0x826EA3A8` | `add r29, r11, r10` | Integer/address arithmetic: r29, r11, r10. |
| `0x826EA3AC` | `bne cr6, loc_826EA404` | Conditional branch to cr6, loc_826EA404 according to the named CR/CTR condition. |
| `0x826EA3B0` | `mr r4, r31` | Copy register value: r4, r31. |
| `0x826EA3B4` | `mr r3, r30` | Copy register value: r3, r30. |
| `0x826EA3B8` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__StartRequest` | Call rw__audio__core__SndPlayer1_CgsStreamMod__StartRequest; place the return address in LR. |
| `0x826EA3BC` | `clrlwi r11, r3, 24` | Shift/rotate/mask or width-normalize: r11, r3, 24. |
| `0x826EA3C0` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA3C4` | `beq cr6, loc_826EA458` | Conditional branch to cr6, loc_826EA458 according to the named CR/CTR condition. |
| `0x826EA3C8` | `li r11, 2` | Materialize immediate/address component: r11, 2. |
| `0x826EA3CC` | `stb r11, 0x1E(r17)` | Store the source value to r11, 0x1E(r17). |
| `0x826EA3D0` | `lbz r11, 0x78(r29)` | Load from r11, 0x78(r29). |
| `0x826EA3D4` | `cmplwi cr6, r11, 3` | Compare cr6, r11, 3 and update the specified condition register. |
| `0x826EA3D8` | `bne cr6, loc_826EA404` | Conditional branch to cr6, loc_826EA404 according to the named CR/CTR condition. |
| `0x826EA3DC` | `lfd f0, 0(r17)` | Load from f0, 0(r17). |
| `0x826EA3E0` | `fcmpu cr6, f0, f31` | Compare cr6, f0, f31 and update the specified condition register. |
| `0x826EA3E4` | `bne cr6, loc_826EA404` | Conditional branch to cr6, loc_826EA404 according to the named CR/CTR condition. |
| `0x826EA3E8` | `lbz r11, 0x181(r30)` | Load from r11, 0x181(r30). |
| `0x826EA3EC` | `cmplw cr6, r31, r11` | Compare cr6, r31, r11 and update the specified condition register. |
| `0x826EA3F0` | `bne cr6, loc_826EA404` | Conditional branch to cr6, loc_826EA404 according to the named CR/CTR condition. |
| `0x826EA3F4` | `lwz r11, 4(r30)` | Load from r11, 4(r30). |
| `0x826EA3F8` | `lfd f0, 8(r11)` | Load from f0, 8(r11). |
| `0x826EA3FC` | `fadd f0, f0, f30` | Floating-point arithmetic/select/conversion: f0, f0, f30. |
| `0x826EA400` | `stfd f0, 0(r17)` | Store the source value to f0, 0(r17). |
| `0x826EA404` | `lbz r11, 0x1E(r17)` | Load from r11, 0x1E(r17). |
| `0x826EA408` | `cmplwi cr6, r11, 2` | Compare cr6, r11, 2 and update the specified condition register. |
| `0x826EA40C` | `bne cr6, loc_826EA4C4` | Conditional branch to cr6, loc_826EA4C4 according to the named CR/CTR condition. |
| `0x826EA410` | `lbz r11, 0x185(r30)` | Load from r11, 0x185(r30). |
| `0x826EA414` | `rotlwi r10, r11, 1` | Shift/rotate/mask or width-normalize: r10, r11, 1. |
| `0x826EA418` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826EA41C` | `slwi r11, r11, 2` | Shift/rotate/mask or width-normalize: r11, r11, 2. |
| `0x826EA420` | `add r11, r11, r30` | Integer/address arithmetic: r11, r11, r30. |
| `0x826EA424` | `lbz r11, 0x65(r11)` | Load from r11, 0x65(r11). |
| `0x826EA428` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA42C` | `bne cr6, loc_826EA4C4` | Conditional branch to cr6, loc_826EA4C4 according to the named CR/CTR condition. |
| `0x826EA430` | `lwz r11, 0x14(r29)` | Load from r11, 0x14(r29). |
| `0x826EA434` | `mr r4, r31` | Copy register value: r4, r31. |
| `0x826EA438` | `lwz r10, 0x18(r17)` | Load from r10, 0x18(r17). |
| `0x826EA43C` | `mr r3, r30` | Copy register value: r3, r30. |
| `0x826EA440` | `cmpw cr6, r11, r10` | Compare cr6, r11, r10 and update the specified condition register. |
| `0x826EA444` | `bne cr6, loc_826EA468` | Conditional branch to cr6, loc_826EA468 according to the named CR/CTR condition. |
| `0x826EA448` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__HandleLoopStart` | Call rw__audio__core__SndPlayer1_CgsStreamMod__HandleLoopStart; place the return address in LR. |
| `0x826EA44C` | `clrlwi r11, r3, 24` | Shift/rotate/mask or width-normalize: r11, r3, 24. |
| `0x826EA450` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA454` | `bne cr6, loc_826EA350` | Conditional branch to cr6, loc_826EA350 according to the named CR/CTR condition. |
| `0x826EA458` | `addi r1, r1, 0x110` | Integer/address arithmetic: r1, r1, 0x110. |
| `0x826EA45C` | `lfd f30, var_A8(r1)` | Load from f30, var_A8(r1). |
| `0x826EA460` | `lfd f31, var_A0(r1)` | Load from f31, var_A0(r1). |
| `0x826EA464` | `b __restgprlr` | Branch unconditionally to __restgprlr. |
| `0x826EA468` | `lwz r10, 0x14(r17)` | Load from r10, 0x14(r17). |
| `0x826EA46C` | `cmpw cr6, r11, r10` | Compare cr6, r11, r10 and update the specified condition register. |
| `0x826EA470` | `bne cr6, loc_826EA4B8` | Conditional branch to cr6, loc_826EA4B8 according to the named CR/CTR condition. |
| `0x826EA474` | `addi r5, r1, 0x110+var_C0` | Integer/address arithmetic: r5, r1, 0x110+var_C0. |
| `0x826EA478` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__HandleSampleEnd` | Call rw__audio__core__SndPlayer1_CgsStreamMod__HandleSampleEnd; place the return address in LR. |
| `0x826EA47C` | `clrlwi r11, r3, 24` | Shift/rotate/mask or width-normalize: r11, r3, 24. |
| `0x826EA480` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA484` | `beq cr6, loc_826EA458` | Conditional branch to cr6, loc_826EA458 according to the named CR/CTR condition. |
| `0x826EA488` | `lbz r11, 0x110+var_C0(r1)` | Load from r11, 0x110+var_C0(r1). |
| `0x826EA48C` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826EA490` | `beq cr6, loc_826EA350` | Conditional branch to cr6, loc_826EA350 according to the named CR/CTR condition. |
| `0x826EA494` | `addi r11, r31, 1` | Integer/address arithmetic: r11, r31, 1. |
| `0x826EA498` | `stb r28, 0x1E(r17)` | Store the source value to r28, 0x1E(r17). |
| `0x826EA49C` | `lbz r10, 0x182(r30)` | Load from r10, 0x182(r30). |
| `0x826EA4A0` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826EA4A4` | `mr r9, r11` | Copy register value: r9, r11. |
| `0x826EA4A8` | `cmplw cr6, r9, r10` | Compare cr6, r9, r10 and update the specified condition register. |
| `0x826EA4AC` | `bne cr6, loc_826EA4E0` | Conditional branch to cr6, loc_826EA4E0 according to the named CR/CTR condition. |
| `0x826EA4B0` | `li r14, 0` | Materialize immediate/address component: r14, 0. |
| `0x826EA4B4` | `b loc_826EA4E4` | Branch unconditionally to loc_826EA4E4. |
| `0x826EA4B8` | `li r5, 0` | Materialize immediate/address component: r5, 0. |
| `0x826EA4BC` | `bl rw__audio__core__SndPlayer1_CgsStreamMod__StreamNextChunk` | Call rw__audio__core__SndPlayer1_CgsStreamMod__StreamNextChunk; place the return address in LR. |
| `0x826EA4C0` | `b loc_826EA44C` | Branch unconditionally to loc_826EA44C. |
| `0x826EA4C4` | `addi r11, r31, 1` | Integer/address arithmetic: r11, r31, 1. |
| `0x826EA4C8` | `lbz r10, 0x182(r30)` | Load from r10, 0x182(r30). |
| `0x826EA4CC` | `li r14, 0` | Materialize immediate/address component: r14, 0. |
| `0x826EA4D0` | `clrlwi r11, r11, 24` | Shift/rotate/mask or width-normalize: r11, r11, 24. |
| `0x826EA4D4` | `mr r9, r11` | Copy register value: r9, r11. |
| `0x826EA4D8` | `cmplw cr6, r9, r10` | Compare cr6, r9, r10 and update the specified condition register. |
| `0x826EA4DC` | `beq cr6, loc_826EA4E4` | Conditional branch to cr6, loc_826EA4E4 according to the named CR/CTR condition. |
| `0x826EA4E0` | `mr r14, r11` | Copy register value: r14, r11. |
| `0x826EA4E4` | `lbz r10, 0x181(r30)` | Load from r10, 0x181(r30). |
| `0x826EA4E8` | `clrlwi r11, r14, 24` | Shift/rotate/mask or width-normalize: r11, r14, 24. |
| `0x826EA4EC` | `cmplw cr6, r11, r10` | Compare cr6, r11, r10 and update the specified condition register. |
| `0x826EA4F0` | `beq cr6, loc_826EA458` | Conditional branch to cr6, loc_826EA458 according to the named CR/CTR condition. |
| `0x826EA4F4` | `lhz r10, 0x17C(r30)` | Load from r10, 0x17C(r30). |
| `0x826EA4F8` | `slwi r11, r11, 5` | Shift/rotate/mask or width-normalize: r11, r11, 5. |
| `0x826EA4FC` | `add r11, r11, r10` | Integer/address arithmetic: r11, r11, r10. |
| `0x826EA500` | `add r17, r11, r30` | Integer/address arithmetic: r17, r11, r30. |
| `0x826EA504` | `b loc_826EA350` | Branch unconditionally to loc_826EA350. |

#### (c) Rodata constants

| VA | file_off | Raw bytes | Decode/use |
|---:|---:|---|---|
| `0x82001CA8` | `0x00004CA8` | `00 00 00 00 00 00 00 00` | `0.0` |
| `0x820B6460` | `0x000B9460` | `3F 75 D8 67 C3 EC E2 A5` | double `0.005333333333333333` (`256/48000`) |
| `0x820B6468` | `0x000B9468` | `2A 2A 2A 2A 20 53 54 52 45 41 4D 20 57 41 52 4E 49 4E 47 3A 20 72 65 61 6C 6C 6F 63 61 74 69 6E 67 20 43 68 75 6E 6B 20 66 72 6F 6D 20 00` | warning prefix |
| `0x8203B570` | `0x0003E570` | `20 74 6F 20 00` | `" to "` |
| `0x820B6498` | `0x000B9498` | `20 2A 2A 2A 2A 0A 00` | warning suffix |
| `0x820B64A0` | `0x000B94A0` | `53 6E 64 50 6C 61 79 65 72 31 5F 43 67 73 53 74 72 65 61 6D 4D 6F 64 20 43 68 75 6E 6B 00` | allocation tag |
| `0x820B64C0` | `0x000B94C0` | `70 52 65 71 75 65 73 74 45 78 74 65 72 6E 61 6C 2D 3E 6D 61 43 68 75 6E 6B 5B 70 52 65 71 75 65 73 74 45 78 74 65 72 6E 61 6C 2D 3E 6D 57 72 69 74 65 42 75 66 66 65 72 53 65 6C 65 63 74 5D 2E 62 75 66 00` | allocation assert |
| `0x820B6508` | `0x000B9508` | `70 52 65 71 75 65 73 74 45 78 74 65 72 6E 61 6C 2D 3E 6D 52 65 61 64 50 6F 69 6E 74 65 72 20 2B 20 70 52 65 71 75 65 73 74 45 78 74 65 72 6E 61 6C 2D 3E 6D 52 65 61 64 53 69 7A 65 20 3C 3D 20 70 52 65 71 75 65 73 74 45 78 74 65 72 6E 61 6C 2D 3E 6D 61 43 68 75 6E 6B 5B 70 52 65 71 75 65 73 74 45 78 74 65 72 6E 61 6C 2D 3E 6D 57 72 69 74 65 42 75 66 66 65 72 53 65 6C 65 63 74 5D 2E 73 69 7A 65 00` | read-bound assert |
| `0x820B6590` | `0x000B9590` | `72 65 73 75 6C 74 20 3C 3D 20 70 52 65 71 75 65 73 74 45 78 74 65 72 6E 61 6C 2D 3E 6D 52 65 61 64 53 69 7A 65 00` | read-result assert |
| `0x820B65B8` | `0x000B95B8` | `70 52 65 71 75 65 73 74 45 78 74 65 72 6E 61 6C 2D 3E 6D 70 52 65 61 64 53 74 72 65 61 6D 00` | stream assert |
| `0x820B65D8` | `0x000B95D8` | `2E 2E 5C 2E 2E 5C 2E 2E 5C 47 61 6D 65 53 68 61 72 65 64 5C 47 61 6D 65 43 6C 61 73 73 65 73 5C 53 6F 75 6E 64 2F 50 6C 61 79 62 61 63 6B 2F 50 6C 75 67 69 6E 73 2F 53 74 72 65 61 6D 69 6E 67 2F 69 6E 74 65 72 6E 61 6C 2F 73 6E 64 70 6C 61 79 65 72 31 2E 63 70 70 00` | assert source file |

#### (d) Member-offset/access table

| Offset | Access | Faithful name |
|---:|---|---|
| Voice `+0x47` | abort if expelled state 2 | `Voice::mucState` |
| attributes `+0x28/+0x30/+0x38` | publish handle/progress/length | three attributes |
| `+0x150..+0x15C` | source for attributes | current request cache |
| `+0x170/+0x174` | assemble 4-byte next chunk size | `muDataReadForNewSize/mau8NewSize` |
| request/feed cursors `+0x17C..+0x186` | cleanup, scan, feed scheduling | named fields |
| internal all fields | active request state/timing | `RequestInternal` |
| external `+0x20/+0x24/+0x2C..+0x80` | complete async read/chunk state machine | `RequestExternal` |

#### (e) Implementation-grade C++ sketch

```cpp
void RwacTimerClient(void* ctx,float)
{
    auto* s=static_cast<SndPlayer1_CgsStreamMod*>(ctx);
    if (s->mpVoice->mucState==2) return;
    s->FeedCleanup(); s->RequestCleanup();
    u32 i=s->mCurrentRequest; RequestInternal* r=&s->Request(i);
    if (!IsActive(r->state)) { s->mAttribute[1].mfValue=s->mAttribute[2].mfValue=0.0f; return; }
    s->mAttribute[0].mfValue=s->mCurrentRequestHandle;
    s->mAttribute[2].mfValue=f64(s->mCurrentRequestNumSamples)/s->mCurrentRequestSampleRate;
    s->mAttribute[1].mfValue=f64(s->mCurrentRequestSamplesPlayed)/s->mCurrentRequestSampleRate;
    while (IsActive(r->state) && r->numSamples==0) { i=(i+1)%s->mMaxRequests; r=&s->Request(i); }
    if (!IsActive(r->state)) return;
    RequestExternal& e=s->mpRequestExternal[i];
    CGS_ASSERT(e.pReadStream,"pRequestExternal->mpReadStream");
    for (u32 budget=0; budget<6 && e.pReadStream->mDeviceStream && e.lockedChunks<6; ++budget) {
        if (e.streamState==SUBMIT_CHUNK) {
            u32 next=(e.writeBufferSelect+1)%6;
            if (next!=e.unlockBufferSelect) { s->muDataReadForNewSize=0; e.streamState=READ_HEADER;
                e.writeBufferSelect=next; ++e.queuedChunks; ++e.lockedChunks; }
        } else if (e.streamState==READ_CHUNK) {
            CGS_ASSERT(e.readPointer+e.readSize<=e.chunks[e.writeBufferSelect].size,"read bound");
            u32 got=e.pReadStream->Read(e.readSize,e.chunks[e.writeBufferSelect].buf+e.readPointer);
            if (!got) break; CGS_ASSERT(got<=e.readSize,"read result");
            e.readSize-=got; e.readPointer+=got; if (!e.readSize) e.streamState=SUBMIT_CHUNK;
        } else {
            u32 got=e.pReadStream->Read(4-s->muDataReadForNewSize,
                                       s->mau8NewSize+s->muDataReadForNewSize);
            s->muDataReadForNewSize+=got; if (s->muDataReadForNewSize!=4) continue;
            u32 size=ReadBE32(s->mau8NewSize)&0x7FFFFFFFu; Chunk& c=e.chunks[e.writeBufferSelect];
            if (size>c.size) { System::Free(s->mpSystemUseGetSystemAccessor,c.buf,nullptr);
                c.buf=static_cast<u8*>(System::Alloc(s->mpSystemUseGetSystemAccessor,size,
                    "SndPlayer1_CgsStreamMod Chunk",16,nullptr)); CGS_ASSERT(c.buf,"chunk buf"); c.size=size; }
            WriteBE32(c.buf,size); e.readSize=size-4; e.readPointer=4; e.streamState=READ_CHUNK;
        }
    }
    for (;;) {
        if (!IsActive(r->state) || s->mFeedDesc[s->mNextFeedSlotToFill].feedState) return;
        RequestExternal& x=s->mpRequestExternal[i];
        if (r->state==QUEUED) {
            if (!s->StartRequest(i)) return; r->state=FEEDING;
            if (x.codec==3 && r->startTime==0.0 && i==s->mCurrentRequest)
                r->startTime=s->mpSystemUseGetSystemAccessor->mfSystemTime+0.005333333333333333;
        }
        if (r->state!=FEEDING || s->mFeedDesc[s->mNextFeedSlotToFill].feedState) {
            i=(i+1)%s->mMaxRequests; if (i==s->mCurrentRequest) return; r=&s->Request(i); continue;
        }
        bool ok;
        if (x.numSamplesFed==r->loopStart) ok=s->HandleLoopStart(i);
        else if (x.numSamplesFed==r->numSamples) {
            bool complete=false; ok=s->HandleSampleEnd(i,&complete);
            if (ok && complete) { r->state=FEEDCOMPLETE; i=(i+1)%s->mMaxRequests;
                if (i==s->mCurrentRequest) return; r=&s->Request(i); continue; }
        } else ok=s->StreamNextChunk(i,false);
        if (!ok) return;
    }
}
```

X64 hazards: all System/Voice/stream/chunk/decoder pointers widen; external/internal/chunk
strides use host `sizeof`, while feed count remains 20.  The four-byte stream header is
file-format data and stays four bytes; `muDataReadForNewSize` is a count, not a pointer.
No deferred command return or GetSize body occurs here.

### Divergences from `rw::audio::core::SndPlayer1`

| Concern | Ordinary SndPlayer1 (ARTIST) | CgsStreamMod (ARTIST) | Evidence |
|---|---|---|---|
| fixed object/tail boundary | declick `+0x1D8` | declick `+0x188` | ordinary `0x82BA0220/0x82BA6CC4`; StreamMod `0x826A4244..48/0x826EA558..59C` |
| feed records | 20 records, console stride `0x10`; includes RW-core chunk/stream pointers | 20 records, console stride `0x0C`; `bool streamed`, played count, three bytes; no pointer | ordinary create loop `0x82BA6DA4..DE0`; StreamMod loops/wrap `0x826EA750..778`, `0x826A4348..398`; DecFIGS type |
| internal request | console `0x30`; three skip counters and decoder size/state at `+0x28/+0x2A` | console `0x20`; no skip counters, decoder size/state at `+0x1C/+0x1E` | ordinary Process/Start; StreamMod rotate-by-5 throughout |
| external request | separate allocation `4 + 0x50*n`; first word is request-handle counter | allocation `0x88*n`; six `(size,buf)` chunks and async read state | ordinary Create `0x82BA6CEC..D30`; StreamMod `0x826EA5A4..6F0` |
| handle counter | `float*` at `+0x1B0`, allocated header | embedded `float mRequestHandle` at `+0x160` | ordinary Event/Create; StreamMod `0x826DB598..5B8`, `0x826EA71C` |
| fixed tail cache | ordinary current fields `+0x1A0..`, format `+0x1BC`, cursors `+0x1C0..` | current fields `+0x150..`, format `+0x16C`, new-size state `+0x170/+0x174`, cursors `+0x178..` | both families' assembly |
| request count | ctor parameter, default 1, low byte stored (same policy) | same | both GetSize/Create pairs |
| chunk/feed supply | RW `StreamPool`, Stream objects and stream request accessors | game `IStreamProvider`, `CgsFileSystem::ReadStream`, six allocated chunk buffers | ordinary Play/stream helpers; StreamMod Play/Timer/Remove |
| decoder consumption | skip counters and more elaborate availability accounting | `Decoder::GetSamplesRemaining(feedHandle)`, direct decode of min(requested, remaining) | Process bodies |
| event surface | six events including PLAY1 compatibility path | five events, PLAY builds prefixed path directly | vtable Event bodies/descriptors (`numEvents 6` vs StreamMod 5) |

### `sndplayer1shared.h` existing coverage

The exact current PC files are
`b5-decomp/src/GameShared/GameClasses/Sound/Playback/Plugins/Streaming/internal/sndplayer1shared.h`,
`b5-decomp/src/GameShared/GameClasses/Sound/Playback/Plugins/Streaming/internal/sndplayer1shared.cpp`,
and
`b5-decomp/src/GameShared/GameClasses/Sound/Playback/Plugins/Streaming/internal/sndplayer1.cpp`.
They provide only:

- static `spPathPrefix` storage and its RootSoundModule assignment;
- a real `AdvanceCurrentRequest` body;
- a real `GetPpuTicksEvent` body;
- a single shared class declaration with some request/timer fields.

What is correct: base `PlugIn`, three attributes, TimerHandle at console `+0x40`,
external pointer `+0x58`, 32-byte console internal request shape, current cache
`+0x150..+0x15C`, request offsets/cursors `+0x178..+0x187`, and the two implemented
bodies' core behavior.

What is wrong or missing:

- `SndPlayer1FeedDesc` is modelled with two invented `void*` members and console-size
  claim 16, then array count 15.  DecFIGS and ARTIST require pointer-free
  `{bool,pad,s32,u8,u8,u8,pad}`, stride 12, count 20.
- `mpRequestHandle` at `+0x160` is declared `f32*`; it is embedded `f32
  mRequestHandle` (`lfs/stfs` directly at `0x826DB598..5B8`, DecFIGS name/type).
- `mUnknown170` is not unknown: it is `u32 muDataReadForNewSize`, followed by
  `u8 mau8NewSize[4]` at `+0x174`; the timer fills these at
  `0x826EA200..238`.
- `mpRequestExternal` is untyped and every descriptor callback/helper/vtable body
  other than the two tiny methods is absent.  No descriptor getter/host record is
  present, and the factory leaves registration #24 commented out.

### `IStreamProvider (off_82FFBA0C)` wiring

The X360 publish is exact in
`.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826E90C0.json`:
`Module::Prepare 0x826E9464..0x826E9474` loads the global, forms `this+0x228` (the
`IStreamProvider` secondary base), and stores it.  Current PC
`b5-decomp/src/GameShared/GameClasses/Sound/Playback/Module/CgsSoundPlaybackModule.cpp`
defines the global as `IStreamProvider*` and assigns
`static_cast<IStreamProvider*>(this)` after Splicer creation, while
`b5-decomp/src/GameShared/GameClasses/Sound/Playback/Plugins/Streaming/CgsStreamingPlugin.h`
contains the typed `IStreamProvider`/`StreamSpec` interface.  Publishing is therefore
already faithful.

Consumption is two virtual calls:

- `PlayHandler 0x826A4458..0x826A449C` constructs the exact 20-byte X360
  `StreamSpec { command.path, &external.pStreamBuffer, plugin, 0, 50 }`, calls provider
  vtable slot 0 `DoOpenStream(StreamSpec&)`, and stores the returned `ReadStream*` at
  external `+0x20`.
- `RemoveRequest 0x826A465C..0x826A4674` loads external `+0x20` and calls provider
  vtable slot `+4`, `DoCloseStream(const ReadStream*)`.

On x64 the interface pointer, three pointer members in StreamSpec, and returned stream
pointer widen; construct the host `StreamSpec` by name.  Do not preserve the console
20-byte size or virtual slot byte displacement manually.

The remaining hookup gap is at the consumer/registry side: StreamMod has no complete PC
implementation/descriptor, and
`b5-decomp/src/GameShared/GameClasses/Sound/Playback/RWAC/CgsGenericRwacFactory.cpp`
explicitly leaves console registration #24 commented out.

## 3. TARGET 2 - GainArray

As in Target 1, every subsection (a) gives the complete consumed register ABI; no
GainArray body has a caller-supplied stack argument.  Prologue stack slots are save
areas/locals only.

The ARTIST object is a normal `rw::audio::core::PlugIn` followed by six target
attributes and six cached current gains.  On X360 the base occupies `0x28` bytes,
`PlugIn::mpAttribute` points to the first `Attribute_t` at `+0x28`, each target has the
canonical eight-byte `Attribute_t` stride, and the current-gain array begins at `+0x58`.

### `GetSize` — `0x82689E08`

#### (a) Exact signature / dispatch ABI

At `Voice::CreateInstance 0x82B6EC98..0x82B6ECA8`, the descriptor GetSize slot is
called indirectly with `r3 = const VoiceStageConfig*` (the current 12-byte stage
record); this leaf ignores it.  There are no stack arguments.  It returns the X360
allocation size as `u32` in `r3`:

```cpp
static u32 GetSize(const rw::audio::core::VoiceStageConfig* config /* r3 */);
```

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82689E08.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x82689E08` | `li r3, 0x70 # 'p'` | Materialize immediate/address component: r3, 0x70 # 'p'. |
| `0x82689E0C` | `blr` | Return to the caller through LR. |

#### (c) Rodata constants

None.  `0x70` is an instruction immediate, not rodata.

#### (d) Member-offset/access table

This function dereferences no object member.  Its returned console extent implies the
last byte of the six-current-gain tail is `+0x6F`.

#### (e) Implementation-grade C++ sketch

```cpp
u32 GainArray::GetSize(const VoiceStageConfig*)
{
    return static_cast<u32>(sizeof(GainArray)); // host layout, not literal 0x70
}
```

X64 hazards: this is the explicit GetSize trap.  The X360 body returns `0x70`, but a
host callback must return `sizeof(GainArray)` after the hidden vptr, four PlugIn
pointers, and `mpAttribute` have widened.  There is no console record stride, narrow
pointer store, or deferred-command cursor return in this body.

### `CreateInstance` — `0x826C3A10`

#### (a) Exact signature / dispatch ABI

The generic call site is `PlugIn::CreateInstance 0x82B6A864..0x82B6A870`: `r3` is
the already base-initialized placement object, `r4` is reloaded from
`VoiceStageConfig+0`, and `r5/r6/r7` still carry descriptor, config, and the input
channel flag.  This callback consumes only `r3` and returns boolean `1` in `r3`; no
arguments are on the stack.  Semantic body signature:

```cpp
static int CreateInstance(GainArray* self /* r3 */);
```

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826C3A10.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826C3A10` | `cmplwi cr6, r3, 0` | Compare cr6, r3, 0 and update the specified condition register. |
| `0x826C3A14` | `beq cr6, loc_826C3A24` | Conditional branch to cr6, loc_826C3A24 according to the named CR/CTR condition. |
| `0x826C3A18` | `lis r11, off_820AE188@ha` | Materialize immediate/address component: r11, off_820AE188@ha. |
| `0x826C3A1C` | `addi r11, r11, off_820AE188@l` | Integer/address arithmetic: r11, r11, off_820AE188@l. |
| `0x826C3A20` | `stw r11, 0(r3)` | Store the source value to r11, 0(r3). |
| `0x826C3A24` | `addi r9, r3, 0x28 # '('` | Integer/address arithmetic: r9, r3, 0x28 # '('. |
| `0x826C3A28` | `lis r8, flt_82001C98@ha` | Materialize immediate/address component: r8, flt_82001C98@ha. |
| `0x826C3A2C` | `addi r10, r3, 0x58 # 'X'` | Integer/address arithmetic: r10, r3, 0x58 # 'X'. |
| `0x826C3A30` | `li r11, 6` | Materialize immediate/address component: r11, 6. |
| `0x826C3A34` | `stw r9, 0xC(r3)` | Store the source value to r9, 0xC(r3). |
| `0x826C3A38` | `lfs f0, flt_82001C98@l(r8)` | Load from f0, flt_82001C98@l(r8). |
| `0x826C3A3C` | `addi r11, r11, -1` | Integer/address arithmetic: r11, r11, -1. |
| `0x826C3A40` | `stfs f0, 0(r10)` | Store the source value to f0, 0(r10). |
| `0x826C3A44` | `stfs f0, 0(r9)` | Store the source value to f0, 0(r9). |
| `0x826C3A48` | `addi r10, r10, 4` | Integer/address arithmetic: r10, r10, 4. |
| `0x826C3A4C` | `addi r9, r9, 8` | Integer/address arithmetic: r9, r9, 8. |
| `0x826C3A50` | `cmplwi cr6, r11, 0` | Compare cr6, r11, 0 and update the specified condition register. |
| `0x826C3A54` | `bne cr6, loc_826C3A3C` | Conditional branch to cr6, loc_826C3A3C according to the named CR/CTR condition. |
| `0x826C3A58` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x826C3A5C` | `blr` | Return to the caller through LR. |

#### (c) Rodata constants

| Constant | File offset | Raw bytes | Decoded value/use |
|---|---:|---|---|
| `off_820AE188` | `0x000B1188` | `82 84 CB 38 82 84 CB 38 82 7E 2F 38 82 6A A9 E0` | GainArray's four X360 virtual slots |
| `flt_82001C98` | `0x00004C98` | `3F 80 00 00` | IEEE-754 `1.0f`, written to all 12 gain values |

#### (d) Member-offset/access table

| X360 offset | Access | Faithful PC name |
|---:|---|---|
| `+0x00` | store X360 vtable address | hidden host vptr installed by construction |
| `+0x0C` | store address `self+0x28` | inherited `PlugIn::mpAttribute` |
| `+0x28 + 8*i` (`i<6`) | store `1.0f` | `mpAttribute[i].mfValue` / six target gains |
| `+0x58 + 4*i` (`i<6`) | store `1.0f` | `maCurrentGain[i]` |

#### (e) Implementation-grade C++ sketch

```cpp
int GainArray::CreateInstance(GainArray* self)
{
    // The generic allocator guarantees non-null.  ARTIST conditionally writes the
    // vptr but then unconditionally dereferences self, so null is not a supported call.
    self->mpAttribute = self->maTargetGain;
    for (u32 i=0; i!=6; ++i) {
        self->maCurrentGain[i] = 1.0f;
        self->maTargetGain[i].mfValue = 1.0f;
    }
    return 1;
}
```

X64 hazards: `mpAttribute` is a widened host pointer; assign `maTargetGain` by name,
never store a truncated X360 `self+0x28`.  `Attribute_t` remains a logical six-record
array but host offsets must follow the host `PlugIn` base.  There is no narrow pointer
field or deferred-command cursor return.  Vptr installation is C++ construction, not
a literal store of `0x820AE188`.

### `Process` — `0x8268CDB0`

#### (a) Exact signature / dispatch ABI

The stage callback ABI is `r3 = GainArray* self`, `r4 = Mixer* processContext`,
`r5 = bool firstPass` (only its low byte is significant), with no stack arguments;
`r3 = 1` is returned.  `Mixer` is therefore the real type of the supposedly opaque
second argument:

```cpp
static int Process(GainArray* self /* r3 */,
                   rw::audio::core::Mixer* mixer /* r4 */,
                   bool firstPass /* low byte of r5 */);
```

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x8268CDB0.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x8268CDB0` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x8268CDB4` | `bl __savegprlr_23` | Call __savegprlr_23; place the return address in LR. |
| `0x8268CDB8` | `stfd f31, var_58(r1)` | Store the source value to f31, var_58(r1). |
| `0x8268CDBC` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x8268CDC0` | `addis r25, r4, 3` | Integer/address arithmetic: r25, r4, 3. |
| `0x8268CDC4` | `lbz r26, 0x21(r3)` | Load from r26, 0x21(r3). |
| `0x8268CDC8` | `addis r24, r4, 3` | Integer/address arithmetic: r24, r4, 3. |
| `0x8268CDCC` | `addi r25, r25, 0xC` | Integer/address arithmetic: r25, r25, 0xC. |
| `0x8268CDD0` | `addi r24, r24, 0x10` | Integer/address arithmetic: r24, r24, 0x10. |
| `0x8268CDD4` | `li r31, 0` | Materialize immediate/address component: r31, 0. |
| `0x8268CDD8` | `cmplwi cr6, r26, 0` | Compare cr6, r26, 0 and update the specified condition register. |
| `0x8268CDDC` | `lwz r28, 0(r25)` | Load from r28, 0(r25). |
| `0x8268CDE0` | `lwz r27, 0(r24)` | Load from r27, 0(r24). |
| `0x8268CDE4` | `beq cr6, loc_8268CE68` | Conditional branch to cr6, loc_8268CE68 according to the named CR/CTR condition. |
| `0x8268CDE8` | `lis r11, flt_820ADC00@ha` | Materialize immediate/address component: r11, flt_820ADC00@ha. |
| `0x8268CDEC` | `clrlwi r23, r5, 24` | Shift/rotate/mask or width-normalize: r23, r5, 24. |
| `0x8268CDF0` | `addi r29, r3, 0x58 # 'X'` | Integer/address arithmetic: r29, r3, 0x58 # 'X'. |
| `0x8268CDF4` | `addi r30, r3, 0x28 # '('` | Integer/address arithmetic: r30, r3, 0x28 # '('. |
| `0x8268CDF8` | `lfs f31, flt_820ADC00@l(r11)` | Load from f31, flt_820ADC00@l(r11). |
| `0x8268CDFC` | `cmplwi cr6, r23, 0` | Compare cr6, r23, 0 and update the specified condition register. |
| `0x8268CE00` | `beq cr6, loc_8268CE0C` | Conditional branch to cr6, loc_8268CE0C according to the named CR/CTR condition. |
| `0x8268CE04` | `lfs f0, 0(r30)` | Load from f0, 0(r30). |
| `0x8268CE08` | `stfs f0, 0(r29)` | Store the source value to f0, 0(r29). |
| `0x8268CE0C` | `lfs f1, 0(r29)` | Load from f1, 0(r29). |
| `0x8268CE10` | `lhz r11, 0xE(r28)` | Load from r11, 0xE(r28). |
| `0x8268CE14` | `lfs f0, 0(r30)` | Load from f0, 0(r30). |
| `0x8268CE18` | `lhz r10, 0xE(r27)` | Load from r10, 0xE(r27). |
| `0x8268CE1C` | `fsubs f0, f0, f1` | Floating-point arithmetic/select/conversion: f0, f0, f1. |
| `0x8268CE20` | `mullw r11, r11, r31` | Integer/address arithmetic: r11, r11, r31. |
| `0x8268CE24` | `mullw r7, r10, r31` | Integer/address arithmetic: r7, r10, r31. |
| `0x8268CE28` | `lwz r8, 4(r28)` | Load from r8, 4(r28). |
| `0x8268CE2C` | `lwz r10, 4(r27)` | Load from r10, 4(r27). |
| `0x8268CE30` | `fmuls f2, f0, f31` | Floating-point arithmetic/select/conversion: f2, f0, f31. |
| `0x8268CE34` | `slwi r9, r11, 2` | Shift/rotate/mask or width-normalize: r9, r11, 2. |
| `0x8268CE38` | `slwi r11, r7, 2` | Shift/rotate/mask or width-normalize: r11, r7, 2. |
| `0x8268CE3C` | `li r7, 0x100` | Materialize immediate/address component: r7, 0x100. |
| `0x8268CE40` | `add r4, r9, r8` | Integer/address arithmetic: r4, r9, r8. |
| `0x8268CE44` | `add r3, r11, r10` | Integer/address arithmetic: r3, r11, r10. |
| `0x8268CE48` | `bl rw__audio__core__CopyWithGainRamp` | Call rw__audio__core__CopyWithGainRamp; place the return address in LR. |
| `0x8268CE4C` | `addi r31, r31, 1` | Integer/address arithmetic: r31, r31, 1. |
| `0x8268CE50` | `lfs f0, 0(r30)` | Load from f0, 0(r30). |
| `0x8268CE54` | `addi r30, r30, 8` | Integer/address arithmetic: r30, r30, 8. |
| `0x8268CE58` | `stfs f0, 0(r29)` | Store the source value to f0, 0(r29). |
| `0x8268CE5C` | `cmplw cr6, r31, r26` | Compare cr6, r31, r26 and update the specified condition register. |
| `0x8268CE60` | `addi r29, r29, 4` | Integer/address arithmetic: r29, r29, 4. |
| `0x8268CE64` | `blt cr6, loc_8268CDFC` | Conditional branch to cr6, loc_8268CDFC according to the named CR/CTR condition. |
| `0x8268CE68` | `lwz r11, 0(r24)` | Load from r11, 0(r24). |
| `0x8268CE6C` | `li r3, 1` | Materialize immediate/address component: r3, 1. |
| `0x8268CE70` | `lwz r10, 0(r25)` | Load from r10, 0(r25). |
| `0x8268CE74` | `stw r11, 0(r25)` | Store the source value to r11, 0(r25). |
| `0x8268CE78` | `stw r10, 0(r24)` | Store the source value to r10, 0(r24). |
| `0x8268CE7C` | `addi r1, r1, 0xB0` | Integer/address arithmetic: r1, r1, 0xB0. |
| `0x8268CE80` | `lfd f31, var_58(r1)` | Load from f31, var_58(r1). |
| `0x8268CE84` | `b __restgprlr_23` | Branch unconditionally to __restgprlr_23. |

#### (c) Rodata constants

| Constant | File offset | Raw bytes | Decoded value/use |
|---|---:|---|---|
| `flt_820ADC00` | `0x000B0C00` | `3C 80 00 00` | IEEE-754 `0.015625f` = `1/64`, the 256-frame block's gain-ramp step factor |

The sample count `0x100` and four-byte float scale (`slwi ...,2`) are instruction
immediates, not rodata.

#### (d) Member-offset/access table

| Base | X360 offset | Access | Faithful PC name |
|---|---:|---|---|
| `self` | `+0x21` | load byte | inherited `PlugIn::mOutputChannels` (loop count) |
| `self` | `+0x28+8*i` | load target | `maTargetGain[i].mfValue` / `mpAttribute[i].mfValue` |
| `self` | `+0x58+4*i` | load/store | `maCurrentGain[i]` |
| `mixer` | `+0x3000C` | load/store pointer | `Mixer::mpSrcBuffer` |
| `mixer` | `+0x30010` | load/store pointer | `Mixer::mpDstBuffer` |
| `src/dst SampleBuffer` | `+0x04` | load pointer | `SampleBuffer::mpSamples` |
| `src/dst SampleBuffer` | `+0x0E` | load halfword | `SampleBuffer::muStride` |

#### (e) Implementation-grade C++ sketch

```cpp
int GainArray::Process(GainArray* self, Mixer* mixer, bool firstPass)
{
    SampleBuffer* src=mixer->mpSrcBuffer;
    SampleBuffer* dst=mixer->mpDstBuffer;
    for (u32 channel=0; channel<self->mOutputChannels; ++channel) {
        const f32 target=self->maTargetGain[channel].mfValue;
        if (firstPass) self->maCurrentGain[channel]=target;
        const f32 current=self->maCurrentGain[channel];
        const f32 step=(target-current)*(1.0f/64.0f);
        CopyWithGainRamp(
            dst->mpSamples + dst->muStride*channel,
            src->mpSamples + src->muStride*channel,
            current, step, 256);
        self->maCurrentGain[channel]=target;
    }
    SampleBuffer* oldSrc=mixer->mpSrcBuffer;
    mixer->mpSrcBuffer=mixer->mpDstBuffer;
    mixer->mpDstBuffer=oldSrc;
    return 1;
}
```

The pointer expressions above are typed `f32*`: the assembly multiplies the stride by
four bytes exactly once.  X64 hazards: the two Mixer buffer pointers and both
`SampleBuffer::mpSamples` pointers widen and must be accessed through `Mixer.h`; do not
retain the X360 `+0x3000C/+0x30010/+0x04` literals in host code.  `Attribute_t` remains
an eight-byte logical record; its host location follows the widened base.  There is no
narrow pointer store, deferred-command cursor return, or GetSize logic here.

### shared no-op body (vtable slots 0 and 1) — `0x8284CB38`

#### (a) Exact signature / dispatch ABI

`off_820AE188[0]` and `[1]` both contain this COMDAT-folded address.  Slot 0 is the
release callback (`r3 = GainArray*`); slot 1 is Event (`r3 = GainArray*`, `r4 = event
id`, `r5 = parameter pointer`).  Neither consumes a register, stack argument, nor
defines a return register.  The slot-1 event contract must therefore be treated as a
no-op using the caller's non-value semantics, not as an invented success/failure code.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x8284CB38.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x8284CB38` | `blr` | Return to the caller through LR. |
| `0x8284CB3C` | `.long 0` | Adjacent exported data/alignment word: 0. |

#### (c) Rodata constants

None.  The `.long 0` is an exported alignment/padding word adjacent to the immediate
return and is included above because it appears in the dossier's assembly field.

#### (d) Member-offset/access table

No member is accessed.

#### (e) Implementation-grade C++ sketch

```cpp
void GainArray::ReleaseEvent() {}
void GainArray::EventEvent(u32, void*) {}
```

X64 hazards: the slot-1 `void*` parameter widens but is unused.  There are no record
strides, narrow pointer stores, deferred-command cursor advances, or GetSize logic.

### zero-return body (vtable slot 2) — `0x827E2F38`

#### (a) Exact signature / dispatch ABI

Called as `u32 GetPpuTicksEvent(const GainArray* self)` with `self` in `r3`, no stack
arguments; it ignores `self` and returns zero in `r3`.

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x827E2F38.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x827E2F38` | `li r3, 0` | Materialize immediate/address component: r3, 0. |
| `0x827E2F3C` | `blr` | Return to the caller through LR. |

#### (c) Rodata constants

None; zero is an instruction immediate.

#### (d) Member-offset/access table

No member is accessed.

#### (e) Implementation-grade C++ sketch

```cpp
u32 GainArray::GetPpuTicksEvent() const { return 0; }
```

X64 hazards: none—no pointers, records, deferred command, or size result occur.

### scalar deleting destructor (vtable slot 3) — `0x826AA9E0`

#### (a) Exact signature / dispatch ABI

MSVC/X360 scalar-deleting destructor: `r3 = GainArray* self`, low bit of `r4 = deleting
flags`, no stack arguments from the caller, return `self` in `r3`.

```cpp
GainArray* ScalarDeletingDestructor(GainArray* self /* r3 */, u32 flags /* r4 */);
```

#### (b) Full instruction-range table

Source: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826AA9E0.json` (`assembly` field).

| Address | Raw mnemonic + operands | Semantic note |
|---|---|---|
| `0x826AA9E0` | `mflr r12` | Copy LR into r12 for prologue preservation. |
| `0x826AA9E4` | `stw r12, var_8(r1)` | Store the source value to r12, var_8(r1). |
| `0x826AA9E8` | `std r31, var_10(r1)` | Store the source value to r31, var_10(r1). |
| `0x826AA9EC` | `stwu r1, back_chain(r1)` | Store with update (r1, back_chain(r1)); allocate/update the stack frame or base register. |
| `0x826AA9F0` | `lis r11, off_820AA810@ha` | Materialize immediate/address component: r11, off_820AA810@ha. |
| `0x826AA9F4` | `mr r31, r3` | Copy register value: r31, r3. |
| `0x826AA9F8` | `addi r11, r11, off_820AA810@l` | Integer/address arithmetic: r11, r11, off_820AA810@l. |
| `0x826AA9FC` | `clrlwi r10, r4, 31` | Shift/rotate/mask or width-normalize: r10, r4, 31. |
| `0x826AAA00` | `cmplwi cr6, r10, 0` | Compare cr6, r10, 0 and update the specified condition register. |
| `0x826AAA04` | `stw r11, 0(r31)` | Store the source value to r11, 0(r31). |
| `0x826AAA08` | `beq cr6, loc_826AAA14` | Conditional branch to cr6, loc_826AAA14 according to the named CR/CTR condition. |
| `0x826AAA0C` | `bl operator_delete` | Call operator_delete; place the return address in LR. |
| `0x826AAA10` | `mr r3, r31` | Copy register value: r3, r31. |
| `0x826AAA14` | `addi r1, r1, 0x60` | Integer/address arithmetic: r1, r1, 0x60. |
| `0x826AAA18` | `lwz r12, var_8(r1)` | Load from r12, var_8(r1). |
| `0x826AAA1C` | `mtlr r12` | Restore/set LR from r12. |
| `0x826AAA20` | `ld r31, var_10(r1)` | Load from r31, var_10(r1). |
| `0x826AAA24` | `blr` | Return to the caller through LR. |

#### (c) Rodata constants

| Constant | File offset | Raw bytes | Decoded value/use |
|---|---:|---|---|
| `off_820AA810` | `0x000AD810` | `82 84 CB 38 82 84 CB 38 82 7E 2F 38 82 68 04 18` | shared destructing/base PlugIn vtable installed before optional delete |

#### (d) Member-offset/access table

| X360 offset | Access | Faithful PC name |
|---:|---|---|
| `+0x00` | store `off_820AA810` | hidden base/destructing vptr |

There is no owned GainArray allocation beyond the object itself.

#### (e) Implementation-grade C++ sketch

```cpp
GainArray* GainArray::ScalarDeletingDestructor(u32 flags)
{
    this->~GainArray();
    if (flags & 1) ::operator delete(this);
    return this;
}
```

X64 hazards: normal host virtual destruction must install the host base vptr and invoke
host `operator delete`; never store the 32-bit X360 vtable address.  No console record
stride, narrow pointer field, deferred-command cursor return, or GetSize calculation is
present.

### PC home (existing TU) coverage gap

The only GainArray PC home is
`b5-decomp/src/GameShared/GameClasses/Sound/Playback/Plugins/GainArray/CgsGainArrayPlugin.cpp`.
It currently contains local definitions for `GetSize`, `CreateInstance`, `Process`, and
a C++ destructor, and correctly recovers `KF_GAIN_RAMP_STEP = 0.015625f`.  It does not
contain a public header, a `PlugIn`-derived host class, a `PlugInDescRunTime` record or
getter, the two shared no-op virtual slots, the zero ticks slot, or definitions for its
declared `gpGainArrayVTable` / `gpGainArrayDtorVTable` externs.

Two source-level corrections are required before that partial TU is implementation
grade (reported only; no source was edited):

- replace its console-shaped local `GainArray`/explicit `mpVtable` and local `MixBuffer`
  model with the committed `PlugIn`, `Mixer`, and `SampleBuffer` types; and
- change both Process channel addresses from `mpData + 4 * muStride * channel` to
  `mpSamples + muStride * channel`.  Since pointer arithmetic already scales by
  `sizeof(f32)`, the current code applies the assembly's `slwi ...,2` a second time.

Its literal `KI_GAIN_ARRAY_INSTANCE_SIZE = 112` must also become host `sizeof`, while
the target/current initialization remains six entries with strides `sizeof(Attribute_t)`
and `sizeof(f32)` respectively.

### descriptor registration gap

The X360 constructor proves the live registration: in
`.ida-exports/BURNOUT_X360_ARTIST.XEX/0x826C17A0.json`,
`0x826C19A4..0x826C19AC` forms `off_82F2E664` in `r4` and `0x826C19B0` calls
`PlugInRegistry::RegisterPlugInRunTime` (immediately after StreamMod at
`0x826C1994..0x826C19A0`).  Raw descriptor bytes at file offset `0x00F31664` identify
`JGA0`, plugInType `4`, six attributes, and callbacks exactly as listed above.

Current
`b5-decomp/src/GameShared/GameClasses/Sound/Playback/RWAC/CgsGenericRwacFactory.cpp`
enumerates console entry 25 only as:
`// 25 "GainArray" off_82F2E664 -- FLAG deferred (same)`; there is no live
`CGS_RWAC_REGISTER(...)` line.  This is not merely a missing table symbol: the partial
TU has no host descriptor getter to register.  The faithful repair is to define a host
`PlugInDescRunTime` whose pointers name the host callbacks and then register its getter
in console order after StreamMod—not to copy any 32-bit descriptor pointer.

## 4. Verification

### Address, offset, and byte checks

- Every function instruction table in this report was generated directly from that function's
  `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x<ADDR>.json` `assembly` field; no
  pseudocode line was promoted into an instruction row.  The first/last addresses were
  rechecked against the JSON body after expansion.  A final exact-list comparison found
  32 source tables, zero residual markers, and zero missing, extra, or reordered
  instruction addresses.
- All descriptor, vtable, float, double, lookup-table, and string bytes in this report
  were read from `IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex` as
  big-endian bytes.  Each listed offset was independently recomputed as
  `0x3000 + vaddr - 0x82000000`; examples: `0x82F2E124 -> 0x00F31124`,
  `0x820AE178 -> 0x000B1178`, `0x82F2E664 -> 0x00F31664`, and
  `0x820ADC00 -> 0x000B0C00`.
- Corrected helper starts came from the containing function ranges and the exact direct
  calls in their `assembly` fields.  The xref chains are: Process/Event/Timer -> named
  helper dossier via `xrefs_from`; `0x8268C9D4`, `0x826A4518`, `0x826C39E8`,
  `0x826DBD78`, and `0x826A46A4` are instructions inside those ranges, not entry
  points.  Their containing JSON dossiers are respectively `0x8268C990`,
  `0x826A43A0`, `0x826C3928`, `0x826DBD40`, and `0x826A45E8`.
- Member offsets were accepted only where a load/store/add-immediate in ARTIST names
  the displacement.  The proposed names were then checked against DecFIGS DWARF for
  StreamMod and against the committed RenderWare `PlugIn.h`, `Mixer.h`, and `Voice.h`
  shapes for both targets.  Pointer-width decisions use names/host types, never a
  transplanted console byte offset.
- Existing-PC coverage statements were checked by searching `b5-decomp/src` for
  `sndplayer1shared.h`, `off_82FFBA0C`, `GainArray`, and the two descriptor names, then
  reading the matching header/TUs and the factory's ordered registration block.
- The ordinary-SndPlayer half of the divergence table is grounded in
  `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82BA0220.json` (GetSize),
  `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82BA6C80.json` (CreateInstance; the
  fixed-tail stores begin at `0x82BA6CC4`), and the
  function/address inventory in `progress/scratch_dossiers/sndplayer1_decode_codex.md`;
  its one explicitly documented exporter gap, EventEvent `0x82BA5C48`, was raw-decoded
  there at XEX file offset `0x00BA8C48`.
- A final raw-data pass re-read all 41 report rows containing XEX bytes and verified
  both the recomputed file offset and every listed byte; no mismatch remained.

### Final BLOCKED list

None.  Every explicitly requested descriptor callback, every identified vtable slot,
the full StreamMod event dispatcher, and every StreamMod-local helper reachable from
the callbacks has a dossier-backed body and is included.  Calls into independent
engine/platform subsystems are identified at their exact call sites and deliberately
terminate the plug-in-local closure; no requested plug-in body is missing, corrupt, or
ambiguous.
