# `rw::audio::core::SndPlayer1` X360 decode

All instruction claims below come from the `assembly` field of the named
`.ida-exports/BURNOUT_X360_ARTIST.XEX/0x<ADDR>.json` file.  Three exporter gaps were
read from `IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex` with
`file_off = 0x3000 + vaddr - 0x82000000`, big-endian: the template initializer at
`0x82B9D368` (file `0x00BA0368`), `SndPlayer1::EventEvent` at `0x82BA5C48`
(file `0x00BA8C48`), and the stream accessor at `0x82BBD948` (file `0x00BC0948`).
ProStreet PDB names are used only where the ARTIST accesses independently attest the
field; the ARTIST offset and behavior always win.

## 1. GetSize

`GetSize` is computed, not constant.  Let `config` be the 12-byte X360
`VoiceStageConfig`, `n = config->mpConstructorParams ? trunc_i32(*(float *)config->mpConstructorParams) : 1`,
and `c = *(u8 *)(config + 8)`:

```text
declickOffset = 0x1D8
requestOffset = align_up(declickOffset + 4*c, 8)
size          = requestOffset + 0x30*n
```

Evidence: `0x82BA0220..0x82BA0260` loads the pointer at config `+0`, converts its
first float with `fctidz/stfiwx`, defaults to one, loads `c` with `lbz +8`, forms
`4*c + 0x1DF`, clears three low bits, and adds `0x30*n`.  `Voice::CreateInstance`
passes the whole config entry in `r3` to descriptor `pGetSize` at
`0x82B6EC98..0x82B6ECA8`; its plug-in placements are 16-aligned, so the cleared
expression is exactly `0x1D8` relative to this instance.

Hazards:

- The X360 literals `0x30` and the fixed `0x1D8` extent contain 32-bit pointers.
  They are not a valid x64 allocation formula.
- There is no range/NaN/sign validation.  The full converted `n` sizes the object,
  while CreateInstance later stores only its low byte as `mMaxRequests`.  The known
  constants `1.0f` and `2.0f` are safe.
- The console formula is coupled to CreateInstance's two relative offsets.  The PC
  implementation must calculate all three from one host-layout helper.

## 2. CreateInstance instance layout table

Register contract: `r31 = self`; `r29 = trunc_i32(*ctorParams)` or one when `r4 == 0`
(`0x82BA6C8C..0x82BA6CB4`).  Before this descriptor callback, generic
`PlugIn::CreateInstance` has initialized the base and passes `config+0` as `r4`
(`0x82B6A828..0x82B6A870`).  The callback returns one only after its private allocation
and timer registration both succeed (`0x82BA6D14..0x82BA6E24`).

