# `rw::audio::core::SndPlayer1` streaming verification

Scope: ARTIST `Process` @ `0x82BA0568`, raw-XEX `EventEvent` @ `0x82BA5C48`,
`ReleaseEvent` @ `0x82BA4178`, `RwacTimerClient` @ `0x82BA6980`, and every
unbodied SndPlayer1 helper reachable from those four. I read the current host headers before
writing the bodies below. The `assembly` fields were used for every exported function.
`EventEvent`, `Decoder::Feed` @ `0x82B67920`, `DecoderRegistry::DecoderFactory` @
`0x82B6C778`, `StreamPool::GetInstance` @ `0x82B6BA68`, and the stream byte query @
`0x82BBD948` were hand-disassembled from
`IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex` as PPC32 big-endian, using
`file_offset = 0x3000 + vaddr - 0x82000000`.

## 1. VERDICT TABLE

Corrections and refutations lead. A row is one banked claim (or one tightly coupled claim
cluster) checked against the instructions shown.

| Verdict | Banked claim checked | Verified result and proving instruction(s) |
|---|---|---|
| **CORRECTED** | Process feed rollover stops when `mpLoadedDecoder == 0` (or when the next feed is not FED). | The banked sketch's two `break`s are wrong. After either test, ARTIST goes to `0x82BA0AF4`, tests `remainingInFeed`, and—because it is still zero—takes `0x82BA0AF8 -> 0x82BA0A50`. Thus a null loaded decoder still retires every consecutive FED record; a non-FED record is what the loop-top test stops on. Proof: `0x82BA0A88..0x82BA0AFC`. The Process body below preserves that back-edge. |
| **CORRECTED** | `DecoderRequest` has one pointer and is 24 bytes on x64. | It has **two** pointers. `Decoder::Feed` stores `r4` at request `+0` and `r8` at `+4` (`0x82B6795C`, `0x82B67964`). `SubmitChunk` loads `r8` from `RequestExternal+0x38` (`0x82BA464C`), and `SetSeekData` copies `SeekTableParser::mpSeekData` there (`0x82B9C0E0..0x82B9C0E4`). With two widened pointers the faithful x64 record is **32 bytes**, not 20 or 24. |
| **REFUTED** | Decoder request stride `0x14` is pointer-free / survives x64 (still stated in the Process section). | Both leading console words are pointers. All `0x14` ring arithmetic must be typed indexing: Process `0x82BA0830`, `0x82BA0AB4`; FeedCleanup `0x82BA02C4`; raw `Decoder::Feed` `0x82B6793C`; raw factory allocation/init `0x82B6C7B0`, `0x82B6C948`. |
| **CORRECTED** | Process's host `RequestInternal` size is `0x38`. | The current declared host record is 48 bytes (`f64`, widened pointer, then 32 bytes of scalars): it lands on **`0x30` by coincidence**. The bank's leading verifier says this correctly, but the Process hazard says `0x38`. The console pointer is proved by `lwz r11,8(r30)` at `0x82BA0818`; typed indexing remains mandatory even though the sizes currently coincide. |
| **REFUTED** | The banked `RequestExternal+0x38` `s32 mSeekBlockA` is usable. | It is `SeekTableParser::mpSeekData`, a pointer: load/copy at `0x82B9C0E0..0x82B9C0E4`, then passed in `r8` at `0x82BA464C`. The **current** header has now corrected this to `u8 *pSeekData`; retain that correction. |
| **REFUTED** | The banked `Decoder::Feed(..., u32 uReserved04, ...)` declaration is usable. | The fifth explicit argument is a seek-data pointer (`0x82BA464C`; stored at `0x82B67964`). The **current** header has now corrected both it and `DecoderRequest::mpSeekData` to `const u8 *`; retain those corrections. |
| **CORRECTED** | Plain C++ `(s64)double` matches `fctidz` in PlayHandler and HandleSampleEnd. | It matches only finite in-range inputs. `fctidz` occurs at `0x82BA43E4`, `0x82BA4478`, `0x82BA631C`, and `0x82BA6400`; it saturates before the low bits are consumed. NaN produces the `INT64_MIN` pattern, huge positive produces `INT64_MAX`. A C++ out-of-range cast is not the required operation. |
| **CORRECTED** | Event's expel conversion may be `static_cast<u8>(static_cast<s64>(f))`. | `fctidz`/`stfd`/`lbz stack+7` at `0x82BA6024..0x82BA6030` stores the low byte of the saturated 64-bit result. Reuse an exact PPC conversion helper; NaN and overflow are observably different from an x64 cast. |
| **CORRECTED** | PlayHandler's seek sample conversion can be a plain `s32` cast. | `fctiwz` + `stfiwx` at `0x82BA4288..0x82BA4290` yields PPC's integer-indefinite `0x80000000` on NaN/out-of-range. The host needs an explicit `PpcFctiwz`, not an out-of-range C++ cast. |
| **CORRECTED** | RwacTimerClient can advance request indices with `% mMaxRequests`. | All three sites truncate the increment to a byte and reset **only on equality**: `0x82BA6A68..0x82BA6A80`, `0x82BA6C08..0x82BA6C28`, `0x82BA6C3C..0x82BA6C58`. `%` changes the `mMaxRequests==0` and corrupted-cursor cases. |
| **REFUTED** | The timer's zero-sample scan can loop forever only if it encounters a non-zero sample request. | A non-zero sample count terminates the scan. It can loop forever when every revisited request is active and has `numSamples==0`; see the back-edge `0x82BA6ABC -> 0x82BA6A60`. A one-entry active zero-length ring is sufficient. |
| **CORRECTED** | The GUID lookup should be an eight-element C++ array indexed without a check. | The asset codec is 4 bits (`0x82B9BF50..0x82B9BF68`), and StartRequest does an unchecked indexed load (`0x82BA647C..0x82BA6494`). Indices 8..15 read eight words of the adjacent allocation-name string. A host eight-element array creates C++ OOB UB; the faithful finite lookup is the 16 attested words listed below. |
| **CORRECTED** | What `DecoderFactory` does with a null descriptor is unverified. | Raw body: `r30=r4` at `0x82B6C784`, then unconditional `lwz r11,0(r30)` at `0x82B6C798`. Null is dereferenced before a decoder result exists. StartRequest's later result-null test does not protect a missing descriptor. |
| **CORRECTED** | First QueueFile offset is `(s64)base + (s32)chunkOffset`. | Base is `fctidz`; `RequestExternal+0x40` is loaded with **`lwz`**, not `lwa`, then added (`0x82BA43E4..0x82BA4404`). The addend is zero-extended `u32`. Loop offsets deliberately use `lwa` before `fcfid` at `0x82BA444C` and `0x82BA62F0`/`0x82BA63D4`. |
| **CORRECTED** | QueueFile is a six-argument/static-shaped call with a “flags” zero. | Thunk `0x82BC09B0` shifts `r5..r7` and inserts `r5=0`; the actual homed member is `Stream::QueueFile(path, Handle *preOpen, u64 value, callback, context)`. The zero is a null pre-open handle. |
| **REFUTED** | `StreamPool` is the only host prerequisite missing. | It is the only wholly missing **top-level type**, but not the only missing surface: `DecoderRegistry::DecoderFactory` is undeclared/unbodied; Decoder's instance-size word has no named member/accessor; `DecoderDesc`'s factory callback prefix is opaque/unpopulated; and `DecoderBuffer` is only partially typed for the factory path. The seek-pointer fixes are present in the current tree. The two stream byte-query symbols also lack declarations, although their behavior can be written through already-homed typed fields. |
| **CORRECTED** | The PC byte order for SubmitChunk/ChunkParsed is unresolved. | The instruction stream proves native BE loads on X360 (`0x82BA458C..0x82BA45B8`, `0x82BA400C..0x82BA402C`). The current PC asset pipeline settles the host side: `GenericRwacWaveContent`/SNR and `.SNS` bodies are **big-endian by format** and deliberately passed through (`tools/assets/bundles/engine_transcode.py`, `tools/assets/game_data_manifest.toml`). Explicit `ReadBe32`/`WriteBe32` is therefore the current faithful PC spelling. |
| **CORRECTED** | ReleaseEvent's timer-byte compare is at `0x82BA4190`. | `0x82BA4190` is the `lbz`; the equality compare is `cmplwi r11,1` at `0x82BA4194`. The substantive `mbTimerAdded == 1` gate remains correct. |
| **CORRECTED** | The Process sketch is written against current names. | It uses non-existent `samplesToSkip`, `seekStreamSampleOffset`, and `seekDecoderSampleOffset`. Current names are `numSamplesToSkipPlayer`, `numSamplesToSkipStream`, and `numSamplesToSkipDecoder`; the initial played count loads `+0x24` then `+0x20` at `0x82BA0938..0x82BA0940`. |
| **CORRECTED** | Hoisting the `StackAllocator` dereference to Process entry is literally faithful. | The binary first dereferences `System::mpObjectTable` only at the carve (`0x82BA07EC..0x82BA0810`) and reloads it for restore/re-carve (`0x82BA09C0..0x82BA0A40`, `0x82BA0B08..0x82BA0B1C`). Hoisting adds reads on invalid/no-feed/future-start paths. The body below does not hoist it. |
| **CONFIRMED** | Process's third parameter is unused. | `r5` is overwritten with zero at `0x82BA05C4` before any read. Current host signature `Process(SndPlayer1*, AudioProcessContext*, bool)` is usable. |
| **CONFIRMED** | Process dispatches Declick only when both bytes are non-zero. | `lbz`/zero branches at `0x82BA057C..0x82BA0598`. |
| **CONFIRMED** | Process retires consecutive active zero-length requests as COMPLETE. | State test and loop at `0x82BA05C8..0x82BA0660`. |
| **CONFIRMED** | Format change publishes an empty available frame and adopts rate/channels. | Compares at `0x82BA0664..0x82BA0680`; stores at `0x82BA0BD0..0x82BA0C0C`. Unordered sample-rate comparison takes the handshake, matching `!=`. |
| **CONFIRMED** | Feed consume scan snapshots the fill cursor, commits every cursor advance, and accepts only state 1. | `0x82BA0684..0x82BA06F8`. |
| **CONFIRMED** | Near-future silence is capped by unsigned `min(frames,mSamplesRequested)`. | `cmplw`/`blt`/move at `0x82BA073C..0x82BA0748`; channel clearing and swap at `0x82BA0750..0x82BA07E4`. |
| **CONFIRMED** | First scratch carve has no decoder-null guard; every carve path restores. | First carve/dereference `0x82BA07EC..0x82BA0828`; mid-body restore `0x82BA09C0..0x82BA09CC`; guarded re-carve `0x82BA09F8..0x82BA0A48`; epilogue restore `0x82BA0AFC..0x82BA0B1C`. |
| **CONFIRMED** | Skip/decode comparisons are signed; skip loop is `!=0`; main Decode runs at count zero. | `0x82BA0870..0x82BA08F4`. |
| **CONFIRMED** | Process initializes played count with stream-skip + decoder-skip, publishes/swallows buffers, and rolls feeds exactly as banked. | `0x82BA0924..0x82BA0988`, `0x82BA098C..0x82BA0AF4`. |
| **CONFIRMED** | Status zero leaves `Mixer::mNumSamples` stale while always publishing cached format. | Format stores `0x82BA0B20..0x82BA0B34`; unavailable return path `0x82BA0B38..0x82BA0B50`. |
| **CONFIRMED** | Last-sample capture uses min(output channels, max channels) and arms only `mDcOffsetsGathered`. | `0x82BA0B54..0x82BA0BCC`. |
| **CONFIRMED** | EventEvent has no dossier and uses a linear IDs 0..5 dispatch; other IDs are no-ops. | Raw `0x82BA5C64..0x82BA5C7C`, `0x82BA5CA8`, `0x82BA5D0C`, `0x82BA5E94`; epilogue `0x82BA6068`. |
| **CONFIRMED** | STOP producer advances before stores; handler must return the matching host record size. | Producer console sequence `0x82BA5C80..0x82BA5CA0`; handler console return 8 at `0x82BA454C`. Both become `sizeof(StopCommand)` on host. |
| **CONFIRMED** | ISREQUESTDONE's unusual ordered/unordered truth condition is banked correctly. | `fcmpu` branches `0x82BA5CBC..0x82BA5CF8`, one output store at `0x82BA5D04`. The faithful predicates are retained below. |
| **CONFIRMED** | GETREQUESTBUFFERED with `mMaxRequests==0` leaves outputs untouched; nonmatching laps write two zeros. | Raw `0x82BA5D14..0x82BA5D20` and `0x82BA5D98..0x82BA5DB4`. |
| **CONFIRMED** | GETREQUESTBUFFERED compares the loop **index** converted to float with attribute 0 (a request handle). | Raw `clrldi`/`fcfid`/`frsp` and `lfs this+0x28` at `0x82BA5E04..0x82BA5E20`. This shipped quirk is preserved. |
| **CONFIRMED** | Stream byte queries are `Stream::miRemaining` or the matching `StreamState::Request::muBufferedBytes`. | Raw `0x82BBD940..0x82BBD944` and `0x82BBD948..0x82BBD98C`. Both are expressible through current `stream.h` fields. |
| **CONFIRMED** | MODIFY producer/handler are a matched deferred record; NaN current start time performs the write. | Producer `0x82BA5E9C..0x82BA5ECC`; handler `fcmpu` + `ble` at `0x82BA0444..0x82BA0450`; console return `0x18` at `0x82BA0454`. |
| **CONFIRMED** | Legacy PLAY is 36 console bytes and expands to the PLAY1 shape; handle wraps strictly above 4194304 to 1.0. | Raw copies `0x82BA5ED4..0x82BA5F24`; counter/`fcmpu`/`ble`/1.0 store `0x82BA5F2C..0x82BA5F60`. Unordered also wraps. |
| **CONFIRMED** | Variable Play record uses fixed head + NUL-terminated path and handler returns the stamped `u16` size. | Producer `0x82BA5F7C..0x82BA6064`; handler `lhz` at `0x82BA44D0`. Host head, alignment, advance, and returned size must agree. |
| **CONFIRMED** | Release order is callback, optional timer removal only for byte exactly 1, then allocation free. | `0x82BA418C`; `0x82BA4190..0x82BA41A4`; `0x82BA41A8..0x82BA41BC`. No fields are cleared. |
| **CONFIRMED** | Timer voice-state 2 returns before cleanup or attributes. | `0x82BA6998..0x82BA69A4`. |
| **CONFIRMED** | Timer calls FeedCleanup then RequestCleanup, always publishes attribute 0, and writes attributes 1/2 as full doubles. | `0x82BA69A8..0x82BA6A4C`. `lwa` makes both numerators signed. |
| **CONFIRMED** | Timer checks feed availability twice, republishes pool-entry priority, and uniquely performs QUEUED→FEEDING. | `0x82BA6AF4..0x82BA6B58`, second check `0x82BA6B90..0x82BA6BB0`. |
| **CONFIRMED** | Codec 3 zero-time current request is delayed by exactly `0.005333333333333333`. | `0x82BA6B5C..0x82BA6B8C`; raw double at `0x820B6460`. NaN does not satisfy `==0.0`. |
| **CONFIRMED** | PlayHandler stores last-processed before testing the free slot; all failure paths leave next-free and last-success unchanged. | `0x82BA41EC..0x82BA4214`; failure `0x82BA4390..0x82BA4398`; commit `0x82BA44A0..0x82BA44CC`. |
| **CONFIRMED** | PlayHandler queues the loop file twice and latches only the first nonzero request ID. | `0x82BA4448..0x82BA449C`. |
| **CONFIRMED** | PlayHandler leaks an already-acquired StreamPool handle if loop-name allocation fails. | Acquire/store `0x82BA4318..0x82BA4330`; allocation-null branch to failure `0x82BA4380..0x82BA4398`; no ReleaseStream call exists in between. Do not silently repair it. |
| **CONFIRMED** | Stop removes every non-FREE request (including COMPLETE), resets only the banked cursors/cache, and arms 16 declick samples. | `0x82BA44F8..0x82BA4564`; cleanup cursor `+0x1CF` is not reset. |
| **CONFIRMED** | RemoveRequest releases decoder, clears matching feed states, conditionally releases chunks, releases pool under System lock, frees loop name, frees request, optionally expels voice. | `0x82BA0498..0x82BA055C`. Neither external pointers nor file-name pointer are nulled. |
| **CONFIRMED** | ChunkParsed is the seven-argument homed callback shape, not a string/data label. | `0x82BA3FF8..0x82BA407C`: minimum 8 bytes, BE word, top-bit flag, masked size, consumed output, optional four-byte rewrite. |
| **CONFIRMED** | StreamNextChunk's failed feed-slot reservation still charges bytes and loses the obtained chunk. | GetFeedSlot `0x82BA6104..0x82BA610C`, charge `0x82BA6110..0x82BA611C`, failure test only at `0x82BA6120..0x82BA6124`. |
| **CONFIRMED** | Resident GetFeedSlot returns are ignored in StartRequest, HandleLoopStart, and HandleSampleEnd. | `0x82BA6554..0x82BA6558`, `0x82BA61E4..0x82BA61E8`, `0x82BA62B4..0x82BA62B8` / `0x82BA638C..0x82BA6390`. |
| **CONFIRMED** | SubmitChunk leaves `pChunkInfo` untouched, writes the stream pointer/state/owner, and passes `continue = !isNewFeedChunk`. | `0x82BA45D0..0x82BA461C`, Feed calls `0x82BA4620..0x82BA4658`. |
| **CONFIRMED** | HandleSampleEnd discards new QueueFile request IDs on both loop requeues. | Calls at `0x82BA6328` and `0x82BA640C`; neither result is stored. |
| **CONFIRMED** | SetSeekData ignores Parse's result and has an asymmetric reset that leaves version and samples-fed stale. | Parse/copies `0x82B9C0B0..0x82B9C104`; reset `0x82B9C108..0x82B9C128`. |
| **CONFIRMED** | FeedCleanup uses three distinct feed cursors and advances cleanup even when the decoder still owes samples. | Entry/bound `0x82BA0278..0x82BA0284`; remaining test branches to common advance `0x82BA0300..0x82BA034C`; advance/wrap `0x82BA034C..0x82BA0374`. |
| **CONFIRMED** | RequestCleanup is an uncapped state-4 loop and uses equality wrap, not modulo. | `0x82BA4094..0x82BA40E4`. |
| **CONFIRMED** | `lbz 8(config)` must be a named low-byte read on host. | Construction assembly reads console `+8`; current host code correctly uses `static_cast<u8>(apConfig->mFlagAndField8)`. A raw x64 `+8` lands inside widened `mpDesc`. |
| **CONFIRMED** | Pseudocode's `&0xFFF8` is 16-bit truncation noise, not a host alignment mask. | GetSize/Create use `clrrwi` align operations; current `ComputeLayout` correctly uses host `sizeof`/`alignof` rather than the pseudocode mask. |

