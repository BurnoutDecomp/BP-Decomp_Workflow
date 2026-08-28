# `rw::audio::core::Dac` X360 decode and PC-homing report

This report records the recovered `Dac` plug-in implementation from
`BURNOUT_X360_ARTIST.XEX`. The X360 `assembly` listings are the behavioural and ABI
authority. Names and declaration shapes come from the RenderWare audio headers already
reconstructed in this tree and from the `rw::audio::core` records in
`IDA Files/ProStreet08Milestone.pdb`; those names are used only where the ARTIST stores
or loads attest the corresponding offset.

No `Dac.h` or `Dac.cpp` exists in the current PC tree. The two helpers used by the final
copy path, `ClipFloats` and `ReOrderRwAudioCoreToWave`, are already homed in
`vendor/renderware/include/rw/audio/core/MixKernels.h` and
`vendor/renderware/src/rw/audio/core/MixKernels.cpp`. The console-specific output leaf
has a PC counterpart in `src/GameShared/GameClasses/System/PC/CgsAudioOutputPC.*`, but
it is not yet connected to an audio-core `Dac`.

## 1. Recovered declarations and fixed values

The declaration shapes below are the implementation-grade forms indicated by the PDB
and by the actual register usage. `PlugInDescRunTime` stores callbacks as opaque slots,
so the first line for each descriptor callback also states the effective dispatch ABI.

```cpp
class Dac : public PlugIn
{
public:
    enum Mode {
        MODE_MONO = 0, MODE_STEREO = 1, MODE_QUAD = 2,
        MODE_5POINT1 = 3, MODE_7POINT1 = 4, MODE_PROLOGIC2 = 5,
        MODE_MAX = 6
    };
    enum Attribute {
        ATTRIBUTE_GETMODE = 0,
        ATTRIBUTE_GETSAMPLERATE = 1,
        ATTRIBUTE_GETLATENCY = 2,
        ATTRIBUTE_MAX = 3
    };
    enum EventId {
        EVENT_ENUMERATEMODE = 0,
        EVENT_SETMODE = 1,
        EVENT_SETSAMPLERATE = 2,
        EVENT_START = 3,
        EVENT_STOP = 4
    };
    enum ProcessingMode {
        PROCESSINGMODE_REALTIME = 0,
        PROCESSINGMODE_OFFLINE = 1,
        PROCESSINGMODE_MAX = 2
    };
    enum PACKET_STATUS {
        PACKET_FREE = 0,
        PACKET_READY = 1,
        PACKET_SUBMITTED = 2
    };

    static bool CreateInstance(PlugIn* pPlugIn, void* pConstructorParams);
    static unsigned GetSize(const VoiceStageConfig* pConfig);
    static PlugInDescRunTime* GetPlugInDescRunTime();
    void EventEvent(EventId eventId, void* pParameterBuffer);
    static int StartHandler(Command* pCommand);
    static int StopHandler(Command* pCommand);
    void RampOutput(float* pBuffer, int numFrames, bool rampUp);
    static BufferStatus Process(Dac* self, AudioProcessContext* context);
    void XenonDownMix();
    BufferStatus Mix();
    void XenonThread();
};

struct DacEnumerateModeParams {
    float mode;                 // +0x00
    float isSupported;          // +0x04
    const char* pModeName;      // +0x08 on X360
};
struct DacSetModeParams       { float mode;       }; // +0x00
struct DacSetSampleRateParams { float sampleRate; }; // +0x00

struct DacCommand {
    int (*pHandler)(DacCommand*); // +0x00 on X360
    Dac* pObject;                 // +0x04 on X360
};
struct DacSetModeCommand : DacCommand       { float mode;       }; // 0x0C X360
struct DacSetSampleRateCommand : DacCommand { float sampleRate; }; // 0x0C X360
struct DacStartCommand : DacCommand {};                            // 0x08 X360
struct DacStopCommand  : DacCommand {};                            // 0x08 X360
```

The PDB nominally calls the `GetSize` argument `PlugInConfig*`; the current PC dispatcher
names the equivalent stage-configuration shape `VoiceStageConfig`. The argument is dead
in the ARTIST body. `CreateInstance` is a C++ `bool`, while the generic descriptor slot
dispatches it as an integer-returning callback; the X360 return register is simply `0`
or `1`. `Process` likewise returns the integer-valued `BufferStatus` (`UNAVAILABLE = 0`,
`AVAILABLE = 1`).

### XEX float/rodata recovery

The recovery formula for the decrypted uncompressed XEX is:

```text
file_off = 0x3000 + vaddr - 0x82000000
```

All float words below were read as big-endian bytes from
`IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex`.

| VA | File-offset calculation | BE bytes | Recovered value | Use |
|---:|---:|---:|---:|---|
| `0x82001CC0` | `0x3000 + 0x1CC0 = 0x4CC0` | `00 00 00 00` | `0.0f` | initialization, mode enumeration, ramp-up origin |
| `0x82001C98` | `0x3000 + 0x1C98 = 0x4C98` | `3F 80 00 00` | `1.0f` | support result, ramp numerator, clip maximum |
| `0x820037C8` | `0x3000 + 0x37C8 = 0x67C8` | `BF 80 00 00` | `-1.0f` | clip minimum |
| `0x82004270` | `0x3000 + 0x4270 = 0x7270` | `40 40 00 00` | `3.0f` | default mode (`5.1`) |
| `0x820AA808` | `0x3000 + 0xAA808 = 0xAD808` | `47 3B 80 00` | `48000.0f` | sample rate and `MixerExecuteParams::outputSampleRate` |
| `0x820ADBFC` | `0x3000 + 0xADBFC = 0xB0BFC` | `43 80 00 00` | `256.0f` | mixer-frame duration numerator |

The seven-word PDB-named `sPossibleSampleRates` array at `0x8215D010` is at
`0x3000 + 0x15D010 = 0x160010`. Its big-endian words recover as
`{ 0x473B8000, 0, 0, 0, 0, 0, 0 }`, hence
`{ 48000.0f, 0, 0, 0, 0, 0, 0 }`. `CreateInstance` compacts only strictly positive
entries, so ARTIST exposes one sample-rate capability: 48 kHz.

The six mode-name pointers at `0x82F8C664` resolve to:

| Index | Pointer | String |
|---:|---:|---|
| 0 | `0x8215D044` | `Mono` |
| 1 | `0x8215D04C` | `Stereo` |
| 2 | `0x8215D054` | `Quad` |
| 3 | `0x8215D05C` | `5.1` |
| 4 | `0x8215D060` | `7.1` |
| 5 | `0x8215D064` | `Dolby Pro Logic II` |