| Offset | Field | Init value/source |
|---:|---|---|
| `+0x00` | vfptr | `0x8217F344`; raw initializer `0x82B9D38C..0x82B9D398` (file `0x00BA038C`). |
| `+0x04` | `System *mpSystem` | System singleton, generic `PlugIn::CreateInstance` `0x82B6A84C..0x82B6A858`. |
| `+0x08` | `Voice *mpVoice` | Generic caller's `r4`, `0x82B6A83C`. |
| `+0x0C` | attribute-array pointer | `self + 0x28`, raw initializer `0x82B9D3A0..0x82B9D3AC`. |
| `+0x10` | runtime descriptor | Generic caller's descriptor, `0x82B6A844`. |
| `+0x14` | latency samples | `0.0f`, `0x82B6A828..0x82B6A840`. |
| `+0x18` | decay samples | `0.0f`, `0x82B6A840`. |
| `+0x1C` | CPU ticks | zero, `0x82B6A848`. |
| `+0x20` | input channels | Previous stage's output-channel byte, `0x82B6A854`. |
| `+0x21` | output channels | Current config `+8` low byte, `0x82B6A85C..0x82B6A860`. |
| `+0x22..+0x27` | base padding | No initialization store found. |
| `+0x28` | attribute 0, current request handle | `0.0f`, `0x82BA6D58..0x82BA6D70`. |
| `+0x2C` | unused half of attribute-0 union slot | No initialization store found; all ARTIST uses of attribute 0 are `lfs/stfs +0x28`. |
| `+0x30` | attribute 1, sample position | `0.0` as an eight-byte store, `0x82BA6D78..0x82BA6D84`. |
| `+0x38` | attribute 2, sample length | `0.0` as an eight-byte store, `0x82BA6D78..0x82BA6D80`. |
| `+0x40` | timer collection node | TimerHandle ctor first stores null (`0x82B6BEB8`); `Collection::AddItem` replaces it with the linked node on registration (`0x82B6E220..0x82B6E224`). |
| `+0x44` | timer callback | `SndPlayer1::RwacTimerClient` (`0x82BA6980`), stored by AddTimer at `0x82B6EBE4`. |
| `+0x48` | timer context | `self`, AddTimer `0x82B6EBE8`. |
| `+0x4C` | timer name | `"SndPlayer"`, ctor first uses `"Unknown"`; AddTimer overwrites at `0x82B6EBEC`. |
| `+0x50` | timer CPU ticks | zero, TimerHandle ctor `0x82B6BEC0` and AddTimer `0x82B6EBF8`. |
| `+0x54` | timer stage | ctor value 3, then registration value 1 (`0x82B6BEC4`, `0x82B6EBF0`). |
| `+0x55` | timer visibility | 1, AddTimer `0x82B6EBF4`. |
| `+0x56..+0x57` | timer padding | No initialization store found. |
| `+0x58` | `RequestExternal *mpRequestExternal` | Private allocation base `+4`, `0x82BA6D24..0x82BA6D30`. |
| `+0x5C + 0x10*i` | `SndPlayer1FeedDesc[i].pChunkInfo`, `i=0..19` | null, loop `0x82BA6DA4..0x82BA6DE0`. |
| `+0x69 + 0x10*i` | `SndPlayer1FeedDesc[i].feedState` | zero, same loop.  Other bytes of each 16-byte feed record are not initialized here. |
| `+0x19C` | `Decoder *mpLoadedDecoder` | null, `0x82BA05A0..0x82BA05AC` at each Process entry; CreateInstance has no store. |
| `+0x1A0` | current request handle | `0.0f`, `0x82BA6DA8`. |
| `+0x1A4` | current request sample rate | `48000.0f`, `0x82BA6D98..0x82BA6DB0`. |
| `+0x1A8` | current request samples played | zero, `0x82BA6DAC`. |
| `+0x1AC` | current request sample count | zero, `0x82BA6DB4`. |
| `+0x1B0` | `float *mpRequestHandle` / private allocation base | `System::Alloc(0x50*n + 4, ..., 16, 0)` result, `0x82BA6CEC..0x82BA6D1C`; pointed float is set to `0.0f` at `0x82BA6D60..0x82BA6D88`. |
| `+0x1B4` | last request handle processed | `0.0f`, `0x82BA6D90`. |
| `+0x1B8` | last request handle successfully processed | `0.0f`, `0x82BA6DA0`. |
| `+0x1BC` | previous sample rate | `48000.0f`, `0x82BA6DB8`. |
| `+0x1C0` | requested samples | Not initialized by CreateInstance; every PreProcess overwrites its halfword. |
| `+0x1C2` | declick-buffer relative offset | `0x1D8` for the 16-aligned instance, `0x82BA6CC4..0x82BA6CF4`. |
| `+0x1C4` | `RequestInternal[]` relative offset | `align_up(0x1D8 + 4*outputChannels, 8)`, `0x82BA6CC4..0x82BA6D10`. |
| `+0x1C6` | maximum channels | Copy of output channels at `+0x21`, `0x82BA6D5C..0x82BA6D6C`. |
| `+0x1C7` | next free request | zero, `0x82BA6D9C`. |
| `+0x1C8` | next request to free | zero, `0x82BA6D94`. |
| `+0x1C9` | current request index | zero, `0x82BA6D8C`. |
| `+0x1CA` | maximum requests | Low byte of full `n`, `0x82BA6D24..0x82BA6D2C`. |
| `+0x1CB` | declick offsets gathered | zero, `0x82BA6DC0`. |
| `+0x1CC` | remaining declick samples | zero, `0x82BA6DBC`. |
| `+0x1CD` | next feed slot to fill | zero, `0x82BA6DC4`. |
| `+0x1CE` | next feed slot to free | zero, `0x82BA6DC8`. |
| `+0x1CF` | ARTIST-only/unknown byte | zero, `0x82BA6DCC`; no semantic reader was found in the decoded paths. |
| `+0x1D0` | timer-added flag | zero before registration (`0x82BA6CF0`), one only after AddTimer returns zero (`0x82BA6E0C..0x82BA6E24`); ReleaseEvent tests this exact byte. |
| `+0x1D1..+0x1D7` | fixed-tail alignment | No initialization store found. |
| `+0x1D8` | `float declickBuffer[outputChannels]` | Not initialized by CreateInstance; Process captures the last emitted sample per channel at `0x82BA0B78..0x82BA0BB8`. |
| `+requestOffset + 0x30*i` | `RequestInternal[i]`, `i=0..n-1` | CreateInstance initializes only its state byte at record `+0x2A` to FREE/0 (`0x82BA6D38..0x82BA6D54`). |