### Complete stride audit

Every site below is a **console record stride**. The host expression is typed array
subscript/`sizeof`, even where today's host size happens to equal the literal.

| Record | All sites in the construction + streaming call graph | Host rule |
|---|---|---|
| `RequestInternal`, console `0x30` | GetSize `0x82BA024C`; Create init `0x82BA6D48`; Process `0x82BA05A8`, `0x82BA0628`, `0x82BA08A8`, `0x82BA09E0`; Event scan `0x82BA5DA8`; PlayHandler `0x82BA41FC`; StopHandler `0x82BA4534`; Modify handler `0x82BA0428`; RemoveRequest `0x82BA0478`; FeedCleanup `0x82BA02B0`; RequestCleanup `0x82BA40D0`; StreamLostCallback `0x82BA4154`; StartRequest `0x82BA644C`; SubmitChunk `0x82BA45BC`; StreamNextChunk `0x82BA6098`; HandleLoopStart `0x82BA61C0`; HandleSampleEnd `0x82BA625C`; UnpackHeader `0x82B9BF18`; SetSeekData `0x82B9C08C`; timer `0x82BA69C4`, `0x82BA6A84`, `0x82BA6C70`. | `GetRequestInternal(i)` / `RequestInternal[i]`. Current host size is coincidentally 48. |
| `RequestExternal`, console `0x50` | Create allocation `0x82BA6CEC`; Event scan `0x82BA5DAC`; PlayHandler `0x82BA4220`; RemoveRequest `0x82BA048C`; FeedCleanup `0x82BA031C`; StartRequest `0x82BA6460`; SubmitChunk `0x82BA4584`; StreamNextChunk `0x82BA60A8`; HandleLoopStart `0x82BA617C`; HandleSampleEnd `0x82BA626C`; UnpackHeader `0x82B9BF30`; SetSeekData `0x82B9C094`; timer `0x82BA6B14`. | `mpRequestExternal[i]`; after correcting the seek pointer the x64 record is 120 bytes. |
| `SndPlayer1FeedDesc`, console `0x10` | Create init `0x82BA6DDC`; GetFeedSlot `0x82BA0388`; Process `0x82BA0688`, `0x82BA06D0`, `0x82BA06E8`, `0x82BA081C`, `0x82BA0958`, `0x82BA0A54`, `0x82BA0A98`; RemoveRequest `0x82BA0500`; FeedCleanup `0x82BA0290`; SubmitChunk `0x82BA45D4`; StreamNextChunk `0x82BA6134`; timer `0x82BA6AF8`, `0x82BA6BA0`. | `mFeedDesc[i]`; current x64 size is 24. `clrlslwi` at `0x82BA0A98` is scaling, not an alignment mask. |
| `DecoderRequest`, console `0x14` | Process `0x82BA0830`, `0x82BA0AB4`; FeedCleanup `0x82BA02C4`; raw Decoder::Feed `0x82B6793C`; raw DecoderFactory allocation/init `0x82B6C7B0`, `0x82B6C948`; GetSamplesRemaining synthesized `5*i` then `*4` at `0x826914D8..0x826914E0`. | `RequestQueue()[i]` or named Decoder methods. Corrected x64 size is 32. |
| `StreamPool::StreamHandle`, console `0x20` | AcquireStream walks at `0x82B6BB08`, `0x82B6BB34`, `0x82B6BBD4`. | Typed `StreamHandle[i]`; it contains callback/context/Stream pointers. |
| filesys `Request`, console `0x140` | Raw per-request buffered query `0x82BBD960`. | `StreamState::mpRequests[i]`; current `stream.h` already does this. |
| Deferred STOP, console `8` | Producer advance `0x82BA5C94`; handler return `0x82BA454C`. | Both `sizeof(SndPlayer1StopCommand)`. |
| Deferred MODIFY, console `0x18` | Producer advance `0x82BA5EB0`; handler return `0x82BA0454`. | Both `sizeof(SndPlayer1ModifyStartTimeCommand)`. |
| Deferred PLAY, console aligned `0x38 + path` | Producer compute/advance `0x82BA5FB4..0x82BA5FD8`; handler return `0x82BA44D0`. | `align_up(offsetof(PlayCommand, macPath)+nameBytes, alignof(PlayCommand))`; stamp the same value into `u16 muRecordSize`. |

