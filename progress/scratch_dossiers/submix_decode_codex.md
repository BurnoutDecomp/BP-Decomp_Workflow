# `rw::audio::core::SubMix` implementation-grade ARTIST decode

This is a read-only reconstruction dossier. The behavioral spine is the `assembly` field in the per-function ARTIST JSON exports. Names and source-level class shape come from the Feb-2007 rwaudiocore headers. Raw image offsets use the required formula throughout:

```text
file_off = 0x3000 + vaddr - 0x82000000
```

The image is `IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex`, length `0x105B000`; all raw values below were reread big-endian from that file. ARTIST behavior wins every disagreement called out below.

## 1. Vendor header summary

Primary shape authority: `references/Feb-2007/BrnEntityModuleUnity/SDKs/Packages/rwaudiocore/2.11.00/include/rw/audio/core/plugins/submix.h`.

### `SubMixConnector`

The vendor header declares:

```cpp
class SubMixConnector
{
public:
    SubMixConnector();
    void Connect(Voice *pVoice, SubMix *pSubMix);
    void Disconnect(float *pDeClickValue = 0);
    static SubMixConnector *GetConnectorFromNode(void *pNode);
    ListDNode *GetNode();
    ListDNode *GetNext();
    float *GetSubMixBuffer();
    int GetNumSubMixChannels();

private:
    ListDNode mListNode;
    float *mpSubMixBuffer;
    SubMix *mpSubMix;
    unsigned char mNumSubMixChannels;
};
```

The related `private/linklist.h` defines `ListDNode` as two node pointers, `pnext` then `pprev`, and `ListDStack` as one `ListDNode *phead`; `Push` inserts at the head and `Remove` repairs `prev->next` and `next->prev`. Thus the exact X360 connector layout is `{mListNode +0x00/+0x04, mpSubMixBuffer +0x08, mpSubMix +0x0C, mNumSubMixChannels +0x10}`. Evidence: vendor `submix.h`; `references/.../private/linklist.h:54-82,142-228`; ARTIST `SubMixConnector::Disconnect` at `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B9C3C0.json` confirms every offset.

### `SubMix`

The vendor header declares `class SubMix : public PlugIn`, one constructor parameter (`const char *ConstructorParams::pName`), and these relevant methods:

```cpp
static unsigned int GetSize(PlugInConfig *);
static bool CreateInstance(PlugIn *pPlugIn, void *pConstructorParams);
static int CreateInstanceHandler(Command *pCommand);
static BufferStatus Process(PlugIn *pThis, Mixer *pMixer, bool discontinuity);
virtual void ReleaseEvent();
static void EnumerateSubMixReset();
static SubMix *EnumerateSubMix();
const char *GetName();
```

`SubMix` is friends with `SubMixConnector`, `Send`, `Route`, and `System`. Its members, in declaration order after the X360 `PlugIn` base, are:

| X360 offset | Vendor member | Exact type / extent |
|---:|---|---|
| base `+0x00..+0x23` | `PlugIn` | 36-byte X360 polymorphic base |
| `+0x24` | `mpSubMixBuffer` | `float *` |
| `+0x28` | `mSendList` | `ListDStack` (one pointer, the inbound connector-list head) |
| `+0x2C` | `mSubMixListNode.pnext` | first word of `ListDNode` |
| `+0x30` | `mSubMixListNode.pprev` | second word of `ListDNode` |
| `+0x34..+0x4B` | `mDeClickValueTotal[MAX_CHANNELS]` | six `float`s; `MAX_CHANNELS == 6` |
| `+0x4C..+0x8B` | `mName[64]` | 64-byte name buffer |
| `+0x8C` | `mSubMixAdded` | `unsigned char` |
| `+0x8D` | `mDeClickRequired` | `unsigned char` |
| `+0x8E..+0x8F` | tail padding | makes X360 `sizeof(SubMix) == 0x90` |

The static registry is `ListDStack SubMix::sSubMixList` plus `ListDNode *SubMix::spSubMixNextNode`. `EnumerateSubMixReset()` assigns the head to the cursor inline; `EnumerateSubMix()` is declared out of line but was inlined/folded at the ARTIST Send consumer. Evidence: vendor `submix.h`; `channel.h` (`MAX_CHANNELS`); ARTIST offsets in `0x82B9C380.json`, `0x82B9C480.json`, `0x82BA0C18.json`, and `0x82B9FF80.json`.

### Related header contracts

- `plugins/send.h`: `Send::ConnectByNameHandler(Command *)`; `ConnectByNameParams { const char *pName; }`; `Send` is a friend of `SubMix`.
- `mixer.h`: `Mixer::SwapBuffers()` swaps `mpSampleBuffer[0]` and `[1]`; on ARTIST those slots are at `Mixer+0x3000C` and `Mixer+0x30010`.
- `samplebuffer.h`: supplies the `SampleBuffer` vocabulary. The ARTIST mixer-local descriptor variant actually consumed by `SubMix::Process` has `mpStorage/mpSamples` at `+0x04` and a 16-bit channel stride at `+0x0E`; those offsets are independently established by `Mixer::Execute` at `0x82B6D958-0x82B6D994` and are already named in `b5-decomp/vendor/renderware/include/rw/audio/core/Mixer.h`.
- `plugin.h`: `PlugIn::Attribute_t`, the polymorphic `PlugIn` base, and `PlugIn::Initialize<T>(T *, uintptr_t)`, which placement-constructs the derived type and optionally installs its attribute pointer. `SubMix` passes an attribute offset of zero.
- `pluginregistry.h`: `PlugInConfig { void *pConstructorParams; PlugInHandle plugInHandle; unsigned char outputChannels; }` and the callback-facing `PlugInConfig *` used by `GetSize`.
- `voice.h`: the exact processing dispatch type is `BufferStatus ProcessFn(PlugIn *, Mixer *, bool)`.
- DecFIGS' `references/DecFIGS/dwarfdump/SDKs/EATech/include/rw/audio/core/plugin.h:331-343` restores one platform-conditioned virtual omitted from the visible Feb header text: virtual order is `ReleaseEvent()`, `EventEvent(int, void *)`, `GetPpuTicksEvent() const`, destructor. ARTIST's four-slot vtable proves that order.

### Explicit vendor/ARTIST divergences

1. The visible Feb `PlugInDescRunTime` text presents PS3/SPU-oriented `pSpuElf`/`spuElfSize` fields after `CreateInstance`. ARTIST's raw 52-byte record and its consumers instead place `pPreProcess` at `+0x0C` and `pProcess` at `+0x10`; there are no SPU fields in the ARTIST record. ARTIST wins for the PC implementation.
2. Feb `send.h` makes `ConnectByNameParams::pName` a pointer. ARTIST `Send::EventEvent` constructs a variable record with a 12-byte X360 header and the NUL-terminated name inline, and `ConnectByNameHandler` byte-loads directly from `command+0x0C` without an intervening pointer load (`0x82B9FFC4-0x82B9FFD0`). ARTIST wins.
3. ARTIST/IDA sometimes assigns unrelated names to ICF-folded one- or two-instruction bodies. Vtable position plus the vendor/DecFIGS virtual order identifies those bodies; the unrelated IDA alias does not override class shape.

## 2. Existing PC implementation audit

### What already exists