The last two regions are within the GetSize allocation.  The separate allocation is
`float requestHandleCounter` followed at byte `+4` by `n` records of console stride
`0x50`; CreateInstance does not blanket-zero those records.

| Dynamic record offset | Field attested later | First relevant ARTIST writer/read |
|---:|---|---|
| `RequestInternal +0x00` | `double startTime` | PlayHandler `0x82BA4230..0x82BA4234`; Process `lfd` at `0x82BA0700`. |
| `+0x08` | `Decoder *pDecoder` | PlayHandler clears at `0x82BA422C`; StartRequest stores factory result at `0x82BA64B0..0x82BA64B8`. |
| `+0x0C` | request handle | PlayHandler `0x82BA4224..0x82BA4228`. |
| `+0x10` | sample rate | UnpackHeader `0x82B9BF80..0x82B9BFA0`. |
| `+0x14` | number of samples | UnpackHeader `0x82B9BFC0..0x82B9BFCC`. |
| `+0x18` | loop start (`-1` means none) | UnpackHeader `0x82B9BFD0..0x82B9BFF0`. |
| `+0x1C/+0x20/+0x24` | player/decoder/stream skip counters | Process reads them at `0x82BA0870`, `0x82BA0938..0x82BA0944`; CreateInstance does not initialize them. |
| `+0x28` | decoder scratch-instance size | StartRequest copies `Decoder+0x20` at `0x82BA64BC..0x82BA64C8`. |
| `+0x2A` | request state | Create FREE/0; PlayHandler writes QUEUED/1 at `0x82BA4254`; timer and Process advance it. |
| `+0x2B` | channel count | UnpackHeader stores decoded six-bit value plus one at `0x82B9BF60..0x82B9BF7C`. |
| `RequestExternal +0x00` | stream file offset | PlayHandler `0x82BA4238..0x82BA4248`. |
| `+0x08` | sample/payload pointer | UnpackHeader advances past the packed header and stores it at `0x82B9C050..0x82B9C05C`. |
| `+0x0C/+0x10` | loop stream offset / resident sample count | UnpackHeader `0x82B9BFF4..0x82B9C04C`. |
| `+0x14/+0x18` | samples/bytes fed | PlayHandler clears both at `0x82BA4258..0x82BA425C`; SubmitChunk increments `+0x14` at `0x82BA4660..0x82BA4670`. |
| `+0x1C/+0x20/+0x24/+0x28/+0x2C` | loop filename, StreamPool, stream handle, Stream, streamer request id | PlayHandler clears `+0x1C/+0x24/+0x2C` and fills the streaming fields at `0x82BA42F8..0x82BA438C`. |
| `+0x30/+0x34/+0x38/+0x3C/+0x40/+0x44` | next/loop chunks and seek state | Not initialized by CreateInstance; consumed by the stream/seek helpers. |
| `+0x48/+0x49` | codec index / play type | UnpackHeader stores them at `0x82B9BF4C..0x82B9BFB4`. |
| `+0x4A/+0x4B/+0x4C` | latest feed slot / expel mode / new-feed flag | PlayHandler stores expel mode at `0x82BA424C..0x82BA4250`; StartRequest and SubmitChunk use the other bytes. |

There is no decoder-registry lookup in CreateInstance.  It allocates request storage,
initializes state, and registers the timer only.

## 3. PreProcess contract

The exact body is four instructions (`0x82B9C2D8.json`):

```text
r3 = SndPlayer1 *plugin
r4 = Mixer *mixer                 (ignored)
r5 = alreadyProcessed/discontinuity (ignored)
r6 = requestedCount

sth r6, +0x1C0(plugin)
return 0
```

Thus it stows the low 16 bits of the request and returns zero as the count for the
next lower stage.  In the proven `Mixer::ProcessInputPlugIns` cascade SnP1 is source
stage 0, so there is no lower stage that needs its return; Process consumes the stowed
count.  The caller caps its normal request to 256, so the halfword is lossless on the
voice path.

## 4. Process contract + Mixer field cross-check

Entry mapping is `r31 = SndPlayer1 *` and `r24 = Mixer *`
(`0x82BA0574..0x82BA0578`).  It returns only buffer status zero or one.