## 2. `Dac0` descriptor at `off_82F8C7A8`

The record VA is `0x82F8C7A8`; its XEX file offset is
`0x3000 + 0xF8C7A8 = 0xF8F7A8`. The 0x34-byte record is:

```text
00F8F7A8: 82 15 D0 80 82 B9 6C B0 82 BA 24 A0 00 00 00 00
00F8F7B8: 82 B9 72 50 82 F8 C6 7C 82 F8 C6 80 82 F8 C7 80
00F8F7C8: 00 00 00 00 00 00 00 00 44 61 63 30 04 00 03 05
00F8F7D8: 00 00 00 00
```

| Offset | Raw value | `PlugInDescRunTime` field | Meaning |
|---:|---:|---|---|
| `+0x00` | `0x8215D080` | `pName` | `"Dac"` |
| `+0x04` | `0x82B96CB0` | `pGetSize` | `Dac::GetSize` |
| `+0x08` | `0x82BA24A0` | `pCreateInstance` | `Dac::CreateInstance` |
| `+0x0C` | `0` | `pPreProcess` | no pre-process callback |
| `+0x10` | `0x82B97250` | `pProcess` | `Dac::Process` |
| `+0x14` | `0x82F8C67C` | `pChannelMaps` | runtime channel-map data |
| `+0x18` | `0x82F8C680` | `pParameterDescRunTime` | three attributes |
| `+0x1C` | `0x82F8C780` | `pEventDescRunTime` | five events |
| `+0x20` | `0` | `pPlugInDescToolSide` | null in the retail image |
| `+0x24` | `0` | `mpNext` | unlinked initial state |
| `+0x28` | `0x44616330` | `muId` | ASCII/FourCC `Dac0` |
| `+0x2C` | `0x04` | `mu8PlugInType` | type 4 |
| `+0x2D` | `0x00` | `mu8NumConstructorParameters` | none |
| `+0x2E` | `0x03` | `mu8NumAttributes` | mode, sample rate, latency |
| `+0x2F` | `0x05` | `mu8NumEvents` | enumerate/set mode, set rate, start, stop |
| `+0x30` | `0x00` | `mbVariableInputChannels` | false |
| `+0x31` | `0x00` | `mbVariableOutputChannels` | false |
| `+0x32` | `0x00` | `mbSeq` | assigned later by registration |
| `+0x33` | `0x00` | padding | zero |

The adjacent metadata begins with the following exact bytes. Their internal element
types are not named by a current ARTIST consumer, so this report deliberately does not
invent field names for them.

```text
pChannelMaps 0x82F8C67C:
06 00 FF FF

pParameterDescRunTime 0x82F8C680 (prefix):
00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 40
14 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00

pEventDescRunTime 0x82F8C780 (complete bytes through the descriptor):
00 00 00 03 00 00 00 00 00 00 00 01 00 00 00 00
00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00
```

## 3. X360 object and supporting layouts

### `Dac` instance (`sizeof == 0x3108`)

| X360 offset | Size | PDB/current-header name | Assembly attestation |
|---:|---:|---|---|
| `+0x00` | `0x24` | `PlugIn` base | vtable at `+0`; `mpSystemUseGetSystemAccessor` at `+4`; `mpAttribute` at `+0x0C`; channel bytes at `+0x20/+0x21` |
| `+0x24` | 4 | `Mixer* mpMixer` | allocated in `CreateInstance`; read by `Mix`/`XenonDownMix` |
| `+0x28` | 8 | `mAttribute[GETMODE]` | `Attribute_t::mfValue = 3.0f` at `+0x28` |
| `+0x30` | 8 | `mAttribute[GETSAMPLERATE]` | `Attribute_t::mfValue = 48000.0f` at `+0x30` |
| `+0x38` | 8 | `mAttribute[GETLATENCY]` | `Attribute_t::mfValue = 0.0f` at `+0x38` |
| `+0x40` | 4 | `IXAudioSourceVoice* mpXenonVoice` | output of `XAudioCreateSourceVoice`; all voice calls load this slot |
| `+0x44` | `0x3000` | `float mpXAudioDataBuffer[3072]` | zeroed as 0x3000 bytes; split into two 0x1800-byte packets |
| `+0x3044` | 4 | `int mNextPacketToSubmit` | packet submit ring index |
| `+0x3048` | 4 | `int mNextPacketToMixInto` | producer ring index |
| `+0x304C` | 4 | `void* mXAudioEvent` | `XAudioCreateEvent(0, 1)` result |
| `+0x3050` | `2 * 0x58` | `XAUDIOPACKET mXAudioPackets[2]` | two packet records, cleared together as 0xB0 bytes |
| `+0x3100` | 8 | `PACKET_STATUS mXAudioPacketStatus[2]` | `FREE/READY/SUBMITTED`, four bytes per entry |

Within each console packet record, `+0x00` receives its data pointer, `+0x04` receives
`0x1800`, and `+0x54` receives the address of its corresponding status word. These are
the only packet-subfield offsets required by the recovered bodies; no unverified XAudio
field names are assigned to the other cleared words.

There is no current PC `Dac` type. Therefore every `Dac` member in the table is missing
from the current PC class model, even though the base `PlugIn` names already exist.
The X360 offsets are documentary ABI facts, not a request to pack an x64 host class to
32-bit pointer offsets.

### `Mixer` and `MixerExecuteParams`

The PDB layout required by `Dac::Mix` is:

| X360 offset | PDB member |
|---:|---|
| `Mixer +0x00000` | `mBuffer[3][16384]` (`0x30000` bytes total) |
| `Mixer +0x30000` | `double mCurrentMixTime` |
| `Mixer +0x30008` | `System* mpSystem` |
| `Mixer +0x3000C` | `SampleBuffer* mpSampleBuffer[3]` |
| `Mixer +0x30018` | `MixerExecuteParams*`/format-execute state pointer (PDB field at this slot) |
| `Mixer +0x3001C` | `unsigned mMixerCpuCycles` |
| `Mixer +0x30020` | `int mSrcNumSamples` |
| `Mixer +0x30024` | `float mSrcSampleRate` |
| `Mixer +0x30028` | `float mTotalPitch` |
| `Mixer +0x3002C` | `unsigned char mSrcNumChannels` |

`sizeof(Mixer) == 0x30080`. No current PC `Mixer.h` or `Mixer.cpp` homes this type.

`MixerExecuteParams` is 0x18 bytes on X360:

| Offset | PDB member | Writer in recovered `Dac::Mix` |
|---:|---|---|
| `+0x00` | `double systemTime` | `System +0x08` |
| `+0x08` | `VoiceListNode* pVoiceListNodes` | `System::mppVoiceListNodes` (`+0x58`) |
| `+0x0C` | `float outputSampleRate` | `48000.0f` |
| `+0x10` | `u16 numVoices` | `System::muActiveVoiceCount` (`+0x10F4`) |
| `+0x12` | `u8 numPlugInsRegistered` | not written by this body; retained from the global record's prior initialization |
| `+0x13` | `u8 verifyFloats` | booleanized `System::maucDebugFeatures[2]` (`+0x10FD`) |

### Dac statics/globals named by the PDB and attested in ARTIST

| ARTIST address | Name/role | Initial or observed use |
|---:|---|---|
| `0x8327A580` | `Dac::spProfiler` | set from `System::GetProfiler` |
| `0x8327A584` | `Dac::sStartRequested` | start-ramp flag |
| `0x8327A585` | `Dac::sChannels` | set to six |
| `0x8327A586` | `Dac::sCapNumSampleRates` | compacted rate count |
| `0x8327A587` | `Dac::sStarted` | start/stop state |
| `0x8327A588` | X360 thread-running flag | not present in the PDB static list; controls `XenonThread` lifetime |
| `0x8327A589` | `Dac::sCapNumModes` | set to one |
| `0x8327D600` | final interleaved scratch buffer | 0x1800 bytes = 1536 floats = 256 frames * 6 channels |
| `0x8327EE04` | `Dac::sCapModes[6]` | first entry receives mode 3 |
| `0x8327EE1C` | `Dac::sCapSampleRates[7]` | first entry receives 48000.0f |
| `0x8327EE40` | global `MixerExecuteParams` | populated by `Dac::Mix` |
| `0x8327EE58` | XAudio initialized/shared-state word | nonzero skips per-instance XAudio/thread setup |
| `0x8327EE6C` | `Dac::sCpuLoadBalancer` | `Init`, `Reset`, `Balance`, cycle counters |
| `0x8327EE88` | `Dac::sProcessingMode` | initialized to realtime (`0`) |

The PDB additionally names `sPossibleModes[6]`, `sModeNames[6]`,
`sDacModeToChannelMap[6]`, `sPossibleSampleRates[7]`, and the enum/static capability
arrays above. This report does not assign addresses to PDB-named arrays that the decoded
bodies do not directly reference.

## 4. `Dac::CreateInstance` at `0x82BA24A0`

Effective descriptor dispatch and canonical declaration:

```cpp
// pConstructorParams arrives in r4 and is unused.
static bool Dac::CreateInstance(PlugIn* pPlugIn, void* pConstructorParams);
```

Register-level/store-for-store decode:

1. `r3` is preserved as `r31 = self`; `r29 = 0`. The function saves `r28..r31`, LR,
   and `f31`, and allocates a 0x120-byte frame.
2. It forms an XAudio-initialize stack record `Q = &var_C8`: `Q[0] = 0`, clears
   `Q+1 .. Q+0x0B`, and later writes `0x82108F38` to `Q+4`.
3. It forms a source-voice stack record `P = &var_90`: stores zero to `P+0`, then
   clears exactly 0x58 bytes beginning at `P+4`. The three bytes `P+1..P+3` are not
   touched by that pair of stores.
4. If `self != 0`, `off_8217F3C4` is stored to `self+0x00` as the `Dac` vtable. The
   null branch only skips this store; subsequent code dereferences `self`, so null is
   outside the callback contract.
5. Stores `0` to `self->mpMixer` (`+0x24`), computes `r30 = self+0x28`, and stores
   `r30` to base `PlugIn::mpAttribute` (`self+0x0C`). Stores `0` to global
   `sProcessingMode` (`0x8327EE88`).
6. Calls `CpuLoadBalancer::Init(&sCpuLoadBalancer, self->mpSystemUseGetSystemAccessor)`.
7. Calls `System::GetProfiler(system)`, stores the result to `spProfiler`, and returns
   `false` immediately if it is null.
8. Calls `System::Alloc(system, 0x30080, 0, 0x80, 0)`, stores the allocation to
   `self+0x24`, and, when nonnull, placement-constructs it with `Mixer::Mixer` and stores
   the constructor result back to `self+0x24`. If the final `mpMixer` is null, returns
   `false` with no cleanup in this body.
9. Stores `system` to `mpMixer+0x30008` (`Mixer::mpSystem`).
10. Initializes all observable state:

    ```text
    sStarted                         = 0
    sStartRequested                  = 0
    self->mAttribute[GETLATENCY]     = 0.0f       // self+0x38
    sCapNumModes                     = 0
    sCapNumSampleRates               = 0
    self->mAttribute[GETSAMPLERATE]  = 48000.0f   // self+0x30
    self->mAttribute[GETMODE]        = 3.0f       // self+0x28
    sChannels                        = 6
    ```

11. Appends integer `3` to `sCapModes[sCapNumModes]` and increments the byte count from
    zero to one. Thus only `MODE_5POINT1` is advertised by this ARTIST platform body.
12. Walks exactly seven floats from `0x8215D010` up to, but not including,
    `0x8215D02C`. For each value strictly greater than `0.0f`, it stores the value to
    `sCapSampleRates[count]` and increments an 8-bit count. It writes the final count
    once after the loop. The recovered table yields `{48000.0f}` and count one.
13. Loads the chosen rate from `self+0x30`, computes single-precision
    `framePeriod = 256.0f / sampleRate`, then writes:

    ```text
    System::mfSampleRate                 (system+0x10C4) = sampleRate
    System::mfSystemTimerPeriod          (system+0x10C0) = framePeriod
    System::mTimerManager.mTimerPeriod   (system+0x0098) = framePeriod
    ```

14. Stores `1` to the thread-running flag at `0x8327A588`.
15. If `dword_8327EE58 != 0`, branches directly to the common success return. No voice,
    packet, event, or thread member is initialized on that path by this function.
16. Otherwise writes `0x82108F38` to `Q+4` and calls `XAudioInitialize(Q)`; there is no
    checked return value.
17. Completes the source-voice record with these exact stores relative to `P`:

    | Stack offset | Store |
    |---:|---|
    | `P+0x00` | byte `0` |
    | `P+0x04` | byte `6` |
    | `P+0x08` | word `0x0000BB80` (`48000`) |
    | `P+0x3B` | byte `2` |
    | `P+0x3C` | float `0.0f` |
    | `P+0x40` | byte `1` |
    | `P+0x4C` | `&Dac::XenonProcessCb` |
    | `P+0x50` | `&Dac::XenonPacketCompleteCb` |
    | `P+0x58` | `self` |

    It calls `XAudioCreateSourceVoice(P, &self->mpXenonVoice)`. The ARTIST body does
    not branch on a result.