## 2. Faithful C++ specification

### Hard implementation gate discovered by this verification

It is impossible to compile all four faithful bodies against the declarations **exactly as
they stand at this verification snapshot** without casts to incomplete types. Two important
corrections landed in the current headers during the audit and are already usable:
`RequestExternal::pSeekData`/the three named parser scalars/`mIsNewFeedChunk`, and
`DecoderRequest::mpSeekData` plus the pointer-typed `Decoder::Feed` argument. They make the
host request sizes 120 and 32 respectively. Do not revert them.

The remaining binary-attested prerequisites are:

1. Decoder `+0x20` becomes a named `u32 muInstanceSize` (or a named accessor over it).
2. Declare/body `DecoderRegistry::DecoderFactory(DecoderDesc*, u32 channels,
   u32 requestCount, System*)` using the repository's explicit-`self` member convention.
3. Home the minimum `StreamPool`/typed handle surface in the external inventory below.
4. Retype the existing opaque SndPlayer1 storage where it is now dereferenced:
   `RequestExternal::streamHandle` to `StreamPool::StreamHandle *`,
   `pRwCoreStream` to `rw::core::filesys::Stream *`, and the two feed pointers to
   `Chunk *`/`Stream *`. Casts could compile, but named pointer fields are the faithful home.
5. The factory path also requires the currently opaque `DecoderDesc` callback prefix and
   the incomplete `DecoderBuffer` fixed header to be homed; otherwise DecoderFactory can
   neither construct a codec nor size/seed its inline source buffer faithfully.
6. Keep the SampleBuffer/DecoderBuffer type-pun guarded by member-offset assertions until
   those two declarations are unified. ARTIST passes the same descriptor pointer directly;
   the current x64 layouts agree only by coincidence at the fields Process consumes.

The bodies below use every existing tree name where it is valid. The few corrected names
above are marked `REQUIRED TYPE FIX`; they are not speculative new engine concepts.

### File-local records and exact machine helpers

```cpp
// Required includes in SndPlayer1.cpp:
//   SDKs/EATech/rwcore/filesys/stream.h
//   rw/audio/core/BitGetter.h
//   rw/audio/core/Decoder.h
//   rw/audio/core/DecoderRegistry.h
//   rw/audio/core/SeekTableParser.h
//   rw/audio/core/Voice.h
//   <cassert>, <cstddef>, <cstring>, <limits>

namespace
{
// Names below come from DecFIGS' sndplayer1.h where that build carries the type.
struct SndPlayer1IsRequestDoneParams
{
    f32 requestHandle;
    f32 isRequestDone;
};
struct SndPlayer1GetRequestBufferedParams
{
    f32 requestHandle;
    f32 streamBytesBuffered;
    f32 isFullyBuffered;
};
struct SndPlayer1ModifyStartTimeParams
{
    f64 newStartTime;
    f32 requestHandle;
};

struct SndPlayer1PlayLegacyParams
{
    f64 startTime;
    f64 streamFileOffset;
    const char *pStreamFilePath;
    const void *pRamData;
    u32 streamPoolGuid;
    f32 expelMode;
    f32 requestHandle; // out
};

struct SndPlayer1PlayParams
{
    f64 startTime;
    f64 streamFileOffset;
    f64 seekTime;
    const char *pStreamFilePath;
    const void *pRamData;
    const void *pSeekData;
    u32 streamPoolGuid;
    f32 expelMode;
    f32 requestHandle; // out
};

struct SndPlayer1StopCommand
{
    int (*pHandler)(void *);
    SndPlayer1 *pPlayer;
};

struct SndPlayer1ModifyStartTimeCommand
{
    int (*pHandler)(void *);
    SndPlayer1 *pPlayer;
    f64 startTime;
    f32 requestHandle;
};

struct SndPlayer1PlayCommand
{
    int (*pHandler)(void *);
    SndPlayer1 *pPlayer;
    f64 startTime;
    f64 streamFileOffset;
    f64 seekTime;
    u32 streamPoolGuid;
    const void *pRamData;
    const void *pSeekData;
    u16 recordSize;
    u8 expelMode;
    f32 requestHandle;
    char path[1];
};

static size_t AlignUpSize(size_t value, size_t alignment)
{
    return (value + alignment - 1) & ~(alignment - 1);
}

// Exact fctidz result bits: truncate toward zero after saturation.
static u64 PpcFctidzBits(f64 value)
{
    if (value != value) // NaN -> integer-indefinite INT64_MIN
        return 0x8000000000000000ULL;
    if (value >= 9223372036854775808.0)
        return 0x7FFFFFFFFFFFFFFFULL;
    if (value <= -9223372036854775808.0)
        return 0x8000000000000000ULL;
    return static_cast<u64>(static_cast<s64>(value));
}

static s32 PpcFctiwz(f64 value)
{
    if (value != value || value >= 2147483648.0 || value < -2147483648.0)
        return (std::numeric_limits<s32>::min)();
    return static_cast<s32>(value);
}

static u32 ReadBe32(const u8 *p)
{
    return (static_cast<u32>(p[0]) << 24) |
           (static_cast<u32>(p[1]) << 16) |
           (static_cast<u32>(p[2]) << 8)  |
            static_cast<u32>(p[3]);
}

static void WriteBe32(u8 *p, u32 value)
{
    p[0] = static_cast<u8>(value >> 24);
    p[1] = static_cast<u8>(value >> 16);
    p[2] = static_cast<u8>(value >> 8);
    p[3] = static_cast<u8>(value);
}

static u8 AdvanceRequestIndex(u8 index, u8 maxRequests)
{
    u8 next = static_cast<u8>(index + 1u);
    if (next == maxRequests)
        next = 0;
    return next;
}

static f64 ReadDoubleAttribute(const PlugIn::Attribute_t &slot)
{
    f64 value;
    std::memcpy(&value, &slot, sizeof(value));
    return value;
}

static s32 StreamBytesBuffered(rw::core::filesys::Stream *stream)
{
    return stream->miRemaining; // raw 0x82BBD940
}

static s32 StreamRequestBytesBuffered(rw::core::filesys::Stream *stream, u32 requestId)
{
    rw::core::filesys::StreamState *state = stream->mpState;
    const u32 slot = requestId & 0xFFu;
    if (static_cast<s32>(slot) >= static_cast<s32>(state->muRequestCount))
        return 0;
    rw::core::filesys::Request &request = state->mpRequests[slot];
    if (request.miId != requestId || request.miState == 0)
        return 0;
    return static_cast<s32>(request.muBufferedBytes);
}

static DecoderBuffer *AsDecoderBuffer(SampleBuffer *buffer)
{
    static_assert(offsetof(SampleBuffer, mpSamples) == offsetof(DecoderBuffer, mpData),
                  "SndPlayer1 decoder-output pointer view diverged");
    static_assert(offsetof(SampleBuffer, muUnk0C) == offsetof(DecoderBuffer, muSampleCursor),
                  "SndPlayer1 decoder-output cursor view diverged");
    static_assert(offsetof(SampleBuffer, muStride) == offsetof(DecoderBuffer, muStride),
                  "SndPlayer1 decoder-output stride view diverged");
    return reinterpret_cast<DecoderBuffer *>(buffer);
}
}
```

The new SndPlayer1 helper declarations required by these bodies are:

```cpp
static int PlayHandler(void *);
static int StopHandler(void *);
static int ModifyStartTimeHandler(void *);
static void StreamLostCallback(void *);
static void RemoveRequest(SndPlayer1 *, u32);
static void FeedCleanup(SndPlayer1 *);
static void RequestCleanup(SndPlayer1 *);
static u8 StartRequest(SndPlayer1 *, u32);
static char *SubmitChunk(SndPlayer1 *, char *, u32, u8, u8);
static u8 StreamNextChunk(SndPlayer1 *, u32, u8, u8);
static u8 HandleLoopStart(SndPlayer1 *, u32);
static u8 HandleSampleEnd(SndPlayer1 *, u32, u8 *);
static void UnpackHeader(SndPlayer1 *, u32, const u8 *);
static void SetSeekData(SndPlayer1 *, u32, const u8 *, s32);
static s32 ChunkParsed(u8 *, u32, u32, void *, u32, u32, u32 *);
```

### `SndPlayer1::Process` @ `0x82BA0568`