| Path | Behavior and return |
|---|---|
| Pending declick | If `+0x1CC` and `+0x1CB` are both nonzero, tail-call-like dispatch to Declick (`0x82BA057C..0x82BA0598`).  Declick writes a linear ramp from each saved last sample to zero, publishes `min(remainingDeclick, requested)`, swaps dst/src, decrements `+0x1CC`, and returns 1 (`0x82B9C1C0..0x82B9C2D4`). |
| No active request/feed | It scans request state and feed slots; FREE/COMPLETE requests are unavailable, zero-length requests are completed and advanced (`0x82BA05C8..0x82BA0658`).  Final return is 0 only when no output and no skipped samples exist while `mSamplesRequested != 0` (`0x82BA0B20..0x82BA0B54`). |
| Format handshake | If request sample rate `RequestInternal+0x10` differs from `+0x1BC`, or request channels `+0x2B` differ from plug-in `+0x21`, it publishes zero samples plus the new rate/channels, updates the plug-in's previous format, and returns 1 (`0x82BA0664..0x82BA0680`, `0x82BA0BD0..0x82BA0C0C`). |
| Future start | `WaitForStartTime` compares request start time with `Mixer+0x30000`.  A start at least 256 output frames away returns unavailable/0.  A nearer future start zero-fills that many frames in the dst descriptor, publishes/swaps it, and returns 1 (`0x82BA06FC..0x82BA07E4`; helper `0x82B9C148..0x82B9C1BC`).  A reached start clears the request's start time and decodes. |
| Decode | It temporarily carves `align_up(RequestInternal+0x28,128)` bytes from the System stack allocator, loads `RequestInternal+0x08` into `+0x19C`, derives feed availability, skips up to `RequestInternal+0x1C` samples via Decode calls capped at 256, then requests `min(+0x1C0, available-skip)` into the Mixer's dst descriptor (`0x82BA07EC..0x82BA08F4`). |
| Publish/account | The Decode return is written to `Mixer+0x30020`; dst/src descriptors are swapped; request channels/rate go to `+0x3002C/+0x30024`.  Played position and feed counters advance by decoded output plus skipped samples (`0x82BA08F8..0x82BA0988`).  Loop/end and feed-slot rollover are handled before scratch-top restoration (`0x82BA098C..0x82BA0B1C`). |
| Successful samples | For each of `min(Mixer.mbChannelCount, +0x1C6)` channels, Process reads sample `produced-1` using descriptor `mpSamples + 4*(muStride*channel + produced-1)` and saves it in the dynamic declick array; it sets `+0x1CB=1` and returns 1 (`0x82BA0B58..0x82BA0BC4`). |
| Successful zero-sample work | Skip-only work or a zero requested count explicitly publishes `mNumSamples=0` and returns 1 (`0x82BA0B38..0x82BA0BCC`).  On status 0, `mNumSamples` is not republished and must be ignored by the caller. |

The decoder receives the descriptor that is in the Mixer's dst slot before the call.
Immediately afterward Process swaps `+0x3000C` and `+0x30010`, so the filled descriptor
is the published src slot on return (`0x82BA08F8..0x82BA0910`).  All channel writes use
SampleBuffer `+4` as the float base and `lhz +0x0E` as the per-channel sample stride
(`Process` last-sample capture at `0x82BA0B8C..0x82BA0BB4`; zero fill at
`0x82BA076C..0x82BA0788`; `Decoder::Decode` at `0x82B67AB0..0x82B67AEC`).

| X360 offset | ARTIST use | `Mixer.h` name/type | Cross-check |
|---:|---|---|---|
| `+0x30000` | Start-time comparison | `f64 mdStreamTime` | Match. |
| `+0x3000C` | Published src slot / swap half | `SampleBuffer *mpSrcBuffer` | Match. |
| `+0x30010` | Decode/zero/declick destination before swap | `SampleBuffer *mpDstBuffer` | Match. |
| `+0x30018` | Format pointer; helper reads its `f32 +0x0C` sample rate | `MixerExecuteParams *mpFormat` | Match. |
| `+0x30020` | Published sample count | `u32 mNumSamples` | Match. |
| `+0x30024` | Published source sample rate | `f32 mfSampleRate` | Match. |
| `+0x30028` | Start-time sample scaling | `f32 mfResampleGain` | Match. |
| `+0x3002C` | Published channel count | `u8 mbChannelCount` | Match. |
| SampleBuffer `+0x04` | Planar float base | `f32 *mpSamples` | Match. |
| SampleBuffer `+0x0E` | Channel stride in samples | `u16 muStride` | Match. |