18. Clears exactly 0xB0 bytes at `self+0x3050`, i.e. both 0x58-byte packet records.
19. For `i = 0,1`, with packet stride `0x58`, buffer stride `0x1800`, and status stride
    four, performs these stores:

    ```text
    mXAudioPacketStatus[i] = PACKET_FREE
    *(packet[i] + 0x54)    = &mXAudioPacketStatus[i]
    *(packet[i] + 0x00)    = &mpXAudioDataBuffer[i * 0x1800 bytes]
    *(packet[i] + 0x04)    = 0x1800
    ```

20. Clears all 0x3000 bytes at `self+0x44`. Stores zero to both
    `mNextPacketToSubmit` and `mNextPacketToMixInto`.
21. Calls `XAudioCreateEvent(0, 1)` and stores the returned handle to `self+0x304C`.
22. Constructs stack `EA::Thread::Thread` and `EA::Thread::ThreadParameters` objects.
    IDA mislabels the first constructor call as
    `rw::movie::VideoRenderable::~VideoRenderable`; the surrounding `Thread::Begin` and
    matching `EA::Thread::Thread::~Thread` call identify the stack object's role, not a
    movie-side dependency.
23. Copies thread settings from the audio `System` into the parameter object:
    priority from `system+0x10EC`, stack size from `system+0x10F0`, processor byte from
    `system+0x10FA` (stored as a word), a zero flag byte, and name
    `"RWAudioCore Dac"`. It calls unnamed `sub_82B42D88`; that return is passed as the
    final `r7` argument to `EA::Thread::Thread::Begin`. Its semantic name is not proven.
24. Calls
    `Thread::Begin(&thread, Dac::XenonThreadFunc, self, &parameters, auxiliaryValue)`.
    It stores the returned thread-id word to a stack temporary, passes its address to
    `System::SetRwAudioCoreThreadId`, and destroys the stack `Thread` object.
25. Loads `self->mpXenonVoice`, calls `XAudioSourceVoice_Start(voice, 0)`, and returns
    `true`.

The only explicit false returns are missing profiler and missing mixer allocation/
construction. None of the XAudio/event/thread calls is checked in this body.

## 5. `Dac::GetSize` at `0x82B96CB0`

```cpp
static unsigned Dac::GetSize(const VoiceStageConfig* /*pConfig*/)
{
    return 0x3108;
}
```

The complete assembly is `li r3, 0x3108; blr`. The nominal configuration argument is
unused. The return is exactly the X360 object allocation size, 12,552 bytes.

## 6. `Dac::GetPlugInDescRunTime` at `0x82B96DB8`

```cpp
static PlugInDescRunTime* Dac::GetPlugInDescRunTime()
{
    return reinterpret_cast<PlugInDescRunTime*>(0x82F8C7A8);
}
```

`lis/addi` materializes `off_82F8C7A8`, then `blr`; the following word at
`0x82B96DC4` is zero padding. The returned descriptor is the `Dac0` record decoded in
section 2.

## 7. `Dac::EventEvent` at `0x82BA27F0`

Effective declaration:

```cpp
void Dac::EventEvent(EventId eventId, void* pParameterBuffer);
// r3=self, r4=eventId, r5=pParameterBuffer
```

The first instruction loads `self->mpSystemUseGetSystemAccessor` (`self+4`) into `r11`
before dispatching on `eventId`; the mode-enumeration path does not otherwise use that
load.

### Event 0: `ENUMERATEMODE`

1. Loads `params->mode` from `r5+0` into `f0`.
2. Converts it toward zero with `fctiwz`, stores the integer through the caller stack
   back-chain word, reloads it, multiplies by four, and indexes the six-pointer table at
   `0x82F8C664`. There is no bounds check before this name lookup.
3. Stores `0.0f` to `params->isSupported` (`r5+4`) and the selected string pointer to
   `params->pModeName` (`r5+8`).
4. Loads the signed byte/positive count `sCapNumModes`. If count `<= 0`, returns.
5. For each `i` in `[0,count)`, loads a signed 32-bit mode from `sCapModes[i]` (`lwa`),
   converts it to single-precision float, and compares that value with the original
   input float in `f0`. On an ordered exact equality, stores `1.0f` to
   `params->isSupported` and returns. Otherwise it advances by four and continues.
6. If no entry matches, returns with the already-stored `0.0f`.

Consequently `3.0f` returns name `"5.1"` and supported `1.0f` in the initialized ARTIST
state. A fractional value can truncate to a valid name index but still be unsupported,
because the support test compares the original float, not the truncated integer.

### Events 1 and 2: deferred 12-byte value commands

For event 1, `r8 = &Dac::SetModeHandler`; for event 2,
`r8 = &Dac::SetSampleRateHandler`. It then:

```text
cursor = system->muDeferredRingCursor                    // system+0x10B8
cmd    = system->commandBufferBase + cursor              // base at system+0x20
system->muDeferredRingCursor = cursor + 0x0C
cmd+0x00 = handler
cmd+0x04 = self
cmd+0x08 = raw 32-bit word at pParameterBuffer+0
return
```

The raw copy preserves the float bits exactly.

### Event 3 and every other event: deferred 8-byte start/stop command

The function reserves eight bytes unconditionally for any event other than 0, 1, or 2:

```text
cursor = system->muDeferredRingCursor
cmd    = system->commandBufferBase + cursor
system->muDeferredRingCursor = cursor + 8
cmd+0x04 = self
cmd+0x00 = (eventId == 3) ? &Dac::StartHandler : &Dac::StopHandler
return
```

Thus official event 4 selects stop, but so does every invalid event outside 0..3. There
is no validation branch. On x64 the producer/handler stride must widen together: use
`sizeof(host command)` on both sides rather than retaining literal console strides with
widened pointers.

## 8. Missing-export recovery: `Dac::StartHandler` at `0x82B9DCF0`

There was no function dossier because this address falls in the exporter gap immediately
after `SetSampleRateHandler`. `EventEvent` proves the address with its
`lis/addi 0x82BA / 0xDCF0` handler materialization. The next exported function is
`StopHandler` at `0x82B9DD48`, making the recovered range exactly
`0x82B9DCF0..0x82B9DD47` (0x58 bytes).

The direct XEX file offset is
`0x3000 + 0xB9DCF0 = 0xBA0CF0`. The recovered bytes are:

```text
7D8802A6 9181FFF8 FBE1FFF0 9421FFA0 3D608328 896BA587
280B0000 40820024 80630004 4BFF90B5 3D608328 3BEBEE6C
7FE3FB78 4BFC9915 4BFC6831 907F0008 38600008 38210060
8181FFF8 7D8803A6 EBE1FFF0 4E800020
```