```cpp
int SndPlayer1::Process(SndPlayer1 *self, AudioProcessContext *ctx, bool /*unused*/)
{
    if (self->mNumDeclickSamples != 0 && self->mDcOffsetsGathered != 0)
        return self->Declick(ctx);

    self->mpLoadedDecoder = 0;
    RequestInternal *request = self->GetRequestInternal(self->mCurrentRequest);
    s32 skipped = 0;
    s32 produced = 0;
    s32 remainingInFeed = 0;
    u8 *carveNew = 0;
    u8 *carveSaved = 0;

    if (IsRequestActive(request->state))
    {
        while (request->numSamples == 0)
        {
            request->state = REQUESTSTATE_COMPLETE;
            self->AdvanceCurrentRequest();
            request = self->GetRequestInternal(self->mCurrentRequest);
            if (!IsRequestActive(request->state))
                goto epilogue;
        }

        if (request->sampleRate != self->mPreviousSampleRate ||
            request->numChannels != self->mOutputChannels)
        {
            ctx->mNumSamples = 0;
            ctx->mbChannelCount = request->numChannels;
            ctx->mfSampleRate = request->sampleRate;
            self->mPreviousSampleRate = request->sampleRate;
            self->mOutputChannels = request->numChannels;
            return 1;
        }

        if (self->mFeedDesc[self->mNextFeedSlotToFree].feedState == FEEDSTATE_FREE)
        {
            const u8 fill = self->mNextFeedSlotToFill; // read once
            while (self->mNextFeedSlotToFree != fill)
            {
                u8 next = static_cast<u8>(self->mNextFeedSlotToFree + 1u);
                if (next == KU_MAX_DECODERFEEDS)
                    next = 0;
                self->mNextFeedSlotToFree = next; // committed each lap
                if (self->mFeedDesc[next].feedState != FEEDSTATE_FREE)
                    break;
            }
        }
        if (self->mFeedDesc[self->mNextFeedSlotToFree].feedState != FEEDSTATE_FED)
            goto epilogue;

        if (request->startTime != 0.0)
        {
            u32 frames = 0;
            if (!self->WaitForStartTime(ctx, request->startTime, &frames))
            {
                self->mCurrentRequestSamplesPlayed = 0;
                goto epilogue;
            }
            if (frames != 0)
            {
                if (frames >= self->mSamplesRequested) // unsigned cap
                    frames = self->mSamplesRequested;
                SampleBuffer *dst = ctx->mpDstBuffer;
                for (u32 channel = 0; channel < request->numChannels; ++channel)
                {
                    std::memset(dst->mpSamples + dst->muStride * channel, 0,
                                frames * sizeof(f32));
                }
                ctx->mNumSamples = frames;
                SampleBuffer *oldSrc = ctx->mpSrcBuffer;
                ctx->mpSrcBuffer = dst;
                ctx->mpDstBuffer = oldSrc;
                ctx->mbChannelCount = request->numChannels;
                ctx->mfSampleRate = request->sampleRate;
                self->mCurrentRequestSamplesPlayed = 0;
                return 1;
            }
            request->startTime = 0.0;
        }

        // First and only first-path StackAllocator dereference: no hoisted read.
        {
            StackAllocator *stack = static_cast<StackAllocator *>(
                self->mpSystemUseGetSystemAccessor->mpObjectTable);
            const u32 bytes = (static_cast<u32>(request->decoderInstanceSize) + 0x7Fu)
                            & ~0x7Fu;
            carveSaved = stack->mpTop;
            carveNew = carveSaved - bytes;
            stack->mpTop = carveNew;
        }

        self->mpLoadedDecoder = request->pDecoder; // no null check: faithful
        Decoder *decoder = self->mpLoadedDecoder;
        s32 available = decoder->GetSamplesRemaining(
            self->mFeedDesc[self->mNextFeedSlotToFree].decoderRequestHandle);

        s32 toSkip = request->numSamplesToSkipPlayer;
        if (available < toSkip)
            toSkip = available;
        s32 toDecode = static_cast<s32>(self->mSamplesRequested);
        if (toDecode >= available - toSkip)
            toDecode = available - toSkip;

        request = self->GetRequestInternal(self->mCurrentRequest); // re-materialize
        SampleBuffer *dst = ctx->mpDstBuffer;
        while (toSkip != 0)
        {
            const s32 count = (toSkip < 256) ? toSkip : 256;
            toSkip -= count;
            skipped += decoder->Decode(AsDecoderBuffer(dst), count);
        }

        produced = decoder->Decode(AsDecoderBuffer(dst), toDecode);
        SampleBuffer *oldSrc = ctx->mpSrcBuffer;
        ctx->mpSrcBuffer = dst;
        ctx->mNumSamples = produced;
        ctx->mpDstBuffer = oldSrc;
        ctx->mbChannelCount = request->numChannels;
        ctx->mfSampleRate = request->sampleRate;

        self->mCurrentRequestHandle = request->requestHandle;
        if (self->mCurrentRequestSamplesPlayed == 0)
        {
            self->mCurrentRequestSamplesPlayed =
                request->numSamplesToSkipStream + request->numSamplesToSkipDecoder;
        }
        remainingInFeed = (available - produced) - skipped;
        self->mCurrentRequestSamplesPlayed += produced + skipped;
        self->mCurrentRequestSampleRate = request->sampleRate;
        self->mCurrentRequestNumSamples = request->numSamples;
        self->mFeedDesc[self->mNextFeedSlotToFree].chunkSamplesPlayed += produced + skipped;

        if (self->mCurrentRequestSamplesPlayed == request->numSamples)
        {
            if (request->loopStart >= 0)
            {
                self->mCurrentRequestSamplesPlayed = request->loopStart;
            }
            else
            {
                request->state = REQUESTSTATE_COMPLETE;
                if (self->mpLoadedDecoder != 0)
                {
                    self->mpLoadedDecoder = 0;
                    static_cast<StackAllocator *>(
                        self->mpSystemUseGetSystemAccessor->mpObjectTable)->mpTop = carveSaved;
                }
                self->AdvanceCurrentRequest();
                RequestInternal *nextRequest =
                    self->GetRequestInternal(self->mCurrentRequest);
                if (IsRequestActive(nextRequest->state) && nextRequest->pDecoder != 0)
                {
                    StackAllocator *stack = static_cast<StackAllocator *>(
                        self->mpSystemUseGetSystemAccessor->mpObjectTable);
                    const u32 bytes =
                        (static_cast<u32>(nextRequest->decoderInstanceSize) + 0x7Fu) & ~0x7Fu;
                    carveSaved = stack->mpTop;
                    carveNew = carveSaved - bytes;
                    stack->mpTop = carveNew;
                    self->mpLoadedDecoder = nextRequest->pDecoder;
                }
            }
        }

        while (remainingInFeed == 0)
        {
            SndPlayer1FeedDesc &feed = self->mFeedDesc[self->mNextFeedSlotToFree];
            if (feed.feedState != FEEDSTATE_FED)
                break;
            feed.feedState = FEEDSTATE_DECODECOMPLETED;
            u8 next = static_cast<u8>(self->mNextFeedSlotToFree + 1u);
            if (next == KU_MAX_DECODERFEEDS)
                next = 0;
            Decoder *loaded = self->mpLoadedDecoder; // before cursor store
            self->mNextFeedSlotToFree = next;
            if (loaded != 0 && self->mFeedDesc[next].feedState == FEEDSTATE_FED)
            {
                remainingInFeed = loaded->GetSamplesRemaining(
                    self->mFeedDesc[next].decoderRequestHandle);
            }
            // Otherwise remainingInFeed stays zero and ARTIST returns to the loop top.
            // In particular, a null loaded decoder retires every consecutive FED record.
        }
    }

epilogue:
    if (self->mpLoadedDecoder != 0)
    {
        self->mpLoadedDecoder = 0;
        if (carveNew != 0)
        {
            static_cast<StackAllocator *>(
                self->mpSystemUseGetSystemAccessor->mpObjectTable)->mpTop = carveSaved;
        }
    }

    ctx->mbChannelCount = self->mOutputChannels;
    ctx->mfSampleRate = self->mPreviousSampleRate;
    if (produced == 0)
    {
        if (skipped == 0 && self->mSamplesRequested != 0)
            return 0; // mNumSamples deliberately remains stale
        ctx->mNumSamples = 0;
        return 1;
    }

    u32 channels = ctx->mbChannelCount;
    if (channels >= self->mMaxChannels)
        channels = self->mMaxChannels;
    SampleBuffer *src = ctx->mpSrcBuffer;
    f32 *declick = self->GetDeclickBuffer();
    for (u32 channel = 0; channel < channels; ++channel)
    {
        declick[channel] =
            src->mpSamples[src->muStride * channel + produced - 1];
    }
    self->mDcOffsetsGathered = 1;
    return 1;
}
```

### `SndPlayer1::Event` / `EventEvent` @ `0x82BA5C48`

```cpp
int SndPlayer1::Event(int eventId, void *param)
{
    System *system = mpSystemUseGetSystemAccessor;
    SndPlayer1PlayParams expanded;
    SndPlayer1PlayParams *play = 0;

    switch (eventId)
    {
    case 1:
    {
        SndPlayer1StopCommand *command = reinterpret_cast<SndPlayer1StopCommand *>(
            system->mpDeferredRingBase + system->muDeferredRingCursor);
        system->muDeferredRingCursor += static_cast<u32>(sizeof(*command));
        command->pHandler = &SndPlayer1::StopHandler;
        command->pPlayer = this;
        return 0;
    }
    case 2:
    {
        SndPlayer1IsRequestDoneParams *query =
            static_cast<SndPlayer1IsRequestDoneParams *>(param);
        const f32 handle = query->requestHandle;
        const f32 current = mAttribute[ATTRIBUTE_GETCURRENTREQUEST].mfValue;
        bool done = handle < current;
        if (!done)
        {
            const bool inWindow =
                (handle == current) ||
                (!(handle > mLastRequestHandleProcessed) &&
                 !(handle <= mLastRequestHandleSuccessfullyProcessed));
            done = inWindow &&
                   ReadDoubleAttribute(mAttribute[ATTRIBUTE_GETSAMPLELENGTH]) == 0.0;
        }
        query->isRequestDone = done ? 1.0f : 0.0f;
        return 0;
    }
    case 3:
    {
        SndPlayer1GetRequestBufferedParams *query =
            static_cast<SndPlayer1GetRequestBufferedParams *>(param);
        if (mMaxRequests == 0)
            return 0; // both outputs untouched

        const f32 handle = query->requestHandle;
        for (u32 index = 0; index < mMaxRequests; ++index) // bound re-read each lap
        {
            RequestInternal *request = GetRequestInternal(index);
            if (request->requestHandle == handle && IsRequestActive(request->state))
            {
                RequestExternal &external = mpRequestExternal[index];
                if (external.playType == 0)
                {
                    query->streamBytesBuffered = 0.0f;
                    query->isFullyBuffered = 1.0f;
                    return 0;
                }
                if (external.playType == 1 || external.playType == 2)
                {
                    query->isFullyBuffered = 0.0f;
                    query->streamBytesBuffered =
                        static_cast<f32>(static_cast<f64>(external.numBytesFed));
                    rw::core::filesys::Stream *stream = external.pRwCoreStream;
                    if (stream != 0)
                    {
                        s32 bytes;
                        // Shipped index-vs-handle comparison, intentionally not corrected.
                        if (request->loopStart >= 0 &&
                            static_cast<f32>(static_cast<f64>(static_cast<u64>(index))) ==
                                mAttribute[ATTRIBUTE_GETCURRENTREQUEST].mfValue)
                        {
                            bytes = StreamBytesBuffered(stream);
                        }
                        else
                        {
                            bytes = StreamRequestBytesBuffered(stream,
                                                               external.streamerRequestId);
                        }
                        query->streamBytesBuffered =
                            static_cast<f32>(static_cast<f64>(bytes)) +
                            query->streamBytesBuffered;
                        if (stream->GetRequestState(external.streamerRequestId) != 3 &&
                            stream->GetState() != 2)
                            return 0;
                    }
                    query->isFullyBuffered = 1.0f;
                    return 0;
                }
            }
            query->streamBytesBuffered = 0.0f;
            query->isFullyBuffered = 0.0f;
        }
        return 0;
    }
    case 4:
    {
        const SndPlayer1ModifyStartTimeParams *input =
            static_cast<const SndPlayer1ModifyStartTimeParams *>(param);
        SndPlayer1ModifyStartTimeCommand *command =
            reinterpret_cast<SndPlayer1ModifyStartTimeCommand *>(
                system->mpDeferredRingBase + system->muDeferredRingCursor);
        system->muDeferredRingCursor += static_cast<u32>(sizeof(*command));
        command->pHandler = &SndPlayer1::ModifyStartTimeHandler;
        command->pPlayer = this;
        command->startTime = input->newStartTime;
        command->requestHandle = input->requestHandle;
        return 0;
    }
    case 0:
    {
        const SndPlayer1PlayLegacyParams *legacy =
            static_cast<const SndPlayer1PlayLegacyParams *>(param);
        expanded.startTime = legacy->startTime;
        expanded.streamFileOffset = legacy->streamFileOffset;
        expanded.seekTime = 0.0;
        expanded.pStreamFilePath = legacy->pStreamFilePath;
        expanded.pRamData = legacy->pRamData;
        expanded.pSeekData = 0;
        expanded.streamPoolGuid = legacy->streamPoolGuid;
        expanded.expelMode = legacy->expelMode;
        expanded.requestHandle = legacy->requestHandle; // dead copy, faithful
        play = &expanded;
        break;
    }
    case 5:
        play = static_cast<SndPlayer1PlayParams *>(param);
        break;
    default:
        return 0;
    }

    *mpRequestHandle = *mpRequestHandle + 1.0f;
    if (!(*mpRequestHandle <= 4194304.0f)) // unordered wraps too
        *mpRequestHandle = 1.0f;
    const f32 handle = *mpRequestHandle;
    play->requestHandle = handle;
    if (eventId == 0)
        static_cast<SndPlayer1PlayLegacyParams *>(param)->requestHandle = handle;

    size_t nameBytes = 1;
    if (play->pStreamFilePath != 0)
        nameBytes = std::strlen(play->pStreamFilePath) + 1;
    const size_t recordSize = AlignUpSize(
        offsetof(SndPlayer1PlayCommand, path) + nameBytes,
        alignof(SndPlayer1PlayCommand));
    assert(recordSize <= (std::numeric_limits<u16>::max)());

    SndPlayer1PlayCommand *command = reinterpret_cast<SndPlayer1PlayCommand *>(
        system->mpDeferredRingBase + system->muDeferredRingCursor);
    system->muDeferredRingCursor += static_cast<u32>(recordSize);
    command->pPlayer = this;
    command->pHandler = &SndPlayer1::PlayHandler;
    command->requestHandle = *mpRequestHandle; // re-read
    command->startTime = play->startTime;
    command->streamFileOffset = play->streamFileOffset;
    command->seekTime = play->seekTime;
    command->pRamData = play->pRamData;
    command->pSeekData = play->pSeekData;
    command->streamPoolGuid = play->streamPoolGuid;
    command->recordSize = static_cast<u16>(recordSize);
    command->expelMode = static_cast<u8>(PpcFctidzBits(play->expelMode));

    if (nameBytes == 1)
        command->path[0] = '\0';
    else
        std::memcpy(command->path, play->pStreamFilePath, nameBytes);
    return 0; // console r3 is a dead indeterminate passthrough
}
```