No Mixer-header mismatch was found.

## 5. Event vtable dump + handler decode

The raw initializer installs `0x8217F344`.  Raw XEX file `0x00182344` contains four
big-endian words `82BA4178 82BA5C48 82BDD2D0 82B9EAF8`.  The next address,
`0x8217F354`, is separately installed by the adjacent VuMeter initializer at raw
`0x82B9D3EC..0x82B9D3F8`, proving the SnP1 table ends after four slots.

| Slot | Address | Name |
|---:|---:|---|
| 0 | `0x82BA4178` | `rw::audio::core::SndPlayer1::ReleaseEvent` |
| 1 | `0x82BA5C48` | `rw::audio::core::SndPlayer1::EventEvent` (raw recovery; exact JSON missing) |
| 2 | `0x82BDD2D0` | `rw::audio::core::SndPlayer1::GetPpuTicksEvent` |
| 3 | `0x82B9EAF8` | `rw::audio::core::SndPlayer1::vector deleting destructor` |

`EventEvent(self,event,param)` is raw-decoded over `0x82BA5C48..0x82BA607C`:

| Event | Handler behavior |
|---:|---|
| 0 `PLAY` | Expands the legacy 40-byte parameters into the newer form: copies start time, stream offset, path, RAM pointer, stream-pool GUID and expel mode, and supplies zero seek time/table (`0x82BA5ED4..0x82BA5F24`).  It then follows the common PLAY1 enqueue path. |
| 1 `STOP` | Appends the 8-byte `{StopHandler,self}` command to the System ring (`0x82BA5C78..0x82BA5CA4`). |
| 2 `ISREQUESTDONE` | Writes `param+4` as 0.0/1.0.  Exact true condition is `handle < attr0`, or `attr2(double)==0` while either `handle == attr0` or `lastSuccessful < handle <= lastProcessed`; otherwise false (`0x82BA5CA8..0x82BA5D08`). |
| 3 `GETREQUESTBUFFERED` | Scans the request ring for `param+0` handle.  It writes byte/sample buffering to `param+4` and completion to `param+8`; resident requests report 0/true.  Streamed requests start from `RequestExternal+0x18`, optionally add stream accessor `0x82BBD940` or raw `0x82BBD948`, then report complete if request state is 3 or stream state is 2 (`0x82BA5D0C..0x82BA5E90`).  No-match output remains 0/false. |
| 4 `MODIFYSTARTTIME` | Appends a 24-byte `{ModifyStartTimeHandler,self,double param[0],float param[8]}` command (`0x82BA5E94..0x82BA5ED0`). |
| 5 `PLAY1` | Uses the expanded parameter block directly (`0x82BA5F28`). |

The common PLAY/PLAY1 path increments the float counter behind `+0x1B0`, wraps values
above `4194304.0f` to zero (raw `0x820B56EC`, file `0x000B86EC`), publishes the handle
back to the parameter block, and appends a variable-size, four-byte-aligned PlayCommand
whose fixed portion contains handler/self, three doubles, stream GUID, RAM/seek pointers,
size, expel mode and handle, followed by the optional path string
(`0x82BA5F2C..0x82BA6068`).

Other slots are short: ReleaseEvent calls StreamLostCallback, removes the timer only
when `+0x1D0 == 1`, and frees the `+0x1B0` allocation (`0x82BA4178..0x82BA41D0`);
GetPpuTicksEvent returns word `+0x50` (`0x82BDD2D0..0x82BDD2D4`).  The deleting
destructor tears down the TimerHandle, installs the base vtable sentinel, optionally
deletes, and returns self (`0x82B9EAF8..0x82B9EB50`).

## 6. Decoder interaction + ctor-param float pointer role

The data path is fully separated from construction:

1. `Voice::CreateInstance` passes config `+0` through generic PlugIn creation as the
   descriptor constructor pointer (`0x82B6EE00..0x82B6EE14`, `0x82B6A85C..0x82B6A870`).
   SnP1 converts only its first float.  It is `ConstructorParams::maxRequests`: it sizes
   `RequestInternal[n]`, allocates `0x50*n+4`, controls request-ring loops, and is stored
   at `+0x1CA`.  It is not the channel count.
2. Channel count independently comes from config byte `+8`, is written to PlugIn
   `+0x21`, then copied to `+0x1C6`.  Therefore splice configs
   `{&1.0f,'SnP1',1}` and `{&2.0f,'SnP1',2}` mean respectively one request/one channel
   and two requests/two channels.  The matching numbers are coincidental, not an alias.