Exact disassembly/effect:

```text
82B9DCF0  mflr  r12
82B9DCF4  stw   r12,-8(r1)
82B9DCF8  std   r31,-0x10(r1)
82B9DCFC  stwu  r1,-0x60(r1)
82B9DD00  lis   r11,0x8328
82B9DD04  lbz   r11,-0x5A79(r11)       // sStarted @8327A587
82B9DD08  cmplwi r11,0
82B9DD0C  bne   0x82B9DD30
82B9DD10  lwz   r3,4(r3)               // command->pObject
82B9DD14  bl    Dac::StartImmediate
82B9DD18  lis   r11,0x8328
82B9DD1C  addi  r31,r11,-0x1194        // &sCpuLoadBalancer @8327EE6C
82B9DD20  mr    r3,r31
82B9DD24  bl    CpuLoadBalancer::Reset
82B9DD28  bl    GetCpuCycle
82B9DD2C  stw   r3,8(r31)              // mOverheadCounter.mCpuCycleStart
82B9DD30  li    r3,8
82B9DD34..44 restore and return
```

Implementation shape:

```cpp
int Dac::StartHandler(DacStartCommand* command)
{
    if (!sStarted)
    {
        command->pObject->StartImmediate();
        sCpuLoadBalancer.Reset();
        sCpuLoadBalancer.mOverheadCounter.mCpuCycleStart = GetCpuCycle();
    }
    return 8; // X360 command-record stride
}
```

It is idempotent while already started. `StartImmediate` owns the actual state transition;
the handler does not itself write `sStarted`.

## 9. `Dac::StopHandler` at `0x82B9DD48`

```cpp
int Dac::StopHandler(DacStopCommand* command)
{
    if (sStarted)
    {
        command->pObject->StopImmediate();
        sCpuLoadBalancer.Balance();
    }
    return 8; // X360 command-record stride
}
```

Assembly details: it loads byte `0x8327A587`, branches directly to the return when zero,
otherwise loads `command+4` into `r3`, calls `StopImmediate`, materializes
`&sCpuLoadBalancer` at `0x8327EE6C`, and calls `CpuLoadBalancer::Balance`. It always
returns `8`. As with `StartHandler`, a host reconstruction must return the same host
record size its event producer reserves.

## 10. `Dac::RampOutput` at `0x82B96CB8`

```cpp
void Dac::RampOutput(float* pBuffer, int numFrames, bool rampUp);
// r3=self (not otherwise read), r4=pBuffer, r5=numFrames, r6=rampUp byte
```

Exact arithmetic and control flow:

1. Sign-extends `numFrames` to 64 bits, stores/reloads it through the stack, converts it
   to float, and computes `step = 1.0f / float(numFrames)`.
2. Loads `sChannels` as an unsigned byte. Computes the exclusive byte end as
   `pBuffer + 4 * sChannels * numFrames` using a 32-bit multiply and shift.
3. If `(r6 & 0xFF) != 0`, replaces the converted frame count in `f0` with `0.0f` and
   enters the ramp-up loop. Otherwise `f0` remains `float(numFrames)` and it enters the
   ramp-down loop.
4. For every frame, it iterates channels from zero to `sChannels-1`. Each sample is
   loaded, multiplied by `f0 * step`, and stored back. The channel count byte is reloaded
   inside the channel loop after each store, exactly as the assembly does.
5. Ramp-up adds `1.0f` to `f0` after each frame; ramp-down subtracts `1.0f`.
6. It advances the outer pointer by `4 * sChannels` and uses unsigned address comparison
   against the precomputed end.

Therefore the exact frame gains are:

```text
rampUp:   gain(i) = i / numFrames,                 i = 0..numFrames-1
rampDown: gain(i) = (numFrames - i) / numFrames,  i = 0..numFrames-1
```

The up-ramp begins at zero and ends at `(N-1)/N`. The down-ramp begins at one and ends
at `1/N`; neither includes both mathematical endpoints. A zero or negative frame count
is outside the intended contract; division and unsigned end-pointer construction remain
literal in the console body.

## 11. `Dac::Process` at `0x82B97250`

Effective descriptor callback:

```cpp
static BufferStatus Dac::Process(Dac* self, AudioProcessContext* context)
{
    self->XenonDownMix(); // context in r4 is neither read nor rewritten
    return BUFFERSTATUS_AVAILABLE;
}
```

The complete semantic body is one call followed by `li r3,1`. `XenonDownMix` receives
the existing `r3=self`; the context argument is dead. There is no branch on mixer status
at this descriptor boundary.

## 12. `Dac::XenonDownMix` at `0x82B97178`

```cpp
void Dac::XenonDownMix();
```

Store-for-store decode:

1. Materializes the global 0x1800-byte scratch buffer at `0x8327D600`.
2. Loads `mpMixer` from `self+0x24`, then loads the first sample-buffer pointer from
   `mpMixer+0x3000C`.
3. Calls:

   ```cpp
   ReOrderRwAudioCoreToWave(scratch, mpMixer->mpSampleBuffer[0],
                            sChannels, 0x100);
   ```

   Thus every output quantum is 256 frames.
4. If `sStartRequested != 0`, calls
   `self->RampOutput(scratch, 0x80, true)` and then stores zero to `sStartRequested`.
   Only the first 128 frames of the 256-frame output block receive the start ramp.
5. Calls `ClipFloats(scratch, -1.0f, 1.0f, 0x600)`. The fixed count is 1536 floats,
   exactly `256 * 6`, not `256 * sChannels`.
6. Restores and returns; it performs no copy to the XAudio packet itself. That copy is
   in `XenonThread` after `Mix` returns available.

The initialized console capability is always six channels, so the fixed 0x600 clip and
0x1800-byte packet agree with the normal path.

## 13. `ReOrderRwAudioCoreToWave` at `0x82B6B590`

Existing PC declaration, confirmed by register use:

```cpp
void ReOrderRwAudioCoreToWave(float* pDst, void* pSampleBuffer,
                              int numChannels, int numSamples);
// r3=dst, r4=SampleBuffer*, r5=channels, r6=samples
```

The input node fields are `SampleBuffer+0x04 = planar channel-0 float base` and
`u16 SampleBuffer+0x0E = per-channel stride in samples`.