| Repo-relative path | Existing coverage | Assessment |
|---|---|---|
| `b5-decomp/vendor/renderware/src/rw/audio/core/SubMix_statics.cpp` | Defines `SubMix::sSubMixList = {}` and `SubMix::spSubMixNextNode = 0`. | Correct static storage home, but the list remains empty only because the real create handler is missing. Its banner explicitly describes this as temporary link closure. |
| `b5-decomp/vendor/renderware/include/rw/audio/core/SubMixConnector.h` | Defines `ListDStack`, a partial/opaque `SubMix`, the two statics, and a flattened `SubMixConnector`. It already pins the ARTIST tail offsets and correct six-float/name/two-flag extents. | Useful evidence scaffold, not an implementation-grade `SubMix`: it is not derived from `PlugIn`, hides the base in `char mHeader00[0x21]`, exposes originally-private registry state, and uses reconstruction aliases (`mbNumChannels`, `mpConnectorHead`, `mafChannelGain`, `mbDirty`). Its absolute X360 prefix cannot be used as an x64 layout. |
| `b5-decomp/vendor/renderware/src/rw/audio/core/SubMixConnector.cpp` | Implements ARTIST `Disconnect` @`0x82B9C3C0`: unlink, optional gain fold-back, and clear connector state. | Behavior is present. The current static return-`SubMixConnector *` spelling differs from vendor `void SubMixConnector::Disconnect(float *)`; the machine's incidental `r3` passthrough should not override the vendor source signature. |
| `b5-decomp/vendor/renderware/src/rw/audio/core/Send.cpp` | Implements the rest of `Send`, including the producer of both deferred connect record forms, and documents the SubMix registry/link behavior. | Present and directly relevant. The file does **not** contain the name handler body; it deliberately points to the sibling part-file. |
| `b5-decomp/vendor/renderware/src/rw/audio/core/Send_wL_01.cpp` | Implements `Send::ConnectByNameHandler` @`0x82B9FF80`, including cursor updates, inline-name comparison, and connector insertion. | This is the live consumer of `sSubMixList`. It already uses host `offsetof`/host record size, which is the correct porting strategy. |
| `b5-decomp/vendor/renderware/include/rw/audio/core/Send.h` | Defines host-width fixed and variable Send command records and the partial Send layout. | The variable inline-name record matches ARTIST, intentionally overriding Feb's by-pointer command shape. |
| `b5-decomp/vendor/renderware/include/rw/audio/core/Mixer.h` | Names the ARTIST mixer context, src/dst slots, and `SampleBuffer::{mpSamples,muStride}`. | Sufficient named host surface for `SubMix::Process`; no raw offsets should be repeated in new code. |
| `b5-decomp/vendor/renderware/include/rw/audio/core/PlugIn.h` | Has a real x64 `PlugIn`, `System`, and typed 52-byte ARTIST `PlugInDescRunTime` model. | Supplies most needed host types. It does not currently expose the vendor `Initialize<T>`/`GetSystem()` helpers, and its virtual declarations do **not** match original names/order (`~PlugIn`, `Event`, `VFunc2`, `Destroy` versus ARTIST `ReleaseEvent`, `EventEvent`, `GetPpuTicksEvent`, deleting destructor); a real SubMix class needs that base-vtable issue resolved rather than adding an explicit second vptr. |

### What is missing

There is no `b5-decomp/vendor/renderware/include/rw/audio/core/SubMix.h` and no `b5-decomp/vendor/renderware/src/rw/audio/core/SubMix.cpp`. Missing bodies/storage beyond the two statics are:

- the real `SubMix : public PlugIn` declaration and vendor member names;
- `GetSize`, `GetPlugInDescRunTime`, `CreateInstance`, `CreateInstanceHandler`, `Process`, `ReleaseEvent`, and the destructor behavior;
- the real `sPlugInDescRunTime`, `sChannelMaps`, and `sParameterDescRunTime` records;
- `EnumerateSubMix()` (the ARTIST inlined body is fully recoverable below);
- `SubMixConnector::Connect` as a declared API surface (the Send/Route handlers open-code its link operation);
- a host-safe `Command`/SubMix-create record stride shared by producer and handler.

The prior `progress/scratch_dossiers/plugin_callbacks_decode_codex.md` section 6 was rechecked instruction by instruction. Its broad flow is right, but this dossier makes two load-bearing facts explicit: `0x82BA4708` stores `mpSubMixBuffer` **even when allocation fails**, and the record handler installed at `0x82BA4728-0x82BA4730` is concretely `SubMix::CreateInstanceHandler @0x82B9C380`.

## 3. Decode targets

### 3.1 `SubMix::GetSize` @ `0x82B982F0`

Evidence: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B982F0.json`; dispatch call at `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B6EC50.json:0x82B6EC98-0x82B6ECA8`; raw descriptor field at `0x82F902E4`.

#### (a) Exact signature at dispatch

```cpp
static unsigned int SubMix::GetSize(PlugInConfig *pPlugInConfig);
```

`Voice::CreateInstance` sets `r3` to the current 12-byte `PlugInConfig`, loads its descriptor from config `+0x04`, loads callback slot `descriptor+0x04`, and indirect-calls it (`0x82B6EC98-0x82B6ECA8`). This body ignores incoming `r3`. IDA's zero-argument prototype is therefore incomplete; the vendor callback shape and actual dispatcher establish the parameter.

#### (b) Full instruction-range table

| Address | Instruction | Exact effect |
|---|---|---|
| `0x82B982F0` | `li r3,0x90` | Return the X360 allocation footprint, 144 bytes. |
| `0x82B982F4` | `blr` | Return to the generic size dispatcher. |

#### (c) Constants / raw bytes

No rodata is loaded by the body. The immediate is `0x90`. Dispatch provenance is the raw descriptor word:

| vaddr | file_off | Raw bytes (BE) | Decoded value |
|---:|---:|---|---|
| `0x82F902E4` | `0xF932E4` | `82 B9 82 F0` | `pGetSize = 0x82B982F0` |

#### (d) Member access table

No instance/config member is read. `pPlugInConfig` is ABI-visible but unused.

#### (e) Implementation-grade C++

```cpp
unsigned int SubMix::GetSize(PlugInConfig *)
{
    // ARTIST/X360: 0x90. The allocator consumes this result, so the host must use
    // the widened class footprint rather than under-allocate 144 bytes.
    return static_cast<unsigned int>(sizeof(SubMix));
}
```

`Voice::CreateInstance` narrows this result to 16 bits at `0x82B6EDF0`/`0x82B6EE08`; the natural x64 SubMix remains far below `0x10000`.

### 3.2 Supporting target: `SubMix::GetPlugInDescRunTime` @ `0x82B9C370`

This ledger body is necessary for a complete TU even though it was not separately named in the request. Evidence: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B9C370.json`; raw descriptor `0x82F902E0..0x82F90313`.

#### (a) Exact signature

```cpp
static PlugInDescRunTime *SubMix::GetPlugInDescRunTime();
```

IDA types it as `char **`; the returned address and vendor declaration identify the real type.

#### (b) Full instruction-range table

| Address | Instruction | Exact effect |
|---|---|---|
| `0x82B9C370` | `lis r11,off_82F902E0@ha` | Form the high half of `SubMix::sPlugInDescRunTime`. |
| `0x82B9C374` | `addi r3,r11,off_82F902E0@l` | Return `&sPlugInDescRunTime` (`0x82F902E0`). |
| `0x82B9C378` | `blr` | Return. |
| `0x82B9C37C` | `.long 0` | Alignment data, not an executed instruction. |

#### (c) Full raw descriptor/constants

| Field / vaddr | file_off | Raw bytes (BE) | Decoded value |
|---|---:|---|---|
| `pName` `0x82F902E0` | `0xF932E0` | `82 17 B0 90` | `0x8217B090` |
| `pGetSize` `0x82F902E4` | `0xF932E4` | `82 B9 82 F0` | `0x82B982F0` |
| `pCreateInstance` `0x82F902E8` | `0xF932E8` | `82 BA 46 80` | `0x82BA4680` |
| `pPreProcess` `0x82F902EC` | `0xF932EC` | `00 00 00 00` | null |
| `pProcess` `0x82F902F0` | `0xF932F0` | `82 B9 C4 80` | `0x82B9C480` |
| `pChannelMaps` `0x82F902F4` | `0xF932F4` | `82 F9 02 BC` | `0x82F902BC` |
| `pParameterDescRunTime` `0x82F902F8` | `0xF932F8` | `82 F9 02 C0` | `0x82F902C0` |
| `pEventDescRunTime` `0x82F902FC` | `0xF932FC` | `00 00 00 00` | null |
| `pPlugInDescToolSide` `0x82F90300` | `0xF93300` | `00 00 00 00` | null in ARTIST |
| list link `0x82F90304` | `0xF93304` | `00 00 00 00` | null |
| `guid` `0x82F90308` | `0xF93308` | `53 75 62 30` | `0x53756230`, `'Sub0'` |
| packed bytes `0x82F9030C` | `0xF9330C` | `04 01 00 00` | type 4 (`STANDARD`), 1 constructor parameter, 0 attributes, 0 events |
| final flags/index `0x82F90310` | `0xF93310` | `00 00 00 00` | variable-in 0, variable-out 0, registry index 0, pad 0 |
| name `0x8217B090` | `0x17E090` | `53 75 62 4D 69 78 00` | `"SubMix\0"` |
| channel maps `0x82F902BC` | `0xF932BC` | `00 FD FF FF` | pairs `{0,-3}` (`STANDARD`) then `{-1,-1}` terminator |
| constructor parameter `0x82F902C0..0x82F902DB` | `0xF932C0..0xF932DB` | `00 00 00 00 00 00 00 03` then twenty zero bytes | direction `INPUT`, type `POINTERTOSTRING`, both double extrema `0.0`, tool-side pointer null |