### `SndPlayer1::~SndPlayer1` / `ReleaseEvent` @ `0x82BA4178`

```cpp
SndPlayer1::~SndPlayer1()
{
    StreamLostCallback(this); // unconditional and first
    if (mbTimerAdded == 1)
        System::RemoveTimer(mpSystemUseGetSystemAccessor, &mTimerClient);
    if (mpRequestHandle != 0)
        System::Free(mpSystemUseGetSystemAccessor, mpRequestHandle, 0);
    // No field is cleared by the console body.
}
```

### `SndPlayer1::RwacTimerClient` @ `0x82BA6980`

```cpp
void SndPlayer1::RwacTimerClient(void *context, f32 /*unused*/)
{
    SndPlayer1 *self = static_cast<SndPlayer1 *>(context);
    if (self->mpVoice->mucState == 2)
        return;

    FeedCleanup(self);
    RequestCleanup(self);

    u8 index = self->mCurrentRequest;
    RequestInternal *request = self->GetRequestInternal(index);
    self->mAttribute[ATTRIBUTE_GETCURRENTREQUEST].mfValue = self->mCurrentRequestHandle;
    if (!IsRequestActive(request->state))
    {
        self->SetSampleLengthAttribute(0.0);
        self->SetSamplePositionAttribute(0.0);
        return;
    }

    const f32 rate = self->mCurrentRequestSampleRate; // deliberately no zero guard
    self->SetSampleLengthAttribute(
        static_cast<f64>(static_cast<s64>(self->mCurrentRequestNumSamples)) / rate);
    self->SetSamplePositionAttribute(
        static_cast<f64>(static_cast<s64>(self->mCurrentRequestSamplesPlayed)) / rate);

    if (request->numSamples == 0)
    {
        const u8 zeroScanMaxRequests = self->mMaxRequests; // `lbz` once @0x82BA6A5C
        do
        {
            index = AdvanceRequestIndex(index, zeroScanMaxRequests); // equality wrap
            request = self->GetRequestInternal(index);
            if (!IsRequestActive(request->state))
                return;
            // No cycle cap: an all-active/all-zero ring spins, as does the binary.
        }
        while (request->numSamples == 0);
    }

    for (;;)
    {
        if (!IsRequestActive(request->state))
            return;
        if (self->mFeedDesc[self->mNextFeedSlotToFill].feedState != FEEDSTATE_FREE)
            return;

        const u8 requestIndex = index;
        RequestExternal &external = self->mpRequestExternal[requestIndex];
        if (external.streamHandle != 0)
            external.streamHandle->mfPriority = self->mpVoice->mfPriority; // REQUIRED TYPE FIX

        if (request->state == REQUESTSTATE_QUEUED)
        {
            if (!StartRequest(self, requestIndex))
                return;
            request->state = REQUESTSTATE_FEEDING;
            if (external.codec == 3 && request->startTime == 0.0 &&
                requestIndex == self->mCurrentRequest)
            {
                request->startTime =
                    self->mpSystemUseGetSystemAccessor->mfSystemTime +
                    0.005333333333333333;
            }
        }

        if (request->state == REQUESTSTATE_FEEDING &&
            self->mFeedDesc[self->mNextFeedSlotToFill].feedState == FEEDSTATE_FREE)
        {
            if (external.numSamplesFed == request->loopStart)
            {
                if (!HandleLoopStart(self, requestIndex))
                    return;
                continue;
            }
            if (external.numSamplesFed == request->numSamples)
            {
                u8 finished;
                if (!HandleSampleEnd(self, requestIndex, &finished))
                    return;
                if (finished == 0)
                    continue;
                request->state = REQUESTSTATE_FEEDCOMPLETE;
            }
            else
            {
                if (!StreamNextChunk(self, requestIndex, 0, 0))
                    return;
                continue;
            }
        }

        index = AdvanceRequestIndex(requestIndex, self->mMaxRequests);
        if (index == self->mCurrentRequest)
            return;
        request = self->GetRequestInternal(index);
    }
}
```

### Deferred handlers and teardown helpers