| `numChannels` | Exact operation per frame |
|---:|---|
| 6 | input RW order `{ch0,ch1,ch2,ch3,ch4,ch5}` becomes WAV `{ch0,ch2,ch1,ch5,ch3,ch4}`; semantically `{FL,C,FR,BL,BR,LFE}` -> `{FL,FR,C,LFE,BL,BR}` |
| 4 | interleave `{ch0,ch1,ch2,ch3}` unchanged |
| 2 | interleave `{ch0,ch1}` unchanged |
| 1 | tail-call `XMemCpy(dst, base, numSamples * 4)` |
| other | return without touching the destination |

For six channels the assembly constructs planar pointers at
`base + {0,4,8,12,16,20} * stride` bytes and writes destination offsets
`{0,8,4,16,20,12}` respectively, which is the mapping above. The loop termination
pointer is channel 2's pointer plus `4*numSamples`; for four and two channels it uses
the analogous channel-1 pointer end. All loop comparisons are unsigned address compares.
The `rotlwi` operations are effective left shifts by two, three, or four for the
zero-extended `u16` stride values in this contract.

This function is already homed correctly in `MixKernels.cpp`; no new Dac-local copy
should be introduced.

## 14. `ClipFloats` at `0x82B64B68`

Existing PC declaration:

```cpp
void ClipFloats(float* pData, float minValue, float maxValue, int numSamples);
// r3=data, f1=min, f2=max, r6=count; r4/r5 are dead carry registers
```

Exact body:

1. Computes `end = pData + (numSamples << 2)` in 32-bit address arithmetic.
2. If unsigned `pData >= end`, returns.
3. For each word before `end`, loads the float once.
4. `fcmpu value,min`; if the less-than bit is set, stores `min` and skips the maximum
   comparison.
5. Otherwise `fcmpu value,max`; if the greater-than bit is set, stores `max`.
6. In-range values are not stored back. PPC unordered compares set neither LT nor GT,
   so NaNs traverse both skip branches and remain unchanged, matching the natural
   `if (v < min) ... else if (v > max)` implementation.
7. Advances by four and repeats with unsigned pointer comparison.

The normal Dac caller supplies positive `0x600`. A negative count would wrap the shifted
32-bit endpoint and is outside the kernel contract.

This function is already homed in `MixKernels.cpp`.

## 15. Missing-export recovery: `Dac::Mix` at `0x82B96E80`

`XenonThread` contains branch-with-link word `0x4BFFFE81` at `0x82B97000`. Its signed
relative displacement is `-0x180`, proving target `0x82B96E80`. The next named export is
`Dac::XenonThread` at `0x82B96F40`; therefore the exact recovered body range is
`0x82B96E80..0x82B96F3F` (0xC0 bytes). This matches the PDB's 192-byte `Dac::Mix` body.

The file offset is `0x3000 + 0xB96E80 = 0xB99E80`. Raw words:

```text
7D8802A6 48072069 9421FF90 3D608328 7C7F1B78 3BCBEE6C
7FC3F378 4BFD8065 3D608328 815F0004 388BEE40 C80A0008
D8040000 817F0004 816B0058 91640008 3D60820B C00BA808
D004000C 817F0004 A16B10F4 B1640010 3D608327 816B1928
896B10FD 7D6B0034 556BDFFE 696B0001 99640013 807F0024
4BFD6A09 3D400003 817F0024 813F0004 7C7D1B78 614A001C
7D6B502E 916910D0 817F0004 C80B0008 C1AB10C0 FC0D002A
D80B0008 4BFCD62D 907E0008 7FA3EB78 38210070 48072000
```

Straight-line register/store decode:

1. Saves LR and `r29..r31`, allocates 0x70 bytes, and preserves `self` in `r31`.
2. Materializes `r30 = &sCpuLoadBalancer` (`0x8327EE6C`) and calls
   `CpuLoadBalancer::Balance(r30)`.
3. Loads `system = self+4`; materializes `r4 = &gMixerExecuteParams` at `0x8327EE40`.
4. Loads double `system+0x08` and stores it to `params+0x00` (`systemTime`).
5. Loads `system+0x58` and stores it to `params+0x08` (`pVoiceListNodes`).
6. Loads big-endian float `48000.0f` from `0x820AA808` and stores it to `params+0x0C`
   (`outputSampleRate`).
7. Loads `u16 system+0x10F4` and stores it to `params+0x10` (`numVoices`).
8. Loads the `System*` singleton through `0x83271928`, then byte
   `system+0x10FD`. `cntlzw`, `rlwinm`, and `xori 1` reduce it to exactly `1` when
   nonzero and `0` when zero; the result is stored to `params+0x13`
   (`verifyFloats`). Current named layout: `System::maucDebugFeatures[2]`.
9. Loads `self->mpMixer` and calls `Mixer::Execute(mpMixer, &params)`. Preserves its
   `BufferStatus` return in `r29`.
10. Loads `mpMixer->mMixerCpuCycles` (`mpMixer+0x3001C`) and stores it to
    `system->muMixerCpuTicks` (`system+0x10D0`).
11. Loads double `system+0x08`, loads float `system->mfSystemTimerPeriod`
    (`+0x10C0`), adds the period to the double time, and stores the double back to
    `system+0x08`.
12. Calls `GetCpuCycle()` and stores the result to `sCpuLoadBalancer+8`, the counter's
    `mCpuCycleStart` slot used by the next accounting interval.
13. Returns the saved `Mixer::Execute` result.

Implementation shape:

```cpp
BufferStatus Dac::Mix()
{
    sCpuLoadBalancer.Balance();

    gMixerExecuteParams.systemTime = mpSystemUseGetSystemAccessor->mSystemTime;
    gMixerExecuteParams.pVoiceListNodes =
        mpSystemUseGetSystemAccessor->mppVoiceListNodes;
    gMixerExecuteParams.outputSampleRate = 48000.0f;
    gMixerExecuteParams.numVoices =
        mpSystemUseGetSystemAccessor->muActiveVoiceCount;
    gMixerExecuteParams.verifyFloats =
        System::GetInstance()->maucDebugFeatures[2] != 0;

    BufferStatus status = mpMixer->Execute(&gMixerExecuteParams);
    mpSystemUseGetSystemAccessor->muMixerCpuTicks = mpMixer->mMixerCpuCycles;
    mpSystemUseGetSystemAccessor->mSystemTime +=
        mpSystemUseGetSystemAccessor->mfSystemTimerPeriod;
    sCpuLoadBalancer.mOverheadCounter.mCpuCycleStart = GetCpuCycle();
    return status;
}
```

The pseudo-body above names the operations; the host must use its named, naturally
widened members. `numPlugInsRegistered` at `params+0x12` is intentionally not assigned,
because the ARTIST body does not store it.

## 16. `Dac::XenonThread` at `0x82B96F40`