The visible Feb descriptor layout disagrees at `+0x0C/+0x10`; the ARTIST raw record and its dispatchers are authoritative.

#### (d) Member access table

No instance member is accessed. This returns the static record above.

#### (e) Implementation-grade C++

```cpp
ChannelMapPair SubMix::sChannelMaps[] = {
    { 0, CHANNELMAPVALUE_STANDARD },
    { CHANNELMAPVALUE_TERMINATOR, CHANNELMAPVALUE_TERMINATOR }
};

ParameterDescRunTime SubMix::sParameterDescRunTime[] = {
    { PARAMETERDIRECTION_INPUT, PARAMETERTYPE_POINTERTOSTRING,
      0.0, 0.0, nullptr }
};

PlugInDescRunTime SubMix::sPlugInDescRunTime = {
    "SubMix", &SubMix::GetSize, &SubMix::CreateInstance,
    nullptr, &SubMix::Process,
    SubMix::sChannelMaps, SubMix::sParameterDescRunTime,
    nullptr, nullptr, nullptr,
    SubMix::GUID,
    PLUGINTYPE_STANDARD, 1, 0, 0, 0, 0, 0
};

PlugInDescRunTime *SubMix::GetPlugInDescRunTime()
{
    return &sPlugInDescRunTime;
}
```

The exact initializer spelling must follow the current host `PlugInDescRunTime` declaration; the field values above are the ARTIST values.

### 3.3 `SubMix::CreateInstance` @ `0x82BA4680`

Evidence: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82BA4680.json`; descriptor dispatch at `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B6A818.json:0x82B6A85C-0x82B6A874`; ring consumer at `0x82B6F7E0-0x82B6F80C` in `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B6F6D0.json`.

#### (a) Exact signature at dispatch

```cpp
static bool SubMix::CreateInstance(PlugIn *pPlugIn, void *pConstructorParams);
// pConstructorParams is either null or points to:
struct SubMix::ConstructorParams { const char *pName; };
```

At `PlugIn::CreateInstance+0x44`, ARTIST loads `r4 = config->pConstructorParams`, loads `descriptor->pCreateInstance` from `+0x08`, and calls it with `r3` still the allocated `PlugIn *`. It tests only the low result byte (`clrlwi. ...,24`), confirming `bool`.

#### (b) Full instruction-range table

| Address range | Instructions covered | Exact effect |
|---|---|---|
| `0x82BA4680-0x82BA4688` | `mflr`; `bl __savegprlr_29`; `stwu` | Save LR/nonvolatile `r29..r31`; allocate the `0x70` frame. |
| `0x82BA468C-0x82BA4698` | `mr r31,r3`; `li r29,0`; null compare/branch | Preserve `self`; establish zero; skip only derived construction stores when `self==0`. |
| `0x82BA469C-0x82BA46A8` | `lis/addi off_8217F554`; two `stw` | Install SubMix vptr `0x8217F554`; set `mSendList.phead` at `+0x28` to null. This is the inlined `Initialize<SubMix>`/default construction. |
| `0x82BA46AC-0x82BA46B4` | compare `r4`; `stb 0,+0x8C`; branch | Clear `mSubMixAdded` unconditionally, then select named versus empty-name path. A null `self` is not supported because this store still dereferences it. |
| `0x82BA46B8-0x82BA46D4` | `lwz` source pointer; destination `self+0x4C`; `lbz/addi/cmplwi/stb/addi/bne` loop | Copy `params->pName` byte by byte into `mName`, including the terminator, with **no bounds check and no null check on `pName`**. |
| `0x82BA46D8` | unconditional branch | Skip the empty-name store after a successful copy. |
| `0x82BA46DC` | `stb 0,+0x4C` | Null constructor params produce `mName[0] = '\0'`. |
| `0x82BA46E0-0x82BA4700` | channel `lbz`; allocation-name address; zero override; System load; `rotlwi`; alignment/name/size args; call `System::Alloc` | Compute `size = mOutputChannels * 1024` (the source is an 8-bit load, so rotate-left 10 equals shift-left 10), then call `System::Alloc(mpSystem,size,"rw::audio::core::SubMix::mpSubMixBuffer",0x80,nullptr)`. |
| `0x82BA4704-0x82BA4714` | null compare; **`stw r3,+0x24`**; branch or false return setup | Store the allocation result into `mpSubMixBuffer` on **both success and failure**. On null, set return false and jump to epilogue. This corrects the omission called out in the task. |
| `0x82BA4718-0x82BA4720` | move byte count; zero fill value; call `XMemSet` | Zero all `outputChannels * 1024` allocated bytes. `r3` is still the returned buffer pointer. |
| `0x82BA4724-0x82BA4734` | load System; materialize handler; set totals pointer; materialize handler into `r4`; zero into `r5` | Prepare the deferred create record and later six-word zero loop. The handler address is concretely `SubMix::CreateInstanceHandler @0x82B9C380`. |
| `0x82BA4738-0x82BA4754` | load cursor `+0x10B8`; `li r8,6`; load ring base `+0x20`; add; cursor `+8`; store cursor; store handler and self | Append the exact X360 record `{ int (*handler)(Command*), SubMix *self }`, stride 8. No capacity check is in this body. |
| `0x82BA4758-0x82BA4768` | clear `+0x8D`; `mtctr 6`; six-word `stw/addi/bdnz` loop | Clear `mDeClickRequired`; clear all six `mDeClickValueTotal` float bit patterns to `0.0f`. These stores occur only after successful allocation. |
| `0x82BA476C-0x82BA4774` | `li r3,1`; frame release; branch restore helper | Return true and restore. |

#### (c) Constants / raw bytes

| Constant | vaddr | file_off | Raw bytes (BE) | Decoded value/use |
|---|---:|---:|---|---|
| derived vtable | `0x8217F554` | `0x182554` | `82 BA 0C 18 82 84 CB 38 82 7E 2F 38 82 BA 1D E8` | four function pointers; decoded in section 3.6 |
| allocation name | `0x8217B098` | `0x17E098` | `72 77 3A 3A 61 75 64 69 6F 3A 3A 63 6F 72 65 3A 3A 53 75 62 4D 69 78 3A 3A 6D 70 53 75 62 4D 69 78 42 75 66 66 65 72 00` | `"rw::audio::core::SubMix::mpSubMixBuffer\0"` |

All other constants (`0`, `6`, `8`, `0x80`, `0x400`) are instruction immediates, not rodata.

#### (d) Member-offset/access table

| Object + X360 offset | Vendor member | Access/effect |
|---|---|---|
| `SubMix+0x00` | hidden vptr | store `off_8217F554` |
| `PlugIn+0x04` | `mpSystemUseGetSystemAccessor` | allocator/ring owner load |
| `PlugIn+0x21` | `mOutputChannels` | `lbz`; allocation/clear size |
| `SubMix+0x24` | `mpSubMixBuffer` | allocation result stored before null branch |
| `SubMix+0x28` | `mSendList.phead` | initialized null |
| `SubMix+0x34..0x4B` | `mDeClickValueTotal[6]` | six 32-bit zero stores on success |
| `SubMix+0x4C..` | `mName[64]` | unbounded copied string or empty string |
| `SubMix+0x8C` | `mSubMixAdded` | cleared before allocation |
| `SubMix+0x8D` | `mDeClickRequired` | cleared on success only |
| `ConstructorParams+0x00` | `pName` | full 32-bit X360 pointer load |
| `System+0x20` | `mpCommandBuffer` | ring base |
| `System+0x10B8` | `mCommandIndex` | byte cursor, advanced by 8 on X360 |
| `Command+0x00/+0x04` | `handler` / `pObject` | `0x82B9C380` / `self` |

#### (e) Implementation-grade C++

```cpp
struct SubMixCreateCommand
{
    int (*handler)(Command *);
    SubMix *pObject;
};