3. PLAY/PLAY1 queues PlayHandler.  PlayHandler reserves a FREE request, copies command
   fields, and calls UnpackHeader on the RAM/header pointer (`0x82BA4218..0x82BA4274`).
   UnpackHeader reads 4 version bits, 4 codec bits, 6 channel bits (stored plus one),
   18 sample-rate bits, 2 play-type bits, loop flag, 29 sample-count bits, and optional
   32-bit loop/resident fields; it stores the pointer immediately after that packed
   header at `RequestExternal+0x08` (`0x82B9BF08..0x82B9C05C`).
4. The timer changes QUEUED request state 1 to FEEDING state 2 only after StartRequest
   succeeds (`0x82BA6B34..0x82BA6B58`).  StartRequest locks the System, gets its decoder
   registry, maps `RequestExternal.codec` through `dword_82174578`, calls
   GetDecoderHandle, then DecoderFactory with `(handle,numChannels,20,System)` and stores
   the returned Decoder at `RequestInternal+0x08` (`0x82BA6470..0x82BA64B8`).
5. SubmitChunk takes the payload/stream chunk, allocates a feed slot, calls
   `Decoder::Feed`, and records the returned decoder request handle in feed `+0x0C`
   (`0x82BA4570..0x82BA4670`).  Process later loads the same Decoder and calls
   `Decoder::Decode(decoder, Mixer.mpDstBuffer, count)` (`0x82BA0814..0x82BA08F4`).

The eight decoder GUID words visible before the adjacent string are at raw XEX file
`0x00177578`:

| Codec index | GUID bytes / fourcc |
|---:|---|
| 0 | `58 61 73 30` / `Xas0` |
| 1 | `45 4C 33 30` / `EL30` |
| 2 | `50 36 42 30` / `P6B0` |
| 3 | `45 58 6D 30` / `EXm0` |
| 4 | `58 61 73 31` / `Xas1` |
| 5 | `45 4C 33 31` / `EL31` |
| 6 | `4C 33 32 50` / `L32P` |
| 7 | `4C 33 32 53` / `L32S` |

StartRequest performs no bounds check before `lwzx` (`0x82BA647C..0x82BA6494`); index
8 is already adjacent `"SndPlayer1 RequestHandle..."` data at `0x82174598`, so valid
assets must supply a supported codec index.

The three attributes are also independently attested: timer callback writes current
request handle as `f32 +0x28`, sample position as `f64 +0x30`, and sample length as
`f64 +0x38` (`0x82BA69EC..0x82BA6A4C`).  They are not decoder handles or constructor
parameters.

As descriptor type 0, SnP1 is the source-stage boundary selected by
`Voice::CreateInstance` (`0x82B6EDC8..0x82B6EDDC`).  In every splice voice it is stage
0: PreProcess captures the requested chunk size, and Process is the first producer that
turns decoder feeds into a published Mixer source buffer.

## 7. Stream-mod shared-callee notes

Raw descriptor `off_82F2E124` at file `0x00F31124` is `JStr`, with its own GetSize,
CreateInstance, PreProcess and Process.  No JStr body was decoded here.  A mechanical
intersection of direct branches in the two families' dossier `assembly` fields shows
parallel implementations sharing these engine services (compiler save/restore helpers
omitted):

| Shared callee | SnP1 call evidence | JStr call evidence |
|---|---|---|
| `BitGetter::GetBits` `0x82680460` | UnpackHeader `0x82B9BF4C` onward | UnpackHeader `0x8268C9D4` onward |
| `Decoder::Release` `0x82691528` | StartRequest `0x82BA6530` | StartRequest `0x826DBE08` |
| `XMemCpy` `0x82926BA0` | PlayHandler `0x82BA43A4` | PlayHandler `0x826A4518` |
| `XMemSet` `0x82926FD0` | Process `0x82BA0788` | Process `0x826A4968` |
| `Decoder::Feed` `0x82B67920` | SubmitChunk `0x82BA4658` | SubmitChunk `0x826C39E8` |
| `Decoder::Decode` `0x82B67A50` | Process `0x82BA08D8/0x82BA08F4` | Process `0x826A4A60` |
| `DecoderRegistry::GetDecoderHandle` `0x82B67C80` | StartRequest `0x82BA6494` | StartRequest `0x826DBD9C` |
| `DecoderRegistry::DecoderFactory` `0x82B6C778` | StartRequest `0x82BA64AC` | StartRequest `0x826DBDB4` |
| `System::GetDecoderRegistry` `0x82B6DD78` | StartRequest `0x82BA6478` | StartRequest `0x826DBD80` |
| `System::Lock/Unlock` `0x82B6BCC8/0x82B6BCF0` | StartRequest `0x82BA6470/0x82BA6540` | StartRequest `0x826DBD78/0x826DBE18` |
| `System::Alloc/Free` `0x82B6BE18/0x82B6BE48` | Create `0x82BA6D14`, Release `0x82BA41BC` | Create `0x826EA5AC`, Release `0x826C3854` |
| `Voice::ExpelAfterDecay` `0x82B6BFD8` | RemoveRequest `0x82BA055C` | RemoveRequest `0x826A46A4` |
| `TimerManager::AddTimer` `0x82B6EB88` | Create `0x82BA6E08` | Create `0x826EA7A4` |
| `System::RemoveTimer` `0x82B6EB80` | Release `0x82BA41A4` | Release `0x826C3810` |