```cpp
void Dac::XenonThread();
// r3=self; nominal void return
```

This is a two-level wait/produce loop around a two-packet ring.

### Entry and outer loop

1. Saves `r24..r31`, loads `system = self+4` into `r26`, and calls
   `System::ExecuteCommandsLock(system)` once before entering any loop.
2. If thread-running byte `0x8327A588` is zero, branches to the common unlock/return.
3. Caches the final scratch pointer (`0x8327D600`), `&sStarted`, `spProfiler`, and
   `&sCpuLoadBalancer`; fixes `r24 = 0` for ring wrap stores.
4. At the top of each outer iteration, calls
   `XAudioWaitForSingleObject(self->mXAudioEvent, -1, 0)`.
5. After the wait, it tests
   `mXAudioPacketStatus[mNextPacketToMixInto]`. Only `PACKET_FREE` enters the inner
   producer loop. Any other status skips to the outer running-flag test and then waits
   again.

### Inner producer iteration

1. Tests the thread-running flag; if clear, exits toward unlock.
2. Calls `spProfiler->Start()`.
3. If `sStarted == 0`, calls `System::ExecuteCommands(system)`, tests the running flag,
   and jumps to the accounting tail. If the running flag became zero it exits directly;
   the assembly does not issue `Profiler::End` on that direct shutdown branch.
4. If started, calls `GetCpuCycle()` and stores it to `sCpuLoadBalancer+8`, then calls
   `System::ExecuteCommands(system)`.
5. Tests running again; if clear, exits. Tests `sStarted` again; if start/stop commands
   made it false, skips mixing and goes to the accounting tail.
6. Calls `status = self->Mix()`.
7. Computes `packet = &mXAudioPackets[mNextPacketToMixInto]` using stride 0x58 and loads
   its `+0x00` destination pointer. If `status == BUFFERSTATUS_AVAILABLE` (`1`), copies
   exactly 0x1800 bytes from global scratch to the packet. Otherwise clears exactly
   0x1800 destination bytes. No other status value is distinguished.
8. Stores `PACKET_READY` (`1`) to
   `mXAudioPacketStatus[mNextPacketToMixInto]`.

### Submit-ready loop

While `mXAudioPacketStatus[mNextPacketToSubmit] == PACKET_READY`:

1. Calls `XAudioVoice_GetVoiceState(mpXenonVoice, &stackState)`.
2. Tests bit `0x20` in the first returned state byte (`rlwinm.` mask bit 26). If absent,
   breaks out of submission without modifying this ready packet. No stronger semantic
   name for that XAudio state bit is assigned here.
3. Stores `PACKET_SUBMITTED` (`2`) to that packet's status.
4. Calls `XAudioSourceVoice_SubmitPacket(mpXenonVoice,
   &mXAudioPackets[mNextPacketToSubmit], 0)`.
5. Increments `mNextPacketToSubmit`; if it becomes two, wraps it to zero.

After the submit loop, increments `mNextPacketToMixInto` and wraps two to zero.

### Accounting and continuation

At the accounting label, it reloads `sStarted`:

- If started, it calls `GetCpuCycle()` and performs exactly
  `accumulated = accumulated + current - start` using
  `sCpuLoadBalancer+4` and `+8`, stores the result back to `+4`, then calls
  `spProfiler->End()`.
- If not started, it calls `spProfiler->End()` and leaves the inner loop.

If still started, the code immediately re-tests the newly selected
`mXAudioPacketStatus[mNextPacketToMixInto]`; if it is `FREE`, it repeats the inner
producer iteration without another event wait. Otherwise it leaves the inner loop.
The outer loop repeats while the thread-running flag is nonzero.

On exit it calls `System::ExecuteCommandsUnlock(system)` exactly once, restores, and
returns. The lock therefore spans all waits and all mixer command execution in this
console implementation; the lock routines are the audio system's special execute-
commands lock/unlock pair, not an arbitrary host mutex inferred from the wait.

The ring requires `XenonPacketCompleteCb` to transition submitted packets back to
`FREE` and signal the event. That callback is an un-homed dependency listed below; this
report does not substitute guessed callback stores for its own dossier.

## 17. Consolidated body shapes

```text
CreateInstance
  install Dac state -> create/attach Mixer -> expose 5.1 @48 kHz -> set 256-frame
  system timing -> if XAudio not already initialized, create a 6ch float voice,
  two 0x1800 packets, event and worker -> start voice

EventEvent
  event 0 answers mode name/support immediately; events 1/2 enqueue 12-byte value
  commands; event 3 enqueues StartHandler; every other id enqueues StopHandler

StartHandler / StopHandler
  idempotent deferred state transitions around StartImmediate/StopImmediate and
  CpuLoadBalancer reset/balance; return console record stride 8

Mix
  balance -> populate the global MixerExecuteParams -> Mixer::Execute -> publish mixer
  ticks -> advance system time one 256/48000 quantum -> re-arm cycle counter

Process / XenonDownMix
  reorder planar mixer output to 256-frame interleaved WAV order -> optional 128-frame
  start ramp -> clip all 1536 floats -> report AVAILABLE

XenonThread
  one execute-command lock around an event-driven two-packet producer; mix/copy or
  silence, submit READY packets while the XAudio state bit permits, account cycles
```

## 18. Un-homed dependencies and missing identities

The `Dac` TU in `progress/tu_index.json` currently contains these 18 identities, all
without a PC primary file:

| Identity | ARTIST address where known |
|---|---:|
| `Dac::GetSize` | `0x82B96CB0` |
| `Dac::RampOutput` | `0x82B96CB8` |
| `Dac::GetPlugInDescRunTime` | `0x82B96DB8` |
| `Dac::StartImmediate` | `0x82B96DC8` |
| `Dac::StopImmediate` | `0x82B96E38` |
| `Dac::XenonThread` | `0x82B96F40` |
| `Dac::XenonThreadFunc` | `0x82B97150` |
| `Dac::XenonDownMix` | `0x82B97178` |
| `Dac::XenonProcessCb` | `0x82B97208` |
| `Dac::XenonPacketCompleteCb` | `0x82B97228` |
| `Dac::Process` | `0x82B97250` |
| `Dac::ReleaseEvent` | `0x82B9DAE0` |
| `Dac::SetModeHandler` | `0x82B9DB78` |
| `Dac::SetSampleRateHandler` | `0x82B9DCE8` |
| `Dac::StopHandler` | `0x82B9DD48` |
| `Dac::CreateInstance` | `0x82BA24A0` |
| `Dac::EventEvent` | `0x82BA27F0` |
| `Dac::scalar deleting destructor` | exported in the Dac TU |