```cpp
int SndPlayer1::PlayHandler(void *rawCommand)
{
    SndPlayer1PlayCommand *command = static_cast<SndPlayer1PlayCommand *>(rawCommand);
    SndPlayer1 *self = command->pPlayer;
    System *system = self->mpSystemUseGetSystemAccessor;

    self->mLastRequestHandleProcessed = command->requestHandle; // before slot test
    const u8 index = self->mNextFreeRequest;
    RequestInternal *request = self->GetRequestInternal(index);
    if (request->state != REQUESTSTATE_FREE)
        return command->recordSize;

    RequestExternal &external = self->mpRequestExternal[index];
    request->requestHandle = command->requestHandle;
    request->pDecoder = 0;
    request->startTime = command->startTime;
    external.streamFileOffset = command->streamFileOffset;
    external.expelMode = command->expelMode;
    request->state = REQUESTSTATE_QUEUED;
    external.numSamplesFed = 0;
    external.numBytesFed = 0;
    external.streamHandle = 0;
    external.streamerRequestId = 0;
    external.pStreamLoopFileName = 0;

    UnpackHeader(self, self->mNextFreeRequest,
                 static_cast<const u8 *>(command->pRamData)); // index re-read by caller shape

    s32 skipSamples = PpcFctiwz(
        static_cast<f64>(request->sampleRate) * command->seekTime);
    if (skipSamples > 0)
    {
        if (external.playType == 2)
            skipSamples = 0;
        if (request->loopStart >= 0)
            skipSamples = 0;
    }
    else
    {
        skipSamples = 0;
    }
    if (request->numSamples <= skipSamples)
        goto fail;

    SetSeekData(self, self->mNextFreeRequest,
                static_cast<const u8 *>(command->pSeekData), skipSamples);

    if (external.playType == 1 || external.playType == 2)
    {
        external.pStreamPool = StreamPool::GetInstance(command->streamPoolGuid);
        // No pStreamPool null check exists in ARTIST.
        external.streamHandle = external.pStreamPool->AcquireStream(
            self->mpVoice->mfPriority, &SndPlayer1::StreamLostCallback, self);
        if (external.streamHandle == 0)
            goto fail;
        external.pRwCoreStream = external.streamHandle->mpStream;

        if (request->loopStart >= 0)
        {
            const u32 bytes = static_cast<u32>(std::strlen(command->path)) + 1u;
            external.pStreamLoopFileName = static_cast<char *>(
                System::Alloc(system, bytes, "SndPlayer1 StreamLoopFileName", 16, 0));
            if (external.pStreamLoopFileName == 0)
                goto fail; // acquired pool entry is deliberately leaked on this path
            std::memcpy(external.pStreamLoopFileName, command->path, bytes);
        }

        bool queueHead = true;
        if (external.playType == 2 && request->loopStart >= 0 &&
            external.gigaSamplesInRam > request->loopStart)
            queueHead = false;
        if (queueHead)
        {
            // +0x40 is loaded with lwz: zero-extend the parser's 32-bit chunk offset.
            const u64 offset = PpcFctidzBits(external.streamFileOffset) +
                               static_cast<u32>(external.mChunkOffset);
            external.streamerRequestId = static_cast<u32>(
                external.pRwCoreStream->QueueFile(
                    command->path, 0, offset, &SndPlayer1::ChunkParsed, self));
        }

        if (request->loopStart >= 0)
        {
            bool queueLoop = true;
            if (external.playType == 2 &&
                external.gigaSamplesInRam >= request->numSamples)
                queueLoop = false;
            if (queueLoop)
            {
                for (int count = 2; count != 0; --count)
                {
                    const f64 offsetValue =
                        static_cast<f64>(static_cast<s64>(external.loopStartStreamOffset)) +
                        external.streamFileOffset;
                    const u32 id = static_cast<u32>(external.pRwCoreStream->QueueFile(
                        command->path, 0, PpcFctidzBits(offsetValue),
                        &SndPlayer1::ChunkParsed, self));
                    if (external.streamerRequestId == 0)
                        external.streamerRequestId = id;
                }
            }
        }
    }

    request->state = REQUESTSTATE_QUEUED; // redundant store is present in ARTIST
    self->mNextFreeRequest = AdvanceRequestIndex(self->mNextFreeRequest,
                                                 self->mMaxRequests);
    self->mLastRequestHandleSuccessfullyProcessed = command->requestHandle;
    return command->recordSize;

fail:
    request->numSamples = 0;
    request->state = REQUESTSTATE_FREE;
    return command->recordSize;
}

int SndPlayer1::StopHandler(void *rawCommand)
{
    SndPlayer1StopCommand *command = static_cast<SndPlayer1StopCommand *>(rawCommand);
    SndPlayer1 *self = command->pPlayer;
    for (u32 index = 0; index < self->mMaxRequests; ++index) // bound re-read
    {
        if (self->GetRequestInternal(index)->state != REQUESTSTATE_FREE)
            RemoveRequest(self, index);
    }
    self->mCurrentRequest = 0;
    self->mNextFreeRequest = 0;
    self->mNextRequestToFree = 0;
    self->mCurrentRequestSamplesPlayed = 0;
    self->mCurrentRequestNumSamples = 0;
    self->mNextFeedSlotToFill = 0;
    self->mNextFeedSlotToFree = 0;
    self->mNumDeclickSamples = 16;
    // mNextFeedSlotToCleanup is deliberately not reset.
    return static_cast<int>(sizeof(SndPlayer1StopCommand));
}

int SndPlayer1::ModifyStartTimeHandler(void *rawCommand)
{
    const SndPlayer1ModifyStartTimeCommand *command =
        static_cast<const SndPlayer1ModifyStartTimeCommand *>(rawCommand);
    SndPlayer1 *self = command->pPlayer;
    const u8 maxRequests = self->mMaxRequests; // this handler loads it once
    for (u32 index = 0; index < maxRequests; ++index)
    {
        RequestInternal *request = self->GetRequestInternal(index);
        if (request->requestHandle != command->requestHandle ||
            !IsRequestActive(request->state))
            continue;

        // fcmpu + ble skips; unordered therefore writes.
        if (!(request->startTime <= self->mpSystemUseGetSystemAccessor->mfSystemTime))
            request->startTime = command->startTime;
        break;
    }
    return static_cast<int>(sizeof(SndPlayer1ModifyStartTimeCommand));
}

void SndPlayer1::RemoveRequest(SndPlayer1 *self, u32 index)
{
    System *system = self->mpSystemUseGetSystemAccessor;
    RequestInternal *request = self->GetRequestInternal(index);
    RequestExternal &external = self->mpRequestExternal[index];

    if (request->pDecoder != 0)
    {
        request->pDecoder->Release();
        request->pDecoder = 0;
    }

    for (u32 slot = 0; slot < KU_MAX_DECODERFEEDS; ++slot)
    {
        SndPlayer1FeedDesc &feed = self->mFeedDesc[slot];
        if (feed.requestIndex != index)
            continue;
        rw::core::filesys::Chunk *chunk = feed.pChunkInfo;
        feed.feedState = FEEDSTATE_FREE; // before chunk-null test
        if (chunk != 0)
        {
            external.numBytesFed = static_cast<s32>(
                static_cast<u32>(external.numBytesFed) - chunk->muSize);
            if (external.streamHandle != 0)
                external.pRwCoreStream->ReleaseChunk(chunk);
            feed.pChunkInfo = 0;
        }
    }

    if (external.streamHandle != 0)
    {
        System::Lock(system);
        external.pStreamPool->ReleaseStream(external.streamHandle);
        System::Unlock(system);
    }
    if (external.pStreamLoopFileName != 0)
        System::Free(system, external.pStreamLoopFileName, 0);
    request->state = REQUESTSTATE_FREE;
    if (external.expelMode == 1)
        Voice::ExpelAfterDecay(self->mpVoice);
}

void SndPlayer1::StreamLostCallback(void *context)
{
    SndPlayer1 *self = static_cast<SndPlayer1 *>(context);
    for (u32 index = 0; index < self->mMaxRequests; ++index) // bound re-read
    {
        if (self->GetRequestInternal(index)->state != REQUESTSTATE_FREE)
            RemoveRequest(self, index);
    }
    self->mCurrentRequest = 0;
    self->mNextFreeRequest = 0;
    self->mNextRequestToFree = 0;
    // Feed cursors and declick state deliberately untouched.
}

void SndPlayer1::RequestCleanup(SndPlayer1 *self)
{
    while (self->GetRequestInternal(self->mNextRequestToFree)->state ==
           REQUESTSTATE_COMPLETE)
    {
        RemoveRequest(self, self->mNextRequestToFree);
        self->mNextRequestToFree = AdvanceRequestIndex(self->mNextRequestToFree,
                                                       self->mMaxRequests);
    }
}

void SndPlayer1::FeedCleanup(SndPlayer1 *self)
{
    if (self->mNextFeedSlotToCleanup == self->mNextFeedSlotToFree)
        return;
    do
    {
        SndPlayer1FeedDesc &feed = self->mFeedDesc[self->mNextFeedSlotToCleanup];
        if (feed.feedState == FEEDSTATE_DECODECOMPLETED)
        {
            Decoder *decoder = self->GetRequestInternal(feed.requestIndex)->pDecoder;
            if (decoder->GetSamplesRemaining(feed.decoderRequestHandle) == 0)
            {
                rw::core::filesys::Chunk *chunk = feed.pChunkInfo;
                feed.feedState = FEEDSTATE_FREE;
                if (chunk != 0)
                {
                    RequestExternal &external = self->mpRequestExternal[feed.requestIndex];
                    external.numBytesFed = static_cast<s32>(
                        static_cast<u32>(external.numBytesFed) - chunk->muSize);
                    if (feed.pRwCoreStream != 0)
                        feed.pRwCoreStream->ReleaseChunk(chunk);
                    feed.pChunkInfo = 0;
                }
            }
        }
        u8 next = static_cast<u8>(self->mNextFeedSlotToCleanup + 1u);
        if (next == KU_MAX_DECODERFEEDS)
            next = 0;
        self->mNextFeedSlotToCleanup = next;
    }
    while (self->mNextFeedSlotToCleanup != self->mNextFeedSlotToFree);
}
```

### Chunk parsing, packed header, and seek-table helpers

```cpp
s32 SndPlayer1::ChunkParsed(u8 *buffer, u32 available, u32 /*requestId*/,
                            void * /*context*/, u32 /*handlerA*/, u32 /*handlerB*/,
                            u32 *consumed)
{
    if (available < 8)
        return 0;
    const u32 raw = ReadBe32(buffer);
    const u32 isLast = raw >> 31;
    const u32 size = raw & 0x7FFFFFFFu;
    if (size > available)
        return 0;
    *consumed = size;
    if (isLast == 1)
    {
        WriteBe32(buffer, size); // clear the top-bit flag in the buffered bytes
        return 2;
    }
    return 1;
}

void SndPlayer1::UnpackHeader(SndPlayer1 *self, u32 index, const u8 *header)
{
    RequestInternal *request = self->GetRequestInternal(index);
    RequestExternal &external = self->mpRequestExternal[index];
    BitGetter bits;
    bits.mpBitBuffer = header;
    bits.mBitPosition = 0;

    (void)BitGetter::GetBits(&bits, 4); // discarded version
    external.codec = static_cast<u8>(BitGetter::GetBits(&bits, 4));
    request->numChannels = static_cast<u8>(BitGetter::GetBits(&bits, 6) + 1u);
    request->sampleRate = static_cast<f32>(
        static_cast<f64>(static_cast<u64>(BitGetter::GetBits(&bits, 18))));
    external.playType = static_cast<u8>(BitGetter::GetBits(&bits, 2));
    const u32 loopFlag = BitGetter::GetBits(&bits, 1);
    request->numSamples = static_cast<s32>(BitGetter::GetBits(&bits, 29));

    if (static_cast<u8>(loopFlag) != 0)
        request->loopStart = static_cast<s32>(BitGetter::GetBits(&bits, 32));
    else
        request->loopStart = -1;

    if (external.playType == 2)
        external.gigaSamplesInRam = static_cast<s32>(BitGetter::GetBits(&bits, 32));

    if (loopFlag != 0)
    {
        if (external.playType == 1 ||
            (external.playType == 2 &&
             request->loopStart >= external.gigaSamplesInRam))
        {
            external.loopStartStreamOffset =
                static_cast<s32>(BitGetter::GetBits(&bits, 32));
        }
        else
        {
            external.loopStartStreamOffset = 0;
        }
    }
    // No-loop arm deliberately leaves loopStartStreamOffset untouched.
    external.pSampleData = const_cast<char *>(
        reinterpret_cast<const char *>(header + (bits.mBitPosition >> 3)));
}

void SndPlayer1::SetSeekData(SndPlayer1 *self, u32 index,
                             const u8 *seekTable, s32 targetSample)
{
    RequestInternal *request = self->GetRequestInternal(index);
    RequestExternal &external = self->mpRequestExternal[index];
    if (targetSample > 0 && seekTable != 0)
    {
        SeekTableParser parser;
        (void)parser.Parse(const_cast<u8 *>(seekTable), targetSample);
        request->numSamplesToSkipDecoder = parser.mDecoderSkip;
        request->numSamplesToSkipStream = parser.mStreamSkip;
        external.mPlayerSkip = parser.mPlayerSkip;
        external.mChunkOffset = parser.mChunkOffset;
        external.pSeekData = parser.mpSeekData; // REQUIRED TYPE FIX
        external.mSeekDataVersion = parser.mSeekDataVersion;
        external.mIsNewFeedChunk = parser.mIsNewFeedChunk;
        request->numSamplesToSkipPlayer = 0;
        external.numSamplesFed = request->numSamplesToSkipStream;
    }
    else
    {
        request->numSamplesToSkipDecoder = 0;
        external.mPlayerSkip = 0;
        external.mChunkOffset = 0;
        external.pSeekData = 0;
        external.mIsNewFeedChunk = 1;
        request->numSamplesToSkipPlayer = 0;
        request->numSamplesToSkipStream = 0;
        // mSeekDataVersion and numSamplesFed deliberately untouched.
    }
}
```

### Decoder/stream feeder helpers

The unchecked lookup must include the eight adjacent rodata words that codec values 8..15
read in ARTIST. This avoids introducing a host-language OOB before reproducing the finite
four-bit lookup.