bool SubMix::CreateInstance(PlugIn *pPlugIn, void *pConstructorParams)
{
    SubMix *self = static_cast<SubMix *>(pPlugIn);
    new (self) SubMix; // exact effect of vendor PlugIn::Initialize(self, 0)

    self->mSubMixAdded = 0;
    const ConstructorParams *params =
        static_cast<const ConstructorParams *>(pConstructorParams);
    if (params)
        std::strcpy(self->mName, params->pName); // deliberately unbounded: ARTIST behavior
    else
        self->mName[0] = '\0';

    const unsigned channels = self->mOutputChannels;
    const std::size_t bytes =
        std::size_t(channels) * MIXER_FRAME_SIZE * sizeof(float); // channels * 1024
    System *system = self->mpSystemUseGetSystemAccessor;
    self->mpSubMixBuffer = static_cast<float *>(
        System::Alloc(system, static_cast<unsigned int>(bytes),
                      "rw::audio::core::SubMix::mpSubMixBuffer", 128, nullptr));
    if (!self->mpSubMixBuffer)
        return false;

    std::memset(self->mpSubMixBuffer, 0, bytes);

    auto *command = reinterpret_cast<SubMixCreateCommand *>(
        system->mpDeferredRingBase + system->muDeferredRingCursor);
    system->muDeferredRingCursor += sizeof(SubMixCreateCommand); // host: 16, X360: 8
    command->handler = &SubMix::CreateInstanceHandler;
    command->pObject = self;

    self->mDeClickRequired = 0;
    for (unsigned i = 0; i != MAX_CHANNELS; ++i)
        self->mDeClickValueTotal[i] = 0.0f;
    return true;
}
```

The host implementation must not use literal stride 8. Producer and handler must use the same `sizeof(SubMixCreateCommand)`.

### 3.4 `SubMix::CreateInstanceHandler` @ `0x82B9C380`

Evidence: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B9C380.json`; generic command replay `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B6F6D0.json:0x82B6F7E0-0x82B6F80C`; `Command` shape in vendor `system.h:98-105`.

#### (a) Exact signature at dispatch

```cpp
static int SubMix::CreateInstanceHandler(Command *pCommand);
```

`Command` is `{ int (*handler)(Command *); void *pObject; }`. `System::ExecuteCommands` loads the first word, calls it with `r3 = record`, and advances `record = record + returned_r3` (`0x82B6F7F4-0x82B6F804`). The return value is therefore the **ring-cursor advance**, not a success code.

#### (b) Full instruction-range table

| Address range | Instructions covered | Exact effect |
|---|---|---|
| `0x82B9C380-0x82B9C38C` | global `lis`; `lwz r8,4(r3)`; `li 0`; `addi r11,r8,0x2C` | Load `self = command->pObject`, zero, and form `node = &self->mSubMixListNode`. |
| `0x82B9C390-0x82B9C398` | load global head; store zero to node `+4`; store head to node `+0` | `node->pprev = nullptr; node->pnext = sSubMixList.phead`. |
| `0x82B9C39C-0x82B9C3A8` | reload head; null test; conditional `stw r11,4(r9)` | If an old head exists, set `oldHead->pprev = node`. |
| `0x82B9C3AC-0x82B9C3B8` | `li 1`; store node as global head; `li r3,8`; `stb 1,+0x8C` | Publish the new head, set X360 return stride 8, and mark `mSubMixAdded = 1`. The flag store occurs after the return register is prepared. |
| `0x82B9C3BC` | `blr` | Return ring stride 8. |

#### (c) Constants / raw bytes

There is no rodata. The code references `sSubMixList` at `vaddr 0x8327EE68`, whose formula-derived `file_off` is exactly `0x1281E68`. That offset is beyond the raw XEX length `0x105B000`, so it is BSS/unbacked and has no file bytes to quote. The initial null head is a zero-initialized static, not a recoverable raw word. This raw-byte point is marked BLOCKED in section 5; behavior is not blocked because all reads/writes are explicit in assembly.

#### (d) Member-offset/access table

| Offset | Vendor member | Access/effect |
|---:|---|---|
| `Command+0x04` | `pObject` | load `SubMix *self` |
| `SubMix+0x2C` | `mSubMixListNode.pnext` | old list head stored |
| `SubMix+0x30` | `mSubMixListNode.pprev` | null stored |
| `SubMix+0x8C` | `mSubMixAdded` | set to 1 |
| global `0x8327EE68` | `sSubMixList.phead` | head loaded (twice) and replaced |

#### (e) Implementation-grade C++

```cpp
int SubMix::CreateInstanceHandler(Command *pCommand)
{
    SubMix *self = static_cast<SubMix *>(pCommand->pObject);
    ListDNode *node = &self->mSubMixListNode;
    node->pnext = sSubMixList.phead;
    node->pprev = nullptr;
    if (sSubMixList.phead)
        sSubMixList.phead->pprev = node;
    sSubMixList.phead = node;
    self->mSubMixAdded = 1;
    return static_cast<int>(sizeof(SubMixCreateCommand)); // host: 16; X360: 8
}
```

The console literal 8 is unsafe on x64 because both record fields widen from four to eight bytes.

### 3.5 `SubMix::Process` @ `0x82B9C480`

Evidence: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B9C480.json`; exact `ProcessFn` type in vendor `voice.h:67`; indirect dispatch at `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B6D900.json:0x82B6DA78-0x82B6DA9C` (`r3=PlugIn *`, `r4=Mixer *`, `r5=bool`).

#### (a) Exact signature at dispatch

```cpp
static BufferStatus SubMix::Process(PlugIn *pThis,
                                    Mixer *pMixer,
                                    bool discontinuity);