There is no direct call from one class family's dossiers into the other's implementation;
the visible relationship is duplicated player machinery over the shared decoder/System
services, not a base SnP1 call-through.

## 8. Full callee list

This includes fixed callees, deferred-handler targets, vtable targets and caller/context
functions whose assembly was used above.  `N` means there is no exact-address JSON; a
symbol shown for an `N` row is the name present at its call site or recovered as noted.

| Address | Function / role | JSON |
|---:|---|:---:|
| `0x82680460` | `BitGetter::GetBits` | Y |
| `0x82691528` | `Decoder::Release` | Y |
| `0x82926BA0` | `XMemCpy` | Y |
| `0x82926FD0` | `XMemSet` | Y |
| `0x82AD5078` | `STUB` (TimerHandle destructor target) | Y |
| `0x82B67920` | `Decoder::Feed` (call-site name) | N |
| `0x82B679D8` | `Decoder::AdvanceDecodeState` | Y |
| `0x82B67A50` | `Decoder::Decode` | Y |
| `0x82B67C80` | `DecoderRegistry::GetDecoderHandle` | Y |
| `0x82B6A818` | `PlugIn::CreateInstance` (caller/context) | Y |
| `0x82B6BA68` | `StreamPool::GetInstance` (call-site name) | N |
| `0x82B6BAB0` | `StreamPool::AcquireStream` | Y |
| `0x82B6BCC8` | `System::Lock` | Y |
| `0x82B6BCF0` | `System::Unlock` | Y |
| `0x82B6BE18` | `System::Alloc` (call-site name) | N |
| `0x82B6BE48` | `System::Free` | Y |
| `0x82B6BEA8` | `TimerHandle::TimerHandle` | Y |
| `0x82B6BFD8` | `Voice::ExpelAfterDecay` | Y |
| `0x82B6C490` | `Collection::AddCapacity` | Y |
| `0x82B6C778` | `DecoderRegistry::DecoderFactory` (call-site name) | N |
| `0x82B6DD78` | `System::GetDecoderRegistry` | Y |
| `0x82B6E1C0` | `Collection::AddItem` | Y |
| `0x82B6EB80` | `System::RemoveTimer` | Y |
| `0x82B6EB88` | `TimerManager::AddTimer` | Y |
| `0x82B6EC50` | `Voice::CreateInstance` (caller/context) | Y |
| `0x82B9BF08` | `SndPlayer1::UnpackHeader` | Y |
| `0x82B9C068` | `SndPlayer1::SetSeekData` | Y |
| `0x82B9C148` | `SndPlayer1::WaitForStartTime` | Y |
| `0x82B9C1C0` | `SndPlayer1::Declick` | Y |
| `0x82B9C2E8` | `SndPlayer1::AdvanceCurrentRequest` | Y |
| `0x82B9D368` | `PlugIn::Initialize<SndPlayer1>` (raw file `0x00BA0368`) | N |
| `0x82B9EAF8` | `SndPlayer1::vector deleting destructor` | Y |
| `0x82BA0268` | `SndPlayer1::FeedCleanup` | Y |
| `0x82BA0380` | `SndPlayer1::GetFeedSlot` | Y |
| `0x82BA03D0` | `SndPlayer1::ModifyStartTimeHandler` | Y |
| `0x82BA4080` | `SndPlayer1::RequestCleanup` | Y |
| `0x82BA4100` | `SndPlayer1::StreamLostCallback` | Y |
| `0x82BA4178` | `SndPlayer1::ReleaseEvent` | Y |
| `0x82BA41D8` | `SndPlayer1::PlayHandler` | Y |
| `0x82BA44E0` | `SndPlayer1::StopHandler` | Y |
| `0x82BA4570` | `SndPlayer1::SubmitChunk` | Y |
| `0x82BA5C48` | `SndPlayer1::EventEvent` (raw file `0x00BA8C48`) | N |
| `0x82BA6080` | `SndPlayer1::StreamNextChunk` | Y |
| `0x82BA6160` | `SndPlayer1::HandleLoopStart` | Y |
| `0x82BA6248` | `SndPlayer1::HandleSampleEnd` | Y |
| `0x82BA6438` | `SndPlayer1::StartRequest` | Y |
| `0x82BA6980` | `SndPlayer1::RwacTimerClient` | Y |
| `0x82BBD940` | Stream `+0x0C` accessor; exact dossier label is the unrelated COMDAT alias `AptNativeHash::GetPrototype` | Y |
| `0x82BBD948` | unnamed Stream request-record `+0x138` accessor (raw file `0x00BC0948`) | N |
| `0x82BBD990` | `rw::core::filesys::Stream::GetState` | Y |
| `0x82BBD9D0` | `rw::core::filesys::Stream::GetRequestState` | Y |
| `0x82BC09B0` | unnamed stream request helper | Y |
| `0x82BDD2D0` | `SndPlayer1::GetPpuTicksEvent` | Y |
| `0x82C08EB4/0x82C08F04` | `__save/__restgprlr_15` | Y/Y |
| `0x82C08ED8/0x82C08F28` | `__save/__restgprlr_24` | Y/Y |
| `0x82C08EDC/0x82C08F2C` | `__save/__restgprlr_25` | Y/Y |
| `0x82C08EE0/0x82C08F30` | `__save/__restgprlr_26` | Y/Y |
| `0x82C08EE4/0x82C08F34` | `__save/__restgprlr_27` | Y/Y |
| `0x82C08EE8/0x82C08F38` | `__save/__restgprlr_28` | N/Y |
| `0x82C08EEC/0x82C08F3C` | `__save/__restgprlr_29` | Y/Y |
| `0x82C08FB0` | `operator delete` (call-site name) | N |