```cpp
static const u32 kDecoderLookupWords[16] = {
    0x58617330u, 0x454C3330u, 0x50364230u, 0x45586D30u,
    0x58617331u, 0x454C3331u, 0x4C333250u, 0x4C333253u,
    0x536E6450u, 0x6C617965u, 0x72312052u, 0x65717565u,
    0x73744861u, 0x6E646C65u, 0x20616E64u, 0x20526571u
};

u8 SndPlayer1::StartRequest(SndPlayer1 *self, u32 index)
{
    RequestInternal *request = self->GetRequestInternal(index);
    RequestExternal &external = self->mpRequestExternal[index];
    System *lockedSystem = self->mpSystemUseGetSystemAccessor;
    System::Lock(lockedSystem);

    DecoderRegistry *registry =
        System::GetDecoderRegistry(self->mpSystemUseGetSystemAccessor);
    DecoderDesc *descriptor = DecoderRegistry::GetDecoderHandle(
        registry, static_cast<int>(kDecoderLookupWords[external.codec]));

    // No descriptor-null guard: raw DecoderFactory dereferences it immediately.
    request->pDecoder = DecoderRegistry::DecoderFactory(
        registry, descriptor, request->numChannels, KU_MAX_DECODERFEEDS,
        self->mpSystemUseGetSystemAccessor);
    if (request->pDecoder == 0)
    {
        System::Unlock(lockedSystem);
        return 0;
    }

    // REQUIRED TYPE FIX: this is the factory's total decoder-instance size at +0x20.
    request->decoderInstanceSize =
        static_cast<u16>(request->pDecoder->GetInstanceSize());
    const u8 seekActive =
        (request->numSamplesToSkipStream != 0 ||
         request->numSamplesToSkipDecoder != 0 ||
         external.mPlayerSkip != 0) ? 1u : 0u;

    if (external.playType != 0 && external.playType != 2)
    {
        if (!StreamNextChunk(self, index, external.mIsNewFeedChunk, seekActive))
        {
            if (request->pDecoder != 0)
            {
                request->pDecoder->Release();
                request->pDecoder = 0;
            }
            System::Unlock(lockedSystem);
            return 0;
        }
    }
    else
    {
        u32 slot; // GetFeedSlot return intentionally ignored
        self->GetFeedSlot(&slot);
        external.feedSlotLatest = static_cast<u8>(slot);
        external.pNextChunk = SubmitChunk(
            self, external.pSampleData + external.mChunkOffset, index,
            external.mIsNewFeedChunk, seekActive);
    }

    System::Unlock(lockedSystem);
    return 1;
}

char *SndPlayer1::SubmitChunk(SndPlayer1 *self, char *block, u32 index,
                              u8 isNewFeedChunk, u8 seekActive)
{
    RequestInternal *request = self->GetRequestInternal(index);
    RequestExternal &external = self->mpRequestExternal[index];
    const u32 blockBytes = ReadBe32(reinterpret_cast<const u8 *>(block));
    const u32 numSamples = ReadBe32(reinterpret_cast<const u8 *>(block + 4));
    const void *payload = block + 8;

    SndPlayer1FeedDesc &feed = self->mFeedDesc[external.feedSlotLatest];
    feed.requestIndex = static_cast<u8>(index);
    feed.feedState = FEEDSTATE_FED;
    feed.chunkSamplesPlayed = 0;
    feed.pRwCoreStream = external.pRwCoreStream;
    // pChunkInfo is deliberately untouched here.

    const u8 continueStream = (isNewFeedChunk == 0) ? 1u : 0u;
    u8 decoderHandle;
    if (seekActive == 0)
    {
        decoderHandle = request->pDecoder->Feed(
            payload, static_cast<s32>(numSamples), continueStream, 0, 0, 0);
    }
    else
    {
        feed.chunkSamplesPlayed = request->numSamplesToSkipDecoder;
        decoderHandle = request->pDecoder->Feed(
            payload, static_cast<s32>(numSamples), continueStream,
            request->numSamplesToSkipDecoder, external.pSeekData,
            static_cast<u8>(external.mSeekDataVersion));
    }
    feed.decoderRequestHandle = decoderHandle;
    external.numSamplesFed = static_cast<s32>(
        static_cast<u32>(external.numSamplesFed) + numSamples);
    return block + blockBytes;
}

u8 SndPlayer1::StreamNextChunk(SndPlayer1 *self, u32 index,
                               u8 isNewFeedChunk, u8 seekActive)
{
    RequestInternal *request = self->GetRequestInternal(index);
    RequestExternal &external = self->mpRequestExternal[index];
    if (request->state == REQUESTSTATE_QUEUED && external.streamerRequestId != 0 &&
        external.pRwCoreStream->GetRequestState(external.streamerRequestId) == 0)
    {
        request->numSamples = 0;
        return 0;
    }

    rw::core::filesys::Chunk *chunk = external.pRwCoreStream->GetChunk();
    if (chunk == 0)
        return 0;
    u32 slot;
    const bool gotSlot = self->GetFeedSlot(&slot);
    external.numBytesFed = static_cast<s32>(
        static_cast<u32>(external.numBytesFed) + chunk->muSize); // before test
    if (!gotSlot)
        return 0; // obtained chunk and byte charge are deliberately leaked

    external.feedSlotLatest = static_cast<u8>(slot);
    self->mFeedDesc[slot].pChunkInfo = chunk;
    (void)SubmitChunk(self, reinterpret_cast<char *>(chunk->mpData), index,
                      isNewFeedChunk, seekActive);
    return 1;
}

u8 SndPlayer1::HandleLoopStart(SndPlayer1 *self, u32 index)
{
    RequestExternal &external = self->mpRequestExternal[index];
    if (external.playType == 1)
        return StreamNextChunk(self, index, 1, 0) ? 1u : 0u;
    if (external.playType != 0)
    {
        RequestInternal *request = self->GetRequestInternal(index);
        if (request->loopStart >= external.gigaSamplesInRam)
            return StreamNextChunk(self, index, 1, 0) ? 1u : 0u;
    }

    external.pLoopStartChunk = external.pNextChunk;
    u32 slot; // return intentionally ignored
    self->GetFeedSlot(&slot);
    external.feedSlotLatest = static_cast<u8>(slot);
    external.pNextChunk = SubmitChunk(self, external.pNextChunk, index, 1, 0);
    return 1;
}

u8 SndPlayer1::HandleSampleEnd(SndPlayer1 *self, u32 index, u8 *finished)
{
    RequestInternal *request = self->GetRequestInternal(index);
    RequestExternal &external = self->mpRequestExternal[index];
    if (request->loopStart < 0)
    {
        *finished = 1;
        return 1;
    }
    *finished = 0;

    if (external.playType == 0)
    {
        if (request->loopStart == 0)
            external.pLoopStartChunk = external.pSampleData;
        u32 slot; // return intentionally ignored
        self->GetFeedSlot(&slot);
        external.feedSlotLatest = static_cast<u8>(slot);
        external.numSamplesFed = request->loopStart;
        external.pNextChunk = SubmitChunk(self, external.pLoopStartChunk, index, 1, 0);
        return 1;
    }

    if (external.playType == 1)
    {
        const f64 offsetValue =
            static_cast<f64>(static_cast<s64>(external.loopStartStreamOffset)) +
            external.streamFileOffset;
        (void)external.pRwCoreStream->QueueFile(
            external.pStreamLoopFileName, 0, PpcFctidzBits(offsetValue),
            &SndPlayer1::ChunkParsed, self); // returned ID deliberately discarded
        external.numSamplesFed = request->loopStart;
        return StreamNextChunk(self, index, 1, 0) ? 1u : 0u;
    }

    external.numSamplesFed = request->loopStart;
    if (request->loopStart < external.gigaSamplesInRam)
    {
        if (request->loopStart == 0)
            external.pLoopStartChunk = external.pSampleData;
        u32 slot; // return intentionally ignored
        self->GetFeedSlot(&slot);
        external.feedSlotLatest = static_cast<u8>(slot);
        external.pNextChunk = SubmitChunk(self, external.pLoopStartChunk, index, 1, 0);
    }
    if (external.gigaSamplesInRam >= request->numSamples)
        return 1;

    const f64 offsetValue =
        static_cast<f64>(static_cast<s64>(external.loopStartStreamOffset)) +
        external.streamFileOffset;
    (void)external.pRwCoreStream->QueueFile(
        external.pStreamLoopFileName, 0, PpcFctidzBits(offsetValue),
        &SndPlayer1::ChunkParsed, self); // returned ID deliberately discarded
    if (request->loopStart < external.gigaSamplesInRam)
        return 1;

    external.numSamplesFed = request->loopStart;
    return StreamNextChunk(self, index, 1, 0) ? 1u : 0u;
}
```

## 3. EXTERNAL SURFACE INVENTORY

`HOMED` means both a usable declaration and a real host body exist where a body is needed.
`NOT HOMED` includes partially declared records whose missing portion is required on the
streaming path. This is why “only StreamPool is missing” is not an implementation plan.