```

ARTIST does not read incoming `r5`; `discontinuity` is an ABI-required unused argument. IDA's two-argument prototype is incomplete.

#### (b) Full instruction-range table

| Address range | Instructions covered | Exact effect |
|---|---|---|
| `0x82B9C480-0x82B9C488` | `mflr`; save `r28..`; `stwu` | Save state; allocate `0x80` frame. |
| `0x82B9C48C-0x82B9C49C` | two `addis`; `addi +0x10/+0x0C`; `mr r31,r3` | Form `&mixer->mpDstBuffer` (`+0x30010`) and `&mixer->mpSrcBuffer` (`+0x3000C`); preserve `self`. |
| `0x82B9C4A0-0x82B9C4B0` | channel index zero; two pointer loads; two pointer stores | Load old destination into `r29`, old source into `r9`, then swap the two Mixer slots. The old destination becomes the new source/output buffer. |
| `0x82B9C4B4-0x82B9C4BC` | output-channel `lbz`; zero compare; branch | Skip the per-channel copy loop when `mOutputChannels == 0`. |
| `0x82B9C4C0` | `li r28,0` | Initialize source byte offset within `mpSubMixBuffer`. |
| `0x82B9C4C4-0x82B9C4E4` | stride `lhz`; count `0x400`; buffer/storage loads; multiply/shift; address adds; `bl XMemCpy` | For channel `r30`, copy exactly 1024 bytes (256 floats) from `mpSubMixBuffer + r28` to `newSrc->mpSamples + 4 * newSrc->muStride * channel`. |
| `0x82B9C4E8-0x82B9C4F8` | reload output count; increment channel; add `0x400`; compare/loop | Advance to the next planar channel. The channel count is reread each iteration. |
| `0x82B9C4FC-0x82B9C504` | load/test `+0x8D`; branch | Skip de-click when `mDeClickRequired == 0`. |
| `0x82B9C508-0x82B9C518` | `r6=0x100`; channel count; totals address; buffer arg; call `DeClick` | Call `DeClick(newSrc, mDeClickValueTotal, mOutputChannels, 256)`. ARTIST places 256 in `r6`; the current decoded helper consumes only the first three arguments and hard-codes its ramp body. |
| `0x82B9C51C-0x82B9C520` | zero and `stb` | Clear `mDeClickRequired` after the call. |
| `0x82B9C524-0x82B9C534` | channel `lbz`; fill zero; buffer load; `rotlwi` by 10; call `XMemSet` | Clear `mOutputChannels * 1024` bytes of the private accumulation buffer for the next frame. |
| `0x82B9C538-0x82B9C540` | `li r3,1`; release frame; branch restore helper | Return `BUFFERSTATUS_AVAILABLE` (1). |

#### (c) Constants / raw bytes

No rodata is loaded in this body. `0x400` bytes/channel and `0x100` samples are instruction immediates. Dispatch provenance:

| vaddr | file_off | Raw bytes (BE) | Decoded value |
|---:|---:|---|---|
| `0x82F902F0` | `0xF932F0` | `82 B9 C4 80` | `pProcess = 0x82B9C480` |

#### (d) Member-offset/access table

| Object + X360 offset | Vendor/current host member | Access/effect |
|---|---|---|
| `SubMix+0x21` | inherited `PlugIn::mOutputChannels` | channel loop bound and clear byte count |
| `SubMix+0x24` | `mpSubMixBuffer` | planar copy source, then cleared |
| `SubMix+0x34` | `mDeClickValueTotal[0]` | base passed to `DeClick` |
| `SubMix+0x8D` | `mDeClickRequired` | conditional de-click flag, cleared after use |
| `Mixer+0x3000C` | `mpSrcBuffer` | swapped with destination |
| `Mixer+0x30010` | `mpDstBuffer` | loaded as output and swapped with source |
| `SampleBuffer+0x04` | `mpSamples` (`mpStorage` vocabulary in Feb header) | destination planar storage base |
| `SampleBuffer+0x0E` | `muStride` / max-sample channel stride | 16-bit samples-per-channel stride |

#### (e) Implementation-grade C++

```cpp
BufferStatus SubMix::Process(PlugIn *pThis, Mixer *pMixer, bool)
{
    SubMix *self = static_cast<SubMix *>(pThis);
    SampleBuffer *output = pMixer->mpDstBuffer;
    SampleBuffer *oldSource = pMixer->mpSrcBuffer;
    pMixer->mpSrcBuffer = output;
    pMixer->mpDstBuffer = oldSource;

    for (unsigned channel = 0; channel < self->mOutputChannels; ++channel)
    {
        std::memcpy(output->mpSamples + output->muStride * channel,
                    self->mpSubMixBuffer + MIXER_FRAME_SIZE * channel,
                    MIXER_FRAME_SIZE * sizeof(float));
    }

    if (self->mDeClickRequired)
    {
        DeClick(output, self->mDeClickValueTotal, self->mOutputChannels);
        // ARTIST also supplies r6 = MIXER_FRAME_SIZE (256); its current helper ignores r6.
        self->mDeClickRequired = 0;
    }

    std::memset(self->mpSubMixBuffer, 0,
                std::size_t(self->mOutputChannels) * MIXER_FRAME_SIZE * sizeof(float));
    return BUFFERSTATUS_AVAILABLE;
}
```

The copy is assignment into the newly published source buffer, not accumulation. Accumulation into `mpSubMixBuffer` happens in connected Send/Route processing before SubMix runs.

### 3.6 Vtable `off_8217F554`, virtuals, and deleting destructor

The object stores vptr `0x8217F554`; therefore the preceding word at `vaddr 0x8217F550`, `file_off 0x182550`, bytes `82 BA 1D A0` belongs to the previous vtable. The next vtable starts at `vaddr 0x8217F564`, `file_off 0x182564`, bytes `82 B9 C5 48`; its first pointer is `TimeStretch::ReleaseEvent @0x82B9C548`. The SubMix vtable is exactly four slots.

#### Raw vtable dump and every slot

| Slot | vaddr | file_off | Raw bytes (BE) | Target | Identification |
|---:|---:|---:|---|---:|---|
| 0 | `0x8217F554` | `0x182554` | `82 BA 0C 18` | `0x82BA0C18` | `SubMix::ReleaseEvent()` |
| 1 | `0x8217F558` | `0x182558` | `82 84 CB 38` | `0x8284CB38` | inherited `PlugIn::EventEvent(int,void *)`, ICF-folded empty body |
| 2 | `0x8217F55C` | `0x18255C` | `82 7E 2F 38` | `0x827E2F38` | inherited `PlugIn::GetPpuTicksEvent() const`, ICF-folded return-zero body |
| 3 | `0x8217F560` | `0x182560` | `82 BA 1D E8` | `0x82BA1DE8` | SubMix deleting destructor (IDA label: ``vector deleting destructor'`) |

The virtual order is additionally proven by `PlugIn::CreateInstance` failure cleanup: it calls vtable `+0x00` first (`0x82B6A87C-0x82B6A88C`, release), then calls vtable `+0x0C` with `r4=0` (`0x82B6A890-0x82B6A8A4`, non-freeing destructor). `PlugIn::Event` tail-dispatches vtable `+0x04` while preserving `r4/r5` (`0x82B6A8F8-0x82B6A904`).

#### 3.6.1 `ReleaseEvent` @ `0x82BA0C18`

##### (a) Exact signature

```cpp
virtual void SubMix::ReleaseEvent();
```

IDA presents an `int` result because `r3` contains the last callee/passthrough value. The vendor virtual is `void`; callers ignore the machine value. Vendor shape wins.

##### (b) Full instruction-range table

| Address range | Instructions covered | Exact effect |
|---|---|---|
| `0x82BA0C18-0x82BA0C20` | LR save; stack frame | Enter 0x60-byte frame. |
| `0x82BA0C24-0x82BA0C28` | preserve self in `r6`; branch to head test | Set up disconnect loop. |
| `0x82BA0C2C-0x82BA0C30` | `r4=0`; call `SubMixConnector::Disconnect` | Disconnect current head with no de-click fold-back array. The callee removes it from `mSendList`. |
| `0x82BA0C34-0x82BA0C3C` | load `mSendList.phead`; test; loop branch | Repeat until the inbound connector list is empty. |
| `0x82BA0C40-0x82BA0C48` | load/test `mSubMixAdded`; branch | Skip registry removal unless the deferred add handler ran. |
| `0x82BA0C4C-0x82BA0C64` | global address; form node; load/compare head; conditional head=`head->next` | If this node is the global head, advance `sSubMixList.phead`. |
| `0x82BA0C68-0x82BA0C78` | load node `pprev`; null test; load `pnext`; store to `pprev->pnext` | Repair the previous neighbor when present. |
| `0x82BA0C7C-0x82BA0C8C` | load node `pnext`; null test; load `pprev`; store to `pnext->pprev` | Repair the next neighbor when present. |
| `0x82BA0C90-0x82BA0CA4` | load buffer; null test; `r5=0`; load System; call `System::Free` | Free `mpSubMixBuffer` with null allocator override when non-null. It does **not** clear the member afterward. |
| `0x82BA0CA8-0x82BA0CB4` | frame release; LR restore; `blr` | Return (source signature is void). |

##### (c) Constants / raw bytes

The vtable slot bytes are in the table above. `sSubMixList` is BSS at `vaddr 0x8327EE68`, exact derived `file_off 0x1281E68`, beyond the raw image; no rodata constants are loaded.

##### (d) Member-offset/access table

| Offset | Vendor member | Access/effect |
|---:|---|---|
| `PlugIn+0x04` | `mpSystemUseGetSystemAccessor` | System for free |
| `SubMix+0x24` | `mpSubMixBuffer` | conditionally freed, not nulled |
| `SubMix+0x28` | `mSendList.phead` | repeatedly disconnected until null |
| `SubMix+0x2C/+0x30` | `mSubMixListNode.{pnext,pprev}` | global registry unlink |
| `SubMix+0x8C` | `mSubMixAdded` | guards registry unlink; not cleared |

##### (e) Implementation-grade C++