The two data-dependent decoder callbacks inside `Decoder::Decode` have no single fixed
target; the wrapper loads its decode callback from `Decoder+0x14` and invokes it via
`bctrl` at `0x82B67B34..0x82B67B48` / `0x82B67C44..0x82B67C58`.

## 9. PC-homing recommendation

- Home this as vendor middleware, with a typed
  `rw/audio/core/plugins/SndPlayer1.h` plus `SndPlayer1.cpp`, deriving from `PlugIn` and
  containing typed `RequestInternal`, `RequestExternal`, `SndPlayer1FeedDesc`, event
  parameter and command records.  Keep descriptor callbacks thin wrappers over those
  methods; let the host compiler create the vtable.
- Widen every address-bearing member: PlugIn vfptr/System/Voice/attribute/descriptor;
  TimerHandle node/callback/context/name; `mpRequestExternal`; each feed's ChunkInfo and
  Stream pointers; `mpLoadedDecoder`; `mpRequestHandle`; and RequestExternal's sample,
  path, StreamPool, stream handle, Stream, chunk and seek pointers.  Counters, GUIDs,
  floats, state bytes, the 16-bit relative offsets and sample counts do not widen.
- Do not use console `0x50*n+4` on x64.  `base+4` places a double-leading
  RequestExternal at only four-byte alignment.  Use a typed/aligned storage header or
  separate allocations and `sizeof(RequestExternal)`.
- Do not import the ProStreet fixed extent unchanged.  ARTIST explicitly has unknown
  byte `+0x1CF` and timer flag `+0x1D0`; ProStreet names the timer flag at `+0x1CF`.
  Preserve the ARTIST extra byte as unknown until a reader names it.
- Implement one `ComputeLayout(config)` used by both GetSize and CreateInstance:
  start the declick array after the naturally widened host object (preserving required
  alignment), add `sizeof(float)*outputChannels`, align for `RequestInternal`, then add
  `sizeof(RequestInternal)*maxRequests`.  Store/check the resulting relative offsets;
  assert they fit the retained 16-bit fields and the Voice stage's 16-bit size.
- Therefore the PC GetSize policy is **host computed size**, not the console literal
  formula and not plain `sizeof(SndPlayer1)`.  This is required because both the fixed
  object and `RequestInternal::pDecoder` widen, while the variable request count remains
  part of the instance allocation.