| Symbol or surface | Status | Current home / exact requirement |
|---|---|---|
| `SndPlayer1`, `RequestInternal`, `RequestExternal`, `SndPlayer1FeedDesc`, layout/accessors, `PreProcess`, `WaitForStartTime`, `Declick`, `AdvanceCurrentRequest`, `GetFeedSlot` | **HOMED** | `b5-decomp/vendor/renderware/include/rw/audio/core/plugins/SndPlayer1.h` and matching `.cpp`. The current seek block is correctly named/typed. The opaque stream pointers still need the typed refinements below. |
| The new SndPlayer1 helpers declared in section 2 | **NOT HOMED** | No declarations/bodies exist in the current SndPlayer1 header/source. Section 2 is their verified implementation specification. DecFIGS supplies the names `IsRequestDoneParams`, `GetRequestBufferedParams`, `ModifyStartTimeParams`, `PlayParams`, `PlayCommand`, and `ModifyStartTimeCommand`; the ARTIST-only PLAY1 additions and command tail are instruction-derived. |
| `PlugIn`, `PlugIn::Attribute_t`; `System::{Alloc,Free,Lock,Unlock,RemoveTimer,GetDecoderRegistry}`; deferred-ring fields; `System::mfSystemTime`; `StackAllocator` link | **HOMED** | `b5-decomp/vendor/renderware/include/rw/audio/core/PlugIn.h`; bodies in `vendor/renderware/src/rw/audio/core/System.cpp`. Process reaches `StackAllocator` through the already-named `System::mpObjectTable`. |
| `Mixer`, `SampleBuffer`, `StackAllocator` and the fields Process reads | **HOMED** | `b5-decomp/vendor/renderware/include/rw/audio/core/Mixer.h`. The currently consumed `mpSamples`/sample-count/stride offsets match `DecoderBuffer`; see the partial-layout row below before changing either record. |
| `Voice::mfPriority`, `Voice::mucState`, `Voice::ExpelAfterDecay` | **HOMED** | `b5-decomp/vendor/renderware/include/rw/audio/core/Voice.h`; body in `vendor/renderware/src/rw/audio/core/Voice.cpp`. |
| `TimerHandle` and `System::RemoveTimer` | **HOMED** | `b5-decomp/vendor/renderware/include/rw/audio/core/TimerHandle.h` and `PlugIn.h`; System body as above. |
| `Decoder::{Decode,GetSamplesRemaining,Feed,Release}`, `DecoderRequest` | **HOMED** | `b5-decomp/vendor/renderware/include/rw/audio/core/Decoder.h` and `vendor/renderware/src/rw/audio/core/Decoder.cpp`. The current `DecoderRequest` has both pointer fields and is 32 bytes on x64; `Feed` now takes `const u8 *apSeekData`. |
| `DecoderRegistry::{GetDecoderHandle,CreateInstance,RegisterDecoder,...}` and list linkage | **HOMED** | `b5-decomp/vendor/renderware/include/rw/audio/core/DecoderRegistry.h` and matching `.cpp`, except for the factory and descriptor prefix separately listed below. |
| `DecoderRegistry::DecoderFactory` @ `0x82B6C778` | **NOT HOMED** | No dossier, declaration, or body. Raw XEX and DecFIGS agree on member shape `Decoder *DecoderFactory(void *handle, u32 channels, u32 maxSlots, System *)`; under the tree's convention add explicit `DecoderRegistry *self`. The raw function immediately calls descriptor slots and allocates `maxSlots * sizeof(DecoderRequest)` on host. |
| `Decoder::muInstanceSize` (ARTIST/DecFIGS `mInstanceSize`) | **NOT HOMED** | Current `Decoder.h` hides `+0x20` in `mPad20[4]`. Factory stores the total at `0x82B6C87C`; StartRequest loads it at `0x82BA64BC` and narrows it to `RequestInternal::decoderInstanceSize`. Add the real `u32` member/accessor—do not call it a decoder-independent scratch constant. |
| `DecoderDesc` factory callback prefix and `muMaxBlockSize` | **NOT HOMED** | Current `DecoderRegistry.h` leaves `+0x00..+0x0F` opaque and stops at GUID. Factory needs DecFIGS-named `pGetSize`, `pCreateInstanceEvent`, `pReleaseEvent`, `pDecodeEvent`, and `u16 maxBlockSize`, all X360-attested at `0x82B6C798..0x82B6C920`. Current registered codec records initialize those callback words to zero, so a declaration-only factory would still crash. Owner recovery in `DecoderRegistry.cpp` must use `offsetof(DecoderDesc, mpNext)`, not console `0x10`. |
| Complete `Decoder` fixed header and `DecoderBuffer`/`Mixer::SampleBuffer` shared prefix | **NOT HOMED** | Both named types exist, but their complete factory-required shape does not. Factory proves Decoder `+0x04/+0x08` are pointers, `+0x18` is GUID, and `+0x20` is instance size (`0x82B6C820..0x82B6C89C`). It proves buffer `+0x00` is `System *`, `+0x04` storage, `+0x08` a pointer-sized temp slot, `+0x0C` count, `+0x0E` max/stride, `+0x10` channels (`0x82B6C910..0x82B6C920`). Correct both buffer views together and retain the section-2 offset assertions. |
| `BitGetter::GetBits` | **HOMED** | `b5-decomp/vendor/renderware/include/rw/audio/core/BitGetter.h` and matching `.cpp`. It consumes the SNR header MSB-first by byte. |
| `SeekTableParser::{Parse,...}` and named output members | **HOMED** | `b5-decomp/vendor/renderware/include/rw/audio/core/SeekTableParser.h` and matching `.cpp`. Its `mpSeekData`, stream/decoder/player skips, chunk offset, version, and new-feed byte map directly at `0x82B9C0BC..0x82B9C0F4`. |
| `rw::core::filesys::{Stream,Chunk,Request,StreamState}`, `QueueFile`, `GetChunk`, `ReleaseChunk`, `GetRequestState`, `GetState` | **HOMED** | `b5-decomp/src/SDKs/EATech/rwcore/filesys/stream.h` and matching `.cpp`. Use the member APIs exactly as section 2 does; the QueueFile zero is a null `Handle *`, not invented flags. |
| `Stream::GetBytesBuffered` @ `0x82BBD940`; `Stream::GetRequestBytesBuffered` @ `0x82BBD948` | **NOT HOMED** as named methods; **not a blocker** | Neither symbol is declared. Their complete raw bodies are the two local typed helpers in section 2: `miRemaining`, or validated `mpState->mpRequests[requestId & 0xff].muBufferedBytes`. No raw offsets or new external symbol are necessary. |
| `rw::audio::core::StreamPool`, `StreamPool::StreamHandle`, `GetInstance`, `AcquireStream`, `ReleaseStream` | **NOT HOMED** | Only the forward declaration exists in `SndPlayer1.h`. Minimum attested surface is shown below. `AcquireStream` dossier `0x82B6BAB0`; `ReleaseStream` dossier `0x82B6BC48`; `GetInstance` was raw-decoded at `0x82B6BA68`. |
| C/C++ primitives used by the spelling (`memset`, `memcpy`, `strlen`, `offsetof`, numeric limits) | **HOMED** | Standard headers `<cstddef>`, `<cstring>`, `<limits>`; `<cassert>` only if the command-size invariant is kept as a debug assertion. |

The minimum pool declaration that the verified SndPlayer1 bodies consume is:

```cpp
class StreamPool
{
public:
    typedef void (*StreamLostFn)(void *);

    struct StreamHandle
    {
        f64 mUnknown00; // copied from pool-owner +8; SndPlayer1 never reads it
        f32 mfPriority;
        StreamLostFn pLostCallback;
        void *pLostContext;
        rw::core::filesys::Stream *mpStream;
        u16 muRefCount;
        u8 mbInUse;
    };

    static StreamPool *GetInstance(u32 guid);
    StreamHandle *AcquireStream(f32 priority, StreamLostFn callback, void *context);
    void ReleaseStream(StreamHandle *handle); // callers do not consume ARTIST's r3
};
```

Those members are ordered from console `+0x00/+0x08/+0x0C/+0x10/+0x14/+0x18/+0x1A`;
they are **not** host offsets. A pool implementation must walk `StreamHandle[]` with typed
subscripts. Natural x64 widening makes the record larger than the console `0x20`.

One activation surface is outside the four-body call graph but still blocks real playback:
`SndPlayer1::GetPlugInDescRunTime` currently returns null and RWAC registration remains
disabled. Do not register `SnP1` until the factory, codec descriptor callbacks, pool, and
the streaming bodies are all real.

## 4. DO NOT INVENT

- Do not name or assign semantics to `StreamHandle::mUnknown00` beyond what the assembly
  proves: AcquireStream copies an `f64` from the pool owner's `+8` at
  `0x82B6BBA4..0x82B6BBB0` / `0x82B6BC28..0x82B6BC30`, and uses it as an eviction
  tie-break at `0x82B6BB68..0x82B6BBCC`. No DWARF name for this pool record was found.
- Do not freeze any StreamPool, RequestInternal, RequestExternal, FeedDesc,
  DecoderRequest, DecoderBuffer, or deferred-command console stride. The complete literal
  sites are in the stride table; every host walk is typed and every producer/handler pair
  uses the same host-derived size.
- Do not “repair” codec 8..15. ARTIST's four-bit codec can index the eight words following
  the real table (`0x82BA647C..0x82BA6494`). The 16-word finite mirror reproduces that read
  without C++ out-of-bounds UB. A missing descriptor then reaches the factory's attested
  unconditional dereference at `0x82B6C798`.
- Do not guess or zero DecoderDesc callbacks. The current standard descriptor objects have
  placeholder zero headers; DecoderFactory calls `pGetSize` and `pCreateInstanceEvent` and
  installs the release/decode callbacks. Each registered codec needs its real host
  callbacks before SndPlayer1 can run.
- Do not guess the host decoder-instance-size overflow outcome. ARTIST intentionally stores
  the factory's `u32` total through `sth` (`0x82BA64BC..0x82BA64C8`). Whether every host
  codec stays below 65536 is knowable only after all host `GetSize` callbacks and the
  corrected buffer/request layouts are live. Preserve the narrowing and measure it; do not
  substitute a console constant.
- Do not connect `RequestExternal::mPlayerSkip` to
  `RequestInternal::numSamplesToSkipPlayer`. SetSeekData copies parser `mPlayerSkip` only to
  external `+0x3C` and explicitly writes zero to request `+0x1C`
  (`0x82B9C0D0..0x82B9C100`). StartRequest only uses the external value to form the seek
  flag; Process consumes the request value. This looks odd, but no missing assignment is
  attested.
- Do not add guards for null decoders, null pools, null streams, failed ignored feed-slot
  reservations, codec bounds, `mMaxRequests==0`, malformed play type 3, or command-ring
  capacity unless a separate PC policy explicitly authorizes divergence. The bodies above
  retain the shipped crashes, stale fields, leaks, uncapped loops, and ignored returns at
  the proving branches cited in the verdict table.
- Do not replace ordered/unordered floating tests with visually equivalent relational
  operators. The required spellings are already explicit: `!(start <= systemTime)` in the
  modify handler; `!(*handle <= 4194304.0f)` for wrap; and the compound negated predicates
  in ISREQUESTDONE. Likewise, keep the `PpcFctidzBits`/`PpcFctiwz` helpers for exceptional
  inputs.
- Do not normalize the timer's byte cursors with `%`, `>=`, or a safety iteration cap.
  Equality-only wrap and the all-active/all-zero infinite loop are observable ARTIST
  behavior (`0x82BA6A60..0x82BA6ABC`). The first zero-sample scan snapshots
  `mMaxRequests`; later advances reload it at their own instruction sites.
- Do not change the Process rollover back-edge. When `mpLoadedDecoder` is null,
  `remainingInFeed` stays zero and ARTIST can mark multiple consecutive FED entries
  decode-complete (`0x82BA0A50..0x82BA0AFC`). This is the substantive error found in the
  banked Process sketch.
- Do not transpose QueueFile's parameters or treat the inserted zero as flags.
  `0x82BC09B0` supplies a null `filesys::Handle *`; the following `u64` is used as a byte
  offset by SndPlayer1 even though the current filesys parameter name says `size`.
- Do not byte-swap the entire SNR/SNS payload. Its scalar headers are big-endian **by
  format** on X360 and the little-endian Remaster; the current PC asset pipeline preserves
  that body. Only the explicit BE word helpers in ChunkParsed/SubmitChunk interpret those
  four-byte fields.
- Do not decide the generic attribute endian policy inside these bodies. ARTIST stores
  attributes 1/2 as full `f64` slots (`0x82BA6A40..0x82BA6A4C`) while generic
  `PlugIn::GetAttribute` reads the slot-leading `f32`. On big-endian PPC that observes the
  double's high word; on little-endian x64 the current raw layout observes its low word.
  Timer/Event above preserve the attested full-double producer/consumer. Whether the
  generic PC accessor should emulate BE word placement or expose a numeric conversion is
  a wider ABI decision not attested by these four functions.
- Do not hand-write a second deleting-destructor thunk. ARTIST splits ReleaseEvent vt[0]
  from the compiler deleting destructor vt[3]; the current host class maps ReleaseEvent to
  `~SndPlayer1()` and lets MSVC synthesize deletion. Keep that established host convention,
  and do not call both teardown paths manually.
- Do not invent a recovery for the acquired-pool-handle leak when loop-name allocation
  fails, the lost Chunk on StreamNextChunk feed-slot failure, the discarded loop QueueFile
  IDs, or SetSeekData's stale version/sample-count fields. Each is instruction-attested and
  called out in the verdict table.