```cpp
void SubMix::ReleaseEvent()
{
    while (ListDNode *node = mSendList.phead)
        SubMixConnector::GetConnectorFromNode(node)->Disconnect(nullptr);

    if (mSubMixAdded)
    {
        ListDNode *node = &mSubMixListNode;
        if (node == sSubMixList.phead)
            sSubMixList.phead = node->pnext;
        if (node->pprev)
            node->pprev->pnext = node->pnext;
        if (node->pnext)
            node->pnext->pprev = node->pprev;
    }

    if (mpSubMixBuffer)
        System::Free(mpSystemUseGetSystemAccessor, mpSubMixBuffer, nullptr);
    // Faithful: ARTIST does not clear mpSubMixBuffer or mSubMixAdded here.
}
```

#### 3.6.2 inherited `EventEvent` slot @ `0x8284CB38`

##### (a) Exact signature

```cpp
virtual void PlugIn::EventEvent(int event, void *pParameterBuffer);
```

SubMix does not override it in vendor `submix.h`.

##### (b) Full instruction-range table

| Address | Instruction | Exact effect |
|---|---|---|
| `0x8284CB38` | `blr` | No-op; returns immediately with `r3/r4/r5` untouched. Source ABI is void. |
| `0x8284CB3C` | `.long 0` | Post-function alignment data, not executed. |

##### (c) Constants / raw bytes

Only the vtable pointer word `82 84 CB 38` at `vaddr 0x8217F558`, `file_off 0x182558`. No function rodata.

##### (d) Member access table

No members or arguments are read.

##### (e) Implementation-grade C++

No SubMix definition is needed; inherit the correct base no-op implementation. If the base must be reconstructed explicitly: `void PlugIn::EventEvent(int, void *) {}`.

#### 3.6.3 inherited `GetPpuTicksEvent` slot @ `0x827E2F38`

##### (a) Exact signature

```cpp
virtual unsigned int PlugIn::GetPpuTicksEvent() const;
```

Name/constness: DecFIGS `plugin.h:337/459`; body and vtable slot: ARTIST.

##### (b) Full instruction-range table

| Address | Instruction | Exact effect |
|---|---|---|
| `0x827E2F38` | `li r3,0` | Return zero PPU ticks. |
| `0x827E2F3C` | `blr` | Return. |

##### (c) Constants / raw bytes

Only the vtable pointer word `82 7E 2F 38` at `vaddr 0x8217F55C`, `file_off 0x18255C`. Zero is an instruction immediate.

##### (d) Member access table

No members are read; `this` is unused.

##### (e) Implementation-grade C++

No SubMix override is needed. The correct base body is `unsigned int PlugIn::GetPpuTicksEvent() const { return 0; }`.

#### 3.6.4 deleting destructor @ `0x82BA1DE8`

##### (a) Exact machine/helper signature

```cpp
SubMix *SubMix_deleting_destructor(SubMix *self, unsigned int flags);
```

IDA names this ``SubMix::`vector deleting destructor'`` and types the low flags input as `char`. Only `flags & 1` is consumed. There is no element count, array loop, or separately exported scalar-deleting SubMix body. Semantically this is the ordinary MSVC deleting-destructor helper used by vtable slot 3.

##### (b) Full instruction-range table

| Address range | Instructions covered | Exact effect |
|---|---|---|
| `0x82BA1DE8-0x82BA1DF4` | LR save; save `r31`; frame | Enter 0x60-byte frame. |
| `0x82BA1DF8-0x82BA1E08` | materialize base vtable; preserve self; extract flags bit 0; store vptr | Set `self`'s vptr to base `PlugIn` vtable `0x820AA810`; test `flags & 1`. |
| `0x82BA1E0C-0x82BA1E10` | conditional branch; call `operator delete` | Free `self` only when bit 0 is set. `r3` still holds `self` at the call. |
| `0x82BA1E14-0x82BA1E28` | restore return `self`; frame/LR/`r31`; `blr` | Return the original pointer even on the deleting path, per compiler-helper ABI. |

##### (c) Constants / raw bytes

| Constant | vaddr | file_off | Raw bytes (BE) | Decoded value |
|---|---:|---:|---|---|
| SubMix vtable slot | `0x8217F560` | `0x182560` | `82 BA 1D E8` | deleting destructor target |
| base PlugIn vtable | `0x820AA810` | `0xAD810` | `82 84 CB 38 82 84 CB 38 82 7E 2F 38 82 68 04 18` | four base virtual targets; the destructor stores this table address |

##### (d) Member-offset/access table

Only hidden vptr `SubMix+0x00` is stored. No SubMix data member is destroyed; the lists/buffer are handled by `ReleaseEvent`, not this helper.

##### (e) Implementation-grade C++

Portable source should declare an empty virtual derived destructor and let the host compiler generate its deleting helper:

```cpp
SubMix::~SubMix() = default;
```

The framework must call `ReleaseEvent()` before destructor dispatch, as ARTIST does on create failure. A low-level semantic sketch of the generated X360 helper is:

```cpp
SubMix *DeletingDestructor(SubMix *self, unsigned flags)
{
    // normal C++ destruction resets the vptr to the PlugIn base identity
    self->~SubMix();
    if (flags & 1)
        ::operator delete(self);
    return self;
}
```

Do not manually store raw vtable addresses in the PC class.

### 3.7 SubMix add/remove/enumeration globals and `Send::ConnectByNameHandler` @ `0x82B9FF80`

No standalone ARTIST symbols named `SubMix::AddSubMix` or `SubMix::RemoveSubMix` exist, and the vendor `submix.h` does not declare them. The requested operations are fully present as inlined `ListDStack::Push` in `CreateInstanceHandler` (section 3.4) and inlined `ListDStack::Remove` in `ReleaseEvent` (section 3.6.1). The global enumeration helpers are inlined into `Send::ConnectByNameHandler`.

Evidence: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B9FF80.json`; vendor `submix.h` and `private/linklist.h`; current implementation at `b5-decomp/vendor/renderware/src/rw/audio/core/Send_wL_01.cpp`.

#### (a) Exact signatures at call/dispatch

```cpp
static void SubMix::EnumerateSubMixReset();
static SubMix *SubMix::EnumerateSubMix();
static int Send::ConnectByNameHandler(Command *pCommand);
```

ARTIST's concrete name command is variable-sized:

```cpp
// X360 offsets only
struct SendConnectByNameCommand {
    int (*handler)(Command *); // +0x00
    Send *pObject;             // +0x04
    unsigned int size;         // +0x08; handler return / ring advance
    char name[1];              // +0x0C; inline NUL-terminated bytes
};
```

This intentionally conflicts with Feb `ConnectByNameParams { const char *pName; }`; ARTIST byte-loads the inline payload and wins.

#### (b) Full instruction-range table for the live consumer

| Address range | Instructions covered | Exact effect |
|---|---|---|
| `0x82B9FF80-0x82B9FF90` | LR/`r30`/`r31` saves; frame | Enter 0x70-byte frame. |
| `0x82B9FF94-0x82B9FFA0` | preserve command; load `command+4`; pass Send; call `DisconnectImmediate` | Disconnect any previous target before searching. |
| `0x82B9FFA4-0x82B9FFB8` | materialize both globals; preserve `command+8` and name `command+0x0C`; load list head; store cursor | Inline `EnumerateSubMixReset`: `spSubMixNextNode = sSubMixList.GetHead()`. `r3` remains `&command->size` for the final return. |
| `0x82B9FFBC` | branch to node test | Enter top-tested enumeration loop. |
| `0x82B9FFC0-0x82B9FFC4` | form `submix->mName`; copy command-name pointer | Set up bytewise comparison. |
| `0x82B9FFC8-0x82B9FFD8` | load command byte; load SubMix byte; test command NUL; subtract; early branch | Compute `commandByte - subMixByte`; terminate at command NUL or mismatch. |
| `0x82B9FFDC-0x82B9FFE8` | increment both pointers; compare difference; loop while equal | Continue bytewise `strcmp` behavior. |
| `0x82B9FFEC-0x82B9FFF0` | test final difference; equal branch | On exact equality, connect; otherwise enumerate next. |
| `0x82B9FFF4-0x82B9FFF8` | test current node; null exit | End at list exhaustion. |
| `0x82B9FFFC-0x82BA0008` | subtract container offset with CR result; load node next; store cursor; branch if owner nonnull | Inline `EnumerateSubMix`: convert node to `SubMix *` using `-0x2C`, advance `spSubMixNextNode = node->pnext`, and return/test the owner. |
| `0x82BA000C` | branch exit | Stop if the computed owner is null. |
| `0x82BA0010-0x82BA0028` | form connector `send+0x30`; zero; store SubMix; load/store buffer pointer; load/store output-channel byte | Set `connector.mpSubMix`, `mpSubMixBuffer`, and `mNumSubMixChannels`. |
| `0x82BA002C-0x82BA0034` | load SubMix send-list head; clear connector prev; store old head as connector next | Prepare head insertion into `SubMix::mSendList`. |
| `0x82BA0038-0x82BA0044` | reload old head; null test; conditional store connector to old-head prev | Repair old head's `pprev`. |
| `0x82BA0048` | store connector to `SubMix+0x28` | Publish connector as new `mSendList` head; first name match terminates search. |
| `0x82BA004C` | `lwz r3,0(r3)` | Return `command->size`, the exact ring advance, whether or not a match was found. |
| `0x82BA0050-0x82BA0064` | frame/LR/nonvolatile restores; `blr` | Return to `System::ExecuteCommands`. |