Two real ARTIST functions are additionally absent from the identity/TU export and must
be added when the Dac home is implemented:

- `Dac::StartHandler @0x82B9DCF0`, recovered in section 8.
- `Dac::Mix @0x82B96E80`, recovered in section 15.

The important non-Dac dependencies are:

- `rw::audio::core::Mixer`, its 0x30080-byte PDB layout, constructor, and
  `Mixer::Execute`; there is no PC home yet.
- `MixerExecuteParams` and the global parameter record used by `Dac::Mix`.
- The already-homed `CpuLoadBalancer::{Init,Reset,Balance}` and its two cycle-counter
  words.
- The already-homed `Profiler::{Start,End}`, `System::{GetProfiler,Alloc,
  SetRwAudioCoreThreadId,ExecuteCommandsLock,ExecuteCommands,
  ExecuteCommandsUnlock}`, and `GetCpuCycle` surfaces.
- The Dac callback bodies `XenonProcessCb`, `XenonPacketCompleteCb`, and
  `XenonThreadFunc`, plus `StartImmediate`, `StopImmediate`, mode/rate handlers, and
  release path. Their exact dossiers should be used when implementing them; the loop
  dependencies described here are not replacements for those decodes.
- X360-only `XAudioInitialize`, source-voice/event/packet calls, `XMemCpy/XMemSet`, and
  the unnamed `sub_82B42D88` thread-begin auxiliary provider.

PDB-only methods such as `SetProcessingMode` or `OfflineModeMixFrame` must not be added
merely because the symbols exist in another build. They need an ARTIST identity/body
attestation first.

## 19. PC-home recommendations

1. **Home the canonical middleware types.** Add `rw/audio/core/Dac.h` and `Dac.cpp` in
   the vendor RenderWare tree, and home `Mixer`/`MixerExecuteParams` alongside or before
   them. Use the PDB names above and current named `PlugIn`/`System` members. Do not use
   raw `reinterpret_cast(this + offset)` access.
2. **Keep console offsets as evidence, not x64 packing rules.** Native pointers widen on
   the PC. Do not use `#pragma pack(4)` or fake 32-bit pointer fields to preserve
   `0x3108`. The descriptor `GetSize` console result is exactly `0x3108`, but the host
   allocator path must be audited before deciding whether its callback returns the
   historical serialized/console stride or the natural `sizeof(Dac)`. It must never
   allocate 0x3108 and then placement-construct a larger naturally widened object.
3. **Preserve the platform-independent engine logic exactly.** Mode enumeration,
   deferred commands, start/stop state, `MixerExecuteParams`, cycle accounting,
   256-frame mixing, channel reorder, ramp, clip, and unavailable-to-silence behaviour
   belong in the faithful `Dac` implementation.
4. **Replace only the Xenon output leaf.** The X360 `XAUDIOPACKET`, event, and source-
   voice API should not be copied into the PC class as pretend host engine state.
   `CgsSystem::AudioOutputPC` is the existing PC-platform XAudio2 leaf and explicitly
   documents that the eventual RenderWare Dac will register its pull via `SetFill`.
5. **Bridge formats explicitly.** ARTIST emits interleaved float, six channels,
   256 frames, clipped to `[-1,1]`; `AudioOutputPC::FillFn` requests interleaved signed
   16-bit mono/stereo and its implementation caps channels at two. A Dac adapter must
   retain the six-channel core mix/order, fold/downmix to the selected one/two-channel
   PC output, and perform saturating float-to-s16 conversion. Never reinterpret the
   0x1800-byte float packet as s16 PCM.
6. **Use the existing 256-frame quantum.** `AudioOutputPC` currently requests exactly
   256 frames per buffer, so it aligns with `Dac::XenonDownMix` and avoids an additional
   staging layer today. Still keep the adapter framed so a later backend request size
   can consume staged 256-frame blocks without changing the mixer contract.
7. **Do not run graph mutation casually on the XAudio2 callback.** The console owns a
   dedicated worker, command lock, packet ring, and event. The safest host shape is a
   producer that retains the Dac command/mix loop and feeds an SPSC block queue consumed
   by `AudioOutputPC::FillFn`. If the callback itself drives `Mixer::Execute`, verify that
   every command/allocator/lock path is callback-safe and cannot recursively take the
   same lock.
8. **Widen deferred command records consistently.** The X360 producers advance by 8 or
   12 and handlers return the same values because function/object pointers are four
   bytes. On x64, reserve `sizeof(DacStartCommand)` / `sizeof(DacSetModeCommand)` and
   return those same host sizes. A literal 8/12 paired with widened members corrupts the
   command ring.
9. **Treat cross-thread state as synchronization state.** `sStarted`,
   `sStartRequested`, the running flag, packet/block states, and output ownership cross
   callback/worker boundaries. Preserve their logical transitions but use appropriate
   host atomics or the established queue synchronization instead of data races.
10. **Coordinate primary-output ownership.** `AudioOutputPC` has one primary `SetFill`
    slot plus persistent overlay and voice slots. Movie/menu-music code can replace the
    primary fill. The Dac integration needs an explicit ownership policy so a movie does
    not permanently clobber game mix output and Dac shutdown does not close a device
    still serving overlay/voice clients.
11. **Advertise an intentional capability policy.** Fidelity-first core operation can
    retain the X360 5.1/48-kHz graph and downmix only at the PC sink. If PC event 0 is
    changed to report actual stereo device capability, mark that as a platform-leaf
    difference and do not silently change the internal RW channel order or mixer channel
    count.
12. **Test the recovered invariants directly.** Minimum coverage should include 1/2/4/6
    channel reorder, exact ramp endpoints for both directions, NaN-preserving clip,
    mode 3/48-kHz enumeration, silence when `Mixer::Execute` is unavailable, two-slot
    queue wrap, start/stop idempotence, command-record host strides, and clean worker/
    callback shutdown.

## 20. Verification status

Every exported function described above was rechecked against its dossier's
`assembly` field rather than its pseudocode. Register arguments, immediate values,
branches, loop endpoints, packet strides, and stores in this report follow the assembly.
The two exporter-gap functions were checked against the raw big-endian instruction words
shown in sections 8 and 15. All cited floats were independently recovered from the XEX
with the stated VA-to-file-offset formula and their big-endian bytes are recorded in the
table.

No assembly/pseudocode disagreement changes a decode in this report. The material
places where pseudocode was insufficient were the generic callback signatures, the
`EventEvent` invalid-event fallthrough, the exact ramp endpoints, the `verifyFloats`
booleanization, the packet-ring loop shape, and the two missing function ranges; in each
case the assembly/raw bytes were trusted.