#### (c) Constants / globals with raw status

| Symbol | vaddr | derived file_off | Raw bytes/value |
|---|---:|---:|---|
| `SubMix::spSubMixNextNode` | `0x8327EE00` | `0x1281E00` | **BLOCKED raw bytes:** beyond XEX length `0x105B000`; BSS static, initially null |
| `SubMix::sSubMixList` (`phead`) | `0x8327EE68` | `0x1281E68` | **BLOCKED raw bytes:** beyond XEX length `0x105B000`; BSS static, initially null |

There is no rodata in the handler.

#### (d) Member-offset/access table

| Object + X360 offset | Vendor member | Access/effect |
|---|---|---|
| command `+0x04` | `Command::pObject` | target `Send *` |
| command `+0x08` | variable record `size` | returned ring advance |
| command `+0x0C` | ARTIST inline name | bytewise compared; **not a pointer field** |
| `Send+0x30` | `mSubMixConnector.mListNode.pnext` | old inbound-list head |
| `Send+0x34` | `mSubMixConnector.mListNode.pprev` | null for new head |
| `Send+0x38` | `mSubMixConnector.mpSubMixBuffer` | copied from SubMix `+0x24` |
| `Send+0x3C` | `mSubMixConnector.mpSubMix` | matched SubMix pointer |
| `Send+0x40` | `mSubMixConnector.mNumSubMixChannels` | copied byte from inherited SubMix output channels |
| `SubMix+0x21` | `PlugIn::mOutputChannels` | copied to connector byte |
| `SubMix+0x24` | `mpSubMixBuffer` | copied to connector pointer |
| `SubMix+0x28` | `mSendList.phead` | connector head insertion |
| `SubMix+0x2C` | `mSubMixListNode` | container-of base for global registry |
| `SubMix+0x4C` | `mName` | comparison string |

#### (e) Implementation-grade C++

The SubMix-owned helpers are:

```cpp
void SubMix::EnumerateSubMixReset()
{
    spSubMixNextNode = sSubMixList.phead;
}

SubMix *SubMix::EnumerateSubMix()
{
    ListDNode *node = spSubMixNextNode;
    if (!node)
        return nullptr;
    SubMix *result = reinterpret_cast<SubMix *>(
        reinterpret_cast<char *>(node) - offsetof(SubMix, mSubMixListNode));
    spSubMixNextNode = node->pnext;
    return result;
}
```

The live Send consumer is already implemented in `Send_wL_01.cpp`; the essential host-safe form is:

```cpp
int Send::ConnectByNameHandler(Command *base)
{
    auto *command = reinterpret_cast<SendConnectByNameCommand *>(base);
    Send *send = command->pObject;
    send->DisconnectImmediate();

    SubMix::EnumerateSubMixReset();
    while (SubMix *subMix = SubMix::EnumerateSubMix())
    {
        if (std::strcmp(command->name, subMix->GetName()) == 0)
        {
            send->mSubMixConnector.Connect(send->GetVoice(), subMix);
            break;
        }
    }
    return static_cast<int>(command->size); // host record's stored size
}
```

The actual existing PC record names are `mpHandler`, `mpTarget`, `muRecordSize`, and `maName`; use those names rather than creating a duplicate record. Its producer already computes a host 8-byte-aligned size.

Static definitions remain:

```cpp
ListDStack SubMix::sSubMixList = {};
ListDNode *SubMix::spSubMixNextNode = nullptr;
```

### 3.8 Consolidated host header blueprint

The partial `SubMix` currently embedded in `SubMixConnector.h` should be replaced/moved, not duplicated. Subject to correcting the base virtual declarations noted in section 2, the implementation-facing class shape is:

```cpp
class SubMix : public PlugIn
{
public:
    static constexpr Guid GUID = 0x53756230u; // 'Sub0'
    struct ConstructorParams { const char *pName; };

    static PlugInDescRunTime *GetPlugInDescRunTime();
    static unsigned int GetSize(PlugInConfig *);
    static bool CreateInstance(PlugIn *, void *);
    static BufferStatus Process(PlugIn *, Mixer *, bool);
    ~SubMix() override = default;

private:
    friend class SubMixConnector;
    friend class Send;
    friend class Route;
    friend class System;

    float *GetBuffer() { return mpSubMixBuffer; }
    const char *GetName() { return mName; }
    static void EnumerateSubMixReset();
    static SubMix *EnumerateSubMix();
    static int CreateInstanceHandler(Command *);
    void ReleaseEvent() override;

    static PlugInDescRunTime sPlugInDescRunTime;
    static ChannelMapPair sChannelMaps[];
    static ParameterDescRunTime sParameterDescRunTime[];
    static ListDStack sSubMixList;
    static ListDNode *spSubMixNextNode;

    float *mpSubMixBuffer;
    ListDStack mSendList;
    ListDNode mSubMixListNode;
    float mDeClickValueTotal[MAX_CHANNELS];
    char mName[64];
    unsigned char mSubMixAdded;
    unsigned char mDeClickRequired;
};
```

Use natural x64 layout and named member access. Do not add padding to reproduce the X360 offsets; `GetSize` and all command/container calculations must derive from host types.

## 4. x64/host-porting hazards

1. **`GetSize` must return host `sizeof(SubMix)`.** The X360 immediate `0x90` includes 4-byte pointers. Returning it on x64 under-allocates the derived object.
2. **Every pointer-bearing member widens.** This includes the hidden vptr; inherited `PlugIn::{mpSystemUseGetSystemAccessor,mpVoice,mpAttribute,mpPlugInDescRunTime}`; `SubMix::mpSubMixBuffer`; `mSendList.phead`; both `mSubMixListNode` links; static `sSubMixList.phead` and `spSubMixNextNode`; all four pointer-bearing `SubMixConnector` fields; descriptor callbacks/metadata pointers; Mixer/SampleBuffer pointers; and every command handler/object pointer. Access by named members only.
3. **The console container offset `0x2C` is not a host constant.** `EnumerateSubMix()` and Send's consumer must use `offsetof(SubMix,mSubMixListNode)` or a typed owner helper.
4. **The create-command record stride widens from 8 to 16 bytes.** Both `CreateInstance`'s producer advance and `CreateInstanceHandler`'s return must be `sizeof(SubMixCreateCommand)` on the host. A hard-coded 8 causes the next record to overwrite the widened `SubMix *` and makes command replay desynchronize.
5. **The Send name record also changes header/stride.** ARTIST uses 12 bytes before the inline name and four-byte alignment; host handler/target pointers make the header larger and the next handler pointer needs eight-byte alignment. Preserve the stored host `muRecordSize` and return it. Do not port Feb's by-pointer name record into this ARTIST path.
6. **Descriptor pointers widen and the descriptor field sequence is ARTIST-specific.** Do not copy the raw 52 X360 bytes or the Feb PS3/SPU descriptor layout. Initialize the current host descriptor by named fields with `pPreProcess=null` and `pProcess=&SubMix::Process`.
7. **The constructor name copy is unbounded.** ARTIST copies through NUL into `char mName[64]` with no length check. A 64-byte-or-longer name (or null `params->pName`) overflows/crashes. A safety hardening would diverge from ARTIST; if introduced, it must be an explicit policy decision rather than silent decomp behavior.
8. **Allocation math must use host `size_t`.** ARTIST's zero-extended byte channel count makes `rotlwi 10` equal `channels * 1024`; express it as `channels * 256 * sizeof(float)`. Do not carry a general rotate into PC code.
9. **Do not preserve raw vptr stores.** Define `SubMix : public PlugIn`, preserve the original virtual order in the base, and let placement construction/destruction install host vtables. A second explicit vptr or `char mHeader00` creates a divergent x64 layout.
10. **No console pointer is narrowed into a 16-bit or byte field in any decoded SubMix/list/Send path.** All pointers use `lwz/stw` word slots on X360 and must become full host pointers. The byte store at connector `+0x10` copies `mOutputChannels`, not a pointer; the halfword load at SampleBuffer `+0x0E` is a sample stride, not a pointer. Separately, the generic Voice factory stores the `GetSize` result in a 16-bit size slot (`0x82B6EE08`), but that value is a byte count, not a pointer.
11. **Release and destruction are separate.** `ReleaseEvent` drains connectors/removes the global node/frees the buffer; the deleting destructor only resets base identity and optionally frees the object. Do not move release side effects into the destructor unless the whole framework call order is deliberately changed.
12. **Faithful stale fields after release.** ARTIST does not clear `mpSubMixBuffer` or `mSubMixAdded` after freeing/unlinking. Clearing them is safer but is additional behavior; the direct decompile should document rather than silently add it.

## 5. Verification

### Claim-by-claim assembly recheck

| Claim | Recheck result and concrete evidence |
|---|---|
| X360 `sizeof(SubMix)==0x90` | PASS: `0x82B982F0 li r3,0x90`; vendor fields tile `0x24..0x8D` and tail-align to `0x90`. |
| `GetSize(PlugInConfig *)` callback shape | PASS: vendor `submix.h`/`pluginregistry.h`; generic call at `0x82B6EC98-0x82B6ECA8` passes config in `r3`; descriptor raw `0x82F902E4` points to the body. |
| `CreateInstance(PlugIn *,void *) -> bool` | PASS: generic dispatch `0x82B6A864-0x82B6A874` passes self/constructor params and tests low result byte; descriptor raw `0x82F902E8`. |
| Derived construction only initializes vptr and send-list head | PASS: `0x82BA469C-0x82BA46A8`; no other base member is overwritten by this block. |
| Name copy is unbounded and includes NUL | PASS: every instruction `0x82BA46B8-0x82BA46D4` rewalked; no counter/bounds branch exists. |
| Allocation is channels * 1024, alignment 128, null override | PASS: `lbz +0x21`, `rotlwi 10`, args at `0x82BA46E0-0x82BA4700`; string bytes reread at `0x17E098`. |
| Buffer member is stored on failure too | PASS: `cmplwi r3,0` at `0x82BA4704` is followed by unconditional `stw r3,0x24(r31)` at `0x82BA4708`, before branch `0x82BA470C`. |
| Concrete handler address is `0x82B9C380` | PASS: relocation materialized at `0x82BA4728-0x82BA4730`; raw handler dossier independently starts at `0x82B9C380`. |
| X360 create record is 8 bytes and handler returns its stride | PASS: producer `cursor += 8` at `0x82BA4748`, two word stores `0x82BA4750/54`; handler `li r3,8` at `0x82B9C3B4`; command consumer advances by returned `r3` at `0x82B6F804`. |
| Handler pushes the SubMix node and sets added flag | PASS: every instruction `0x82B9C380-0x82B9C3BC` mapped to `ListDStack::Push`; offsets exactly `+0x2C/+0x30/+0x8C`. |
| Process exact dispatch signature | PASS: vendor `ProcessFn`; `Mixer::Execute` indirect call at `0x82B6DA90-0x82B6DA9C` sets `r3=plugin,r4=mixer,r5=bool`; body leaves `r5` unread. |
| Process swaps src/dst before copy | PASS: load/store quartet `0x82B9C4A4-0x82B9C4B0`; current Mixer names match `+0x3000C/+0x30010`. |
| Per-channel copy is 256 floats | PASS: `li r5,0x400` and source offset `+=0x400`; destination uses `lhz +0x0E`, multiply channel, shift by 2. |
| De-click occurs after copy and before private-buffer clear | PASS: copy loop ends `0x82B9C4F8`; flag/call `0x82B9C4FC-0x82B9C518`; clear flag; `XMemSet` only at `0x82B9C524-0x82B9C534`. |
| Process always returns available | PASS: `li r3,1` at `0x82B9C538`; no earlier return. |
| Vtable has exactly four slots | PASS: raw words reread at `0x182554..0x182560`; previous table ends at `0x182550`; next table begins `0x182564` with `0x82B9C548` (`TimeStretch::ReleaseEvent`). |
| Slot identities/order | PASS: named Release/dtor dossiers; empty/zero shared bodies; vendor/DecFIGS virtual order; generic dispatch at vtable `+0/+4/+0xC`. ICF alias names were explicitly ignored. |
| Release drains all inbound connectors | PASS: loop `0x82BA0C28-0x82BA0C3C` reloads `mSendList.phead` after each `Disconnect(head,null)`. |
| Release removes from global list only if added | PASS: `lbz +0x8C` gate and complete doubly-linked remove at `0x82BA0C40-0x82BA0C8C`. |
| Release frees but does not null buffer | PASS: only load/test/call at `0x82BA0C90-0x82BA0CA4`; no following store to `+0x24`. |
| Deleting destructor tests only bit 0 | PASS: `clrlwi. r10,r4,31` at `0x82BA1E04`; only conditional operation is `operator delete`. No array loop/count. |
| Registry cursor reset/advance | PASS: `0x82B9FFB4-0x82B9FFB8` stores head to cursor; `0x82B9FFFC-0x82BA0004` computes owner, loads next, stores next to cursor. |
| Send command name is inline | PASS: handler forms `r4=command+0x0C` and byte-loads it; no pointer load. This explicitly overrides Feb `send.h`. |
| Send returns stored record size on every path | PASS: all match/no-match exits converge at `0x82BA004C lwz r3,0(r3)`, with `r3` preserved as `command+8`. |
| Connector insertion fields | PASS: every load/store `0x82BA0010-0x82BA0048` mapped to vendor `SubMixConnector` and `mSendList` fields. |
| Raw file-off arithmetic | PASS: all cited backed offsets were recomputed with the required formula and reread from the XEX. Examples: `0x8217F554 -> 0x182554`, `0x8217B098 -> 0x17E098`, `0x82F902E0 -> 0xF932E0`, `0x820AA810 -> 0xAD810`. |

### BLOCKED / genuinely unrecoverable points

1. **Raw bytes for `0x8327EE00` and `0x8327EE68`: BLOCKED by unbacked BSS.** Their exact formula-derived offsets are `0x1281E00` and `0x1281E68`, both beyond the XEX's `0x105B000` bytes. No byte value can honestly be quoted from the raw file. Their runtime roles and all accesses are completely recovered from ARTIST assembly; initial null is the static/BSS initialization contract.
2. **Unique symbol provenance for the ICF stubs: BLOCKED by code folding.** `0x8284CB38` and `0x827E2F38` have unrelated IDA primary names because many identical bodies share those addresses. Their SubMix vtable identities are nevertheless implementation-complete from slot order, source declarations, and exact bodies.
3. **Standalone `AddSubMix`, `RemoveSubMix`, and ARTIST `EnumerateSubMix` code ranges do not exist.** This is not missing behavior: add/remove are the fully decoded inline list ranges in `CreateInstanceHandler`/`ReleaseEvent`, and enumeration is the fully decoded inline range in `Send::ConnectByNameHandler`. Inventing separate ARTIST addresses would be false.
4. **No separate scalar-deleting SubMix export exists.** The only SubMix helper in the ledger/vtable is `0x82BA1DE8`, named vector-deleting by IDA but consuming only delete flag bit 0. Its complete behavior is decoded; a second body must not be invented.

No functional SubMix behavior requested by this dossier remains blocked.
